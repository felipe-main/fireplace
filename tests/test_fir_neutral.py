"""Emerald Dream mini-set (Firelands, FIR_ prefix) — NEUTRAL collectibles.

Tight unit tests asserting the PRINTED behaviour of every collectible
NEUTRAL FIR_ card. One test per card; assertions are exact wherever the
setup can be constrained.
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, SpellSchool, Zone


# FIR_921 — Petal Picker: Battlecry: If you've Imbued your Hero Power twice,
# draw 2 cards.
def test_petal_picker_not_imbued_twice():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    p1.hand[:] = []
    # Stock the deck so a draw WOULD have something to pull.
    for _ in range(3):
        c = p1.give("CS2_029")  # Fireball
        c.zone = Zone.DECK
    p1.imbues_this_game = 1
    pre_deck = len(p1.deck)
    picker = p1.give("FIR_921")
    picker.play()
    # Only imbued once -> no draw.
    assert len(p1.deck) == pre_deck


def test_petal_picker_imbued_twice():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    p1.hand[:] = []
    for _ in range(3):
        c = p1.give("CS2_029")
        c.zone = Zone.DECK
    p1.imbues_this_game = 2
    pre_deck = len(p1.deck)
    picker = p1.give("FIR_921")
    picker.play()
    # Imbued twice -> draw exactly 2.
    assert len(p1.deck) == pre_deck - 2
    assert sum(1 for c in p1.hand if c.id == "CS2_029") == 2


# FIR_929 — Living Flame: Deathrattle: Draw a Fire spell.
def test_living_flame_draws_fire_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.deck[:] = []
    p1.hand[:] = []
    # Deck has one Fire spell (Fireball) and one non-Fire spell (Moonfire,
    # Arcane). Only the Fire spell is eligible.
    fire = p1.give("CS2_029")   # Fireball — Fire
    fire.zone = Zone.DECK
    arcane = p1.give("CS2_008")  # Moonfire — Arcane
    arcane.zone = Zone.DECK
    flame = p1.summon("FIR_929")
    flame.destroy()
    game.process_deaths()
    assert fire.zone == Zone.HAND
    assert arcane.zone == Zone.DECK


# FIR_940 — Zaqali Flamemancer: Battlecry: If every card in your hand is of a
# different Cost, reduce their Costs by (2).
def test_zaqali_all_distinct_costs():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    # Three hand cards with distinct costs: Wisp (0), Moonfire (0?) — pick
    # clearly distinct-cost cards. Fireball=4, Pyroblast=10, Frostbolt=2.
    a = p1.give("CS2_029")  # Fireball, cost 4
    b = p1.give("EX1_279")  # Pyroblast, cost 10
    c = p1.give("CS2_024")  # Frostbolt, cost 2
    zaqali = p1.give("FIR_940")
    zaqali.play()
    # All distinct -> every remaining hand card costs (2) less.
    assert a.cost == 2
    assert b.cost == 8
    assert c.cost == 0


def test_zaqali_duplicate_costs_no_reduction():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.hand[:] = []
    # Two cards share cost 4 -> condition fails, no reduction.
    a = p1.give("CS2_029")  # Fireball, cost 4
    b = p1.give("CS2_029")  # second Fireball, cost 4 (duplicate cost)
    c = p1.give("EX1_279")  # Pyroblast, cost 10
    zaqali = p1.give("FIR_940")
    zaqali.play()
    assert a.cost == 4
    assert b.cost == 4
    assert c.cost == 10


# FIR_958 — Tindral Sageswift: Deathrattle: Deal 1 damage to all enemies.
# If it's your opponent's turn, deal 4 damage instead.
def test_tindral_your_turn_one_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    # Enemy minion + enemy hero soak the hit.
    enemy = p2.summon("CS2_182")  # 4/5 Chillwind Yeti
    enemy.max_health = 80
    enemy.damage = 0
    tindral = p1.summon("FIR_958")
    tindral.destroy()
    game.process_deaths()
    # It's p1's turn -> 1 damage to all enemies.
    assert enemy.damage == 1
    assert p2.hero.damage == 1


def test_tindral_opponent_turn_four_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Make it p2's (opponent's) turn from p1's perspective.
    if game.current_player is p1:
        game.end_turn()
    enemy = p2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    tindral = p1.summon("FIR_958")
    tindral.destroy()
    game.process_deaths()
    # Opponent's turn -> 4 damage to all enemies.
    assert enemy.damage == 4
    assert p2.hero.damage == 4


# FIR_959 — Fyrakk the Blazing: Immune to Fire spells.
# Battlecry: Cast 20 Mana worth of Fire spells at random enemies.
def test_fyrakk_immune_to_fire_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    fyrakk = p1.summon("FIR_959")
    fyrakk.max_health = 80
    fyrakk.damage = 0
    # A non-spell source (hero) still damages Fyrakk normally.
    game.cheat_action(p2.hero, [Hit(fyrakk, 6)])
    assert fyrakk.damage == 6
    fyrakk.damage = 0
    # Damage from a Fire-school SPELL source is nullified.
    fireball = p2.give("CS2_029")  # Fireball — Fire school
    game.cheat_action(fireball, [Hit(fyrakk, 6)])
    assert fyrakk.damage == 0


def test_fyrakk_not_immune_to_nonfire_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    fyrakk = p1.summon("FIR_959")
    fyrakk.max_health = 80
    fyrakk.damage = 0
    # Frostbolt (Frost school spell) deals its damage — immunity is Fire-only.
    frostbolt = p2.give("CS2_024")  # Frostbolt — Frost school
    game.cheat_action(frostbolt, [Hit(fyrakk, 3)])
    assert fyrakk.damage == 3


def test_fyrakk_casts_fire_spells_at_enemies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    game.random.seed(12345)
    # Give the enemy hero a huge health pool so every random Fire spell that
    # lands on it is absorbed; this keeps the cast loop deterministic-shape.
    p2.hero.max_health = 500
    p2.hero._max_health = 500
    pre_cast = len(p1.spells_cast_this_game)
    fyrakk = p1.give("FIR_959")
    fyrakk.play()
    cast = p1.spells_cast_this_game[pre_cast:]
    # At least one Fire spell was cast.
    assert len(cast) >= 1
    # EVERY cast was a costed Fire-school spell.
    assert all(c.spell_school == SpellSchool.FIRE for c in cast)
    assert all((c.cost or 0) > 0 for c in cast)
    # The candidate filter only ever picks a spell whose Cost fits the
    # remaining budget, and 1-Cost Fire spells always exist, so the budget
    # drains to exactly 0 -> total Mana spent is exactly 20.
    total = sum(c.cost for c in cast)
    assert total == 20
