# Ubuntu digital assistant

Run this service separately from the document API. It uses the existing API for all model requests; it does not install, start or expose Ollama. Conversation history stays in the open page's memory. HTTP LAN access is for trusted local acceptance; provide TLS and normal process supervision before public hosting. Browser speech recognition may require a secure context. Browser read-aloud is optional and is not voice cloning.

The supported Next.js 15 maintenance release is pinned to 15.5.28, including the [October 2026 security patches](https://nextjs.org/blog/nextjs-security-update-october-14-2026). PostCSS is pinned to 8.5.23 for subsequent upstream fixes. The lockfile pins all dependencies. The portable Node installer uses the official 22.23.4 Linux x64 binary and its [published SHA256](https://nodejs.org/download/release/v22.23.4/SHASUMS256.txt); it only writes under the application's `digital/runtime` directory. No system package or shared service is changed.

Create a fresh digital source package from the checkout:

```sh
python3 ChatVRM/deploy/prepare.py --output /path/to/new-digital-source.tar.gz
```

The archive contains tracked digital source/public assets, an explicit deployment-file list and the generated shared API contract. It excludes installs, build output, environment files and private application data. The manifest records the base commit and every included file hash; modified checkout bytes are included and must be reviewed before release. Identical input bytes and base commit produce identical package bytes.

On the target Ubuntu user account, transfer the package and verify its printed SHA256. Extract into a new directory under `~/SJL/LabourLawyer/digital/releases/` (never overwrite a running release), then run:

```sh
bash ChatVRM/deploy/install-node.sh
export PATH="$HOME/SJL/LabourLawyer/digital/runtime/node-v22.23.4-linux-x64/bin:$PATH"
export NEXT_TELEMETRY_DISABLED=1
cd ChatVRM
npm ci --no-fund
npm audit --audit-level=low
npm run build
python3 deploy/run.py --node "$HOME/SJL/LabourLawyer/digital/runtime/node-v22.23.4-linux-x64/bin/node" --host YOUR_LAN_IP --port 8089 --api-base http://YOUR_LAN_IP:8088
```

The runner requires an existing production build and a free unprivileged port. It never builds during start and never kills a process. Keep it in the foreground for manual operation, or capture stdout/stderr under the application's private `digital/var` directory when using an already authorized user-level supervisor. No systemd, firewall, proxy or global Node configuration is installed.

Configure the main web client's digital-service URL to the selected origin. `/api/health/` is a read-only cross-origin connectivity check; `/api/chat/` remains same-origin JSON POST and streams from the configured API. The iframe must use the updated memory-only page. Check image-ready state separately from backend-ready state, then verify 375/768/1440 widths and a synthetic answer. Do not copy actual case data into acceptance artifacts.
