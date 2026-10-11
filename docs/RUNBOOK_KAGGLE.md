# Kaggle runbook

Account: `carsonrodrigues` (token in `~/.kaggle/kaggle.json`). CLI: `.venv/bin/kaggle` (2.2.4).

## One-time inputs (already created, private)

| Kaggle ref | built by | contents |
|---|---|---|
| `carsonrodrigues/arc3-harness-bundle` | `python kaggle/build_bundle.py --push` | `src/` = `harness/` + Tufa's two pickles |
| `carsonrodrigues/python312-standalone` | by hand (see kaggle/build/python312) | CPython 3.12.15 install_only tarball |
| `dfranzen/pennyroyal-v253` (public) | Franzen | SGLang Pennyroyal 2.5.3 cp312 wheelhouse |
| `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround` (public model) | Franzen | target weights, 17 shards |
| `dfranzen/albucino-qwen3-8-flash-next-drafter` (public model) | Franzen | MTP draft |

Re-run `build_bundle.py --push` after every harness change; it versions the dataset.
Make both datasets **public** before the deadline (prize rule).

## Build and commit a variant

```bash
.venv/bin/python kaggle/build_notebook.py kaggle/variants/v1-franzen-faithful.json --push
.venv/bin/kaggle kernels status carsonrodrigues/arc3-duck-v1
.venv/bin/kaggle kernels output carsonrodrigues/arc3-duck-v1 -p data/runs/arc3-duck-v1   # log + diagnostics.html
```

`--push` is a *commit* (Save & Run All). On the RTX Pro 6000 it waits in a queue that has
been 8 h long, then runs the smoke configuration (two public games, ~35 min including the
~9 min model load). It consumes the weekly 30 h GPU quota; the scored rerun does not.

## Submit (one per day, 23:59 UTC boundary)

1. Wait for status `complete`.
2. Open https://www.kaggle.com/code/carsonrodrigues/arc3-duck-v1, pick the version, click
   **Submit to Competition**, choose `submission.parquet`.
3. Log it in `docs/SUBMISSIONS.md` (variant, version, date, public score when it lands ~9 h later).

## Things that will bite

- **Python 3.13 image.** New notebooks pin to the 2026-10-01 image. Cell 00 picks
  `/usr/bin/python3.12` for the SGLang venv (present on the image as of 2026-10-12), else
  extracts the standalone tarball. Keep `docker_image_pinning_type: original` so the image never
  drifts under a notebook that has worked.
- **Accelerator.** The push uses `--accelerator NvidiaRtxPro6000`; if a version shows up on a
  different GPU, fix it in the notebook sidebar before committing.
- **Budget check.** `bm.run` is told the 9 h budget by `deploy_target.pkl`; the smoke run uses a
  soft end from `smoke.total_minutes` instead.
- **Zero-score reruns.** If the server never comes up, the warmup RESET on one game still
  produces a valid (zero) submission. Check `serve.log` in the commit output for the cause.
- **Model dataset removal.** All model/wheelhouse inputs belong to Franzen. If they disappear,
  mirror them (`kaggle models` / `datasets` uploads of ~90 GB) before the next commit.
