#!/usr/bin/env bash
# Push a new GPU commit for each named variant even if its latest version is COMPLETE (for example
# after a harness or cell fix), and record it on the automation/state branch like a tick would.
#   kaggle/force_push.sh v2-level-memory v1-franzen-faithful
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q origin automation/state
git show origin/automation/state:state.json > kaggle/state.json
PYTHONPATH=. .venv/bin/python - "$@" <<'PY'
import sys; sys.path.insert(0, "kaggle")
from datetime import datetime, timezone
import daily
state, client, plan = daily.load_state(), daily.KaggleClient(), daily.load_plan()
for variant in sys.argv[1:]:
    rec = {"at": datetime.now(timezone.utc).isoformat(), "variant": variant, "version": None, "error": None,
           "note": "forced re-push (kaggle/force_push.sh)"}
    try:
        rec["version"] = client.push(variant); rec["kernel"] = daily.variant_kernel(plan["owner"], variant)
        print(f"pushed {variant} -> {rec['kernel']} v{rec['version']}")
    except Exception as exc:  # noqa: BLE001
        rec["error"] = str(exc)[-300:]; rec["transient"] = daily.is_transient_push_error(rec["error"])
        print(f"FAILED {variant}: {rec['error'][-160:]}")
    state.setdefault("pushes", []).append(rec)
daily.save_state(state)
PY
tmp=$(mktemp -d); git worktree add -q "$tmp" origin/automation/state; cp kaggle/state.json "$tmp/state.json"
(cd "$tmp" && git add state.json && if ! git diff --cached --quiet; then git -c user.name=arc3-bot -c user.email=arc3-bot@users.noreply.github.com commit -qm "state $(date -u +%FT%TZ) (forced re-push)" && git push -q origin HEAD:automation/state; fi)
git worktree remove --force "$tmp"
