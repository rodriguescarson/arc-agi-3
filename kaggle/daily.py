#!/usr/bin/env python3
"""Daily ARC-AGI-3 submission scheduler (one submission per UTC day; Kaggle is the source of truth).

    python kaggle/daily.py tick [--dry-run] [--now 2026-10-17T00:20:00Z] [--summary FILE]
    python kaggle/daily.py report

Each tick (the workflow runs one every two hours):
  1. reads the competition's submissions (dates, descriptions, public scores) and today's slot;
  2. picks the variant that should be submitted next: the configured order first, then the variant
     with the best public score (and only that one after the freeze date);
  3. submits that variant's latest completed kernel version if the slot is free;
  4. pushes (Save & Run All) the kernel for the variant that comes after it, so a version is
     complete before the next UTC day begins.
Before the start date only the configured pre-start test submissions happen.

State that Kaggle cannot tell us (which kernel version belongs to which variant, when a push was
last attempted) lives in kaggle/state.json; the workflow keeps that file on the `automation/state`
branch so main never receives bot commits.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle"))

PLAN_PATH = ROOT / "kaggle" / "plan.json"
STATE_PATH = ROOT / "kaggle" / "state.json"
VARIANTS_DIR = ROOT / "kaggle" / "variants"
TAG = "arc3-auto"
DESC_RE = re.compile(r"arc3-auto (?:variant=(?P<variant>\S+)|test=(?P<test>\S+)) kernel=(?P<kernel>\S+) version=(?P<version>\d+)")


# ----------------------------------------------------------------------------- data

@dataclass
class Submission:
    date: datetime            # UTC
    description: str
    status: str               # COMPLETE | PENDING | ERROR ...
    public_score: float | None
    ref: str = ""

    @property
    def parsed(self) -> dict | None:
        m = DESC_RE.search(self.description or "")
        return m.groupdict() if m else None


@dataclass
class Action:
    kind: str                 # submit | push | note | failure
    text: str
    variant: str | None = None
    kernel: str | None = None
    version: int | None = None
    message: str | None = None


@dataclass
class Outcome:
    actions: list[Action] = field(default_factory=list)
    failed: bool = False

    def note(self, text: str) -> None:
        self.actions.append(Action("note", text))

    def markdown(self, now: datetime) -> str:
        lines = [f"### arc3 daily tick {now:%Y-%m-%d %H:%M} UTC", ""]
        for a in self.actions:
            lines.append(f"- **{a.kind}**: {a.text}")
        if self.failed:
            lines.append("- **FAILED**: see above")
        return "\n".join(lines) + "\n"


def parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def load_plan(path: Path = PLAN_PATH) -> dict:
    return json.loads(path.read_text())


def load_state(path: Path = STATE_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text() or "{}")
    return {}


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def variant_kernel(owner: str, variant: str) -> str:
    cfg = json.loads((VARIANTS_DIR / f"{variant}.json").read_text())
    return f"{owner}/{cfg['kernel_slug']}"


# ----------------------------------------------------------------------------- kaggle client

class KaggleClient:
    """Thin wrapper over the Kaggle API; everything the scheduler needs, nothing else."""

    def __init__(self) -> None:
        from kaggle.api.kaggle_api_extended import KaggleApi

        self.api = KaggleApi()
        self.api.authenticate()

    def submissions(self, competition: str) -> list[Submission]:
        out = []
        for s in self.api.competition_submissions(competition):
            score = getattr(s, "public_score", None)
            try:
                score = float(score) if score not in (None, "", "None") else None
            except (TypeError, ValueError):
                score = None
            out.append(Submission(as_utc(s.date), s.description or "", str(s.status).split(".")[-1].upper(), score, str(getattr(s, "ref", ""))))
        return out

    def kernel_status(self, kernel: str) -> str:
        r = self.api.kernels_status(kernel)
        status = getattr(r, "status", None) or (r.get("status") if isinstance(r, dict) else None)
        return str(status).split(".")[-1].upper()

    def push(self, variant: str) -> int:
        import build_notebook

        out, cfg = build_notebook.build(VARIANTS_DIR / f"{variant}.json")
        return build_notebook.push(out, cfg)

    def submit(self, competition: str, kernel: str, version: int, file_name: str, message: str) -> str:
        import build_notebook

        cmd = [build_notebook.kaggle_bin(), "competitions", "submit", "-c", competition, "-k", kernel,
               "-v", str(version), "-f", file_name, "-m", message]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        text = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if proc.returncode != 0:
            raise RuntimeError(f"submit failed: {text[-400:]}")
        return text


# ----------------------------------------------------------------------------- decisions

def slot_free(subs: list[Submission], now: datetime) -> tuple[bool, list[Submission]]:
    todays = [s for s in subs if s.date.date() == now.date()]
    counted = [s for s in todays if s.status != "ERROR"]
    return (not counted), todays


def submitted_variants(subs: list[Submission]) -> set[str]:
    return {p["variant"] for s in subs if (p := s.parsed) and p["variant"] and s.status != "ERROR"}


def best_scores(subs: list[Submission]) -> dict[str, float]:
    best: dict[str, float] = {}
    for s in subs:
        p = s.parsed
        if p and p["variant"] and s.public_score is not None:
            best[p["variant"]] = max(best.get(p["variant"], float("-inf")), s.public_score)
    return best


def candidates(plan: dict, subs: list[Submission], now: datetime) -> list[str]:
    """Variants in the order they should be submitted: the configured order (unsubmitted first),
    then the best public score; after the freeze only the best, then the rest as a fallback."""
    order = list(plan["order"])
    done = submitted_variants(subs)
    scores = best_scores(subs)
    best = max(order, key=lambda v: (scores.get(v, float("-inf")), -order.index(v))) if scores else None
    frozen = now >= parse_time(plan["freeze_utc"])
    out: list[str] = []
    if not frozen:
        out += [v for v in order if v not in done]
    if best:
        out.append(best)
    out += [v for v in order if v not in out]
    seen: set[str] = set()
    return [v for v in out if not (v in seen or seen.add(v))]


def choose_target(plan: dict, subs: list[Submission], now: datetime, exclude: set[str] = frozenset()) -> str:
    """Which variant should be submitted next (first candidate not excluded)."""
    for v in candidates(plan, subs, now):
        if v not in exclude:
            return v
    return plan["order"][0]


def latest_push(state: dict, variant: str) -> dict | None:
    pushes = [p for p in state.get("pushes", []) if p["variant"] == variant and p.get("version")]
    return max(pushes, key=lambda p: p["version"]) if pushes else None


def last_attempt(state: dict, variant: str) -> datetime | None:
    stamps = [parse_time(p["at"]) for p in state.get("pushes", []) if p["variant"] == variant]
    return max(stamps) if stamps else None


def last_failed_attempt(state: dict) -> datetime | None:
    """Most recent push that errored, any variant: quota errors are account-wide, so one failure
    pauses every push for push_retry_hours instead of burning a tick on each variant."""
    stamps = [parse_time(p["at"]) for p in state.get("pushes", []) if p.get("error")]
    return max(stamps) if stamps else None


def tick(plan: dict, state: dict, client, now: datetime, dry_run: bool = False) -> Outcome:
    out = Outcome()
    competition = plan["competition"]
    subs = client.submissions(competition)
    free, todays = slot_free(subs, now)
    out.note(f"{len(subs)} submissions on record; today's slot {'free' if free else 'used'}"
             + (f" ({todays[-1].description[:60]!r}, {todays[-1].status})" if todays else ""))
    start, end = parse_time(plan["start_utc"]), parse_time(plan["end_utc"])
    state.setdefault("pushes", [])

    def do_submit(kernel: str, version: int, message: str, variant: str | None) -> bool:
        a = Action("submit", f"{kernel} v{version}: {message}", variant, kernel, version, message)
        if dry_run:
            a.text = "(dry-run) " + a.text
            out.actions.append(a)
            return True
        try:
            reply = client.submit(competition, kernel, version, plan["submission_file"], message)
            a.text += f" -> {reply[-120:]}"
            out.actions.append(a)
            state.setdefault("submissions", []).append({"at": now.isoformat(), "kernel": kernel, "version": version, "variant": variant, "message": message})
            return True
        except Exception as exc:  # noqa: BLE001 - surfaced in the summary and the exit code
            out.actions.append(Action("failure", f"submit {kernel} v{version}: {exc}"))
            out.failed = True
            return False

    def do_push(variant: str) -> None:
        a = Action("push", f"{variant}", variant)
        if dry_run:
            a.text = "(dry-run) push " + variant
            out.actions.append(a)
            return
        record = {"at": now.isoformat(), "variant": variant, "version": None, "error": None}
        try:
            record["version"] = client.push(variant)
            record["kernel"] = variant_kernel(plan["owner"], variant)
            a.text = f"{variant} -> {record['kernel']} v{record['version']}"
            out.actions.append(a)
        except Exception as exc:  # noqa: BLE001
            record["error"] = str(exc)[-300:]
            out.actions.append(Action("failure", f"push {variant}: {record['error']}"))
            out.failed = now >= start
        state["pushes"].append(record)

    # ---- before the start date: only the pre-start tests ----
    if now < start:
        for test in plan.get("pre_start_tests", []):
            already = any((p := s.parsed) and p["test"] == test["label"] and s.status != "ERROR" for s in subs)
            if already:
                out.note(f"pre-start test {test['label']} already submitted")
                continue
            if now < parse_time(test["not_before"]):
                out.note(f"pre-start test {test['label']} waits until {test['not_before']}")
                continue
            if not free:
                out.note(f"pre-start test {test['label']} waits for a free slot")
                continue
            msg = f"{TAG} test={test['label']} kernel={test['kernel']} version={test['version']}"
            if do_submit(test["kernel"], int(test["version"]), msg, None):
                free = False
        out.note(f"GPU pushes begin at {plan['start_utc']}")
        return out
    if now >= end:
        out.note("past end_utc; nothing to do")
        return out

    # ---- submit the first candidate that has a COMPLETE version (never waste the day) ----
    status_cache: dict[str, str] = {}

    def version_status(variant: str) -> tuple[dict | None, str | None]:
        rec = latest_push(state, variant)
        if not rec:
            return None, None
        if rec["kernel"] not in status_cache:
            status_cache[rec["kernel"]] = client.kernel_status(rec["kernel"])
        return rec, status_cache[rec["kernel"]]

    ranked = candidates(plan, subs, now)
    submitted_now = False
    if free:
        for variant in ranked:
            rec, status = version_status(variant)
            if rec and status == "COMPLETE":
                rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "unknown"
                msg = f"{TAG} variant={variant} kernel={rec['kernel']} version={rec['version']} rev={rev}"
                submitted_now = do_submit(rec["kernel"], rec["version"], msg, variant)
                break
            out.note(f"{variant}: " + (f"{rec['kernel']} v{rec['version']} is {status}" if rec else "no version yet") + "; not submittable")
        if not submitted_now:
            out.note("slot free but no variant has a completed version; nothing submitted")
    else:
        out.note("candidates: " + ", ".join(ranked))

    # ---- keep versions ready: push every variant that lacks one, at most max_in_flight at a time ----
    in_flight = 0
    for variant in plan["order"]:
        rec, status = version_status(variant)
        if rec and status in {"QUEUED", "RUNNING"}:
            in_flight += 1
    max_in_flight = int(plan.get("max_in_flight", 2))
    retry_hours = float(plan.get("push_retry_hours", 20))
    failed_at = last_failed_attempt(state)
    if failed_at and now - failed_at < timedelta(hours=retry_hours):
        out.note(f"pushes paused: last push error at {failed_at:%Y-%m-%d %H:%M} UTC; retry after {retry_hours:g} h")
        return out
    for variant in ranked:
        rec, status = version_status(variant)
        if rec and status in {"COMPLETE", "QUEUED", "RUNNING"}:
            continue
        attempt = last_attempt(state, variant)
        if attempt and now - attempt < timedelta(hours=float(plan.get("push_retry_hours", 20))):
            out.note(f"{variant}: last push attempt {attempt:%Y-%m-%d %H:%M}; retry after {plan.get('push_retry_hours', 20)} h")
            continue
        if in_flight >= max_in_flight:
            out.note(f"{variant}: needs a push; {in_flight} commits already in flight")
            break
        do_push(variant)
        if state["pushes"][-1].get("error"):
            out.note("push failed; the remaining pushes wait for the next tick")
            break
        in_flight += 1
    return out


# ----------------------------------------------------------------------------- cli

def report(client, plan: dict) -> str:
    rows = ["| date (UTC) | variant / test | kernel | version | status | public |", "|---|---|---|---|---|---|"]
    for s in sorted(client.submissions(plan["competition"]), key=lambda s: s.date):
        p = s.parsed or {}
        rows.append(f"| {s.date:%Y-%m-%d %H:%M} | {p.get('variant') or p.get('test') or s.description[:40]} | {p.get('kernel', '')} | {p.get('version', '')} | {s.status} | {'' if s.public_score is None else s.public_score} |")
    return "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["tick", "report"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--now", help="override the clock, e.g. 2026-10-17T00:20:00Z")
    ap.add_argument("--summary", type=Path, help="append the markdown summary to this file")
    ap.add_argument("--plan", type=Path, default=PLAN_PATH)
    ap.add_argument("--state", type=Path, default=STATE_PATH)
    args = ap.parse_args()
    plan = load_plan(args.plan)
    client = KaggleClient()
    if args.command == "report":
        print(report(client, plan))
        return 0
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    state = load_state(args.state)
    outcome = tick(plan, state, client, now, dry_run=args.dry_run)
    if not args.dry_run:
        save_state(state, args.state)
    text = outcome.markdown(now)
    print(text)
    if args.summary:
        with open(args.summary, "a") as fh:
            fh.write(text)
    return 2 if outcome.failed else 0


if __name__ == "__main__":
    sys.exit(main())
