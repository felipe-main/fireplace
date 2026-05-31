"""Emerald Dream mini-set (Firelands, FIR_) — DRUID collectible cards.

Tight, one-per-card tests asserting PRINTED behaviour. Choices / random rolls
are constrained (clear hand, beef HP, control which cards exist) so == holds.
"""

import pytest

# --- Test isolation shim ------------------------------------------------------
# The `emerald_dream` package is built by several agents in parallel; some
# sibling class-files may be mid-edit and raise at import time. Importing the
# package __init__ (which star-imports every sibling) would abort and stop OUR
# druid cards from merging. Pre-load each emerald_dream submodule individually
# and stub any that fail, BEFORE the card DB initializes. Our `druid` module and
# the helper modules it / our tests lean on must load for real.
import os as _os
import sys as _sys
import types as _types
import importlib.util as _ilu

import fireplace.cards as _fc  # base package (safe)
import fireplace.cards.utils  # noqa: F401

_BASE = "fireplace.cards.emerald_dream"
_DIR = _os.path.join(_os.path.dirname(fireplace.cards.__file__), "emerald_dream")
if _os.path.isdir(_DIR) and _BASE not in _sys.modules:
    _pkg = _types.ModuleType(_BASE)
    _pkg.__path__ = [_DIR]
    _pkg.__package__ = _BASE
    _sys.modules[_BASE] = _pkg
    # Load order: helper modules + our real units first so their failures
    # surface; then the rest (stubbing any peer file currently broken).
    _real = ["_smolder", "druid", "tokens", "neutral"]
    _siblings = [
        f[:-3]
        for f in sorted(_os.listdir(_DIR))
        if f.endswith(".py") and f != "__init__.py"
    ]
    _order = _real + [m for m in _siblings if m not in _real]
    for _mod in _order:
        _name = "%s.%s" % (_BASE, _mod)
        _path = _os.path.join(_DIR, _mod + ".py")
        if not _os.path.exists(_path):
            continue
        _spec = _ilu.spec_from_file_location(_name, _path)
        _m = _ilu.module_from_spec(_spec)
        _sys.modules[_name] = _m
        try:
            _spec.loader.exec_module(_m)
        except Exception:
            if _mod in _real:
                raise  # our own code (or a helper we need) is broken — fail loud
            _m = _types.ModuleType(_name)
            _sys.modules[_name] = _m
        setattr(_pkg, _mod, _m)
        for _attr in dir(_m):
            if not _attr.startswith("_"):
                setattr(_pkg, _attr, getattr(_m, _attr))
# -----------------------------------------------------------------------------

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone, SpellSchool


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# FIR_906 — Overheat (3 mana spell): Give your minions +1/+1. Discard a random
# Nature spell to give them +1/+1 more.
def test_overheat_with_nature_spell_buffs_twice_and_discards():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Two friendly minions to buff.
    a = p1.summon(WISP)  # 1/1
    b = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    # Hand holds exactly one Nature spell (Horn of Plenty) + the Overheat card.
    nature = p1.give("EDR_270")
    assert int(nature.spell_school) == int(SpellSchool.NATURE)
    overheat = p1.give("FIR_906")
    overheat.play()
    # Nature spell was discarded (leaves hand) -> minions got +2/+2 total.
    assert nature.zone != Zone.HAND
    assert nature not in p1.hand
    assert a.atk == 1 + 2 and a.max_health == 1 + 2
    assert b.atk == 4 + 2 and b.max_health == 5 + 2


def test_overheat_without_nature_spell_buffs_once_only():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    a = p1.summon(WISP)  # 1/1
    # No Nature spell in hand: only the Coin (non-Nature) + the Overheat card.
    coin = p1.give("GAME_005")
    assert int(coin.spell_school) != int(SpellSchool.NATURE)
    overheat = p1.give("FIR_906")
    overheat.play()
    # Only the base +1/+1 applied; the Coin is untouched.
    assert a.atk == 1 + 1 and a.max_health == 1 + 1
    assert coin.zone == Zone.HAND


# FIR_907 — Amirdrassil (4 mana Location, durability 3): Summon a @-Cost minion.
# Gain @ Armor. Draw @ card(s). Refresh @ Mana Crystal. (Improves each use!)
def test_amirdrassil_first_use_is_level_one():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Deck so the draw has something to pull (avoid fatigue noise).
    for _ in range(3):
        c = p1.card(WISP, source=p1.hero)
        c.zone = Zone.DECK
    loc = p1.give("FIR_907")
    loc.play()
    assert p1.location is loc
    # A Location is exhausted the turn it lands; backdate turn_played + clear
    # cooldown so it is usable now (no setter on `exhausted`).
    loc.turn_played = -1
    loc.cooldown = 0
    assert not loc.exhausted
    # Set up clean pre-state.
    p1.hero.armor = 0
    p1.used_mana = 5  # 5 of 10 crystals spent
    pre_hand = len(p1.hand)
    pre_field = len(p1.field)
    loc.use()
    # Level 1: summon a 1-Cost minion, +1 Armor, draw 1, refresh 1 crystal.
    assert p1.hero.armor == 1
    assert len(p1.field) == pre_field + 1
    summoned = p1.field[-1]
    assert summoned.cost == 1
    assert len(p1.hand) == pre_hand + 1
    # Refresh 1 Mana Crystal: one more usable mana this turn (temp_mana = 1).
    assert p1.temp_mana == 1
    # Using consumed a durability and set the cooldown.
    assert loc.durability == 2
    assert loc.cooldown == 2


def test_amirdrassil_second_use_is_level_two():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    for _ in range(6):
        c = p1.card(WISP, source=p1.hero)
        c.zone = Zone.DECK
    loc = p1.give("FIR_907")
    loc.play()
    loc.turn_played = -1
    loc.cooldown = 0
    loc.use()  # level 1
    # Clear the cooldown so we can use it again, then reset pre-state.
    loc.cooldown = 0
    p1.hero.armor = 0
    p1.used_mana = 10
    p1.temp_mana = 0
    pre_hand = len(p1.hand)
    pre_field = len(p1.field)
    loc.use()  # level 2
    assert p1.hero.armor == 2
    assert len(p1.field) == pre_field + 1
    assert p1.field[-1].cost == 2
    assert len(p1.hand) == pre_hand + 2
    assert p1.temp_mana == 2
    assert loc.durability == 1


# FIR_908 — Charred Chameleon (1 mana 1/2 Dragon): Battlecry: If you've used
# your Hero Power this turn, give a friendly minion +1/+2 and Rush.
def test_charred_chameleon_buffs_when_hero_power_used():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    target = p1.summon(WISP)  # 1/1, no Rush
    assert not target.rush
    # Use the Hero Power this turn.
    p1.max_mana = 10
    p1.used_mana = 0
    p1.hero.power.use()
    assert p1.hero.power.activations_this_turn == 1
    chameleon = p1.give("FIR_908")
    chameleon.play(target=target)
    # +1/+2 and Rush granted.
    assert target.atk == 1 + 1
    assert target.max_health == 1 + 2
    assert target.rush


def test_charred_chameleon_no_buff_without_hero_power():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    target = p1.summon(WISP)  # 1/1
    # Hero Power NOT used this turn.
    assert p1.hero.power.activations_this_turn == 0
    chameleon = p1.give("FIR_908")
    chameleon.play(target=target)
    # No buff, no Rush.
    assert target.atk == 1
    assert target.max_health == 1
    assert not target.rush
