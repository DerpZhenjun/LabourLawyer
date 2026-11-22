"""Start the privately frozen LabourLawyer compact pilot on localhost."""

from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def app_from_release(root, expected_manifest):
    if not re.fullmatch('[0-9a-f]{64}', expected_manifest):
        raise ValueError('请输入独立获知的归档清单 SHA-256。')
    manifest_path = root / 'DEPLOYMENT-MANIFEST.json'
    if manifest_path.is_symlink() or sha256(manifest_path.read_bytes()).hexdigest() != expected_manifest:
        raise ValueError('试点归档清单 SHA-256 不一致。')
    sys.path.insert(0, str(root / 'pilot'))
    from verify import verify

    verify(root)
    manifest = json.loads(manifest_path.read_bytes())
    if manifest['scope'] != 'PRIVATE_LABOURLAWYER_COMPACT_CANDIDATE':
        raise ValueError('该归档不属于本次私有试点。')

    sys.path.insert(0, str(root / 'backend'))
    from compact_catalogue_experiment import load
    from compact_locality_experiment import create_locality_app
    from deployment_app import attach_frontend
    from fastapi.responses import RedirectResponse

    proof, bindings, guides, areas = load(root / 'data/pilot', manifest['catalogue_inventory_sha256'])
    layout_hash = getattr(proof, 'derivative_sha256', None)
    app = create_locality_app(proof, bindings, guides, areas, layout_hash=layout_hash)
    attach_frontend(app, root / 'frontend/dist')

    def landing():
        return RedirectResponse('/pilot-scope.html', status_code=302)

    app.add_api_route('/', landing, methods=['GET', 'HEAD'])
    app.router.routes.insert(0, app.router.routes.pop())
    return app, guides, bindings


def offline_checks(app, guides, bindings):
    from fastapi.testclient import TestClient

    matched = {}
    for binding in bindings:
        matched[(binding['region_code'], binding['kind'])] = binding
    result = {'localities': 0, 'originals': 0, 'contracts': 0, 'generated_blank_fixtures': 0,
              'nonpilot_api_404': 0}
    base = '/api/regional-guides'
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        for guide in guides:
            locality = {key: guide[key] for key in ('province', 'city', 'district')}
            response = client.get(base + '/lookup', params=locality)
            assert response.status_code == 200 and response.json() == guide
            result['localities'] += 1
            source = dict(locality, source_id=guide['source_id'], version=guide['version'])
            for template in guide['templates']:
                kind, = template['document_types']
                binding = matched[(guide['region_code'], kind)]
                query = dict(source, kind=kind, template_id=template['id'])
                response = client.get(base + '/form-contract', params=dict(query, xlsx='true'))
                assert response.status_code == 200 and response.json()['contract_id'] == binding['contract_id']
                contract = response.json()
                result['contracts'] += 1
                path = base + '/templates/' + quote(template['id'], safe='')
                original = client.get(path, params=source)
                assert original.status_code == 200 and sha256(original.content).hexdigest() == template['sha256']
                assert (template.get('official_sha256') or template['sha256']) == binding['original_sha256']
                if template.get('official_sha256'):
                    assert original.headers['x-official-original-sha256'] == binding['original_sha256']
                    assert original.headers['x-document-origin'] == 'official-blank-metadata-sanitized-layout'
                result['originals'] += 1
                created = client.post(base + '/generate', json=dict(
                    query, mode='blank', data=contract['defaults'], contract_id=contract['contract_id']))
                assert created.status_code == 200 and created.content[:4] == b'PK\x03\x04'
                if template.get('official_sha256'):
                    assert created.headers['x-document-origin'] == 'official-blank-metadata-sanitized-filled'
                    assert created.headers['x-official-original-sha256'] == binding['original_sha256']
                    assert created.headers['x-template-sha256'] == template['sha256']
                result['generated_blank_fixtures'] += 1
        for path in ('/api/cases', '/api/ai', '/api/portal-reports', '/health'):
            assert client.get(path).status_code == 404
            result['nonpilot_api_404'] += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--port', type=int, default=8093)
    parser.add_argument('--self-test', action='store_true', help='Run a local smoke test without a listener')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('端口必须在 1024 到 65535 之间。')
    sys.dont_write_bytecode = True
    app, guides, bindings = app_from_release(ROOT, args.manifest_sha256)
    if args.self_test:
        print(json.dumps(offline_checks(app, guides, bindings), sort_keys=True), flush=True)
        return
    import uvicorn

    print(f'本机私有试点 http://127.0.0.1:{args.port}/pilot-scope.html', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=args.port, proxy_headers=False, access_log=False)


if __name__ == '__main__':
    main()
