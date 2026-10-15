import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle"))

import build_notebook  # noqa: E402


def _variants():
    return sorted((ROOT / "kaggle" / "variants").glob("*.json"))


def test_every_variant_renders_and_compiles():
    assert _variants()
    for path in _variants():
        cfg = json.loads(path.read_text())
        cells = build_notebook.render_cells(cfg)
        build_notebook.check_cells(cells)
        names = [n for n, _ in cells]
        assert names == sorted(names)
        assert names[0].startswith("00_") and names[-1].startswith("90_")


def test_kernel_metadata_matches_inputs():
    cfg = json.loads(_variants()[0].read_text())
    meta = build_notebook.kernel_metadata(cfg)
    assert meta["enable_internet"] is False
    assert meta["enable_gpu"] is (cfg.get("accelerator", "NvidiaRtxPro6000") != "none")
    assert meta["docker_image_pinning_type"] == "original"
    assert meta["competition_sources"] == ["arc-prize-2026-arc-agi-3"]
    assert cfg["inputs"]["model"] in meta["model_sources"]
    assert cfg["inputs"]["bundle"] in meta["dataset_sources"]


def test_model_sources_cover_parts_and_fallback():
    inputs = {
        "model_parts": ["o/m/PyTorch/a/1", "o/m/PyTorch/b/1"],
        "fallback_model": "d/f/Transformers/default/1",
        "draft": "d/d/Transformers/default/1",
    }
    assert build_notebook.model_sources(inputs) == [
        "o/m/PyTorch/a/1", "o/m/PyTorch/b/1", "d/d/Transformers/default/1", "d/f/Transformers/default/1",
    ]
    single = {"model": "d/f/Transformers/default/1", "draft": "d/d/Transformers/default/1"}
    assert build_notebook.model_sources(single) == ["d/f/Transformers/default/1", "d/d/Transformers/default/1"]


def test_every_variant_lists_all_model_inputs():
    for path in _variants():
        cfg = json.loads(path.read_text())
        meta = build_notebook.kernel_metadata(cfg)
        for ref in list(cfg["inputs"].get("model_parts") or []) + [cfg["inputs"].get("fallback_model")]:
            if ref:
                assert ref in meta["model_sources"], f"{path.name}: {ref} missing from model_sources"


def test_rendered_env_cell_contains_franzen_settings():
    cfg = json.loads((ROOT / "kaggle" / "variants" / "v1-franzen-faithful.json").read_text())
    env_cell = dict(build_notebook.render_cells(cfg))["00_env.py"]
    for key in ("LOCAL_ANALYZER_CONTEXT_WINDOW", "ARC3_ANIMATION", "EXPOSE_UNDO", "ARC3_MAX_ACTIVE_STREAMS"):
        assert key in env_cell


def test_rendered_literals_are_python_not_json():
    for path in _variants():
        cfg = json.loads(path.read_text())
        for name, src in build_notebook.render_cells(cfg):
            for bad in (": true", ": false", ": null", " true,", " false,"):
                assert bad not in src, f"{path.name}/{name} contains JSON literal {bad!r}"


def _smoke_mode_fn():
    import ast

    cfg = json.loads((ROOT / "kaggle" / "variants" / "v3-cpucheck.json").read_text())
    source = dict(build_notebook.render_cells(cfg))["00_env.py"]
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "_smoke_mode")
    scope: dict = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "00_env", "exec"), scope)
    return scope["_smoke_mode"]


def test_smoke_mode_keeps_gpu_variants_on_the_gpu_in_the_rerun():
    mode = _smoke_mode_fn()
    gpu, no_gpu = (lambda: True), (lambda: False)
    # a GPU variant's scored rerun serves the model whatever nvidia-smi says
    assert mode("gpu", True, no_gpu) == "gpu"
    assert mode(None, True, no_gpu) == "gpu"
    # interactive commits fall back to the CPU check only when no GPU is visible
    assert mode("gpu", False, gpu) == "gpu"
    assert mode("gpu", False, no_gpu) == "cpu"
    # a CPU-check variant stays on the CPU path, also in the rerun (a valid ~0 instead of a crash)
    assert mode("cpu", True, gpu) == "cpu"
    assert mode("cpu", False, no_gpu) == "cpu"


def test_every_gpu_variant_renders_gpu_smoke_mode():
    for path in _variants():
        cfg = json.loads(path.read_text())
        if cfg.get("accelerator", "NvidiaRtxPro6000") != "none":
            assert str(cfg.get("smoke", {}).get("mode", "gpu")).lower() == "gpu", path.name


def test_smoke_scores_come_from_the_played_runs():
    import ast
    from types import SimpleNamespace

    cfg = json.loads((ROOT / "kaggle" / "variants" / "v6-swift-level-memory.json").read_text())
    source = dict(build_notebook.render_cells(cfg))["80_run.py"]
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "_run_scores")
    scope: dict = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "80_run", "exec"), scope)
    runs = [SimpleNamespace(game_id="ls20-1", state="won", levels_completed=7, final_score=1.0, actions_per_level=[3, 4]),
            SimpleNamespace(game_id="vc33-2", state="playing", levels_completed=1, final_score=None, actions_per_level=[9])]
    rows = scope["_run_scores"](runs, lambda r: r.final_score if r.final_score is not None else 0.25,
                                lambda r: sum(r.actions_per_level))
    assert rows == [
        {"game_id": "ls20-1", "score": 1.0, "state": "won", "levels": 7, "actions": 7},
        {"game_id": "vc33-2", "score": 0.25, "state": "playing", "levels": 1, "actions": 9},
    ]
