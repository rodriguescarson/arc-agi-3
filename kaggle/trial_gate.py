"""Gate a 6-game trial against a reference trial (the v10 trial for the 2026-10-31 v11 gates).

usage: python3 -I kaggle/trial_gate.py <trial_dir> --ref <ref_dir> [--prefix "Stall rule"] [--effort medium]

Each dir holds one kernel's outputs, fetched with
    kaggle kernels output <kernel> -p <dir> --file-pattern "telemetry.json|requests.jsonl$|\\.log$"
Reads telemetry.json, *_p0_requests.jsonl and *.log from each dir. Prints per-game and total metrics and
a PASS/FAIL line per gate. Gate G1 (stall rule): COMPLETE with no errors, system prompt leads with the
prefix, a no-action run that reached 5 replies goes on to 8 in <= 25% of cases (v10 35%, v1f 34%), cut-off tokens
<= 6.6%, levels >= 30, actions per solved level up by <= 15%, no game at 0 levels where the reference
solved 2+. Gate G2 (effort medium): every request carries reasoning_effort=medium, tokens per reply
<= 0.6x the reference, levels >= 30, no errors.
"""

import argparse
import glob
import json
import os
import re

LVL = re.compile(r"Current state: step (\d+), level (\d+)")


def textof(c):
    if isinstance(c, list):
        return "\n".join(p.get("text", "") for p in c if p.get("type") == "text")
    return c or ""


def load_game(path):
    recs, pend, system, efforts = [], None, None, set()
    for line in open(path):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ev = r.get("event")
        if ev == "request":
            msgs = r["messages"]
            if system is None and msgs and msgs[0]["role"] == "system":
                system = textof(msgs[0].get("content"))
            efforts.add((r.get("chat_template_kwargs") or {}).get("reasoning_effort"))
            lvl = None
            for m in reversed(msgs):
                if m["role"] == "user":
                    mm = LVL.search(textof(m.get("content")))
                    if mm:
                        lvl = int(mm.group(2))
                    break
            pend = dict(level=lvl, action=r.get("action"))
        elif ev == "response":
            u = r.get("usage") or {}
            d = dict(pend or {})
            d.update(ctok=u.get("completion_tokens") or 0, finish=r.get("finish_reason"))
            recs.append(d)
            pend = None
    for j, r in enumerate(recs):
        nxt = recs[j + 1] if j + 1 < len(recs) else None
        r["acted"] = (
            None if (nxt is None or r["action"] is None or nxt["action"] is None) else nxt["action"] > r["action"]
        )
    return recs, system, efforts


def streak_tok(recs, minlen=6):
    out, cur = 0, []
    for r in recs + [{"acted": True}]:
        if r.get("acted") is False:
            cur.append(r)
        else:
            if len(cur) >= minlen:
                out += sum(x["ctok"] for x in cur)
            cur = []
    return out


def streak_lengths(recs):
    out, n = [], 0
    for r in recs + [{"acted": True}]:
        if r.get("acted") is False:
            n += 1
        else:
            if n:
                out.append(n)
            n = 0
    return out


def load_trial(d):
    tel = json.load(open(os.path.join(d, "telemetry.json")))
    games = {}
    for s in tel["smoke_scores"]:
        g = s["game_id"].split("-")[0]
        f = glob.glob(os.path.join(d, f"{g}-*_p0_requests.jsonl"))
        recs, system, efforts = load_game(f[0]) if f else ([], None, set())
        games[g] = dict(
            score=s["score"],
            levels=s["levels"],
            actions=s["actions"],
            state=s.get("state"),
            replies=len(recs),
            ctok=sum(r["ctok"] for r in recs),
            cut=sum(r["ctok"] for r in recs if r["finish"] == "length"),
            streak=streak_tok(recs),
            lengths=streak_lengths(recs),
            system=system,
            efforts=efforts,
            has_log=bool(f),
        )
    errs = 0
    for lf in glob.glob(os.path.join(d, "*.log")):
        txt = open(lf, errors="replace").read()
        errs += len(re.findall(r"^Traceback|\bERROR\b", txt, re.M))
    return tel, games, errs


def totals(games):
    t = {
        k: sum(g[k] for g in games.values()) for k in ("score", "levels", "actions", "replies", "ctok", "cut", "streak")
    }
    t["mean"] = t["score"] / max(1, len(games))
    t["streak_share"] = t["streak"] / max(1, t["ctok"])
    t["cut_share"] = t["cut"] / max(1, t["ctok"])
    t["tok_per_reply"] = t["ctok"] / max(1, t["replies"])
    t["act_per_level"] = t["actions"] / max(1, t["levels"])
    lens = [n for g in games.values() for n in g["lengths"]]
    t["reach5"] = sum(1 for n in lens if n >= 5)
    t["go_on8"] = sum(1 for n in lens if n >= 8) / max(1, t["reach5"])  # P(run reaches 8 | it reached 5)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trial")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--effort", default=None)
    a = ap.parse_args()
    _, ref, _ = load_trial(a.ref)
    tel, tri, errs = load_trial(a.trial)
    R, T = totals(ref), totals(tri)
    print(
        f"{'game':6} {'score':>7} {'ref':>7} {'lvl':>4} {'ref':>4} {'act':>5} {'streak6':>8} {'ref':>6} {'cut':>6} {'tok/rep':>8}"
    )
    for g in tri:
        x, y = tri[g], ref.get(g, {})
        print(
            f"{g:6} {x['score']:7.2f} {y.get('score', 0):7.2f} {x['levels']:4} {y.get('levels', 0):4} {x['actions']:5} "
            f"{x['streak'] / max(1, x['ctok']):8.3f} {y.get('streak', 0) / max(1, y.get('ctok', 1)):6.3f} "
            f"{x['cut'] / max(1, x['ctok']):6.3f} {x['ctok'] / max(1, x['replies']):8.0f}"
        )
    print(
        f"total  mean {T['mean']:.2f} (ref {R['mean']:.2f}); levels {T['levels']} (ref {R['levels']}); "
        f"streak6 share {T['streak_share']:.3f} (ref {R['streak_share']:.3f}); cut share {T['cut_share']:.3f} "
        f"(ref {R['cut_share']:.3f}); tok/reply {T['tok_per_reply']:.0f} (ref {R['tok_per_reply']:.0f}); "
        f"actions/level {T['act_per_level']:.1f} (ref {R['act_per_level']:.1f}); log errors {errs}; "
        f"P(no-action run reaches 8 | reached 5) {T['go_on8']:.2f} of {T['reach5']} (ref {R['go_on8']:.2f} of {R['reach5']})"
    )
    missing = [g for g in tri if not tri[g]["has_log"]]
    gates = [
        ("all 6 games scored, request logs present", len(tri) == 6 and not missing),
        ("no errors in the log", errs == 0),
        ("levels >= 30", T["levels"] >= 30),
    ]
    if a.prefix:
        gates += [
            (
                "system prompt leads with the prefix",
                all((g["system"] or "").startswith(a.prefix) for g in tri.values()),
            ),
            # v10 0.35 of 40, v1f 0.34 of 32: stable without the rule, so a drop to 0.25 is the rule acting
            ("P(no-action run reaches 8 | reached 5) <= 0.25", T["go_on8"] <= 0.25),
            ("cut-off tokens <= 6.6%", T["cut_share"] <= 0.066),
            ("actions per solved level up <= 15%", T["act_per_level"] <= 1.15 * R["act_per_level"]),
            (
                "no 0-level game where ref solved 2+",
                not any(tri[g]["levels"] == 0 and ref.get(g, {}).get("levels", 0) >= 2 for g in tri),
            ),
        ]
    if a.effort:
        gates += [
            (f"every request has reasoning_effort={a.effort}", all(g["efforts"] == {a.effort} for g in tri.values())),
            ("tokens per reply <= 0.6x ref", T["tok_per_reply"] <= 0.6 * R["tok_per_reply"]),
        ]
    for name, ok in gates:
        print(("PASS " if ok else "FAIL ") + name)
    print("GATE", "PASS" if all(ok for _, ok in gates) else "FAIL")


if __name__ == "__main__":
    main()
