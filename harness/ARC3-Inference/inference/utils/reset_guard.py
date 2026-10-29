"""Whether a RESET would restart anything (pure; ARC3_RESET_GUARD).

arcengine decides what RESET means from its own per-level action counter
(``ARCBaseGame.handle_reset``): with at least one non-RESET action since the level was set it
restarts the CURRENT level, with none it performs a FULL game reset back to level 1. The counter
is zero at game start, right after a level-up and right after any RESET, so a RESET issued
straight after a level-up or straight after another RESET wipes the run (offline engine, ls20: one
RESET after the 22-move level-1 solution takes levels_completed from 1 to 0). The competition
gateway swallows that RESET instead, but it still bills it as an action.

The harness cannot read the engine's counter, so it mirrors it from what it executes: every
executed action goes through ``note_action``, and ``refusal`` says whether a RESET issued now
would have nothing to restart. Automatic resets (after a death, the warmup keepalive) are noted
like any other action and never checked.
"""

REFUSAL = (
    "RESET was NOT executed and no action was spent: no other action has been taken on this "
    "level since it began or since the last RESET, so the level is already at its starting "
    "state and a RESET would restart nothing (on this engine it can also restart the whole game "
    "from level 1). Take a real action first. RESET is for abandoning progress you have made on "
    "this level."
)


class ResetGuard:
    """Mirror of the engine's count of non-RESET actions on the current level."""

    def __init__(self) -> None:
        self.level_actions = 0

    def note_action(self, *, is_reset: bool, level_changed: bool) -> None:
        """Record one executed action.

        A RESET and a level change both leave the engine's counter at zero; every other action,
        including a no-op and the action that ended the attempt, adds one.
        """
        if is_reset or level_changed:
            self.level_actions = 0
        else:
            self.level_actions += 1

    def refusal(self) -> str | None:
        """The message to return instead of executing a RESET now, or None when it may run."""
        return None if self.level_actions > 0 else REFUSAL
