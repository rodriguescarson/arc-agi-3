"""Drain-time pinned memory and image window (ARC3_PIN_MEMORY_AT_DRAIN, ARC3_DRAIN_IMAGE_KEEP).

The property that matters most is cache safety: both edits happen only on the turn the
token trimmer drops history, and later turns must see a byte-identical prefix."""
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))

import inference.agent.tool_agent as ta  # noqa: E402

FN_A = "def find_player(grid):\n    return [(r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v == 'R']\n"
FN_B = "def path_to(a, b):\n    return [a, b]\n"


@dataclass
class F:
    level: int


@dataclass
class E:
    action: str
    frame: F
    result: dict = field(default_factory=dict)


GAME = [E("", F(1)), E("UP", F(1)), E("LEFT", F(2), {"level_completed": True}), E("DOWN", F(2))]


def img():
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}


def user(i, image=True):
    content = [{"type": "text", "text": f"turn {i}"}] + ([img()] if image else [])
    return {"role": "user", "content": content}


def assistant(i):
    return {"role": "assistant", "content": f"reply {i}"}


def conversation(n):
    msgs = [{"role": "system", "content": "sys"}]
    for i in range(n):
        msgs += [user(i), assistant(i)]
    return msgs


def stub(drop_first: int):
    """An object exposing just what _persistent_history_messages uses; the trimmer drops
    the oldest `drop_first` history messages when told to drain, else keeps everything."""
    s = types.SimpleNamespace(_kept_functions={"find_player": FN_A, "path_to": FN_B}, evictions=0, drain=True)

    def trim(messages, tools=None):
        if s.drain:
            return [messages[0], *messages[1 + drop_first:]]
        return list(messages)

    s._trim_messages_for_context = trim
    s._keep_recent_history_turns = lambda history, **_: list(history)
    s._drop_until_first_user_message = types.MethodType(ta.ToolAgent._drop_until_first_user_message, s)
    s._note_history_evicted = lambda: setattr(s, "evictions", s.evictions + 1)
    s._pinned_memory_block = types.MethodType(ta.ToolAgent._pinned_memory_block, s)
    s.run = types.MethodType(ta.ToolAgent._persistent_history_messages, s)
    return s


def _env(monkeypatch, **values):
    for key in ("ARC3_PIN_MEMORY_AT_DRAIN", "ARC3_DRAIN_IMAGE_KEEP", "ARC3_HISTORY_IMAGE_KEEP", "ARC3_PERSISTENT_FUNCTIONS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(ta, "load_runtime_state", lambda path: (None, GAME))


def test_note_lists_levels_and_newest_functions_first():
    text = ta._pinned_memory_text(
        [{"level": 1, "winning_actions": ["UP", "LEFT"], "n_actions": 2, "attempts": 1, "total_actions": 2}],
        [FN_A, FN_B], 4500)
    assert text.startswith(ta._PINNED_MEMORY_HEADER)
    assert "L1: 2 actions in 1 attempt(s) (2 spent): UP, LEFT" in text
    assert text.index("def path_to") < text.index("def find_player")


def test_note_caps_whole_functions_and_names_the_rest():
    text = ta._pinned_memory_text([], [FN_A, FN_B], len(FN_B) + 20)
    assert "def path_to" in text and "def find_player" not in text
    assert "Also retained, source not shown here: find_player(grid)." in text


def test_nothing_to_pin_means_no_note():
    assert ta._pinned_memory_text([], [], 4500) == ""


def test_off_by_default_changes_nothing(monkeypatch):
    _env(monkeypatch)
    s = stub(drop_first=4)
    msgs = conversation(5)
    out = s.run(msgs, state_path=Path("x"))
    assert out == msgs[1 + 4:]


def test_drain_pins_memory_and_strips_old_images(monkeypatch):
    _env(monkeypatch, ARC3_PIN_MEMORY_AT_DRAIN="1", ARC3_DRAIN_IMAGE_KEEP="1", ARC3_PERSISTENT_FUNCTIONS="1")
    s = stub(drop_first=4)
    out = s.run(conversation(5), state_path=Path("x"))
    first = out[0]["content"]
    assert first[0]["type"] == "text" and first[0]["text"].startswith(ta._PINNED_MEMORY_HEADER)
    assert "L1: 2 actions in 1 attempt(s) (2 spent): UP, LEFT" in first[0]["text"]
    assert "def find_player" in first[0]["text"]
    images = [i for i, m in enumerate(out) if ta._message_has_image(m)]
    assert images == [len(out) - 2]                       # only the newest image-bearing message keeps its image
    assert s.evictions == 1


def test_later_turns_reuse_the_pinned_prefix_unchanged(monkeypatch):
    _env(monkeypatch, ARC3_PIN_MEMORY_AT_DRAIN="1", ARC3_DRAIN_IMAGE_KEEP="1", ARC3_PERSISTENT_FUNCTIONS="1")
    s = stub(drop_first=4)
    stored = s.run(conversation(5), state_path=Path("x"))
    s.drain = False
    s._kept_functions["late_helper"] = "def late_helper():\n    return 1\n"   # new function after the drain
    nxt = s.run([{"role": "system", "content": "sys"}, *stored, user(99), assistant(99)], state_path=Path("x"))
    assert nxt[: len(stored)] == stored                    # byte-identical prefix: no re-pinning, no new stripping
    assert "late_helper" not in str(nxt[0]["content"])
    assert ta._message_has_image(nxt[-2])                  # the new turn's image is untouched
