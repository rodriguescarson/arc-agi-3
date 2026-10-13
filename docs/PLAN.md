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

**Submission order from Oct 17 (revised 2026-10-14 after the external review):** v6 (Swift + level
memory) x2, v2 (Intel + level memory) x2, v7 (v6 + drain memory) x2, then the variant with the best
**mean** public score; from Oct 31 only the best. If v2 beats v6 by more than 2 points over two draws
each, v7 is replaced by v7i (the same mechanism on the Intel base) automatically. No standalone v1, v3
or v4 draws: v1's distribution is already known from hundreds of public copies (mean 25.77, SD 3.93),
and v4's global medium effort is unproven and plausibly harmful.

**Final two submissions:** if the best variant's mean beats the runner-up by 3 points or more, pick its
two highest-scoring runs (the private score is the better of the two, worth about +0.56 SD over one
run when they are independent). Otherwise pick the best run of each of the top two variants (nearly
the same order-statistic gain, plus a hedge against one variant not transferring).

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

## External review (2026-10-14): what we adopted and what we rejected

We gave `docs/MASTER_BRIEF.md` to an external model. Its direction was sound; several of its factual
claims about our harness were wrong, so each was checked against the code first.

**Adopted**
- Bundle and order changes above (v6 first, two draws per variant, best by mean, finals rule).
- **Drain memory (v7):** at each context drain, a frozen note with the completed levels' winning
  actions and the source of the retained functions is prepended to the first retained message
  (`ARC3_PIN_MEMORY_AT_DRAIN`), and images are stripped from all but the 4 newest image-bearing
  messages (`ARC3_DRAIN_IMAGE_KEEP`). Both act only on the turn the trimmer drops history and are
  stored with the message, so the prefix stays byte-identical until the next drain (unit-tested).
  The existing `ARC3_HISTORY_IMAGE_KEEP` was not used because it strips one more image every turn,
  which moves the cached prefix every turn.
- **Commit telemetry:** the scored rerun's logs are never visible, so the commit writes
  `telemetry.json` (served model, SGLang counters, generated tokens per request, smoke scores).
- **Served-model labelling:** before submitting, the scheduler reads `served_model.txt` from that
  kernel version's commit output and adds `model=swift|intel|unknown` to the submission message; a
  Swift variant that served Intel fails the job so GitHub emails an alert.

**Rejected or changed**
- "Retained functions vanish after a drain and cause NameError loops": wrong. The functions stay
  callable and their signatures are re-announced in every user message; a drain loses only their
  bodies and the level record. Expect a smaller gain than the review's +5 to +10.
- "Fail loud if Swift falls back": would waste a day. v6's fallback is exactly v2 (Intel + level
  memory), so the draw is valid; we label it and alert instead.
- "8 streams and 72 Mamba slots are 15 to 18 % faster": no evidence; fewer streams usually lowers
  aggregate throughput, and Franzen chose 10 after tuning. Not changed without a measurement.
- "11-minute commits": GPU quota is not binding (about 3 h a week planned) and the 34-minute smoke
  run is what produces the telemetry needed to judge Swift. Kept.
- `verify_sim` helper: the sketch did not match our sandbox API, and Franzen found stronger
  verification hints did not help. Deferred.
- Level-1 stall demotion (its v8): the diagnosis is partly right (counters are per level, the B term
  dominates A so depth barely matters, and a game re-prices only at a context trim), but the harness
  tracks no stall signal yet. Next candidate after v7 data.
- `click_candidates()` and a strategy-audit prompt: plausible, unmeasured; later candidates.
- Gated-attention probe for Swift: not needed. Marlin's shape rules hold for every quantised Swift
  projection (inputs 2,560 or 6,144; outputs 12,288, 512, 10,240, 6,144, 2,560) and the generic QKV
  loader already handles packed output dims. The fallback and the label cover the rest.
- The effect sizes in the review are priors, not evidence.
