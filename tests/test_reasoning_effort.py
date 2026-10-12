import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))

import inference.agent.tool_agent as ta  # noqa: E402


def _kwargs(monkeypatch, env: dict[str, str], rung: int = -1) -> dict:
    for key in ("ARC3_REASONING_EFFORT", "ARC3_REASONING_EFFORT_LADDER", "ARC3_PRESERVE_THINKING"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return ta.ToolAgent._harness_template_kwargs(types.SimpleNamespace(_reasoning_effort_rung=rung))


def test_default_leaves_template_effort_alone(monkeypatch):
    assert _kwargs(monkeypatch, {}) == {"preserve_thinking": True}


def test_global_effort_is_sent_every_turn(monkeypatch):
    assert _kwargs(monkeypatch, {"ARC3_REASONING_EFFORT": "medium"})["reasoning_effort"] == "medium"
    assert _kwargs(monkeypatch, {"ARC3_REASONING_EFFORT": " LOW "})["reasoning_effort"] == "low"


def test_unknown_effort_is_dropped_not_sent(monkeypatch):
    # the Qwen3.8 template raises on anything but xhigh/medium/low; never forward a typo
    assert "reasoning_effort" not in _kwargs(monkeypatch, {"ARC3_REASONING_EFFORT": "high"})


def test_ladder_overrides_global_after_truncation(monkeypatch):
    env = {"ARC3_REASONING_EFFORT": "medium", "ARC3_REASONING_EFFORT_LADDER": "medium,low"}
    assert _kwargs(monkeypatch, env, rung=-1)["reasoning_effort"] == "medium"
    assert _kwargs(monkeypatch, env, rung=1)["reasoning_effort"] == "low"
