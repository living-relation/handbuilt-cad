#!/bin/bash
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"; export REPO
RB=$REPO/sim-tools/rollback
cp $RB/wsl-packages-before.txt $RB/wsl-packages-before.BROKEN.txt
grep -h ' install ' /var/log/dpkg.log | awk '$1=="2026-10-09" && $2>="16:19:00" {print $4}' | sed 's/:.*//' | sort -u > /tmp/added_today.txt
echo "installed today since 16:19: $(wc -l < /tmp/added_today.txt)"
grep -h ' upgrade ' /var/log/dpkg.log | awk '$1=="2026-10-09" && $2>="16:19:00"' | head -3
dpkg-query -W -f='${Package}\t${Version}\n' | sort > /tmp/now.txt
awk 'NR==FNR{a[$1];next} !($1 in a)' /tmp/added_today.txt /tmp/now.txt > $RB/wsl-packages-before.txt
cp /tmp/added_today.txt $RB/wsl-packages-added.txt
echo "before: $(wc -l < $RB/wsl-packages-before.txt)  (original count was 544 lines incl. header-less dpkg -W)"
for p in ca-certificates git make python3-pip curl; do grep -qP "^$p\t" $RB/wsl-packages-before.txt && echo "$p was already installed" || echo "$p NEW"; done