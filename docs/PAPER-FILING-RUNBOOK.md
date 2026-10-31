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
| 1 | by 2 Nov 23:59 | Carson | Kaggle, ARC-AGI-3 competition, Submissions: select the two finals: 57372857 (v1, 29.93) and 57820036 (v10, 29.78), Carson's call on 31 Oct; a 1 or 2 Nov v10 draw above 29.78 replaces 57820036. The paper keeps linking 57477157 (v2), which need not be a final: the paper prize asks only for a linked working submission, and Kaggle scores every submission on the private set. |
| 2 | 3 Nov | Claude, on Carson's go | Copy the paper folder into `rodriguescarson/arc-prize-2026` as `paper/level-transfer/` (the ~/Research repo holds other papers and stays private). |
| 3 | 3 Nov | Carson | Make public: GitHub `rodriguescarson/arc-agi-3` and `rodriguescarson/arc-prize-2026` (Settings, Danger Zone, Change visibility). Kaggle datasets `arc3-harness-bundle` (licence: Apache 2.0, the strictest of its parts) and `py312-portable` (licence: Other, PSF): Settings, Sharing, Public. Kaggle notebooks `carsonrodrigues/arc3-duck-v2-level-memory-budget-bar` and the reproduce notebook: Share, Public. |
| 4 | 3 Nov | Claude | Verify: both repos public, both datasets and both notebooks public, every link resolves logged out, secrets scan re-run, the v2 notebook's **version 2** URL (the linked submission's kernel) copied for step 5. |
| 5 | 6 or 7 Nov | Carson | Kaggle paper-track writeup, **Edit** (never delete and recreate; one per team). Paste `writeup_v2.md` as the body. Set the title and subtitle below. Cover: `paper/figures/card_560x280.png`. Project links: the PDF as the main paper (link to `paper/level-transfer/paper/paper_full.pdf` in the public arc-prize-2026 repo), the v2 notebook version 2 URL, both repos. Track: Main Track. Save, then read Kaggle's word counter (must be at most 1,500). |
| 6 | 6 or 7 Nov | Carson | arcprize.org: update the separate paper entry with the same title, the PDF link and the linked submission 57477157. |
| 7 | after 5 | Claude | Read the live writeup back and check it against the local files. |

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
