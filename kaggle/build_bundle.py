#!/usr/bin/env python3
"""Build the Kaggle source-bundle dataset from ./harness.

The competition notebook imports the harness from a Kaggle dataset (internet is off in
the rerun).  Tufa Labs and Daniel Franzen ship a *source bundle* dataset with this layout:

    src/ARC3-Inference/            the Duck harness (Franzen's fork, Apache-2.0)
    src/tufa-arc-agi-framework/    TAAF (Tufa Labs, MIT)
    benchmark_initial.pkl          pickled TAAF Benchmark (25 public games + HarnessSolver)
    deploy_target.pkl              pickled Kaggle deploy target (carries max_runtime_s)
    README.dataset.md
    LICENSE.franzen-apache-2.0, LICENSE-MIT-0.txt, NOTICE   licence texts and third-party notice

Franzen's notebook attaches Tufa's unchanged bundle and `git apply`s a 500 KB patch at boot.
We instead publish our own bundle built from `harness/` so the notebook needs no patch step
and the deployed tree is exactly what is committed in this repo.  The two pickles are copied
verbatim from Tufa's bundle (data/bundles/taaf-kaggle-source-bundle-copy); our harness keeps
the pickled classes' names and fields so they unpickle unchanged.

Usage:
    python kaggle/build_bundle.py            # writes kaggle/build/bundle/
    python kaggle/build_bundle.py --push     # also creates/updates the Kaggle dataset
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"
PICKLE_SOURCE = ROOT / "data" / "bundles" / "taaf-kaggle-source-bundle-copy"
OUT = ROOT / "kaggle" / "build" / "bundle"
DATASET_ID = "carsonrodrigues/arc3-harness-bundle"
DATASET_TITLE = "ARC-AGI-3 LLM Agent Harness (ARC Prize 2026)"
DATASET_SUBTITLE = "Carson Rodrigues' ARC-AGI-3 LLM agent harness for ARC Prize 2026 notebooks"
DATASET_DESCRIPTION = ROOT / "kaggle" / "datasets" / "arc3-harness-bundle.md"
# Kaggle refuses a version with more than five tags ("exceeded the max category limit").
DATASET_KEYWORDS = ["artificial intelligence", "games", "computer science", "python", "benchmark"]
LICENCE_FILES = {
    "LICENSE.franzen-apache-2.0": HARNESS / "LICENSE.franzen-apache-2.0",
    "LICENSE-MIT-0.txt": ROOT / "LICENSE",
    "NOTICE": ROOT / "NOTICE",
}
RESOURCES = [
    {"path": "README.dataset.md", "description": "Contents, licences and the git revision this bundle was built from"},
    {"path": "benchmark_initial.pkl", "description": "Tufa Labs' pickled TAAF benchmark, copied verbatim from dfranzen/taaf-kaggle-source-bundle-copy"},
    {"path": "deploy_target.pkl", "description": "Tufa Labs' pickled Kaggle deploy target, copied verbatim from dfranzen/taaf-kaggle-source-bundle-copy"},
    {"path": "git_status.txt", "description": "Git revision of rodriguescarson/arc-agi-3 the bundle was built from"},
    {"path": "preamble.txt", "description": "One-line build note"},
    {"path": "LICENSE.franzen-apache-2.0", "description": "Apache-2.0 licence of Daniel Franzen's ARC3-Inference fork"},
    {"path": "LICENSE-MIT-0.txt", "description": "MIT-0 licence of the code written for this entry"},
    {"path": "NOTICE", "description": "Third-party notice: which parts are Apache-2.0, MIT and MIT-0"},
]

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".git", "viewer", "tests"}
SKIP_SUFFIXES = {".pyc", ".lock"}


def _copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        n += 1
    return n


def _tree_sha(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(root)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _git_rev() -> str:
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "harness"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return rev + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def build() -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    n = 0
    for repo in ("ARC3-Inference", "tufa-arc-agi-framework"):
        n += _copy_tree(HARNESS / repo, OUT / "src" / repo)
    for name in ("benchmark_initial.pkl", "deploy_target.pkl"):
        src = PICKLE_SOURCE / name
        if not src.is_file():
            sys.exit(f"missing {src}: download dfranzen/taaf-kaggle-source-bundle-copy into data/bundles first")
        shutil.copy2(src, OUT / name)
    for name, src in LICENCE_FILES.items():
        shutil.copy2(src, OUT / name)
    (OUT / "git_status.txt").write_text(f"arc-agi-3 harness bundle built from {_git_rev()}\n")
    (OUT / "preamble.txt").write_text("arc-agi-3 harness bundle (carsonrodrigues). See README.dataset.md.\n")
    (OUT / "README.dataset.md").write_text(
        "# arc3-harness-bundle\n\n"
        "Source bundle for the ARC Prize 2026 ARC-AGI-3 notebook of carsonrodrigues.\n\n"
        "- `src/ARC3-Inference`: Daniel Franzen's fork of Tufa Labs' Duck harness (Apache-2.0),\n"
        "  with this repository's changes on top.\n"
        "- `src/tufa-arc-agi-framework`: TAAF, Tufa Labs (MIT).\n"
        "- `benchmark_initial.pkl`, `deploy_target.pkl`: copied verbatim from\n"
        "  `dfranzen/taaf-kaggle-source-bundle-copy` (Tufa Labs' original bundle).\n"
        "- `LICENSE.franzen-apache-2.0`, `LICENSE-MIT-0.txt`, `NOTICE`: the licence texts. Franzen's fork,\n"
        "  including the edits inside its files, is Apache-2.0; the new modules written for this entry are\n"
        "  MIT-0; TAAF is MIT as stated by Tufa Labs (see NOTICE).\n\n"
        f"Built from git revision {_git_rev()}; tree sha256 {_tree_sha(OUT / 'src')[:16]}.\n"
    )
    # `kaggle datasets version` sends subtitle, description, keywords and resources from this file
    # and blanks any that are missing, so all of them are written on every build.
    (OUT / "dataset-metadata.json").write_text(json.dumps({
        "title": DATASET_TITLE,
        "subtitle": DATASET_SUBTITLE,
        "description": DATASET_DESCRIPTION.read_text(),
        "id": DATASET_ID,
        "licenses": [{"name": "apache-2.0"}],
        "keywords": DATASET_KEYWORDS,
        "resources": RESOURCES,
    }, indent=2) + "\n")
    print(f"bundle: {n} source files -> {OUT}  (src sha {_tree_sha(OUT / 'src')[:16]}, git {_git_rev()})")
    return OUT


def push(out: Path) -> None:
    kaggle = ROOT / ".venv" / "bin" / "kaggle"
    exists = subprocess.run([str(kaggle), "datasets", "status", DATASET_ID], capture_output=True, text=True)
    if exists.returncode == 0 and "not found" not in (exists.stdout + exists.stderr).lower():
        cmd = [str(kaggle), "datasets", "version", "-p", str(out), "-m", f"harness {_git_rev()}", "--dir-mode", "zip"]
    else:
        cmd = [str(kaggle), "datasets", "create", "-p", str(out), "--dir-mode", "zip"]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="create or version the Kaggle dataset")
    args = ap.parse_args()
    out = build()
    if args.push:
        push(out)
