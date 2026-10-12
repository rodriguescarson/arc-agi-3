# Status and handover (written 2026-10-13 01:30 IST; keep this file current)

Everything a reader needs to run, check or stop this entry without the chat history.
Times are IST unless marked UTC. Competition deadlines are UTC.

## Where things stand

| item | state |
|---|---|
| Repo | `rodriguescarson/arc-agi-3` (private; make public before the deadline, prize rule). main is protected by convention: all changes via PR. |
| Kaggle account | `carsonrodrigues`. One submission per UTC day, shared by every session that uses the account. |
| GPU quota | exhausted until **2026-10-17 00:00 UTC (05:30 IST)**; keep that week's 30 h for ARC. Each commit ≈ 35 min + an RTX queue of up to 8 h; scored reruns cost no quota. |
| Submissions so far | 2026-10-12 04:25 UTC: "model-based explorer v7" from the paper-track workspace (`~/Projects/arc_prize_2026`), public 0.15. Nothing from this repo yet. |
| Public LB (Oct 11) | Yi-Chia Chen 62.96, Tufa 56.52, mtg 45.0; Franzen's open notebook 27.89; identical copies score mean 25.8, SD 3.9. |
| Variants built | v1 Franzen-faithful, v3 Swift-1.5 target (+ Intel fallback + loader patch), v2 level memory, v4 reasoning effort medium. All render, 34 tests, CI green. CPU checks of v1 and v3 passed on Kaggle. |
| Untested until the first GPU commit | the model server itself; for v3 the Swift load (patched loader, quantised gated `q_proj`). If Swift fails to boot, the notebook relaunches on the Intel checkpoint and records it in `served_model.txt`. |

## What runs automatically

`kaggle/daily.py tick` (plan in `kaggle/plan.json`) decides and acts; three independent triggers run it:

1. **GitHub Actions cron** `.github/workflows/daily-submit.yml`, every 2 h at :15 UTC. On this account scheduled runs lag by hours (none fired in the 11 h after the merge on Oct 12), so it is not the primary trigger.
2. **LaunchAgent on this Mac** `~/Library/LaunchAgents/com.carson.arc3-daily-submit.plist`: every 2 h while the Mac is awake it runs `gh workflow run daily-submit.yml`. Verified 2026-10-13 01:08 IST (run 38298924033 succeeded). Log: `~/Library/Logs/arc3/daily-submit.log`. Remove with `launchctl bootout gui/$(id -u)/com.carson.arc3-daily-submit`.
3. **claude.ai routine** "arc3: dispatch daily-submit workflow" (`trig_01YSqbMMHHuCFKzDbZVL32V8`) at 00:20 and 06:20 UTC (05:50 / 11:50 IST) in a cloud session on this repo; it only dispatches the workflow (REST: `gh api -X POST repos/rodriguescarson/arc-agi-3/actions/workflows/daily-submit.yml/dispatches -f ref=main`, because `gh workflow run` needs GraphQL, which that sandbox blocks) and sends a push notification if the run fails. Test fires on 2026-10-13 01:10 and 01:13 IST both queued a run that succeeded.

Several dispatches per day are harmless: ticks are idempotent (the slot is checked live on Kaggle) and the workflow's concurrency group queues them.

Timeline the plan encodes:

- **2026-10-13 (first tick after 00:05 UTC):** zero-score test submission of `arc3-duck-v3-cpucheck` v1. Purpose: prove the submit API, the competition rerun of our cells in `TRUE_SUBMISSION` mode (CPU, server never starts, warm-up RESET yields a valid 0), and the scoring path. Expect public score 0.0 after the ~9 h rerun.
- **2026-10-17 00:05 UTC onward:** order v1 → v3 → v2 → v4: the first tick of each UTC day submits the target's latest COMPLETE kernel version, then pushes (Save & Run All, smoke config) the next variant so it is complete before the next midnight.
- **After the order, and from 2026-10-31 00:00 UTC (freeze):** re-submit the variant with the best public score; completed versions are reused, no new pushes.
- **2026-11-02 22:30 UTC:** `end_utc`; final deadline 23:59 UTC.

State Kaggle cannot provide (kernel version ↔ variant, push attempts) lives in `state.json` on the `automation/state` branch; the bot never commits to main. Secrets `KAGGLE_USERNAME` / `KAGGLE_KEY` are GitHub Actions secrets on the private repo.

## How to check

- `gh run list --workflow daily-submit.yml --limit 5` and the job summary of a run (Actions → daily-submit).
- `PYTHONPATH=. .venv/bin/python kaggle/daily.py report` (every submission with variant, kernel, version, status, public score).
- `git show origin/automation/state:state.json` (what was pushed, when, and any push errors).
- Kaggle: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/submissions
- A failed push or submit after Oct 17 fails the Actions job → GitHub emails the failure.

## How to intervene

- Pause: disable the workflow (`gh workflow disable daily-submit.yml`), unload the LaunchAgent, pause the routine on claude.ai.
- Change the order or freeze date: edit `kaggle/plan.json` via PR.
- Add a variant: `kaggle/variants/<name>.json` (+ append to `plan.json` order). Do not push `arc3-duck-*` kernels by hand while the bot runs; it assumes the latest version of each kernel is its own.
- Dry run of any date: `PYTHONPATH=. .venv/bin/python kaggle/daily.py tick --dry-run --now 2026-10-17T00:20:00Z`.
- Manual submit (fallback): `kaggle competitions submit -c arc-prize-2026-arc-agi-3 -k carsonrodrigues/<kernel> -v <version> -f submission.parquet -m "<message>"`.

## Decisions and why (2026-10-12)

- **No fine-tuning.** Four teams report zero gain on Flash-Next (SFT with teachers, RL on H200 nodes); same-model LoRA gains on 27B did not transfer; the RTX Pro 6000 cannot train a 100B model; our SGLang W4A16+MTP stack has no adapter path; single daily draws (SD 3.9) cannot measure a small effect. Details: `docs/LANDSCAPE.md`.
- **No "enable thinking".** Already at the template maximum (`reasoning_effort=xhigh`, reasoning preserved).
- **v3 = Swift-1.5 model swap** (vendor claim: 55–63 % fewer thinking tokens, <1 % accuracy loss): the fast "more turns per game" lever; one input swap plus a boot-time loader patch found by reading the Pennyroyal wheel in free CPU kernels.
- **v4 = reasoning effort medium**: one flag.
- **Compaction** (OpenAI's second setting): Franzen tested both summary modes, no clear gain; skipped.
- **RunPod / A6000 not used**: nothing needed them; the A6000 (48 GB) cannot hold the 125B model.

## Risks

- GPU quota consumed by other sessions on the account in the week of Oct 17 → pushes fail → job fails → email.
- The daily slot taken by another session before the bot's first tick → the bot waits for the next day (it never double-submits).
- Swift's quantised gated attention may not load in Pennyroyal → automatic Intel fallback; the v3 draw is then a v1-equivalent run (check `served_model.txt`).
- Franzen could remove his public model/wheelhouse datasets → mirror them (~90 GB) if that happens.
- GitHub cron lag: mitigated by the LaunchAgent and the routine.

## Next decisions (Carson)

- Merge policy: PRs are opened and merged by the agent when asked; otherwise they wait.
- Oct 17–20: read the first four draws; if v3 fell back to Intel, decide on the Swift NVFP4 route (rellik13's recipe in `data/bundles/sirikilohit-cell11.py`).
- Before Nov 2: make the repo and the datasets `arc3-harness-bundle`, `py312-portable` public.
