#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from typing import Dict, List
from zoneinfo import ZoneInfo
from pathlib import Path

from find_next_competition import (
    list_tournaments,
    fetch_text,
    extract_ena_url,
    extract_ic_url,
    extract_club_entries,
)


def build_catalog(country: str, years: List[int], include_entries: bool = True, previous=None) -> Dict[str, object]:
    today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    tournaments: List[Dict[str, object]] = []
    errors = []
    old = {str(t["to_id"]): t for t in (previous or {}).get("tournaments", [])} if (previous or {}).get("country") == country else {}
    for year in years:
        try:
            listed = list_tournaments(year, country)
        except Exception as exc:
            errors.append({"year": year, "message": str(exc)})
            for t in old.values():
                if str(t.get("year")) == str(year) and t.get("end_date", "") >= today.isoformat():
                    tournaments.append({**t, "entries_status": "error", "stale": True, "error": str(exc)})
            continue
        for t in listed:
            end_date = dt.date.fromisoformat(t["end_date"])
            if end_date < today:
                continue
            details_url = t.get("details_url", f"https://www.ianseo.net/Details.php?toId={t['to_id']}")
            item = {
                "to_id": t["to_id"],
                "country": country,
                "entries_status": "not_checked",
                "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "year": str(year),
                "name": t.get("name", ""),
                "organizer": t.get("organizer", ""),
                "date_text": t.get("date_text", ""),
                "end_date": t.get("end_date", ""),
                "details_url": details_url,
                "ena_url": f"https://www.ianseo.net/TourData/{year}/{t['to_id']}/ENA.php",
                "ic_url": f"https://www.ianseo.net/TourData/{year}/{t['to_id']}/IC.php",
                "entries_count": 0,
                "entries": [],
            }

            if include_entries:
                try:
                    details_html = fetch_text(details_url)
                    ena_url = extract_ena_url(details_html, t["to_id"]) or item["ena_url"]
                    ic_url = extract_ic_url(details_html, t["to_id"]) or item["ic_url"]
                    ena_html = fetch_text(ena_url)
                    entries = extract_club_entries(ena_html, [])
                    item["ena_url"] = ena_url
                    item["ic_url"] = ic_url
                    item["entries_count"] = len(entries)
                    item["entries_status"] = "published" if entries else "not_published"
                    # Keep payload bounded while preserving all useful fields.
                    item["entries"] = [
                        {
                            "name": e.get("name", ""),
                            "club": e.get("club", ""),
                            "category": e.get("category", ""),
                            "session": e.get("session", ""),
                            "target": e.get("target", ""),
                            "depart": e.get("depart", ""),
                            "time": e.get("time", ""),
                        }
                        for e in entries
                    ]
                except Exception as exc:
                    item["entries_status"] = "error"
                    item["error"] = str(exc)
                    if str(t["to_id"]) in old:
                        item["entries"] = old[str(t["to_id"])].get("entries", [])
                        item["entries_count"] = len(item["entries"])
                        item["stale"] = True
                    errors.append({"to_id": t["to_id"], "message": str(exc)})

            tournaments.append(item)
    tournaments.sort(key=lambda x: x.get("end_date", "9999-12-31"))
    return {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "country": country,
        "years": years,
        "count": len(tournaments),
        "errors": errors,
        "coverage_status": "partial" if errors else "published_entries_only",
        "entries_tournaments": sum(bool(t["entries"]) for t in tournaments),
        "tournaments": tournaments,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build upcoming IANSEO competition catalog")
    parser.add_argument("--country", default="FRA")
    parser.add_argument("--output", default="data/competition_catalog.json")
    parser.add_argument("--years", default="")
    parser.add_argument("--without-entries", action="store_true")
    args = parser.parse_args()

    now = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    years = [int(y.strip()) for y in args.years.split(",") if y.strip()] if args.years else [now.year, now.year + 1]
    previous = json.loads(Path(args.output).read_text(encoding="utf-8")) if Path(args.output).exists() else None
    payload = build_catalog(args.country, years, include_entries=not args.without_entries, previous=previous)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps({"output": args.output, "count": payload["count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
