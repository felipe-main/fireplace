from ..utils import *


##
# Minions


class AV_112:
    """Snowblind Harpy"""

    # <b>Battlecry:</b> If you're holding a Frost spell, gain 5 Armor.
    play = Find(FRIENDLY_HAND + SPELL) & GainArmor(FRIENDLY_HERO, 5)


class AV_134:
    """Frostwolf Warmaster"""

    # Costs (1) less for each card you've played this turn.
    cost_mod = -Attr(CONTROLLER, GameTag.NUM_CARDS_PLAYED_THIS_TURN)


class AV_135:
    """Stormpike Marshal"""

    # [x]<b>Taunt</b> If you took 5 or more damage on your opponent's turn,
    # this costs (1).
    # Cost reduces to 1 (i.e. -3 from base 4) when the trigger condition
    # holds. The counter resets at the start of each of your turns.
    cost_mod = (Attr(CONTROLLER, "damage_taken_on_opponents_turn") >= 5) & -3


class AV_136:
    """Kobold Taskmaster"""

    # [x]<b>Battlecry:</b> Add 2 Armor Scraps to your hand that give +2
    # Health to a minion.
    play = Give(CONTROLLER, "AV_136t") * 2


class AV_137:
    """Irondeep Trogg"""

    # [x]After your opponent casts a spell, summon another Irondeep Trogg.
    events = Play(OPPONENT, SPELL).after(Summon(CONTROLLER, "AV_137"))
