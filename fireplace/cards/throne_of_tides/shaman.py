from ..utils import *


##
# Spells


class TID_005:
    """Command of Neptulon"""

    # Summon two 5/4 Elementals with Rush. Overload: (1) is carried by data.
    play = Summon(CONTROLLER, "TID_005t") * 2


class TID_005t:
    """Water Revenant"""

    # 5/4 Elemental with Rush — token, behavior driven by data tags.
    pass


##
# Minions


class TID_003:
    """Tidelost Burrower"""

    # Battlecry: Dredge. If it's a Murloc, summon a 2/2 copy of it.
    play = Dredge(CONTROLLER).then(
        (
            (Attr(Dredge.CARD, GameTag.CARDTYPE) == int(CardType.MINION))
            & (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.MURLOC))
        )
        & Summon(CONTROLLER, Copy(Dredge.CARD)).then(
            Buff(Summon.CARD, "TID_003e2")
        )
    )


class TID_003e2:
    # "Revealed" — flatten the dredged Murloc copy to a 2/2.
    atk = SET(2)
    max_health = SET(2)


class TID_004:
    """Clownfish"""

    # Battlecry: Your next two Murlocs cost (2) less.
    def play(self):
        self.controller.next_n_murlocs_discount = 2
        return
        yield
