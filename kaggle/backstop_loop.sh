#!/usr/bin/env bash
# Backstop ticks for every remaining day, in one process that outlives the Claude session that
# starts it: kaggle/local_tick.sh at 00:30:30 and again at 02:30:30 UTC each day, through LAST_DAY.
# Each tick submits only if the day's slot is still free, so a second tick is harmless and covers
# a first one that failed (rate limit, Mac asleep). The one-shot backstop_tick.sh died with its
# session on 2026-10-29; start this detached instead:
#   nohup caffeinate -i kaggle/backstop_loop.sh 2026-11-02 >/dev/null 2>&1 & disown
set -u
cd "$(dirname "$0")/.."
last=${1:-2026-11-02}
log=~/Library/Logs/arc3/local-tick.log
mkdir -p "$(dirname "$log")"
last_day=$(( $(TZ=UTC date -j -f "%Y-%m-%d %H:%M:%S" "$last 00:00:00" +%s) / 86400 ))
day=$(( $(date -u +%s) / 86400 ))
echo "=== $(date -u +%FT%TZ) backstop loop started (pid $$) through $last" >> "$log"
while [ "$day" -le "$last_day" ]; do
  for offset in 1830 9030; do
    target=$(( day * 86400 + offset ))
    [ "$target" -le "$(date -u +%s)" ] && continue
    echo "=== $(date -u +%FT%TZ) backstop tick armed for $(date -u -r $target +%FT%TZ)" >> "$log"
    while [ "$(date -u +%s)" -lt "$target" ]; do sleep 20; done
    kaggle/local_tick.sh >> "$log" 2>&1
  done
  day=$(( day + 1 ))
done
echo "=== $(date -u +%FT%TZ) backstop loop finished" >> "$log"
