#!/usr/bin/env bash
# Run kaggle/local_tick.sh once at the next UTC midnight plus OFFSET seconds (default 1830 = 00:30:30).
# The tick submits only if the day's slot is still free, so this is a backstop for whatever else
# submits at 00:01 UTC. Run it under `caffeinate -i` so the Mac does not sleep through it.
#   kaggle/backstop_tick.sh [OFFSET_SECONDS]
set -u
cd "$(dirname "$0")/.."
offset=${1:-1830}
target=$(( ( $(date -u +%s) / 86400 + 1 ) * 86400 + offset ))
log=~/Library/Logs/arc3/local-tick.log
mkdir -p "$(dirname "$log")"
echo "=== $(date -u +%FT%TZ) backstop tick armed for $(date -u -r $target +%FT%TZ)" >> "$log"
while [ "$(date -u +%s)" -lt "$target" ]; do sleep 20; done
out=$(kaggle/local_tick.sh 2>&1); rc=$?
echo "$out" >> "$log"
echo "$out" | grep -E '^- \*\*'
exit $rc
