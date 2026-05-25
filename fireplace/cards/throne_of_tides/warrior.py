from ..utils import *


##
# Spells


def _is_colossal(card):
    return bool(card.tags.get(GameTag.COLOSSAL, 0)) and not card.tags.get(
        GameTag.COLOSSAL_LIMB, 0
    )


_RandomColossal = RandomMinion(custom_filter=_is_colossal)


class TID_715:
    """Clash of the Colossals"""

    # Add a random Colossal minion to both players' hands. Yours costs (2)
    # less.
    play = (
        Give(CONTROLLER, _RandomColossal).then(Buff(Give.CARD, "TID_715e")),
        Give(OPPONENT, _RandomColossal),
    )


class TID_715e:
    tags = {GameTag.COST: -2}


##
# Minions


class TID_714:
    """Igneous Lavagorger"""

    # Taunt. Battlecry: Dredge. Gain Armor equal to its Cost.
    tags = {GameTag.TAUNT: True}
    play = Dredge(CONTROLLER).then(
        GainArmor(FRIENDLY_HERO, Attr(Dredge.CARD, GameTag.COST))
    )


class TID_716:
    """Tidal Revenant"""

    # Battlecry: Deal 5 damage. Gain 8 Armor.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 5), GainArmor(FRIENDLY_HERO, 8)
