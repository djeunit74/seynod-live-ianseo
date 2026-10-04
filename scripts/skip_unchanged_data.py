"""Avoid a Pages rebuild when only collection timestamps changed.

Leave the latest successful snapshot in Git. Live proxy freshness is independent
of these background discovery snapshots.
"""
import json
import subprocess
from pathlib import Path

TIMES = {'generatedAtUtc', 'generated_at_utc', 'checked_at_utc', 'fetchedAtUtc', 'sourceFetchedAtUtc'}
def semantic(value):
    if isinstance(value, dict):
        return {k: semantic(v) for k, v in value.items() if k not in TIMES}
    if isinstance(value, list):
        return [semantic(v) for v in value]
    return value

if __name__ == '__main__':
    for path in Path('data').glob('*.json'):
        result = subprocess.run(['git', 'show', f'HEAD:{path.as_posix()}'], capture_output=True, text=True)
        if result.returncode:
            continue
        old = json.loads(result.stdout)
        new = json.loads(path.read_text(encoding='utf-8'))
        if semantic(old) == semantic(new):
            path.write_text(result.stdout, encoding='utf-8')
