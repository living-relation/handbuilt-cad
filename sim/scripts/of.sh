#!/bin/bash
set -x
export DEBIAN_FRONTEND=noninteractive
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || pgrep -x apt-get >/dev/null; do sleep 5; done
mkdir -p /etc/apt/keyrings
curl -fsSL https://dl.openfoam.org/gpg.key -o /etc/apt/keyrings/openfoam.asc
echo "deb [signed-by=/etc/apt/keyrings/openfoam.asc] https://dl.openfoam.org/ubuntu resolute main" > /etc/apt/sources.list.d/openfoam.list
apt-get update -qq
PKG=$(apt-cache search --names-only '^openfoam[0-9]+$' | awk '{print $1}' | sort -V | tail -1)
echo "OPENFOAM_PKG=$PKG"
apt-get install -y $PKG
echo EXIT=$?