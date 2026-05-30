from ..utils import *

from hearthstone.enums import CardType, Zone


##
# Custom actions


def _offer_deck_spells(source):
    """Offer up to 3 DISTINCT deck spells as preview copies for a faithful
    "Discover from your deck". Returns (controller, [preview cards]); the list
    is empty when the deck holds no spells."""
    ctrl = source.controller
    seen = set()
    distinct = []
    for c in ctrl.deck:
        if c.type == CardType.SPELL and c.id not in seen:
            seen.add(c.id)
            distinct.append(c)
    if not distinct:
        return ctrl, []
    n = min(3, len(distinct))
    picks = source.game.random.sample(distinct, n)
    return ctrl, [ctrl.card(c.id, source=source) for c in picks]


class _AsteroidStrike(TargetedAction):
    """Asteroid — when drawn, deal (2 + Bolide bonus) damage to a random
    enemy."""

    TARGET = ActionArg()

    def do(self, source, target):
        dmg = 2 + getattr(source.controller, "asteroid_damage_bonus", 0)
        amount = source.controller.get_spell_damage(source, dmg)
        source.game.cheat_action(source, [Hit(RANDOM(ENEMY_CHARACTERS), amount)])


class _ArmAsteroidBonus(TargetedAction):
    """Bolide Behemoth — your Asteroids deal 1 more damage this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.asteroid_damage_bonus += 1


class _ArmPlanetaryNavigator(TargetedAction):
    """Planetary Navigator — the next Draenei you play costs (2) less but has
    Overload: (2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_draenei_discount = 2
        game = source.game

        def hook(played):
            game.queue_actions(played, [Overload(played.controller, 2)])

        target.next_draenei_hooks.append(hook)


class _Triangulate(TargetedAction):
    """Triangulate — Discover a spell from your deck (move it to hand), then
    shuffle 3 copies of it into your deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl, offered = _offer_deck_spells(source)
        if not offered:
            return
        source.game.queue_actions(
            source,
            [Choice(ctrl, offered).then(_TriangulatePick(Choice.PLAYER, Choice.CARD))],
        )


class _TriangulatePick(TargetedAction):
    """Triangulate choose-callback: move the real chosen deck spell to hand,
    then shuffle 3 fresh copies of it into the deck."""

    PLAYER = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, picked):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if picked is None:
            return
        real = next((c for c in player.deck if c.id == picked.id), None)
        if real is not None:
            real.zone = Zone.HAND
        for _ in range(3):
            source.game.cheat_action(source, [Shuffle(player, picked.id)])


class _Cosmonaut(TargetedAction):
    """Cosmonaut — Discover a spell from your deck (move it to hand) and reduce
    its Cost by (5)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl, offered = _offer_deck_spells(source)
        if not offered:
            return
        source.game.queue_actions(
            source,
            [Choice(ctrl, offered).then(_CosmonautPick(Choice.PLAYER, Choice.CARD))],
        )


class _CosmonautPick(TargetedAction):
    """Cosmonaut choose-callback: move the real chosen deck spell to hand and
    apply the (5)-Cost reduction."""

    PLAYER = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, picked):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if picked is None:
            return
        real = next((c for c in player.deck if c.id == picked.id), None)
        if real is not None:
            real.zone = Zone.HAND
            source.game.cheat_action(source, [Buff(real, "GDB_443e")])


##
# Minions


class GDB_434:
    """Bolide Behemoth"""

    # Battlecry: Your Asteroids deal 1 more damage this game. Spellburst:
    # Shuffle 3 of them into your deck.
    play = _ArmAsteroidBonus(CONTROLLER)
    spellburst = Shuffle(CONTROLLER, "GDB_430") * 3


class GDB_443:
    """Cosmonaut"""

    # Battlecry: Discover a spell from your deck. Reduce its Cost by (5).
    play = _Cosmonaut(SELF)


class GDB_444:
    """Planetary Navigator"""

    # Battlecry: The next Draenei you play costs (2) less, but has Overload: (2).
    play = _ArmPlanetaryNavigator(CONTROLLER)


class GDB_447:
    """Farseer Nobundo"""

    # Deathrattle: Open the Galaxy's Lens. It absorbs the power of the next
    # spell you cast. (Approximation: summons the Galaxy's Lens Location; the
    # spell-absorb interaction is simplified. Tracked in review.csv.)
    deathrattle = Summon(CONTROLLER, "GDB_136t")


class GDB_448:
    """Murmur"""

    # Your Battlecry minions cost (1), but immediately die after being played.
    # (Approximation: the cost-to-(1)/die-on-play aura is not modelled — plays
    # as a 6/6 Elemental. Tracked in review.csv.)


##
# Spells


class GDB_445:
    """Meteor Storm"""

    # Deal $5 damage to all minions. Shuffle 5 Asteroids into your deck.
    play = Hit(ALL_MINIONS, 5), Shuffle(CONTROLLER, "GDB_430") * 5


class GDB_451:
    """Triangulate"""

    # Discover a different spell from your deck. Shuffle 3 copies of it into
    # your deck.
    play = _Triangulate(SELF)


class GDB_479:
    """Nebula"""

    # Discover two 8-Cost minions to summon with Taunt and Elusive.
    play = (
        Discover(CONTROLLER, RandomMinion(cost=8)).then(
            Summon(CONTROLLER, Discover.CARD).then(
                SetTags(
                    Summon.CARD,
                    {
                        GameTag.TAUNT: True,
                        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
                        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
                    },
                )
            )
        )
    ) * 2


class GDB_864:
    """First Contact"""

    # Summon two random 1-Cost minions. Overload: (1) (data).
    play = Summon(CONTROLLER, RandomMinion(cost=1)) * 2


class GDB_901:
    """Ultraviolet Breaker"""

    # Battlecry: Deal 3 damage to an enemy minion. Shuffle 3 Asteroids into
    # your deck.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Hit(TARGET, 3), Shuffle(CONTROLLER, "GDB_430") * 3


##
# Tokens


class GDB_430:
    """Asteroid"""

    # Casts When Drawn: Deal damage to a random enemy (2 + Bolide bonus).
    play = _AsteroidStrike(SELF)


##
# Enchantments


@custom_card
class GDB_443e:
    # Cosmonaut — the discovered spell costs (5) less.
    tags = {
        GameTag.CARDNAME: "Cosmonaut",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -5,
    }
