"""Firelands mini-set (FIR_) — PALADIN.

Tight unit tests for the three FIR_ Paladin collectibles that fold into the
Into the Emerald Dream package:

  * FIR_914 — Smoldering Strength
  * FIR_941 — Searing Reflection
  * FIR_961 — Ashleaf Pixie
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards


# ---------------------------------------------------------------------------
# FIR_914 — Smoldering Strength: Give a friendly minion +{0}/+{0}.
# (Upgrades each turn, but discards after {1}!)
#
# Smoldering {0}/{1} are server-resolved; the package default is base 1,
# +1 per held turn, discard after 3. We assert that default behaviour.
# ---------------------------------------------------------------------------
def test_smoldering_strength_base_gives_plus_one():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    target = p1.summon("CS2_182")  # 4/5 Chillwind Yeti
    spell = p1.give("FIR_914")
    # Played the turn it entered hand -> level 1 -> +1/+1.
    spell.play(target=target)
    assert (target.atk, target.max_health) == (5, 6)


def test_smoldering_strength_upgrades_each_held_turn():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    target = p1.summon("CS2_182")  # 4/5 Chillwind Yeti
    spell = p1.give("FIR_914")
    # Hold it across one full round so its Smoldering counter ticks once at the
    # start of p1's next turn -> level 2 -> +2/+2.
    game.end_turn()  # p1 -> p2
    game.end_turn()  # p2 -> p1 (OWN_TURN_BEGIN tick: _smolder_turns_held = 1)
    assert spell.zone == Zone.HAND
    spell.play(target=target)
    assert (target.atk, target.max_health) == (6, 7)


def test_smoldering_strength_discards_after_three_turns():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    spell = p1.give("FIR_914")
    # Three of p1's turn-begins tick the Smoldering counter; on the third the
    # card is discarded (held >= SMOLDER_DISCARD_AFTER == 3).
    for _ in range(3):
        game.end_turn()  # p1 -> p2
        game.end_turn()  # p2 -> p1 (tick)
    # Smoldering discards the card out of hand once it has been held for
    # SMOLDER_DISCARD_AFTER turns. Discard() removes it from the game.
    assert spell.zone == Zone.REMOVEDFROMGAME
    assert spell not in p1.hand


# ---------------------------------------------------------------------------
# FIR_941 — Searing Reflection: Draw a minion. Summon an 8/8 copy of it with
# Divine Shield.
# ---------------------------------------------------------------------------
def test_searing_reflection_draws_minion_and_summons_8_8_divine_shield():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Exactly one minion in the deck so the draw + copy source is deterministic.
    minion = p1.give("CS2_172")  # 3/2 Bloodfen Raptor
    minion.zone = Zone.DECK
    spell = p1.give("FIR_941")
    spell.play()
    # The minion is drawn to hand.
    assert minion.zone == Zone.HAND
    # An 8/8 copy with Divine Shield is on the board.
    copies = [m for m in p1.field if m.id == "CS2_172"]
    assert len(copies) == 1
    copy = copies[0]
    assert (copy.atk, copy.max_health) == (8, 8)
    assert copy.divine_shield


def test_searing_reflection_no_minion_in_deck_summons_nothing():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Only a spell in the deck -> nothing to draw/copy.
    s = p1.give("CS2_029")  # Fireball
    s.zone = Zone.DECK
    spell = p1.give("FIR_941")
    spell.play()
    assert s.zone == Zone.DECK
    assert len(p1.field) == 0


# ---------------------------------------------------------------------------
# FIR_961 — Ashleaf Pixie: Battlecry: If you're holding a spell that costs (5)
# or more, gain Divine Shield and Lifesteal.
# ---------------------------------------------------------------------------
def test_ashleaf_pixie_with_expensive_spell_gains_shield_and_lifesteal():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Clear any incidental hand, then hold a confirmed 7-cost spell.
    for c in list(p1.hand):
        c.discard()
    p1.give("FIR_941")  # Searing Reflection, cost 7 (a held spell >= 5)
    pixie = p1.give("FIR_961")
    pixie.play()
    assert pixie.divine_shield
    assert pixie.lifesteal


def test_ashleaf_pixie_without_expensive_spell_is_vanilla():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give("CS2_025")  # Arcane Explosion, cost 2 (< 5)
    pixie = p1.give("FIR_961")
    pixie.play()
    assert not pixie.divine_shield
    assert not pixie.lifesteal


def test_ashleaf_pixie_held_spell_must_be_a_spell_not_a_minion():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # A 7-cost MINION in hand must not satisfy the "holding a spell" clause.
    p1.give("CS2_186")  # War Golem, 7-cost MINION (not a spell)
    pixie = p1.give("FIR_961")
    pixie.play()
    assert not pixie.divine_shield
    assert not pixie.lifesteal
