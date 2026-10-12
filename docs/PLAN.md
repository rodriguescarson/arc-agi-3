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

| id | what changes vs v1 | why | status |
|---|---|---|---|
| v1-franzen-faithful | our bundle dataset, Python 3.12 selection, smoke commits | pipeline + own baseline draw | built; CPU check passed; GPU push blocked by quota until 2026-10-17 00:00 UTC |
| v3-swift | target checkpoint = Swift-1.5 Qwen3.8-Flash-Next (UkisAI post-train: 55-63% fewer thinking tokens, <1% accuracy loss on xhigh), same tokenizer / draft / FR-Spec map; Intel checkpoint attached as boot fallback | more turns per game with zero serving work; the lever every winner cites | built (`kaggle/variants/v3-swift.json`); CPU check kernel `arc3-duck-v3-cpucheck` pushed; Gated-DeltaNet loader patched at boot for Swift's quantised in_proj (source-probed, unit-tested); quantised gated `q_proj` still unverified until the GPU smoke; Intel fallback on boot failure |
| v2-level-memory | `solved_levels()` in the REPL + one line in the level-up prompt; "level restarted" wording; drop the "ignore the bar" line | rellik13's fixes; cheap; cannot cost tokens | built, unit-tested |
| v4-effort-medium | `ARC3_REASONING_EFFORT=medium` (template default is xhigh) | fewer thinking tokens per turn (UkisAI table: -76% for the base model at -3.4 GPQA); one flag | built, unit-tested |
| v5-throughput | REAP-448e NVFP4 target with the NVFP4 draft (rellik13's serving recipe in `data/bundles/sirikilohit-cell11.py`) | frees VRAM for KV; more tokens per game | recipe saved, not ported |
| v6-scheduler | fewer slots (8) with longer context, or UCB slices | comparison table: fewest slots + longest context scored best | after v5 |

Submission order from Oct 17: v1, v3, v2, v4, then repeat the best draw and interleave v5/v6.

Decision rule for keeping a change: it stays if its public draw is >= the running mean of our
previous draws minus 1 SD **and** the run log shows the mechanism did what it was meant to
(e.g. more tokens generated, fewer no-op actions). A single higher score is not evidence.

## Timeline given the quota

- Oct 12-16: no GPU commits possible (quota refreshes Oct 17 00:00 UTC). Use the days for the CPU
  pipeline check, v2/v3 preparation, and (if Carson approves the spend) one RunPod validation of
  v1 boot + throughput.
- Oct 13: automated zero-score test submission (CPU notebook) to prove the submit + rerun path.
- Oct 17: the bot commits v1 at 00:15 UTC, submits it when complete, and pre-commits v3 the same day (`.github/workflows/daily-submit.yml`).
- Oct 18 - Nov 2: one submission per day, alternating the best-known config with one new
  mechanism; freeze on Oct 31 and spend the last two days re-submitting the best config.

## What we will not do

- Fine-tune the model. Not only budget: four teams report zero gain on Flash-Next (SFT with teachers,
  RL on an H200 node) and same-model LoRA gains that did not transfer to the hidden set; our SGLang
  stack has no adapter path. See docs/LANDSCAPE.md "What changed since Oct 1".
- Enable "more thinking": it is already at the template maximum (xhigh, reasoning preserved).
- Spend Carson's money on RunPod without a specific question that a Kaggle commit cannot
  answer (see docs/RUNBOOK_RUNPOD.md for the recipe if that changes).
- Submit the paper-track entry from this repo (the sibling workspace `arc_prize_2026/` owns it;
  a real ARC-AGI-3 submission from here makes that entry eligible).
