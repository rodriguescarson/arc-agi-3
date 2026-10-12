# Kaggle runbook

Account: `carsonrodrigues` (token in `~/.kaggle/kaggle.json`). CLI: `.venv/bin/kaggle` (2.2.4).

## One-time inputs (already created, private)

| Kaggle ref | built by | contents |
|---|---|---|
| `carsonrodrigues/arc3-harness-bundle` | `python kaggle/build_bundle.py --push` | `src/` = `harness/` + Tufa's two pickles |
| `carsonrodrigues/py312-portable` | by hand (see kaggle/build/python312) | CPython 3.12.15 install_only tarball (`.tgz.bin`) |
| `phuongncn/arc3-qwen38-swift-w4a16-autoround` (public model, two PyTorch instances `w4a16-a`/`w4a16-b`) | Fususu | verbatim mirror of `ukisai/Swift-1.5-Qwen3.8-Flash-Next-W4A16-AutoRound` (177 GB); v3 target, re-assembled into one directory of symlinks by cell 00 (`model_parts`) |
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

**GPU quota (checked 2026-10-12):** the account had used 37 h of the 30 h weekly allowance; it refreshes
**2026-10-17 00:00 UTC**. `kaggle kernels push` for a GPU kernel fails with "Maximum weekly GPU quota
reached" until then. Check with
`.venv/bin/python -c "from kaggle.api.kaggle_api_extended import KaggleApi as K;a=K();a.authenticate();a.quota_view_cli()"`.
The CPU variant `kaggle/variants/v1-cpucheck.json` (kernel `arc3-duck-v1-cpucheck`) exercises everything
except the model server and costs no quota.

`--push` is a *commit* (Save & Run All). On the RTX Pro 6000 it waits in a queue that has
been 8 h long, then runs the smoke configuration (two public games, ~35 min including the
~9 min model load). It consumes the weekly 30 h GPU quota; the scored rerun does not.

Variants: `v1-franzen-faithful`, `v3-swift` (kernel `arc3-duck-v3-swift`), `v2-level-memory`,
`v4-effort-medium` (kernel `arc3-duck-v4-effort`). CPU checks (no quota): `v1-cpucheck`, `v3-cpucheck`.
`v3-swift` attaches the Intel checkpoint as `fallback_model`: if the Swift server exits before it is
healthy, cell 40 relaunches on the Intel checkpoint and writes `served_model.txt` (status + path) to the
output, so check that file before logging which model a draw came from.

Free source probes: `kaggle/probes/sglang-src-probe/` is a CPU script kernel that unzips the Pennyroyal
SGLang wheel and prints the loader code paths (used to check Swift's quantised attention layers).
A variant's `serve_cfg` overrides cell 40's `CFG` (e.g. `PATCH_GDN_PACKED_IN_PROJ`, the Swift loader
patch; `SPEC`, `FRSPEC`, `MAXREQ`, ...). Server outcome per run: `served_model.txt` in the output.

## Automation (default from 2026-10-13): `.github/workflows/daily-submit.yml`

`kaggle/daily.py tick` runs every two hours on GitHub Actions (secrets `KAGGLE_USERNAME` /
`KAGGLE_KEY`; schedule in `kaggle/plan.json`). It submits one kernel version per UTC day and keeps
one commit in flight so the next variant is complete before midnight:

1. **Before `start_utc` (2026-10-17 00:05 UTC):** only the `pre_start_tests` (the zero-score
   `arc3-duck-v3-cpucheck` v1 on 2026-10-13) to prove the submit call, the competition rerun of our
   cells and the scoring pipeline.
2. **Order phase:** `order` = v1, v3, v2, v4. The first tick of a UTC day submits the target's latest
   COMPLETE version (message `arc3-auto variant=... kernel=... version=... rev=...`), then pushes the
   next variant (Save & Run All, smoke config, ~35 min of GPU quota).
3. **Best phase (order done, or after `freeze_utc`):** re-submit the variant with the best public
   score; completed versions are reused, so no further pushes unless a variant file changes.

Reads come from Kaggle (submissions, scores, kernel status). Which version belongs to which variant
and when a push was last tried is kept in `state.json` on the `automation/state` branch (never main).
A push or submit failure after the start date fails the job, so GitHub emails the failure. Check
`Actions -> daily-submit` job summaries, or run `python kaggle/daily.py report`. Manual pushes to the
`arc3-duck-*` kernels would confuse the "latest version" bookkeeping: let the bot own them, or edit
the state branch.

Dry run: `gh workflow run daily-submit.yml -f dry_run=true`, or locally
`PYTHONPATH=. .venv/bin/python kaggle/daily.py tick --dry-run --now 2026-10-17T00:20:00Z`.

## Submit by hand (fallback; one per day, 23:59 UTC boundary)

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
