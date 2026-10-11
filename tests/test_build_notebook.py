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


def test_rendered_env_cell_contains_franzen_settings():
    cfg = json.loads((ROOT / "kaggle" / "variants" / "v1-franzen-faithful.json").read_text())
    env_cell = dict(build_notebook.render_cells(cfg))["00_env.py"]
    for key in ("LOCAL_ANALYZER_CONTEXT_WINDOW", "ARC3_ANIMATION", "EXPOSE_UNDO", "ARC3_MAX_ACTIVE_STREAMS"):
        assert key in env_cell
