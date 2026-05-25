from ..utils import *


##
# Spells


class REV_350:
    """Frenzied Fangs"""

    # Summon two 2/1 Bats. (Infused: Give them +1/+2.)
    play = Summon(CONTROLLER, "REV_350t") * 2


class REV_350t:
    """Thirsty Bat"""


class REV_350t2:
    """Frenzied Fangs"""

    # Infused — Summon two 2/1 Bats and give them +1/+2.
    play = Summon(CONTROLLER, "REV_350t").then(Buff(Summon.CARD, "REV_350e")) * 2


class REV_350e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class REV_361:
    """Wild Spirits"""

    # Summon two different Dormant Wildseeds. Make your Wildseeds awaken
    # 1 turn sooner. The Wildseed pool isn't implemented in our engine
    # (a TITANS-era construct); approximate with two random Beasts.
    play = Summon(CONTROLLER, RandomMinion(race=Race.BEAST)) * 2


class REV_364:
    """Stag Charge"""

    # Deal 3 damage. Summon a random Dormant Wildseed.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 3), Summon(CONTROLLER, RandomMinion(race=Race.BEAST))


class REV_369:
    """Collateral Damage"""

    # Deal 6 damage to three random enemy minions. Excess damage hits the
    # enemy hero. Approximation: deal 6 to three random enemies; excess is
    # not modeled.
    play = Hit(RANDOM_ENEMY_MINION, 6) * 3


##
# Minions


class REV_352:
    """Stonebound Gargon"""

    # Rush. (Infused: Also damages the minions next to whomever this
    # attacks — CLEAVE applied to its attack.)
    pass


class REV_352t:
    """Stonebound Gargon"""

    # Infused — Rush + cleave on its attack.
    events = Attack(SELF).on(Hit(TARGET_ADJACENT, ATK(SELF)))


class REV_353:
    """Huntsman Altimor"""

    # Battlecry: Summon a Gargon Companion. (Infused 4: Summon another.
    # Infused 8: And another!)
    play = Summon(CONTROLLER, RandomMinion(race=Race.BEAST))


class REV_353t:
    """Huntsman Altimor"""

    # Infused — summon two Gargon Companions instead.
    play = Summon(CONTROLLER, RandomMinion(race=Race.BEAST)) * 2


class REV_356:
    """Batty Guest"""

    # Deathrattle: Summon a 2/1 Bat.
    deathrattle = Summon(CONTROLLER, "REV_350t")


class REV_360:
    """Spirit Poacher"""

    # Battlecry: Summon a random Dormant Wildseed. Approximated as a
    # random Beast minion.
    play = Summon(CONTROLLER, RandomMinion(race=Race.BEAST))


class REV_363:
    """Ara'lon"""

    # Battlecry: Summon one of each Dormant Wildseed. Approximated as
    # four random Beasts.
    play = Summon(CONTROLLER, RandomMinion(race=Race.BEAST)) * 4


##
# Locations


class REV_362:
    """Castle Kennels"""

    # Give a friendly minion +2 Attack. If it's a Beast, give it Rush.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = (
        Buff(TARGET, "REV_362e"),
        (Find(TARGET + BEAST)) & GiveRush(TARGET),
    )


class REV_362e:
    tags = {GameTag.ATK: 2}
