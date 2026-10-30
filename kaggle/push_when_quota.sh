#!/usr/bin/env bash
# Push GPU commits for the named variants as soon as Kaggle's weekly GPU quota allows, retrying
# every RETRY seconds (default 1800) until each has pushed or DEADLINE (UTC, default
# 2026-11-01T18:00:00Z) passes, then record each pushed version on the automation/state branch the
# way force_push.sh does. Every refusal is retried, not just quota and session-count ones: on
# 2026-10-30 an empty Kaggle reply ("Expecting value: line 1 column 1") was taken as permanent and
# dropped a trial, and a push that can never succeed only costs one API call per RETRY seconds.
# Start it detached so it outlives the Claude session:
#   nohup python3 -c "import os,subprocess; os.setsid(); subprocess.run(['kaggle/push_when_quota.sh','v11-stall-rule','v11-stall-medium'])" >/dev/null 2>&1 &
set -u
cd "$(dirname "$0")/.."
log=~/Library/Logs/arc3/push-when-quota.log
mkdir -p "$(dirname "$log")"
retry=${RETRY:-1800}
deadline=$(TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%SZ" "${DEADLINE:-2026-11-01T18:00:00Z}" +%s)
pending=("$@")
echo "=== $(date -u +%FT%TZ) push-when-quota started (pid $$) for: ${pending[*]}" >> "$log"
while [ ${#pending[@]} -gt 0 ] && [ "$(date -u +%s)" -lt "$deadline" ]; do
  still=()
  for v in "${pending[@]}"; do
    out=$(PYTHONPATH=. .venv/bin/python kaggle/build_notebook.py "kaggle/variants/$v.json" --push 2>&1 | grep -v outdated)
    echo "$(date -u +%FT%TZ) $v: $(echo "$out" | tail -1)" >> "$log"
    ver=$(echo "$out" | sed -n 's/^version \([0-9][0-9]*\)$/\1/p' | tail -1)
    if [ -n "$ver" ]; then
      git fetch -q origin automation/state && git show origin/automation/state:state.json > kaggle/state.json
      PYTHONPATH=. .venv/bin/python - "$v" "$ver" <<'PY'
import sys; sys.path.insert(0, "kaggle")
from datetime import datetime, timezone
import daily
state, plan = daily.load_state(), daily.load_plan()
v, ver = sys.argv[1], int(sys.argv[2])
state.setdefault("pushes", []).append({"at": datetime.now(timezone.utc).isoformat(), "variant": v, "version": ver,
    "kernel": daily.variant_kernel(plan["owner"], v), "error": None, "note": "push_when_quota.sh"})
daily.save_state(state)
PY
      tmp=$(mktemp -d); git worktree add -q "$tmp" origin/automation/state; cp kaggle/state.json "$tmp/state.json"
      (cd "$tmp" && git add state.json && if ! git diff --cached --quiet; then git -c user.name=arc3-bot -c user.email=arc3-bot@users.noreply.github.com commit -qm "state $(date -u +%FT%TZ) (push_when_quota $v v$ver)" && git push -q origin HEAD:automation/state; fi)
      git worktree remove --force "$tmp"; git checkout -q -- kaggle/state.json 2>/dev/null
      echo "=== $(date -u +%FT%TZ) pushed $v v$ver and recorded it" >> "$log"
    else
      still+=("$v")
    fi
  done
  pending=(${still[@]+"${still[@]}"})
  [ ${#pending[@]} -gt 0 ] && sleep "$retry"
done
echo "=== $(date -u +%FT%TZ) push-when-quota finished; still pending: ${pending[*]-none}" >> "$log"
