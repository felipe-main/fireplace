"""Into the Emerald Dream — engine primitive tests.

Covers the IMBUE keyword:
  - "Imbue your Hero Power" replaces the controller's Hero Power with their
    class's Imbued Hero Power token and bumps player.imbues_this_game.
  - subsequent imbues keep counting and scale the Imbued Hero Power's level.
  - the counter is readable by payoff cards.
  - classes without an Imbued Hero Power count but keep their Hero Power.
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, Zone

from fireplace.actions import Imbue, imbued_hero_power_for, IMBUED_HERO_POWERS


# class -> (imbued HP id, base hero power id)
IMBUE_CLASSES = {
    CardClass.PALADIN: "EDR_445p",
    CardClass.SHAMAN: "EDR_448p",
    CardClass.PRIEST: "EDR_449p",
    CardClass.DRUID: "EDR_847p",
    CardClass.HUNTER: "EDR_850p",
    CardClass.MAGE: "EDR_851p",
}

NO_IMBUE_CLASSES = [
    CardClass.DEATHKNIGHT,
    CardClass.DEMONHUNTER,
    CardClass.ROGUE,
    CardClass.WARLOCK,
    CardClass.WARRIOR,
]


def _imbue(player):
    player.game.queue_actions(player.hero, [Imbue(player)])


def test_imbue_replaces_hero_power_and_counts():
    """First imbue installs the class token and bumps the counter to 1."""
    for card_class, hp_id in IMBUE_CLASSES.items():
        game = prepare_game(card_class, CardClass.MAGE)
        p1 = game.player1
        assert p1.imbues_this_game == 0
        original_hp = p1.hero_power
        assert original_hp.id != hp_id

        _imbue(p1)

        assert p1.imbues_this_game == 1
        assert p1.hero_power.id == hp_id
        assert p1.hero_power.imbue_level == 1
        # The old hero power is gone from play.
        assert original_hp.zone != Zone.PLAY


def test_imbue_scales_on_repeat():
    """A second imbue keeps the same token but bumps level + counter."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1

    _imbue(p1)
    assert p1.imbues_this_game == 1
    assert p1.hero_power.id == "EDR_851p"
    assert p1.hero_power.imbue_level == 1

    first_token = p1.hero_power
    _imbue(p1)
    assert p1.imbues_this_game == 2
    assert p1.hero_power.id == "EDR_851p"
    assert p1.hero_power.imbue_level == 2
    # Same class -> reuse the installed token (no needless re-summon).
    assert p1.hero_power is first_token

    _imbue(p1)
    assert p1.imbues_this_game == 3
    assert p1.hero_power.imbue_level == 3


def test_imbue_counter_readable_by_payoff():
    """imbues_this_game is a plain per-game int payoff cards can gate on."""
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p1 = game.player1
    assert p1.imbues_this_game == 0
    _imbue(p1)
    _imbue(p1)
    # e.g. EDR_860 "if you've Imbued twice", EDR_888 "Imbued 4 times".
    assert p1.imbues_this_game == 2
    assert (p1.imbues_this_game >= 2) is True
    assert (p1.imbues_this_game >= 4) is False


def test_imbue_no_token_class_counts_only():
    """Classes without an Imbued HP still count; HP is left unchanged."""
    for card_class in NO_IMBUE_CLASSES:
        game = prepare_game(card_class, CardClass.MAGE)
        p1 = game.player1
        original_hp = p1.hero_power
        assert imbued_hero_power_for(p1) is None

        _imbue(p1)

        assert p1.imbues_this_game == 1
        # Hero Power untouched.
        assert p1.hero_power is original_hp


def test_imbue_counter_never_resets_across_turns():
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p1 = game.player1
    _imbue(p1)
    assert p1.imbues_this_game == 1
    game.end_turn()
    game.end_turn()
    assert p1.imbues_this_game == 1


def test_imbued_golem_summons_scaling_plant():
    """Druid's Blessing of the Golem summons a 2N/2N Plant Golem."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p1 = game.player1
    _imbue(p1)  # level 1 -> 2/2
    p1.hero_power.activate(target=None, choose=None)
    golems = [m for m in p1.field if m.id == "EDR_847pt2"]
    assert len(golems) == 1
    assert golems[0].atk == 2
    assert golems[0].max_health == 2


def test_imbued_wisp_summons_and_damages():
    """Mage's Blessing of the Wisp summons N+1 Wisps and deals N+1 damage."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero.damage = 0
    _imbue(p1)  # level 1 -> 2 wisps, 2 damage
    pre_hp = p2.hero.health
    p1.hero_power.activate(target=None, choose=None)
    wisps = [m for m in p1.field if m.id == "EDR_851t"]
    assert len(wisps) == 2
    # 2 damage split among enemies; p2 has only its hero (board empty).
    total_enemy_damage = (pre_hp - p2.hero.health)
    assert total_enemy_damage == 2


def test_imbued_dragon_shuffles_two_portals():
    """Paladin's Blessing of the Dragon shuffles 2 Emerald Portals."""
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p1 = game.player1
    _imbue(p1)
    pre_deck = len(p1.deck)
    p1.hero_power.activate(target=None, choose=None)
    portals = [c for c in p1.deck if c.id == "EDR_445pt3"]
    assert len(portals) == 2
    assert len(p1.deck) == pre_deck + 2
