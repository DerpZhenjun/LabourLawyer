set -eu
umask 077
base="$HOME/SJL/LabourLawyer/digital"
mkdir -p "$base/runtime" "$base/releases" "$base/var"
cd "$base/runtime"
if [ ! -e node-v22.23.4-linux-x64 ]; then
  curl --fail --location --proto '=https' --tlsv1.2 --max-time 180 -o node-v22.23.4-linux-x64.tar.xz https://nodejs.org/dist/v22.23.4/node-v22.23.4-linux-x64.tar.xz
  printf '%s  %s\n' '1805bcd35e6815559bd2eb97db438d3fdb0eb3a5e6a977b7c1badca76337e9ce' 'node-v22.23.4-linux-x64.tar.xz' | sha256sum --check -
  tar -xf node-v22.23.4-linux-x64.tar.xz
fi
./node-v22.23.4-linux-x64/bin/node --version
