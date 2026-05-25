from ..utils import *


##
# Spells


class _DewProcessStamp(TargetedAction):
    """Stamp the per-game flag on both players. The engine's
    _begin_turn hook reads `player.dew_process_active` and draws one
    extra card on turn begin."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.dew_process_active = True
        target.opponent.dew_process_active = True


class MAW_024:
    """Dew Process"""

    # For the rest of the game, players draw an extra card at the start
    # of their turn. Stamps a per-player flag both players consult on
    # turn-begin (engine hook in game._begin_turn).
    play = _DewProcessStamp(CONTROLLER)


class MAW_026:
    """Incarceration"""

    # Choose a minion. It goes Dormant for 3 turns.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Dormant(TARGET, 3)


##
# Minions


class MAW_025:
    """Attorney-at-Maw"""

    # Choose One — Silence a minion; or Give a minion Immune this turn.
    choose = ("MAW_025a", "MAW_025b")
    play = ChooseBoth(CONTROLLER) & (Silence(TARGET), Buff(TARGET, "MAW_025e"))


class MAW_025a:
    """Guilty!"""

    # Silence a minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Silence(TARGET)


class MAW_025b:
    """Innocent!"""

    # Give a minion Immune this turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "MAW_025e")


class MAW_025e:
    # Data card has TAG_ONE_TURN_EFFECT but no IMMUNE tag — patch the
    # script to add CANT_BE_DAMAGED so the engine actually grants
    # immunity. End-of-turn cleanup is handled by TAG_ONE_TURN_EFFECT.
    tags = {GameTag.CANT_BE_DAMAGED: True}
