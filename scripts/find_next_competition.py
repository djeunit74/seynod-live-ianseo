#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from typing import Dict, List, Optional, Tuple


MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def fetch_text(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SeynodNextCompetitionBot/1.0)",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " | ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_end_date(date_text: str, year: int) -> Optional[dt.date]:
    date_text = date_text.strip()

    m = re.search(r"(\d{1,2})\s*([A-Za-z]{3})\s*-\s*(\d{1,2})\s*([A-Za-z]{3})", date_text)
    if m:
        return dt.date(year, MONTHS[m.group(4).title()[:3]], int(m.group(3)))

    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*([A-Za-z]{3})", date_text)
    if m:
        return dt.date(year, MONTHS[m.group(3).title()[:3]], int(m.group(2)))

    m = re.search(r"(\d{1,2})\s*([A-Za-z]{3})", date_text)
    if m:
        return dt.date(year, MONTHS[m.group(2).title()[:3]], int(m.group(1)))

    return None


def list_tournaments(year: int, country: str) -> List[Dict[str, str]]:
    url = f"https://www.ianseo.net/TourList.php?Year={year}&countryid={country}"
    page = fetch_text(url)

    rows = re.findall(
        r"<tr[^>]*onclick=\"window\.open\('Details\.php\?toId=(\d+)'[^\"]*\"[^>]*>(.*?)</tr>",
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )

    tournaments: Dict[str, Dict[str, str]] = {}
    for to_id, row in rows:
        tds = re.findall(r"<td([^>]*)>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        by_class: Dict[str, str] = {}
        for attrs, inner in tds:
            cls = re.search(r'class="([^"]+)"', attrs, flags=re.IGNORECASE)
            if cls:
                by_class[cls.group(1)] = clean_text(inner)

        date_text = by_class.get("column7", "")
        end_date = parse_end_date(date_text, year)
        if not end_date:
            continue

        name = by_class.get("column3 mobile-noshow") or by_class.get(
            "column2 mobile-show-notresponsive results-lines-topspacing width-limiter",
            "",
        )
        organizer = by_class.get("column4 width-limiter", "")

        tournaments[to_id] = {
            "to_id": to_id,
            "year": str(year),
            "name": name,
            "organizer": organizer,
            "date_text": date_text,
            "end_date": end_date.isoformat(),
            "details_url": f"https://www.ianseo.net/Details.php?toId={to_id}",
        }

    return sorted(tournaments.values(), key=lambda x: x["end_date"])


def extract_ena_url(details_html: str, to_id: str) -> Optional[str]:
    m = re.search(r'href="(/TourData/\d+/' + re.escape(to_id) + r'/ENA\.php)"', details_html, flags=re.IGNORECASE)
    if not m:
        return None
    return "https://www.ianseo.net" + m.group(1)


def extract_ic_url(details_html: str, to_id: str) -> Optional[str]:
    m = re.search(r'href="(/TourData/\d+/' + re.escape(to_id) + r'/IC\.php)"', details_html, flags=re.IGNORECASE)
    if not m:
        return None
    return "https://www.ianseo.net" + m.group(1)


def extract_seynod_entries(ena_html: str, keywords: List[str]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", ena_html, flags=re.IGNORECASE | re.DOTALL)
    for row in rows:
        low = row.lower()
        if not any(k in low for k in keywords):
            continue

        cells = [clean_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)]
        if len(cells) < 3:
            continue
        entries.append(
            {
                "name": cells[0],
                "target": cells[1] if len(cells) > 1 else "",
                "club": cells[2] if len(cells) > 2 else "",
                "category": cells[3] if len(cells) > 3 else "",
                "session": cells[4] if len(cells) > 4 else "",
            }
        )
    return entries


def find_next_competition(today: dt.date, keywords: List[str], country: str) -> Dict[str, object]:
    candidate_years = [today.year, today.year + 1]
    candidates: List[Tuple[dt.date, Dict[str, str]]] = []

    for year in candidate_years:
        for tournament in list_tournaments(year, country):
            end_date = dt.date.fromisoformat(tournament["end_date"])
            if end_date > today:
                candidates.append((end_date, tournament))

    candidates.sort(key=lambda x: x[0])

    for _, tournament in candidates:
        details_html = fetch_text(tournament["details_url"])
        ena_url = extract_ena_url(details_html, tournament["to_id"])
        if not ena_url:
            continue

        ena_html = fetch_text(ena_url)
        entries = extract_seynod_entries(ena_html, keywords)
        if not entries:
            continue

        ic_url = extract_ic_url(details_html, tournament["to_id"])
        return {
            "found": True,
            "next_competition": {
                **tournament,
                "ena_url": ena_url,
                "ic_url": ic_url,
                "seynod_entries": entries,
            },
        }

    return {
        "found": False,
        "message": "Aucune competition future avec inscrits Seynod trouvee pour le moment.",
        "checked_candidates": len(candidates),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Find next IANSEO competition with Seynod entries")
    parser.add_argument("--output", default="data/next_competition.json")
    parser.add_argument("--keywords", default="seynod,0174246")
    parser.add_argument("--country", default="FRA")
    parser.add_argument("--today", default="")
    args = parser.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    keywords = [k.strip().lower() for k in args.keywords.split(",") if k.strip()]

    result = find_next_competition(today=today, keywords=keywords, country=args.country)
    payload = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "today": today.isoformat(),
        "country": args.country,
        "keywords": keywords,
        **result,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps({"output": args.output, "found": payload["found"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
