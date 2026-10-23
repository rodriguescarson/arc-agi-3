# Environment, mode and configuration.
# Adapted from Daniel Franzen's ARC-AGI-3 Milestone 2 notebook (Apache-2.0,
# https://github.com/da-fr/arc-agi-3-solution), itself built on Tufa Labs' Duck harness (MIT).
# Changes vs upstream: the harness comes pre-patched from our own source-bundle dataset (no
# `git apply` step); a CPython 3.12 interpreter is selected for the cp312 wheelhouse; a short
# "smoke" configuration is used for interactive commits so a Save & Run All costs minutes of
# GPU quota instead of nine hours.  The real competition rerun is unchanged.
import json
import os
import pickle
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

NOTEBOOK_START_TIME = time.time()
NOTEBOOK_START_EPOCH = NOTEBOOK_START_TIME
VARIANT = __VARIANT__
print(f"arc-agi-3 notebook variant {VARIANT!r}; python {sys.version.split()[0]} at {sys.executable}")

# Kaggle might cancel the run if no action is done in some timeframe.  The harness starts
# even if the backend is not ready yet, and the first started game performs a single RESET.
SERVER_STARTUP_TIMEOUT = __SERVER_STARTUP_TIMEOUT__
os.environ["ARC3_WARMUP_ACTION_GAMES"] = "1"
# Each game's first request waits this long for the server before failures start to count
# (10 in a row abandon the game). 900 s was Franzen's; on 2026-10-23 weights took 24+ minutes
# to load and the server was not up 40 minutes after start, so a game whose grace ran out
# first would be abandoned. 90 minutes covers it; it only applies until the first request lands.
os.environ["ARC3_HTTP_RETRY_INITIAL_SECONDS"] = "5400"
# Keepalive (2026-10-23): the rerun ends after 15 minutes without a move, and slow mounts now
# push server readiness past that. The warmup game RESETs every 5 minutes until /health is 200.
os.environ["ARC3_WARMUP_KEEPALIVE_SECONDS"] = "300"
os.environ["ARC3_WARMUP_HEALTH_URL"] = "http://127.0.0.1:8001/health"

# ---- attached inputs (all public Kaggle datasets / models) ----
INPUTS = __INPUTS__
# e.g. {"wheelhouse": "dfranzen/pennyroyal-v253", "bundle": "carsonrodrigues/arc3-harness-bundle",
#       "py312": "carsonrodrigues/py312-portable",
#       "model": "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1",
#       "draft": "dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1"}
# A checkpoint split over several model instances uses "model_parts": [ref, ref, ...] instead of
# "model"; an optional "fallback_model" is served if the primary never becomes healthy.


def _resolve_input(ref: str, *, model: bool = False, required: bool = True) -> str:
    """Kaggle mounts datasets at /kaggle/input/datasets/<owner>/<slug> (new layout) or
    /kaggle/input/<slug> (old layout); models at /kaggle/input/models/<owner>/<slug>/<fw>/<v>/<n>."""
    if not ref:
        return ""
    parts = ref.split("/")
    candidates = []
    if model:
        candidates.append(Path("/kaggle/input/models").joinpath(*parts))
        candidates.append(Path("/kaggle/input/models").joinpath(parts[0], parts[1], parts[2].lower(), *parts[3:]))
        candidates.append(Path("/kaggle/input").joinpath(parts[1], *parts[2:]))
    else:
        candidates.append(Path("/kaggle/input/datasets").joinpath(*parts))
        candidates.append(Path("/kaggle/input").joinpath(parts[-1]))
    for c in candidates:
        if c.is_dir():
            return str(c)
    if required:
        raise FileNotFoundError(f"attached input {ref!r} not found; tried {[str(c) for c in candidates]}")
    return ""


def _competition_dir(slug: str = "arc-prize-2026-arc-agi-3", root: Path = Path("/kaggle/input")) -> Path:
    """The competition's own input (arc_agi_3_wheels, environment_files) follows the same two
    layouts: /kaggle/input/competitions/<slug> or /kaggle/input/<slug>. Kernels created on
    2026-10-18 got the flat one while older kernels kept the nested one, and a hard-coded nested
    path made pip find no arc-agi wheel (v1, v2, v7 died in 15 s)."""
    candidates = [root / "competitions" / slug, root / slug]
    for c in candidates:
        if (c / "arc_agi_3_wheels").is_dir():
            return c
    raise FileNotFoundError(f"competition input not found; tried {[str(c) for c in candidates]}")


def _merged_model_view(refs: list[str], view: Path) -> str:
    """A checkpoint uploaded as several Kaggle model instances (50-file limit per instance) is
    re-assembled as one directory of symlinks, so the loader sees a single HF-layout checkpoint."""
    parts = [Path(_resolve_input(ref, model=True)) for ref in refs]
    shutil.rmtree(view, ignore_errors=True)
    view.mkdir(parents=True, exist_ok=True)
    linked = 0
    for part in parts:
        for src in sorted(part.rglob("*")):
            if not src.is_file():
                continue
            dest = view / src.relative_to(part)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() or dest.is_symlink():
                raise RuntimeError(f"duplicate file across model parts: {src.relative_to(part)}")
            dest.symlink_to(src.resolve())
            linked += 1
    for required in ("config.json", "model.safetensors.index.json", "tokenizer.json"):
        assert (view / required).exists(), f"merged model view lacks {required}; parts={parts}"
    print(f"merged {len(parts)} model parts into {view}: {linked} files")
    return str(view)


WHEELHOUSE_DIR = _resolve_input(INPUTS["wheelhouse"])
if INPUTS.get("model_parts"):
    MODEL_DIR = _merged_model_view(list(INPUTS["model_parts"]), Path("/kaggle/arc3-model-view"))
else:
    MODEL_DIR = _resolve_input(INPUTS["model"], model=True)
# Optional second checkpoint: if the primary server never becomes healthy, cell 40 relaunches
# with this one so the day's submission slot still produces a real run.
FALLBACK_MODEL_DIR = _resolve_input(INPUTS.get("fallback_model", ""), model=True, required=False)
DRAFT_MODEL_DIR = _resolve_input(INPUTS["draft"], model=True)
BUNDLE_SOURCE_DIR = _resolve_input(INPUTS["bundle"])
PY312_DATASET_DIR = _resolve_input(INPUTS["py312"], required=False)
COMPETITION_DIR = _competition_dir()
SERVED_MODEL_NAME = __SERVED_MODEL_NAME__
print({"wheelhouse": WHEELHOUSE_DIR, "model": MODEL_DIR, "fallback_model": FALLBACK_MODEL_DIR, "draft": DRAFT_MODEL_DIR, "bundle": BUNDLE_SOURCE_DIR, "py312": PY312_DATASET_DIR, "competition": str(COMPETITION_DIR)})

# ---- the harness source bundle: copy to a writable location ----
BUNDLE_DIR = Path("/kaggle/arc3-bundle")
shutil.rmtree(BUNDLE_DIR, ignore_errors=True)
shutil.copytree(BUNDLE_SOURCE_DIR, BUNDLE_DIR)
print("bundle:", (BUNDLE_DIR / "git_status.txt").read_text().strip())

# ---- true competition rerun vs interactive commit ----
TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
os.environ["MPLBACKEND"] = "Agg"
os.environ["TAAF_RUN_AS_SUBMISSION"] = "1" if TRUE_SUBMISSION else "0"
os.environ["TAAF_MINIMAL_DIAGNOSTICS"] = "1" if TRUE_SUBMISSION else "0"
# Pin arc_agi's cached level_reset_only before its client is built (RESET keeps the level).
os.environ["ONLY_RESET_LEVELS"] = "true"
WORKING_DIR = Path("/kaggle/working")
WORKING_DIR.mkdir(parents=True, exist_ok=True)
print(f"taaf.kaggle: TRUE_SUBMISSION={TRUE_SUBMISSION}")

# ---- smoke configuration for interactive commits (ignored in the real rerun) ----
SMOKE = __SMOKE__
# e.g. {"games": ["ls20", "vc33"], "minutes_per_game": 20, "total_minutes": 40, "passes": 1}

# ---- smoke mode: "gpu" (full server, two games) or "cpu" (pipeline check, no GPU quota) ----
def _has_gpu() -> bool:
    try:
        return subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=20).returncode == 0
    except Exception:
        return False


def _smoke_mode(configured, true_submission, has_gpu) -> str:
    """A GPU variant always serves the model in the rerun.  A CPU-check variant keeps the CPU
    path there too, so its scored rerun yields a valid near-zero score instead of crashing."""
    mode = str(configured or "gpu").lower()
    if mode == "cpu":
        return "cpu"
    if true_submission:
        return "gpu"
    return "gpu" if has_gpu() else "cpu"


SMOKE_MODE = _smoke_mode(SMOKE.get("mode"), TRUE_SUBMISSION, _has_gpu)
if SMOKE_MODE == "cpu" and str(SMOKE.get("mode", "gpu")).lower() != "cpu":
    print("WARNING: no GPU visible in an interactive commit; falling back to the cpu pipeline check")
CPU_SMOKE = SMOKE_MODE == "cpu"
print("smoke mode:", SMOKE_MODE)

# ---- choose the interpreter for the cp312 SGLang wheelhouse ----
def _python_ok(exe: str) -> bool:
    try:
        out = subprocess.run(
            [exe, "-c", "import sys, ssl, ctypes, zlib, sqlite3; print(sys.version_info[:2])"],
            capture_output=True, text=True, timeout=60,
        )
        return out.returncode == 0 and "(3, 12)" in out.stdout
    except Exception:
        return False


def resolve_server_python() -> str:
    if sys.version_info[:2] == (3, 12):
        return sys.executable
    system = [exe for exe in ("/usr/bin/python3.12", "/usr/local/bin/python3.12", "/opt/conda/bin/python3.12") if Path(exe).exists()]
    for exe in system:
        print(f"{exe}: full-stdlib check {'passed' if _python_ok(exe) else 'FAILED'}")
    if PY312_DATASET_DIR:
        extracted = sorted(Path(PY312_DATASET_DIR).rglob("bin/python3.12"))
        for exe in extracted:
            if _python_ok(str(exe)):
                return str(exe)
        tarballs = sorted(p for p in Path(PY312_DATASET_DIR).rglob("cpython-3.12*") if p.is_file() and (p.name.endswith(".tar.gz") or p.name.endswith(".tgz.bin")))
        if tarballs:
            dest = Path("/tmp/py312")
            exe = dest / "python" / "bin" / "python3.12"
            if not exe.exists():
                dest.mkdir(parents=True, exist_ok=True)
                with tarfile.open(tarballs[0]) as tar:
                    tar.extractall(dest)
            if _python_ok(str(exe)):
                return str(exe)
            print(f"standalone CPython at {exe} failed its import check")
    for exe in system:
        if _python_ok(exe):
            return exe
    for exe in system:
        print(f"falling back to {exe} without the full import check")
        return exe
    raise RuntimeError("No CPython 3.12 available: no standalone tarball attached and no system python3.12")


SERVER_PYTHON = resolve_server_python()
print("server python:", SERVER_PYTHON)

# ---- serving + harness configuration (environment variables read by the harness) ----
SERVED_MODEL_HOST = "127.0.0.1"
SERVED_MODEL_PORT = 8001
SERVER_BASE_URL = f"http://{SERVED_MODEL_HOST}:{SERVED_MODEL_PORT}/v1"
USE_PRIORITY_SCHEDULING = __USE_PRIORITY_SCHEDULING__

setup_env = __SETUP_ENV__
setup_env.update({
    "LOCAL_ANALYZER_BASE_URL": SERVER_BASE_URL,
    "OPENAI_BASE_URL": SERVER_BASE_URL,
    "LOCAL_ANALYZER_MODEL_ID": SERVED_MODEL_NAME,
    "INFERENCE_ANALYZER_MODEL": SERVED_MODEL_NAME,
})
if USE_PRIORITY_SCHEDULING:
    setup_env.update(__PRIORITY_ENV__)
os.environ.update({k: str(v) for k, v in setup_env.items()})
print("harness env keys:", len(setup_env))
