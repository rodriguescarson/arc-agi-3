import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))


def _variant_env(name):
    return json.loads((ROOT / "kaggle" / "variants" / f"{name}.json").read_text())["setup_env"]


def test_stall_rule_leads_the_system_prompt(monkeypatch):
    env = _variant_env("v11-stall-rule")
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    from inference.agent import tool_agent

    prompt = tool_agent._build_system_prompt(tool_output_tokens=3072)
    assert prompt.startswith(env["ARC3_SYSTEM_PROMPT_PREFIX"])
    assert "You are" in prompt[len(env["ARC3_SYSTEM_PROMPT_PREFIX"]):]


def test_v10_prompt_unchanged_without_prefix(monkeypatch):
    for key, value in _variant_env("v10-harness-fixes").items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.delenv("ARC3_SYSTEM_PROMPT_PREFIX", raising=False)
    from inference.agent import tool_agent

    assert not tool_agent._build_system_prompt(tool_output_tokens=3072).startswith("Stall rule")


def test_medium_effort_is_a_valid_level(monkeypatch):
    env = _variant_env("v11-stall-medium")
    monkeypatch.setenv("ARC3_REASONING_EFFORT", env["ARC3_REASONING_EFFORT"])
    from inference.agent import tool_agent

    assert tool_agent._reasoning_effort_default() == "medium"
