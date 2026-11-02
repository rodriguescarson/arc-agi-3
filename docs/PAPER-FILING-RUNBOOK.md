# Paper filing runbook (ARC Prize 2026 Paper Track)

The text is approved (2026-10-30): `~/Research/22-arc-agi3-level-transfer/paper/writeup_v2.md` (Kaggle
Writeup body, 1,448 words by `wc -w`) and `paper/paper_full.pdf` (main paper, 7 pages, 20 references).
Screen behind it: `docs/PAPER-SCREEN-2026-10-29.md`.

Deadlines (UTC): code and final-two selection **2 Nov 23:59**; paper **8 Nov 23:59** (arcprize.org;
Kaggle staff say 9 Nov). Target: file on 6 or 7 Nov.

## Timing: publish the code on 3 Nov, not before

The paper needs the code public when it is judged, and prize eligibility needs it public before private
scores are released (4 Dec). Nothing requires it public before the code deadline. Publishing before 2 Nov
23:59 UTC would hand every rival the v10 harness fixes for the last three draws. So: publish on 3 Nov, then
file.

## Done already

- arc_prize_2026 has an MIT-0 `LICENSE` (rodriguescarson/arc-prize-2026#1); arc-agi-3 already had one.
  Franzen's Apache-2.0 and Tufa's MIT code keep their notices.
- Secrets scan (gitleaks, full history, 2026-10-30): arc_prize_2026 0 findings; arc-agi-3 2 findings, both
  SHA-256 checksums in `kaggle/cells/40_serve.py` (`TOKEN_MAP_SHA`, `TOKENIZER_SHA`), not secrets.
- Labels: GitHub descriptions and topics set on both repos; Kaggle datasets `arc3-harness-bundle` and
  `py312-portable` now have titles, subtitles and descriptions (still private); the card image states the
  two findings.

## Steps

| # | when | who | step |
|---|---|---|---|
| 1 | **done 2 Nov** | Claude, on Carson's go | Finals selected on Kaggle: 57372857 (v1, 29.93) and 57820036 (v10, 29.78). They had been v1 + 57477157 (v2, 29.54); swapped at Carson's confirmation, read back as 2/2 selected. The paper keeps linking 57477157 (v2), which need not be a final: the paper prize asks only for a linked working submission, and Kaggle scores every submission on the private set. |
| 2 | **done 2 Nov** | Claude | rodriguescarson/arc-prize-2026#3 (merged, repo still private): `paper/llm-arm-results` merged into main (all 21 draw rows, stale v1 paper files gone); `paper/level-transfer/` added from the allow-list below with a public README mapping the paper's code paths; both scripts made portable (outputs byte- and pixel-identical); LICENSE now plain MIT-0; `data/human_replays_packed/NOTICE`. arc-agi-3: LICENSE plain MIT-0, third-party licences in NOTICE (#53). Carson decided on 2 Nov: keep redistributing the packed replays (with the NOTICE) and keep rodriguescarson@gmail.com in arc-prize-2026 `pyproject.toml`. |
| 3 | 3 Nov | Carson | Make public: GitHub `rodriguescarson/arc-agi-3` and `rodriguescarson/arc-prize-2026` (Settings, Danger Zone, Change visibility). Kaggle datasets `arc3-harness-bundle` (licence: Apache 2.0, the strictest of its parts) and `py312-portable` (licence: Other, PSF): Settings, Sharing, Public. Kaggle notebooks `carsonrodrigues/arc3-duck-v2-level-memory-budget-bar` and the reproduce notebook: Share, Public. |
| 4 | 3 Nov | Claude | Verify: both repos public, both datasets and both notebooks public, every link resolves logged out, secrets scan re-run, the v2 notebook's **version 2** URL (the linked submission's kernel) copied for step 5. |
| 5 | **done 2 Nov** (Claude, in Carson's Chrome, on his request) | Claude | Kaggle paper-track writeup edited in place and saved with "Update Submission": body = `writeup_v2.md` without its H1 (8,652 characters, 1,436 words by `wc -w`), the subtitle below, the rebuilt card. Read back live: new subtitle and body, status Submitted, both notebook project links kept. Backup of the replaced 28 Oct body: scratchpad `filing/live_oct28_body.md`. Kaggle's own deadline for edits: 9 Nov 23:59 UTC. |
| 5a | **done 2 Nov** | Claude | `paper_full.pdf` attached under Project Files; media gallery now holds only `fig6_e21_transfer.png` (1,186 pairs, 23 games, 99.7%, "filed bar"), the old 1,237-pair figure deleted; saved with Update Submission and read back live. How: Kaggle's upload buttons call `input.click()` on a file input, which opens the macOS picker; patching `HTMLInputElement.prototype.click` in the page to capture the input and then setting its files with the browser tool avoids the picker. |
| 5b | after 4 | Carson | Project links: replace the v2 notebook link (it opens the latest version 4, 19.75) with the **version 2** URL (`?scriptVersionId=` of version 2, 29.54, rev 4033b27); add both repos once public. |
| 6 | not needed | | There is no separate arcprize.org entry: the Kaggle paper-track overview says the Writeup is the submission (required: Writeup, media gallery, project link; public notebook optional), and arcprize.org/competitions/2026/paper links only to Kaggle (checked 2 Nov). Deadline 9 Nov 23:59 UTC. |
| 7 | after 3 and 5a | Claude | Read the live writeup back logged out: every link resolves, the PDF opens, and the "Code, data and every experiment log are released with the paper" sentence is true (it is not until step 3). |

### Release checklist for steps 2 and 3 (pre-flight check, 2 Nov)

- Copy an allow-list, not the folder: `HYPOTHESES.md`, `paper/paper_full.{md,pdf}`, `paper/writeup_v2.md`,
  `paper/figures/{fig6_e21_transfer,card_560x280}.png`, `paper/make_fig_e21.py`, `paper/make_card_560x280.py`,
  `experiments/` (E21 json and out, `level1_cost_check.{py,out}`), plus a new short public README. Leave out the
  screen, `RUBRIC_SCORECARD.md`, `cover.png`, `draft.md`, `OUTLINE_v2.md`, `writeup_clean.md` (internal or v1 framing).
- The public README maps the paper's code paths: `inference/utils/level_memory.py` is
  `harness/ARC3-Inference/inference/utils/level_memory.py` in arc-agi-3; `arc3/agents/model_based.py` is
  `src/arc_prize_2026/arc3/agents/model_based.py` in arc-prize-2026.
- Make the two scripts portable: `experiments/level1_cost_check.py` (ROOT is an absolute path) and
  `paper/make_fig_e21.py` (sys.path uses the home directory); re-run and diff against the committed outputs.
- arc-prize-2026: the default branch `main` is behind `paper/llm-arm-results` (SUBMISSIONS rows, LLM draws) and
  still holds the old v1 paper files; the branch lacks the MIT-0 `LICENSE` that main has. Merge the branch into
  main by PR before the flip and check that `LICENSE`, all draw rows and the removal of the stale paper files land.
- Licences: GitHub reads both `LICENSE` files as "Other" (NOASSERTION) because of the "(MIT-0)" title and the
  appended harness note; use the plain SPDX MIT-0 text and move the note to README or NOTICE. Add a NOTICE for
  `data/human_replays_packed/` (derived from the ARC Prize human replay release; source names no licence) and for
  the Tufa harness (MIT declared only in `pyproject.toml`). `arc3-harness-bundle`: licence "Other", description
  stating MIT-0 for Carson's files, Apache-2.0 Franzen, MIT Tufa.
- `pyproject.toml` in arc-prize-2026 lists a personal gmail address: Carson keeps it (2 Nov).
- Leaving files out does not unpublish git history (gitleaks over all 155 commits: no findings); accept that.

## Labels for the writeup

- **Title** (keep; the entry is filed under it): What should an agent carry from one level to the next?
- **Subtitle** (replaces the stale "0 of 1,237 human pairs, 0 of 25 games, positive control 95.6%"):
  Replaying the plan re-solves the next level in 0 of 1,186 pairs; the mechanics partly transfer
- **Card:** `paper/figures/card_560x280.png` (rebuilt 30 Oct: "Replaying the plan: does not transfer",
  "The mechanics: partly transfer", 0 of 1,186 pairs, 23 games, control 99.7%, 0.740 against a 0.301 null).
- **Do not upload** `paper/cover.png` (stale v1 cover).

## Facts only Carson can confirm before step 5

The text uses safe interim wording for each; confirming lets the full paper be exact.

- Kaggle discussion 745062 (Son Pham): title, date, mean 25.77, SD 3.93, whether failed runs were excluded.
- The Kaggle per-level score cap (the Writeup says "capped per level"; the PDF quotes the technical report's 1.15).
- The replay licence and the 342 (release post) against 340 (mirror) count.
- How often `solved_levels()` was called in the scored runs of 57477157 and 57575322 (the text says
  "unknown"; scored-run logs are not downloadable, so it may stay unknown).
