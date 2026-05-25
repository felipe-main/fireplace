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
    # We snapshot each new card's printed cost on a per-card attribute
    # and apply a Cost = 5 buff (delta from printed cost).
    def play(self):
        controller = self.controller
        # Preserve cant_fatigue across the deck rewrite — some tests/runs
        # set it to skip fatigue damage; replacing the deck shouldn't
        # change that game-wide state.
        cant_fatigue = controller.cant_fatigue
        target_size = len(controller.deck)
        for c in list(controller.deck):
            c.discard()
        for _ in range(target_size):
            new = controller.card(
                _pick_high_cost_minion(controller, self.game), self
            )
            new.zone = Zone.DECK
        controller.cant_fatigue = cant_fatigue
        for c in controller.deck:
            base = max(0, c.data.cost or 0)
            delta = 5 - base
            yield Buff(c, "TSC_944e", cost=delta)
        return


TSC_944e = buff()


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


class _NellieRememberCrew(TargetedAction):
    """Side-effect action used by Nellie's Discover .then() chain to
    append each chosen Pirate to the Ship's crew list. The Ship token
    holds the list on `_nellie_crew`; the Ship's deathrattle then gives
    the same set back to Nellie's hand."""

    TARGET = ActionArg()  # the discovered Pirate card

    def do(self, source, target):
        ship = next(
            (m for m in source.controller.field if m.id == "TSC_660t"),
            None,
        )
        if ship is None:
            return
        if not hasattr(ship, "_nellie_crew"):
            ship._nellie_crew = []
        if target is not None and hasattr(target, "id"):
            ship._nellie_crew.append(target.id)


class TSC_660:
    """Nellie, the Great Thresher"""

    # Colossal +1. Battlecry: Discover 3 Pirates to crew Nellie's Ship.
    # The three Discovers are nested inside each other's .then() callbacks
    # so each choice is resolved before the next one is offered — a flat
    # tuple of Discovers would all set `player.choice` at once and only
    # the last would survive.
    play = Discover(CONTROLLER, RandomMinion(race=Race.PIRATE)).then(
        Give(CONTROLLER, Discover.CARD),
        _NellieRememberCrew(Discover.CARD),
        Discover(CONTROLLER, RandomMinion(race=Race.PIRATE)).then(
            Give(CONTROLLER, Discover.CARD),
            _NellieRememberCrew(Discover.CARD),
            Discover(CONTROLLER, RandomMinion(race=Race.PIRATE)).then(
                Give(CONTROLLER, Discover.CARD),
                _NellieRememberCrew(Discover.CARD),
            ),
        ),
    )


class TSC_660t:
    """Nellie's Pirate Ship"""

    # Taunt. Deathrattle: Add Nellie's Pirate crew to your hand.
    def deathrattle(self):
        crew = getattr(self, "_nellie_crew", None) or []
        for card_id in crew:
            yield Give(CONTROLLER, card_id)


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
