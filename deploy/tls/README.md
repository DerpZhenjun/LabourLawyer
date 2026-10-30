# Rootless HTTPS proxy

This optional deployment layer terminates TLS for one application origin and forwards to an existing HTTP API or digital service. It never starts a model, changes Tailscale settings, installs OS trust, binds privileged ports, edits a firewall or takes over an existing listener. It runs in the foreground as the application user. The existing HTTP application keeps its own authentication and data storage.

## Certificate prerequisite

Provide a certificate chain and matching unencrypted private key for the exact DNS name or IP SAN being served. Keep the key under an application-owned private directory with mode0700, and the key itself mode0600. The preflight checks file location, regular-file ownership, symlinks, key permissions, certificate/key match, validity dates, remaining lifetime and exact SAN coverage. It does not certify that the issuer is publicly trusted. Wildcard-only certificates are not supported by this conservative preflight.

A Tailscale certificate is an option only when the node's own name is eligible, the node can reach its control plane, and the tailnet administrator has enabled HTTPS certificates. Tailscale documents that enabling this feature publishes machine/tailnet names to the public Certificate Transparency ledger. Do not change tailnet-wide settings as part of this application deployment. See [Tailscale HTTPS setup](https://tailscale.com/docs/how-to/set-up-https-certificates). File-based certificates require renewal; this tool rejects certificates with less than seven days remaining by default.

## Prepare and run

Install the fixed official Linux amd64 binary into the private application directory:

```sh
mkdir -m700 -p "$HOME/SJL/LabourLawyer/var/tls"
python3 deploy/tls/install_caddy.py --directory "$HOME/SJL/LabourLawyer/var/tls"
```

The installer pins Caddy2.11.7 and the SHA512 in the [official release checksum file](https://github.com/caddyserver/caddy/releases/download/v2.11.7/caddy_2.11.7_checksums.txt). It verifies cached archives and existing binary bytes too; mismatches stop without extraction or overwrite. No package manager or global service is invoked. See [official static binary installation](https://caddyserver.com/docs/install#static-binaries).

Place the issued certificate chain and key in that private directory through the normal deployment process. Use explicit values for the selected host and existing upstream, then create a fresh configuration file:

```sh
python3 deploy/tls/runtime.py \
  --private-root "$HOME/SJL/LabourLawyer/var/tls" \
  --cert "$HOME/SJL/LabourLawyer/var/tls/server.crt" \
  --key "$HOME/SJL/LabourLawyer/var/tls/server.key" \
  --hostname YOUR_CERTIFICATE_HOST \
  --listen 127.0.0.1 --port 8443 \
  --upstream http://YOUR_EXISTING_API_HOST:8088 \
  --output "$HOME/SJL/LabourLawyer/var/tls/reviewed-proxy.json" \
  --caddy "$HOME/SJL/LabourLawyer/var/tls/caddy-2.11.7"
```

Omitting `--run` only validates and writes configuration. Add `--run` to an invocation with a new output filename to perform the free-port check and run the validated proxy in the foreground. Existing configuration files are never overwritten. Stop only this foreground process with Ctrl+C; this tool never stops a process itself. For a durable deployment, arrange normal application-owned process supervision and certificate renewal separately.

The JSON disables Caddy's admin API, automatic certificate issuance/renewal, HTTP redirect listeners and HTTP/3 UDP listeners. Only the explicit host is forwarded; other Host values receive421. Caddy data/config directories remain under the private application directory. No access-log request bodies or credentials are configured. [Supplied TLS certificates](https://caddyserver.com/docs/caddyfile/directives/tls) use the default TLS settings. [Reverse proxy streaming](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming) retains Caddy's normal cancellation behavior and immediate forwarding for unknown-length responses; a negative flush interval is deliberately not used because it changes upstream cancellation semantics.

The default loopback listener is a local validation boundary. A certificate, successful local TLS test or private-network listener does not establish internet reachability, trusted public DNS, firewall access, production process supervision or a publicly trusted certificate. If the main app is served over HTTPS, its configured digital-human origin must also use HTTPS to avoid mixed content. The digital app assumes an origin-root deployment; use a separate approved HTTPS origin/port for it, rather than adding a path prefix to a frozen build.

## Isolated acceptance

Use a temporary test CA and short-lived SAN certificate created in a private runtime directory. Never commit private keys or install this test CA into Windows, Linux or browser trust stores. Passing `--minimum-days 0` is only for that explicitly short-lived test. The live checker accepts loopback origins only and supplies the CA to its own HTTPS client:

```sh
# Use a new private directory under the application's var/tls directory.
python3 scripts/create-tls-test-ca.py --directory /NEW_PRIVATE_TEST_DIRECTORY
# Start the proxy with these server.crt/server.key files, a new config output,
# --hostname 127.0.0.1 --minimum-days 0, and the normal explicit upstream.
python3 scripts/test-tls-proxy.py \
  --origin https://127.0.0.1:8443 \
  --ca /PRIVATE_TEST_DIRECTORY/ca.crt \
  --output /PRIVATE_TEST_DIRECTORY/result.json
LABOURLAWYER_TLS_TEST_CERT_DIR=/PRIVATE_TEST_DIRECTORY \
  python3 backend/tests/test_tls_deployment.py
```

The checker verifies HTTPS health, unauthenticated401s, public HTML/JavaScript, SPA refresh, preserved404s, unknown-Host rejection, rejection by default OS trust, unexpected SNI/hostname rejection, and refusal to take over the occupied port. It never logs in, changes a database or sends an AI prompt. Certificate test fixtures are generated privately and are skipped when not explicitly supplied; the ordinary validation/config tests need no model, browser or certificate key in the repository.
