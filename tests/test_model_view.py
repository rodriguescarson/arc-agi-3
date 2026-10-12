"""The merged model view (cell 00) must re-assemble a checkpoint split over several Kaggle model
instances into one directory of symlinks, and refuse duplicates."""
import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle"))

import build_notebook  # noqa: E402


def _merged_model_view():
    cfg = json.loads((ROOT / "kaggle" / "variants" / "v3-swift.json").read_text())
    src = dict(build_notebook.render_cells(cfg))["00_env.py"]
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_merged_model_view")
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "00_env.py", "exec"), {"Path": Path, "shutil": __import__("shutil"), "_resolve_input": lambda ref, model=False: ref}, ns)
    return ns["_merged_model_view"]


def _part(root: Path, name: str, files: dict[str, str]) -> Path:
    d = root / name
    for rel, text in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return d


def test_view_links_every_file_from_every_part(tmp_path):
    a = _part(tmp_path, "a", {"config.json": "{}", "model.safetensors.index.json": "{}", "tokenizer.json": "{}", "model-00001-of-00002.safetensors": "x"})
    b = _part(tmp_path, "b", {"model-00002-of-00002.safetensors": "y", "chat_template.jinja": "t"})
    view = tmp_path / "view"
    out = _merged_model_view()([str(a), str(b)], view)
    assert out == str(view)
    names = sorted(p.name for p in view.iterdir())
    assert names == ["chat_template.jinja", "config.json", "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors", "model.safetensors.index.json", "tokenizer.json"]
    assert all(p.is_symlink() for p in view.iterdir())
    assert (view / "model-00002-of-00002.safetensors").read_text() == "y"


def test_view_rejects_duplicate_files(tmp_path):
    a = _part(tmp_path, "a", {"config.json": "{}", "model.safetensors.index.json": "{}", "tokenizer.json": "{}"})
    b = _part(tmp_path, "b", {"config.json": "{}"})
    with pytest.raises(RuntimeError, match="duplicate"):
        _merged_model_view()([str(a), str(b)], tmp_path / "view")


def test_view_requires_the_loader_files(tmp_path):
    a = _part(tmp_path, "a", {"model-00001-of-00001.safetensors": "x"})
    with pytest.raises(AssertionError, match="config.json"):
        _merged_model_view()([str(a)], tmp_path / "view")
