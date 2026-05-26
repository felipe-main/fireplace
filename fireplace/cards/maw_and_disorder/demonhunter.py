from ..utils import *

from ..castle_nathria.utils import InfuseCardtextMixin


##
# Spells


class MAW_012(InfuseCardtextMixin):
    """All Fel Breaks Loose"""

    # Summon a friendly Demon that died this game. (Infused: 3 instead.)
    # Copy() wraps the random pick so the resurrected minion keeps its
    # printed/base stats (the standard resurrect idiom).
    play = Summon(CONTROLLER, Copy(RANDOM(FRIENDLY + KILLED + MINION + DEMON)))


class MAW_012t:
    """All Fel Breaks Loose"""

    # Infused — summon three friendly Demons that died this game.
    play = Summon(
        CONTROLLER, Copy(RANDOM(FRIENDLY + KILLED + MINION + DEMON))
    ) * 3


##
# Minions


class MAW_008:
    """Sightless Magistrate"""

    # Battlecry: Both players draw until they have 5 cards.
    play = DrawUntil(CONTROLLER, 5), DrawUntil(OPPONENT, 5)


class _MeltranixLockHand(TargetedAction):
    """Stamp the opponent with a leftmost/rightmost lockdown lasting
    exactly their next turn.  Set to 2 because the engine ticks the
    counter on turn-begin: 2 → 1 on opp's next begin (active), 1 → 0
    on opp's turn after that (released)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._meltranix_lockdown_turns = 2


class MAW_014:
    """Prosecutor Mel'tranix"""

    # Battlecry: Your opponent can only play their left- and right-most
    # cards on their next turn.  Engine enforcement lives in
    # card.py is_playable() (filters middle hand cards while the
    # opponent's `_meltranix_lockdown_turns` is > 0).
    play = _MeltranixLockHand(OPPONENT)
