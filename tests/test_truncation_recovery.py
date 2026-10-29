"""ARC3_TRUNCATION_RECOVERY: tell the model when a reply was cut off before any tool call, and cap
the replies that follow on the same level.

Default off must be byte-identical to the harness as it was: no max_tokens override, no extra text."""
import sys
import types
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))

import inference.agent.tool_agent as ta  # noqa: E402
from inference.agent.runtime_state import Frame, write_runtime_state  # noqa: E402

CEILING = 12288
CUT_MARKER = "CUT OFF at the output limit"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in ("ARC3_TRUNCATION_RECOVERY", "ARC3_TRUNCATION_RECOVERY_CAP", "ARC3_STUB_DEAD_REASONING"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ARC3_REASONING_HISTORY_KEY", "reasoning_content")  # as the daily variants set it


def _agent(**attrs):
    base = dict(
        _max_output_tokens=CEILING,
        _length_cut_level=None,
        _length_cut_pending=False,
        _length_cut_kept=False,
    )
    base.update(attrs)
    return types.SimpleNamespace(**base)


def _cap(agent, level):
    return ta.ToolAgent._truncation_capped_max_tokens(agent, level)


def _notice(agent, resuming=True):
    return ta.ToolAgent._take_length_cut_notice(agent, resuming)


# ---- the switch and the cap are read from the environment ----------------------------------


def test_off_by_default(monkeypatch):
    assert ta._truncation_recovery() is False
    agent = _agent(_length_cut_level=3, _length_cut_pending=True, _length_cut_kept=True)
    assert _cap(agent, 3) is None
    assert _notice(agent) == ""


def test_switch_and_cap_are_read(monkeypatch):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    assert ta._truncation_recovery() is True
    assert ta._truncation_recovery_cap() == 6144
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", "4096")
    assert ta._truncation_recovery_cap() == 4096
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", "-5")
    assert ta._truncation_recovery_cap() == 0
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", "garbage")
    assert ta._truncation_recovery_cap() == 6144


def test_cap_applies_only_on_the_level_that_was_cut(monkeypatch):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    agent = _agent(_length_cut_level=3)
    assert _cap(agent, 3) == 6144
    assert _cap(agent, 4) is None  # a new level starts with the full ceiling
    assert _cap(agent, None) is None
    assert _cap(_agent(), 3) is None  # nothing has been cut off yet


def test_cap_never_raises_the_ceiling_and_zero_disables_it(monkeypatch):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    agent = _agent(_length_cut_level=2)
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", str(CEILING))
    assert _cap(agent, 2) is None
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", "999999")
    assert _cap(agent, 2) is None
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", "0")
    assert _cap(agent, 2) is None
    # no configured ceiling (server default): the cap is still a ceiling
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY_CAP", "5000")
    assert _cap(_agent(_length_cut_level=2, _max_output_tokens=None), 2) == 5000


def test_notice_is_consumed_once_and_only_on_a_resumption(monkeypatch):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    agent = _agent(_length_cut_pending=True, _length_cut_kept=True)
    text = _notice(agent)
    assert CUT_MARKER in text and "still in context" in text and text.endswith("\n\n")
    assert _notice(agent) == ""

    # a failed request rolls the history back, so the invocation is not a resumption: the cut
    # it saw is gone and must not be announced, now or later
    agent = _agent(_length_cut_pending=True, _length_cut_kept=True)
    assert _notice(agent, resuming=False) == ""
    assert _notice(agent) == ""


def test_notice_does_not_claim_the_reasoning_survived_when_it_did_not(monkeypatch):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    text = _notice(_agent(_length_cut_pending=True, _length_cut_kept=False))
    assert CUT_MARKER in text and "still in context" not in text and "short" in text


# ---- end to end through ToolAgent.analyze() ------------------------------------------------


class _Recorder:
    """Stands in for the model endpoint: scripted replies, every request recorded."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages, *, tools=None, request_timeout_seconds=None, max_tokens=None, enable_thinking=None):
        self.calls.append(
            {"max_tokens": max_tokens, "last_user": _text(messages[-1]), "roles": [m["role"] for m in messages]}
        )
        if not self.replies:
            raise RuntimeError("script exhausted")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _text(message):
    content = message.get("content")
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "")


def _reasoning(words=700):
    # varied on purpose: a repeated phrase is treated as a repetition loop and dropped from history
    return " ".join(f"hypothesis{i} puts a {i % 7}-cell block at row {i % 61} col {(i * 7) % 59}" for i in range(words))


def _cut_reply(reasoning=None):
    reasoning = reasoning or _reasoning()
    return ta._ChatCompletionResult(
        message={"role": "assistant", "content": "", "reasoning_content": reasoning},
        finish_reason="length",
        usage={"prompt_tokens": 9000, "completion_tokens": CEILING, "total_tokens": 9000 + CEILING},
    )


def _done_reply():
    return ta._ChatCompletionResult(
        message={"role": "assistant", "content": "ok", "reasoning_content": "short"},
        finish_reason="stop",
        usage={"prompt_tokens": 9000, "completion_tokens": 40, "total_tokens": 9040},
    )


def _make_agent(monkeypatch, tmp_path, recorder, *, yield_tokens, level=3):
    monkeypatch.setattr(ta, "_LOCAL_ANALYZER_YIELD_TOKENS", yield_tokens)
    monkeypatch.setattr(ta, "_LOCAL_ANALYZER_MAX_OUTPUT", CEILING)
    monkeypatch.setattr(ta, "_LOCAL_ANALYZER_CONTEXT_WINDOW", 131072)  # the default 32k evicts a 12k-token reply
    monkeypatch.setattr(ta, "_LOCAL_ANALYZER_TOOL_STEPS", 0)
    agent = ta.ToolAgent(model="flashnext", base_url="http://127.0.0.1:9/v1", provider="vllm")
    monkeypatch.setattr(ta.ToolAgent, "_chat_completion", lambda _self, messages, **kwargs: recorder(messages, **kwargs))
    state_path = tmp_path / "tool_runtime_state.json"
    grid = tuple(tuple(0 for _ in range(8)) for _ in range(8))
    write_runtime_state(state_path, current_frame=Frame(grid=grid, step=7, level=level), history=[])
    return agent, state_path


def _analyze(agent, state_path, step):
    return agent.analyze(state_path, step, valid_actions=["UP", "DOWN"], analysis_step=step)


def test_off_a_cut_reply_changes_nothing(monkeypatch, tmp_path):
    recorder = _Recorder([_cut_reply(), _done_reply()])
    agent, state_path = _make_agent(monkeypatch, tmp_path, recorder, yield_tokens=2048)
    first = _analyze(agent, state_path, 7)
    assert first is not None and first.yielded_control and not first.step_executed
    _analyze(agent, state_path, 7)
    assert len(recorder.calls) >= 2
    assert all(c["max_tokens"] is None for c in recorder.calls)
    assert all(CUT_MARKER not in c["last_user"] for c in recorder.calls)


def test_on_next_opener_says_the_reply_was_cut_and_the_level_is_capped(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    recorder = _Recorder([_cut_reply(), _done_reply(), _done_reply()])
    agent, state_path = _make_agent(monkeypatch, tmp_path, recorder, yield_tokens=2048)
    first = _analyze(agent, state_path, 7)
    assert first is not None and first.yielded_control
    assert recorder.calls[0]["max_tokens"] is None  # the cut itself ran at the full ceiling

    _analyze(agent, state_path, 7)
    assert recorder.calls[1]["max_tokens"] == 6144
    opener = recorder.calls[1]["last_user"]
    assert opener.startswith("Your previous reply was CUT OFF at the output limit")
    assert "still in context" in opener  # the reasoning stayed in the history it was sent
    # the cut reply is in the history the resumption sends, so the claim is true
    assert "assistant" in recorder.calls[1]["roles"]

    # a complete reply clears it: the next resumption is not told it was cut off again
    _analyze(agent, state_path, 7)
    assert CUT_MARKER not in recorder.calls[2]["last_user"]
    assert recorder.calls[2]["max_tokens"] == 6144  # the cap lasts the level, the notice does not


def test_on_cap_ends_with_the_level(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    recorder = _Recorder([_cut_reply(), _done_reply(), _done_reply()])
    agent, state_path = _make_agent(monkeypatch, tmp_path, recorder, yield_tokens=2048, level=3)
    _analyze(agent, state_path, 7)
    grid = tuple(tuple(0 for _ in range(8)) for _ in range(8))
    write_runtime_state(state_path, current_frame=Frame(grid=grid, step=30, level=4), history=[])
    _analyze(agent, state_path, 30)
    assert recorder.calls[1]["max_tokens"] is None


def test_on_stubbed_reasoning_is_not_claimed_as_kept(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    monkeypatch.setenv("ARC3_STUB_DEAD_REASONING", "1")
    recorder = _Recorder([_cut_reply(), _done_reply()])
    agent, state_path = _make_agent(monkeypatch, tmp_path, recorder, yield_tokens=2048)
    _analyze(agent, state_path, 7)
    _analyze(agent, state_path, 7)
    opener = recorder.calls[1]["last_user"]
    assert opener.startswith("Your previous reply was CUT OFF")
    assert "still in context" not in opener


def test_in_turn_nudge_stops_telling_a_cut_model_to_investigate_first(monkeypatch, tmp_path):
    # no token yield configured, so the same invocation nudges instead of resuming
    for enabled in (False, True):
        if enabled:
            monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
        recorder = _Recorder([_cut_reply(), _done_reply()])
        agent, state_path = _make_agent(monkeypatch, tmp_path, recorder, yield_tokens=0)
        _analyze(agent, state_path, 7)
        nudge = recorder.calls[1]["last_user"]
        if enabled:
            assert nudge.startswith("Your previous reply was CUT OFF") and "Investigate first" not in nudge
            assert recorder.calls[1]["max_tokens"] == 6144
        else:
            assert nudge.startswith("You have not acted yet. Investigate first.")
            assert recorder.calls[1]["max_tokens"] is None


def test_a_cut_followed_by_a_timeout_is_not_announced_on_the_resumption(monkeypatch, tmp_path):
    # the cut happened earlier in the invocation; what ended it was the timeout, and the resumed
    # opener must not describe the wrong event
    monkeypatch.setenv("ARC3_TRUNCATION_RECOVERY", "1")
    recorder = _Recorder([_cut_reply(), requests.exceptions.ReadTimeout("slow"), _done_reply()])
    agent, state_path = _make_agent(monkeypatch, tmp_path, recorder, yield_tokens=0)
    first = _analyze(agent, state_path, 7)
    assert first is not None and first.yielded_control
    _analyze(agent, state_path, 7)
    assert CUT_MARKER not in recorder.calls[2]["last_user"]
