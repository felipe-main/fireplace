"""The Great Dark Beyond — DRUID collectible cards.

Tests assert the PRINTED card behaviour. One test (cluster) per collectible
card: Sha'tari Cloakfield, Starlight Reactor, Uluu the Everdrifter, Star Grazer,
Exarch Othaar (minions); Astral Phaser, Arkonite Revelation, Final Frontier,
Cosmic Phenomenon, Distress Signal (spells).
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards


# GDB_103 — Sha'tari Cloakfield (2/1/4): Elusive. Your first spell each turn
# costs (1) less. Starship Piece.
def test_shatari_cloakfield_stats_and_starship_piece():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    cloak = p1.summon("GDB_103")
    assert cloak.atk == 1 and cloak.max_health == 4
    # Starship Piece tag is present in data (drives the build-on-death flow).
    assert bool(cloak.data.tags.get(GameTag.STARSHIP_PIECE))


# The discount path itself works when armed (the spell-cost reduction is real),
# but the in-play arming is wiped out each turn — see the xfail below.
def test_shatari_cloakfield_discount_machinery_reduces_spell_cost():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.first_spell_discount = 1
    fireball = p1.give("CS2_029")
    assert fireball.cost == p1.card("CS2_029").cost - 1


def test_shatari_cloakfield_first_spell_discount_armed_each_turn():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.summon("GDB_103")
    # Re-arm at the controller's next turn begin.
    game.end_turn()
    game.end_turn()
    # Printed: the first spell each turn costs (1) less.
    assert p1.first_spell_discount == 1
    fireball = p1.give("CS2_029")
    assert fireball.cost == p1.card("CS2_029").cost - 1


# GDB_108 — Starlight Reactor (3/3/3): After you cast an Arcane spell, recast it
# (targets chosen randomly). Starship Piece.
def test_starlight_reactor_recasts_arcane_spell():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    p1.summon("GDB_108")
    # Single enemy minion with lots of HP so both casts of Arcane Explosion
    # (1 dmg to all enemy minions) land on it: original + recast == 2 damage.
    target = p2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    arcane_explosion = p1.give("CS2_025")  # Arcane, 1 dmg to all enemy minions
    arcane_explosion.play()
    # Original cast deals 1, the Reactor recast deals another 1 -> exactly 2.
    assert target.damage == 2


def test_starlight_reactor_ignores_non_arcane_spell():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    p1.summon("GDB_108")
    target = p2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    # Frost Shock is a FROST spell, not Arcane -> no recast (1 dmg total).
    frost_shock = p1.give("CS2_037")  # Frost school, 1 damage to target
    frost_shock.play(target=target)
    assert target.damage == 1


# GDB_854 — Uluu, the Everdrifter (5/6/5 Beast): Each turn this is in your hand,
# gain two random Choose One choices. (Implemented as a vanilla 6/5 Beast —
# the dynamic Choose One accumulation is not modelled; tracked in review.csv.)
def test_uluu_the_everdrifter_vanilla_stats():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    uluu = p1.summon("GDB_854")
    assert uluu.atk == 6 and uluu.max_health == 5
    assert Race.BEAST in uluu.races


# GDB_855 — Star Grazer (8/8/8): Elusive, Taunt. Spellburst: Give your hero +8
# Attack this turn and gain 8 Armor.
def test_star_grazer_keywords_and_spellburst():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    grazer = p1.summon("GDB_855")
    assert grazer.atk == 8 and grazer.max_health == 8
    assert grazer.taunt
    assert grazer.has_spellburst
    p1.hero.armor = 0
    assert p1.hero.atk == 0
    # Cast any spell -> Spellburst fires once.
    p1.give(MOONFIRE).play(target=p1.hero)
    assert not grazer.has_spellburst
    assert p1.hero.armor == 8
    assert p1.hero.atk == 8  # +8 Attack this turn


def test_star_grazer_spellburst_attack_expires_end_of_turn():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.summon("GDB_855")
    p1.give(MOONFIRE).play(target=p1.hero)
    assert p1.hero.atk == 8
    # "+8 Attack this turn" — the hero buff wears off at end of turn.
    game.end_turn()
    assert p1.hero.atk == 0


# GDB_856 — Exarch Othaar (4/3/3): Battlecry: If you're building a Starship,
# get 3 different Arcane spells and reduce their Costs by (2).
def test_exarch_othaar_no_starship_does_nothing():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    assert not p1.is_building_starship
    pre_hand = len(p1.hand)
    p1.give("GDB_856").play()
    # Not building a Starship -> no Arcane spells generated.
    assert len(p1.hand) == pre_hand


def test_exarch_othaar_building_starship_gives_three_discounted_arcane():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    # Bank a Starship Piece by killing one (engine: building starship).
    piece = p1.summon("GDB_100")
    piece.destroy()
    game.process_deaths()
    assert p1.is_building_starship
    pre_hand = len(p1.hand)
    p1.give("GDB_856").play()
    gained = [c for c in p1.hand if c not in ()][pre_hand:]
    gained = p1.hand[pre_hand:]
    assert len(gained) == 3
    for c in gained:
        cdata = _cards.db[c.id]
        assert cdata.type == CardType.SPELL
        assert int(cdata.spell_school) == int(SpellSchool.ARCANE)
        # Cost reduced by exactly 2 (clamped at 0).
        assert c.cost == max(0, _cards.db[c.id].cost - 2)
        assert any(b.id == "GDB_856e" for b in c.buffs)
    # Three DIFFERENT Arcane spells.
    assert len({c.id for c in gained}) == 3


# GDB_851 — Astral Phaser (2): Choose One - Deal $2 damage to two random enemy
# minions; or Make one Dormant for 2 turns.
def test_astral_phaser_choose_lethal_rays():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    # Exactly two enemy minions, each beefy -> each takes exactly 2 damage.
    a = p2.summon(WISP); a.max_health = 80; a.damage = 0
    b = p2.summon(WISP); b.max_health = 80; b.damage = 0
    spell = p1.give("GDB_851")
    spell.play(choose="GDB_851a")
    assert a.damage == 2
    assert b.damage == 2


def test_astral_phaser_stunning_star_subcard_dormant():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    target = p2.summon("CS2_186")  # War Golem 7/7, survives to go dormant
    # The "Make one Dormant" mode is the GDB_851b sub-card (targeted).
    p1.give("GDB_851b").play(target=target)
    assert target.dormant
    assert target.dormant_turns == 2


def test_astral_phaser_lethal_rays_subcard():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    a = p2.summon(WISP); a.max_health = 80; a.damage = 0
    b = p2.summon(WISP); b.max_health = 80; b.damage = 0
    p1.give("GDB_851a").play()
    assert a.damage == 2 and b.damage == 2


# GDB_852 — Arkonite Revelation (1): Draw a card. If it's a spell, it costs (1)
# less.
def test_arkonite_revelation_draws_spell_and_discounts():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    spell_in_deck = p1.card(MOONFIRE)  # a spell, base cost 0
    spell_in_deck.zone = Zone.DECK
    base_cost = spell_in_deck.cost
    p1.give("GDB_852").play()
    assert spell_in_deck.zone == Zone.HAND
    # It's a spell -> costs (1) less (clamped at 0).
    assert spell_in_deck.cost == max(0, base_cost - 1)
    assert any(b.id == "GDB_852e" for b in spell_in_deck.buffs)


def test_arkonite_revelation_minion_not_discounted():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    minion = p1.card(WISP)  # a minion, not a spell
    minion.zone = Zone.DECK
    base_cost = minion.cost
    p1.give("GDB_852").play()
    assert minion.zone == Zone.HAND
    # Not a spell -> no discount.
    assert minion.cost == base_cost
    assert not any(b.id == "GDB_852e" for b in minion.buffs)


# GDB_857 — Final Frontier (7): Discover a 10-Cost minion from the past. Set its
# Cost to (1).
def test_final_frontier_discovers_ten_cost_and_sets_cost_to_one():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    spell = p1.give("GDB_857")
    spell.play()
    # Discover popped up: every option is a 10-Cost minion.
    assert p1.choice is not None
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.type == CardType.MINION
        assert cdata.cost == 10
    chosen_id = p1.choice.cards[0]
    p1.choice.choose(chosen_id)
    given = [c for c in p1.hand if c.id == chosen_id]
    assert given
    card = given[0]
    # Its Cost is SET to (1).
    assert card.cost == 1
    assert any(b.id == "GDB_857e" for b in card.buffs)


# GDB_882 — Cosmic Phenomenon (5): Summon three 2/3 Elementals with Taunt. If
# your board is full, give your minions +1/+1.
def test_cosmic_phenomenon_summons_three_taunt_elementals():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.give("GDB_882").play()
    tokens = [m for m in p1.field if m.id == "GDB_882t"]
    assert len(tokens) == 3
    for m in tokens:
        assert m.atk == 2 and m.max_health == 3
        assert m.taunt
        assert Race.ELEMENTAL in m.races


def test_cosmic_phenomenon_full_board_buffs_minions():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    # Fill the board to 4 so the three summons fill it to 7 and trigger the
    # board-full +1/+1. Use vanilla 1/1 Wisps as the pre-existing minions.
    pre = [p1.summon(WISP) for _ in range(4)]
    p1.give("GDB_882").play()
    # Only 3 of the 3 tokens fit (4 + 3 = 7), board is full.
    assert len(p1.field) == 7
    tokens = [m for m in p1.field if m.id == "GDB_882t"]
    assert len(tokens) == 3
    # Board became full -> every friendly minion gets +1/+1.
    for w in pre:
        assert w.atk == 2 and w.max_health == 2
    for t in tokens:
        assert t.atk == 3 and t.max_health == 4


# GDB_883 — Distress Signal (4): Summon two random 2-Cost minions. Refresh 2
# Mana Crystals.
def test_distress_signal_summons_two_2cost_and_refreshes_mana():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.max_mana = 10
    p1.used_mana = 0
    spell = p1.give("GDB_883")
    cost = spell.cost  # 4
    pre_field = len(p1.field)
    spell.play()
    summoned = p1.field[pre_field:]
    assert len(summoned) == 2
    for m in summoned:
        assert _cards.db[m.id].cost == 2
        assert _cards.db[m.id].type == CardType.MINION
    # Paid `cost`, then Refresh 2 Mana Crystals restores 2.
    assert p1.mana == (10 - cost) + 2
