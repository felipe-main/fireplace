"""Delve into Deepholm (Patch 28.4) tests — WILD_WEST mini-set (DEEP_ ids).

38 collectible cards. No new keywords: the mini-set reuses Excavate, Quickdraw,
Forge, Finale, Choose One, Discover, Magnetic and Secret (all already in the
engine). The only engine extension is two new tier-4 Excavate Legendaries:

- Paladin -> DEEP_999t4 "The Azerite Dragon"
- Shaman  -> DEEP_999t5 "The Azerite Murloc"

plus three neutral treasures added to the shared Excavate pools
(DEEP_999t1 Heartblossom / DEEP_999t2 Deepholm Geode / DEEP_999t3 World Pillar
Fragment, rarity Common/Rare/Epic -> tiers 1/2/3).

The first block exercises that engine extension directly; the rest are
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
# Engine extension: Paladin + Shaman Excavate Legendaries
# ---------------------------------------------------------------------------

def _excavate(game, player):
    game.queue_actions(player.hero, [Excavate(player)])


def test_excavate_paladin_digs_to_azerite_dragon_on_tier_four():
    """Paladin is now an Excavate class: dig Common -> Rare -> Epic ->
    DEEP_999t4 (The Azerite Dragon), then the cycle restarts at tier 1."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p = game.player1
    assert EXCAVATE_LEGENDARY[CardClass.PALADIN] == "DEEP_999t4"

    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[1]
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[2]
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[3]
    _excavate(game, p)
    assert p.excavates_this_game == 4
    assert p.hand[-1].id == "DEEP_999t4"
    # Cycle restarts at tier 1.
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[1]


def test_excavate_shaman_digs_to_azerite_murloc_on_tier_four():
    """Shaman is now an Excavate class: tier-4 dig yields DEEP_999t5
    (The Azerite Murloc)."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.player1
    assert EXCAVATE_LEGENDARY[CardClass.SHAMAN] == "DEEP_999t5"
    for _ in range(3):
        _excavate(game, p)
    _excavate(game, p)
    assert p.excavates_this_game == 4
    assert p.hand[-1].id == "DEEP_999t5"


def test_excavate_new_neutral_treasures_in_shared_pools():
    """The three Deepholm neutral treasures live in the shared tier pools."""
    assert "DEEP_999t1" in EXCAVATE_TIERS[1]
    assert "DEEP_999t2" in EXCAVATE_TIERS[2]
    assert "DEEP_999t3" in EXCAVATE_TIERS[3]
