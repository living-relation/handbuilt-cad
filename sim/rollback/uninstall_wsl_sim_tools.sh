#!/bin/bash
# Removes everything the Oct 9 2026 sim-tools install added to WSL Ubuntu.
# Run from Windows:  wsl -d Ubuntu -u root -- bash /home/daniel/projects/handbuilt-models/sim-tools/rollback/uninstall_wsl_sim_tools.sh
# Add --dry-run to only show what would happen.
RB=/home/daniel/projects/handbuilt-models/sim-tools/rollback
DRY=0; [ "$1" = "--dry-run" ] && DRY=1
run(){ echo "+ $*"; [ $DRY = 1 ] || "$@"; }
BEFORE=$(cut -f1 $RB/wsl-packages-before.txt)
PURGE=(); REAUTO=()
for p in $(cat $RB/wsl-manual-added.txt); do
  if echo "$BEFORE" | grep -qx "$p"; then REAUTO+=("$p"); else PURGE+=("$p"); fi
done
[ ${#REAUTO[@]} -gt 0 ] && echo "Keeping packages that were already installed before: ${REAUTO[*]}"
[ ${#PURGE[@]} -gt 0 ] && run env DEBIAN_FRONTEND=noninteractive apt-get purge -y "${PURGE[@]}"
run env DEBIAN_FRONTEND=noninteractive apt-get autoremove --purge -y
run rm -f /etc/apt/sources.list.d/openfoam.list /etc/apt/keyrings/openfoam.asc
run rm -rf /opt/elmer /opt/src /usr/local/bin/ElmerSolver /usr/local/bin/ElmerGrid
run rm -rf /home/daniel/simvenv /home/daniel/sim-runs
run apt-get update -qq
echo "Compare with $RB/wsl-packages-before.txt:"
comm -13 <(cut -f1 $RB/wsl-packages-before.txt | sort) <(dpkg-query -W -f='${Package}\n' | sort) | sed 's/^/  still extra: /'