"""Festival of Legends — shared per-set helpers.

Currently houses the Harmonic-spell phase-swap dispatcher used by the
five "Swaps each turn" spells (Mood, Metal, Hip Hop, Pop, Disco —
Druid / Death Knight / Rogue / Priest / Paladin). The "Swaps each turn"
line on each Harmonic card means that on alternating turns the printed
text is replaced by another effect. HS ships a 6-way rotation across
the Harmonic family; we approximate as a binary swap (base ↔ alt)
which pins the "alternating effect" invariant the tests assert.

Each Harmonic card script declares two class attributes:

    _HARMONIC_BASE = <action or tuple of actions>   # printed text
    _HARMONIC_ALT  = <action or tuple of actions>   # alt branch

…then sets `play = _HarmonicSwap(TARGET)` (or `SELF` if untargeted).
At cast time `_HarmonicSwap.do` reads the controller's
`_harmonic_phase_swapped` boolean (lives on Player, toggled in
`Game.end_turn_cleanup`) and fires the chosen branch via cheat_action.
"""

from ..utils import *


class _HarmonicSwap(TargetedAction):
    """Reads the source card's `_HARMONIC_BASE` / `_HARMONIC_ALT` class
    attributes and the controller's `_harmonic_phase_swapped` flag,
    then fires the appropriate branch's actions."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        swapped = getattr(ctrl, "_harmonic_phase_swapped", False)
        attr = "_HARMONIC_ALT" if swapped else "_HARMONIC_BASE"
        branch = getattr(source.data.scripts, attr, None)
        if branch is None:
            return
        if not isinstance(branch, (list, tuple)):
            branch = (branch,)
        # The branch may reference TARGET / SELF / CONTROLLER selectors;
        # cheat_action resolves those in this source/target context.
        for action in branch:
            if action is None:
                continue
            source.game.cheat_action(source, [action])
