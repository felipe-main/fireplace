from ..utils import *


##
# Spells


class TID_703:
    """Topple the Idol"""

    # Dredge. Reveal it and deal damage equal to its Cost to all minions.
    play = Dredge(CONTROLLER).then(
        Hit(ALL_MINIONS, Attr(Dredge.CARD, GameTag.COST))
    )


##
# Minions


class TID_704:
    """Fossil Fanatic"""

    # After your hero attacks, draw a Fel spell.
    events = Attack(FRIENDLY_HERO).after(
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + FEL_SPELL))
    )


class TID_706:
    """Herald of Chaos"""

    # Lifesteal. Battlecry: If you've cast a Fel spell while holding this,
    # gain Rush.
    tags = {GameTag.LIFESTEAL: True}

    def play(self):
        schools = getattr(self, "spell_schools_cast_while_holding", set())
        if int(SpellSchool.FEL) in schools:
            yield Buff(self, "TID_706e")


class TID_706e:
    tags = {GameTag.RUSH: True}
