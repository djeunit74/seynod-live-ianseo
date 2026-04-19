#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import List, Dict, Any

from fetch_ianseo import fetch_html, parse_ianseo


def parse_urls(raw: str) -> List[str]:
    parts = re.split(r"[\n,;]+", raw or "")
    urls = [p.strip() for p in parts if p.strip()]
    return urls


def extract_competition_id(url: str) -> str:
    m = re.search(r"/TourData/\d+/(\d+)/IC\.php", url, flags=re.IGNORECASE)
    return m.group(1) if m else re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-")[:32]


def load_urls(urls_arg: str, sources_file: str) -> List[str]:
    urls = parse_urls(urls_arg)
    if urls:
        return urls

    source_path = Path(sources_file)
    if source_path.exists():
        with source_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        file_urls = data.get("urls", [])
        return [u.strip() for u in file_urls if isinstance(u, str) and u.strip()]

    return []


def build_payload(urls: List[str], club_keywords: List[str]) -> Dict[str, Any]:
    competitions: List[Dict[str, Any]] = []
    flat_archers: List[Dict[str, Any]] = []
    places = set()
    seen_competitions = set()

    for url in urls:
        page_html = fetch_html(url)
        parsed = parse_ianseo(page_html, club_keywords, url)
        comp_id = extract_competition_id(url)
        key = (comp_id, url)
        if key in seen_competitions:
            continue
        seen_competitions.add(key)
        place = parsed["places"][0] if parsed.get("places") else ""
        name = parsed.get("competitionName") or f"Competition {comp_id}"

        competition = {
            "id": comp_id,
            "name": name,
            "place": place,
            "sourceUrl": url,
            "archers": parsed.get("archers", []),
        }
        competitions.append(competition)

        if place:
            places.add(place)
        for archer in competition["archers"]:
            merged = dict(archer)
            merged["competitionId"] = comp_id
            merged["competitionName"] = name
            flat_archers.append(merged)

    source_url = competitions[0]["sourceUrl"] if competitions else ""

    return {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sourceUrl": source_url,
        "places": sorted(places),
        "archers": flat_archers,
        "competitions": competitions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/live.json from one or multiple IANSEO competitions")
    parser.add_argument("--urls", default="", help="IANSEO IC.php URLs separated by comma/newline/semicolon")
    parser.add_argument("--sources-file", default="data/competition_sources.json", help="Optional JSON file with {\"urls\": [...]}")
    parser.add_argument("--output", default="data/live.json")
    parser.add_argument("--club-keywords", default="Seynod,0174246")
    args = parser.parse_args()

    urls = load_urls(args.urls, args.sources_file)
    if not urls:
        raise SystemExit("No IANSEO URLs provided. Set --urls or create data/competition_sources.json.")

    club_keywords = [k.strip().lower() for k in args.club_keywords.split(",") if k.strip()]
    payload = build_payload(urls, club_keywords)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        json.dumps(
            {
                "output": args.output,
                "competitions": len(payload["competitions"]),
                "archers": len(payload["archers"]),
                "places": payload["places"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
