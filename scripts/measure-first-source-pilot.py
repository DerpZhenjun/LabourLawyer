"""Reproduce reviewed first-source stage counts without network or user data."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from first_source_measurement import aggregate, verify_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-index', type=Path)
    parser.add_argument('--evidence-root', type=Path)
    args = parser.parse_args()
    if bool(args.evidence_index) != bool(args.evidence_root):
        parser.error('evidence-index and evidence-root must be supplied together')
    data = json.loads(args.input.read_text(encoding='utf-8'))
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    result = aggregate(data['cohort'], data['records'], baseline['raw_sha256'],
                       completed_at=data['research_completed_at'])
    if args.evidence_index:
        result['evidence_entries_verified'] = verify_files(
            args.evidence_root, json.loads(args.evidence_index.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'regions': result['regions_attempted'], 'counts': result['counts'],
                      'qualified_blank_bindings': result['templates']['qualified_blank_bindings'],
                      'unique_originals': result['templates']['unique_originals']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
