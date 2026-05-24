from ..utils import *


##
# Minions


class AV_261:
    """Flag Runner"""

    # Whenever a friendly minion dies, gain +1 Attack.
    events = Death(FRIENDLY + MINION).on(Buff(SELF, "AV_261e"))


AV_261e = buff(atk=1)


class AV_262:
    """Warden of Chains"""

    # [x]<b>Taunt</b> <b>Battlecry:</b> If you're holding a Demon that costs
    # (5) or more, gain +1/+2.
    play = Find(FRIENDLY_HAND + DEMON + (COST >= 5)) & Buff(SELF, "AV_262e2")


class AV_262e2:
    # "Terrifying" — Blizzard's real enchant id for the Warden buff.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class AV_265:
    """Ur'zul Giant"""

    # Costs (1) less for each friendly minion that died this game.
    cost_mod = -Count(FRIENDLY + KILLED + MINION)


class AV_267:
    """Caria Felsoul"""

    # <b>Battlecry:</b> Transform into a 6/6 copy of a Demon in your deck.
    play = Morph(SELF, RANDOM(FRIENDLY_DECK + DEMON + MINION)).then(
        Buff(Morph.CARD, "AV_267e2")
    )


class AV_267e2:
    # "Demonic" — Blizzard's real enchant id for the Caria 6/6 morph stats.
    tags = {GameTag.ATK: 6, GameTag.HEALTH: 6}


class AV_118:
    """Battleworn Vanguard"""

    # [x]After your hero attacks, summon two 1/1 Felwings.
    # Uses BT_922t (the existing 1/1 Felwing token from Outlands).
    events = Attack(FRIENDLY_HERO).after(Summon(CONTROLLER, "BT_922t") * 2)


##
# Spells


class AV_264:
    """Sigil of Reckoning"""

    # At the start of your next turn, summon a random Demon from your hand.
    events = OWN_TURN_BEGIN.on(
        Summon(CONTROLLER, RANDOM(FRIENDLY_HAND + DEMON)), Destroy(SELF)
    )


class AV_269:
    """Flanking Maneuver"""

    # Summon a 4/2 Demon with <b>Rush</b>. If it dies this turn, summon
    # another.
    play = Summon(CONTROLLER, "AV_269t").then(
        Death(Summon.CARD).on(Summon(CONTROLLER, "AV_269t"))
    )


class AV_661:
    """Field of Strife"""

    # [x]Your minions have +1 Attack. Lasts 3 turns.
    update = Refresh(FRIENDLY_MINIONS, {GameTag.ATK: 1})


##
# Weapons


class AV_209:
    """Dreadprison Glaive"""

    # [x]<b>Honorable Kill:</b> Deal damage equal to your hero's Attack to the
    # enemy hero.
    honorable_kill = Hit(ENEMY_HERO, ATK(FRIENDLY_HERO))


##
# Heros


class AV_204:
    """Kurtrus, Demon-Render"""

    # [x]<b>Battlecry:</b> Summon two @/4 Demons with <b>Rush</b>. <i>(Improved
    # by your hero attacks this game.)</i>
    # Demon's attack scales with the player's `num_hero_attacks_this_game`
    # counter; we apply the buff after summoning.
    play = Summon(CONTROLLER, "AV_204t2").then(
        Buff(Summon.CARD, "AV_204e", atk=Attr(CONTROLLER, "num_hero_attacks_this_game"))
    ) * 2
