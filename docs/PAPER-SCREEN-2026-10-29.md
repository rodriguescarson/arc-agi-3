# SCREEN report: ARC Prize 2026 Paper Track, paper 22 (`paper/writeup_v2.md`), merged 2026-10-29

**VERDICT: WRONG VENUE by the CHECKLIST.md rule (two G items fail: G6, G8). 13 FAIL, 24 WARN, 15 PASS, 1 N/A constraint. Nothing is READY.**

Read this label correctly. The ARC Prize 2026 Paper Track is the right venue and the only one with a live deadline (it has no desk-reject stage; every entry is scored on a six-criterion rubric). The rule says "any G fail = WRONG VENUE, no exceptions", and a scope or evidence flag may never be downgraded. The venue screen graded G6 as FAIL and still wrote "FIX FIRST"; that is the downgrade the rule forbids, so I applied the rule. The three G fails are all closable in days: (1) G6, add the scope sentence to section 7; (2) G8, paste the corrected text into the already-submitted Kaggle writeup; (3) G8, both attached notebooks are private. After those, the same screen returns FIX FIRST until the N, C and W fails below are fixed (N: F02 to F04, F06 to F09; C: F05, F10; W: F11). READY needs every WARN dispositioned in writing.

Deadlines: Kaggle staff say the binding paper deadline is **9 Nov 2026 23:59 UTC**; arcprize.org says 8 Nov. Plan the last save for **8 Nov 23:59 UTC**. Code submissions and final-two selection close **2 Nov 23:59 UTC**.

Nothing was edited, uploaded or sent. The four screens' scratch work is under `.../scratchpad/paperscreen/{numbers,venue-gate,refs-writing,G7}`; this merge's scratch is `.../paperscreen/merge/`. The checklist's mechanical script expects LaTeX, so every item was applied by reading. T0 to T4, T7, C2 to C5, C8 to C12 (bibliography), F1 to F5, F8 to F10, V (no PDF), A (review is not blind; the author name is shown) and M2 to M8 (single author) are N/A for a Markdown writeup.

---

## 1. FAIL findings (13)

Each block: quoted manuscript text, evidence, fix, owner. "Claude drafts" means the text below is ready and Claude applies it once Carson approves; the change touches a claim, so it is not purely mechanical.

### F01 (G6, G3a, rubric Universality) Scope flag opened by our own scorecard is not closed
- **Quote (section 7, whole limitations paragraph):** "The effect model expresses only rigid displacements, so click and recolour mechanics are memorised, not planned toward; ... E21 measures human play, so it bounds what is *available* to transfer, not what an agent uses." Nowhere does it say one benchmark, one LLM base model, or public 25 only.
- **Evidence:** RUBRIC_SCORECARD.md, Universality: "Still one benchmark. No evidence the result holds outside ARC-AGI-3." Next action: "State the scope limit plainly in §7 rather than overclaiming." Progress: "note the release in §7". Not applied. The only second LLM base (Swift pair) was dropped after one draw of 4.92.
- **Fix, section 7, about 28 words:** "Scope: one benchmark (ARC-AGI-3), human replays on the public 25 games only, one LLM base model (a second pair was dropped); nothing here tests transfer outside ARC-AGI-3."
- **Owner:** Claude drafts, Carson approves. Screens: venue G6, G3a; editor UNI.

### F02 (N2, N4) M1 headline contradicts its own caveat and overstates the sample
- **Quote (abstract):** "A winning sequence re-solves the next level in **0 of 1,237** testable pairs across **0 of 25** games, positive control 95.6 percent". **Quote (caveats):** "The positive control fails on all 51 tn36 pairs (and 3 lf52, 1 sc25), so tn36 is excluded wherever M1 is quoted; s5i5 has no reproducible pair".
- **Evidence (re-run in this merge from `experiments/E21_level_transfer.json`):** 340 sessions, 309 frame-exact, 1,314 pairs, 1,237 reproducible (94.14%). M1 successes 0. C2 = 1,182 of 1,237 = 95.55%. Games with any M1 pair: 24 (s5i5 has 0). C2 failures: tn36 51 of 51, lf52 3 of 64, sc25 1 of 58. Excluding tn36: **1,186 pairs, 0 successes, 23 games, C2 = 99.66%**. Every quoted M1 figure includes tn36, so "excluded wherever M1 is quoted" is false. The 1,237 pairs are only **150 distinct (game, k) transitions (144 without tn36)**, about 8 sessions each. Clopper-Pearson 95% upper bound: 0.30% treating 1,237 pairs as independent; **2.5% at transition level (0 of 144)**. Both are far below the filed 10% bar.
- **Same wording elsewhere:** Kaggle subtitle ("0 of 1,237 human pairs, 0 of 25 games, positive control 95.6%"), `card_560x280.png` ("0 of 1,237 pairs · 0 of 25 games"), README, table row P21a, figure `fig6_e21_transfer.png` panel A title ("1,237 testable pairs, 25 games").
- **Fix, recommended Option B (keeps the filed numbers visible):** abstract "A winning sequence re-solves the next level in **0 of 1,186** testable pairs (23 games with a working positive control, 144 distinct level transitions; control 99.7 percent)". Table: "**0 of 1,186 pairs, 0 of 23 games**", control "**99.7%**". Caveat: "The positive control fails on all 51 tn36 pairs (and 3 lf52, 1 sc25), so M1 is quoted without tn36 (with it: 0 of 1,237, control 95.6 percent, the filed run); s5i5 has no reproducible pair; six other games record no movement". Option A (keep 1,237 and 25, change only the caveat to "tn36 is included in these counts although its control fails") is acceptable but weaker. State the interval at transition level.
- **Owner:** Carson picks A or B; Claude then updates abstract, table, caveat, README, card and fig6. Screens: numbers N2-games, venue G3b, editor CLM-M1.

### F03 (N2) "19 of 25 games" is true under the filed rule and misleading as written
- **Quote (abstract):** "successive winning sequences are more alike than chance on 19 of 25 games: the plan carries real structure and is not executable". Table: "**19 of 25 games**". Text: "more alike than chance on most games".
- **Evidence:** merge re-run reproduces 19 (mean of sim minus shuffle above 0); not above: lp85, ls20, m0r0, r11l, tu93, vc33. Pooled similarity 0.4461 against shuffle 0.4307 (+0.015). Numbers screen: two of the 19 are floating-point ties (s5i5 +5.8e-18, tn36 +5.4e-19); five games (lp85, r11l, s5i5, tn36, vc33) cannot differ from their shuffle (M2 tokens are action ids only, `level_transfer.py:337`), so 17 of the 20 games where a shuffle can differ are above, 3 below (ls20, m0r0, tu93, tu93 clearly negative). Two methods give 12 games distinguishable from zero (pair-level t, and the editor's session-clustered bootstrap); that bootstrap is not in the repository, so do not print 12 until the code is released. P21c fails under any count.
- **Fix:** abstract "successive winning sequences are only slightly more alike than a shuffle (0.446 against 0.431; above it on 17 of the 20 games where a shuffle can differ)"; table "**17 of 20 games** (19 of 25 under the filed rule)"; M2 definition "over action ids"; replace "the plan is neither empty nor executable" with "the plan has structure but cannot be replayed".
- **Owner:** Carson approves. Screens: numbers N2-M2, editor CLM-M2.

### F04 (N6) "pre-registered before any code ran" is false; "pre-registered" needs a public record
- **Quote (section 4):** "pre-registered before any code ran". Abstract: "a pre-registered 11-point rule". Also on the card and in README.
- **Evidence:** RESEARCH_LOG 2026-10-13 19:28 holds the pre-registration, `level_transfer.py` and a "12-session smoke: 65/65 pairs ... C2 100%" in one entry; `E21_level_transfer_n12.json` shows M1 0 of 65 already. Three full-run launches (10-13 19:32, 10-15 00:48, 10-15 05:45) died before output. First independent record: GitHub PushEvent for commit ec242a3 (pre-registration, code and smoke JSON together) at **2026-10-15T03:05:13Z**. The first pair draw is 57372857 on 10-19, so "The rule filed before any pair ran" is true. Both repos are private; Playbook section 5: "Only write pre-registered if there is a timestamped public record." Editor called the pre-registration "genuine and creditable"; that holds for the bars filed before full results and the 11-point rule, not for "before any code ran".
- **Fix (section 4):** "fixed in HYPOTHESES.md (pushed 15 Oct 03:05 UTC, after a 12-session smoke that already showed M1 = 0 of 65, before any full result)". Abstract: "an 11-point rule filed 15 Oct". Card: "predictions filed in advance". Making the repos public creates the record.
- **Owner:** Carson. Screen: numbers N6-prereg.

### F05 (C13, N7) Section 2 misdescribes the field, and the novelty claim is contradicted
- **Quote (section 2):** "Harnesses inject each solved level's winning sequence into context; our explorer carries a learned effect model. Neither family publishes a comparison against its own no-memory twin." Abstract: "The two leading families of entries each bet on one and neither tests the bet." Section 4: "That is what an LLM harness's `solved_levels()` hands its model." Heading: "both families choose, neither measures".
- **Evidence:** `docs/franzen-writeup.md` line 246: "Build a new plan for this layout rather than continuing the previous level's action sequence"; line 248: "Start from the mechanics you established on the previous level; do not rediscover them without reason."; line 20 reports that turning off his text world model "worked best". `kaggle/variants/v1-franzen-faithful.json` sets `ARC3_LEVEL_TRANSFER_GUIDANCE: "1"`. `solved_levels()` exists only in our fork (`v2-level-memory.json`: "v1 plus two prompt-side mechanisms, both off in v1"). Plan memory comes from Siriki's (rellik13) Milestone-2 notebook (bundle code `M85_ACTIONS_KEPT = 30`). PRO-LONG (arXiv:2607.20064) gains 18.0 points over a no-log baseline; NOOA (2607.20709) +11.8 over plain files; both on public games. So both sentences are wrong as written.
- **Fix:** replace section 2 with the paragraph in section 7 below (about 150 words, +50). Abstract: "Entries carry a plan, a rule or both from level to level, and none we found measures which helps on hidden games." Section 4: "an LLM harness's" becomes "our harness fork's" (mechanical). Do not print rellik13's "22.53" placing unless linked (project notes only).
- **Owner:** Claude drafts, Carson approves (changes the abstract's premise). Screens: numbers C13-franzen, citation C13-harness-injects and C13-no-twin, editor CLM-PRIOR.

### F06 (N5) The v2 versus v1 pair is not a clean "plan memory" ablation
- **Quote:** heading "**5b. Plan memory, controlled (LLM harness, hidden 55).**"; "The level-memory variant was paired with its no-memory twin on the same Intel base"; table column "plan memory | on | off"; abstract "plan memory on averages 24.65 ... off 27.89".
- **Evidence:** `v2-level-memory.json`: v2 adds `ARC3_LEVEL_MEMORY=1` (an optional REPL call, `solved_levels()`, mentioned once at level-up) **and** `ARC3_BAR_GUIDANCE=budget` (rewrites the edge-bar prompt line; kernel slug `v2-level-memory-budget-bar`). v1 (the "off" arm) already carries Franzen's level-transfer guidance. `docs/TASKS-2026-10-29.md`: "Optional REPL tools are ignored by this model (navigate_to 0 of 200 snippets ...)". The paper reports no call rate for `solved_levels()`. v1f (identical code, faster load) is a further no-helper arm with draws 29.44, 21.86, 28.19; pooled off arm (v1 plus v1f, n=5) mean 27.05, SD 3.30, gap to v2 2.41.
- **Fix:** header and abstract "`solved_levels()` on / off"; add "v2 also rewords the budget-bar line; both arms keep Franzen's level-transfer guidance"; add the fraction of v2 games that called the helper (count `solved_levels(` in the draw logs of 57477157 and 57575322) or say it is unknown; add v1f draws or say why excluded. About +30 words.
- **Owner:** Carson (needs the logs). Screens: numbers N5-LLM-arm-confound, citation C13-v2-confound, editor CLM-ARMS.

### F07 (N3, N4, G3c) "The harness agrees from the other direction" cannot be supported
- **Quote (abstract):** "The harness agrees from the other direction: plan memory on averages 24.65 over two hidden draws, off 27.89, a 3.2-point gap under a pre-registered 11-point rule." Section 5b: "**no effect is claimed**, as predicted."
- **Evidence (recomputed):** v2 (29.54, 19.75) mean 24.645; v1 (29.93, 25.85) mean 27.89; gap 3.245. With the copy SD 3.93, SD of a 2-versus-2 mean difference is 3.93; 95% interval for off minus on is [-4.5, +11.0]; 11.0 is 42% of the 26.22 mean; observed 0.8 SD. A rule that can only detect 11 points "predicting none" could not fail. 3.93 x sqrt(2) = 5.56 (the "about 5.5"), 2 x 5.56 = 11.1.
- **Fix:** abstract "The harness comparison is too coarse to confirm or refute anything: two hidden draws per arm average 24.65 with the helper and 27.89 without, a 3.2-point gap inside the 11 points the design resolves." Section 5b: "The means differ by **3.2** (0.8 SD), memory lower: no effect is claimed; two draws per arm resolve only 11 points, so this neither supports nor rules out one." README line 18 ("comes out the same from two unrelated directions") the same.
- **Owner:** Carson approves. All four screens agree.

### F08 (N5, N3) Section 6: the public-25 column mixes agent versions and "sevenfold ... refutes" rests on one game and one draw
- **Quote:** table cells "0.277", "0.227", "0.204"; "The fifth refutes that: contact curiosity, worth +0.080 publicly, moves the hidden score sevenfold, 0.08 to 0.01."; "The metric is selective, not blind. Contact curiosity buys **first-level efficiency**, ... and the metric pays for it."
- **Evidence:** 0.277 and 0.227 are v5 memory-on and memory-off (0.276995, 0.227412); 0.204 is v4 contact-off (0.203870). The submitted kernels are the v7 agent plus E15 speed-up, public-25 0.280 (0.279741, 15 levels). "+0.080" is v4 0.283913 minus 0.203870; the table's own cells give 0.073. Per game, the +0.080 is lp85 (+0.1111; solved at level 1 in 15 actions only with contact on); lf52 is -0.0332; without lp85 contact-on is lower. The 21.2x and 8.6x medians come from different game sets (10 and 11 games; on the 9 shared games 21.95x against 8.59x). 0.08 / 0.01 = 8.0, not 7, and at 2-decimal precision the ratio is anywhere from 5 to 17. 0.07 x 55 = 3.85 game points, one level, which the paper's own last paragraph says ("about 4.4 game points over 55 games, roughly one such level"). HYPOTHESES.md E16: the ablations "cannot be distinguished from the full agent; the pre-registered ratio test is void". The 21.2x/8.6x figures are not stored in a results file.
- **Fix (recommended, keeps the information):** table 57123503 "0.280", 57199354 "0.227 (v5 twin)", 57248168 "0.204 (v4 twin)", header "public 25 (nearest measured twin)". Replace the "fifth refutes" sentence with "The fifth is a level lower: contact curiosity (+0.080 publicly on the v4 pair, all of it lp85) scores 0.01 against 0.08 in one draw, about one level." Change "buys ... and the metric pays for it" to "is consistent with"; delete "The metric is selective, not blind." Abstract: "We also find evidence, from one draw per arm, that ...". Alternative (editor): drop the public column.
- **Owner:** Carson. Screens: numbers N5-public-column and N3-contact-curiosity, editor CLM-S6 and CHG5, citation W4 item 8.

### F09 (N6) Released-folder files contradict the paper
- **Quote (HYPOTHESES.md, E21 outcome):** "(843 movement pairs, in-sample ceiling 0.906)". The paper and `E21_level_transfer.out` say 431.
- **Evidence (merge re-run):** movement games with M3: 431 pairs, transfer 0.7395, ceiling 0.9064, null 0.3005; all games with M3 data: **843** pairs, 0.716, null 0.247, ceiling 0.892. Also: deviation note "2026-10-16 15:05 IST" against commit 0e3754d pushed 08:34:07Z (14:04 IST); HYPOTHESES.md H2 "342 released human replays" against 340; README "Draft is at 1,496 words" (now 1,498); RUBRIC_SCORECARD "five Intel draws (mean 26.00, SD 4.13)", "1,473 of a hard 1,500 words", leaderboard top 62.96 (now 75.56).
- **Fix:** append a dated erratum to HYPOTHESES.md (the file's rule: outcomes are never edited in place): "2026-10-29: 843 should read 431; 843 is all games with M3 data; 0.740, 0.301 and 0.906 are the 431-pair movement subset. 15:05 IST is the log label; the commit was pushed 14:04 IST." Update README and RUBRIC_SCORECARD.
- **Owner:** Claude (after approval; these files are outside this task's write scope).

### F10 (C1, C7) No reference list, no links, no in-text citation for eight named works; recent work missing
- **Quote (section 2):** "LLM-in-REPL harnesses (Tufa Labs' Duck, Franzen's Milestone-2) ... Stochastic Goose ... The papers (Twin, Tycho, PRO-LONG) ... AERA". Section 4 uses the replay data and section 1 the scoring formula with no source.
- **Evidence:** all 12 arXiv ids in the list below were re-fetched live in this merge (title, first author, date match). The closest prior work, Tracing (2610.11450), and the same-month ablations (NOOA, Self-harness) are uncited. Ledger rows 5, 11, 25 (unverifiable, fabricated, stale references).
- **Fix:** add the reference list in section 7 below (14 core entries about 146 words, 19 with the optional five about 190). Test whether the Kaggle counter counts it (see section 9).
- **Owner:** Claude drafts the list and tags; Carson decides the counter/PDF route. Screens: citation C1, C7; editor C-REFS.

### F11 (W4) Eleven negative parallelisms (house rule)
- Abstract "each bet on one and neither tests the bet"; "the plan carries real structure and is not executable". Section 1 "Squaring pays for efficiency, not coverage"; "The paying question is not whether to carry state ... but **what** to carry". Section 2 heading "both families choose, neither measures". Section 4 "the plan is neither empty nor executable". Section 5b "excluded as platform kills, not results". Section 6 "The metric is selective, not blind"; "uninformative *about this paper's treatment*, not in general". Section 7 "memorised, not planned toward"; "bounds what is *available* to transfer, not what an agent uses".
- **Fix:** exact replacements in section 8. Items tied to F03, F05, F07, F08 are rewritten by those fixes; the rest are mechanical.
- **Owner:** Claude. Screen: citation W4 (numbers W6 lists the same phrases).

### F12 (G8) The release claim is not true today: repos, datasets and both attached notebooks are private
- **Quote:** "Code, data and every experiment log are released with the paper" and "every reported number comes from the released code and traces to a file in the repository."
- **Evidence:** `gh repo view`: `rodriguescarson/arc-agi-3`, `arc-prize-2026`, `Research` are PRIVATE; `arc-prize-2026` has no LICENSE. Live writeup Project Links: both notebooks "Private". Host (discussion 751337): "The notebook should be open source/public at the time of paper submission." The linked submission 57477157 is kernel **version 2** (rev 4033b27); the attached notebook is **version 4** ("Public Score 19.75 | Best Score 29.54 V2"). arcprize.org requires code be open under a permissive licence (CC0 or MIT-0); Franzen's code is Apache-2.0. No URL for any repository appears in the text. Datasets `arc3-harness-bundle` and `py312-portable` also need to be readable.
- **Fix:** Carson makes the repos, datasets and notebooks public (open the notebook Share dialog now to see whether Public is still offered; the ARC-AGI-3 publishing lock value could not be read), adds MIT-0 to `arc_prize_2026`, keeps Franzen's Apache-2.0 notice and credits him by name, scrubs secrets, and attaches the version 2 notebook as primary. Then add the URLs. If anything stays private, delete the "released with the paper" sentence.
- **Owner:** Carson. Screens: venue G8-notebooks, G8-open-source; numbers and citation C13-repo-claim.

### F13 (G8) The live Kaggle writeup was submitted 28 Oct and is already behind the local file
- **Evidence:** live page status "Submitted! You can make changes until the deadline"; live text "All seven of our Intel draws ... 26.56 (SD 3.61)" against local "All nine ... 26.22 (SD 3.57)" (recomputed: 26.220, 3.566). README still says "Before filing".
- **Fix:** after the edits are approved Carson pastes the final text into the existing writeup (edit in place, never delete and recreate; one submission per team), re-checks title, subtitle, cover, project links and track, and separately updates the arcprize.org entry.
- **Owner:** Carson.

---

## 2. WARN findings (24) with dispositions

| ID | Item and quoted text | Disposition | Owner |
|---|---|---|---|
| W01 | G1 type. A pre-specified measurement and negative-result study; past top-3 papers were methods (TRM, 2025). Nearest precedents from the venue: 2024 2nd place "The Surprising Effectiveness of Test-Time Training for Abstract Reasoning"; 2025 honourable mentions "ARC-AGI is a Vision Problem!", "Don't throw the baby out with the bathwater". No ARC-AGI-3 paper precedent exists. | ACCEPT: the track accepts any type and judges on a rubric. Lead with the finding; cite one analysis precedent in the PDF reference list. | Claude |
| W02 | G2 and W7. Title is a question: "What should an agent carry from one level to the next?" The subtitle carries the finding. Option: "Winning Plans Do Not Transfer Between ARC-AGI-3 Levels: What an Agent Should Carry". Avoid an absolute "never" given tn36. | FIX if Carson wants; entry already filed under the current title. | Carson |
| W03 | G3 evidence floor. One LLM base ("on the same Intel base", never named); explorer ablation "Memory on scores 0.277 ... off 0.227" is one seed pair on the development set; no interval printed. | FIX: scope sentence (F01), intervals (F02), name the model (W11). The single-base-model limit cannot be edited away and is stated, not hidden. | Claude drafts |
| W04 | G4 depth. Host: a PDF via the Public Project Link "can be as long as you'd like"; bibliography and appendices do not count. The 1,500-word body cannot hold the full fix set plus references (section 9). | Carson decision (route). | Carson |
| W05 | G5. No earlier rejection, no external review; the only internal evaluation (RUBRIC_SCORECARD, mean 3.5) is stale and about one point high; the paper-screen was never run before the 28 Oct submission. | FIX: refresh scorecard; save this report as `SCREEN-arc-paper-track-2026-10-29.md` in the paper folder (R2) after approval. | Claude |
| W06 | G7 calibration. Editor: mean about 2.5, "would not be sent on" as an above-4.5 paper; pool arithmetic: above 4.5 needs a sum above 27, and with Accuracy 2.0 the other five would all have to be 5.0. | ACCEPT because the venue has no desk stage and every entry is scored; plan on the top-three or credibility, not the $375k pool. See section 8. | Carson |
| W07 | G8 mechanics. Deadlines differ (arcprize.org 8 Nov, Kaggle 9 Nov UTC); code and final selection 2 Nov 23:59 UTC; "up to two Final Submissions". | FIX: file by 8 Nov 23:59 UTC; select finals by 2 Nov. | Carson |
| W08 | G8 licence. arcprize.org wants permissive licence for the submitter's code; Kaggle winner licence CC-BY 4.0; repo licences differ (MIT-0, none, Apache-2.0 third party). | FIX with F12. | Carson |
| W09 | N2 M3. "A mechanics model predicts the next level's movement at 0.740 against a 0.301 null". Mean 0.7395 over 431 pairs; the null is over 421 (10 cd82 pairs have NaN null); same-rows 0.757 against 0.301 (2.52x). Only 10 of the 12 movement games have M3 data; per game 0.99 (dc22) to 0.00 (cd82), tr87 0.36, m0r0 0.30; game-macro mean 0.682. The editor adds that three games hold 48% of pairs and 56 distinct transitions underlie 431. | FIX: abstract "0.740 (pair mean, 10 movement games)"; add "(null over 421 pairs; 0.757 on those)" and the per-game range 0.00 to 0.99. Verdicts do not change. | Claude |
| W10 | N3 object tested. M1 asks whether W_k completes level k+1 "within \|W_k\| actions". The human's own next solution is no longer than that in only 469 of 1,237 pairs (37.9%); the harness shows the model the last 60 actions (30 when pinned) and 330 of 1,237 W_k exceed 60. "That is what [our fork's] `solved_levels()` hands its model" is a hint to adapt, not a script. | FIX: one clause "within \|W_k\| actions (the next human solution is no longer in 469 of 1,237 pairs)"; section 3 "records W_k (last 60 actions)"; say M1 bounds a verbatim replay, not an adaptable hint. Optional run: M1 at 2 x length and prefix reuse. | Carson |
| W11 | N5, N8, G3d dating and model. "All nine of our Intel draws" is an undated moving statistic (v10, a different harness, takes the remaining draws); the model is never named; paired draws differ in kernel version (v2 draws on versions 2 and 4, v1 draws on versions 2 and 5); four variants but only v1 and v2 described. Model: Intel/Qwen3.8-Flash-Next-W4A16-AutoRound; Swift = UkisAI Swift1.5 post-train; draws 19 to 25 Oct (nine through 29 Oct); E21 run 16 Oct. | FIX: mechanical edits in section 8; keep the 29 Oct cutoff if a v10 draw lands. | Claude |
| W12 | N6 other failed predictions. HYPOTHESES.md: P1 level-1 cost not met, P4 accuracy not met, P5 void, H2 and E12, E13, E18 to E20d negative or failed; the paper reports only P21. | FIX (about 20 words): "Its level-1 efficiency (P1) and next-state accuracy (P4) predictions failed, and the click-effect, ordered-goal and goal-proposer extensions (E12, E13, E19 to E20d) were negative or fragile; all are in HYPOTHESES.md." | Carson |
| W13 | C13 copies statistic. "Identical copies of the reference notebook score mean 25.77, standard deviation 3.93" has no source; project notes: Son Pham, forum thread 745062, 2 Oct. Corroboration: arXiv:2610.30499, SD 3.99 over ten repeats. The thread is JavaScript-only and could not be read. | FIX after Carson opens the thread, confirms numbers and whether failed runs were excluded. | Carson |
| W14 | C13 and C6 replays. "all 340 released human sessions"; the release post says 342 replays, the Hugging Face mirror 340; no licence stated (RESEARCH_LOG: "use for analysis/baselines only"). | FIX: "all 340 sessions in the public release mirror (the post counts 342)" once Carson checks the post and licence. | Carson |
| W15 | C13 cause of the two 0.00 draws stated as fact: "The rerun ends a submission when no game moves for 15 minutes, and model loading had slowed past that." It is an inference (forum 750173 plus load times). | FIX: "We attribute them to the platform ending a rerun after 15 minutes without a game move, together with slower model loading." | Claude |
| W16 | C13 cap. "capped at 115": the toolkit allows 115; the local scorer notes the Kaggle Overview says 100; a project note says 1.0. Public-25 numbers come from the local scorer and the paper does not say so. | FIX: "capped per level" now; Carson confirms the Kaggle figure; say "local scorer" once. | Claude / Carson |
| W17 | C6 credits. Not cited: ARC-AGI-3 technical report (scoring, 340 sessions); Siriki's notebook (source of plan memory); "Stochastic Goose" should read StochasticGoose; "AERA" undefined and understated ("partly solve"; it reports null strategies reach all 25); "report 88 to 100 percent" quotes best configurations (PRO-LONG's matched-budget results are 41 to 42 percent); the white-box family names no work. | FIX in the section 2 paragraph (section 7 below). | Claude |
| W18 | C13 leaderboard and units. "1,087 of 4,233 teams sit in the same (0.05, 0.23] band" is the 13 Oct snapshot (now 4,969 teams); "game points" undefined. (v1 mean 27.89 equals Franzen's own leaderboard score; arithmetic verified, coincidence only.) | FIX: "On 13 October, 1,087 of 4,233 teams sat in the same band"; define "game points" or cut the clause. | Claude |
| W19 | F12 figure and cards. `fig6_e21_transfer.png` plotted values match the data, but panel A says "1,237 testable pairs, 25 games" (24 games have a pair), and the text never cites the figure; `card_560x280.png` repeats the unfixed wording; `paper/cover.png` is the stale v1 cover ("no language model · CPU only"). | FIX after F02: regenerate fig6 and card; add "Figure 1" caption; retire cover.png. | Claude |
| W20 | W6 pitch. 32 bold spans (including numerals); recurring economy metaphor ("pays", "buys", "prices", "the paying one", "blind"). | FIX: unbold numerals and table cells (keep the three filed predictions); metaphors replaced by F08 and mechanical edits. | Claude |
| W21 | W-abbrev and terms. LLM, REPL, CNN, AERA, "draw", "Intel"/"Swift", "contact curiosity" (first used in the section 6 table), "E21", "keepalive fix"; "plan memory" / "level memory" / "memory"; "hidden set" / "hidden 55". | FIX: define on first use (section 8); fix terms after F06 settles the label. | Claude |
| W22 | M1 AI-use statement: "produced by the author with an AI coding assistant". No venue rule requires one; wording understates the assistant's role and names no tool. | Carson decides the extent. Proposed: "Claude Code (Anthropic) wrote most of the code, ran the experiments and drafted this text under the author's direction. The author set the hypotheses and pre-registrations, reviewed every change and approved each claim; every reported number comes from the released code or the Kaggle submission list and traces to a file in the repository." | Carson |
| W23 | Sections and linked submission. No Conclusion; the linked submission is one line ("57477157 (`v2-level-memory`), the best level-memory draw, 29.54 on the hidden 55"); selecting the better of two draws biases the score (private score expected near 26); Progress wording differs between arcprize.org and Kaggle. | FIX: add the two-sentence conclusion and one linked-submission sentence (section 7), within the word budget. | Carson |
| W24 | 5a labelling. "**5a. Mechanics memory, controlled (ours, public 25).**" is one seed pair on the development set; two games reach level 2; hidden twin shows 0.08 against 0.08. | FIX: heading "(ours, public 25 development set, one seed)". | Claude |
| N/A | Word limit. `wc -w writeup_v2.md` = **1,498** of 1,500 (Kaggle's counter read 1,464 on the filed text; the live counter must be re-read). Every addition needs an equal cut or the PDF route. | Constraint, see section 9. | |

---

## 3. PASS items (15)

T5 word limit met (1,498, penalty wording only). T6 abstract 196 words, no limit imposed. T8 title, subtitle, track, cover and project links present on the live page. W1 zero em-dashes (0 U+2014, 0 U+2013; the 13 "---" hits are table rules). W2 no banned vocabulary. W3 no placeholders. W5 one spelling convention (UK: colours, recolour, memorised). N2 core E21 counts and rates reproduce exactly (section 5). N2 explorer ablation, hidden-set table and the four LLM draws with 26.22 (SD 3.57) match source. N6 failed predictions P21b and P21c are disclosed ("One of three met"). N7 abstract names only evaluated systems. N4 restatements (abstract, body, README, card) agree with each other; their shared defects are F02 to F08. G8 no fee; solo team; AI-use has no venue rule. Rubric text confirmed (six equal criteria, 0 to 5).

---

## 4. G answers (written)

- **G1.** Type: pre-specified measurement study with reported failures (agent-free human-replay analysis plus two controlled ablations). Venue: ARC Prize 2026 Paper Track (Kaggle writeup, rubric judged, any type). Precedents from the venue: the 2024 2nd-place test-time-training empirical study; 2025 honourable-mention analysis papers ("ARC-AGI is a Vision Problem!", "Rethinking Visual Intelligence: Insights from Video Pretraining", "Don't throw the baby out with the bathwater"). Past top-3 papers were methods. WARN W01.
- **G2.** Editor sentence: "A pre-specified measurement shows that replaying a winning plan never re-solves the next ARC-AGI-3 level while a mechanics model transfers partly, and a level-memory LLM harness cannot be told apart from its twin at two draws per arm." Names ARC-AGI-3, as expected for an ARC-specific venue. The finding leads the Kaggle subtitle, not the title. WARN W02.
- **G3.** Independent validation of the measured quantity: yes (frame-exact fidelity gate, own-solution positive control, shuffled and random controls, full population of 340 sessions). No judge or annotator is needed. Unmet: one LLM base model, explorer ablation one seed pair, no interval printed, and pair-level independence assumed (150 transitions). Headline is a zero rate, so the right interval is an upper bound (0.30% pair-level, 2.5% transition-level). Public set is saturated by other entries, so hidden scores are used where available. WARN W03; closed by F01 and F02.
- **G4.** Design depth is high; the 1,500-word body compresses theory and omits prior-work links. A PDF has no word limit. WARN W04.
- **G5.** No earlier rejection or reviewer point exists. The internal scorecard is stale (W05).
- **G6.** FAIL (F01).
- **G7.** Simulated panel: no desk-reject stage, so the paper goes to full rubric scoring ("send out for review": yes). It would not be sent on as an above-4.5 pool paper (editor FAIL label, venue screen scored it PASS on this basis). I record this as calibration W06, not a venue fail. Scores in section 8.
- **G8.** Fee $0, no purchase necessary. Solo team; one submission per team, edit in place. Review is not blind. Format: Kaggle Markdown writeup (or PDF via Public Project Link). Live link followed 29 Oct: `kaggle.com/competitions/arc-prize-2026-paper-track/writeups/what-should-an-agent-carry-from-one-level-to-the-n`, status Submitted, stale (F13). Notebooks private (F12). FAIL.

---

## 5. Numbers (N2 against source at full precision)

"Merge" = re-run in this merge; "screen" = reported by a screen and matched to files there, not re-run here.

| Paper | Source value | Status | Check |
|---|---|---|---|
| 340 sessions; 309 frame-exact | 340; 309 | PASS | merge |
| 1,314 pairs; 1,237 (94.1%) | 1,314; 1,237 = 94.140% | PASS | merge |
| M1 "0 of 1,237" | 0 of 1,237 (exhausted 1,108, game over 129) | PASS number, FAIL framing (F02) | merge, ends from screen |
| Control 95.6% | 1,182/1,237 = 95.554%; without tn36 1,182/1,186 = 99.663% | PASS; see F02 | merge |
| "0 of 25 games" | 24 games have a pair; 23 with a working control | FAIL | merge |
| tn36 51 of 51, lf52 3 of 64, sc25 1 of 58 | exact | PASS | merge |
| C1 shuffled 0 | 0 of 6,185 | PASS | merge |
| C3 random 0; 188 of 6,185 (3.0%) | 0 of 5,997 evaluated + 188 unevaluable = 6,185 | PASS (all lf52 from screen) | merge |
| P21c "19 of 25" | 19 reproduces; 17 of 20 where a shuffle can differ; pooled 0.4461 against 0.4307 | FAIL (F03) | merge; 17 and ties from screen |
| M3 0.740, ceiling 0.906, null 0.301, 2.5x, 431 pairs | 0.73952; 0.90636; 0.30052; 2.46x; 431 | PASS; null over 421 pairs (W09) | merge, 421 from screen |
| HYPOTHESES "843 pairs" | 843 = all games (0.716, null 0.247, ceiling 0.892) | FAIL (F09) | merge |
| Distinct transitions (not in paper) | 150; 144 without tn36 | new | merge |
| 0.277/13 levels, 0.227/11, +0.050 | v5 log values | PASS | screen |
| 21.2x to 8.6x | 21.24x (10 games), 8.59x (11 games) | PASS; different sets, not stored (F08) | screen |
| "90 percent of 0.280" | 6.324/6.994 = 90.4% | PASS | screen |
| Hidden table 0.15, 0.08, 0.12, 0.08, 0.01 | match the Kaggle list (snapshot saved 29 Oct 00:01 by the numbers screen) | PASS | merge from snapshot |
| Public-25 column 0.277, 0.227, 0.204 | v5, v5, v4 versions; submitted v7 is 0.280 | FAIL (F08) | screen |
| 29.54 / 19.75 mean 24.65; 29.93 / 25.85 mean 27.89; gap 3.2 | 24.645; 27.89; 3.245 | PASS | merge |
| Nine Intel draws 26.22 (SD 3.57) | 26.220; 3.566 | PASS | merge |
| "SD about 5.5", "11 points" | 3.93 x sqrt(2) = 5.56; 2 x = 11.1 | PASS, derivation applies to single draws (F07) | merge |
| "capped at 115" | Kaggle cap not 115 per Overview and notes | WARN W16 | screen |
| Word count | 1,498 | constraint | merge |

---

## 6. Citations (C6, C13)

Live fetch in this merge (arXiv API: title, first author, date) for all 12 ids; GitHub, Kaggle and Hugging Face entries as verified by the citation screen.

| Work | Id or location | Exists and attributed | Issue |
|---|---|---|---|
| ARC-AGI-3 technical report | arXiv:2603.24621, ARC Prize Foundation, 24 Mar 2026 | yes | not cited; "games keep their mechanics" is stronger than the report ("reuse and extend") |
| The Duck (Tufa Labs) | github.com/Tufalabs/duck-harness | yes | uncited; licence not seen |
| Franzen Milestone 2 | github.com/da-fr/arc-agi-3-solution (Apache-2.0); Kaggle dfranzen/arc-agi-3-milestone-2-solution | yes | description wrong (F05) |
| Siriki (rellik13) | Kaggle sirikilohit/arc-agi-3-duck-18-1gc-submit | yes | uncredited as plan-memory source; "22.53" placing unconfirmed |
| StochasticGoose | github.com/DriesSmit/ARC3-solution | yes | misspelled in text |
| Persistent-memory BFS notebook (white-box example) | Kaggle nihilisticneuralnet/0-46-arc-agi-3-persistent-memory-bfs-arc-solver | yes | family unnamed in text |
| Tycho | arXiv:2607.28287 (J. Lehmann, 30 Jul 2026) | yes | best-config range |
| Twin | arXiv:2608.14490 (A. Skoutnev, 14 Aug 2026) | yes | |
| PRO-LONG | arXiv:2607.20064 (A. Fox, 22 Jul 2026) | yes | has its own no-log twin (+18.0); "76.1" in LITERATURE_MAP does not match the PDF text |
| AERA | arXiv:2605.25931 (arXiv lists "Liew Keong Han", 25 May 2026) | yes | understated; acronym undefined |
| NOOA | arXiv:2607.20709 (P. Furgale, 22 Jul 2026) | yes | uncited; +11.8 ablation |
| Tracing | arXiv:2610.11450 (C. Wu, 8 Oct 2026) | yes | uncited, closest prior work |
| Self-harness | arXiv:2610.30499 (J. Lehmann, 21 Oct 2026) | yes | SD 3.99 corroborates the copy SD |
| Schema / VISTA / Memento 3 / Kepler | 2609.39140; 2610.02200; 2610.11794; 2610.00834 | yes | optional (public-set scores near 100%; leakage) |
| Replay release | arcprize.org/blog/arc-agi-3-human-dataset; HF magic-sword/arc_agi_3_public_demo_human_testing | yes | 342 against 340; no licence |
| Pham variance thread | Kaggle discussion 745062 | not readable | Carson to confirm (W13) |

---

## 7. Proposed text and reference list (Claude drafts; Carson approves)

**Section 2 (about 150 words, no bracket tags):** "Entries fall into three families. Harnesses let a language model write Python against the frames: the Duck and Franzen's Milestone-2 solution. Franzen's level-up prompt tells the model to plan afresh and reuse the previous level's mechanics; Siriki's fork pins each cleared level's rule and last 30 winning actions. StochasticGoose is a CNN that predicts whether an action changes the frame and resets at each level. Some notebooks search the public games' source, which hidden games do not expose. Papers report 88 to 100 percent on the 25 public games with their best frontier-model configurations (Tycho, Twin, PRO-LONG), a set that AERA reports reachable by non-intelligent strategies. The memory ablations we found are on public games: PRO-LONG gains 18.0 points over a no-log twin, NOOA 11.8 over plain files, and Tracing finds that agent scripts rarely survive a level change. We found no paired hidden-set comparison of what to carry across levels."

**Abstract if the recommended defaults are accepted (about 205 words):** "ARC-AGI-3 games reuse and extend their mechanics across levels and change their layout, so an agent that has solved level k holds two things it could reuse on level k+1: the **plan** it used, or the **mechanics** it learned. Entries carry a plan, a rule or both from level to level, and none we found measures which helps on hidden games. We measure which transfers, three ways: in the 340 released human replay sessions, in a controlled ablation of our own agent, and in paired hidden-set draws of a large language model (LLM) harness with its `solved_levels()` helper on and off. A winning sequence re-solves the next level in 0 of 1,186 testable pairs (23 games with a working positive control, 144 distinct level transitions; control 99.7 percent), and successive winning sequences are only slightly more alike than a shuffle (0.446 against 0.431). A mechanics model predicts the next level's movement at 0.740 against a 0.301 null, short of our 0.8 bar. The harness comparison is too coarse to confirm or refute anything: two hidden draws per arm average 24.65 with the helper and 27.89 without, a 3.2-point gap inside the 11 points the design resolves. We also find evidence, from one draw per arm, that the hidden metric rewards first-level efficiency and barely registers later-level coverage."

**Section 8 Conclusion (about 55 words):** "Replaying a winning plan completes no next level in human play, and a helper that returns plans moved our harness's hidden score by less than its draw noise. Mechanics predict next-level movement at 0.740, short of the bar we filed. Next entrants should log that a feature is used before crediting it, and report several draws against the copy spread."

**Linked submission (about 30 words):** "57477157 (`v2-level-memory`, kernel version 2): Franzen's Milestone-2 harness plus `solved_levels()` and a reworded budget-bar line; 29.54 hidden, the better of two draws, so expect a private score nearer 26."

**References (numbered in citation order; entries 1 to 14 are core, 15 to 19 optional):**
1. ARC Prize Foundation. ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence. arXiv:2603.24621, 2026.
2. Tufa Labs. The Duck harness, ARC-AGI-3 Milestone #1. github.com/Tufalabs/duck-harness, 2026.
3. D. Franzen. ARC-AGI-3 Milestone 2 solution. github.com/da-fr/arc-agi-3-solution, 2026.
4. L. Siriki (rellik13). arc-agi-3-duck-18-1gc-submit. Kaggle notebook sirikilohit/arc-agi-3-duck-18-1gc-submit, 2026.
5. D. Smit. StochasticGoose. github.com/DriesSmit/ARC3-solution, 2025.
6. nihilisticneuralnet. [0.46] ARC-AGI-3: Persistent Memory BFS ARC Solver. Kaggle notebook, 2026.
7. J. Lehmann, A. Aioanei, S. Vahdati. Tycho: Active Abstraction with Programmatic World Models for ARC-AGI-3. arXiv:2607.28287, 2026.
8. A. Skoutnev et al. Twin: Playing an Unknown Game with a Test-Time Digital Twin. arXiv:2608.14490, 2026.
9. A. Fox et al. PRO-LONG: Programmatic Memory Enables Long-Horizon Reasoning. arXiv:2607.20064, 2026.
10. Liew Keong Han. Explore Before You Solve: The Speed-Depth Trade-off in Epistemic Agents for ARC-AGI-3 (AERA). arXiv:2605.25931, 2026.
11. P. Furgale et al. NVIDIA-labs OO Agents: Native Python Object-Oriented Agents. arXiv:2607.20709, 2026.
12. C. Wu et al. Tracing the Thoughts of a Coding Agent Playing ARC-AGI-3: Lessons for Continual Learning. arXiv:2610.11450, 2026.
13. ARC Prize. ARC-AGI-3 human replay release. arcprize.org/blog/arc-agi-3-human-dataset, 2026 (mirror: huggingface.co/datasets/magic-sword/arc_agi_3_public_demo_human_testing).
14. S. Pham. Variance of identical notebook copies. Kaggle discussion 745062, 2026. (Hold until Carson confirms.)
15. J. Lehmann, S. Vahdati. Can LLMs Improve Their Own Harness? A Controlled Study on ARC-AGI-3. arXiv:2610.30499, 2026.
16. G. Zeng et al. Schema: Discovering Unknown Environments via Agentic Program Induction. arXiv:2609.39140, 2026.
17. Q. Han et al. VISTA: A Visual Harness for Reasoning in an Interactive World. arXiv:2610.02200, 2026.
18. H. Zhao et al. Memento 3: Model-Based Recursive Self-Improvement through Reflective Rulebooks. arXiv:2610.11794, 2026.
19. W. Wu. Kepler: Auditable World Models for ARC-AGI-3. arXiv:2610.00834, 2026.

---

## 8. Editor simulation (G7) and top-5 changes

Scores 0 to 5, editor screen; venue screen and scorecard shown for comparison.

| Criterion | Editor | Venue screen | Scorecard | Reason |
|---|---|---|---|---|
| Accuracy | 2.0 (1.5 to 2.5) | 2 to 3 | 3 | 29.54 against a leaderboard top of 75.56; better of two draws; indistinguishable from unmodified copies |
| Universality | 2.0 | 3 | 3 | one benchmark, one model; fixed only by stating scope |
| Progress | 2.0 (1.5 to 3.0) | 3 | 4 | takeaways exist but no Conclusion states them |
| Theory | 3.0 | 3 to 4 | 4 | one explanatory sentence; two of three filed predictions failed |
| Completeness | 3.0 | 3 to 4 | 4 | linked submission barely described; strong failure disclosure |
| Novelty | 3.0 | 3 | 3 | new question and protocol; agents are forks; novelty claim contradicted (F05) |
| **Mean** | **about 2.5 (2.0 to 3.1)** | about 3 to 3.5 | 3.5 | expected about 2.8 after the changes below |

Rank: the venue screen reports userRank 867 of 4,969; the editor pages the leaderboard and finds 29.54 near row 980. Both are consistent: the team's leaderboard score is its best draw (29.93, the v1 arm), which sits near 867; 29.54 alone sits near 980. This is an inference, not re-measured here; re-pull the rank on filing day before printing any.

Top-5 changes, merged from the editor's CHG1 to CHG5 with the other screens' corrections:
1. Correct section 2 and the arm labels (F05, F06): the single most damaging error, because a judge who opens Franzen's write-up or the variant JSON can cut Novelty and Theory by a point.
2. Make the abstract and section 4 numbers true and consistent (F02, F03, F07): 1,186 / 23 / 99.7%, the M2 count, the "agrees" sentence.
3. Add scope and a Conclusion (F01, W23): answers Universality and Progress and closes G6.
4. Describe the linked submission and its provenance (W23, F12): Completeness; state the selection effect.
5. Repair section 6 (F08): relabel the public column and drop "sevenfold ... refutes".
Superseded or unsafe editor details: "12 of 25 with interval above zero" (bootstrap code not in the repo); "rellik13 (22.53)" (placing unverified); "ranked about 980th" (see above); "Papers report up to 100 percent" (use the citation screen's wording). The editor's full candidate (`.../paperscreen/G7/writeup_v2_G7_proposed.md`, 1,500 words) predates these corrections and must not be pasted as is.

---

## 9. Word budget (the 1,500 limit is the binding constraint)

Approximate, if every recommended default is accepted. Additions: scope +28, M1 and M2 wording +18, pre-registration +14, section 2 +50, arm confound +30, agrees +5, model, dates and definitions +24, M1-budget clause +12, other-failed-hypotheses +20, Conclusion +55, linked submission +30, abstract +9; about **+295**. Cuts available: caveat paragraph -40, earlier-draws paragraph -25, section 6 rewrite -30, section 6 closing clause -20, headings and parallelism fixes -20; about **-135**. Net about **+160**, so about 1,660 by `wc -w` (about 1,625 by Kaggle's counter), roughly 125 over, before references (+146 to +190 if counted).

Therefore either (a) test the counter first (paste draft plus references into the Kaggle editor; if references are excluded, cut about 125 more: drop W12, shorten the Conclusion, drop item 14), or (b) attach a PDF as the main paper (no word limit; bibliography and appendices excluded; the PDF must then pass T, F, V and C checks) and keep a 1,500-word Writeup as a standalone summary. Recommended: (b) with the Writeup carrying F01 to F09 only. Say in the Writeup which document is the main submission.

---

## 10. Where the screens disagreed and how it was resolved

- **Verdict:** venue screen FIX FIRST despite G6 FAIL; rule applied, WRONG VENUE (section 1).
- **G7:** venue PASS (scored about 3 to 3.5), editor FAIL (about 2.5); reconciled as calibration W06.
- **"six games record no movement":** numbers screen called it seven. Seven games have zero M3 steps (ft09, lp85, r11l, s5i5, su15, tn36, vc33) but the text names s5i5 separately, so "six" is correct; add "other" to remove the ambiguity (not a defect).
- **PRO-LONG range:** numbers screen "76 to 100" (from LITERATURE_MAP "76.1"); citation screen read the PDF, where 76.1 is only a chart value. Used the citation screen: best configurations, not a floor.
- **Which M2 count:** 19 (filed rule, reproduced), 17 of 20 (non-degenerate, screen), 12 (two methods, not reproducible from the repo). Print 19 and 17; hold 12.
- **M1 framing:** numbers offered A or B, editor B, venue (a) or (b); B recommended, decision is Carson's.
- **Rank:** 867 against 980 reconciled above.
- **Pre-registration:** editor "genuine" against numbers "false": both partly right (F04).

---

## 11. Not verified in this merge

Re-run here: E21 recompute (all counts above), nine-draw statistics, 12 arXiv ids, the Franzen prompt quotes, the v1 and v2 variant configuration, word count. Taken from the screens and not re-fetched: Kaggle forum posts and thread contents, live writeup page state, GitHub privacy and push timestamps, Kaggle rank and leaderboard, explorer and EXPERIMENT_LOG values, the Kaggle overview cap and deadline wording, the 29 Oct Kaggle submission list (read from the numbers screen's saved CSV).
