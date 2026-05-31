"""Firelands mini-set (Into the Emerald Dream) — MAGE collectible tests.

Covers the three FIR_ mage cards: FIR_910 Scorching Winds, FIR_911 Smoldering
Grove, FIR_913 Inferno Herald. Assertions pin the PRINTED behaviour.
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone

import fireplace.cards as _cards


FIREBALL = "CS2_029"        # 4-cost Fire spell (deal 6)
ARCANE_MISSILES = "EX1_277"  # 1-cost Arcane spell (NOT Fire)
YETI = "CS2_182"            # 4/4/5 vanilla body (deterministic target)


def _clear_hand(p):
    for c in list(p.hand):
        c.discard()


# FIR_910 — Scorching Winds — Deal 3 damage. Discard a random Fire spell to
# deal 3 more.
def test_scorching_winds_no_fire_spell_deals_three():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    tank = p2.summon(YETI)
    tank.max_health = 80
    tank.damage = 0
    p1.give("FIR_910").play(target=tank)
    # No Fire spell to discard: only the base 3.
    assert tank.damage == 3


def test_scorching_winds_discards_fire_spell_for_six():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    # Exactly one Fire spell in hand -> deterministic discard.
    fireball = p1.give(FIREBALL)
    tank = p2.summon(YETI)
    tank.max_health = 80
    tank.damage = 0
    p1.give("FIR_910").play(target=tank)
    # Base 3 + 3 more after discarding the Fire spell.
    assert tank.damage == 6
    # Discarded cards leave the hand to REMOVEDFROMGAME.
    assert fireball.zone == Zone.REMOVEDFROMGAME
    assert fireball not in p1.hand


def test_scorching_winds_ignores_non_fire_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    # A non-Fire spell (Arcane Missiles is Arcane) must NOT be discarded.
    arcane = p1.give(ARCANE_MISSILES)
    tank = p2.summon(YETI)
    tank.max_health = 80
    tank.damage = 0
    p1.give("FIR_910").play(target=tank)
    assert tank.damage == 3
    assert arcane.zone == Zone.HAND
    assert arcane in p1.hand


# FIR_911 — Smoldering Grove — Draw {0} card(s). (Upgrades each turn, but
# discards after {1}!)  Approximation: base 1, +1 per turn held, discard
# after 3 of your turns.
def test_smoldering_grove_draws_one_when_played_immediately():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    # Stock the deck so the draw is real.
    for _ in range(5):
        c = p1.card(YETI)
        c.zone = Zone.DECK
    grove = p1.give("FIR_911")
    pre_hand = len(p1.hand)
    grove.play()
    # Base level 1 -> draw exactly 1; the spell itself leaves hand.
    assert len(p1.hand) == pre_hand - 1 + 1


def test_smoldering_grove_upgrades_each_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    for _ in range(10):
        c = p1.card(YETI)
        c.zone = Zone.DECK
    grove = p1.give("FIR_911")
    # Survive two of the controller's turn-begins -> level 1 + 2 = 3.
    game.end_turn()  # p1 -> p2
    game.end_turn()  # p2 -> p1 : tick 1
    game.end_turn()  # p1 -> p2
    game.end_turn()  # p2 -> p1 : tick 2
    assert grove.zone == Zone.HAND  # held 2 < 3 turns, not discarded
    _clear_hand_keep = [c for c in p1.hand if c is not grove]
    for c in _clear_hand_keep:
        c.discard()
    pre_hand = len(p1.hand)
    grove.play()
    # Level = base 1 + 2 ticks = 3 cards drawn; -1 for the spell leaving hand.
    assert len(p1.hand) == pre_hand - 1 + 3


def test_smoldering_grove_discards_after_three_turns():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    grove = p1.give("FIR_911")
    # Three of the controller's turn-begins -> held >= 3 -> discarded.
    game.end_turn()  # p1 -> p2
    game.end_turn()  # p2 -> p1 : tick 1
    game.end_turn()
    game.end_turn()  # tick 2
    game.end_turn()
    game.end_turn()  # tick 3 -> discard
    assert grove.zone == Zone.REMOVEDFROMGAME
    assert grove not in p1.hand


# FIR_913 — Inferno Herald — After you cast a Fire spell, get a random
# Elemental and reduce its Cost by 3.
def test_inferno_herald_gives_discounted_elemental_after_fire_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("FIR_913")
    _clear_hand(p1)
    p2.hero.set_current_health(30)
    # Cast a Fire spell (Fireball) at the enemy hero.
    p1.give(FIREBALL).play(target=p2.hero)
    # Exactly one Elemental was added to hand (the gifted card).
    assert len(p1.hand) == 1
    gained = p1.hand[0]
    assert Race.ELEMENTAL in gained.races
    # Its printed cost was reduced by 3 (clamped at 0) via FIR_913e.
    base_cost = _cards.db[gained.id].cost
    assert gained.cost == max(0, base_cost - 3)
    assert "FIR_913e" in [b.id for b in gained.buffs]


def test_inferno_herald_ignores_non_fire_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("FIR_913")
    _clear_hand(p1)
    # Arcane Missiles is NOT a Fire spell -> no Elemental gained.
    p1.give(ARCANE_MISSILES).play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 0
