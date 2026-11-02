# Post-competition retro: to do

Open. Written 2026-11-02, the day the code submissions closed. Do it once the material exists: the paper track
closes 9 Nov 23:59 UTC, and private scores and prizes are announced 4 Dec 2026. Kaggle makes notebooks that are
linked to writeups public when the competition ends.

## Where we ended

- Best public draw 29.93 (57372857, v1, Franzen's notebook unchanged); 988th of 5,032 teams on 1 Nov.
- Top of the public board on 1 Nov: 75.56 (Yi-Chia Chen @ Fields Model), 70.24 (Tufa Labs), 58.59 (faster
  machine is all you need), 56.15 (NVARC3), 56.02 (Team Turducken); 77 teams at 35 or above.
- Our 13 valid Intel draws average 26.35 (SD 3.18). Every variant we built (v1f, v2, v8i, v10; v11 and v11m in
  trials) sits inside draw noise around Franzen's baseline. Details: `docs/TASKS-2026-10-29.md`, `docs/SUBMISSIONS.md`.
- The gap was visible early: on 18 Oct the top three were already at 68.91, 67.49 and 50.37 (memory note
  "Top 3 are private"), and none of them had published anything.

## Questions to answer

1. **What did the teams above 50 do?** For each of the top 10, and any team that jumped late, read the writeup,
   the public notebook and the discussion posts, and note: base model and size, serving stack, harness design
   (REPL, tools, memory, search), any offline training or fine-tuning, game-specific code or priors, compute per
   game, and how they used the 9-hour budget.
2. **Which of their ideas were open to us?** Sort every idea into: available to us and not tried; tried and
   dropped (say why, with the evidence we had then); impossible for us (compute, data, money).
3. **Why did we not find it?** Check our own assumptions against what they did. Candidates to test, not
   conclusions:
   - "No bigger or better model is servable on the RTX Pro 6000" (`TASKS-2026-10-29.md`, P3).
   - "No public notebook beats noise", taken to mean no available method beats Franzen.
   - "The scored run is time-bound, so throughput is the lever."
   - Building our search around the public Franzen forks after the 18 Oct finding that the top three had
     published nothing.
   - Time split: paper work and daily-draw infrastructure against score work after mid-October.
4. **Why did we not act once the gap was clear?** From 18 Oct to 2 Nov we ran small, noise-level variants. Was
   there a decision point where a different bet (new model, new harness, offline training) was still possible,
   and what stopped us: compute quota, the deadline, the paper, or not seeing the option?
5. **What would we do differently?** Three to five concrete lessons, each tied to evidence from 1-4.

## Output

- `docs/RETRO-2026.md`: the answers, with links to every source read.
- The lessons added to the `competition-playbook` skill, so the next competition starts from them.

## Sources to read

- Kaggle ARC-AGI-3 leaderboard history and the top teams' writeups and notebooks (public after the competition).
- ARC Prize 2026 paper-track writeups (kaggle.com/competitions/arc-prize-2026-paper-track/writeups).
- The ARC-AGI-3 discussion forum, especially "solution" posts after 2 Nov.
- arcprize.org results and the ARC Prize 2026 technical report when published.
