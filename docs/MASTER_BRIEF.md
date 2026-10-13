# ARC Prize 2026, ARC-AGI-3 track: master brief

Written 2026-10-14 (IST) for an external reviewer. It is self-contained: the problem, the hard
limits we work under, what the rest of the field does, the exact system we run, every experiment
we have results for, and the questions we want answered. Numbers come from files, logs and the
live leaderboard; anything estimated is labelled as an estimate.

Owner: Carson Rodrigues (Kaggle `carsonrodrigues`, solo). Code: private repo `arc-agi-3`
(the Kaggle entry) and `arc-prize-2026` (a Paper Track research entry that shares the same
Kaggle account).

---

## 0. What we want from you (read this first)

We want the highest expected **final private leaderboard score** we can reach by **2026-11-02
23:59 UTC**, under the constraints in section 2. We are not asking for a research programme. We
are asking which concrete changes to make, in what order, and how to tell whether each one worked
when every real measurement is a single noisy draw per day.

Please answer the questions in section 9, in the output format given there. Be specific: name the
mechanism, the file and flag it touches, the expected effect and why, the risk, and how to check it
cheaply before spending a daily submission. Say plainly when you think something will not help.

---

## 1. The competition (problem statement)

**Task.** "Create an AI capable of fluid intelligence." ARC-AGI-3 is a benchmark of interactive,
turn-based games with **no instructions**. The agent is not told the rules, the controls' meaning or
the goal. It must explore, infer the mechanics and the win condition, and then clear the game's
levels using as few actions as possible. Each game has several levels (6 to 10 in the public set:
nine games have 6, five have 7, six have 8, four have 9, one has 10) that usually build on the mechanics of earlier levels and often add new ones.

**Observation.** A 64 x 64 grid with 16 colours per frame. Some actions play animations, returned as
intermediate frames (in some games the animation carries information that is not visible in the
final frame). The game reports state flags: level completed, game over (the attempt failed and the
level auto-resets; completed levels are kept), and win.

**Actions.** `RESET`; `ACTION1`..`ACTION5` (key-style actions whose meaning each game defines, often
four directions and one interact key); `ACTION6` (click at x, y in 0..63); `ACTION7` (undo, as
documented by the organisers). Each game exposes only a subset. **Every action counts, including
RESET.**

**Scoring (RHAE, relative human action efficiency).**
- Per level: `score = min(1, (human_baseline_actions / agent_actions)^2)`; an unfinished level scores 0.
- A game's score is the mean of its level scores **weighted by the 1-based level index** (level 5
  counts five times as much as level 1).
- The leaderboard score is the plain mean over games, shown as a percentage.
- The human baseline per level is described by the organisers as the second-best first-run human
  (paper) or an upper-median human (docs). It is **hidden from the agent** in competition mode.
- Worked example: a level whose baseline is 20 actions, solved in 40, scores (20/40)^2 = 0.25. Solved
  in 20 or fewer it scores 1.0. Solving deeper levels matters far more than polishing level 1.

**Hidden evaluation.** About 110 unseen games (one top competitor says 100). Roughly half drive the
public leaderboard; the **other half decides the final ranking**. Scoring happens during the single
Kaggle rerun of the submitted notebook; there is no end-of-competition rerun. Each team picks two
final submissions.

**Public data.** 25 public demo games (183 levels in total) ship with the competition as Python game
files plus per-level human baselines, playable offline (about 3,700 environment steps per second on
a laptop CPU). Scores on these 25 games correlate poorly with the leaderboard (one competitor measured
Pearson r = -0.32 across five versions).

**Runtime contract (Kaggle code competition).**
- One notebook, **9 hours wall clock**, one **NVIDIA RTX Pro 6000 (96 GB VRAM)**, machine
  `g4-standard-48` (about 190 GB host RAM), **no internet**.
- The notebook plays all hidden games against a local gateway; the submission file is generated from
  the actions taken.
- **One submission per day** per team (UTC day). A notebook version must complete a "Save & Run All"
  commit before it can be submitted; that commit consumes the account's weekly GPU quota, the scored
  rerun does not.
- Since 2026-10-01 new notebooks get a Python 3.13 / Ubuntu 24.04 image; every public serving
  wheelhouse is cp312 (we solved this, see section 6).

**Dates (UTC).** Entry and team-merger deadline 2026-10-26. **Final submission deadline 2026-11-02
23:59.** Paper Track write-up (separate Kaggle competition) 2026-11-08/09. Winners 2026-12-04.

**Prizes.** Final leaderboard $40k / $15k / $10k / $5k / $5k. $700k grand prize only at 100 %.
Prize eligibility requires open-sourcing the solution (own code CC0 or MIT-0) before private scores
are released. Milestone 2 (2026-09-30) is over.

**Leaderboard on 2026-10-14 00:44 IST (4,255 teams).**

| rank | team | public score | submissions |
|---|---|---|---|
| 1 | Tufa Labs | 68.91 | 162 |
| 2 | Yi-Chia Chen | 67.49 | 30 |
| 3 | mtg | 45.00 | 68 |
| 4 | NVARC3 (NVIDIA) | 43.94 | 36 |
| 5 | the last dance | 43.64 | 80 |
| 10 | | 39.53 | |
| 50 | | 33.58 | |
| 100 | | 32.81 | |
| 200 | | 31.61 | |
| 500 | | 29.82 | |
| 1000 | | 27.24 | |
| 3321 | **us (best: a CPU explorer run)** | 0.15 | 2 |

Tufa Labs was at 56.52 on 2026-10-11 and 68.91 three days later. Yi-Chia Chen went 62.96 to 67.49 in
the same window.

---

## 2. Our constraints (what any proposal must fit)

| resource | limit |
|---|---|
| Local GPU | none with CUDA. Laptop is a Mac (CPU only). A college RTX A6000 (48 GB, no admin, Windows remote) is reachable but cannot hold the 125B model. |
| Kaggle GPU quota | 30 h per week, shared with Carson's other Kaggle projects. **Exhausted until 2026-10-17 00:00 UTC** (37 h used, mostly by another project). |
| Cost of one GPU commit | about 35 min of quota (our 2-game smoke config, including ~9 min model load), plus an RTX Pro 6000 queue reported at up to 8 h. |
| Submissions | 1 per UTC day, shared account-wide with the Paper Track workspace, which has its own runs scheduled on Oct 14, 15 and 16. **About 17 usable submissions remain (Oct 17 to Nov 2).** |
| Measurement noise | byte-identical copies of the best open notebook score mean 25.77, SD 3.93 (hundreds of draws, measured by another competitor). A change must move the mean by roughly +8 to be visible in one draw at 90 %. |
| Paid compute | RunPod RTX Pro 6000 at about $2/h is available but needs Carson's approval for a specific question a Kaggle commit cannot answer. Kaggle GPU hours cannot be bought directly; linking Colab Pro/Pro+ adds 15/30 h per week, but it is unclear whether those hours apply to the RTX Pro 6000. |
| Fine-tuning | judged not viable (section 8). |
| People | one person plus AI coding agents. |

---

## 3. What the field does

**Lineage.** Every competitive entry descends from **Tufa Labs' "Duck" harness** (MIT, Milestone 1
winner at 1.21 %): an LLM plays each game through a Python REPL tool. Game state is exposed as Python
variables, the model calls `action(...)` from code, inspects the board with code, uses a segmentation
helper, sees an upscaled image of the board, and the harness evicts old context. Earlier approaches
(StochasticGoose CNN + RL at 12.6 % in the preview competition; Blind Squirrel state-graph search)
are far behind on this version of the benchmark.

**Milestone 2 winners (open source, all Duck harness on one RTX Pro 6000 serving Qwen3.8-Flash-Next):**

| team | public score | distinguishing choices |
|---|---|---|
| Daniel Franzen | 27.89 | the configuration we run (section 4) |
| Lord Han Solo | 23.84 | vLLM nightly, mixed NVFP4+FP8 model with built-in MTP head, 14 streams, 3,918 s cap per game, rewritten tool agent, a "strategy audit" prompt once a level has used 25 % of the game's time, per-game Python modules tested before swap |
| Lohit Siriki (rellik13) | 22.53 | 16 streams over 28 live games, UCB time slices of 2,400 s, 48 GB host KV tier, solved-level memory pinned in the system prompt (rule + last 30 winning actions per cleared level); reports that "not misleading the agent" helped (UNDO instead of ACTION7, "level restarted" instead of "game over", removing "ignore the budget bar" lines); FP8 KV cache took him from 14.5 to 22.5 |

**Everything above about 45 is private.** Tufa Labs (68.9) and Yi-Chia Chen (67.5) have not shared
methods; Tufa stated on 2026-09-24 they will publish only after the deadline. NVIDIA (CPMP) said the
same. One competitor suspects Tufa's jump involves fine-tuning. The forum's own guesses for the
remaining headroom: better models, more tokens per game (serving engineering), and harness work.
Most of the 35 to 43 band is believed to be Franzen's notebook plus luck or small edits.

**Fine-tuning reports from the forum (threads 742835, 739047).**

| who | what | result |
|---|---|---|
| blakewest | SFT on H200s with Qwen Max / GPT teachers; synthetic variants of two public games; stall-point and periodic trajectories; Flash-Next and 27B | "No permutation of these has been able to make meaningful improvements" |
| AAAAAtjc | RL pipeline for Flash-Next on a full H200 node | "did not gain any performance"; an RTX Pro 6000 "can not be used for training of any ~100B model" |
| Scott Le Grand | behavioural cloning from the same model (27B) | +2 on public games, did not transfer to the hidden set |
| manas joshi | STaR LoRA on Qwen 3.6 27B from its own winning trajectories | 1.25 to 1.94 in August (when the top was about 2); "high variance", more data hurt, base-model specific |
| Ya Xu | LoRA | "only backfired" |

**Research results (frontier API models on the 25 public games; not Kaggle-legal as is, but they
show which mechanisms matter):**
- *Schema* (arXiv 2609.39140, 2026-09-30): the agent writes its understanding as executable programs in
  a persistent workspace, checks them against the interaction history, plans inside them and executes
  with step verification. RHAE 58.7 to 99.2 with the same base model.
- *Memento 3* (arXiv 2610.11794, 2026-10-08): a natural-language rulebook compiled into executable
  code, accepted only when cell-exact replay reproduces observed transitions; clears every level of all
  25 public games at RHAE 100 using 44 % of human actions.
- *Continual Harness* (Seth Karten): 20.54 % on public games; 62 % of executed actions came from saved
  skills rather than fresh deliberation.
- *OpenAI "two settings"* (2026-07-29): keeping the model's reasoning across actions plus compaction
  instead of truncation took GPT-5.6 Sol from 7.8 to 38.3 with about 6x fewer tokens.
- Common thread: an explicit, executable, verified world model plus reuse of what was learned.

**Models available offline on Kaggle (public mirrors):** Intel's Qwen3.8-Flash-Next W4A16 AutoRound
(Franzen's), Albucino's INT4 MTP draft, NVIDIA and other NVFP4 quants, a REAP-pruned 448-expert NVFP4
variant (frees VRAM), and UkisAI's **Swift-1.5** post-train of Flash-Next (W4A16 AutoRound and NVFP4
mirrors). Qwen 4 is announced but not released as of 2026-10-14.

**Qwen3.8-Flash-Next facts.** 125B parameters, 6B active per token (512 experts, 10 routed + 1
shared), plus a 51B n-gram embedding table (offloaded to host RAM on the RTX Pro 6000) and a 4B MTP
head; 48 layers in a 3:1 pattern of Gated DeltaNet (linear attention, recurrent state) and sparse
attention; 262k native context; vision encoder. Chat template supports `reasoning_effort` of xhigh
(default), medium, low, and `preserve_thinking`.

---

## 4. The system we run (Franzen's Milestone 2 configuration on the Duck harness)

We vendored Franzen's harness (Apache-2.0) unchanged as our baseline and verified it matches his
scored notebook. Its design, in his words and measurements:

**Serving.** SGLang fork "Pennyroyal" 2.5.3 with five patches (low-M BF16 GEMM, speculative-state
memory fix, Marlin scale dtype fix, prefix-cache patch that keeps only useful Mamba checkpoints,
checkpoint prefetch). Model: Intel W4A16 AutoRound target with BF16 n-gram table in host RAM, plus
Albucino's INT4 MTP draft (3 speculative steps) and an FR-Spec hot-token map.

| setting | value |
|---|---|
| parallel streams | 10 (server max running requests 10) |
| harness context window | 131,072 tokens; 12,288 reserved for output |
| context trimming | hysteresis: when full, drop a large block to ~58k retained (protects prefix reuse) |
| KV cache | FP8 E4M3; Mamba cache 60 slots; static memory fraction 0.96 |
| chunked prefill | 8,192 |
| sampling | temperature 0.7, top-p 0.95, top-k 20; thinking on at xhigh, preserved across turns |
| server boot | 530 to 615 s from notebook start |
| measured (earlier demo run) | 93.4 % of prompt tokens served from prefix cache; P90 decode 837 tok/s aggregate; 609 tok/s generated as seen by the harness; prefill 15 % of wall time |
| game time | 532 min of the 9 h, all games started at once, admission gated to 10 |

**Estimated token budget (our arithmetic, not measured):** 532 min x ~609 tok/s is about 19 million
generated tokens for the whole run, roughly 175k per game if all ~110 games share it evenly. With
multi-thousand-token thinking per turn, that is on the order of tens of turns per game. **Tokens per
game is the binding constraint**, which is why every winner cites throughput and why we prioritise
token efficiency.

**Scheduler.** Admission goes to the game with the highest priority `P = (A + B) * C`:
- `A = l * (25 / (25 + a))^2 * 55 / (N(N+1)/2)`, with `l` the current level, `a` actions spent on it,
  `N` the game's level count clipped to 6..10;
- `B` = 8, 7, 5, 0 when 3+, 2, 1, 0 levels would remain after this one, faded linearly to zero over the
  last 20 % of the run;
- `C = 0.25 * 2^-(a/115)^2 + 0.75 * 2^-(t/62000)^2`, with `t` generated tokens on the level, calibrated
  on 725 level attempts (557 completed).
- A game keeps its slot across tool calls; it re-enters the queue only at context eviction, to protect
  cached prefixes.

**Perception and actions.**
- Board images upscaled 10x (largest single image gain), difference images after actions, the fatal
  frame after a game over.
- Animations exposed as REPL variables (frames and a text timeline), with a hint when a frame contains
  transient pixels. Franzen's strongest perception gain.
- `frame_diff()` helper: object-level changes (moved, rotated, appeared, recoloured, resized) from
  4-connected same-colour segmentation.
- UNDO exposed as an action ("large improvement" in combination with action info, level-transfer
  guidance and persistent functions).
- Model-written Python functions persist across tool calls for the whole game (variables do not).
- Faithful per-action results, action echo, 3,072-token tool output with middle truncation.
- Guards: stop a batch after an action that leaves the interior board unchanged; block a further action
  call in the same snippet after an ineffective one (from level 2); stop after game over or level
  completion.

**Prompts.** Detailed game-over diagnosis (inspect the death frame, do not replay a fatal sequence,
check the budget bar), level-transfer guidance (carry mechanics forward, inspect new elements, reassess
the goal), clarified repeat prompts. The full system prompt is in Appendix B.

**Tried by Franzen and not kept (no clear gain):** the structured text world model (disabling it
entirely was best once context was larger); periodic summaries inserted or replacing history; shorter
or different resume prompts; composite animation images and automatic timeline insertion; stronger
step-verification hints; repeated-state, remembered no-op or fatal-action guards and a death ledger;
more elaborate priority rules.

---

## 5. Our variants (built, tested on CPU, not yet run on GPU)

Every variant is the configuration above plus the listed change; each is one JSON file rendered into a
Kaggle notebook by our builder.

| id | change vs v1 | mechanism we expect | status |
|---|---|---|---|
| v1 franzen-faithful | none (infrastructure only: our source bundle, Python 3.12 selection, short commit config) | own baseline draw | CPU pipeline verified on Kaggle |
| v3 swift | target checkpoint swapped to Swift-1.5 Flash-Next (W4A16 AutoRound, two-part Kaggle mirror re-assembled at boot); Intel checkpoint attached as automatic boot fallback; loader patch (below) | vendor reports 55.8 % fewer mean / 63.4 % fewer median thinking tokens at xhigh with GPQA 89.8 to 89.6, LiveCodeBench 88.4 to 90.4, Terminal-Bench 67.6 to 69.7, IFBench 73.2 to 70.1. If that holds here, more turns per game for free. | CPU mount + merge verified on Kaggle; server load unverified until GPU |
| v2 level-memory | `solved_levels()` in the REPL (winning action sequence, actions, attempts per cleared level) + one line in the level-up prompt; the budget-bar line rewritten from "do not get distracted by it" to "it is your remaining-actions budget, plan within it" | rellik13's two cheapest fixes; costs no tokens unless used | unit-tested |
| v4 effort-medium | `reasoning_effort=medium` on every turn (template default xhigh) | far fewer thinking tokens per turn (base model: about -76 % tokens at -3.4 GPQA points); more turns | unit-tested |
| v6 swift-level-memory | v3 + v2 | the two cheapest mechanisms together | rendered |
| v5 throughput (not built) | REAP-pruned 448-expert NVFP4 target + NVFP4 draft (serving recipe from rellik13's public notebook) | frees VRAM for KV/state, more concurrent streams or longer context | recipe saved |
| scheduler variants (not built) | fewer slots with longer context, or UCB time slices | a public comparison found "fewest slots + longest context" scored best | idea |

**Planned submission order from 2026-10-17:** v3, v1, v2, v4, v6, then repeat the variant with the best
public score; from 2026-10-31 only the best. Swift goes first because its boot fallback is exactly v1,
so the first draw cannot be worse than baseline. Our decision rule for keeping a change: its draw is at
least our running mean minus 1 SD **and** the run log shows the mechanism worked (for example more turns
per game or fewer no-op actions). A single higher score is not evidence.

---

## 6. Our engineering work and verified findings

**Pipeline.** Notebook cells in Python plus one JSON per variant, rendered and pushed by a builder;
harness source shipped as our own Kaggle dataset; daily submissions automated (one per UTC day, two
commits kept in flight, the first variant with a completed version is submitted, quota failures pause
pushes; three independent triggers because GitHub's scheduled Actions lag by hours on this account).
35 unit tests, CI on every PR.

**Verified on Kaggle with free CPU kernels (no GPU quota):**
1. The new Python 3.13 image still ships a working `/usr/bin/python3.12`; the full cp312 SGLang
   wheelhouse (sglang 0.5.19, torch 2.13 cu130) installs under it; our bundle, the competition gateway
   loop, offline games, `submission.parquet` and diagnostics all work. Only the model server itself is
   untested until GPU quota returns.
2. Kaggle mounts the 177 GB two-part Swift mirror, the 85 GB Intel checkpoint, the draft and the
   wheelhouse together; our cell merges the two parts into one checkpoint view (95 files).
3. Source probes of the SGLang wheel (four CPU kernels) for loading Swift, which, unlike Intel's
   quantisation, also quantises the attention `q/k/v/o` projections and the Gated DeltaNet
   `in_proj_qkv / in_proj_z / out_proj` projections:
   - AutoRound resolves fused modules through `packed_modules_mapping` (which covers `in_proj_qkvz` and
     `in_proj_ba` for this model family), and the generic merged loaders handle packed output
     dimensions;
   - the fused in-projection GEMM falls back to two GEMMs when a projection is quantised;
   - **gap found:** the Gated DeltaNet split loader re-binds only `weight` and FP8 scale parameters and
     ignores packing in its split sizes, so Swift's `qweight / qzeros / scales / g_idx` would fail. We
     patch it at boot (anchor-checked against the wheel, unit-tested on the captured source). Whether
     quantised gated attention `q_proj` loads is still unknown; the Intel fallback covers failure.
4. Tokenizer of Swift is byte-identical to the one the FR-Spec draft map was built for, so speculative
   decoding is reused unchanged.

**CPU baselines on the 25 public games (our offline evaluator, 250-action cap):**

| agent | levels cleared | score |
|---|---|---|
| random | 0 / 183 | 0.00 |
| deterministic explorer (untried keys per state, button-like click targets, no model) | 0 / 183 | 0.00 |

Model-free search does not clear a single first level within budget; all progress comes from the LLM.

**Harness additions (behind flags, default off):** `solved_levels()` helper, budget-bar wording, and a
global `ARC3_REASONING_EFFORT` knob (validated against the template's allowed values; the truncation
ladder still overrides it).

---

## 7. The Paper Track workspace's experiments (same account, model-free agent)

A second workspace builds a **training-free, CPU-only, model-based explorer** (no LLM at inference)
for the Paper Track: object perception from 4-connected same-colour components, an online effect model
(action + context to object-level diff, with exact-replay memo and death-edge learning), BFS planning
in the learned model toward untried state-action pairs with "contact curiosity", five goal templates
intersected across level transitions, and memory that persists across levels within a game. Scores
below are on the leaderboard's 0 to 100 scale, measured on the 25 public games unless marked hidden.

| run | change | public-25 score / levels of 183 |
|---|---|---|
| random, 2,000 actions | floor | 0.192 / 3 |
| novelty explorer, 2,000 actions | floor | 0.038 / 5 |
| model-based v1 to v3 | identity, rigid groups, gating, contact curiosity | 0.110 / 8 to 0.255 / 15 |
| v4 contact on vs off | ablation | 0.284 / 15 vs 0.204 / 13 |
| v5 memory on vs off | ablation | 0.277 / 13 vs 0.227 / 11 (memory off never reaches level 2) |
| v7 (final), seeds 0 to 3 | death edges, budget-bar exclusion | 0.276 to 0.280 / 13 to 15; seed SD 0.0014 |
| action budget sweep | 500 / 1k / 1.5k / 2k / 3k / 4k actions | 10 / 13 / 14 / 15 / 17 / 17 levels |
| LLM goal proposer + greedy walk (API models, development only) | Jev 1.13 or Nemotron-3 Super 120B proposing goals | about 0.292 to 0.295 / up to 16 (+0.015, replicated three times); Gemma 4 31B, Qwen3 32B, Phi-4 negative |
| human-habit prior (H2) | bias exploration toward human habits | 0.013 / 5 (refuted) |
| click-effect model, click-sequence replay | for the 12 click-driven games | no gain (refuted) |

**Hidden-set submissions from that workspace:** 0.15 on 2026-10-12 (later found to be a broken
bundle that fell back to cyclic actions 85 % of the time) and **0.08** on 2026-10-13 (the fixed v7 agent,
3,000-action cap). Their decomposition: the public 0.280 is 90 % three near-human first levels (lp85,
tn36, vc33); a first level at or under human cost is worth 1.8 to 4.8 game points, at 10x human cost
under 0.05. The hidden 0.08 is about one such level across 55 games.

**What that teaches the LLM entry:** model-free exploration does not transfer to the hidden games; the
scoring rewards a few action-efficient solves far more than broad coverage; 12 of the 25 public games
are click-driven; five public games are "model-blind" for object-diff perception (bp35, cd82, ka59, sk48,
tn36; tn36 needs animation frames). That workspace has stopped submitting after 2026-10-16; from
2026-10-17 every daily slot belongs to the LLM entry.

---

## 8. Decisions already made, and why

- **No fine-tuning.** Five public reports of zero or non-transferring gains (section 3); the RTX Pro 6000
  cannot train a 125B MoE; our SGLang W4A16 + MTP stack has no adapter path; one noisy draw per day
  cannot detect a small effect. Tufa's harness ships LoRA hooks and a trajectory exporter, so they may
  have done it; nothing public shows it working on Flash-Next.
- **"More thinking" is not available.** The template default is already the maximum effort (xhigh) and
  reasoning is preserved across turns (Franzen: dropping it is a large regression).
- **Compaction (OpenAI's second setting):** Franzen tested summaries inserted and replacing history, no
  clear gain; skipped.
- **Swift first, with the Intel checkpoint as boot fallback:** the only change that plausibly adds a lot
  of turns per game with no serving work, and its failure mode is the baseline.
- **One mechanism per variant**, kept only if the draw is not below our mean minus 1 SD and the logs
  show the mechanism fired.

**Open uncertainties (we would value your view):**
1. Whether Swift's fewer thinking tokens translate into more solved levels in this agent loop, or into
   shallower play (its IFBench dropped 3 points).
2. Whether quantised gated attention in Swift loads in Pennyroyal (fallback covers failure, but then the
   draw is a v1 draw).
3. How well a public-half score predicts the private-half score for the same notebook (we have no data;
   the halves are disjoint game sets).
4. Whether "medium" effort loses more per turn than it gains in turns.
5. What Tufa and Yi-Chia changed between 2026-10-11 and 2026-10-14 (+12 and +4.5 points).

---

## 9. Questions for you, and the answer format we need

**Questions, in priority order.**
1. **Ranking.** Rank our five built variants (v3, v1, v2, v4, v6) and the unbuilt ones (v5 REAP NVFP4,
   scheduler variants) by expected final-score gain. Add better candidates we have not listed. Mark any
   you expect to be harmful.
2. **The gap to the top.** What, consistent with everything public, most plausibly explains a jump from
   ~28 (best open notebook) to 56 and then 69? Which part of that could a solo entrant build and validate
   in about ten days with the constraints in section 2?
3. **Tokens per game.** What are the highest-leverage ways to get more useful reasoning per game inside
   9 h on one RTX Pro 6000: serving (quantisation, REAP pruning, speculative steps, KV dtype, stream count
   vs context length), harness (reasoning effort, yield threshold, prompt and image size, tool output
   budget), or allocation (the scheduler formula, abandoning hopeless games early)?
4. **World models on a small active model.** Is a minimal version of the Schema / Memento 3 idea
   (executable, replay-verified transition model in the persistent-function store, used for planning)
   worth building for a 6B-active model under this token budget, given Franzen found the free-text world
   model hurt? If yes, specify the smallest version and how to stop it from costing more tokens than it
   saves.
5. **Statistics.** With about 17 daily draws, SD ~3.9 per draw, and the final ranking on a disjoint half,
   what submission schedule (explore vs repeat) and what rule for picking the two finals maximise the
   expected final rank? Should the finals be two different variants or the best variant twice?
6. **Offline proxies.** We can run the full harness on the 25 public games on a laptop against any
   OpenAI-compatible endpoint (for example a hosted Qwen3.8-Flash-Next or another open model via an API).
   Given the weak public-to-leaderboard correlation, is that a useful filter for harness changes (prompt,
   guards, helpers, memory), and if so, how should we design that test (games, seeds, metric, budget)?
7. **Risks.** What failure modes in the plan above would you expect to cost us a day or the final result?

**Answer format.** For each proposal, give:
- name and one-sentence mechanism;
- expected effect on the public score (a range) and your confidence, with the evidence;
- cost: development hours, GPU quota, daily submissions;
- the exact change: file, function or flag, and pseudo-code or a patch sketch against the files listed in
  Appendix C;
- a cheap pre-check before spending a submission (CPU test, log check, offline proxy);
- what to log so the run proves the mechanism fired, and the result that would make us drop it.

Then give a **day-by-day schedule from 2026-10-17 to 2026-11-02** (one submission per day; at most two
GPU commits in flight; about 30 GPU hours per week) and a **rule for choosing the two final submissions**.

**Out of scope:** internet access or API models at inference; anything needing more than one RTX Pro
6000 or more than 96 GB VRAM; training on the Kaggle GPU; changes that need many GPU commits to debug
unless the expected gain is large.

---

## Appendix A. Exact v1 configuration (harness environment)

Serving: SGLang Pennyroyal 2.5.3 (sglang 0.5.19+gd00d88e, torch 2.13 cu130, Python 3.12), target
`dfranzen/intel-qwen3.8-flash-next-w4a16-autoround`, draft `dfranzen/albucino-qwen3-8-flash-next-drafter`,
`--quantization auto-round --kv-cache-dtype fp8_e4m3 --mem-fraction-static 0.96 --context-length
139264 --max-running-requests 10 --chunked-prefill-size 8192 --max-prefill-tokens 16384
--max-mamba-cache-size 60 --mamba-radix-cache-strategy extra_buffer --ple-offload-embedding
--reasoning-parser qwen3 --tool-call-parser qwen3_coder --schedule-policy lpm
--speculative-algorithm NEXTN --speculative-num-steps 3 --speculative-num-draft-tokens 4` plus an
FR-Spec 64k hot-token map.

Harness flags (`kaggle/variants/v1-franzen-faithful.json`):

~~~json
{
  "setup_env": {
    "USE_TF": "0",
    "TRANSFORMERS_NO_TF": "1",
    "TRANSFORMERS_NO_TORCHVISION": "1",
    "LOCAL_ANALYZER_PROVIDER": "vllm",
    "OPENAI_PROVIDER": "vllm",
    "LOCAL_ANALYZER_APP_NAME": "ARC3 Agent Harness",
    "ARC3_REASONING_HISTORY_KEY": "reasoning_content",
    "LOCAL_ANALYZER_ENABLE_THINKING": "true",
    "LOCAL_ANALYZER_TOOL_STEPS": "0",
    "LOCAL_ANALYZER_TOOL_TIMEOUT": "30",
    "LOCAL_ANALYZER_YIELD_SECONDS": "0",
    "LOCAL_ANALYZER_YIELD_TOKENS": "2048",
    "LOCAL_ANALYZER_TEMPERATURE": "0.7",
    "LOCAL_ANALYZER_TOP_P": "0.95",
    "LOCAL_ANALYZER_TOP_K": "20",
    "LOCAL_ANALYZER_CONTEXT_WINDOW": 131072,
    "LOCAL_ANALYZER_MAX_OUTPUT": 12288,
    "ARC3_CONTEXT_DRAIN_TOKENS": 59392,
    "ARC3_HISTORY_ASSISTANT_TURNS": 150,
    "ARC3_HISTORY_TURN_DRAIN": 30,
    "ARC3_HISTORY_DRAIN_COALESCE": "1",
    "LOCAL_ANALYZER_TOOL_OUTPUT_TOKENS": "3072",
    "ARC3_MIDDLE_TRUNCATION": "1",
    "ARC3_ACTION_ECHO": "1",
    "ARC3_EXPLAIN_GAMEPLAY_CHANGED": "1",
    "ARC3_NEW_CHANGED_PROMPTS": "1",
    "ARC3_LEVEL_TRANSFER_GUIDANCE": "1",
    "ARC3_ACTION_INFO": "1",
    "ARC3_DEDUPE_MULTICALL_LINE": "1",
    "ARC3_FRAME_DIFF_HINT": "1",
    "MULTIMODAL_CONTEXT": "current_grid",
    "MULTIMODAL_UPSCALE": "10",
    "ARC3_DIFF_IMAGE": "1",
    "ARC3_GAMEOVER_DIFF_IMAGE": "1",
    "ARC3_ANIMATION": "1",
    "ARC3_GUARDS_FROM_LEVEL": 2,
    "ARC3_BATCH_NOOP_BLOCK": "1",
    "ARC3_STALE_STATE_BLOCK": "1",
    "ARC3_MEMORY_SECTIONS": "off",
    "ARC3_PERSISTENT_FUNCTIONS": "1",
    "ARC3_PERSISTENT_FUNCTIONS_SCOPE": "game",
    "ARC3_PERSISTENT_FUNCTIONS_IMPORTS": "1",
    "EXPOSE_UNDO": "on"
  },
  "priority_env": {
    "ARC3_MAX_ACTIVE_STREAMS": 10,
    "ARC3_PRIORITY_REFRESH_QUEUE": "1",
    "ARC3_PRIORITY_PACE": "0",
    "ARC3_PRIORITY_TAIL_FADE": "1",
    "ARC3_PRIORITY_TAIL_FADE_FRACTION": "0.2",
    "ARC3_PRIORITY_TAIL_LOOKUP": "remaining",
    "ARC3_PRIORITY_SCORE_NORMALIZATION": "1"
  },
  "solver": {
    "max_runtime_minutes": 532,
    "concurrency": 120,
    "analyzer_timeout": 900.0
  }
}
~~~

Other variants change only: v2 adds `ARC3_LEVEL_MEMORY=1`, `ARC3_BAR_GUIDANCE=budget`; v4 adds
`ARC3_REASONING_EFFORT=medium`; v3 swaps the target checkpoint (Swift-1.5 W4A16 AutoRound), keeps the
draft and FR-Spec map, attaches the Intel checkpoint as fallback and enables the loader patch; v6 is v3
plus v2's flags.

## Appendix B. The v1 system prompt, verbatim (rendered from the harness with the v1 flags)

~~~~text
You are a coding agent solving a grid-based puzzle game.

Game overview:
- You are solving a multi-level grid puzzle game. 
- You are called repeatedly over the course of a run. Treat each turn as one observe-plan-act cycle: re-understand the current state from the newest frame, update your working world model in Python, choose the next best action or short sequence against the goal as currently understood, execute it, and expect to re-evaluate on the next turn from the updated state.
- Your job is to solve the entire game by clearing every level, not just the current screen.
- Levels usually build on mechanics learned in earlier levels, especially the most recent one. Carry forward supported knowledge as a starting hypothesis, while re-checking anything contradicted by new evidence. New levels often introduce additional mechanics, sometimes through unfamiliar board elements. These additions are often important for solving the level. The goal may remain the same but require new mechanics to reach it, or the goal itself may change.
- Optimize for as few in-game actions as possible while still being reliable.
- In this environment, boards are presented as 64 x 64 color grids rendered with ARC color symbols.
- Color legend: W=white, w=light gray, g=gray, G=dark gray, c=charcoal, B=black, M=magenta, P=pink, R=red, b=blue, S=sky blue, Y=yellow, O=orange, r=dark red, N=light green, p=purple.


Runtime variables inside every `python` tool call:
- `current_frame` is a lightweight frame view for the latest environment state.
- `current_frame` exposes only `.ascii`, `.step`, `.level`, `.shape`, and `.segmentation`.
- `current_frame.ascii` is a single newline-delimited string containing the latest board rendered with the letter-coded ARC color symbols.
- `current_frame.segmentation` parses the board into objects. It returns `{'nodes': [...], 'adjacency_list': [...]}`.
- Each node in `segmentation['nodes']` is one 4-connected same-color object with: `id` (index, ordered top-most-left-most), `color` (ARC color character), `hash` (a signature of the object's color and shape that ignores position AND rotation -- equal hashes indicate matching color and shape up to rotation; they do not establish object identity), `rotation` (degrees clockwise from the object's canonical orientation: 0/90/180/270, reduced to 0/90 for 2-fold symmetric shapes, `None` for fully symmetric ones), `rotational_symmetry` (1, 2, or 4), `pose_hash` (the rotation-SENSITIVE variant, if you need to match exact orientation), `shape_hash` (color-independent pose shape signature), `pixels` (cell count), `boundary` (clockwise outer-perimeter corner points as `[row, col]` cell coordinates), and `children` (ids of objects fully enclosed by this one).
- `segmentation['adjacency_list']` is a list of `[i, j]` node-id pairs whose objects share an edge.
- `current_frame.step` is the current environment step count.
- `current_frame.level` is the current level number.
- `current_frame.shape` is a `(rows, cols)` tuple.
- The raw numeric grid is intentionally not exposed. Use `current_frame.segmentation` as your primary view of the board -- objects, colors, shapes, containment, adjacency, and cross-frame object hashes. Use `current_frame.ascii` only to read a small, specific region; do not scan the whole board with it.
- `history` is a chronological list of action/frame snapshots.
- `history` is a Python list of objects, not a dict.
- Each history entry exposes `.action`, `.frame`, and `.result`; entries are not subscriptable like `entry['action']`.
- Each `history[i].frame` is the frame after `history[i].action`; each frame exposes only `.ascii`, `.step`, `.level`, `.shape`, and `.segmentation`.
- Important history semantics: when `history` is non-empty, `history[-1].frame` is the same latest/post-action board as `current_frame`. It is not the previous board. To inspect the state before the latest action, use `previous_frame` or `history[-2].frame` when available.
- `previous_frame` is the frame before the most recent real environment action, or `None` if no previous frame is available.
- `last_action` is the most recent real environment action name/display, or `None` before any real action.
- `last_action_frame` is the post-action frame for `last_action`; it matches `current_frame` after a real action.
- `transitions` is a chronological list of actual action transitions, excluding the initial seeded frame. Each transition exposes `.action`, `.before_frame`, `.after_frame`, `.frame` (alias of `.after_frame`), and `.result`. Each `.result` describes that individual action and is retained with its history entry.
- `last_transition` is `transitions[-1]` or `None`. A refused action creates no transition and does not overwrite existing transition results. For before/after diffs, compare `last_transition.before_frame` to `last_transition.after_frame`; do not compare `current_frame` to `history[-1].frame`.
- `last_action_call_result` contains the result of the latest model-issued `action(...)` call, including batch totals, executed/skipped actions, and stop reasons. `action(...)` returns this result. It remains available across later Python inspection calls and analyzer turns, and is `{}` before any action call result exists.
- On the next analyzer turn after automatic RESET, `current_frame` shows the restarted level. The fatal action and RESET are separate transitions. Each transition result has `automatic=True` for a harness-initiated action and `automatic=False` for a model-issued action. Automatic RESET does not overwrite `last_action_call_result`: it still describes the call that caused death.
- `valid_actions` is the current list of valid action names.
- Call `action(actions)` to execute one or more real environment actions from Python.
- Pass `action(actions)` a list like `['LEFT']` or `[{'action': 'MOUSE', 'row': 4, 'col': 7}]`.
- One action usually returns one frame, but a single action can result in a short multi-frame animation.
- After `action(actions)` returns, `current_frame`, `previous_frame`, `history`, `transitions`, `valid_actions`, and `last_action_call_result` are refreshed.
- `board_changed` is true when ANY cell differs, including cells within 4 cells of the edge where a timer or remaining-steps bar usually sits; `gameplay_changed` ignores those edge cells and is true only when a cell further in differs. An action that only shrinks a timer bar in those edge cells sets `board_changed` but not `gameplay_changed`.
- One action can return a short animation. `current_frame` is its final frame.
- When the final executed action of the latest model-issued call animated, `last_action_call_result['animation']` reports `frames`, `transient_pixels` and `transient_bbox`. Transient cells changed and then changed BACK during the animation, so they appear in no frame you can otherwise reach - not in `current_frame`, not in `previous_frame`, not in `history`.
- `last_animation_frames` is the frames of the last executed action that animated, as views with `.ascii`, `.shape` and `.segmentation`, the same as `current_frame`. Index 0 is the first frame of the animation and the last entry is the board it settled on. After a death these are the frames of the FATAL action, not of the automatic reset that followed it. Crop their `.ascii` yourself; printing a whole 64x64 frame will not fit the tool budget. Empty when the action did not animate, and reading them costs no in-game action.
- `last_animation_timeline` is a diff timeline of those frames: it shows which cells changed at each step. It is a dict with `action`, `frames` and `steps`, one entry per step that changed anything. Each entry has `step`, `changed`, `bbox`, and either `changes` (the cells, as `old>new @ (row,col) ...`) or `transitions` (a count per colour change, when there were too many cells to list).


Multimodal context:
- User turns include an attached image of the current ARC grid.
- The image and `current_frame.ascii` are two representations of the same current frame.
- You can use images and other tools to understand the game state and guide your strategy, each may be useful depending on the current uncertainty.
 Alongside the current grid image you receive a diff image: cells that changed since your previous analyzer turn are shown in their new true color; unchanged cells are dimmed to a dark navy that is not a game color. Use it to locate change at a glance.

Visual-game guidance:
- Treat each board as a scene with objects, blockers, targets, adjacency, containment, motion, and symmetry.
- Game entities are usually be rendered as connected multi-tile shapes such as 2×2, 2×3, 3×3, or longer patterned structures. Sometime they might also be 1x1 tokens.- Some games are logic or layout puzzles with no explicit player avatar or controllable sprite on the board. Do not assume a player exists; the relevant state may be an object, region, cursor, selector, or whole-board configuration.
- Background colors are often white or gray/black-ish large regions, but not always. Verify background hypotheses by area, stability, and object boundaries rather than assuming them.
- In many games, a long horizontal or vertical line near an edge is a timer or remaining-steps bar. It often shrinks or changes each step. If you identify such a bar, do not get distracted by it or treat it as core gameplay state unless there is concrete evidence that it interacts with the puzzle mechanics.
A common failure mode is to mistake a segmented edge bar for clickable puzzle pieces. If a repeated strip of small blocks sits flush against the top, bottom, left, or right border and actions only change that strip while the interior board stays the same, classify it as HUD/timer state, not as an object to click through segment by segment. DON'T DO THIS!
- Use coordinates only to target actions or describe local evidence. Do not frame the objective as reaching a specific absolute row or column.
- `WIN` means the whole game is solved.


Action meanings (use only actions currently available):
- `UP`, `DOWN`, `LEFT`, and `RIGHT` are directional controls; what they affect depends on the game.
- When available, `SPACE` performs a game-specific action, such as interacting, selecting, rotating, attaching/detaching, or executing. Test its effect rather than assuming what it does.
- When available, `MOUSE` clicks a board location. Pass integer `row` and `col` fields from 0 to 63. Coordinates are zero-based from the top-left: `row` increases downward and `col` increases rightward.
- When available, `UNDO` reverses a previous action, usually the last turn. Check what it restores. It cannot recover a failed attempt after game over.


Python tool guidance:
- Use `current_frame.segmentation` as your primary view of the board -- objects, colors, containment, adjacency, and cross-frame object hashes.
- Use `current_frame.ascii` only to read a small, specific region of the board when `segmentation` is not enough; never use it to scan or summarize the whole board.
- Python variables reset between tool calls. Re-import modules as needed; eligible functions are retained as described in the tool session rules below.
- The only importable standard-library modules are: bisect, collections, copy, fractions, functools, heapq, itertools, json, math, operator, random, re, statistics, string.
- The only tool is `python`; call it with one ephemeral `code` string.
- Always inspect `current_frame`, `history`, and `valid_actions` from Python instead of reasoning from the raw board by eye.
- For the most recent change, compare `previous_frame` to `current_frame`, or `last_transition.before_frame` to `last_transition.after_frame`. `history[-1].frame` is the current frame, so comparing it to `current_frame` only compares the board to itself.
- Optimize for the shortest reliable sequence that advances the current goal. If confidence is low, program a discriminating probe and revise your approach from the result.
- IMPORTANT: Especially when the game is about making an agent navigate to a target, it is usually safer to write an explicit search algorithm such as BFS. More generally, when the objective is understood but the best action order is unclear, pathfinding, flood fill, BFS, DFS, beam search, shortest-path search, limited action-sequence search, or custom heuristics are all valid.
- Once the important state variables and action effects are sufficiently understood, stop probing and search in the inferred state space.
- Inspect current and history frames from Python instead of describing frames freehand.
- Never print or echo full board frames. Return only compact derived summaries such as object lists, diffs, coordinates, counts, or tiny local crops.
- Keep tool-output context size minimal and decision-oriented so you can quickly compare before/after state. It's fine to write a lot of python code, just make the output short and interpretable
- A strong default loop is: summarize the board, infer the desired environment change, write a small scorer or search over candidate sequences, execute the best probe or plan with `action(...)`, then inspect again until you understand exactly what changed.
- For object tracking, match objects by color, overlap, bounding box proximity, area change, and edge contact rather than by exact coordinates alone.
- For frame diffs, summarize changed cells, color transitions, appearing/disappearing components, movement candidates, and small local row slices around the changed region.
- After every action, verify whether gameplay objects changed or whether only a timer, progress bar, or remaining-step bar moved. Do not treat HUD-only changes as evidence that the move worked.
- Use `print(...)` for compact summaries, or assign a final compact object to `result`.
- Call `action(...)` inside Python rather than returning action text in the chat.
- `action(...)` accepts an ordered list of one or more actions. Once your code has selected a reliable sequence, it is often useful to batch it.
- You can also call `action(...)` multiple times in one Python snippet, including inside loops. Each call updates the preloaded variables before execution continues.
- If an action result reports `game_over`, `run_complete`, or `done`, stop acting immediately and re-ground on the next turn.
- Flag semantics: `game_over` = this attempt FAILED (death or a limit ran out) — the level auto-resets to its initial state and completed levels are kept; it never means the run is won. `level_completed` = advanced one level. `run_complete`/`done` = the whole game is won. Deaths come either from the action itself (e.g., a hazard cell) or from a step/time budget depleting — watch for a bar at the grid border that shrinks each action, and count remaining budget into your plans.
- `frame_diff(before=None, after=None)` compares two frames. Omitted arguments default to `previous_frame` and `current_frame`, respectively.
- It returns a dictionary containing `changed_cell_count` (an integer) and lists named `moved`, `rotated`, `appeared`, `disappeared`, `changed_color`, and `resized`. Unchanged objects are omitted.
- Object-level changes are inferred by matching same-color, 4-connected components between frames: cells connect through shared edges, not diagonally. A game object may therefore be split into several components, or touching same-color objects may form one component.
- `moved` describes components matched at different positions. Matching does not establish persistent object identity: with multiple similar components, the reported correspondence may be ambiguous or incorrect. Movement combined with rotation includes `rotated_by` in degrees clockwise; `rotated` describes rotation in place.
- `changed_color` requires identical occupied cells with a different color. Entries contain `at`, `pixels`, `before_color`, `after_color`, `before_hash`, and `after_hash`.
- `resized` describes same-color components with overlapping footprints whose size changed. This can include backgrounds and budget bars. `at_before` and `at_after` can differ.
- `appeared` and `disappeared` entries include `bbox` in `[r0, c0, r1, c1]` order. Object hashes use the same rotation-invariant shape-and-color representation as segmentation; they are not unique object identities, and multiple objects can share a hash.
- Examples: `frame_diff()` compares the latest action’s before/after frames; `frame_diff(history[-3].frame, history[-2].frame)` compares two explicitly selected historical frames, when available.


Tool session rules:
- You have exactly one tool: `python`.
- When calling `python`, emit exactly the tool-call format shown elsewhere in this prompt for this model. Use only that format; do not add markdown fences, prose wrappers, or alternate tool-call syntax. Do not quote or place tool-call markup inside explanatory text; when you decide to call the tool, emit the tool call itself.
- Python variables reset between tool calls. Eligible functions you define are retained automatically for later calls throughout this game, including across level changes; they are cleared when a new game starts. Call your retained functions directly without repeating their definitions. Redefine a function when you need to change it.
- For a function to be retained, its dependencies must also be available next call. Pass snippet-specific data as arguments. You may use Python builtins, provided globals such as `current_frame`, and other retained functions. Provided globals are refreshed for each call. Supported explicit top-level imports used by retained functions are restored with them; imports inside a function also work. Use plain top-level definitions without decorators or annotations, and literal defaults. Tool results report which functions were retained and explain any rejection.
- You can call the `python` tool as many times as you want per step. Investigate until your code has a clear probe or plan.
- Do not ration tool calls when the state is unclear. Spend extra tool calls to confirm what changed between frames and whether the last action affected gameplay state or only HUD elements such as countdown bars.
- After `action(...)` returns, the structured runtime state is refreshed before the next Python statement and before the next tool call. Inspection-only Python calls do not clear `last_action_call_result`.
- Each `python` tool call has a hard time limit of 30 seconds.
- Tool responses are capped to about 3072 tokens. If a response is cut off, the tool result will tell you that.
- Keep code snippets short and purpose-built rather than dumping large frameworks into one call.

~~~~

v2 differences (lines removed `-`, added `+`):

~~~~text
-- In many games, a long horizontal or vertical line near an edge is a timer or remaining-steps bar. It often shrinks or changes each step. If you identify such a bar, do not get distracted by it or treat it as core gameplay state unless there is concrete evidence that it interacts with the puzzle mechanics.
+- In many games, a long horizontal or vertical line near an edge is a remaining-actions budget bar: it shrinks by one unit per action and the attempt fails when it is empty. Read its length as the number of actions you still have, plan sequences that fit inside it, and prefer short, reliable probes early in an attempt. The bar is not something to click or interact with.
+- `solved_levels()` returns one dict per level you have already completed in this game: `level`, `winning_actions` (the action sequence of the attempt that completed it, oldest first), `n_actions`, `attempts` (1 + resets on that level) and `total_actions`. It is computed from `history`, costs no in-game action, and is the fastest way to recall what worked: mechanics and the shape of a winning plan usually carry over to the next level even when the layout changes.
~~~~

## Appendix C. Code map (files you may ask us for)

| path | lines | what it does |
|---|---|---|
| `harness/ARC3-Inference/inference/agent/tool_agent.py` | 7,300 | the agent loop: prompts, context management and trimming, chat requests, guards, retained functions, level-up and game-over prompts |
| `harness/ARC3-Inference/inference/agent/prompts.py` | 383 | prompt fragments and addenda |
| `harness/ARC3-Inference/inference/agent/python_tool_sandbox.py` | 980 | the Python REPL tool, runtime variables, `action(...)` |
| `harness/ARC3-Inference/inference/agent/priority_scheduler.py` | 134 | the `P = (A + B) * C` admission gate |
| `harness/ARC3-Inference/inference/framework/solver.py` | 1,925 | per-game solver orchestration on the TAAF framework |
| `harness/ARC3-Inference/inference/utils/frame_diff.py`, `segmentation.py`, `animation.py` | 307 / 252 / 333 | perception helpers |
| `harness/ARC3-Inference/inference/utils/retained_functions.py` | 301 | persistent model-written functions |
| `harness/ARC3-Inference/inference/utils/level_memory.py` | 107 | our `solved_levels()` (v2) |
| `kaggle/cells/*.py`, `kaggle/variants/*.json`, `kaggle/build_notebook.py` | | notebook cells, per-variant config, builder |
| `kaggle/daily.py`, `kaggle/plan.json` | | the daily submission scheduler and its plan |
| `arc3/rhae.py`, `arc3/local_eval.py` | | the official score formula and an offline evaluator on the 25 public games |

## Appendix D. Sources

- Competition: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3 (overview, rules, data,
  leaderboard); organiser docs at https://docs.arcprize.org.
- Tufa Labs Duck harness: https://github.com/Tufalabs/duck-harness and Kaggle discussion 717133.
- Franzen's Milestone 2 solution: https://github.com/da-fr/arc-agi-3-solution and notebook
  `dfranzen/arc-agi-3-milestone-2-solution`.
- Other Milestone 2 notebooks: `lordhansolo/built-on-tufa-labs-duck-harness-milestone-2`,
  `sirikilohit/arc-agi-3-duck-18-1gc-submit`.
- Forum threads: 742835 (fine-tuning on the RTX Pro 6000), 739047 (STaR LoRA), 745062 (variance of
  identical copies), 744792 (Milestone 2 comparison), 742801 (Tufa not open-sourcing).
- Swift-1.5: https://huggingface.co/ukisai/Swift1.5-Qwen3.8-Flash-Next and its W4A16 AutoRound repo.
- Qwen3.8-Flash-Next model card: https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- Schema: arXiv 2609.39140. Memento 3: arXiv 2610.11794.
