#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run_cmd(args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), text=True, capture_output=True)


def git_has_changes(repo_root: Path, path: str) -> bool:
    p = run_cmd(["git", "status", "--porcelain", "--", path], repo_root)
    return bool((p.stdout or "").strip())


def git_commit_and_push(repo_root: Path, path: str, message: str) -> None:
    run_cmd(["git", "add", path], repo_root)
    if not git_has_changes(repo_root, path):
        return
    run_cmd(["git", "commit", "-m", message], repo_root)
    push = run_cmd(["git", "push"], repo_root)
    if push.returncode != 0:
        raise RuntimeError(f"git push failed: {(push.stderr or push.stdout).strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update IANSEO data every N seconds and optionally push to GitHub."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30).",
    )
    parser.add_argument(
        "--url",
        default="https://www.ianseo.net/TourData/2026/27251/IC.php",
        help="IANSEO IC.php URL.",
    )
    parser.add_argument(
        "--club-keywords",
        default="Seynod,0174246",
        help="Club keywords for filtering (comma-separated).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory.",
    )
    parser.add_argument(
        "--output",
        default="data/live.json",
        help="Output JSON file path (relative to repo root).",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Only refresh local file, do not git commit/push.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    fetch_script = repo_root / "scripts" / "fetch_ianseo.py"
    output_path = args.output.replace("\\", "/")

    if not fetch_script.exists():
        print(f"Missing script: {fetch_script}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "mode": "local_updater",
                "interval_sec": args.interval,
                "url": args.url,
                "club_keywords": args.club_keywords,
                "output": output_path,
                "push_enabled": not args.no_push,
            },
            ensure_ascii=False,
        )
    )

    while True:
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        fetch = run_cmd(
            [
                sys.executable,
                str(fetch_script),
                "--url",
                args.url,
                "--club-keywords",
                args.club_keywords,
                "--output",
                output_path,
            ],
            repo_root,
        )
        if fetch.returncode != 0:
            print(f"[{started}] fetch error: {(fetch.stderr or fetch.stdout).strip()}")
        else:
            changed = git_has_changes(repo_root, output_path)
            if changed and not args.no_push:
                try:
                    git_commit_and_push(repo_root, output_path, "chore(data): live update (30s)")
                    print(f"[{started}] updated + pushed")
                except Exception as exc:
                    print(f"[{started}] push error: {exc}")
            elif changed:
                print(f"[{started}] updated locally (no push)")
            else:
                print(f"[{started}] no change")

        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
