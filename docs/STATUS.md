# Status and handover (written 2026-10-13 01:30 IST, updated 2026-10-18 14:30 IST; keep this file current)

Everything a reader needs to run, check or stop this entry without the chat history.
Times are IST unless marked UTC. Competition deadlines are UTC.

## Where things stand

| item | state |
|---|---|
| Repo | `rodriguescarson/arc-agi-3` (private; make public before the deadline, prize rule). All changes via PR. GitHub refuses branch protection and rulesets on a private free-plan repo (HTTP 403 "Upgrade to GitHub Pro or make this repository public"), so the rule is procedural: merge only after the `test` check is green (PR #7 slipped through with a red check; fixed in #8). |
| Kaggle account | `carsonrodrigues`. One submission per UTC day, shared by every session that uses the account. |
| GPU quota | week of Oct 17: four commits so far (v6 v1, v3 v1, both broken; v6 v2 COMPLETE and submitted 2026-10-18; v3 v2 pushed 08:57 UTC; v2 waiting), ≈ 3 h of the 30 h. Each commit ≈ 35 min + an RTX queue of up to 8 h; scored reruns cost no quota. Kaggle allows **2 GPU batch sessions per account across all projects**: a queued `rsna-knee-reader-train-features` kernel held one on Oct 18. |
| **GitHub Actions** | **Dead since 2026-10-16 17:35 UTC**: every `daily-submit` job (and the CI `test` check) fails in 3 s with "The job was not started because recent account payments have failed or your spending limit needs to be increased". Only Carson can fix it (Settings → Billing & plans). Until then the tick runs from this Mac: `kaggle/local_tick.sh` (loads/saves the `automation/state` branch like the workflow); on Oct 18 a shell loop ran it every 15 min, log `~/Library/Logs/arc3/local-tick.log`. The LaunchAgent and the routine keep dispatching a workflow that cannot start; harmless. |
| Submissions so far | From this repo: 2026-10-14 pre-start CPU test 0.12. From the paper-track workspace (`~/Projects/arc_prize_2026`): Oct 12 0.15, Oct 13 0.08, Oct 15 0.08, Oct 16 0.01 (its last scheduled one). **Oct 17 slot lost**: the first two GPU commits (v6, v3) were COMPLETE but played 0 and 1 actions, a SyntaxError in the sandbox bootstrap (`from __future__` in the spliced `level_memory.py`); fixed 2026-10-18, details in `docs/SUBMISSIONS.md`. Oct 18 08:57 UTC: **v6 v2 submitted** (fixed bundle 605bc36; smoke 286 actions, 3 levels, model=swift), the first real GPU draw; score expected ≈ 9 h later. |
| Public LB (Oct 11) | Yi-Chia Chen 62.96, Tufa 56.52, mtg 45.0; Franzen's open notebook 27.89; identical copies score mean 25.8, SD 3.9. |
| Variants built | v1 Franzen-faithful, v3 Swift-1.5 target (+ Intel fallback + loader patch), v2 level memory, v4 reasoning effort medium. All render, 34 tests, CI green. CPU checks of v1 and v3 passed on Kaggle. |
| GPU path | **Verified 2026-10-17**: Swift-1.5 loads with the Gated-DeltaNet loader patch (two-part model view, `served_model.txt` = ready), the Pennyroyal server boots in ~11 min and serves at 240-270 tok/s with MTP accept rate 0.82; the harness talks to it (1,974 requests). v6 v2's smoke run (2026-10-18) played 286 actions and cleared 3 levels, so the whole GPU path works end to end. **Not yet verified**: the Intel fallback path (v2/v1 commits pending). |
| Guards added 2026-10-18 | `plan.json` `min_smoke_actions=5`: a COMPLETE commit whose smoke run played fewer actions is BROKEN (alert, never submitted, re-pushed). Kernel slugs must equal the slugified title (Kaggle names kernels after the title; a mismatched second push is HTTP 409). "Maximum batch GPU session count" refusals are transient retries, not a 20 h pause. |

## What runs automatically

`kaggle/daily.py tick` (plan in `kaggle/plan.json`) decides and acts; three independent triggers run it:

1. **GitHub Actions cron** `.github/workflows/daily-submit.yml`, every 2 h at :15 UTC. On this account scheduled runs lag by hours (none fired in the 11 h after the merge on Oct 12), so it is not the primary trigger.
2. **LaunchAgent on this Mac** `~/Library/LaunchAgents/com.carson.arc3-daily-submit.plist`: every 2 h while the Mac is awake it runs `gh workflow run daily-submit.yml`. Verified 2026-10-13 01:08 IST (run 38298924033 succeeded). Log: `~/Library/Logs/arc3/daily-submit.log`. Remove with `launchctl bootout gui/$(id -u)/com.carson.arc3-daily-submit`.
3. **claude.ai routine** "arc3: dispatch daily-submit workflow" (`trig_01YSqbMMHHuCFKzDbZVL32V8`) at 00:20 and 06:20 UTC (05:50 / 11:50 IST) in a cloud session on this repo; it only dispatches the workflow (REST: `gh api -X POST repos/rodriguescarson/arc-agi-3/actions/workflows/daily-submit.yml/dispatches -f ref=main`, because `gh workflow run` needs GraphQL, which that sandbox blocks) and sends a push notification if the run fails. Test fires on 2026-10-13 01:10 and 01:13 IST both queued a run that succeeded.

**Slot race (added 2026-10-13):** the paper-track workspace on the same account submits at about 00:07 UTC, which consumed the Oct 13 slot before our ticks. All three triggers now also fire in the first minute of the UTC day (cron `1 0 * * *`; LaunchAgent at 05:31 and 05:36 IST; routine at 00:01 and 06:01 UTC), so our submission is attempted at ~00:02 UTC. The paper-track workspace has session crons for Oct 14, 15 and 16 (its E16 ablations, ~00:07 UTC) and nothing scheduled after that; its two 'final' submissions can be chosen among runs that already exist. Our test was deferred so it never takes those days. From Oct 17 this repo owns the slot unless a new conflict appears; the proper rule is one automation per account: Carson decides.

Several dispatches per day are harmless: ticks are idempotent (the slot is checked live on Kaggle) and the workflow's concurrency group queues them.

Timeline the plan encodes:

- **Pre-start test (moved up to 2026-10-14 on Carson's request; the paper-track session left that day's slot unused):** near-zero test submission of `arc3-duck-v3-cpucheck` **v3**. Purpose: prove the submit API and the competition rerun of our cells in `TRUE_SUBMISSION` mode (gateway, hidden games, submission writing, scoring). The CPU variant now keeps its CPU path in the rerun (`_smoke_mode` in `kaggle/cells/00_env.py`) and plays the offline random solver, 60 actions per game. Versions 1 and 2 would have crashed there: the rerun forced the GPU path and stopped at the libcuda lookup on a CPU machine. GPU variants are unchanged (always the model server in the rerun).
- **2026-10-17 00:00:30 UTC onward:** order **v6 (Swift + level memory) x2 → v2 (Intel + level memory) x2 → v7 (v6 + drain memory) x2**, with an automatic swap of v7 for v7i (Intel base) if v2 beats v6 by more than 2 points over two draws each. The first tick pushes v6 and v2 together. Each tick submits the first candidate with a COMPLETE version, labels the submission with the model its commit actually served (`model=swift|intel`), and alerts by failing the job if a Swift variant fell back to Intel. Up to two commits in flight; one push failure pauses pushes for 20 h. The pre-start test never runs on the start day.
- **After the order, and from 2026-10-31 00:00 UTC (freeze):** re-submit the variant with the best **mean** public score; completed versions are reused, no new pushes. Finals rule and the external review's adopted/rejected items: `docs/PLAN.md`.
- **2026-11-02 22:30 UTC:** `end_utc`; final deadline 23:59 UTC.

State Kaggle cannot provide (kernel version ↔ variant, push attempts) lives in `state.json` on the `automation/state` branch; the bot never commits to main. Secrets `KAGGLE_USERNAME` / `KAGGLE_KEY` are GitHub Actions secrets on the private repo.

## How to check

- `gh run list --workflow daily-submit.yml --limit 5` and the job summary of a run (Actions → daily-submit). While Actions is billing-blocked: `tail -40 ~/Library/Logs/arc3/local-tick.log`.
- A GPU commit is healthy only if its `telemetry.json` `smoke_scores` show actions played (download with `kaggle kernels output <kernel>/<version> --file-pattern telemetry.json`); COMPLETE alone proved nothing on Oct 17.
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
- GitHub Actions billing (live since Oct 16): no automatic ticks and no CI until Carson restores billing; the local loop dies with the Mac's sleep or the session. Fix billing, or move the LaunchAgent to run `kaggle/local_tick.sh` directly.
- Another project's GPU kernels (RSNA knee) share the account's two GPU batch sessions and can delay a push for hours.

## Next decisions (Carson)

- Merge policy: PRs are opened and merged by the agent when asked; otherwise they wait.
- Oct 17–20: read the first four draws; if v3 fell back to Intel, decide on the Swift NVFP4 route (rellik13's recipe in `data/bundles/sirikilohit-cell11.py`).
- Before Nov 2: make the repo and the datasets `arc3-harness-bundle`, `py312-portable` public.
