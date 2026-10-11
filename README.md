# arc-agi-3 — ARC Prize 2026, ARC-AGI-3 track

Carson Rodrigues' entry for the Kaggle competition
[arc-prize-2026-arc-agi-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
(final submissions 2026-11-02 23:59 UTC).

The agent is an LLM in a Python REPL: Qwen3.8-Flash-Next (Intel AutoRound W4A16 + Albucino MTP
draft, served by SGLang "Pennyroyal") plays each game through Tufa Labs' Duck harness as extended
by Daniel Franzen for Milestone 2. This repository owns the deployment pipeline, the configuration
variants, local CPU tooling, and the harness changes layered on top of Franzen's tree.

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

## Licences

Our code: MIT-0 (see LICENSE). `harness/ARC3-Inference` is Apache-2.0 (Daniel Franzen, 2026,
on top of Tufa Labs' MIT Duck harness); `harness/tufa-arc-agi-framework` is MIT (Tufa Labs).
Model weights and the serving wheelhouse are third-party artefacts under their own licences;
they are referenced by Kaggle dataset/model id, not vendored.
