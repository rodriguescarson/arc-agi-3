# Validating a variant on a rented RTX Pro 6000 (not executed; Carson's money)

Only worth doing for a question Kaggle cannot answer in one day, e.g. "does the REAP-pruned
NVFP4 model boot with this SGLang config and what is its decode tok/s?".

Cost: RTX Pro 6000 96 GB on RunPod is roughly $1.5-2.0 / h (check the catalogue). A boot +
2-game check is ~45 min; a full 25-game pass at Franzen's settings is ~4 h.

## Recipe

```bash
# on the pod (Ubuntu 22.04/24.04, CUDA 13 driver, 192 GB RAM recommended because the
# BF16 PLE table is offloaded to host memory)
pip install kaggle
export KAGGLE_API_TOKEN=...            # Carson's token, never commit it
mkdir -p /work && cd /work
kaggle datasets download dfranzen/pennyroyal-v253 --unzip -p pennyroyal-v253
kaggle models instances versions download dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1 -p model --untar
kaggle models instances versions download dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1 -p draft --untar
kaggle datasets download carsonrodrigues/arc3-harness-bundle --unzip -p bundle
kaggle competitions download -c arc-prize-2026-arc-agi-3 -p comp && unzip -q comp/*.zip -d comp
```

Then run the notebook cells as a script. The simplest way is `jupyter nbconvert --to script
kaggle/build/<variant>/submission.ipynb` with these environment overrides before executing:

- `KAGGLE_IS_COMPETITION_RERUN` unset (smoke/offline path),
- replace the `/kaggle/input/...` roots in cell 00's `_resolve_input` candidates with `/work/...`,
- `/kaggle/working` -> `/work/working`.

`runpodctl stop pod $RUNPOD_POD_ID` from inside the pod when the run ends. Never leave it idle.

## What to record

`serve.log` (startup time, tok/s lines), `diagnostics.html`, per-game scores, and the exact
variant JSON. Put the numbers in `docs/SUBMISSIONS.md` next to the Kaggle draw.
