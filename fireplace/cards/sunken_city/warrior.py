from ..utils import *


##
# Spells


class TSC_939:
    """Forged in Flame"""

    # Destroy your weapon, then draw cards equal to its Attack.
    def play(self):
        weapon = self.controller.weapon
        if weapon is None:
            return
        atk = weapon.atk
        yield Destroy(weapon)
        for _ in range(atk):
            yield Draw(CONTROLLER)


class TSC_940:
    """From the Depths"""

    # Reduce the Cost of the bottom five cards in your deck by (3), then Dredge.
    def play(self):
        for card in list(self.controller.deck[:5]):
            yield Buff(card, "TSC_940e")
        yield Dredge(CONTROLLER)


@custom_card
class TSC_940e:
    tags = {
        GameTag.CARDNAME: "Sunken Cost",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class TSC_941:
    """Guard the City"""

    # Gain 3 Armor. Summon a 2/3 Naga with Taunt.
    play = GainArmor(FRIENDLY_HERO, 3), Summon(CONTROLLER, "TSC_941t")


@custom_card
class TSC_941t:
    tags = {
        GameTag.CARDNAME: "City Guard Naga",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 2,
        GameTag.ATK: 2,
        GameTag.HEALTH: 3,
        GameTag.CARDRACE: Race.NAGA,
        GameTag.TAUNT: True,
    }


class TSC_944:
    """The Fires of Zin-Azshari"""

    # Replace your deck with minions that cost (5) or more. They cost (5).
    def play(self):
        controller = self.controller
        # Drop the current deck, replace with random 5+ cost minions.
        target_size = len(controller.deck)
        for c in list(controller.deck):
            c.discard()
        for _ in range(target_size):
            new = controller.card(
                _pick_high_cost_minion(controller, self.game), self
            )
            new.zone = Zone.DECK
        for c in controller.deck:
            yield Buff(c, "TSC_944e")
        return


class TSC_944e:
    # Approximation — set cost to 5 via a large negative offset clamp.
    # The buff effectively wins out when the engine clamps to base 5.
    tags = {GameTag.COST: -100}


def _pick_high_cost_minion(controller, game):
    """Pick a random collectible minion costing 5+."""
    from ..utils import db
    import random as _random

    candidates = [
        cid
        for cid, c in db.items()
        if c.collectible
        and c.type == CardType.MINION
        and (c.cost or 0) >= 5
    ]
    return _random.choice(candidates) if candidates else "CS2_186"


##
# Minions


class TSC_659:
    """Trenchstalker"""

    # Battlecry: Attack three different random enemies.
    def play(self):
        enemies = (
            self.controller.opponent.field[:] + [self.controller.opponent.hero]
        )
        import random as _random

        _random.shuffle(enemies)
        for victim in enemies[:3]:
            if victim is None or getattr(victim, "dead", False):
                continue
            yield Attack(SELF, victim)


class TSC_660:
    """Nellie, the Great Thresher"""

    # Colossal +1. Battlecry: Discover 3 Pirates to crew Nellie's Ship.
    # Approximation: discover one Pirate.
    play = DISCOVER(RandomMinion(race=Race.PIRATE))


class TSC_660t:
    """Nellie's Pirate Ship"""

    # Taunt. Deathrattle: Add Nellie's Pirate crew to your hand.
    pass


class TSC_917:
    """Blackscale Brute"""

    # Taunt. Battlecry: If you have a weapon equipped, summon a 5/6
    # Naga with Rush.
    play = Find(FRIENDLY_WEAPON) & Summon(CONTROLLER, "TSC_917t")


@custom_card
class TSC_917t:
    tags = {
        GameTag.CARDNAME: "Battle Naga",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 5,
        GameTag.ATK: 5,
        GameTag.HEALTH: 6,
        GameTag.CARDRACE: Race.NAGA,
        GameTag.RUSH: True,
    }


class TSC_942:
    """Obsidiansmith"""

    # Battlecry: Dredge. If it's a minion or a weapon, give it +1/+1.
    play = Dredge(CONTROLLER).then(
        (
            (Attr(Dredge.CARD, GameTag.CARDTYPE) == int(CardType.MINION))
            | (Attr(Dredge.CARD, GameTag.CARDTYPE) == int(CardType.WEAPON))
        )
        & Buff(Dredge.CARD, "TSC_942e")
    )


TSC_942e = buff(atk=1, health=1)


class TSC_943:
    """Lady Ashvane"""

    # Battlecry: Give all weapons in your hand, deck, and battlefield +1/+1.
    play = (
        Buff(FRIENDLY_HAND + WEAPON, "TSC_943e"),
        Buff(FRIENDLY_DECK + WEAPON, "TSC_943e"),
        Find(FRIENDLY_WEAPON) & Buff(FRIENDLY_WEAPON, "TSC_943e"),
    )


TSC_943e = buff(atk=1, health=1)


##
# Weapons


class TSC_913:
    """Azsharan Trident"""

    # Deathrattle: Put a 'Sunken Trident' on the bottom of your deck.
    deathrattle = PutOnBottom(CONTROLLER, "TSC_913t")


class TSC_913t:
    """Sunken Trident"""

    # After your hero attacks, deal 2 damage to all enemy minions.
    events = Attack(FRIENDLY_HERO).after(Hit(ENEMY_MINIONS, 2))
