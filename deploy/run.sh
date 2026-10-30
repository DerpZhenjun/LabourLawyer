#!/usr/bin/env bash
set -euo pipefail
umask 077
if [[ "$(id -u)" == 0 ]]; then
  printf '%s\n' 'Run LabourLawyer as the application user, not root.' >&2
  exit 1
fi
release="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
app_home="${LABOURLAWYER_APP_HOME:-$HOME/SJL/LabourLawyer}"
python="$app_home/venv/bin/python"
if [[ ! -x "$python" ]]; then
  printf '%s\n' 'Install the isolated application venv before starting this release.' >&2
  exit 1
fi
export PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
"$python" "$release/deploy/verify.py"
export LABOURLAWYER_DEPLOY_DATA="$app_home/var"
export LABOURLAWYER_CORS_ORIGINS='http://192.168.110.81:8088,capacitor://localhost,http://localhost,https://localhost'
# Explicit LABOURLAWYER_DIGITAL_URL and LABOURLAWYER_COLLECTOR_CONFIG values are
# inherited from the operator. This launcher never guesses or starts either service.
cd -- "$release"
if [[ "${LABOURLAWYER_ENABLE_UBUNTU_AI:-0}" == 1 ]]; then
  export LABOURLAWYER_AI_TRANSPORT='ubuntu-local'
  export OLLAMA_API_BASE='http://127.0.0.1:11434'
  export LABOURLAWYER_UBUNTU_OLLAMA_ROOT="$HOME/SJL/Ollama"
  "$python" -c 'from llm_service.remote import resolve_remote; resolve_remote(); print("Existing Ubuntu Ollama process verified; no model started.")'
fi
exec "$python" -m uvicorn deployment_app:create_app --factory --app-dir "$release/backend" --host 192.168.110.81 --port 8088 --no-proxy-headers
