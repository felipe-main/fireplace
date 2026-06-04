"""Tests for Cataclysm — DEATHKNIGHT (CATA_) cards.

ISOLATION NOTE: the cataclysm package star-imports every per-class sibling
file. While the multi-agent set build is in flight, some siblings may raise at
import time. To test the deathknight cards in isolation we inject a stub
`fireplace.cards.cataclysm` package that exposes ONLY the deathknight module's
classes before fireplace.cards initializes. Once all sibling files are complete
this shim is a no-op and the official gate (tests/test_carddb.py) exercises the
full package.
"""

import sys
import types
import importlib.util


def _install_deathknight_only_package():
    if "fireplace.cards.cataclysm" in sys.modules:
        return
    import fireplace.cards.utils  # noqa: F401

    pkg_name = "fireplace.cards.cataclysm"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = ["fireplace/cards/cataclysm"]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

    spec = importlib.util.spec_from_file_location(
        pkg_name + ".deathknight", "fireplace/cards/cataclysm/deathknight.py"
    )
    dk = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name + ".deathknight"] = dk
    spec.loader.exec_module(dk)
    for name in dir(dk):
        if name.startswith("CATA_"):
            setattr(pkg, name, getattr(dk, name))


_install_deathknight_only_package()

from hearthstone.enums import CardClass, GameTag, Zone, Race, CardType  # noqa: E402
from utils import prepare_game  # noqa: E402
from fireplace.cards import db  # noqa: E402


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_155 Arisen Onyxia — Colossal +2 + max-Health-instead-of-damage
# ---------------------------------------------------------------------------


def test_arisen_onyxia_summons_two_wing_limbs():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    onyxia = p1.summon("CATA_155")
    # Colossal +2: body + two Onyxia's Wing limbs on the field.
    wings = [c for c in p1.field if c.id in ("CATA_155t", "CATA_155t1")]
    assert onyxia in p1.field
    assert len(wings) == 2


def test_arisen_onyxia_converts_self_damage_to_max_health_on_own_turn():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.summon("CATA_155")
    hero = p1.hero
    hero.max_health = 30
    hero.damage = 0
    base_max = hero.max_health
    # On p1's own turn, a self-inflicted 3 damage becomes +3 max Health, no loss.
    from fireplace.actions import Hit

    game.queue_actions(p1.hero, [Hit(hero, 3)])
    assert hero.damage == 0
    assert hero.max_health == base_max + 3


def test_arisen_onyxia_takes_damage_normally_on_enemy_turn():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.summon("CATA_155")
    hero = p1.hero
    hero.max_health = 30
    hero.damage = 0
    base_max = hero.max_health
    game.end_turn()  # now player2's turn
    p2 = game.player2
    from fireplace.actions import Hit

    game.queue_actions(p2.hero, [Hit(hero, 3)])
    # Opponent's turn: normal damage, no max-Health conversion.
    assert hero.damage == 3
    assert hero.max_health == base_max


# ---------------------------------------------------------------------------
# CATA_155t Onyxia's Wing — "get a random {0}-Cost minion that costs Health"
# ---------------------------------------------------------------------------


def test_onyxia_wing_token_gives_two_cost_minion_costing_health():
    # The wing token's own battlecry (when PLAYED directly) gets one minion.
    # Base {0} is 2 (CardXML TAG_SCRIPT_DATA_NUM_1=2) with no Heralds.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.heralds_this_game = 0
    wing = p1.give("CATA_155t")
    wing.play()  # wing leaves hand, battlecry adds exactly one minion
    assert len(p1.hand) == 1
    got = p1.hand[-1]
    assert got.type == CardType.MINION
    assert (got.data.cost or 0) == 2  # heralds == 0 -> base 2-Cost
    # Stamped with Onyxia's Blood -> pays Health instead of Mana this turn.
    assert got.card_costs_health


def test_arisen_onyxia_battlecry_gives_two_cost_health_minions():
    # Playing the parent resolves both wings' rewards: two base 2-Cost minions
    # that cost Health this turn (no Heralds yet).
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.heralds_this_game = 0
    onyxia = p1.give("CATA_155")
    onyxia.play()  # Onyxia leaves hand; both wings' rewards land (two minions)
    gained = [c for c in p1.hand]
    assert len(gained) == 2
    for c in gained:
        assert (c.data.cost or 0) == 2
        assert c.card_costs_health


def test_onyxia_wing_cost_scales_with_heralds():
    # base 2, +1 per Herald, capped at +2: 0->2, 1->3, 2->4, 3->4.
    for heralds, expected in [(0, 2), (1, 3), (2, 4), (3, 4)]:
        game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
        p1 = game.player1
        p1.discard_hand()
        p1.heralds_this_game = heralds
        wing = p1.give("CATA_155t")
        wing.play()
        assert len(p1.hand) == 1
        assert (p1.hand[-1].data.cost or 0) == expected, (heralds, expected)


# ---------------------------------------------------------------------------
# CATA_156 Experimental Animation — Herald + AoE
# ---------------------------------------------------------------------------


def test_experimental_animation_heralds_and_aoe():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.heralds_this_game = 0
    p2 = game.player2
    # Two enemy minions with enough HP to survive (assert exact damage).
    m1 = p2.summon("CS2_182")  # 4/5 Ogre
    m1.max_health = 10
    m1.damage = 0
    m2 = p2.summon("CS2_182")
    m2.max_health = 10
    m2.damage = 0
    # Friendly minion must be untouched (AoE hits ENEMY minions only).
    friendly = p1.summon("CS2_182")
    friendly.max_health = 10
    friendly.damage = 0
    spell = p1.give("CATA_156")
    spell.play()
    assert p1.heralds_this_game == 1
    assert m1.damage == 4
    assert m2.damage == 4
    assert friendly.damage == 0


# ---------------------------------------------------------------------------
# CATA_161 Gruesome Nightmare — give a friendly minion +Attack == its Attack
# ---------------------------------------------------------------------------


def test_gruesome_nightmare_buffs_field_minion_by_own_attack():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    # Only one eligible friendly minion -> the random pick is deterministic.
    target = p1.summon("CS2_182")  # 4/5 Ogre, atk 4
    assert target.atk == 4
    nightmare = p1.give("CATA_161")  # 3/3
    nightmare.play()
    _resolve_choices(p1)
    # Eligible pool = {target on field, nightmare itself excluded}. The buff is
    # +3 (nightmare's Attack). nightmare may also be eligible (it's on field),
    # so check that exactly one of the two eligible minions got +3.
    # Pool is FRIENDLY_MINIONS - SELF (just the Ogre) | nothing in hand.
    assert target.atk == 4 + 3


def test_gruesome_nightmare_choose_hand_or_battlefield_minion():
    # The player CHOOSES a minion across hand AND battlefield. Here we pick the
    # one sitting in hand; it gets +Attack equal to Gruesome Nightmare's Attack.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    field_minion = p1.summon("CS2_182")   # 4/5 on board
    hand_minion = p1.give("CS2_182")       # 4/5 in hand
    nightmare = p1.give("CATA_161")        # 3/3 (atk 3)
    nightmare.play()
    assert p1.choice is not None
    # Both the field minion and the hand minion are offered.
    assert field_minion in p1.choice.cards and hand_minion in p1.choice.cards
    p1.choice.choose(hand_minion)          # pick the in-hand minion
    assert hand_minion.atk == 4 + 3        # +3 from Nightmare's Attack
    assert field_minion.atk == 4           # the board minion untouched


# ---------------------------------------------------------------------------
# CATA_464 Blackwing Experiment — deathrattle spell scaling with Attack
# ---------------------------------------------------------------------------


def test_blackwing_experiment_deathrattle_gives_scaled_spell():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    exp = p1.summon("CATA_464")  # 3/1
    assert exp.atk == 3
    pre = len(p1.hand)
    exp.destroy()
    assert len(p1.hand) == pre + 1
    spell = p1.hand[-1]
    assert spell.id == "CATA_464t"
    assert spell._breath_damage == 3
    # Cast it on a beefy enemy minion -> exactly 3 damage.
    p2 = game.player2
    victim = p2.summon("CS2_182")
    victim.max_health = 10
    victim.damage = 0
    spell.play(target=victim)
    assert victim.damage == 3


def test_blackwing_experiment_buffed_attack_scales_spell():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    exp = p1.summon("CATA_464")
    exp.atk = 7  # buffed
    exp.destroy()
    spell = p1.hand[-1]
    assert spell._breath_damage == 7


# ---------------------------------------------------------------------------
# CATA_465 Chow Down — five Drakes, conditional Rush on 8 Corpses
# ---------------------------------------------------------------------------


def test_chow_down_summons_five_drakes_no_rush_without_corpses():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 0
    spell = p1.give("CATA_465")
    spell.play()
    drakes = [c for c in p1.field if c.id == "CATA_465t"]
    assert len(drakes) == 5
    assert all(d.atk == 5 and d.max_health == 4 for d in drakes)
    assert all(not d.rush for d in drakes)
    assert p1.corpses == 0


def test_chow_down_spends_8_corpses_for_rush():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 8
    spell = p1.give("CATA_465")
    spell.play()
    drakes = [c for c in p1.field if c.id == "CATA_465t"]
    assert len(drakes) == 5
    assert all(d.rush for d in drakes)
    assert p1.corpses == 0


def test_chow_down_full_board_does_not_waste_corpses():
    # Regression for the summon/Corpse ordering: with a FULL board (7 minions)
    # no Drakes can be summoned, so no Rush is granted -> the 8 Corpses must NOT
    # be spent. The old code spent Corpses before the summon loop and would
    # drop to 0 here; the fixed code summons first and only spends on a grant.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    for _ in range(7):
        p1.summon("CS2_182")  # fill the board to 7
    assert len(p1.field) == 7
    p1.corpses = 8
    spell = p1.give("CATA_465")
    spell.play()
    drakes = [c for c in p1.field if c.id == "CATA_465t"]
    assert len(drakes) == 0          # board was full
    assert p1.corpses == 8           # nothing summoned -> no Rush -> no spend


def test_chow_down_partial_board_spends_corpses_and_rushes_summoned():
    # Six minions on board -> exactly one Drake fits. >= 8 Corpses present, so
    # the single summoned Drake gets Rush and 8 Corpses are spent.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    for _ in range(6):
        p1.summon("CS2_182")  # board at 6 -> room for exactly one Drake
    p1.corpses = 8
    spell = p1.give("CATA_465")
    spell.play()
    drakes = [c for c in p1.field if c.id == "CATA_465t"]
    assert len(drakes) == 1
    assert drakes[0].rush
    assert p1.corpses == 0


# ---------------------------------------------------------------------------
# CATA_467 Command Claw — after hero attacks, give random friendly +2 Attack
# ---------------------------------------------------------------------------


def test_command_claw_buffs_random_minion_after_hero_attack():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    # One friendly minion -> deterministic buff target.
    minion = p1.summon("CS2_182")  # 4/5
    assert minion.atk == 4
    weapon = p1.give("CATA_467")
    weapon.play()
    assert p1.weapon is weapon
    p2 = game.player2
    p2.hero.max_health = 30
    p2.hero.damage = 0
    p1.hero.attack(p2.hero)
    # After the hero attacks, the lone friendly minion gains +2 Attack.
    assert minion.atk == 4 + 2


# ---------------------------------------------------------------------------
# CATA_469 Chromatic Broodmother — refresh mana == its Attack on attack
# ---------------------------------------------------------------------------


def test_chromatic_broodmother_refreshes_mana_on_attack():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    brood = p1.summon("CATA_469")  # 2/5 Rush, atk 2
    assert brood.atk == 2
    p1.used_mana = 6  # 4 available
    p2 = game.player2
    victim = p2.summon("CS2_182")
    victim.max_health = 20
    victim.damage = 0
    brood.attack(victim)
    # Refresh 2 mana crystals == its Attack -> used_mana drops by 2.
    assert p1.used_mana == 4


# ---------------------------------------------------------------------------
# CATA_470 Victor Nefarius — craft, cost reduction with Dragon in hand
# ---------------------------------------------------------------------------


def _resolve_victor_picks(player):
    """Resolve Victor's two Discovers (pick the first option each), returning the
    chosen (dragon, undead) cards so the test can assert the combined statline."""
    picks = []
    while player.choice:
        chosen = player.choice.cards[0]
        picks.append(chosen)
        player.choice.choose(chosen)
    return picks


def test_victor_nefarius_combines_discovered_dragon_and_undead():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.give("CATA_470").play()
    dragon, undead = _resolve_victor_picks(p1)
    assert dragon.type == CardType.MINION and Race.DRAGON in dragon.races
    assert undead.type == CardType.MINION and Race.UNDEAD in undead.races
    creation = next(c for c in p1.hand if c.id == "CATA_470t1")
    # Combined statline: summed Attack/Health, summed Cost capped at 10.
    assert creation.atk == dragon.atk + undead.atk
    assert creation.health == dragon.health + undead.health
    assert creation.cost == min(10, dragon.cost + undead.cost)
    # The Creation is an Undead Dragon.
    assert Race.DRAGON in creation.races and Race.UNDEAD in creation.races


def test_victor_nefarius_discounts_creation_with_dragon_in_hand():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    held = p1.give("CATA_465t")  # Hungry Drake — a Dragon held in hand
    assert Race.DRAGON in held.races
    p1.give("CATA_470").play()
    dragon, undead = _resolve_victor_picks(p1)
    creation = next(c for c in p1.hand if c.id == "CATA_470t1")
    # Holding a Dragon -> 3 off the combined Cost (clamped at 0).
    expected = max(0, min(10, dragon.cost + undead.cost) - 3)
    assert creation.cost == expected


# ---------------------------------------------------------------------------
# CATA_471 Talanji's Last Stand — grant deathrattle to your minions
# ---------------------------------------------------------------------------


def test_talanji_grants_deathrattle_summoning_4cost_minion():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    minion = p1.summon("CS2_182")  # 4/5
    spell = p1.give("CATA_471")
    spell.play()
    # The buff (granted deathrattle) is applied to the minion.
    assert any(b.id == "CATA_471e" for b in minion.buffs)
    minion.destroy()
    # Deathrattle summons a random 4-Cost minion: the Ogre left, one summon
    # arrived in its place.
    summoned = [c for c in p1.field if c.id != "CS2_182"]
    assert len(summoned) == 1
    assert (summoned[0].data.cost or 0) == 4


# ---------------------------------------------------------------------------
# CATA_780 Obsessive Technician — Lifesteal + Herald
# ---------------------------------------------------------------------------


def test_obsessive_technician_heralds_on_battlecry():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.heralds_this_game = 0
    tech = p1.give("CATA_780")
    tech.play()
    assert p1.heralds_this_game == 1
    assert tech.lifesteal


# ---------------------------------------------------------------------------
# CATA_007 Consumption — deal 3 to two random enemy minions, draw per dead.
# ---------------------------------------------------------------------------


def test_consumption_hits_two_enemies_and_draws_per_dead():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p2 = game.player2
    # Exactly two enemy minions -> both are hit (distinct random sample of 2).
    weak = p2.summon("CS2_182")   # 4/5
    weak.max_health = 3
    weak.damage = 0               # dies to 3 damage
    tough = p2.summon("CS2_182")  # 4/5
    tough.max_health = 10
    tough.damage = 0              # survives at damage 3
    # Stock the deck so the draw can actually pull a card.
    p1.card("CS2_182").zone = Zone.DECK
    pre_hand = len(p1.hand)
    spell = p1.give("CORE_CATA_007")
    spell.play()
    _resolve_choices(p1)
    assert weak.zone == Zone.GRAVEYARD
    assert tough.zone == Zone.PLAY and tough.damage == 3
    # Exactly one minion died -> exactly one card drawn.
    assert len(p1.hand) == pre_hand + 1


def test_consumption_no_draw_when_none_die():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p2 = game.player2
    a = p2.summon("CS2_182")
    a.max_health = 10
    a.damage = 0
    b = p2.summon("CS2_182")
    b.max_health = 10
    b.damage = 0
    p1.card("CS2_182").zone = Zone.DECK
    pre_hand = len(p1.hand)
    spell = p1.give("CORE_CATA_007")
    spell.play()
    _resolve_choices(p1)
    assert a.damage == 3 and b.damage == 3
    # Nothing died -> no draw.
    assert len(p1.hand) == pre_hand


# ---------------------------------------------------------------------------
# CATA_009 Death's Advance — Freeze a character, Discover a spell.
# ---------------------------------------------------------------------------


def test_deaths_advance_freezes_and_discovers_spell():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p2 = game.player2
    victim = p2.summon("CS2_182")  # 4/5
    pre_hand = len(p1.hand)
    spell = p1.give("CORE_CATA_009")
    spell.play(target=victim)
    # The target is frozen.
    assert victim.frozen
    # A Discover (spell) is offered; resolve it -> exactly one spell to hand.
    assert p1.choice is not None
    assert all(c.type == CardType.SPELL for c in p1.choice.cards)
    _resolve_choices(p1)
    assert len(p1.hand) == pre_hand + 1
    assert p1.hand[-1].type == CardType.SPELL
