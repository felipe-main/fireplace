"""Firelands mini-set (FIR_) — DEATHKNIGHT collectible card tests.

One tight test per collectible Death Knight card:
  FIR_900 Cremate, FIR_901 Frostburn Matriarch, FIR_951 Volcoross.
Assertions follow the PRINTED card text.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone, Race

# FIR_900 — Cremate: Discover a minion with a Dark Gift. It costs (2) less.
def test_cremate_discovers_minion_costs_two_less_and_dark_gift():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    spell = p1.give("FIR_900")
    spell.play()
    assert p1.choice is not None
    # Every Discover option is a minion.
    for c in p1.choice.cards:
        assert c.type == CardType.MINION
    chosen = p1.choice.cards[0]
    chosen_id = chosen.id
    base_cost = p1.card(chosen_id).cost
    p1.choice.choose(chosen)
    assert p1.choice is None
    # The gifted minion usually lands in hand, but the "Sweet Dreams" gift
    # relocates it to the top of the deck — locate it wherever it ended up.
    card = [c for c in (list(p1.hand) + list(p1.deck)) if c.id == chosen_id][0]
    # Cremate's own -2 enchant is applied.
    assert "FIR_900e" in [b.id for b in card.buffs]
    # Exactly one real Dark Gift was recorded.
    gifts = getattr(card, "_dark_gifts", [])
    assert len(gifts) == 1
    # Final cost = base - 2 (Cremate), minus another 2 if the gift is the
    # "Short Claws" Dark Gift (EDR_100t2, which also reduces Cost by 2).
    expected = base_cost - 2 - (2 if gifts[0] == "EDR_100t2" else 0)
    assert card.cost == max(expected, 0)


# FIR_901 — Frostburn Matriarch: Battlecry: If you're holding a minion with a
# Dark Gift, summon two 4/4 Dragons with Taunt.
def test_frostburn_matriarch_no_dark_gift_minion_in_hand_no_dragons():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    # A plain held minion with NO Dark Gift.
    p1.give(WISP)
    matriarch = p1.give("FIR_901")
    matriarch.play()
    dragons = [m for m in p1.field if m.id == "FIR_901t"]
    assert len(dragons) == 0


def test_frostburn_matriarch_with_dark_gift_minion_summons_two_taunt_dragons():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    # Give a held minion an explicit Dark Gift marker (what _GiveDarkGift sets).
    gifted = p1.give(WISP)
    gifted._dark_gifts = ["EDR_100t3"]  # gift id marker (Bundled Up)
    matriarch = p1.give("FIR_901")
    matriarch.play()
    dragons = [m for m in p1.field if m.id == "FIR_901t"]
    assert len(dragons) == 2
    for d in dragons:
        assert (d.atk, d.max_health) == (4, 4)
        assert d.taunt
        assert Race.DRAGON in d.races


# FIR_951 — Volcoross: Rush, Taunt. Battlecry: Choose to spend 10, 20, or 30
# Corpses to gain that many stats.
def test_volcoross_has_rush_and_taunt():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 0
    volc = p1.summon("FIR_951")
    assert volc.rush
    assert volc.taunt
    assert (volc.atk, volc.max_health) == (5, 5)


def test_volcoross_no_corpses_no_choice_no_buff():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 0
    volc = p1.give("FIR_951")
    volc.play()
    # Cannot afford even 10 -> no choice presented, no stats gained.
    assert p1.choice is None
    assert (volc.atk, volc.max_health) == (5, 5)
    assert volc.buffs == []


def test_volcoross_spends_ten_corpses_for_ten_stats():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 10  # affords only the +10 option
    volc = p1.give("FIR_951")
    volc.play()
    assert p1.choice is not None
    # Only the affordable (10) option is offered.
    assert len(p1.choice.cards) == 1
    p1.choice.choose(p1.choice.cards[0])
    assert p1.choice is None
    assert p1.corpses == 0
    assert (volc.atk, volc.max_health) == (5 + 10, 5 + 10)


def test_volcoross_choose_thirty_of_three_options():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 30  # affords all three options (10/20/30)
    volc = p1.give("FIR_951")
    volc.play()
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    # Pick the 30-Corpse option.
    thirty = [c for c in p1.choice.cards if c._volcoross_amount == 30][0]
    p1.choice.choose(thirty)
    assert p1.choice is None
    assert p1.corpses == 0
    assert (volc.atk, volc.max_health) == (5 + 30, 5 + 30)
    # The chosen marker did not leak into hand.
    assert all(c.id != "FIR_951e" for c in p1.hand)
