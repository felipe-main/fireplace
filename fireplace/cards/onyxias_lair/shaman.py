from ..utils import *


##
# Spells


class ONY_011:
    """Don't Stand in the Fire!"""

    # Deal $10 damage randomly split among all enemy minions. Overload: (1)
    play = Hit(RANDOM(ENEMY_MINIONS), 1) * SPELL_DAMAGE(10)


class ONY_012:
    """Spirit Mount"""

    # Give a minion +1/+2 and <b>Spell Damage +1</b>. When it dies, summon a
    # Spirit Raptor (Bru'kan's Raptor — ONY_012t).
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "ONY_012e")


class ONY_012e:
    # Grants stat buff, Spell Damage +1, and a deathrattle that summons the
    # Spirit Raptor token.
    tags = {
        GameTag.ATK: 1,
        GameTag.HEALTH: 2,
        GameTag.SPELLPOWER: 1,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "ONY_012t")


class ONY_013:
    """Bracing Cold"""

    # Restore #5 Health to your hero. Reduce the Cost of a random spell in
    # your hand by (2).
    play = (
        Heal(FRIENDLY_HERO, 5),
        Find(FRIENDLY_HAND + SPELL) & Buff(RANDOM(FRIENDLY_HAND + SPELL), "ONY_013e"),
    )


class ONY_013e:
    tags = {GameTag.COST: -2}
