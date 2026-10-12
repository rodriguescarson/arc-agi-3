# What everyone else is doing (ARC-AGI-3, as of 2026-10-12)

## Leaderboard (public, 55 hidden games)

| Rank | Team | Score | Open? | Notes |
|---|---|---|---|---|
| 1 | Yi-Chia Chen | 62.96 | no | "excited to see how high people get by combining the three winning notebooks" |
| 2 | Tufa Labs | 56.52 | no (until the end) | Duck harness authors; won Milestone 1 at 1.21 |
| 3 | mtg | 45.00 | no | |
| 4-20 | Majkel1337, the last dance, NVARC3 (CPMP/NVIDIA), Son & Mark & Ronen, dreach.ai, ... | 36.5-42.7 | no | most of this band is Franzen's notebook plus luck or small edits |
| ~100 | | 32.1 | | |
| ~300 | | 30.3 | | |
| ~500 | | 29.0 | | |

Milestone 2 winners (Sep 30, all open-sourced): Daniel Franzen 27.89, Lord Han Solo 23.84,
Lohit Siriki (rellik13) 22.53. All three run Tufa Labs' Duck harness on TAAF and serve
Qwen3.8-Flash-Next on the single RTX Pro 6000.

## The lineage

1. **StochasticGoose** (Tufa, preview competition, 12.6 %): CNN + RL action learning, no LLM.
   Shipped by Kaggle as the sample submission (`inversion/arc3-sample-submission-stochastic-goose`).
2. **Blind Squirrel** (preview 2nd, 6.7 %): state-graph exploration + ResNet18.
3. **Symbolica ARCgentica** (36 % on public games with frontier APIs): recursive orchestration,
   code-driven; not Kaggle-legal (API).
4. **RGB Agent** (OpenCode): generic coding harness, first near-human action efficiency on the
   3 preview games.
5. **The Duck** (Tufa, Milestone 1, 1.21 %, MIT): Qwen 3.6 27B FP8 in a Python REPL; game state as
   Python variables; `action(...)` from code; segmentation tool; 4x image of the board; context
   eviction. Write-up: Kaggle discussion 717133. Repo: `Tufalabs/duck-harness`.
6. **Franzen** (Milestone 2, 27.89, Apache-2.0): Duck + Qwen3.8-Flash-Next (Intel W4A16
   AutoRound, BF16 PLE offloaded to host RAM, Albucino INT4 MTP draft for speculative decoding)
   on SGLang "Pennyroyal" 2.5.3 with 5 patches; 128 Ki harness context, 12 Ki output,
   hysteresis trimming to 58 Ki; 10 concurrent streams gated by a priority scheduler
   `P = (A+B)*C` with tail fade; animations and `frame_diff()` exposed as REPL variables;
   10x board images, diff images, death images; UNDO exposed; batch no-op / stale-state /
   terminal guards; persistent model-written functions; world-model text mechanism OFF.
   Repo: `da-fr/arc-agi-3-solution`; notebook `dfranzen/arc-agi-3-milestone-2-solution`;
   write-up vendored at `docs/franzen-writeup.md`.
7. **Lord Han Solo** (23.84): vLLM 0.29 nightly, mixed NVFP4+FP8 model with built-in MTP head,
   14 streams, 3,918 s cap per game, tool-agent rewrite (1,745 lines), strategy-audit prompt
   once a level has used 25 % of the game's time, per-game Python modules tested before swap.
8. **rellik13 / Lohit Siriki** (22.53): 16 streams over 28 live games, UCB time slices of
   2,400 s, 48 GB host KV tier, context watermarks 57k -> 45k, **solved-level memory pinned in
   the system prompt** (rule + last 30 winning actions per cleared level), no Python state
   carried over. He reports that *not misleading the agent* helped: UNDO instead of ACTION7,
   "level restarted" instead of "game over", removing the "ignore the budget bar" lines;
   FP8 KV cache halved memory and took him 14.5 -> 22.5.

Everything above the Milestone-2 band is private. Tufa said on Sep 24 they will not open-source
until the end because "the winner would simply be the luckiest of 4,000 copies". NVIDIA (CPMP)
said the same. Scott Le Grand suspects Tufa's jump involves fine-tuning. The forum's own guess
for the remaining headroom: better models (everyone is "waiting for Qwen 4"), more tokens per
game (serving engineering: REAP-pruned experts, KV quantisation, prefix caching), and harness
work now that serving is roughly equal across the public notebooks.

## What changed since Oct 1 (checked 2026-10-12)

**Fine-tuning: tried by others, no gain on this model.** Kaggle threads 742835 and 739047:

| who | what | result |
|---|---|---|
| blakewest | SFT on H200s; teachers Qwen Max / Astra; synthetic LS20 + CD82 variants; stall-point and periodic trajectories; Flash-Next and 27B | "No permutation of these has been able to make meaningful improvements" |
| AAAAAtjc | RL pipeline for Flash-Next on a full H200 node | "did not gain any performance"; "rtx 6000 pro can not be used for training of any ~100B model even with aggressive cpu offload" |
| Scott Le Grand | behavioural cloning from the same model (Qwen 3.6 27B) | +2 on public games, "didn't translate" to the hidden set |
| manas joshi | STaR LoRA on Qwen 3.6 27B, own winning trajectories (CC0: `arc3-sft-trajectories`, `arc3-duck-lora-sft`) | LB 1.25 -> 1.94 in August; "high variance", "naively scaling the data hurt", "base-model-specific" |
| Ya Xu | LoRA | "only backfired on me" |

Franzen did not fine-tune (write-up: "I did not train or fine-tune the models"). Tufa's harness ships
vLLM LoRA hooks (`SERVER_ENABLE_LORA`, alias `policy`, Gated-DeltaNet module aliases) and a chat-JSONL
trace exporter (`inference/tools/traces.py`), so Tufa is set up for it; nothing public shows it working.
Our serving stack (SGLang, AutoRound W4A16 + MTP draft) has no adapter path. Decision: no fine-tuning.

**Thinking is already maxed.** Franzen sends `enable_thinking=true`; the Qwen3.8 template defaults
`reasoning_effort` to `xhigh` (the top of xhigh/medium/low) and `preserve_thinking=true` keeps every
earlier turn's reasoning in context. His write-up: dropping the thinking history is a large regression.
The remaining knobs are the effort ladder (`ARC3_REASONING_EFFORT_LADDER`, steps down after a
truncated turn) and our new global `ARC3_REASONING_EFFORT` (v4).

**Compaction (OpenAI's "two settings", 7.8 -> 38.3 on GPT-5.6 Sol: keep reasoning + summarise instead
of truncate).** Reasoning is already kept. Franzen tried both summary modes (`ARC3_SUMMARY_*`):
"Neither gave a clear improvement"; off in his submission. Not a priority.

**Swift-1.5 Qwen3.8-Flash-Next (UkisAI, Sep 24).** RL + on-policy-distillation post-train of the same
model against overthinking: GPQA 89.8 -> 89.6 with 55.8% fewer mean / 63.4% fewer median thinking
tokens at xhigh; LiveCodeBench 88.4 -> 90.4; Terminal-Bench 67.6 -> 69.7; IFBench 73.2 -> 70.1 (all
vendor numbers, BF16). Same tokenizer (sha256 identical to Franzen's FR-Spec map), same AutoRound
W4A16 packaging (`auto_round:auto_gptq`, g128 sym). Difference from Intel's quant: Swift also quantises
`self_attn.{q,k,v,o}_proj` and `linear_attn.{in_proj_qkv,in_proj_z,out_proj}` (Intel leaves them BF16).
Kaggle mirrors: `phuongncn/arc3-qwen38-swift-w4a16-autoround` (two PyTorch instances, 177 GB, verbatim)
and `lordhansolo/swift-1-5-qwen3-8-flash-next-nvfp4` (Lord Han Solo served Swift NVFP4 on vLLM for his
23.84). License: Swift Open License 1.0 (free under US$1M revenue) on top of Qwen Community 1.0. This is
our v3: one input swap, the "more turns per game" lever without serving work.

**Harness research (frontier models, public games, not Kaggle-legal as-is):** Schema (arXiv
2609.39140, Sep 30): program induction instead of prose notes, RHAE 58.7 -> 99.2 with the same model.
Memento 3 (arXiv 2610.11794, Oct 8): natural-language rulebook compiled to code, verified by replay,
100 RHAE on all 25 public games. Continual Harness (Karten): 62% of actions from saved skills. Common
thread: an explicit, executable world model. Franzen's harness already has persistent model-written
functions; a rulebook mechanism for a 6B-active model is a research item, not a 21-day item.

**Qwen 4:** announced (four sizes, "training"), nothing shipped as of Oct 12.

## Variance, the thing that decides submissions

- Hundreds of byte-identical Franzen copies: mean 25.77, SD 3.93 (Son Pham, Oct 2).
- Same notebook resubmitted by one team: 27-28 four times (xz); another team sees +/-1; others
  see +/-5 and "+10 between two runs of the same version on the public games".
- Local public-game scores do not rank versions the way the LB does (Pearson r = -0.32 over 5
  versions on a 6-game regime, Shehab Anwer).

Implication: with one submission per day and 21 days left, every submission is a draw. Changes
worth shipping are the ones with a mechanism (more useful tokens, less misleading feedback,
less wasted actions), not the ones that "scored 2 points higher once".

## Serving facts that matter on the RTX Pro 6000

- Weights on GPU ~70-74 GB (W4A16 or NVFP4) + ~3.8 GB draft; KV + Mamba cache 16-20 GB; FP8 E4M3
  KV; 95 GB BF16 PLE table in host RAM (machine has ~190 GB RAM).
- Notebook start to server ready: 530-615 s. Decode 720-1,160 tok/s aggregate across streams.
- Fewer slots with longer per-slot context scored best (Franzen: 10 slots x 128k).
- Kaggle Models available offline (public): `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround`,
  `dfranzen/albucino-qwen3-8-flash-next-drafter`, `nvidia/qwen3-8-flash-next-nvfp4`,
  `boristown/qwen3-8-flash-next-nvfp4-reap-448e` (REAP-pruned 512->448 experts, frees VRAM),
  `lordhansolo/swift-1-5-qwen3-8-flash-next-nvfp4`, several AutoRound mirrors.
- Wheelhouse (public dataset): `dfranzen/pennyroyal-v253` (SGLang Pennyroyal 2.5.3, cp312).

## Forum threads read (ids on the competition discussion board)

717133 Tufa write-up · 744792 Milestone-2 comparison (Tong Hui Kang) · 742801 Tufa not
open-sourcing · 697944 9 h runtime · 705405 1 submission/day · 691696 "It is 0.66 %" · 745654
Python 3.13 image · 745062 copy variance · 746010 Franzen LB display · 748193 small deviations.
Not yet read: 709355 run-time viewer, 687648 offline evaluation + recording viewer, the long-queue
threads, "Human scores visible to agents" (baselines are hidden in competition mode anyway).
