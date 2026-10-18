#!/usr/bin/env python3
"""Render a Kaggle submission notebook from kaggle/cells/*.py and a variant JSON.

    python kaggle/build_notebook.py kaggle/variants/v1-franzen-faithful.json
    python kaggle/build_notebook.py kaggle/variants/v1-franzen-faithful.json --push

Output: kaggle/build/<variant>/submission.ipynb + kernel-metadata.json.

Every cell file is Python source.  Tokens of the form __NAME__ are replaced by the Python
literal of the variant's value (see TOKENS below), so a cell stays valid Python both as a
template and after rendering.  Cell order is the lexical order of the file names.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELLS_DIR = ROOT / "kaggle" / "cells"
COMPETITION = "arc-prize-2026-arc-agi-3"
OWNER = "carsonrodrigues"
ACCELERATOR_NOTEBOOK = "nvidiaRtxPro6000"   # notebook metadata value Franzen's notebook carries
ACCELERATOR_SHAPE = "NvidiaRtxPro6000"      # kernel-metadata machine_shape / --accelerator (TAAF)


def _git_rev() -> str:
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return rev + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def literal(value) -> str:
    """Python source for a JSON-derived value (json.dumps would emit true/false/null)."""
    import ast
    import pprint

    text = pprint.pformat(value, width=100, sort_dicts=False)
    assert ast.literal_eval(text) == value
    return text


def tokens(cfg: dict) -> dict[str, str]:
    return {
        "__VARIANT__": literal(cfg["variant"]),
        "__SERVER_STARTUP_TIMEOUT__": literal(int(cfg.get("server_startup_timeout_s", 720))),
        "__INPUTS__": literal(cfg["inputs"]),
        "__SERVED_MODEL_NAME__": literal(cfg["served_model_name"]),
        "__SMOKE__": literal(cfg["smoke"]),
        "__USE_PRIORITY_SCHEDULING__": literal(bool(cfg.get("use_priority_scheduling", True))),
        "__SETUP_ENV__": literal(cfg["setup_env"]),
        "__PRIORITY_ENV__": literal(cfg.get("priority_env", {})),
        "__SOLVER__": literal(cfg["solver"]),
        "__SERVE_CFG__": literal(cfg.get("serve_cfg", {})),
    }


def render_cells(cfg: dict) -> list[tuple[str, str]]:
    subs = tokens(cfg)
    out = []
    for path in sorted(CELLS_DIR.glob("*.py")):
        src = path.read_text()
        for key, value in subs.items():
            src = src.replace(key, value)
        leftover = [line for line in src.splitlines() if "__" in line and any(t in line for t in subs)]
        assert not leftover, f"unreplaced tokens in {path.name}: {leftover}"
        out.append((path.name, src))
    return out


def check_cells(cells: list[tuple[str, str]]) -> None:
    import ast
    flags = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    for name, src in cells:
        try:
            compile(src, name, "exec", flags=flags)
        except SyntaxError as exc:
            sys.exit(f"{name}: {exc}")


def accelerator(cfg: dict) -> tuple[str, str | None]:
    """(notebook metadata value, kernel machine_shape / --accelerator value)."""
    acc = str(cfg.get("accelerator", "NvidiaRtxPro6000"))
    if acc.lower() in {"none", "cpu", ""}:
        return "none", None
    return ACCELERATOR_NOTEBOOK, ACCELERATOR_SHAPE


def notebook(cfg: dict, cells: list[tuple[str, str]]) -> dict:
    header = (
        f"# ARC Prize 2026 / ARC-AGI-3 — {cfg['title']}\n\n"
        f"Variant `{cfg['variant']}`, built from `rodriguescarson/arc-agi-3` @ `{_git_rev()}`.\n\n"
        "Built on **Daniel Franzen's Milestone 2 solution** (Apache-2.0, "
        "https://github.com/da-fr/arc-agi-3-solution) which builds on **Tufa Labs' Duck harness** "
        "(MIT, https://github.com/Tufalabs/duck-harness). Model: "
        f"{cfg.get('model_label', 'Qwen3.8-Flash-Next (Intel AutoRound W4A16)')} "
        "with Albucino's MTP draft, served by SGLang Pennyroyal 2.5.3 from Franzen's public wheelhouse. "
        "Third-party code and weights remain under their own licences.\n\n"
        f"Notes: {cfg.get('notes', '')}\n\n"
        "Interactive commits run a short smoke configuration on two public games; the competition rerun "
        "(`KAGGLE_IS_COMPETITION_RERUN`) plays the full hidden set for the 9-hour budget."
    )
    nb_cells = [{"cell_type": "markdown", "metadata": {}, "source": header}]
    for name, src in cells:
        nb_cells.append({"cell_type": "markdown", "metadata": {}, "source": f"## {name[:-3]}"})
        nb_cells.append({"cell_type": "code", "metadata": {"trusted": True}, "outputs": [], "execution_count": None, "source": src})
    return {
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "mimetype": "text/x-python", "file_extension": ".py", "pygments_lexer": "ipython3"},
            "kaggle": {
                "accelerator": accelerator(cfg)[0],
                "isInternetEnabled": False,
                "isGpuEnabled": accelerator(cfg)[1] is not None,
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 4,
        "cells": nb_cells,
    }


def model_sources(inputs: dict) -> list[str]:
    """Every Kaggle model instance the notebook must mount: the target (one ref or several
    `model_parts`), the MTP draft, and the optional fallback target."""
    refs = [inputs.get("model")] + list(inputs.get("model_parts") or []) + [inputs["draft"], inputs.get("fallback_model")]
    out: list[str] = []
    for ref in refs:
        if ref and ref not in out:
            out.append(ref)
    assert inputs.get("model") or inputs.get("model_parts"), "variant needs inputs.model or inputs.model_parts"
    return out


def kernel_slug_for(title: str) -> str:
    """Kaggle derives a kernel's slug from its title on the first push (lowercase, runs of
    non-alphanumerics -> '-'), whatever `id` says; a later push with a mismatching id gets
    HTTP 409. So the declared slug must equal the slugified title (2026-10-18)."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def kernel_metadata(cfg: dict) -> dict:
    inputs = cfg["inputs"]
    _, shape = accelerator(cfg)
    expected = kernel_slug_for(cfg["title"])
    if cfg["kernel_slug"] != expected:
        raise ValueError(f"{cfg['variant']}: kernel_slug {cfg['kernel_slug']!r} must equal the slugified title {expected!r}")
    meta = {
        "id": f"{OWNER}/{cfg['kernel_slug']}",
        "title": cfg["title"],
        "code_file": "submission.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": shape is not None,
        "enable_tpu": False,
        "enable_internet": False,
        "docker_image_pinning_type": "original",
        "keywords": ["gpu"] if shape else [],
        "dataset_sources": [ref for ref in (inputs["wheelhouse"], inputs["bundle"], inputs.get("py312")) if ref],
        "kernel_sources": [],
        "competition_sources": [COMPETITION],
        "model_sources": model_sources(inputs),
    }
    if shape:
        meta["machine_shape"] = shape
    return meta


def build(variant_path: Path) -> tuple[Path, dict]:
    """Render a variant into kaggle/build/<variant>/; returns (out_dir, cfg)."""
    cfg = json.loads(variant_path.read_text())
    cells = render_cells(cfg)
    check_cells(cells)
    out = ROOT / "kaggle" / "build" / cfg["variant"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "submission.ipynb").write_text(json.dumps(notebook(cfg, cells), indent=1))
    (out / "kernel-metadata.json").write_text(json.dumps(kernel_metadata(cfg), indent=2) + "\n")
    (out / "variant.json").write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"built {out}  ({len(cells)} code cells, git {_git_rev()})")
    return out, cfg


def kaggle_bin() -> str:
    import shutil
    venv = ROOT / ".venv" / "bin" / "kaggle"
    return str(venv) if venv.exists() else (shutil.which("kaggle") or "kaggle")


def push(out: Path, cfg: dict) -> int:
    """`kaggle kernels push` for a built variant (a Save & Run All commit); returns the new version number."""
    import re
    cmd = [kaggle_bin(), "kernels", "push", "-p", str(out)]
    if accelerator(cfg)[1]:
        cmd += ["--accelerator", accelerator(cfg)[1]]
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    print(text.strip())
    match = re.search(r"Kernel version (\d+) successfully pushed", text)
    if proc.returncode != 0 or not match:
        raise RuntimeError(f"kernel push failed: {text.strip()[-400:]}")
    return int(match.group(1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", type=Path)
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()
    out, cfg = build(args.variant)
    if args.push:
        print("version", push(out, cfg))


if __name__ == "__main__":
    main()
