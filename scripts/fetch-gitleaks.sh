#!/bin/sh
# Downloads the pinned gitleaks into .tools/ and checks its sha256 (Linux/WSL x64).
set -eu
ROOT=$(git rev-parse --show-toplevel); V=$(cat "$ROOT/.gitleaks-version")
SHA=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb  # gitleaks_8.30.1_linux_x64.tar.gz
mkdir -p "$ROOT/.tools"; cd "$ROOT/.tools"
if [ -x gitleaks ] && [ "$(./gitleaks version | tr -d v)" = "$V" ]; then echo "gitleaks $V ok"; exit 0; fi
curl -fsSL -o gl.tgz "https://github.com/gitleaks/gitleaks/releases/download/v$V/gitleaks_${V}_linux_x64.tar.gz"
echo "$SHA  gl.tgz" | sha256sum -c - ; tar xzf gl.tgz gitleaks; rm gl.tgz; ./gitleaks version
