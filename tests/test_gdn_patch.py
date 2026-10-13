"""The serve-cell source patch for Pennyroyal's Gated-DeltaNet loader must match the real wheel
(anchors captured by the arc3-sglang-source-probe-cpu kernel) and refuse to apply twice."""
import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle"))

import build_notebook  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "pennyroyal_qwen3_5_gdn_excerpt.txt"   # indented class-body excerpt


def _patch_fn():
    cfg = json.loads((ROOT / "kaggle" / "variants" / "v3-swift.json").read_text())
    src = dict(build_notebook.render_cells(cfg))["40_serve.py"]
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "patch_gdn_packed_in_proj")
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "40_serve.py", "exec"), {}, ns)
    return ns["patch_gdn_packed_in_proj"]


def test_patch_applies_to_the_pennyroyal_source():
    patched = _patch_fn()(FIXTURE.read_text())
    assert '"qweight", "qzeros", "scales", "g_idx"' in patched
    assert "sizes = [int(size // factor) for size in sizes]" in patched
    assert "return original_weight_loader(param, loaded_weight, None)" in patched
    compile("class _Excerpt:\n" + patched, "qwen3_5_excerpt.py", "exec")   # still valid Python


def test_patch_refuses_to_apply_twice():
    once = _patch_fn()(FIXTURE.read_text())
    with pytest.raises(AssertionError, match="anchor"):
        _patch_fn()(once)


def test_only_the_swift_variant_enables_the_patch():
    for path in sorted((ROOT / "kaggle" / "variants").glob("*.json")):
        cfg = json.loads(path.read_text())
        enabled = bool(cfg.get("serve_cfg", {}).get("PATCH_GDN_PACKED_IN_PROJ"))
        assert enabled == (cfg["variant"] in {"v3-swift", "v6-swift-level-memory"}), path.name
