import datetime as dt
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ianseo_entries import extract_entries, club_matches
from fetch_ianseo import parse_category_meta, parse_ianseo
from find_next_competition import find_next_competition
from build_competition_catalog import build_catalog
from build_live_data import build_payload, load_urls
from skip_unchanged_data import semantic
from save_admin_state import validate

GROUPED = '<table><tr><td colspan="4">0174246 - SEYNOD</td></tr><tr><td>DUPONT Rennes</td><td>1A</td><td>U18</td><td>Départ 2 - 14h00</td></tr></table>'
FLAT = '<table><tr><th>Target</th><th>Athlete</th><th>Country</th><th>Class</th><th>Session</th></tr><tr><td>2B</td><td>Élodie Martin</td><td>0335067 - RENNES</td><td>U21</td><td>Départ 1 - 09:00</td></tr></table>'
LIVE = '''<div class="results-header-center"><div>Tir en salle</div><div>Annecy, 4 Oct 2026</div></div><table><thead><tr><th colspan="12">Arc Classique [Après 60 flèches]</th></tr></thead><tbody><tr><td>1</td><td>Élodie Martin</td><td>0335067 - RENNES</td><td>250/1</td><td>260/1</td><td>510</td><td>12</td><td>3</td></tr></tbody></table>'''

class EntriesTests(unittest.TestCase):
    def test_grouped_and_schedule(self):
        e = extract_entries(GROUPED, ['0174246'])[0]
        self.assertEqual((e['club'], e['category'], e['depart'], e['time']), ('0174246 - SEYNOD', 'U18', 'Départ 2 - 14h00', '14h00'))
    def test_flat_header_order(self):
        e = extract_entries(FLAT)[0]
        self.assertEqual((e['name'],e['target'],e['club']), ('Élodie Martin','2B','0335067 - RENNES'))
    def test_name_does_not_match_club(self):
        self.assertEqual(extract_entries(GROUPED, ['rennes']), [])
    def test_code_exact_not_substring(self):
        self.assertFalse(club_matches('0174246 - SEYNOD', ['174246']))
    def test_accents(self):
        self.assertTrue(club_matches('1234567 - ÉVIAN', ['evian']))

class ResultsTests(unittest.TestCase):
    def test_indoor60_and_outdoor60(self):
        self.assertTrue(parse_category_meta('Arc Classique [Après 60 flèches]', 'Salle')['finished'])
        self.assertFalse(parse_category_meta('Arc Classique [Après 60 flèches]', 'TAE 70m')['finished'])
    def test_72(self):
        self.assertTrue(parse_category_meta('Arc Classique [Après 72 flèches]')['finished'])
    def test_native_different_colspan(self):
        e = parse_ianseo(LIVE, ['0335067'], 'source')['archers'][0]
        self.assertEqual((e['score'],e['arrows'],e['maxArrows'],e['finished']), (510,60,60,True))
    def test_all_clubs_mode(self):
        self.assertEqual(len(parse_ianseo(LIVE, [], 'source')['archers']),1)
    def test_invalid_200_response(self):
        with self.assertRaises(ValueError): parse_ianseo('File not found.', [], 'source')
    def test_partial_failure_keeps_score(self):
        previous={'competitions':[{'id':'1','name':'Old','sourceUrl':'bad','archers':[{'name':'Paul','score':500}],'fetchedAtUtc':'2026-10-03T10:00:00Z'}]}
        with patch('build_live_data.fetch_html',side_effect=lambda u: LIVE if u=='good' else (_ for _ in ()).throw(OSError('offline'))):
            data=build_payload(['bad','good'], [], previous)
        self.assertEqual(len(data['competitions']),2)
        self.assertTrue(data['competitions'][0]['stale'])
        self.assertEqual(data['archers'][0]['score'],500)
        self.assertEqual(len(data['errors']),1)

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.today=dt.datetime.now(ZoneInfo('Europe/Paris')).date()
        self.t={'to_id':'1','end_date':self.today.isoformat(),'name':'Today','details_url':'details'}
    def test_today_catalog_included(self):
        with patch('build_competition_catalog.list_tournaments', return_value=[self.t]), patch('build_competition_catalog.fetch_text',return_value=GROUPED):
            data=build_catalog('FRA',[self.today.year])
        self.assertEqual(data['count'],1)
        self.assertEqual(data['tournaments'][0]['entries_status'],'published')
    def test_today_next_included(self):
        with patch('find_next_competition.list_tournaments',side_effect=[[self.t],[]]), patch('find_next_competition.fetch_text',side_effect=['<a href="/TourData/2026/1/ENA.php">Entries</a>',GROUPED]):
            data=find_next_competition(self.today,['0174246'],'FRA')
        self.assertTrue(data['found'])
    def test_catalog_failure_reported(self):
        with patch('build_competition_catalog.list_tournaments',return_value=[self.t]), patch('build_competition_catalog.fetch_text',side_effect=OSError('offline')):
            data=build_catalog('FRA',[self.today.year])
        self.assertEqual(data['tournaments'][0]['entries_status'],'error')
        self.assertEqual(data['coverage_status'],'partial')
    def test_catalog_preserves_previous_entries_on_error(self):
        previous={'country':'FRA','tournaments':[{**self.t,'entries':[{'name':'Paul','club':'0174246'}]}]}
        with patch('build_competition_catalog.list_tournaments',return_value=[self.t]), patch('build_competition_catalog.fetch_text',side_effect=OSError('offline')):
            data=build_catalog('FRA',[self.today.year],previous=previous)
        self.assertEqual(data['tournaments'][0]['entries'][0]['name'],'Paul')
        self.assertTrue(data['tournaments'][0]['stale'])
    def test_year_failure_preserves_catalog(self):
        previous={'country':'FRA','tournaments':[{**self.t,'year':str(self.today.year),'entries':[]}]}
        with patch('build_competition_catalog.list_tournaments',side_effect=OSError('offline')):
            data=build_catalog('FRA',[self.today.year],previous=previous)
        self.assertEqual(data['count'],1)
        self.assertEqual(data['coverage_status'],'partial')
    def test_shared_state_rejects_external_source(self):
        with self.assertRaises(ValueError): validate({'trackedTournaments':[{'url':'https://evil.example/IC.php'}]})
    def test_shared_state_preserves_archer_selection(self):
        data=validate({'selectionMode':'archers','selectedArchers':[{'name':'Paul','club':'0174246'}]})
        self.assertEqual(data['selectedArchers'][0]['name'],'Paul')
        self.assertTrue(data['updatedAtUtc'])
    def test_skip_timestamp_only_changes(self):
        self.assertEqual(semantic({'generatedAtUtc':'a','archers':[{'score':10,'fetchedAtUtc':'a'}]}),semantic({'generatedAtUtc':'b','archers':[{'score':10,'fetchedAtUtc':'b'}]}))
        self.assertNotEqual(semantic({'score':10}),semantic({'score':11}))

if __name__ == '__main__': unittest.main()
