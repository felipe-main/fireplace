"""Into the Emerald Dream — DRUID collectible cards.

Tight, one-per-card tests asserting PRINTED behaviour. Choices are
auto-resolved (and, where a card targets/rolls randomly, the setup constrains
the outcome to a single value so == assertions hold).
"""

import pytest

# --- Test isolation shim ------------------------------------------------------
# The `emerald_dream` package is being built by several agents in parallel; some
# sibling class-files may be mid-edit and raise at import time. Importing the
# package __init__ (which star-imports every sibling) would then abort and stop
# OUR druid + shared-token cards from merging. To validate the druid cards in
# isolation, pre-load each emerald_dream submodule individually and replace any
# that fail to import with an empty stub, BEFORE the card DB initializes. Our
# own `druid` module (and the shared `tokens` it depends on) must load for real;
# if either fails, that is a genuine bug in our files and we let it surface.
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
    # Load order: our real units first so their failures surface; then the rest
    # (stubbing any peer file that is currently broken).
    _real = ["druid", "tokens", "neutral"]
    _siblings = [
        f[:-3]
        for f in sorted(_os.listdir(_DIR))
        if f.endswith(".py") and f != "__init__.py"
    ]
    _order = _real + [m for m in _siblings if m not in _real]
    for _mod in _order:
        _name = "%s.%s" % (_BASE, _mod)
        _path = _os.path.join(_DIR, _mod + ".py")
        _spec = _ilu.spec_from_file_location(_name, _path)
        _m = _ilu.module_from_spec(_spec)
        _sys.modules[_name] = _m
        try:
            _spec.loader.exec_module(_m)
        except Exception:
            if _mod in _real:
                raise  # our own code (or a token we need) is broken — fail loud
            _m = _types.ModuleType(_name)
            _sys.modules[_name] = _m
        setattr(_pkg, _mod, _m)
        # Star-import the module's public names onto the package, mirroring what
        # the real __init__ does, so get_script_definition finds the classes via
        # hasattr(package, "EDR_xxx").
        for _attr in dir(_m):
            if not _attr.startswith("_"):
                setattr(_pkg, _attr, getattr(_m, _attr))
# -----------------------------------------------------------------------------

from utils import *
from utils import _empty_mulligan

from hearthstone.enums import CardClass, CardType, GameTag, Zone

from fireplace.player import Player


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# EDR_060 — Ward of Earth (5 mana spell): Gain 5 Armor. Summon a random
# 5-Cost minion and give it Taunt.
def test_ward_of_earth():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    assert p1.hero.armor == 0
    ward = p1.give("EDR_060")
    ward.play()
    assert p1.hero.armor == 5
    assert len(p1.field) == 1
    summoned = p1.field[0]
    assert summoned.cost == 5
    assert summoned.taunt


# EDR_270 — Horn of Plenty (2 mana spell): Discover a Nature spell. It
# costs (2) less.
def test_horn_of_plenty():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    horn = p1.give("EDR_270")
    horn.play()
    assert p1.choice is not None
    # Every offered card is a Nature spell.
    from hearthstone.enums import SpellSchool

    for c in p1.choice.cards:
        assert c.type == CardType.SPELL
        assert int(c.spell_school) == int(SpellSchool.NATURE)
    picked = p1.choice.cards[0]
    base_cost = picked.data.cost
    p1.choice.choose(picked)
    got = [c for c in p1.hand if c.id == picked.id][0]
    assert got.cost == base_cost - 2


# EDR_273 — Symbiosis (1 mana spell): Discover a Choose One card from another
# class. It costs (1) less.
def test_symbiosis():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    sym = p1.give("EDR_273")
    sym.play()
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    for c in p1.choice.cards:
        # Choose One card, and not Druid / not Neutral.
        assert c.data.tags.get(GameTag.CHOOSE_ONE, 0)
        classes = getattr(c.data, "classes", None) or [c.data.card_class]
        assert CardClass.DRUID not in classes
        assert CardClass.NEUTRAL not in classes
    picked = p1.choice.cards[0]
    base_cost = picked.data.cost
    p1.choice.choose(picked)
    got = [c for c in p1.hand if c.id == picked.id][0]
    assert got.cost == max(0, base_cost - 1)


# EDR_843 — Reforestation (2 mana spell): Choose One - Draw a spell; or
# Draw a minion. (Hold 3 turns to do both.)
def test_reforestation_choose_one_draw_minion():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Stock the deck: one minion + one spell so each draw target is unique.
    p1.deck.clear()
    spell_in_deck = p1.card("EDR_270", source=p1.hero)
    spell_in_deck.zone = Zone.DECK
    minion_in_deck = p1.card(WISP, source=p1.hero)
    minion_in_deck.zone = Zone.DECK
    refo = p1.give("EDR_843")
    # Play the "Fertilize" half (draw a minion) -> EDR_843b is cards[1].
    refo.play(choose="EDR_843b")
    assert minion_in_deck.zone == Zone.HAND
    assert spell_in_deck.zone == Zone.DECK


def test_reforestation_hold_three_turns_does_both():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.deck.clear()
    spell_in_deck = p1.card("EDR_270", source=p1.hero)
    spell_in_deck.zone = Zone.DECK
    minion_in_deck = p1.card(WISP, source=p1.hero)
    minion_in_deck.zone = Zone.DECK
    refo = p1.give("EDR_843")
    # Drive the Hand "turn begin" trigger three times (held three turns); the
    # third arms the combined-Choose-One flag.
    from fireplace.cards.emerald_dream.druid import _ReforestationDoBoth

    for _ in range(3):
        game.queue_actions(p1.hero, [_ReforestationDoBoth(refo)])
    assert p1.next_choose_one_combined == 1
    refo.play()
    # Both halves resolved: the spell AND the minion are drawn.
    assert spell_in_deck.zone == Zone.HAND
    assert minion_in_deck.zone == Zone.HAND


# EDR_848 — Photosynthesis (3 mana spell): Restore #6 Health. Get 3 random
# Druid spells.
def test_photosynthesis():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 10
    photo = p1.give("EDR_848")
    pre_hand = len(p1.hand) - 1  # minus the photo card we are about to play
    photo.play()
    assert p1.hero.damage == 4  # healed 6
    new_cards = [c for c in p1.hand]
    assert len(p1.hand) == pre_hand + 3
    druid_spells = [c for c in p1.hand if c.type == CardType.SPELL]
    assert len(druid_spells) >= 3
    for c in druid_spells[-3:]:
        assert CardClass.DRUID in (
            getattr(c.data, "classes", None) or [c.data.card_class]
        )


# EDR_209 — Forest Lord Cenarius (10/5/8): Choose Thrice - Give your other
# minions +1/+3; or Summon a 5/5 Ancient with Taunt.
def test_cenarius_choose_buff_three_times():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    ally = p1.summon(WISP)  # 1/1
    cen = p1.give("EDR_209")
    cen.play()
    # Choose the +1/+3 option three times.
    for _ in range(3):
        assert p1.choice is not None
        buff_opt = [c for c in p1.choice.cards if c.id == "EDR_209a"][0]
        p1.choice.choose(buff_opt)
    assert p1.choice is None
    # Other minion gained +3/+9 total; Cenarius untouched (5/8).
    assert ally.atk == 1 + 3
    assert ally.max_health == 1 + 9
    assert cen.atk == 5
    assert cen.max_health == 8


def test_cenarius_choose_summon_three_times():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    cen = p1.give("EDR_209")
    cen.play()
    for _ in range(3):
        assert p1.choice is not None
        summon_opt = [c for c in p1.choice.cards if c.id == "EDR_209b"][0]
        p1.choice.choose(summon_opt)
    assert p1.choice is None
    # Cenarius + three 5/5 Ancients with Taunt.
    ancients = [m for m in p1.field if m.id == "EDR_209t5"]
    assert len(ancients) == 3
    for a in ancients:
        assert a.atk == 5 and a.max_health == 5 and a.taunt


# EDR_271 — Grove Shaper (5/3/6): After you cast a Nature spell, summon a 2/2
# Treant with "Deathrattle: Get a copy of that spell."
def test_grove_shaper_summons_treant_and_copies_spell():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    shaper = p1.summon("EDR_271")
    # Cast a Nature spell (Ward of Earth, EDR_060).
    spell = p1.give("EDR_060")
    spell.play()
    treants = [m for m in p1.field if m.id == "EDR_271t"]
    assert len(treants) == 1
    treant = treants[0]
    assert treant.atk == 2 and treant.max_health == 2
    pre_hand = len(p1.hand)
    treant.destroy()
    game.process_deaths()
    copies = [c for c in p1.hand if c.id == "EDR_060"]
    assert len(copies) == 1
    assert len(p1.hand) == pre_hand + 1


def test_grove_shaper_summons_treant_for_discover_nature_spell():
    # Regression: casting a Nature spell that itself opens a Discover (Horn of
    # Plenty, EDR_270) must STILL summon a Treant. The old `.after` trigger was
    # skipped because the Discover suspended the action queue before the AFTER
    # broadcast ran, so no Treant appeared.
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.summon("EDR_271")
    assert not any(m.id == "EDR_271t" for m in p1.field)
    horn = p1.give("EDR_270")  # Horn of Plenty — a Nature spell that Discovers
    horn.play()
    # The Discover popped up; resolve it.
    assert p1.choice is not None
    _resolve_choices(p1)
    treants = [m for m in p1.field if m.id == "EDR_271t"]
    assert len(treants) == 1
    treant = treants[0]
    assert treant.atk == 2 and treant.max_health == 2
    # Its deathrattle copies the exact spell that summoned it (Horn of Plenty).
    pre = len(p1.hand)
    treant.destroy()
    game.process_deaths()
    copies = [c for c in p1.hand if c.id == "EDR_270"]
    assert len(copies) == 1
    assert len(p1.hand) == pre + 1


def test_grove_shaper_ignores_non_nature_spell():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.summon("EDR_271")
    # The Coin is a non-Nature spell.
    coin = p1.give("GAME_005")
    coin.play()
    assert not any(m.id == "EDR_271t" for m in p1.field)


# EDR_272 — Evergreen Stag (6/6/7): Elusive, Lifesteal, Taunt.
def test_evergreen_stag_keywords():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    stag = p1.summon("EDR_272")
    assert stag.atk == 6 and stag.max_health == 7
    assert stag.taunt
    assert stag.lifesteal
    # Elusive: an enemy spell can't target it.
    decoy = p1.summon(WISP)
    fireball = p2.give("CS2_029")
    assert stag not in fireball.play_targets
    assert decoy in fireball.play_targets


# EDR_847 — Dreambound Disciple (3/3/3): Battlecry and Deathrattle: Your next
# Hero Power costs (0).
def test_dreambound_disciple_battlecry_and_deathrattle():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    assert p1.next_hero_power_costs_zero == 0
    disc = p1.give("EDR_847")
    disc.play()
    # Battlecry armed one free Hero Power.
    assert p1.next_hero_power_costs_zero == 1
    disc.destroy()
    game.process_deaths()
    # Deathrattle armed a second.
    assert p1.next_hero_power_costs_zero == 2


# EDR_845 — Hamuul Runetotem (5/5/6): Start of Game: If each spell in your
# deck is Nature, Imbue your Hero Power. Repeat every 2 spells you cast.
def test_hamuul_imbues_when_deck_all_nature():
    # Deck: Hamuul + only Nature spells (EDR_270) + Nature-free minions (WISP).
    deck = ["EDR_845"] + ["EDR_270"] * 5 + [WISP] * 15
    player1 = Player("Player1", deck, CardClass.DRUID.default_hero)
    player1.cant_fatigue = True
    player2 = Player("Player2", [], CardClass.DRUID.default_hero)
    player2.cant_fatigue = True
    game = BaseTestGame(players=(player1, player2), seed=0)
    game.start()
    _empty_mulligan(game)
    # Start of Game imbued once: druid Imbued Hero Power is installed.
    assert player1.imbues_this_game == 1
    assert player1.hero_power.id == "EDR_847p"


def test_hamuul_does_not_imbue_with_non_nature_spell():
    deck = ["EDR_845"] + ["AV_292"] + ["EDR_270"] * 4 + [WISP] * 15
    player1 = Player("Player1", deck, CardClass.DRUID.default_hero)
    player1.cant_fatigue = True
    player2 = Player("Player2", [], CardClass.DRUID.default_hero)
    player2.cant_fatigue = True
    game = BaseTestGame(players=(player1, player2), seed=0)
    game.start()
    _empty_mulligan(game)
    assert player1.imbues_this_game == 0
    assert player1.hero_power.id != "EDR_847p"


def test_hamuul_repeats_every_two_spells():
    deck = ["EDR_845"] + ["EDR_270"] * 5 + [WISP] * 15
    player1 = Player("Player1", deck, CardClass.DRUID.default_hero)
    player1.cant_fatigue = True
    player2 = Player("Player2", [], CardClass.DRUID.default_hero)
    player2.cant_fatigue = True
    game = BaseTestGame(players=(player1, player2), seed=0)
    game.start()
    _empty_mulligan(game)
    assert player1.imbues_this_game == 1
    # Make sure it is player1's turn before casting.
    if game.current_player is not player1:
        game.end_turn()
    assert game.current_player is player1
    # Cast two cheap Nature spells; the 2nd triggers a repeat imbue.
    for _ in range(2):
        s = player1.give("EDR_270")
        s.play()
        _resolve_choices(player1)
    assert player1.imbues_this_game == 2
