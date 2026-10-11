# Plan (written 2026-10-12, 21 days before the deadline)

## The honest shape of the problem

- The public top is 63 (Yi-Chia Chen) and 56.5 (Tufa Labs); both are private. The best open
  code (Franzen) draws from N(25.8, 3.9) on the public half of the hidden set.
- We have no CUDA GPU. The model (Qwen3.8-Flash-Next, 125B MoE) needs the 96 GB RTX Pro 6000
  that Kaggle provides. Every real evaluation is a Kaggle commit (8 h queue + ~35 min) and a
  scored rerun (9 h), and **one submission per day**.
- Public-game scores do not predict the leaderboard well, and single draws differ by +/-4.

So the strategy is not "find a clever trick locally". It is:

1. **Ship a Franzen-faithful notebook under our own account first** (v1). It proves the
   pipeline on the post-Oct-1 Kaggle image, gives us our own draw, and makes us eligible.
2. **Submit every single day.** The leaderboard keeps the best draw; the final two picks are
   chosen by public score. Skipping a day is the only unforced error available.
3. **Change one mechanism at a time, each with a reason**, and prefer changes that cannot
   lower the score: reliability (server boot, Python 3.12 selection, fallback actions),
   throughput (more useful tokens per game), and feedback fidelity (what rellik13 called
   "not misleading the agent").
4. Keep the repo private until the deadline; open-source at the end (required for prizes).

## Variants, in order

| id | what changes vs the previous | why | status |
|---|---|---|---|
| v1-franzen-faithful | our bundle dataset, Python 3.12 selection, smoke commits | pipeline + own baseline draw | built, pushed 2026-10-12 |
| v2-level-memory | `solved_levels` in the REPL + one line in the level-up prompt; "level restarted" wording; drop the "ignore the bar" line | rellik13's three fixes; cheap; cannot cost tokens | next |
| v3-throughput | REAP-448e NVFP4 target (`boristown/qwen3-8-flash-next-nvfp4-reap-448e`) with the NVFP4 draft, freeing VRAM for KV | more tokens per game is the lever every winner cites | serving recipe for an NVFP4 target exists in rellik13's public notebook (`data/bundles/sirikilohit-cell11.py`, Pennyroyal 2.5.0, `keithtyser/qwen3-8-flash-next-nvfp4` + RadixArk MTP); port after v1/v2 run clean |
| v4-scheduler | fewer slots (8) with longer context, or UCB slices | comparison table: fewest slots + longest context scored best | after v3 |

Decision rule for keeping a change: it stays if its public draw is >= the running mean of our
previous draws minus 1 SD **and** the run log shows the mechanism did what it was meant to
(e.g. more tokens generated, fewer no-op actions). A single higher score is not evidence.

## Timeline given the quota

- Oct 12-16: no GPU commits possible (quota refreshes Oct 17 00:00 UTC). Use the days for the CPU
  pipeline check, v2/v3 preparation, and (if Carson approves the spend) one RunPod validation of
  v1 boot + throughput.
- Oct 17: commit v1 at 00:00 UTC, submit the moment it completes; commit v2 the same day.
- Oct 18 - Nov 2: one submission per day, alternating the best-known config with one new
  mechanism; freeze on Oct 31 and spend the last two days re-submitting the best config.

## What we will not do

- Fine-tune the model (no GPU budget, no time).
- Spend Carson's money on RunPod without a specific question that a Kaggle commit cannot
  answer (see docs/RUNBOOK_RUNPOD.md for the recipe if that changes).
- Submit the paper-track entry from this repo (the sibling workspace `arc_prize_2026/` owns it;
  a real ARC-AGI-3 submission from here makes that entry eligible).
