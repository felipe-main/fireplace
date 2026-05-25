from ..utils import *


##
# Spells


class REV_842:
    """Promotion"""

    # Give a Silver Hand Recruit +3/+3.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "REV_842e")


class REV_842e:
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class REV_948:
    """Service Bell"""

    # Discover a Class card from your deck and draw all copies of it.
    # Approximation: draw a random class card from your deck.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + CLASS_CARD))


class REV_950:
    """Divine Toll"""

    # Shoot 5 rays at random minions: friendly minions get +2/+2; enemy
    # minions take 2 damage. Approximated as 3 friendly buffs + 2 enemy
    # hits to spread the rays.
    play = (
        Buff(RANDOM(FRIENDLY_MINIONS), "REV_950e") * 3,
        Hit(RANDOM_ENEMY_MINION, 2) * 2,
    )


class REV_950e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


##
# Minions


class REV_947:
    """Muckborn Servant"""

    # Taunt. Battlecry: Discover a Paladin card.
    play = DISCOVER(RandomCollectible(card_class=CardClass.PALADIN))


class REV_951:
    """The Countess"""

    # Battlecry: If your deck has no Neutral cards, add 3 Legendary
    # Invitations to your hand. We use REV_951t as the invitation token.
    play = (
        Count(FRIENDLY_DECK - CLASS_CARD) == Count(FRIENDLY_DECK)
    ) & Give(CONTROLLER, "REV_951t") * 3


class REV_951t:
    """Legendary Invitation"""


class REV_952:
    """Sinful Sous Chef"""

    # Deathrattle: Add 2 Silver Hand Recruits to your hand.
    deathrattle = Give(CONTROLLER, "CS2_101t") * 2


class REV_955:
    """Stewart the Steward"""

    # Deathrattle: Give the next Silver Hand Recruit you summon +3/+3
    # and this Deathrattle. Approximated as a permanent buff trigger on
    # the next Silver Hand Recruit summoned.
    deathrattle = Buff(CONTROLLER, "REV_955e")


class REV_955e:
    events = Summon(CONTROLLER, ID("CS2_101t")).on(
        Buff(Summon.CARD, "REV_842e"), Destroy(SELF)
    )


class REV_958:
    """Buffet Biggun"""

    # Battlecry: Summon two Silver Hand Recruits. (Infused: Give them
    # +2 Attack and Divine Shield.)
    play = Summon(CONTROLLER, "CS2_101t") * 2


class REV_958t:
    """Buffet Biggun"""

    # Infused — Summon two SHRs with +2 Attack and Divine Shield.
    play = Summon(CONTROLLER, "CS2_101t").then(
        Buff(Summon.CARD, "REV_958e"), GiveDivineShield(Summon.CARD)
    ) * 2


class REV_958e:
    tags = {GameTag.ATK: 2}


class REV_961:
    """Elitist Snob"""

    # Battlecry: For each Paladin card in your hand, randomly gain
    # Divine Shield, Lifesteal, Rush, or Taunt. Approximation: gain
    # all four keywords once if any Paladin cards are in hand.
    play = (Count(FRIENDLY_HAND + CLASS_CARD) >= 1) & (
        GiveDivineShield(SELF),
        GiveLifesteal(SELF),
        GiveRush(SELF),
        Taunt(SELF),
    )


##
# Locations


class REV_983:
    """Great Hall"""

    # Set a minion's Attack and Health to 3.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Buff(TARGET, "REV_983e"), SetCurrentHealth(TARGET, 3)


class REV_983e:
    atk = SET(3)
    max_health = SET(3)
