from ..utils import *


class _FullHealthExactCopy(ExactCopy):
    """ExactCopy (buffs/enchantments/tags preserved) but the copy spawns at
    FULL health — "Summon a copy" does not transfer the original's current
    damage. ExactCopy carries ret.damage = entity.damage; we clear it."""

    def copy(self, source, entity):
        ret = super().copy(source, entity)
        ret.damage = 0
        return ret


##
# Spells


class DEEP_010:
    """Aftershocks"""

    # Deal $1 damage to all minions, three times.
    # Costs (2) less if you cast a spell last turn.
    play = Hit(ALL_MINIONS, 1) * 3
    cost_mod = (Attr(CONTROLLER, "spells_played_last_turn") >= 1) & -2


class DEEP_011:
    """Burning Heart"""

    # Deal $2 damage to a minion. If it survives, give your hero +3 Attack
    # this turn.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2), Dead(TARGET) | Buff(FRIENDLY_HERO, "DEEP_011e")


# Heart of Fire — +3 Attack this turn. (TAG_ONE_TURN_EFFECT in data.)
DEEP_011e = buff(atk=3)


##
# Location


class DEEP_019:
    """Crimson Expanse"""

    # Choose a damaged minion. Summon a copy of it that goes Dormant for
    # one turn.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_DAMAGED_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    activate = Summon(CONTROLLER, _FullHealthExactCopy(TARGET)).then(
        Dormant(Summon.CARD, 1)
    )


class DEEP_019e:
    # Crimson Containment — Dormant. Awaken in @ turn(s).
    # Engine marker enchant attached automatically by the Dormant action.
    tags = {GameTag.TAG_ONE_TURN_EFFECT: False}


##
# Minions


class DEEP_020:
    """Deepminer Brann"""

    # <b>Battlecry:</b> If your deck has no duplicates, your <b>Battlecries</b>
    # trigger twice for the rest of the game.
    powered_up = -FindDuplicates(FRIENDLY_DECK)
    play = powered_up & Buff(CONTROLLER, "DEEP_020e")


class DEEP_020e:
    # Deepmining — Your Battlecries trigger twice.
    # Player enchant: a persistent aura (Refresh) that keeps EXTRA_BATTLECRIES
    # set on the controller for the rest of the game, surviving Brann's death.
    update = Refresh(CONTROLLER, {enums.EXTRA_BATTLECRIES: True})
