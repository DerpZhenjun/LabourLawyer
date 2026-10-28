"""Reversible capability publication; never reclassifies a sample as a blank form."""
import argparse
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from regional_adapters import with_reference_capabilities
from regional_guides import RegionalStore


def run(args):
    database = Path(os.getenv('LABOURLAWYER_REGIONAL_DB', ROOT / 'backend/data/regional-guides.sqlite')).resolve()
    if not database.is_file():
        raise RuntimeError('地区资料库不存在；不会新建空库或操作用户案件库。')
    output = ROOT / args.report_dir / 'runs' / uuid.uuid4().hex[:12]
    output.mkdir(parents=True)
    store = RegionalStore(database)
    before = store.inventory()
    proposals, checks = [], []
    spec = importlib.util.spec_from_file_location('regional_capture_import', ROOT / 'scripts/import-regional-captures.py')
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    for guide in before:
        candidate = with_reference_capabilities(guide)
        if candidate == guide:
            continue
        changed = [t for t in candidate['templates'] if t.get('can_generate')]
        for template in changed:
            path = (ROOT / template['file']).resolve()
            if not path.is_relative_to((ROOT / 'templates/_docx/_regional').resolve()) or not path.is_file():
                raise RuntimeError('模板路径不在地区附件目录中。')
            retained_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if retained_sha != template['sha256']:
                raise RuntimeError('留存附件已变化，停止发布。')
            check = {'district': guide['district'], 'source_id': guide['source_id'],
                     'template_id': template['id'], 'source_url': guide['source_url'],
                     'download_endpoint': template['download_endpoint'], 'sha256': retained_sha,
                     'checked_at': datetime.now(timezone.utc).isoformat(), 'public_recheck': 'not_requested'}
            if args.recheck_public_files:
                try:
                    reply = json.loads(importer.public_get(template['download_endpoint'])[0])
                    if str(reply.get('code')) != '0':
                        raise RuntimeError('官方附件接口没有返回下载地址。')
                    body, _ = importer.public_get(reply['data'])
                    current_sha = hashlib.sha256(body).hexdigest()
                    if current_sha != retained_sha:
                        raise RuntimeError('本次官方附件与已检验文件不一致，必须重新适配。')
                    annex = output / f"{guide['district']}-{template['id']}.docx"
                    annex.write_bytes(body)
                    check.update(public_recheck='sha256_match', bytes=len(body), captured_file=str(annex.relative_to(ROOT)))
                    time.sleep(1)
                except Exception as exc:
                    check.update(public_recheck='failed', reason=str(exc))
                    (output / 'recheck-failure.json').write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding='utf8')
                    raise RuntimeError('公开附件复核失败，未发布任何地区能力；详见本次报告。') from exc
            checks.append(check)
        proposals.append(candidate)
    backup = None
    if args.apply and proposals:
        backup = output / 'regional-guides-before.sqlite'
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        (output / 'before.json').write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding='utf8')
        # All file/network preflight checks completed before the first DB mutation.
        for guide in proposals:
            store.put_guide(guide)
    after = store.inventory() if args.apply else proposals
    catalog = ROOT / 'reports/government-guide-localization/SOURCE-INVENTORY.json'
    if args.apply and database == (ROOT / 'backend/data/regional-guides.sqlite').resolve() and catalog.is_file():
        previous_catalog = catalog.read_text(encoding='utf8')
        (output / 'source-inventory-before.json').write_text(previous_catalog, encoding='utf8')
        updated_catalog = json.loads(previous_catalog)
        updated_catalog['regions'] = after
        catalog.write_text(json.dumps(updated_catalog, ensure_ascii=False, indent=2), encoding='utf8')
    report = {'at': datetime.now(timezone.utc).isoformat(), 'applied': args.apply,
              'database': str(database), 'backup': str(backup) if backup else None,
              'changed_districts': [g['district'] for g in proposals], 'checks': checks,
              'change_kind': 'platform_adapter_capability_not_official_rule_change',
              'official_collected_at_preserved': True,
              'model_calls': 0, 'local_ollama_started': False}
    (output / 'publication.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    (output / 'after.json').write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'report': str(output / 'publication.json'), 'applied': args.apply,
                      'changed_districts': report['changed_districts']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Explicitly publish to the isolated regional database only')
    parser.add_argument('--recheck-public-files', action='store_true')
    parser.add_argument('--report-dir', default='reports/regional-expansion-20261023')
    run(parser.parse_args())
