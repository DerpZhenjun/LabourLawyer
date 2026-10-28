"""Import the retained own Chengdu official directory, never guide capabilities."""
import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_directory import DirectoryStore, sichuan_city_areas

SOURCE = ROOT / 'reports/chengdu-district-expansion-20261023/official-region-tree.json'
DATABASE = ROOT / 'backend/data/regional-directory.sqlite'
OUT = ROOT / 'reports/nationwide-localization-20261028/directory'


def import_directory(source, database, output, apply=False):
    raw = Path(source).read_bytes()
    capture = json.loads(raw)
    rows = sichuan_city_areas(capture)  # Validate the entire response before any write.
    result = {'at': datetime.now(timezone.utc).isoformat(), 'applied': apply,
              'source_file': str(source), 'source_file_sha256': hashlib.sha256(raw).hexdigest(),
              'source_url': capture['source_url'], 'source_collected_at': capture['collected_at'],
              'city': rows[0]['city'], 'own_district_count': sum(r['level'] == 4 for r in rows),
              'directory_is_not_guide_coverage': True, 'grants_generation': False}
    if not apply:
        return result
    folder = Path(output) / ('import-' + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True, exist_ok=False)
    if Path(database).exists():
        with sqlite3.connect(database) as db, sqlite3.connect(folder / 'before.sqlite') as backup:
            db.backup(backup)
    store = DirectoryStore(database)
    for row in rows:
        row['capture_file'] = str(source)
        row['capture_sha256'] = result['source_file_sha256']
        store.put_area(row)
    result['selected_targets'] = store.areas('sichuan', rows[0]['city'])
    result['backup'] = str(folder / 'before.sqlite')
    (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    result['result_file'] = str(folder / 'result.json')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = import_directory(SOURCE, DATABASE, OUT, args.apply)
    print(json.dumps({k: v for k, v in result.items() if k != 'selected_targets'}, ensure_ascii=False))
