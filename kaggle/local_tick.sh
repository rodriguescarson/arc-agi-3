#!/usr/bin/env bash
# One tick of the daily scheduler from this machine, with the same state handling as
# .github/workflows/daily-submit.yml: load state.json from the automation/state branch, tick,
# save it back. Fallback for when GitHub Actions cannot run (2026-10-16 onward: the account's
# Actions billing refused every job). Usage: kaggle/local_tick.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q origin automation/state
git show origin/automation/state:state.json > kaggle/state.json
set +e
PYTHONPATH=. .venv/bin/python kaggle/daily.py tick "$@"
rc=$?
set -e
if [[ " $* " != *" --dry-run "* ]]; then
  tmp=$(mktemp -d)
  git worktree add -q "$tmp" origin/automation/state
  cp kaggle/state.json "$tmp/state.json"
  (cd "$tmp" && git add state.json && if ! git diff --cached --quiet; then
     git -c user.name=arc3-bot -c user.email=arc3-bot@users.noreply.github.com commit -qm "state $(date -u +%FT%TZ) (local tick)" \
     && git push -q origin HEAD:automation/state; fi)
  git worktree remove --force "$tmp"
fi
exit $rc
