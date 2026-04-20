#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from typing import Dict, List

from find_next_competition import list_tournaments


def build_catalog(country: str, years: List[int]) -> Dict[str, object]:
    today = dt.date.today()
    tournaments: List[Dict[str, object]] = []
    for year in years:
        for t in list_tournaments(year, country):
            end_date = dt.date.fromisoformat(t["end_date"])
            if end_date <= today:
                continue
            tournaments.append(
                {
                    "to_id": t["to_id"],
                    "year": str(year),
                    "name": t.get("name", ""),
                    "organizer": t.get("organizer", ""),
                    "date_text": t.get("date_text", ""),
                    "end_date": t.get("end_date", ""),
                    "details_url": t.get("details_url", f"https://www.ianseo.net/Details.php?toId={t['to_id']}"),
                    "ena_url": f"https://www.ianseo.net/TourData/{year}/{t['to_id']}/ENA.php",
                    "ic_url": f"https://www.ianseo.net/TourData/{year}/{t['to_id']}/IC.php",
                }
            )
    tournaments.sort(key=lambda x: x.get("end_date", "9999-12-31"))
    return {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "country": country,
        "years": years,
        "count": len(tournaments),
        "tournaments": tournaments,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build upcoming IANSEO competition catalog")
    parser.add_argument("--country", default="FRA")
    parser.add_argument("--output", default="data/competition_catalog.json")
    parser.add_argument("--years", default="")
    args = parser.parse_args()

    now = dt.date.today()
    years = [int(y.strip()) for y in args.years.split(",") if y.strip()] if args.years else [now.year, now.year + 1]
    payload = build_catalog(args.country, years)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps({"output": args.output, "count": payload["count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
