"""Verify an explicitly trusted isolated TLS proxy; never sends credentials or model prompts."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPSHandler, ProxyHandler, Request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--ca', type=Path, required=True, help='Explicit test CA file; no trust-store install occurs')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    target = urlsplit(args.origin)
    if target.scheme != 'https' or target.hostname not in {'127.0.0.1', '::1'} or target.path not in {'', '/'} or target.query or target.fragment or target.username or target.password:
        parser.error('This acceptance helper only targets an explicit loopback HTTPS origin')
    origin = args.origin.rstrip('/')
    context = ssl.create_default_context(cafile=str(args.ca))
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
    checks = []
    def get(path, host=None, accept=None):
        headers = {}
        if host:
            headers['Host'] = host
        if accept:
            headers['Accept'] = accept
        request = Request(origin + path, headers=headers)
        try:
            with opener.open(request, timeout=15) as response:
                return response.status, response.read(), response.headers
        except HTTPError as response:
            return response.code, response.read(), response.headers
    code, data, _ = get('/health')
    assert code == 200 and json.loads(data)['service'] == 'api'
    checks.append({'name':'HTTPS health with explicit test CA and hostname validation','status':code,'passed':True})
    for route in ['/api/platform/cases', '/api/auth/me']:
        code, _, _ = get(route)
        assert code == 401, (route, code)
        checks.append({'name':'Anonymous protected route '+route,'status':code,'passed':True})
    code, html, _ = get('/')
    assert code == 200 and b'</html>' in html
    script = re.search(rb'<script[^>]+src="([^"]+)"', html)
    assert script
    path = script.group(1).decode()
    assert path.startswith('/assets/') and '..' not in path
    code, content, _ = get(path)
    assert code == 200 and content
    checks.append({'name':'HTTPS public HTML and application static JavaScript','status':code,'passed':True})
    code, html, _ = get('/province/zhejiang', accept='text/html')
    assert code == 200 and b'</html>' in html
    checks.append({'name':'HTTPS SPA refresh','status':code,'passed':True})
    for path in ['/api/nonexistent-tls-synthetic', '/assets/nonexistent-tls-synthetic.js']:
        code, _, _ = get(path)
        assert code == 404, (path, code)
    checks.append({'name':'Unknown API and missing static script preserve404','passed':True})
    code, _, _ = get('/health', 'wrong.invalid')
    assert code == 421, code
    checks.append({'name':'Unexpected Host rejected before upstream','status':code,'passed':True})
    untrusted = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()))
    try:
        untrusted.open(origin+'/health', timeout=10)
    except URLError as error:
        assert isinstance(error.reason, ssl.SSLCertVerificationError), type(error.reason)
    else:
        raise AssertionError('An untrusted test CA must not be accepted')
    checks.append({'name':'Default OS trust rejects isolated test certificate','passed':True})
    try:
        with socket.create_connection((target.hostname, target.port), timeout=10) as connection:
            context.wrap_socket(connection, server_hostname='wrong.invalid')
    except ssl.SSLError as error:
        # Caddy may reject unknown SNI before sending any certificate; otherwise
        # the client rejects the certificate's hostname. Both must fail closed.
        assert error.reason in {'TLSV1_ALERT_INTERNAL_ERROR', 'TLSV1_UNRECOGNIZED_NAME', 'CERTIFICATE_VERIFY_FAILED'}, error.reason
    else:
        raise AssertionError('Wrong TLS hostname must be rejected even with the test CA trusted')
    checks.append({'name':'Unexpected TLS SNI/hostname rejected with explicit CA','passed':True})
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('tls_runtime', root/'deploy/tls/runtime.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    try:
        runtime.check_port(target.hostname, target.port)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Occupied TLS port was not rejected')
    assert get('/health')[0] == 200
    checks.append({'name':'Occupied-port preflight refuses takeover and existing proxy stays healthy','passed':True})
    report = {'test_ca_only':True,'public_trust_deployed':False,'os_trust_modified':False,'origin':origin,'synthetic_model_calls':0,'checks':checks}
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed':len(checks),'failed':0,'public_trust_deployed':False,'os_trust_modified':False}))

if __name__ == '__main__':
    main()
