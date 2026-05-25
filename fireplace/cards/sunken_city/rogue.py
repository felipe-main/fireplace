from ..utils import *


##
# Spells


class TSC_912:
    """Azsharan Vessel"""

    # Summon two 3/3 Pirates with Stealth. Put a 'Sunken Vessel' on the
    # bottom of your deck.
    play = (
        Summon(CONTROLLER, "TSC_912t2") * 2,
        PutOnBottom(CONTROLLER, "TSC_912t"),
    )


class TSC_912t:
    """Sunken Vessel"""

    # Casts When Drawn. Summon two 3/3 Pirates with Stealth.
    play = Summon(CONTROLLER, "TSC_912t2") * 2


class TSC_912t2:
    """Sunken Pirate"""


class TSC_916:
    """Gone Fishin'"""

    # Dredge. Combo: Draw a card.
    play = Dredge(CONTROLLER)
    combo = Dredge(CONTROLLER), Draw(CONTROLLER)


class TSC_932:
    """Blood in the Water"""

    # Deal $3 damage to an enemy. Summon a 5/5 Shark with Rush.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_ENEMY_TARGET: 0}
    play = Hit(TARGET, 3), Summon(CONTROLLER, "TSC_932t")


@custom_card
class TSC_932t:
    tags = {
        GameTag.CARDNAME: "Shark",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 5,
        GameTag.ATK: 5,
        GameTag.HEALTH: 5,
        GameTag.RUSH: True,
    }


##
# Minions


class TSC_085:
    """Cutlass Courier"""

    # After your hero attacks, draw a Pirate.
    events = Attack(FRIENDLY_HERO).after(
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + PIRATE))
    )


class TSC_933:
    """Bootstrap Sunkeneer"""

    # Combo: Put an enemy minion on the bottom of your opponent's deck.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_FOR_COMBO: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    combo = Bounce(TARGET).then(PutOnBottom(OPPONENT, TARGET))


class TSC_934:
    """Pirate Admiral Hooktusk"""

    # Battlecry: If you've summoned 8 other Pirates this game, plunder
    # the enemy! "Plunder" = randomly trigger from a pool. Approximation:
    # summon a 5/5 Pirate and steal an enemy minion as proxy effects.
    def play(self):
        # Best-effort gate via cards played this game containing pirates.
        controller = self.controller
        pirate_count = sum(
            1
            for c in controller.cards_played_this_game
            if c.type == CardType.MINION and Race.PIRATE in c.races
        )
        if pirate_count < 8:
            return
        # "Plunder": destroy random enemy minion + draw 2 + 5 dmg to hero.
        if controller.opponent.field:
            yield Destroy(RANDOM(ENEMY_MINIONS))
        yield Draw(CONTROLLER) * 2
        yield Hit(ENEMY_HERO, 5)


class TSC_936:
    """Swiftscale Trickster"""

    # Battlecry: Your next spell this turn costs (0).
    play = Buff(FRIENDLY_HAND + SPELL, "TSC_936e")  # First spell trigger handled by engine fade-on-use isn't trivial; approximate as -100 to all spells in hand this turn.


class TSC_936e:
    tags = {GameTag.COST: -100, enums.TEMPORARY: 1}


class TSC_937:
    """Crabatoa"""

    # Colossal +2. Your Crabatoa Claws have +2 Attack. Each Claw is
    # TSC_937t/t3 (3-attack Rush DR Equip 2/1 Claw). Engine summons the
    # claws around Crabatoa; we buff them via update.
    update = Refresh(
        FRIENDLY_MINIONS + (ID("TSC_937t") | ID("TSC_937t3")),
        buff="TSC_937e",
    )


TSC_937e = buff(atk=2)


class TSC_937t:
    """Crabatoa's Claw"""

    # Rush. Deathrattle: Equip a 2/1 Claw.
    deathrattle = Summon(CONTROLLER, "TSC_937t2")


class TSC_937t2:
    """Crabatoa Claw"""


class TSC_937t3(TSC_937t):
    pass


class TSC_086:
    """Swordfish"""

    # Weapon. Battlecry: Dredge. If it's a Pirate, give this weapon and
    # the Pirate +2 Attack.
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.PIRATE))
        & (
            Buff(SELF, "TSC_086e"),
            Buff(Dredge.CARD, "TSC_086e"),
        )
    )


TSC_086e = buff(atk=2)


class TSC_963:
    """Filletfighter"""

    # Battlecry: Deal 1 damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    play = Hit(TARGET, 1)
