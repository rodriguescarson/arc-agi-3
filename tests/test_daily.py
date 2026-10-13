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
    fake.status["me/arc3-duck-v1"] = "COMPLETE"
    fake.now = T("2026-10-17T04:20:00")
    out = daily.tick(PLAN, state, fake, fake.now)
    assert fake.subs[-1].description.startswith("arc3-auto variant=v1-franzen-faithful kernel=me/arc3-duck-v1 version=1")
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
