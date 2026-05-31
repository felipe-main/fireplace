"""The Great Dark Beyond — SHAMAN collectible card tests.

Covers all 10 collectible Shaman cards (GDB_ prefix):
  GDB_434 Bolide Behemoth, GDB_443 Cosmonaut, GDB_444 Planetary Navigator,
  GDB_445 Meteor Storm, GDB_447 Farseer Nobundo, GDB_448 Murmur,
  GDB_451 Triangulate, GDB_479 Nebula, GDB_864 First Contact,
  GDB_901 Ultraviolet Breaker.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards

ASTEROID = "GDB_430"
FIREBALL = "CS2_029"


# GDB_434 — Bolide Behemoth: Battlecry: Your Asteroids deal 1 more damage this
# game. Spellburst: Shuffle 3 of them into your deck.
def test_bolide_behemoth_battlecry_arms_asteroid_bonus():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    assert p1.asteroid_damage_bonus == 0
    behemoth = p1.give("GDB_434")
    behemoth.play()
    assert p1.asteroid_damage_bonus == 1
    # Spellburst is armed until a spell is cast.
    assert behemoth.has_spellburst


def test_bolide_behemoth_spellburst_shuffles_three_asteroids():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.cant_fatigue = True
    behemoth = p1.give("GDB_434")
    behemoth.play()
    assert len([c for c in p1.deck if c.id == ASTEROID]) == 0
    # Cast any spell to trigger spellburst -> shuffle 3 Asteroids into deck.
    p1.give(FIREBALL).play(target=game.player2.hero)
    assert not behemoth.has_spellburst
    assert len([c for c in p1.deck if c.id == ASTEROID]) == 3


def test_bolide_behemoth_bonus_boosts_asteroid_damage():
    # The asteroid_damage_bonus arms +1 damage on Asteroid strikes (2 -> 3).
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.cant_fatigue = True
    p1.give("GDB_434").play()
    assert p1.asteroid_damage_bonus == 1
    # Give the opponent a lone, fat target so the random hit is deterministic.
    target = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    target.max_health = 80
    target.damage = 0
    # Shuffle an Asteroid into deck then draw it -> casts when drawn.
    p1.give(ASTEROID).shuffle_into_deck()
    asteroid = next(c for c in p1.deck if c.id == ASTEROID)
    asteroid.draw()
    game.process_deaths()
    # 2 base + 1 Bolide bonus = 3 damage to the only enemy character available.
    # The enemy hero is also a legal target; beef the minion and assert the
    # total damage dealt across both enemy characters equals 3.
    total = target.damage + (p2.hero.max_health - p2.hero.health)
    assert total == 3


# GDB_443 — Cosmonaut: Battlecry: Discover a spell from your deck. Reduce its
# Cost by (5).
def test_cosmonaut_pulls_deck_spell_to_hand_discounted():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.cant_fatigue = True
    for c in list(p1.hand):
        c.discard()
    # Seed the deck with a single known spell: Fireball (base cost 4).
    p1.give(FIREBALL).shuffle_into_deck()
    assert FIREBALL in [c.id for c in p1.deck]
    p1.give("GDB_443").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # The Fireball is now in hand and no longer in the deck.
    in_hand = [c for c in p1.hand if c.id == FIREBALL]
    assert len(in_hand) == 1
    assert FIREBALL not in [c.id for c in p1.deck]
    # Cost reduced by 5, clamped to 0 (base 4 -> 0).
    assert in_hand[0].cost == 0


# GDB_444 — Planetary Navigator: Battlecry: The next Draenei you play costs (2)
# less, but has Overload: (2).
def test_planetary_navigator_discounts_next_draenei():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.give("GDB_444").play()
    assert p1.next_draenei_discount == 2
    # A Draenei in hand is now (2) cheaper.
    velen = p1.give("GDB_131")  # Velen, Leader of the Exiled (Draenei)
    base = p1.card("GDB_131").cost
    assert velen.cost == base - 2


def test_planetary_navigator_next_draenei_overloads_two():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.give("GDB_444").play()
    assert p1.overloaded == 0
    assert len(p1.next_draenei_hooks) == 1
    velen = p1.give("GDB_131")
    velen.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Playing the next Draenei overloads for (2)...
    assert p1.overloaded == 2
    # ...and the pending hook is consumed (one-shot).
    assert p1.next_draenei_hooks == []


# GDB_445 — Meteor Storm: Deal $5 damage to all minions. Shuffle 5 Asteroids
# into your deck.
def test_meteor_storm_damages_all_minions_and_shuffles_five():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.cant_fatigue = True
    friendly = p1.summon("CS2_182")  # Yeti 4/5
    enemy = p2.summon("CS2_182")     # Yeti 4/5
    p1.give("GDB_445").play()
    # 5 damage to every minion: both 5-health Yetis die.
    game.process_deaths()
    assert friendly.dead
    assert enemy.dead
    # Hero faces are untouched.
    assert p2.hero.health == p2.hero.max_health
    # 5 Asteroids shuffled into the caster's deck.
    assert len([c for c in p1.deck if c.id == ASTEROID]) == 5


# GDB_447 — Farseer Nobundo: Deathrattle: Open the Galaxy's Lens. It absorbs
# the power of the next spell you cast.
def test_farseer_nobundo_deathrattle_opens_galaxys_lens():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    nobundo = p1.summon("GDB_447")
    assert p1.location is None
    nobundo.destroy()
    game.process_deaths()
    # The Galaxy's Lens Location is now in the player's location slot.
    lens = p1.location
    assert lens is not None
    assert lens.id == "GDB_136t"
    assert lens.type == CardType.LOCATION
    assert lens.has_spellburst


def test_galaxys_lens_absorbs_and_recasts_spell():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    lens = p1.summon("GDB_136t")
    p2.hero.set_current_health(30)
    # Cast Fireball (6 to enemy hero) -> the Lens absorbs it.
    p1.give("CS2_029").play(target=p2.hero)
    assert p2.hero.health == 24
    assert lens._absorbed_spell == "CS2_029"
    # Using the Location re-casts the absorbed Fireball (auto-targeted).
    lens.use()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert p2.hero.health == 18


# GDB_448 — Murmur: Your Battlecry minions cost (1), but immediately die after
# being played.
def test_murmur_battlecry_minions_cost_one_and_die_after_play():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    murmur = p1.summon("GDB_448")
    assert (murmur.atk, murmur.max_health) == (6, 6)
    assert Race.ELEMENTAL in murmur.races
    game.refresh_auras()
    # Seed the deck so Novice Engineer's Battlecry (draw a card) has a target.
    seed = p1.give(WISP)
    seed.zone = Zone.DECK
    eng = p1.give("EX1_015")  # Novice Engineer (Battlecry: Draw a card), base 2
    assert eng.cost == 1  # aura sets Battlecry minions' cost to 1
    eng.play()
    # Battlecry resolved (the seeded card was drawn) ...
    assert seed in p1.hand
    # ... and then the minion died from Murmur's aura.
    assert eng.zone == Zone.GRAVEYARD


def test_murmur_aura_only_affects_battlecry_minions_cost():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.summon("GDB_448")
    game.refresh_auras()
    # Wisp has no Battlecry -> cost unchanged (still 0).
    wisp = p1.give(WISP)
    assert wisp.cost == 0
    # Novice Engineer (Battlecry) -> cost set to 1.
    eng = p1.give("EX1_015")
    assert eng.cost == 1
    eng.play()
    # Non-Battlecry Wisp survives play (the die-after rule is Battlecry-only).
    wisp.play()
    assert wisp.zone == Zone.PLAY


# GDB_451 — Triangulate: Discover a different spell from your deck. Shuffle 3
# copies of it into your deck.
def test_triangulate_pulls_spell_and_shuffles_three_copies():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.cant_fatigue = True
    for c in list(p1.hand):
        c.discard()
    # Seed deck with exactly one spell: Fireball.
    p1.give(FIREBALL).shuffle_into_deck()
    assert len([c for c in p1.deck if c.id == FIREBALL]) == 1
    p1.give("GDB_451").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # The chosen Fireball moved to hand...
    assert len([c for c in p1.hand if c.id == FIREBALL]) == 1
    # ...and exactly 3 fresh copies were shuffled back into the deck.
    assert len([c for c in p1.deck if c.id == FIREBALL]) == 3


# GDB_479 — Nebula: Discover two 8-Cost minions to summon with Taunt and
# Elusive.
def test_nebula_summons_two_eight_cost_taunt_elusive_minions():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    pre = len(p1.field)
    p1.give("GDB_479").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    summoned = p1.field[pre:]
    assert len(summoned) == 2
    for m in summoned:
        assert m.data.cost == 8
        assert m.taunt
        # Elusive = can't be targeted by spells or hero powers.
        assert m.tags.get(GameTag.CANT_BE_TARGETED_BY_SPELLS)
        assert m.cant_be_targeted_by_hero_powers


# GDB_864 — First Contact: Summon two random 1-Cost minions. Overload: (1).
def test_first_contact_summons_two_one_cost_minions():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    pre = len(p1.field)
    p1.give("GDB_864").play()
    summoned = p1.field[pre:]
    assert len(summoned) == 2
    for m in summoned:
        assert m.data.cost == 1


def test_first_contact_overloads_one():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    assert p1.overloaded == 0
    p1.give("GDB_864").play()
    # Overload: (1) from the card data.
    assert p1.overloaded == 1


# GDB_901 — Ultraviolet Breaker: Battlecry: Deal 3 damage to an enemy minion.
# Shuffle 3 Asteroids into your deck.
def test_ultraviolet_breaker_hits_enemy_minion_and_shuffles_three():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.cant_fatigue = True
    target = p2.summon("CS2_182")  # Yeti 4/5
    p1.give("GDB_901").play(target=target)
    # Exactly 3 damage to the enemy minion (4/5 -> 5 health, 3 damage taken).
    assert target.damage == 3
    # 3 Asteroids shuffled into the caster's deck.
    assert len([c for c in p1.deck if c.id == ASTEROID]) == 3
