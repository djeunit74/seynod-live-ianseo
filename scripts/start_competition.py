#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Any

from build_live_data import build_payload
from find_next_competition import find_next_competition


def parse_keywords(raw: str) -> List[str]:
    return [k.strip().lower() for k in (raw or "").split(",") if k.strip()]


def write_json(path: str, data: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="All-in-one start: find next competition and switch live source")
    parser.add_argument("--keywords", default="seynod,0174246")
    parser.add_argument("--country", default="FRA")
    parser.add_argument("--today", default="")
    parser.add_argument("--next-output", default="data/next_competition.json")
    parser.add_argument("--live-output", default="data/live.json")
    parser.add_argument("--sources-output", default="data/competition_sources.json")
    args = parser.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    keywords = parse_keywords(args.keywords)

    result = find_next_competition(today=today, keywords=keywords, country=args.country)
    next_payload = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "today": today.isoformat(),
        "country": args.country,
        "keywords": keywords,
        **result,
    }
    write_json(args.next_output, next_payload)

    output = {
        "found": bool(next_payload.get("found")),
        "source_switched": False,
        "ic_url": None,
    }

    if not next_payload.get("found"):
        output["status"] = "not_found"
        print(json.dumps(output, ensure_ascii=False))
        return 0

    next_comp = next_payload.get("next_competition") or {}
    ic_url = str(next_comp.get("ic_url") or "").strip()
    output["ic_url"] = ic_url or None

    if not ic_url:
        output["status"] = "found_without_ic"
        print(json.dumps(output, ensure_ascii=False))
        return 0

    sources_payload = {
        "updatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "keywords": keywords,
        "selectedCompetition": {
            "name": next_comp.get("name", ""),
            "details_url": next_comp.get("details_url", ""),
            "ic_url": ic_url,
        },
        "urls": [ic_url],
    }
    write_json(args.sources_output, sources_payload)

    live_payload = build_payload([ic_url], keywords)
    write_json(args.live_output, live_payload)

    output["source_switched"] = True
    output["status"] = "ok"
    output["competitions"] = len(live_payload.get("competitions", []))
    output["archers"] = len(live_payload.get("archers", []))
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
