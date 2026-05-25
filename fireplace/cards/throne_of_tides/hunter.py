from ..utils import *


##
# Spells


class TID_075:
    """Shellshot"""

    # Deal $3 damage to a random enemy minion. Repeat this with 1 less damage.
    def play(self):
        for dmg in (3, 2, 1):
            if not self.controller.opponent.field:
                return
            yield Hit(RANDOM(ENEMY_MINIONS), dmg)


##
# Minions


class TID_074(ThreeSpellsProgressUtils):
    """Ancient Krakenbane"""

    # Battlecry: If you've cast three spells while holding this, deal 5
    # damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}

    def play(self):
        if (
            getattr(self, "spells_cast_while_holding", 0) >= 3
            and self.target is not None
        ):
            yield Hit(self.target, 5)


class TID_099:
    """K9-0tron"""

    # Battlecry: Dredge. If it's a 1-Cost minion, summon it.
    play = Dredge(CONTROLLER).then(
        (
            (Attr(Dredge.CARD, GameTag.CARDTYPE) == int(CardType.MINION))
            & (Attr(Dredge.CARD, GameTag.COST) == 1)
        )
        & Summon(CONTROLLER, Dredge.CARD)
    )
