"""The Lost City of Un'Goro — engine primitive tests (Kindred)."""

from utils import *

from hearthstone.enums import CardClass, Race, SpellSchool

from fireplace.dsl.evaluator import kindred_active

BEAST = "CS2_172"   # Bloodfen Raptor (Beast)
MURLOC = "CS2_168"  # Murloc Raider (Murloc)
FIRE_SPELL = "CS2_029"  # Fireball (Fire)


def test_kindred_inactive_same_turn():
    # Kindred reads the PREVIOUS turn, so a matching play this turn does not
    # activate a Kindred card played the same turn.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give(BEAST).play()
    beast2 = p1.give(BEAST)
    assert kindred_active(beast2) is False


def test_kindred_active_after_matching_type_last_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give(BEAST).play()
    game.end_turn(); game.end_turn()  # back to p1's next turn
    assert Race.BEAST in p1.races_played_last_turn
    assert kindred_active(p1.give(BEAST)) is True
    # A non-matching type does not activate.
    assert kindred_active(p1.give(MURLOC)) is False


def test_kindred_active_by_spell_school():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    fb = p1.give(FIRE_SPELL)
    assert fb.spell_school == SpellSchool.FIRE
    # need a target to cast; hit the enemy hero
    fb.play(target=p1.opponent.hero)
    game.end_turn(); game.end_turn()
    assert SpellSchool.FIRE in p1.schools_played_last_turn


def test_kindred_resets_each_turn():
    # After a turn where nothing matching is played, last-turn set is empty.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give(BEAST).play()
    game.end_turn(); game.end_turn()      # turn N: beast is "last turn"
    assert Race.BEAST in p1.races_played_last_turn
    game.end_turn(); game.end_turn()      # turn N+1: nothing played in between
    assert Race.BEAST not in p1.races_played_last_turn
    assert kindred_active(p1.give(BEAST)) is False
