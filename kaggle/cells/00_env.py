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
os.environ["ARC3_HTTP_RETRY_INITIAL_SECONDS"] = "900"

# ---- attached inputs (all public Kaggle datasets / models) ----
INPUTS = __INPUTS__
# e.g. {"wheelhouse": "dfranzen/pennyroyal-v253", "bundle": "carsonrodrigues/arc3-harness-bundle",
#       "py312": "carsonrodrigues/python312-standalone",
#       "model": "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/transformers/default/1",
#       "draft": "dfranzen/albucino-qwen3-8-flash-next-drafter/transformers/default/1"}


def _resolve_input(ref: str, *, model: bool = False, required: bool = True) -> str:
    """Kaggle mounts datasets at /kaggle/input/datasets/<owner>/<slug> (new layout) or
    /kaggle/input/<slug> (old layout); models at /kaggle/input/models/<owner>/<slug>/<fw>/<v>/<n>."""
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


WHEELHOUSE_DIR = _resolve_input(INPUTS["wheelhouse"])
MODEL_DIR = _resolve_input(INPUTS["model"], model=True)
DRAFT_MODEL_DIR = _resolve_input(INPUTS["draft"], model=True)
BUNDLE_SOURCE_DIR = _resolve_input(INPUTS["bundle"])
PY312_DATASET_DIR = _resolve_input(INPUTS["py312"], required=False)
SERVED_MODEL_NAME = __SERVED_MODEL_NAME__
print({"wheelhouse": WHEELHOUSE_DIR, "model": MODEL_DIR, "draft": DRAFT_MODEL_DIR, "bundle": BUNDLE_SOURCE_DIR, "py312": PY312_DATASET_DIR})

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


SMOKE_MODE = "gpu" if TRUE_SUBMISSION else str(SMOKE.get("mode", "gpu")).lower()
if SMOKE_MODE == "gpu" and not TRUE_SUBMISSION and not _has_gpu():
    print("WARNING: no GPU visible in an interactive commit; falling back to the cpu pipeline check")
    SMOKE_MODE = "cpu"
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
    for exe in ("/usr/bin/python3.12", "/usr/local/bin/python3.12"):
        if Path(exe).exists():
            print(f"falling back to {exe} without the full import check")
            return exe
    for exe in system:
        if _python_ok(exe):
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
