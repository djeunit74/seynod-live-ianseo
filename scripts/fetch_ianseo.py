#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from typing import List, Dict, Any


DEFAULT_URL = "https://www.ianseo.net/TourData/2026/27251/IC.php"
DEFAULT_KEYWORDS = "Seynod,0174246"


def strip_tags(value: str) -> str:
    text = re.sub(r"<br\s*/?>", " | ", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_html(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SeynodLiveBot/1.0; +https://github.com/)",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_place(page_html: str) -> str:
    m = re.search(
        r'<div class="results-header-center">\s*<div>(.*?)</div>\s*<div>(.*?)</div>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return ""
    second_line = strip_tags(m.group(2))
    city_match = re.search(r"\(([^)]+)\)", second_line)
    if city_match:
        return city_match.group(1).strip()
    return second_line.split(",")[0].strip()


def parse_competition_name(page_html: str) -> str:
    m = re.search(
        r'<div class="results-header-center">\s*<div>(.*?)</div>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return ""
    return strip_tags(m.group(1))


def parse_category_meta(category_title: str) -> Dict[str, Any]:
    title = strip_tags(category_title)
    category = title.split("[", 1)[0].strip()
    arrows = None
    arr_match = re.search(r"Après\s+(\d+)\s+flèches", title, flags=re.IGNORECASE)
    if arr_match:
        arrows = int(arr_match.group(1))
    finished = bool(arrows is not None and arrows >= 72)
    progress = (
        f"Terminé ({arrows} flèches)"
        if finished and arrows is not None
        else f"En cours ({arrows} flèches)"
        if arrows is not None
        else "En cours"
    )
    return {"category": category, "arrows": arrows, "finished": finished, "progress": progress}


def parse_table_rows(tbody_html: str, category_meta: Dict[str, Any], place: str) -> List[Dict[str, Any]]:
    rows = re.findall(r"(<tr[^>]*>.*?</tr>)", tbody_html, flags=re.IGNORECASE | re.DOTALL)
    archers = []
    pending = None

    for row in rows:
        class_match = re.search(r'class="([^"]*)"', row, flags=re.IGNORECASE | re.DOTALL)
        class_name = class_match.group(1) if class_match else ""
        class_lc = class_name.lower()

        if "compressed-group" in class_lc:
            cols_raw = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
            cols = [strip_tags(c) for c in cols_raw]
            if len(cols) < 6:
                pending = None
                continue

            score_text = cols[-3]
            score_match = re.search(r"\d+", score_text)
            score = int(score_match.group(0)) if score_match else 0
            score_label = (
                f"{score} (après {category_meta['arrows']} flèches)"
                if category_meta["arrows"] is not None
                else str(score)
            )

            pending = {
                "place": place,
                "name": cols[1],
                "club": cols[2],
                "position": cols[0],
                "score": score,
                "scoreLabel": score_label,
                "category": category_meta["category"],
                "progress": category_meta["progress"],
                "detail": "",
                "finished": category_meta["finished"],
            }
            archers.append(pending)
            continue

        if pending and "results-secondary-lines-bottomspacing" in row:
            detail_cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
            detail_text = strip_tags(detail_cells[-1] if detail_cells else row)
            detail_text = re.sub(r"^\s*&?\s*", "", detail_text).strip()
            pending["detail"] = detail_text

    return archers


def parse_ianseo(page_html: str, club_keywords: List[str], source_url: str) -> Dict[str, Any]:
    place = parse_place(page_html)
    competition_name = parse_competition_name(page_html)
    results = []

    blocks = re.findall(
        r"<thead>\s*<tr[^>]*>\s*<th[^>]*colspan=\"20\"[^>]*>(.*?)</th>.*?</thead>\s*<tbody>(.*?)</tbody>",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for category_title, tbody in blocks:
        if "Après" not in category_title:
            continue
        meta = parse_category_meta(category_title)
        rows = parse_table_rows(tbody, meta, place)
        for row in rows:
            club_lc = row["club"].lower()
            if any(k in club_lc for k in club_keywords):
                results.append(row)

    return {
        "competitionName": competition_name,
        "sourceUrl": source_url,
        "places": [place] if place else [],
        "archers": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch IANSEO live data and build data/live.json")
    parser.add_argument("--url", default=DEFAULT_URL, help="IANSEO IC.php URL")
    parser.add_argument("--output", default="data/live.json", help="Output JSON path")
    parser.add_argument(
        "--club-keywords",
        default=DEFAULT_KEYWORDS,
        help="Comma-separated club filters (case-insensitive), e.g. 'Seynod,0174246'",
    )
    args = parser.parse_args()

    club_keywords = [k.strip().lower() for k in args.club_keywords.split(",") if k.strip()]
    if not club_keywords:
        print("No club keywords provided.", file=sys.stderr)
        return 1

    page_html = fetch_html(args.url)
    data = parse_ianseo(page_html, club_keywords, args.url)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        json.dumps(
            {
                "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source": args.url,
                "club_keywords": club_keywords,
                "archers_count": len(data["archers"]),
                "places": data["places"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
