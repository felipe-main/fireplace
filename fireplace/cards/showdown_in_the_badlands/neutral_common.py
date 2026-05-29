"""Showdown in the Badlands — Neutral Common cards (WILD_WEST)."""

from ..utils import *


##
# Minions


class WW_001:
    """Kobold Miner"""

    # Battlecry: Excavate a treasure.
    play = Excavate(CONTROLLER)


class WW_044:
    """Tram Mechanic"""

    # Deathrattle: Get a Barrel of Sludge.
    deathrattle = Give(CONTROLLER, "WW_044t")


class WW_300:
    """Trapdoor Spider"""

    # Stealth, Poisonous (data). After your opponent plays a minion,
    # attack it.
    events = Play(OPPONENT, MINION).after(Attack(SELF, Play.CARD))


class WW_331:
    """Miracle Salesman"""

    # Deathrattle: Get a Tradeable Snake Oil.
    deathrattle = Give(CONTROLLER, "WW_331t")


class WW_376:
    """Cactus Rager"""

    # Poisonous (data only).


class WW_383:
    """Dryscale Deputy"""

    # Battlecry: The next time you draw a spell, get a copy of it.
    play = Buff(CONTROLLER, "WW_383e")


class WW_383e:
    # The next spell you draw gives you an extra copy.
    events = Draw(CONTROLLER).on(
        Find(Draw.CARD + SPELL) & (Give(CONTROLLER, Copy(Draw.CARD)), Destroy(SELF))
    )


class WW_391:
    """Gold Panner"""

    # At the end of your turn, draw a card.
    events = OWN_TURN_END.on(Draw(CONTROLLER))


class _DangBlastedDeathrattle(TargetedAction):
    # Deal 2 damage to all minions except friendly Elementals.
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        victims = [
            m
            for m in source.game.board
            if m.type == CardType.MINION
            and not (m.controller is ctrl and Race.ELEMENTAL in (m.races or []))
        ]
        for m in victims:
            source.game.cheat_action(source, [Hit(m, 2)])


class WW_397:
    """Dang-Blasted Elemental"""

    # Taunt. Deathrattle: Deal 2 damage to all minions except friendly
    # Elementals.
    deathrattle = _DangBlastedDeathrattle(SELF)


class _GaslightShuffleDraw(TargetedAction):
    # Shuffle your hand into your deck, then draw that many cards.
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        hand_cards = list(ctrl.hand)
        count = len(hand_cards)
        if count:
            source.game.cheat_action(source, [Shuffle(ctrl, hand_cards)])
        for _ in range(count):
            source.game.cheat_action(source, [Draw(ctrl)])


class WW_398:
    """Gaslight Gatekeeper"""

    # Battlecry: Shuffle your hand into your deck, then draw that many
    # cards.
    play = _GaslightShuffleDraw(CONTROLLER)


class _HighNoonDuel(TargetedAction):
    # Both players DRAW! Destroy the card that costs less.
    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        p1 = source.controller
        p2 = p1.opponent
        drawn = {}
        for player in (p1, p2):
            before = set(player.hand)
            game.cheat_action(source, [Draw(player)])
            new = [c for c in player.hand if c not in before]
            drawn[player] = new[0] if new else None
        c1 = drawn[p1]
        c2 = drawn[p2]
        if c1 is None or c2 is None:
            return
        cost1 = c1.cost
        cost2 = c2.cost
        if cost1 < cost2:
            game.cheat_action(source, [Destroy(c1)])
        elif cost2 < cost1:
            game.cheat_action(source, [Destroy(c2)])
        # Equal cost: neither is destroyed.


class WW_399:
    """High Noon Duelist"""

    # Deathrattle: Both players DRAW! Destroy the card that costs less.
    deathrattle = _HighNoonDuel(SELF)


class WW_418:
    """Ogre-Gang Outlaw"""

    # Rush (data). 50% chance to attack the wrong enemy.
    events = FORGETFUL


class WW_423:
    """Saloon Brewmaster"""

    # Battlecry: Return a friendly minion to your hand. Give it +2/+2.
    requirements = {
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Bounce(TARGET).then(Buff(Bounce.TARGET, "WW_423e", atk=2, max_health=2))


class WW_428:
    """Eroded Sediment"""

    # Battlecry: If you played an Elemental last turn, Discover an
    # Elemental from the past.
    play = ELEMENTAL_PLAYED_LAST_TURN & DISCOVER(RandomElemental(is_standard=False))


class WW_433:
    """Linedance Partner"""

    # Battlecry: If you're holding another 3-Cost card, summon a random
    # 3-Cost minion.
    play = Find(FRIENDLY_HAND + (COST == 3) - SELF) & Summon(
        CONTROLLER, RandomMinion(cost=3)
    )


class WW_434:
    """Sunspot Dragon"""

    # Tradeable, Lifesteal (data). Quickdraw: Deal 6 damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    play = QUICKDRAW & Hit(TARGET, 6)


class WW_435:
    """Bunny Stomper"""

    # Your Beasts have Rush.
    update = Refresh(FRIENDLY_MINIONS + BEAST, {GameTag.RUSH: True})


class WW_827:
    """Whelp Wrangler"""

    # At the end of your turn, get a 1/2 Whelp with Taunt.
    events = OWN_TURN_END.on(Give(CONTROLLER, "WW_816t"))


class _HorseshoeSling(TargetedAction):
    # Deal 2 damage to a random enemy minion. Quickdraw: And one of its
    # neighbors.
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        enemy_minions = list(ctrl.opponent.field)
        if not enemy_minions:
            return
        victim = source.game.random.choice(enemy_minions)
        source.game.cheat_action(source, [Hit(victim, 2)])
        if source.quickdraw_played:
            # Pick one neighbor (left or right) of the hit minion.
            field = victim.controller.field
            try:
                idx = field.index(victim)
            except ValueError:
                return
            neighbors = []
            if idx - 1 >= 0:
                neighbors.append(field[idx - 1])
            if idx + 1 < len(field):
                neighbors.append(field[idx + 1])
            if neighbors:
                neighbor = source.game.random.choice(neighbors)
                source.game.cheat_action(source, [Hit(neighbor, 2)])


class WW_900:
    """Horseshoe Slinger"""

    # Mech. Battlecry: Deal 2 damage to a random enemy minion.
    # Quickdraw: And one of its neighbors.
    play = _HorseshoeSling(SELF)


class WW_901:
    """Greedy Partner"""

    # Battlecry: If you're holding another 2-Cost card, get a Coin.
    play = Find(FRIENDLY_HAND + (COST == 2) - SELF) & Give(CONTROLLER, THE_COIN)


class WW_906:
    """Rowdy Partner"""

    # Battlecry: If you're holding another 4-Cost card, deal 4 damage.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Find(FRIENDLY_HAND + (COST == 4) - SELF) & Hit(TARGET, 4)
