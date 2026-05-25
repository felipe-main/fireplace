from ..utils import *


##
# Spells


class REV_504:
    """Solid Alibi"""

    # Until your next turn, your hero can only take 1 damage at a time.
    # Approximated as Ice Block-style hero buff with a per-turn marker
    # (incoming_damage_divider isn't quite the same, but close).
    play = Buff(FRIENDLY_HERO, "REV_504e")


class REV_504e:
    tags = {GameTag.INCOMING_DAMAGE_CAP: 1}
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


class REV_505:
    """Cold Case"""

    # Summon two 2/2 Volatile Skeletons. Gain 4 Armor.
    play = Summon(CONTROLLER, "REV_845") * 2, GainArmor(FRIENDLY_HERO, 4)


class REV_516:
    """Vengeful Visage"""

    # Secret: After an enemy minion attacks your hero, summon a copy of
    # it to attack the enemy hero.
    secret = Attack(ENEMY_MINIONS, FRIENDLY_HERO).after(
        Reveal(SELF),
        Summon(CONTROLLER, Copy(Attack.ATTACKER)).then(
            Attack(Summon.CARD, ENEMY_HERO)
        ),
    )


class REV_601:
    """Frozen Touch"""

    # Deal 3 damage. (Infused: Add a Frozen Touch to your hand.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 3)


class REV_601t:
    """Frozen Touch"""

    # Infused — Deal 3 damage; add a Frozen Touch back to your hand.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 3), Give(CONTROLLER, "REV_601")


class REV_840:
    """Deathborne"""

    # Deal 2 damage to all minions. Summon a 2/2 Volatile Skeleton for
    # each killed. We approximate by counting dying minions before/after
    # via a custom action.
    play = (
        Hit(ALL_MINIONS, 2),
        Summon(
            CONTROLLER, "REV_845"
        ) * Count(KILLED_THIS_TURN + MINION),
    )


##
# Minions


class REV_000:
    """Suspicious Alchemist"""

    # Battlecry: Discover a spell. If your opponent guesses your choice,
    # they get a copy. Approximated as a plain Discover-a-spell.
    play = DISCOVER(RandomSpell())


class REV_513:
    """Chatty Bartender"""

    # At the end of your turn, if you control a Secret, deal 2 damage to
    # all enemies.
    events = OWN_TURN_END.on(
        (Count(FRIENDLY + SECRET) >= 1) & Hit(ENEMY_CHARACTERS, 2)
    )


class REV_514:
    """Kel'Thuzad, the Inevitable"""

    # Battlecry: Resurrect your Volatile Skeletons. Any that can't fit on
    # the battlefield instantly explode (deal 2 to enemy hero each).
    play = Summon(
        CONTROLLER,
        FRIENDLY + KILLED + MINION + ID("REV_845"),
    )


class REV_515:
    """Orion, Mansion Manager"""

    # After a friendly Secret is revealed, cast a different Mage Secret
    # and gain +2/+2.
    events = Reveal(FRIENDLY + SECRET).on(
        CastSpell(RandomSpell(card_class=CardClass.MAGE, secret=True)),
        Buff(SELF, "REV_515e"),
    )


class REV_515e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


##
# Locations


class REV_602:
    """Nightcloak Sanctum"""

    # Freeze a minion. Summon a 2/2 Volatile Skeleton.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Freeze(TARGET), Summon(CONTROLLER, "REV_845")
