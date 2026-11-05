ARC-AGI-3 LLM agent harness for Kaggle notebooks: the source code behind Carson Rodrigues' entry to **ARC Prize 2026 (ARC-AGI-3)**. Attach it to a notebook to run the same Duck / Franzen Milestone-2 harness, with the level-memory and reliability changes studied in the paper *What should an agent carry from one level to the next?*

## What is inside

| path | what it is | licence |
|---|---|---|
| `src/ARC3-Inference/` | Tufa Labs' Duck harness as extended by Daniel Franzen for Milestone 2, plus this entry's changes behind default-off switches: level memory (`solved_levels()`), `navigate_to`, start-up hardening, a guarded RESET, recovery after cut-off replies, and an attempt-loss stop | Apache-2.0 for Franzen's fork (`LICENSE.franzen-apache-2.0`); the new modules `inference/utils/level_memory.py`, `navigation.py`, `attempt_loss.py` and `reset_guard.py` are MIT-0 (`LICENSE-MIT-0.txt`); edits inside Franzen's files stay Apache-2.0 |
| `src/tufa-arc-agi-framework/` | TAAF, Tufa Labs' ARC-AGI framework, with small default-off start-up hardening edits in `taaf/benchmark.py` and `taaf/game_api.py` | MIT as stated by Tufa Labs; no licence file ships with it upstream (see `NOTICE`) |
| `benchmark_initial.pkl`, `deploy_target.pkl` | Tufa Labs' benchmark and deploy-target pickles, copied verbatim from `dfranzen/taaf-kaggle-source-bundle-copy` | no licence stated upstream |
| `LICENSE.franzen-apache-2.0`, `LICENSE-MIT-0.txt`, `NOTICE` | the licence texts and the third-party notice | |
| `README.dataset.md`, `git_status.txt`, `preamble.txt` | build record: the git revision of rodriguescarson/arc-agi-3 the bundle was built from | |

## How it is used

The `carsonrodrigues/arc3-duck-*` notebooks add this dataset as an input next to the model and wheelhouse inputs. In the scored Intel variants the model is Intel/Qwen3.8-Flash-Next-W4A16-AutoRound with the Albucino MTP draft, served by SGLang (Franzen's "Pennyroyal" wheelhouse), and the harness lets the model write Python against the game frames. Cell 00 of the notebook (`kaggle/cells/00_env.py` in the GitHub repository) finds the bundle under either Kaggle input layout. The bundle is rebuilt and versioned with `python kaggle/build_bundle.py --push`.

## Results

On the 55 hidden ARC-AGI-3 games scored on the public leaderboard, the best draw of this harness is 29.93 (v1, with every added switch off), and the thirteen valid draws across five variants average 26.35 (SD 3.18), in line with an unmodified copy of the notebook it forks. With the `solved_levels()` helper on (together with a reworded budget-bar prompt line), two draws averaged 24.65; with it off, 27.89. How often the model called the helper is unknown, and the 3.2-point gap is smaller than run-to-run noise, so the paper claims no effect either way.

## Links

- Competition: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Paper (PDF): https://github.com/rodriguescarson/arc-prize-2026/blob/main/paper/level-transfer/paper/paper_full.pdf, also filed as a writeup in the ARC Prize 2026 Paper Track: https://www.kaggle.com/competitions/arc-prize-2026-paper-track
- Harness and deployment code: https://github.com/rodriguescarson/arc-agi-3
- Paper code, data and experiment logs: https://github.com/rodriguescarson/arc-prize-2026
- Companion dataset: https://www.kaggle.com/datasets/carsonrodrigues/py312-portable (Python 3.12 for the cp312 wheelhouses)

## Licence

The Kaggle licence field is set to Apache 2.0 because most of the bundled code (Franzen's harness) is Apache-2.0. The table above gives the licence of each part; the field does not relicense TAAF, the MIT-0 modules or the pickles.
