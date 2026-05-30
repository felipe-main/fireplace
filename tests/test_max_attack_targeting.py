"""
Regression guard for REQ_TARGET_MAX_ATTACK targeting.

Most MAX_ATTACK cards use a FIXED data cap ("an enemy minion that has 2 or less
Attack"). A few instead read "Attack <= THIS minion's" and must track the
source's LIVE Attack (Perils in Paradise: Undercooked Calamari). The engine
distinguishes the two via fireplace.targeting.MAX_ATTACK_TRACKS_SOURCE.

These tests lock both behaviors so the fixed-cap cards can never be widened by a
source buff (the bug an over-broad fix would introduce: a 4-Attack Cabal Shadow
Priest stealing a 3- or 4-Attack minion).
"""
from utils import *


def test_cabal_shadow_priest_cap_is_fixed_two_not_source_attack():
    # EX1_091 Cabal Shadow Priest is a 4-Attack minion whose Battlecry steals an
    # enemy minion with "2 or less Attack" -- a FIXED 2, independent of its own 4.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    cabal = game.player1.give("EX1_091")
    assert cabal.atk == 4

    two = game.player2.summon("CS2_182")  # Chillwind Yeti, re-statted to 2 Attack
    two.atk = 2
    three = game.player2.summon("CS2_182")
    three.atk = 3

    # The 2-Attack minion is a legal target; the 3-Attack one is NOT (cap is 2,
    # not the caster's 4).
    assert two in cabal.play_targets
    assert three not in cabal.play_targets


def test_book_wyrm_cap_is_fixed_three_even_when_buffed():
    # KAR_033 Book Wyrm: "Destroy an enemy minion with 3 or less Attack." Fixed 3
    # regardless of buffs to the Book Wyrm itself.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    wyrm = game.player1.give("KAR_033")
    wyrm.atk = 9  # buff in hand; cap must stay 3

    three = game.player2.summon("CS2_182")
    three.atk = 3
    four = game.player2.summon("CS2_182")
    four.atk = 4

    assert three in wyrm.play_targets
    assert four not in wyrm.play_targets


def test_undercooked_calamari_cap_tracks_live_attack():
    # VAC_341 Undercooked Calamari (base 3 Attack): "Destroy an enemy minion with
    # Attack <= this minion's." The cap is the source's LIVE Attack.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    calamari = game.player1.give("VAC_341")

    four = game.player2.summon("CS2_182")
    four.atk = 4

    # Unbuffed (3 Attack): a 4-Attack minion is out of range.
    assert four not in calamari.play_targets

    # Buffed to 7 Attack in hand: the same 4-Attack minion becomes a legal
    # target, and the Battlecry destroys it.
    calamari.atk = 7
    assert four in calamari.play_targets
    four.max_health = 5
    four.damage = 0
    calamari.play(target=four)
    game.process_deaths()
    assert four.dead
