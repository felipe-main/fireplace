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
    """Stamp the opponent with a 1-turn lockdown flag. Approximation: we
    don't model UI playability constraints — the flag is descriptive
    only and the engine still lets the opponent play any hand card."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._meltranix_lockdown_turns = 1


class MAW_014:
    """Prosecutor Mel'tranix"""

    # Battlecry: Your opponent can only play their left- and right-most
    # cards on their next turn. Approximation: stamp a flag; no engine
    # enforcement (engine has no per-card playability gating hook).
    play = _MeltranixLockHand(OPPONENT)
