"""Emerald Dream mini-set (Firelands) — the "Smoldering" mechanic.

Several mini-set spells read:
    "<effect using {0}>. (Upgrades each turn, but discards after {1}!)"

While the card sits in hand its effect value ({0}) rises by 1 at the start of
each of the controller's turns, and after a fixed number of turns the card is
discarded ({1}).

The per-turn magnitude and the discard threshold ({0} start/step and {1}) are
server-resolved (NOT present in CardXML — the tags carry no SCRIPT_DATA_NUM),
so the values here are best-fidelity approximations, flagged as `watch` rows in
the audit (same class as the Imbue @-scaling). Default: base {0} = 1, +1 per
turn held, discarded after SMOLDER_DISCARD_AFTER (3) of your turns.

Usage on a Smoldering card class:

    class FIR_911:
        '''Smoldering Grove'''
        class Hand:
            events = OWN_TURN_BEGIN.on(_SmolderTick(SELF))
        def play(self):
            yield Draw(CONTROLLER) * smolder_level(self, base=1)
"""

from ..utils import *

# Turns the card may be held before it is discarded (the printed {1}).
SMOLDER_DISCARD_AFTER = 3


class _SmolderTick(TargetedAction):
    """Bump a Smoldering card's held-turn counter; discard it once it has been
    held for SMOLDER_DISCARD_AFTER of the controller's turns."""

    TARGET = ActionArg()

    def do(self, source, target):
        held = getattr(target, "_smolder_turns_held", 0) + 1
        target._smolder_turns_held = held
        discard_after = getattr(target, "_smolder_discard_after", SMOLDER_DISCARD_AFTER)
        if held >= discard_after:
            target.discard()


def smolder_level(card, base=1, step=1):
    """The live {0} value: `base` on the turn the card became holdable, then
    `+step` for each of the controller's turns it has survived in hand."""
    return base + step * getattr(card, "_smolder_turns_held", 0)
