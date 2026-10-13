# Submission log

One submission per day. Public score = 55 hidden games; final ranking uses the other 55.

| date (UTC) | variant | kernel version | commit (git) | public score | notes |
|---|---|---|---|---|---|
| 2026-10-12 | v1-franzen-faithful | not yet committed | 110b447 | - | GPU quota exhausted (37/30 h); first GPU commit possible 2026-10-17 00:00 UTC |
| 2026-10-12 | v1-cpucheck (CPU, not a submission) | arc3-duck-v1-cpucheck v1-v3 | 0771be0 | n/a | v1: JSON `false` rendered into Python (fixed + test). v2: everything up to the GPU driver lookup worked (fixed for CPU). **v3 COMPLETE**: on the Python 3.13 image, `/usr/bin/python3.12` passes the stdlib check, the full Pennyroyal cp312 wheelhouse installs under it (`sglang 0.5.19+gd00d88efc8d6`, `torch 2.13.0+cu130`), bundle + pickles + TAAF loop + offline games + `submission.parquet` + `diagnostics.html` all fine. Only the model server itself is untested until the GPU quota refreshes. |
| 2026-10-12 | v3-cpucheck (CPU, not a submission) | arc3-duck-v3-cpucheck v1 | 5417b38 | n/a | COMPLETE: Kaggle mounted the two-part Swift-1.5 mirror (177 GB) + Intel fallback (85 GB) + draft + wheelhouse together; cell 00 merged the two parts into `/kaggle/arc3-model-view` (95 files); wheelhouse installed under python3.12; offline games + `submission.parquet` + `diagnostics.html` fine. Server (and the Gated-DeltaNet loader patch) untested until the GPU quota refreshes. |
| 2026-10-13 | (pre-start test, not submitted) | arc3-duck-v3-cpucheck v1 | bed0326 | - | Slot taken at 00:07 UTC by the paper-track workspace's "v7 agent (E15), memory ON" submission (PENDING). The bot's ticks at 00:20 UTC (manual dispatch), 00:15 cron, 00:20 routine and 01:38 LaunchAgent all see the slot used and wait; the test re-tries on the next free day before Oct 17. **Account-level conflict:** if the other session keeps submitting daily at 00:07 UTC, no submission from this repo can ever land, including the GPU runs from Oct 17. Carson must pick one automation per day. Note: GitHub's own cron fired once at 19:48 UTC on Oct 12 (33 min late). |

From 2026-10-13 submissions are made by `kaggle/daily.py` (see docs/STATUS.md); messages read `arc3-auto variant=... kernel=... version=... rev=...`. `python kaggle/daily.py report` prints the live table.

Reference distribution for the v1 configuration (Franzen copies, Son Pham, Oct 2):
mean 25.77, SD 3.93, median 26.19.

CPU baselines on the 25 public games (`arc3.local_eval`, 250 actions/game cap, competition cap 1.0):
explorer 0/183 levels (0.00), random 0/183 levels (0.00). Model-free search does not clear a single
level 1; everything rides on the LLM harness.
