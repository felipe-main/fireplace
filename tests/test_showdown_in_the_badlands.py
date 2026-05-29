"""Showdown in the Badlands (Patch 28.0) tests — WILD_WEST CardSet.

145 collectible cards across 11 classes + neutrals. Two novel keywords:

- Excavate: dig a treasure, escalating tier per dig (1 Common -> 2 Rare ->
  3 Epic -> 4 class Legendary for the five Excavate classes that shipped in
  28.0: DK, Mage, Rogue, Warlock, Warrior). After the deepest tier the cycle
  restarts at tier 1.
- Quickdraw: a bonus effect that fires only when the card is played the same
  turn it entered hand (drawn or generated).

The first block exercises the two engine primitives directly; the rest are
one-test-per-card (or per-cluster) with tight assertions.
"""

import pytest

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone

from utils import *

from fireplace.actions import (
    Excavate,
    EXCAVATE_TIERS,
    EXCAVATE_LEGENDARY,
)


# ---------------------------------------------------------------------------
# Engine primitive: Excavate
# ---------------------------------------------------------------------------

def _excavate(game, player):
    game.queue_actions(player.hero, [Excavate(player)])


def test_excavate_tier_escalation_excavate_class():
    """An Excavate class (Mage) digs Common -> Rare -> Epic -> Legendary,
    then the cycle restarts at tier 1."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    assert p.excavates_this_game == 0

    _excavate(game, p)
    assert p.excavates_this_game == 1
    assert p.hand[-1].id in EXCAVATE_TIERS[1]

    _excavate(game, p)
    assert p.excavates_this_game == 2
    assert p.hand[-1].id in EXCAVATE_TIERS[2]

    _excavate(game, p)
    assert p.excavates_this_game == 3
    assert p.hand[-1].id in EXCAVATE_TIERS[3]

    # 4th dig: Mage's class Legendary (deterministic).
    _excavate(game, p)
    assert p.excavates_this_game == 4
    assert p.hand[-1].id == EXCAVATE_LEGENDARY[CardClass.MAGE]

    # 5th dig: cycle restarts at tier 1.
    _excavate(game, p)
    assert p.excavates_this_game == 5
    assert p.hand[-1].id in EXCAVATE_TIERS[1]


def test_excavate_non_excavate_class_caps_at_tier_three():
    """A non-Excavate class (Druid) never reaches tier 4 — it cycles
    Common -> Rare -> Epic -> Common."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    assert CardClass.DRUID not in EXCAVATE_LEGENDARY

    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[1]
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[2]
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[3]
    # 4th dig wraps back to tier 1, NOT a Legendary.
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[1]


# ---------------------------------------------------------------------------
# Engine primitive: Quickdraw
# ---------------------------------------------------------------------------

def test_quickdraw_active_when_played_same_turn():
    """A card generated/drawn this turn is Quickdraw-active while in hand,
    and the flag snapshots True the moment it is played."""
    game = prepare_game()
    card = game.player1.give(WISP)
    # Entered hand this turn -> active.
    assert card.quickdraw_active is True
    card.play()
    assert card.quickdraw_played is True


def test_quickdraw_inactive_after_turn_cycle():
    """A card that has sat in hand since a previous turn is NOT Quickdraw
    -active, and the play snapshot is False."""
    game = prepare_game()
    card = game.player1.give(WISP)
    # Simulate the card having entered hand on an earlier turn.
    card._turn_entered_hand = game.turn - 1
    assert card.quickdraw_active is False
    card.play()
    assert card.quickdraw_played is False
