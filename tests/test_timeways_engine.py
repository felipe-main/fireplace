"""Across the Timeways — engine primitive: Rewind.

Rewind offers, after the card's play effect resolves, a choice between
"Keep Timeline" (no-op) and "Rewind Timeline" (re-run the effect once).
Exercised here with Conflux Crasher (TIME_004, "Deal 7 damage to a random
enemy") against an opponent whose only enemy character is the hero, so the
7 damage lands deterministically.
"""
from utils import *


def _play_conflux(game):
    """Play Conflux Crasher; return (card, choice)."""
    card = game.player1.give("TIME_004")
    card.play()
    assert game.player1.choice is not None
    return card, game.player1.choice


def test_rewind_offers_two_timeline_tokens():
    game = prepare_game()
    _, choice = _play_conflux(game)
    ids = sorted(c.id for c in choice.cards)
    assert ids == ["TIME_000ta", "TIME_000tb"]
    # The first effect already resolved: hero took 7.
    assert game.player2.hero.health == 23


def test_rewind_keep_timeline_locks_outcome():
    game = prepare_game()
    _, choice = _play_conflux(game)
    keep = next(c for c in choice.cards if c.id == "TIME_000ta")
    choice.choose(keep)
    assert game.player1.choice is None
    # Kept: a single resolution, 7 damage total.
    assert game.player2.hero.health == 23


def test_rewind_timeline_reruns_effect_once():
    game = prepare_game()
    _, choice = _play_conflux(game)
    rewind = next(c for c in choice.cards if c.id == "TIME_000tb")
    choice.choose(rewind)
    # Rewound exactly once: 7 + 7 = 14 damage, no further choice queued.
    assert game.player1.choice is None
    assert game.player2.hero.health == 16
