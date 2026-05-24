from ..utils import *


##
# Minions


class AV_321:
    """Glory Chaser"""

    # After you play a <b>Taunt</b> minion, draw a card.
    events = Play(CONTROLLER, MINION + TAUNT).after(Draw(CONTROLLER))


class AV_323:
    """Scrapsmith"""

    # <b>Taunt</b> <b>Battlecry:</b> Add two 2/4 Grunts with <b>Taunt</b> to
    # your hand.
    play = Give(CONTROLLER, "AV_323t") * 2


class AV_145:
    """Captain Galvangar"""

    # [x]<b>Battlecry:</b> If you have gained 15 or more Armor this game,
    # gain +3/+3 and <b>Charge</b>.
    play = (Attr(CONTROLLER, "armor_gained_this_game") >= 15) & (
        Buff(SELF, "AV_145e"),
        GiveCharge(SELF),
    )


AV_145e = buff(atk=3, health=3)


class AV_565:
    """Axe Berserker"""

    # <b>Rush</b>. <b>Honorable Kill:</b> Draw a weapon.
    honorable_kill = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + WEAPON))


##
# Spells


class AV_108:
    """Shield Shatter"""

    # [x]Deal $5 damage to all minions. Costs (1) less for each Armor you
    # have.
    cost_mod = -Attr(FRIENDLY_HERO, GameTag.ARMOR)
    play = Hit(ALL_MINIONS, 5)


class AV_109:
    """Frozen Buckler"""

    # Gain 10 Armor. At the start of your next turn, lose 5 Armor.
    play = GainArmor(FRIENDLY_HERO, 10), Summon(CONTROLLER, "AV_109e")


class AV_109e:
    # Hidden helper that loses 5 armor next turn then destroys itself.
    events = OWN_TURN_BEGIN.on(GainArmor(FRIENDLY_HERO, -5), Destroy(SELF))


class AV_322:
    """Snowed In"""

    # Destroy a damaged minion. <b>Freeze</b> all other minions.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_DAMAGED_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Destroy(TARGET), Freeze(ALL_MINIONS - TARGET)


class AV_119:
    """To the Front!"""

    # Your minions cost (2) less this turn <i>(but not less than 1)</i>.
    play = Buff(FRIENDLY_HAND + MINION, "AV_119e")


class AV_119e:
    tags = {GameTag.COST: -2}
    events = OWN_TURN_END.on(Destroy(SELF))


class AV_660:
    """Iceblood Garrison"""

    # [x]At the end of your turn, deal $1 damage to all_ minions. Lasts 3
    # turns.
    events = OWN_TURN_END.on(Hit(ALL_MINIONS, 1))


##
# Heros


class AV_202:
    """Rokara, the Valorous"""

    # <b>Battlecry:</b> Equip a 5/2 Unstoppable Force.
    # AV_202t2 is the 5/2 Unstoppable Force weapon token.
    play = Summon(CONTROLLER, "AV_202t2")
