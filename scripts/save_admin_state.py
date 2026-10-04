"""Validate the authenticated administrator's shared state before publishing it."""
import base64
import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('Shared state must be an object')
    if payload.get('selectionMode', 'clubs') not in ('clubs', 'archers'):
        raise ValueError('Invalid selection mode')
    if not re.fullmatch(r'[A-Z]{3}', payload.get('trackedCountryRaw', 'FRA')):
        raise ValueError('Invalid country')
    for field in ('selectedArchers', 'watchedArchers', 'trackedTournaments'):
        if not isinstance(payload.get(field, []), list):
            raise ValueError(f'Invalid {field}')
    for a in payload.get('selectedArchers', []):
        if not isinstance(a, dict) or not a.get('name') or not a.get('club'):
            raise ValueError('Selected archer needs name and club')
    for t in payload.get('trackedTournaments', []):
        if not isinstance(t, dict):
            raise ValueError('Invalid tournament')
        urls = [t.get(k, '') for k in ('url', 'ic_url', 'ena_url', 'details_url')] + t.get('urls', [])
        for raw in urls:
            if not raw:
                continue
            u = urlparse(raw)
            if u.scheme != 'https' or u.netloc != 'www.ianseo.net' or not re.fullmatch(r'/(?:Details\.php|TourData/\d{4}/\d+/[A-Z0-9]+\.php)', u.path):
                raise ValueError('Invalid tournament source URL')
    payload['updatedAtUtc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    return payload


if __name__ == '__main__':
    encoded = os.environ.get('WF_STATE_B64', '').strip()
    if not encoded or len(encoded) > 250000 or not re.fullmatch(r'[A-Za-z0-9_-]+', encoded):
        raise SystemExit('Invalid state input')
    raw = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
    payload = validate(json.loads(raw.decode('utf-8')))
    target = Path('data/admin_state.json')
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Validated shared state saved')
