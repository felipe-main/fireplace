from ..utils import *


##
# Spells


class REV_334:
    """Burden of Pride"""

    # Summon three 1/3 Jailers with Taunt. If you have 20 or less Health,
    # give them +1/+1.
    play = (
        Summon(CONTROLLER, "REV_334t") * 3,
        (Attr(FRIENDLY_HERO, GameTag.HEALTH) <= 20)
        & Buff(FRIENDLY_MINIONS + ID("REV_334t"), "REV_334e"),
    )


class REV_334t:
    """Sanguine Jailer"""

    tags = {GameTag.TAUNT: True}


class REV_334e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class REV_337:
    """Riot!"""

    # Your minions can't be reduced below 1 Health this turn. They each
    # attack a random enemy minion. The damage floor is a per-turn aura
    # that sets min_health=1 on all friendly minions; the engine's
    # post-damage clamp (card.py: if health < min_health) handles the
    # actual flooring.
    play = (
        Buff(CONTROLLER, "REV_337e"),
        Attack(FRIENDLY_MINIONS, RANDOM_ENEMY_MINION),
    )


@custom_card
class REV_337e:
    tags = {
        GameTag.CARDNAME: "Riot! Damage Floor",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = Refresh(FRIENDLY_MINIONS, {GameTag.HEALTH_MINIMUM: 1})
    events = OWN_TURN_END.on(Destroy(SELF))


class REV_931:
    """Conqueror's Banner"""

    # Reveal a card from each player's deck, three times. Draw any of
    # yours that cost more. Approximation: draw a single card from your
    # deck (no compare).
    play = ForceDraw(FRIENDLY_DECK) * 3


##
# Weapons


class REV_933:
    """Imbued Axe"""

    # After your hero attacks, give your damaged minions +1/+1.
    # (Infused: +2/+2 instead.)
    events = Attack(FRIENDLY_HERO).after(
        Buff(FRIENDLY_MINIONS + DAMAGED, "REV_933e")
    )


class REV_933e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class REV_933t:
    """Imbued Axe"""

    # Infused weapon — +2/+2 buff instead.
    events = Attack(FRIENDLY_HERO).after(
        Buff(FRIENDLY_MINIONS + DAMAGED, "REV_933ee")
    )


@custom_card
class REV_933ee:
    tags = {
        GameTag.CARDNAME: "Imbued Axe Buff",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
    }


##
# Minions


class REV_006:
    """Suspicious Pirate"""

    # Battlecry: Discover a weapon. If your opponent guesses your choice,
    # they get a copy. Approximated as plain Discover-a-weapon.
    play = DISCOVER(RandomCollectible(type=CardType.WEAPON))


class REV_316:
    """Remornia, Living Blade"""

    # Rush. After this attacks, the minion is destroyed and the
    # controller equips the 4/10 Remornia weapon (REV_316t). Modeled
    # as an after-attack event that destroys SELF and summons the
    # weapon; current durability carries the remaining HP via the
    # weapon's max_durability.
    events = Attack(SELF).after(Destroy(SELF), Summon(CONTROLLER, "REV_316t"))


class REV_316t:
    """Remornia, Living Blade"""

    # Weapon form — base 4/10. The data card handles stats.


class REV_332:
    """Anima Extractor"""

    # Whenever a friendly minion takes damage, give a random minion in
    # your hand +1/+1.
    events = Damage(FRIENDLY_MINIONS).on(
        Buff(RANDOM(FRIENDLY_HAND + MINION), "REV_332e")
    )


class REV_332e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class REV_930:
    """Crazed Wretch"""

    # Has +2 Attack and Charge while damaged.
    update = (
        Find(SELF + DAMAGED)
        & Refresh(SELF, {GameTag.ATK: 2, GameTag.CHARGE: True})
    )


class REV_934:
    """Decimator Olgra"""

    # Battlecry: Gain +1/+1 for each damaged minion, then attack all
    # enemies. Approximation: gain the buff and attack a random enemy.
    play = (
        Buff(SELF, "REV_934e")
        * Count(ALL_MINIONS + DAMAGED),
        Attack(SELF, ALL_HEROES + ENEMY),
    )


class REV_934e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


##
# Locations


class REV_990:
    """Sanguine Depths"""

    # Deal 1 damage to a minion and give it +1 Attack.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Hit(TARGET, 1), Buff(TARGET, "REV_990e")


class REV_990e:
    tags = {GameTag.ATK: 1}
