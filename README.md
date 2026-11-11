# ARC-AGI-3 LLM agent for ARC Prize 2026 (Kaggle)

An LLM agent harness and Kaggle notebook pipeline for ARC-AGI-3: Carson Rodrigues' entry for the Kaggle
competition [arc-prize-2026-arc-agi-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
(final submissions closed 2026-11-02 23:59 UTC).

By [Carson Rodrigues](https://carsonrodrigues.com) ([Kaggle](https://www.kaggle.com/carsonrodrigues), [ORCID](https://orcid.org/0009-0001-7195-6742)). The paper and every public part of the entry are listed at [carsonrodrigues.com/research](https://carsonrodrigues.com/research#paper-22).

The agent is an LLM in a Python REPL: Qwen3.8-Flash-Next (Intel AutoRound W4A16 + Albucino MTP
draft, served by SGLang "Pennyroyal") plays each game through Tufa Labs' Duck harness as extended
by Daniel Franzen for Milestone 2. This repository owns the deployment pipeline, the configuration
variants, local CPU tooling, and the harness changes layered on top of Franzen's tree.

Its best draw on the 55 hidden games scored on the public leaderboard was 29.93 (v1, all added switches off); the
thirteen valid draws across five variants average 26.35 (SD 3.18). The paper that uses it, *What should an agent
carry from one level to the next?*, is in [rodriguescarson/arc-prize-2026](https://github.com/rodriguescarson/arc-prize-2026)
([PDF](https://github.com/rodriguescarson/arc-prize-2026/blob/main/paper/level-transfer/paper/paper_full.pdf)) and was
filed as a [writeup](https://www.kaggle.com/competitions/arc-prize-2026-paper-track/writeups/what-should-an-agent-carry-from-one-level-to-the-n) in the [ARC Prize 2026 Paper Track](https://www.kaggle.com/competitions/arc-prize-2026-paper-track).
The GPU notebooks mount two Kaggle datasets:
[arc3-harness-bundle](https://www.kaggle.com/datasets/carsonrodrigues/arc3-harness-bundle) (the harness source, built
from this repository by `kaggle/build_bundle.py`) and
[py312-portable](https://www.kaggle.com/datasets/carsonrodrigues/py312-portable) (an unmodified python-build-standalone
CPython 3.12 for the cp312 wheelhouses); their descriptions are kept in `kaggle/datasets/`. How to cite:
[`CITATION.cff`](CITATION.cff).

```
harness/        vendored harness tree deployed to Kaggle
  ARC3-Inference/            Franzen's fork of the Duck harness (Apache-2.0) + our changes
  tufa-arc-agi-framework/    TAAF, Tufa Labs (MIT)
kaggle/
  cells/*.py                 notebook cells (Franzen's, adapted; tokens filled per variant)
  variants/*.json            one JSON per submission configuration
  build_notebook.py          renders + pushes a variant   (python kaggle/build_notebook.py <variant> --push)
  build_bundle.py            builds + pushes the harness source-bundle dataset
arc3/                        CPU tooling: score formula, offline evaluator, random/explorer agents
tests/                       pytest (CPU only, seconds)
docs/                        COMPETITION, LANDSCAPE, PLAN, RUNBOOK_KAGGLE, RUNBOOK_RUNPOD, SUBMISSIONS
data/                        downloaded competition data and reference notebooks (gitignored)
```

## Quick start (Mac / CPU)

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
kaggle competitions download -c arc-prize-2026-arc-agi-3 -p data/kaggle && unzip -q data/kaggle/*.zip -d data/kaggle
PYTHONPATH=. .venv/bin/python -m pytest
.venv/bin/python -m arc3.local_eval --agent explorer --games ls20,vc33   # offline engine, ~3,700 steps/s
```

## Ship a variant to Kaggle

```bash
.venv/bin/python kaggle/build_bundle.py --push                                  # after harness/ changes
.venv/bin/python kaggle/build_notebook.py kaggle/variants/v1-franzen-faithful.json --push
.venv/bin/kaggle kernels status carsonrodrigues/arc3-duck-v1
```

Then "Submit to Competition" on the kernel page (one per day). Details, hazards and the
Python 3.13 image workaround: `docs/RUNBOOK_KAGGLE.md`. Why this plan: `docs/PLAN.md`.

## Author and citation

[Carson Rodrigues](https://carsonrodrigues.com) is the author of this entry, its harness changes, the notebook pipeline and the paper. GitHub's "Cite this repository" button reads `CITATION.cff`; in BibTeX:

```bibtex
@misc{rodrigues2026carry,
  author       = {Rodrigues, Carson},
  title        = {What should an agent carry from one level to the next?},
  year         = {2026},
  howpublished = {ARC Prize 2026 Paper Track entry, Kaggle},
  url          = {https://github.com/rodriguescarson/arc-prize-2026/blob/main/paper/level-transfer/paper/paper_full.pdf}
}
```

## Licences

Our code: MIT-0 (see LICENSE; third-party parts are listed in NOTICE). `harness/ARC3-Inference` is Apache-2.0 (Daniel Franzen, 2026,
on top of Tufa Labs' MIT Duck harness); `harness/tufa-arc-agi-framework` is MIT (Tufa Labs).
Model weights and the serving wheelhouse are third-party artefacts under their own licences;
they are referenced by Kaggle dataset/model id, not vendored.

**Current state and how the automation works: [docs/STATUS.md](docs/STATUS.md).**
