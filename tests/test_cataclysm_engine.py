"""Cataclysm — engine primitives: Herald and Shatter."""
from utils import *

from hearthstone.enums import Zone

from fireplace.actions import Herald


def test_herald_bumps_per_game_counter():
    game = prepare_game()
    p1 = game.player1
    assert p1.heralds_this_game == 0
    game.queue_actions(p1.hero, [Herald(p1)])
    assert p1.heralds_this_game == 1
    game.queue_actions(p1.hero, [Herald(p1)])
    assert p1.heralds_this_game == 2


def test_shatter_card_splits_into_two_halves_on_draw():
    game = prepare_game()
    p1 = game.player1
    assert p1.shatters_this_game == 0
    # Put a Shatter spell (Arcane Flow) on top of the deck, then draw it.
    card = p1.give("CATA_489")  # Arcane Flow — Shatter
    card.zone = Zone.DECK
    p1.draw()
    # The full card shattered into its two "Shattered" halves.
    assert p1.shatters_this_game == 1
    ids = [c.id for c in p1.hand]
    assert "CATA_489t" in ids
    assert "CATA_489t2" in ids
    assert "CATA_489" not in ids
