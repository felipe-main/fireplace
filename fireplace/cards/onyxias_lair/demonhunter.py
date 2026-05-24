from ..utils import *


##
# Spells


class ONY_014:
    """Keen Reflex"""

    # Deal $1 damage to all minions. <b>Honorable Kill:</b> Gain +1 Attack
    # this turn (on the friendly hero — emulates the data-script side
    # effect of a HK trigger on an AOE spell).
    play = Hit(ALL_MINIONS, 1)
    honorable_kill = Buff(FRIENDLY_HERO, "ONY_014e")


class ONY_014e:
    tags = {GameTag.ATK: 1, enums.TEMPORARY: 1}


class ONY_016:
    """Wings of Hate (Rank 1)"""

    # Summon two 1/1 Felwings. <i>(Upgrades when you have 5 Mana.)</i>
    play = Summon(CONTROLLER, "BT_922t") * 2

    class Hand:
        update = (MANA(CONTROLLER) >= 5) & Morph(SELF, "ONY_016t")


class ONY_016t:
    """Wings of Hate (Rank 2)"""

    play = Summon(CONTROLLER, "BT_922t") * 3

    class Hand:
        update = (MANA(CONTROLLER) >= 10) & Morph(SELF, "ONY_016t2")


class ONY_016t2:
    """Wings of Hate (Rank 3)"""

    play = Summon(CONTROLLER, "BT_922t") * 4


##
# Minions


class ONY_036:
    """Razorglaive Sentinel"""

    # After you play the left or right-most card in your hand, draw a card.
    events = Play(CONTROLLER, PLAY_OUTCAST).after(Draw(CONTROLLER))
