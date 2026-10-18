"""The daily scheduler, driven by a fake Kaggle: pre-start tests, the variant order, slot
accounting, one-day-ahead pushes, best-variant repeats after the order, and failure surfacing."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle"))

import daily  # noqa: E402

PLAN = {
    "competition": "comp", "owner": "me", "submission_file": "submission.parquet",
    "start_utc": "2026-10-17T00:05:00Z", "freeze_utc": "2026-10-31T00:00:00Z", "end_utc": "2026-11-02T22:30:00Z",
    "order": ["v1-franzen-faithful", "v3-swift", "v2-level-memory", "v4-effort-medium"],
    "push_retry_hours": 20,
    "pre_start_tests": [{"label": "cpu-test", "kernel": "me/arc3-duck-v3-cpucheck", "version": 1, "not_before": "2026-10-13T00:05:00Z"}],
}


def T(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


class Fake:
    def __init__(self):
        self.subs: list[daily.Submission] = []
        self.status: dict[str, str] = {}
        self.versions: dict[str, int] = {}
        self.pushes: list[str] = []
        self.push_error: str | None = None
        self.submit_error: str | None = None
        self.now = T("2026-10-17T00:20:00")
        self.served: dict[str, str] = {}
        self.smoke: dict[str, int | None] = {}      # kernel -> actions played by its smoke run

    def smoke_actions(self, kernel, version):
        return self.smoke.get(kernel, 50)

    def submissions(self, competition):
        return list(self.subs)

    def kernel_status(self, kernel):
        return self.status.get(kernel, "COMPLETE")

    def push(self, variant):
        if self.push_error:
            raise RuntimeError(self.push_error)
        self.pushes.append(variant)
        kernel = daily.variant_kernel("me", variant)
        self.versions[kernel] = self.versions.get(kernel, 0) + 1
        self.status[kernel] = "QUEUED"
        return self.versions[kernel]

    def served_model(self, kernel, version):
        return self.served.get(kernel, "swift")

    def submit(self, competition, kernel, version, file_name, message):
        if self.submit_error:
            raise RuntimeError(self.submit_error)
        self.subs.append(daily.Submission(self.now, message, "PENDING", None))
        return "ok"


def kinds(out):
    return [a.kind for a in out.actions]


def test_pre_start_test_submission_waits_then_fires_once():
    fake, state = Fake(), {}
    out = daily.tick(PLAN, state, fake, T("2026-10-12T10:00:00"))
    assert kinds(out) == ["note", "note", "note"] and not fake.subs
    fake.now = T("2026-10-13T00:20:00")
    out = daily.tick(PLAN, state, fake, fake.now)
    assert "submit" in kinds(out) and fake.subs[-1].description == "arc3-auto test=cpu-test kernel=me/arc3-duck-v3-cpucheck version=1"
    out = daily.tick(PLAN, state, fake, T("2026-10-13T06:20:00"))
    assert "submit" not in kinds(out) and len(fake.subs) == 1
    out = daily.tick(PLAN, state, fake, T("2026-10-14T06:20:00"))
    assert "submit" not in kinds(out) and len(fake.subs) == 1        # already submitted, never repeats
    assert not fake.pushes                                           # no GPU push before start


def test_slot_used_by_someone_else_blocks_the_test():
    fake, state = Fake(), {}
    fake.subs.append(daily.Submission(T("2026-10-13T04:25:00"), "model-based explorer v7", "COMPLETE", 0.15))
    out = daily.tick(PLAN, state, fake, T("2026-10-13T06:00:00"))
    assert "submit" not in kinds(out) and any("free slot" in a.text for a in out.actions)


def test_run_phase_pushes_two_then_submits_and_refills():
    fake, state = Fake(), {}
    out = daily.tick(PLAN, state, fake, T("2026-10-17T00:20:00"))
    assert fake.pushes == ["v1-franzen-faithful", "v3-swift"] and "submit" not in kinds(out)   # two in flight
    out = daily.tick(PLAN, state, fake, T("2026-10-17T02:20:00"))     # both queued: no third push
    assert fake.pushes == ["v1-franzen-faithful", "v3-swift"]
    fake.status["me/arc3-duck-v1-franzen-faithful"] = "COMPLETE"
    fake.now = T("2026-10-17T04:20:00")
    out = daily.tick(PLAN, state, fake, fake.now)
    assert fake.subs[-1].description.startswith("arc3-auto variant=v1-franzen-faithful kernel=me/arc3-duck-v1-franzen-faithful version=1")
    assert fake.pushes == ["v1-franzen-faithful", "v3-swift", "v2-level-memory"]   # slot refilled to two in flight
    out = daily.tick(PLAN, state, fake, T("2026-10-17T06:20:00"))     # slot used; nothing more today
    assert "submit" not in kinds(out) and len(fake.subs) == 1 and len(fake.pushes) == 3


def test_errored_version_is_skipped_and_the_day_is_not_wasted():
    fake, state = Fake(), {}
    for variant, status in (("v1-franzen-faithful", "ERROR"), ("v3-swift", "COMPLETE")):
        kernel = daily.variant_kernel("me", variant)
        state.setdefault("pushes", []).append({"at": "2026-10-15T20:00:00+00:00", "variant": variant, "version": 1, "kernel": kernel})
        fake.status[kernel] = status
    fake.now = T("2026-10-17T00:20:00")
    out = daily.tick(PLAN, state, fake, fake.now)
    assert fake.subs[-1].parsed["variant"] == "v3-swift"                 # first candidate with a COMPLETE version
    assert any("not submittable" in a.text for a in out.actions)
    assert fake.pushes[0] == "v1-franzen-faithful"                       # and the errored one is re-pushed


def test_order_then_best_repeats_without_new_pushes():
    fake, state = Fake(), {}
    scores = {"v1-franzen-faithful": 24.0, "v3-swift": 29.5, "v2-level-memory": 26.0, "v4-effort-medium": 20.0}
    day = T("2026-10-17T00:20:00")
    for i, variant in enumerate(PLAN["order"]):
        kernel = daily.variant_kernel("me", variant)
        if not daily.latest_push(state, variant):                    # day 1 has nothing pushed yet
            state.setdefault("pushes", []).append({"at": (day - timedelta(days=1)).isoformat(), "variant": variant, "version": 1, "kernel": kernel})
        fake.status[kernel] = "COMPLETE"                             # the queued commit finished overnight
        fake.now = day + timedelta(days=i)
        daily.tick(PLAN, state, fake, fake.now)
        fake.subs[-1].status, fake.subs[-1].public_score = "COMPLETE", scores[variant]
    assert [s.parsed["variant"] for s in fake.subs] == PLAN["order"]
    assert fake.pushes == PLAN["order"][1:]                          # each day pre-pushed the next variant
    pushes_before = len(fake.pushes)
    fake.now = day + timedelta(days=4)
    daily.tick(PLAN, state, fake, fake.now)
    assert fake.subs[-1].parsed["variant"] == "v3-swift"             # best public score repeats
    assert len(fake.pushes) == pushes_before                         # completed versions are reused
    fake.now = T("2026-10-31T01:00:00")                              # after the freeze: still the best
    daily.tick(PLAN, state, fake, fake.now)
    assert fake.subs[-1].parsed["variant"] == "v3-swift"


def test_push_failure_after_start_is_a_failure_and_pauses_all_pushes():
    fake, state = Fake(), {}
    fake.push_error = "Maximum weekly GPU quota of 30.00 hours reached"
    out = daily.tick(PLAN, state, fake, T("2026-10-17T00:20:00"))
    assert out.failed and [a.kind for a in out.actions].count("failure") == 1     # one failed push, not four
    out = daily.tick(PLAN, state, fake, T("2026-10-17T02:20:00"))
    assert not out.failed and any("pushes paused" in a.text for a in out.actions)   # no hammering
    out = daily.tick(PLAN, state, fake, T("2026-10-18T00:20:00"))
    assert out.failed                                                                # retried next day


def test_errored_submission_does_not_count_and_variant_is_retried():
    fake, state = Fake(), {}
    kernel = daily.variant_kernel("me", "v1-franzen-faithful")
    state["pushes"] = [{"at": "2026-10-16T20:00:00+00:00", "variant": "v1-franzen-faithful", "version": 2, "kernel": kernel}]
    fake.subs.append(daily.Submission(T("2026-10-17T00:30:00"), f"arc3-auto variant=v1-franzen-faithful kernel={kernel} version=2 rev=x", "ERROR", None))
    fake.now = T("2026-10-17T02:20:00")
    out = daily.tick(PLAN, state, fake, fake.now)
    assert "submit" in kinds(out) and fake.subs[-1].parsed["variant"] == "v1-franzen-faithful"


def test_dry_run_changes_nothing():
    fake, state = Fake(), {}
    out = daily.tick(PLAN, state, fake, T("2026-10-17T00:20:00"), dry_run=True)
    assert any(a.kind == "push" and "dry-run" in a.text for a in out.actions)
    assert not fake.pushes and state.get("pushes", []) == []


def test_real_plan_and_variants_resolve():
    plan = daily.load_plan()
    for v in plan["order"]:
        assert daily.variant_kernel(plan["owner"], v).startswith(plan["owner"] + "/")
    assert plan["pre_start_tests"][0]["kernel"].split("/")[1] == json.loads((ROOT / "kaggle/variants/v3-cpucheck.json").read_text())["kernel_slug"]


def _seed_versions(state, fake, variants, status="COMPLETE"):
    for variant in variants:
        kernel = daily.variant_kernel("me", variant)
        state.setdefault("pushes", []).append({"at": "2026-10-15T20:00:00+00:00", "variant": variant, "version": 1, "kernel": kernel})
        fake.status[kernel] = status


def test_two_draws_per_variant_then_best_mean():
    plan = {**PLAN, "order": ["v6-swift-level-memory", "v2-level-memory"], "draws_per_variant": 2, "pre_start_tests": []}
    fake, state = Fake(), {}
    _seed_versions(state, fake, plan["order"])
    scores = iter([30.0, 22.0, 27.0, 26.0, 0.0])          # v6: 30, 22 (mean 26); v2: 27, 26 (mean 26.5)
    for day in range(5):
        fake.now = T("2026-10-17T00:20:00") + timedelta(days=day)
        daily.tick(plan, state, fake, fake.now)
        fake.subs[-1].status, fake.subs[-1].public_score = "COMPLETE", next(scores)
    picked = [s.parsed["variant"] for s in fake.subs]
    assert picked[:4] == ["v6-swift-level-memory"] * 2 + ["v2-level-memory"] * 2
    assert picked[4] == "v2-level-memory"                 # best MEAN (26.5), not the single best draw (30)


def test_swap_moves_the_next_mechanism_onto_the_better_base():
    plan = {**PLAN, "order": ["v6-swift-level-memory", "v2-level-memory", "v7-drain-memory"], "draws_per_variant": 2,
            "swaps": [{"better": "v2-level-memory", "than": "v6-swift-level-memory", "margin": 2.0, "min_draws": 2,
                       "replace": {"v7-drain-memory": "v7i-drain-memory"}}]}
    def subs(v6, v2):
        out = []
        for variant, values in (("v6-swift-level-memory", v6), ("v2-level-memory", v2)):
            for x in values:
                out.append(daily.Submission(T("2026-10-18T00:00:00"), f"arc3-auto variant={variant} kernel=k version=1", "COMPLETE", x))
        return out
    assert daily.effective_order(plan, subs([24, 24], [28, 27]))[-1] == "v7i-drain-memory"   # Intel ahead by 3.5
    assert daily.effective_order(plan, subs([24, 25], [26, 25]))[-1] == "v7-drain-memory"    # within the 2-point margin
    assert daily.effective_order(plan, subs([24], [30]))[-1] == "v7-drain-memory"            # not enough draws yet


def test_fallback_draw_is_labelled_submitted_and_alerts():
    plan = {**PLAN, "order": ["v6-swift-level-memory"], "pre_start_tests": []}
    fake, state = Fake(), {}
    _seed_versions(state, fake, plan["order"])
    fake.served[daily.variant_kernel("me", "v6-swift-level-memory")] = "intel"
    out = daily.tick(plan, state, fake, T("2026-10-17T00:20:00"))
    assert fake.subs[-1].description.endswith("model=intel")
    assert out.failed and state["fallbacks"][0]["served"] == "intel"


def test_classify_served_model():
    assert daily.classify_served_model("ready\t/kaggle/arc3-model-view\n") == "swift"
    assert daily.classify_served_model("ready\t/kaggle/input/models/dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1") == "intel"
    assert daily.classify_served_model("crashed\t/kaggle/arc3-model-view") == "unknown"
    assert daily.classify_served_model("") == "unknown"


def test_real_plan_swaps_point_at_real_variants():
    plan = daily.load_plan()
    for swap in plan.get("swaps", []):
        for name in [swap["better"], swap["than"], *swap["replace"].keys(), *swap["replace"].values()]:
            assert (ROOT / "kaggle" / "variants" / f"{name}.json").exists(), name


def test_pre_start_test_never_takes_the_start_day_slot():
    fake, state = Fake(), {}
    out = daily.tick(PLAN, state, fake, T("2026-10-17T00:02:00"))     # before start_utc 00:05, same UTC day
    assert not fake.subs and any("start day" in a.text for a in out.actions)


def test_zero_action_smoke_is_broken_not_submitted_and_repushed():
    """2026-10-17: v6 and v3 were COMPLETE on Kaggle, served the model, and played 0 and 1 actions
    (a SyntaxError in the sandbox bootstrap). Such a version must not take the day's slot."""
    plan = dict(PLAN, min_smoke_actions=5)
    fake, state = Fake(), {}
    for variant in ("v1-franzen-faithful", "v3-swift"):
        kernel = daily.variant_kernel("me", variant)
        state.setdefault("pushes", []).append({"at": "2026-10-16T12:00:00+00:00", "variant": variant, "version": 1, "kernel": kernel})
        fake.status[kernel] = "COMPLETE"
    fake.smoke["me/arc3-duck-v1-franzen-faithful"] = 1          # broken
    fake.smoke["me/arc3-duck-v3-swift-1-5-flash-next"] = 40   # healthy
    fake.now = T("2026-10-17T10:20:00")
    out = daily.tick(plan, state, fake, fake.now)
    assert fake.subs[-1].parsed["variant"] == "v3-swift"                      # the healthy one takes the slot
    assert out.failed and any("played 1 action" in a.text for a in out.actions)  # and the broken one alerts
    assert fake.pushes[0] == "v1-franzen-faithful"                            # and is re-pushed (last push > 20 h ago)
    assert daily.smoke_actions_from_telemetry({"smoke_scores": []}) == 0
    assert daily.smoke_actions_from_telemetry({"smoke_scores": {}}) is None   # pre-PR-17 CPU checks: unknown, not broken
    assert daily.smoke_actions_from_telemetry({"smoke_scores": [{"actions": 3}, {"actions": 4}]}) == 7


def test_unknown_smoke_telemetry_does_not_block_a_submission():
    fake, state = Fake(), {}
    kernel = daily.variant_kernel("me", "v1-franzen-faithful")
    state.setdefault("pushes", []).append({"at": "2026-10-16T12:00:00+00:00", "variant": "v1-franzen-faithful", "version": 1, "kernel": kernel})
    fake.status[kernel] = "COMPLETE"
    fake.smoke[kernel] = None
    out = daily.tick(dict(PLAN, min_smoke_actions=5), state, fake, T("2026-10-17T10:20:00"))
    assert fake.subs[-1].parsed["variant"] == "v1-franzen-faithful" and not out.failed


def test_gpu_session_count_refusal_is_transient_and_retried_next_tick():
    """2026-10-18: 'Maximum batch GPU session count of 2 reached' (another project's kernel held a
    slot). Not a quota failure: no 20 h pause, no job failure, retried on the next tick."""
    fake, state = Fake(), {}
    fake.push_error = "Kernel push error: Maximum batch GPU session count of 2 reached."
    out = daily.tick(PLAN, state, fake, T("2026-10-17T00:20:00"))
    assert not out.failed and any(a.text.startswith("push v1-franzen-faithful waits") for a in out.actions)
    assert state["pushes"][-1]["transient"] is True
    fake.push_error = None
    out = daily.tick(PLAN, state, fake, T("2026-10-17T02:20:00"))      # two hours later, slot free: pushed
    assert fake.pushes == ["v1-franzen-faithful", "v3-swift"] and "paused" not in " ".join(a.text for a in out.actions)

