#!/usr/bin/env python3
import argparse
import datetime as dt
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset data/live.json for a new competition cycle")
    parser.add_argument("--output", default="data/live.json")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--place", default="")
    args = parser.parse_args()

    data = {
        "generatedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sourceUrl": args.source_url,
        "places": [args.place] if args.place else [],
        "archers": [],
        "competitions": [],
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("reset_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
