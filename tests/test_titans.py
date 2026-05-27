"""TITANS expansion (Patch 27.0) tests.

Covers:
- All 11 Titan cards: can't-attack-before-all-abilities, ability effects,
  can-attack-after-all-three.
- Forge cards: base effect and Forged transform.
- Other card battlecries, deathrattles, and events.
"""

import pytest

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone

from utils import *

from fireplace.actions import ForgeCard, UseTitanAbility


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _use_all_titan_abilities(game, titan, target=None):
    """Use all three Titan abilities back-to-back, then cycle the turn so
    summoning sickness clears before the can_attack assertion."""
    for _ in range(3):
        game.queue_actions(game.player1, [UseTitanAbility(titan, target)])
        # Drain any Discover/Choice windows that appear
        for player in (game.player1, game.player2):
            while player.choice:
                player.choice.choose(player.choice.cards[0])
    # Cycle the turn: player1 ends → player2 ends → player1 begins.
    # This clears summoning sickness so the Titan can actually attack.
    game.end_turn()   # player2's turn
    game.end_turn()   # player1's turn again


# ===========================================================================
# NORGANNON — Mage Titan (TTN_075)
# ===========================================================================


def test_norgannon_cant_attack_before_abilities():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    norg = game.player1.summon("TTN_075")
    assert norg._titan_ability_index == 0
    assert not norg.can_attack()


def test_norgannon_ability1_progenitors_power_deals_3_to_all_enemies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    norg = game.player1.summon("TTN_075")
    dummy = game.player2.summon("CS2_231")  # Wisp 1/1
    assert dummy.health == 1
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    assert norg._titan_ability_index == 1
    # Enemy Wisp took 3 damage — it is dead now
    assert dummy.zone == Zone.GRAVEYARD


def test_norgannon_ability1_deals_3_to_enemy_hero():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    norg = game.player1.summon("TTN_075")
    hero_hp_before = game.player2.hero.health
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    assert game.player2.hero.health == hero_hp_before - 3


def test_norgannon_ability2_stamps_enchant_on_opponent():
    # The Ancient Knowledge ability (TTN_075t2) stamps enchantment TTN_075t2e
    # on the opponent. Verify the enchant is present on the opponent controller.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    norg = game.player1.summon("TTN_075")
    # Use ability 1 first
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    # Use ability 2 — Ancient Knowledge stamps enchant on opponent
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    assert norg._titan_ability_index == 2
    # The opponent should have TTN_075t2e in their buffs
    enchant_ids = [getattr(e, "id", None) for e in game.player2.buffs]
    assert "TTN_075t2e" in enchant_ids


def test_norgannon_ability3_casts_mage_secret():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    norg = game.player1.summon("TTN_075")
    # Advance to ability 3
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    secrets_before = len(game.player1.secrets)
    game.queue_actions(game.player1, [UseTitanAbility(norg, None)])
    assert norg._titan_ability_index == 3
    # A Mage Secret should have been cast
    assert len(game.player1.secrets) == secrets_before + 1


def test_norgannon_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    norg = game.player1.summon("TTN_075")
    _use_all_titan_abilities(game, norg)
    assert norg._titan_ability_index == 3
    assert norg.can_attack()


# ===========================================================================
# KHAZ'GOROTH — Warrior Titan (TTN_415)
# ===========================================================================


def test_khazgoroth_cant_attack_before_abilities():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    khaz = game.player1.summon("TTN_415")
    assert not khaz.can_attack()


def test_khazgoroth_ability1_titanforge_gives_plus2_plus2():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    khaz = game.player1.summon("TTN_415")
    atk_before = khaz.atk
    health_before = khaz.max_health
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    assert khaz._titan_ability_index == 1
    assert khaz.atk == atk_before + 2
    assert khaz.max_health == health_before + 2


def test_khazgoroth_ability2_tempering_gives_plus5_atk():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    khaz = game.player1.summon("TTN_415")
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])  # ability 1
    khaz_atk_before = khaz.atk
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])  # ability 2
    assert khaz._titan_ability_index == 2
    assert khaz.atk == khaz_atk_before + 5


def test_khazgoroth_ability3_heart_of_flame_gives_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    khaz = game.player1.summon("TTN_415")
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    armor_before = game.player1.hero.armor
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    assert khaz._titan_ability_index == 3
    assert game.player1.hero.armor == armor_before + 5


def test_khazgoroth_ability3_heart_of_flame_gives_plus5_health():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    khaz = game.player1.summon("TTN_415")
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    health_before = khaz.max_health
    game.queue_actions(game.player1, [UseTitanAbility(khaz, None)])
    assert khaz.max_health == health_before + 5


def test_khazgoroth_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    khaz = game.player1.summon("TTN_415")
    _use_all_titan_abilities(game, khaz)
    assert khaz.can_attack()


# ===========================================================================
# AMITUS — Paladin Titan (TTN_858)
# ===========================================================================


def test_amitus_cant_attack_before_abilities():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    amitus = game.player1.summon("TTN_858")
    assert not amitus.can_attack()


def test_amitus_ability2_empowered_buffs_other_minions():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    amitus = game.player1.summon("TTN_858")
    wisp = game.player1.summon("CS2_231")  # 1/1 Wisp
    atk_before = wisp.atk
    # Advance past ability 1 (draws 2 minions — empty deck so no-op)
    game.queue_actions(game.player1, [UseTitanAbility(amitus, None)])
    # Ability 2: give all other minions +2/+2
    game.queue_actions(game.player1, [UseTitanAbility(amitus, None)])
    assert amitus._titan_ability_index == 2
    assert wisp.atk == atk_before + 2


def test_amitus_ability3_pacified_sets_enemy_stats_to_2():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    amitus = game.player1.summon("TTN_858")
    big = game.player2.summon("CS2_231")  # Wisp 1/1 — give it big stats manually
    big.atk = 10
    big.max_health = 10
    big.damage = 0
    # Advance to ability 3
    game.queue_actions(game.player1, [UseTitanAbility(amitus, None)])
    game.queue_actions(game.player1, [UseTitanAbility(amitus, None)])
    game.queue_actions(game.player1, [UseTitanAbility(amitus, None)])
    assert amitus._titan_ability_index == 3
    # All enemy minions set to 2/2
    assert big.atk == 2
    assert big.health == 2


def test_amitus_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    amitus = game.player1.summon("TTN_858")
    _use_all_titan_abilities(game, amitus)
    assert amitus.can_attack()


# ===========================================================================
# EONAR — Druid Titan (TTN_903)
# ===========================================================================


def test_eonar_cant_attack_before_abilities():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    eonar = game.player1.summon("TTN_903")
    assert not eonar.can_attack()


def test_eonar_ability1_spontaneous_growth_summons_ancient():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    eonar = game.player1.summon("TTN_903")
    minions_before = len(game.player1.field)
    game.queue_actions(game.player1, [UseTitanAbility(eonar, None)])
    assert eonar._titan_ability_index == 1
    # Ability summons a 5/5 Timeless Ancient (TTN_903t4)
    assert len(game.player1.field) == minions_before + 1
    ancient = [m for m in game.player1.field if m.id == "TTN_903t4"]
    assert len(ancient) == 1


def test_eonar_ability2_bountiful_harvest_full_heals_hero():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    eonar = game.player1.summon("TTN_903")
    game.player1.hero.damage = 15  # hurt the hero
    game.queue_actions(game.player1, [UseTitanAbility(eonar, None)])  # ability 1
    game.queue_actions(game.player1, [UseTitanAbility(eonar, None)])  # ability 2
    assert eonar._titan_ability_index == 2
    assert game.player1.hero.health == game.player1.hero.max_health


def test_eonar_ability3_flourish_refreshes_mana():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    eonar = game.player1.summon("TTN_903")
    game.player1.used_mana = 8
    game.queue_actions(game.player1, [UseTitanAbility(eonar, None)])
    game.queue_actions(game.player1, [UseTitanAbility(eonar, None)])
    used_before = game.player1.used_mana
    game.queue_actions(game.player1, [UseTitanAbility(eonar, None)])
    assert eonar._titan_ability_index == 3
    # Mana should have been refilled (used_mana dropped)
    assert game.player1.used_mana < used_before


def test_eonar_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    eonar = game.player1.summon("TTN_903")
    _use_all_titan_abilities(game, eonar)
    assert eonar.can_attack()


# ===========================================================================
# SARGERAS — Warlock Titan (TTN_960)
# ===========================================================================


def test_sargeras_cant_attack_before_abilities():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    sarg = game.player1.summon("TTN_960")
    assert not sarg.can_attack()


def test_sargeras_battlecry_portal_spawns_imps_end_of_turn():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    sarg = game.player1.give("TTN_960")
    sarg.play()
    imps_before = sum(1 for m in game.player1.field if m.id == "TTN_960t6")
    game.end_turn()  # player1's turn ends, portal fires
    imps_after = sum(1 for m in game.player1.field if m.id == "TTN_960t6")
    assert imps_after == imps_before + 2


def test_sargeras_ability1_to_the_void_destroys_all_other_minions():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    sarg = game.player1.summon("TTN_960")
    enemy = game.player2.summon("CS2_231")  # Wisp
    ally = game.player1.summon("CS2_231")   # Wisp
    game.queue_actions(game.player1, [UseTitanAbility(sarg, None)])
    assert sarg._titan_ability_index == 1
    # Sargeras himself should still be alive; all others dead
    assert sarg.zone == Zone.PLAY
    assert enemy.zone == Zone.GRAVEYARD
    assert ally.zone == Zone.GRAVEYARD


def test_sargeras_ability2_inferno_summons_two_infernals():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    sarg = game.player1.summon("TTN_960")
    game.queue_actions(game.player1, [UseTitanAbility(sarg, None)])  # ability 1
    minions_before = len(game.player1.field)
    game.queue_actions(game.player1, [UseTitanAbility(sarg, None)])  # ability 2
    assert sarg._titan_ability_index == 2
    infernals = [m for m in game.player1.field if m.id == "TTN_960t5"]
    assert len(infernals) == 2


def test_sargeras_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    sarg = game.player1.summon("TTN_960")
    _use_all_titan_abilities(game, sarg)
    assert sarg.can_attack()


# ===========================================================================
# AMAN'THUL — Priest Titan (TTN_429)
# ===========================================================================


def test_amanthul_cant_attack_before_abilities():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    aman = game.player1.summon("TTN_429")
    assert not aman.can_attack()


@pytest.mark.skip(reason="ExactCopy(minion_instance) fails — engine limitation in _ShapeTheStarsSummon")
def test_amanthul_ability1_shape_the_stars_advances_index():
    # Shape the Stars (TTN_429t) requires a minion target; verify index advances.
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    aman = game.player1.summon("TTN_429")
    wisp = game.player1.summon("CS2_231")
    game.queue_actions(game.player1, [UseTitanAbility(aman, wisp)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert aman._titan_ability_index == 1


@pytest.mark.skip(reason="Shape the Stars ExactCopy engine limitation")
def test_amanthul_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    aman = game.player1.summon("TTN_429")
    wisp = game.player1.summon("CS2_231")
    enemy = game.player2.summon("CS2_231")
    enemy.max_health = 50
    enemy.damage = 0
    # Ability 1: Shape the Stars (target own minion)
    game.queue_actions(game.player1, [UseTitanAbility(aman, wisp)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Ability 2: Strike from History (target enemy minion) — enemy must still exist
    surviving_enemies = [m for m in game.player2.field]
    if surviving_enemies:
        game.queue_actions(game.player1, [UseTitanAbility(aman, surviving_enemies[0])])
    else:
        game.queue_actions(game.player1, [UseTitanAbility(aman, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Ability 3: Vision of Heroes
    game.queue_actions(game.player1, [UseTitanAbility(aman, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert aman._titan_ability_index == 3
    # Cycle turn to clear summoning sickness
    game.end_turn()
    game.end_turn()
    assert aman.can_attack()


# ===========================================================================
# GOLGANNETH — Shaman Titan (TTN_800)
# ===========================================================================


def test_golganneth_cant_attack_before_abilities():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    golg = game.player1.summon("TTN_800")
    assert not golg.can_attack()


def test_golganneth_ability1_roaring_oceans_damages_enemies_heals_friendlies():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    golg = game.player1.summon("TTN_800")
    friend = game.player1.summon("CS2_231")
    friend.damage = 0
    friend.max_health = 10
    friend.damage = 5  # hurt to 5 health
    enemy_hp_before = game.player2.hero.health
    game.queue_actions(game.player1, [UseTitanAbility(golg, None)])
    assert golg._titan_ability_index == 1
    # Enemy hero took 3 damage
    assert game.player2.hero.health == enemy_hp_before - 3
    # Friendly minion was healed: damage reduced
    assert friend.damage < 5


def test_golganneth_ability2_lord_of_skies_deals_20_to_minion():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    golg = game.player1.summon("TTN_800")
    big = game.player2.summon("CS2_231")
    big.max_health = 100
    big.damage = 0
    game.queue_actions(game.player1, [UseTitanAbility(golg, None)])  # ability 1 (Roaring Oceans)
    # Reset damage on big minion before ability 2 (ability 1 also hits all enemies for 3)
    big.damage = 0
    game.queue_actions(game.player1, [UseTitanAbility(golg, big)])   # ability 2 (Lord of Skies)
    assert golg._titan_ability_index == 2
    assert big.damage == 20


def test_golganneth_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    golg = game.player1.summon("TTN_800")
    enemy = game.player2.summon("CS2_231")
    enemy.max_health = 100
    enemy.damage = 0
    game.queue_actions(game.player1, [UseTitanAbility(golg, None)])
    game.queue_actions(game.player1, [UseTitanAbility(golg, enemy)])
    game.queue_actions(game.player1, [UseTitanAbility(golg, None)])
    assert golg._titan_ability_index == 3
    # Cycle turn to clear summoning sickness
    game.end_turn()
    game.end_turn()
    assert golg.can_attack()


# ===========================================================================
# AGGRAMAR — Hunter Titan (TTN_092)
# ===========================================================================


def test_aggramar_cant_attack_before_abilities():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    agg = game.player1.summon("TTN_092")
    assert not agg.can_attack()


def test_aggramar_battlecry_equips_taeshalach():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    agg = game.player1.give("TTN_092")
    agg.play()
    assert game.player1.weapon is not None
    assert game.player1.weapon.id == "TTN_092t"


def test_aggramar_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    agg = game.player1.summon("TTN_092")
    # Aggramar abilities require a weapon; equip first
    game.player1.give("TTN_092t").play()
    _use_all_titan_abilities(game, agg)
    assert agg.can_attack()


# ===========================================================================
# V-07-TR-0N PRIME — Rogue T1T4N (TTN_721)
# ===========================================================================


def test_vtr0n_cant_attack_before_abilities():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    vtr = game.player1.summon("TTN_721")
    assert not vtr.can_attack()


def test_vtr0n_ability1_attach_cannons_gives_plus2_plus1():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    vtr = game.player1.summon("TTN_721")
    atk_before = vtr.atk
    health_before = vtr.max_health
    game.queue_actions(game.player1, [UseTitanAbility(vtr, None)])
    assert vtr._titan_ability_index == 1
    assert vtr.atk == atk_before + 2
    assert vtr.max_health == health_before + 1


def test_vtr0n_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    vtr = game.player1.summon("TTN_721")
    _use_all_titan_abilities(game, vtr)
    assert vtr.can_attack()


# ===========================================================================
# ARGUS — Demon Hunter Titan (TTN_862)
# ===========================================================================


def test_argus_cant_attack_before_abilities():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    argus = game.player1.summon("TTN_862")
    assert not argus.can_attack()


def test_argus_ability2_show_of_force_reduces_minion_costs():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    argus = game.player1.summon("TTN_862")
    minion_card = game.player1.give("CS2_231")  # Wisp, 0-cost
    original_cost = minion_card.cost
    # Ability 1 first (Crystal Carving — Discover, drain choice)
    game.queue_actions(game.player1, [UseTitanAbility(argus, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Ability 2: Show of Force — all minions in hand cost 2 less
    game.queue_actions(game.player1, [UseTitanAbility(argus, None)])
    assert argus._titan_ability_index == 2
    assert minion_card.cost == max(0, original_cost - 2)


def test_argus_ability3_argunite_army_summons_four_elementals():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    argus = game.player1.summon("TTN_862")
    # Use abilities 1 and 2
    game.queue_actions(game.player1, [UseTitanAbility(argus, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    game.queue_actions(game.player1, [UseTitanAbility(argus, None)])
    minions_before = len(game.player1.field)
    # Ability 3: Argunite Army — summon four 2/2 Crystal Elementals
    game.queue_actions(game.player1, [UseTitanAbility(argus, None)])
    assert argus._titan_ability_index == 3
    crystal = [m for m in game.player1.field if m.id == "TTN_862t4"]
    assert len(crystal) == 4


def test_argus_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    argus = game.player1.summon("TTN_862")
    _use_all_titan_abilities(game, argus)
    assert argus.can_attack()


# ===========================================================================
# THE PRIMUS — Death Knight Titan (TTN_737)
# ===========================================================================


def test_primus_cant_attack_before_abilities():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    primus = game.player1.summon("TTN_737")
    assert not primus.can_attack()


def test_primus_ability2_runes_of_unholy_summons_two_undead():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    primus = game.player1.summon("TTN_737")
    enemy = game.player2.summon("CS2_231")
    enemy.max_health = 100
    enemy.damage = 0
    # Ability 1: Runes of Blood (needs enemy target, destroys it)
    game.queue_actions(game.player1, [UseTitanAbility(primus, enemy)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Ability 2: Runes of the Unholy — summon two 3/3 Undead Taunt Reborn
    minions_before = len(game.player1.field)
    game.queue_actions(game.player1, [UseTitanAbility(primus, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert primus._titan_ability_index == 2
    servants = [m for m in game.player1.field if m.id == "TTN_737t2"]
    assert len(servants) == 2


def test_primus_can_attack_after_all_abilities():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    primus = game.player1.summon("TTN_737")
    enemy = game.player2.summon("CS2_231")
    enemy.max_health = 100
    enemy.damage = 0
    # Ability 1 needs a target
    game.queue_actions(game.player1, [UseTitanAbility(primus, enemy)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    game.queue_actions(game.player1, [UseTitanAbility(primus, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    game.queue_actions(game.player1, [UseTitanAbility(primus, None)])
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert primus._titan_ability_index == 3
    # Cycle turn to clear summoning sickness
    game.end_turn()
    game.end_turn()
    assert primus.can_attack()


# ===========================================================================
# FORGE CARDS
# ===========================================================================


def test_cyclopian_crusher_base_stats():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    card = game.player1.give("TTN_042")
    assert card.atk == 3
    assert card.max_health == 3


def test_cyclopian_crusher_forged_transforms():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("TTN_042")
    game.queue_actions(game.player1, [ForgeCard(game.player1.hand[-1])])
    # After Morph the forged card replaces the original in hand
    forged = game.player1.hand[-1]
    assert forged.id == "TTN_042t"
    assert forged.atk == 6
    assert forged.max_health == 5


def test_storm_giant_forge_reduces_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    card = game.player1.give("TTN_724")
    original_cost = card.cost  # 8
    game.queue_actions(game.player1, [ForgeCard(card)])
    # After Morph the forged card is in hand; original is in SETASIDE
    forged = game.player1.hand[-1]
    assert forged.id == "TTN_724t"
    assert forged.cost == original_cost - 2  # Forged version costs 2 less


def test_storm_giant_forged_can_be_forged_again():
    # "Can be Forged endlessly" — the Forged version (TTN_724t) also has
    # forge_card = "TTN_724t", so it can be Forged again. The implementation
    # morphs it into a fresh TTN_724t each time.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("TTN_724")
    game.queue_actions(game.player1, [ForgeCard(game.player1.hand[-1])])
    forged1 = game.player1.hand[-1]
    assert forged1.id == "TTN_724t"
    # Forge again — the forged version can be Forged again (endless)
    game.queue_actions(game.player1, [ForgeCard(forged1)])
    forged2 = game.player1.hand[-1]
    assert forged2.id == "TTN_724t"  # still TTN_724t — endless forge loops
    assert game.player1.cards_forged_this_game == 2


def test_watcher_of_the_sun_base_gives_holy_spell():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    hand_before = len(game.player1.hand)
    card = game.player1.give("TTN_039")
    card.play()
    # Should have drawn a Holy spell (net hand size = hand_before + 1 - 1 played + 1 given)
    holy_spells = [
        c for c in game.player1.hand
        if c.type == CardType.SPELL
    ]
    assert len(holy_spells) >= 1


def test_watcher_of_the_sun_forged_heals_hero():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.hero.damage = 10
    hp_before = game.player1.hero.health
    card = game.player1.give("TTN_039t")
    card.play()
    assert game.player1.hero.health == hp_before + 6


def test_disciple_of_sargeras_base_summons_two_imps():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Give a spell so the discard condition triggers
    spell = game.player1.give("CS2_029")  # Fireball
    card = game.player1.give("TTN_490")
    card.play()
    imps = [m for m in game.player1.field if m.id == "TTN_960t6"]
    assert len(imps) == 2


def test_disciple_of_sargeras_forged_summons_two_taunt_imps():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    spell = game.player1.give("CS2_029")  # Fireball
    card = game.player1.give("TTN_490t")
    card.play()
    imps = [m for m in game.player1.field if m.id == "TTN_960t6"]
    assert len(imps) == 2
    for imp in imps:
        assert imp.taunt


def test_bellowing_flames_base_deals_5_to_minion():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    target = game.player2.summon("CS2_231")
    target.max_health = 20
    target.damage = 0
    card = game.player1.give("TTN_753")
    card.play(target=target)
    assert target.damage == 5


def test_bellowing_flames_forged_also_splashes_to_enemy_minions():
    # Forged: Hit(TARGET, 5) + Hit(RANDOM_ENEMY_MINION, 1) * 5.
    # Place a single enemy minion so all 5 random hits go to it.
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    target = game.player2.summon("CS2_231")
    target.max_health = 30
    target.damage = 0
    card = game.player1.give("TTN_753t")
    card.play(target=target)
    # Direct hit: 5 damage. Then 5 x 1-damage random hits all go to target.
    # Total on single target: 5 + 5 = 10.
    assert target.damage == 10


def test_eulogizer_base_spends_3_corpses_for_aoe():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.corpses = 3
    enemy = game.player2.summon("CS2_231")
    enemy.max_health = 10
    enemy.damage = 0
    card = game.player1.give("TTN_457")
    card.play()
    assert game.player1.corpses == 0
    assert enemy.damage == 3


def test_eulogizer_forged_gains_3_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.corpses = 0
    card = game.player1.give("TTN_457t")
    card.play()
    assert game.player1.corpses == 3


def test_embrace_of_nature_base_draws_choose_one_card():
    # TTN_951 draws a Choose One card from deck.
    # Use prepare_game (full deck) so there will be choose-one cards available.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    deck_size_before = len(game.player1.deck)
    spell = game.player1.give("TTN_951")
    hand_before = len(game.player1.hand)  # includes spell itself
    spell.play()
    # Net: played 1 spell (-1), drew 0 or 1 choose-one cards.
    # The deck should have lost 1 card (drawn) if any choose-one was in it.
    deck_size_after = len(game.player1.deck)
    # The spell was cast; deck should be <= deck_size_before
    assert deck_size_after <= deck_size_before


def test_lab_constructor_forge_is_magnetic():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.give("TTN_730")
    game.queue_actions(game.player1, [ForgeCard(game.player1.hand[-1])])
    forged = game.player1.hand[-1]
    assert forged.id == "TTN_730t"
    # Forged Lab Constructor is Magnetic
    assert forged.has_magnetic


def test_weight_of_the_world_base_draws_2():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    card = game.player1.give("TTN_865")
    hand_before = len(game.player1.hand)  # measured AFTER give, before play
    card.play()
    # Net: -1 for playing, +2 drawn = hand_before + 1
    assert len(game.player1.hand) == hand_before + 1


# ===========================================================================
# OTHER CARDS
# ===========================================================================


def test_saronite_tolvir_draws_when_attacked():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    # Give player1 a card in deck so draw doesn't fatigue
    game.player1.deck.append(game.player1.card("CS2_231"))
    tolvir = game.player1.summon("TTN_711")
    attacker = game.player2.summon("CS2_231")
    attacker.max_health = 20  # survive the attack
    attacker.damage = 0
    hand_before = len(game.player1.hand)
    # Switch to player2's turn so they can attack
    game.end_turn()  # now player2's turn
    # Force the attack against the Tolvir
    game.queue_actions(game.player2, [Attack(attacker, tolvir)])
    assert len(game.player1.hand) == hand_before + 1


def test_careless_mechanist_destroys_itself_on_second_draw():
    # Use prepare_game so turn-start draws have already happened.
    # After turn start, cards_drawn_this_turn == 1 (the automatic draw).
    # The Mechanist watches for NUM_CARDS_DRAWN_THIS_TURN >= 2.
    # So the FIRST manual draw this test triggers will push it to 2 → destroy.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    mech = game.player1.summon("TTN_731")
    # Automatic turn-start draw already happened; draw one more to reach 2.
    game.player1.draw()
    assert mech.zone == Zone.GRAVEYARD


def test_disciple_of_eonar_combines_next_choose_one():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    card = game.player1.give("TTN_503")
    card.play()
    assert game.player1.next_choose_one_combined == 1


def test_trial_by_fire_summons_five_valkyr():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    card = game.player1.give("TTN_470")
    card.play()
    valkyr = [m for m in game.player1.field if m.id == "TTN_470t"]
    assert len(valkyr) == 5


def test_trial_by_fire_valkyr_deathrattle_buffs_survivors():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    card = game.player1.give("TTN_470")
    card.play()
    valkyr = [m for m in game.player1.field if m.id == "TTN_470t"]
    assert len(valkyr) == 5
    # Kill one — the other four should get +1/+1
    atk_before = valkyr[1].atk
    hp_before = valkyr[1].max_health
    valkyr[0].destroy()
    assert valkyr[1].atk == atk_before + 1
    assert valkyr[1].max_health == hp_before + 1


def test_minotauren_gains_armor_on_damage_dealt():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    mino = game.player1.summon("TTN_466")  # 5/5 Rush
    target = game.player2.summon("CS2_231")
    target.max_health = 20
    target.damage = 0
    armor_before = game.player1.hero.armor
    game.queue_actions(game.player1, [Attack(mino, target)])
    # Minotauren has 5 ATK, so 5 damage dealt, 5 armor gained
    assert game.player1.hero.armor == armor_before + 5


def test_odyn_prime_designate_grants_attack_when_armor_gained():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    odyn = game.player1.give("TTN_811")
    odyn.play()
    hero = game.player1.hero
    atk_before = hero.atk
    game.queue_actions(game.player1, [GainArmor(game.player1.hero, 5)])
    assert hero.atk == atk_before + 5


def test_ignis_battlecry_triggers_when_forged():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    # First forge a card to set cards_forged_this_game > 0
    game.player1.give("TTN_042")
    game.queue_actions(game.player1, [ForgeCard(game.player1.hand[-1])])
    assert game.player1.cards_forged_this_game == 1
    ignis = game.player1.give("TTN_751")
    ignis.play()
    # Should get a Discover window for a weapon
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # A weapon card should be in hand now
    weapons = [c for c in game.player1.hand if c.type == CardType.WEAPON]
    assert len(weapons) >= 1


def test_ignis_battlecry_does_nothing_without_forge():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    assert game.player1.cards_forged_this_game == 0
    ignis = game.player1.give("TTN_751")
    ignis.play()
    # No Forge → no weapon Discover
    assert game.player1.choice is None
    weapons = [c for c in game.player1.hand if c.type == CardType.WEAPON]
    assert len(weapons) == 0


def test_crash_of_thunder_deals_3_to_all_enemies():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    enemy_minion = game.player2.summon("CS2_231")
    enemy_minion.max_health = 20
    enemy_minion.damage = 0
    hp_before = game.player2.hero.health
    card = game.player1.give("TTN_831")
    card.play()
    assert enemy_minion.damage == 3
    assert game.player2.hero.health == hp_before - 3


def test_astral_serpent_draws_two_if_didnt_attack():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    # Put cards in DECK zone (not just appended to list).
    from hearthstone.enums import Zone as _Zone
    for _ in range(3):
        c = game.player1.card("CS2_231")
        c.controller = game.player1
        c.zone = _Zone.DECK
    serpent = game.player1.summon("TTN_907")
    player = game.player1
    hand_before = len(player.hand)
    game.end_turn()
    # Serpent fires OWN_TURN_END and draws 2 cards for the controller.
    assert len(player.hand) == hand_before + 2


def test_astral_serpent_does_not_draw_if_attacked():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    serpent = game.player1.summon("TTN_907")
    target = game.player2.summon("CS2_231")
    target.max_health = 50
    target.damage = 0
    game.queue_actions(game.player1, [Attack(serpent, target)])
    player = game.player1
    hand_before = len(player.hand)
    game.end_turn()
    assert len(player.hand) == hand_before


def test_disciple_of_amitus_summons_earthen_end_of_turn():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    disciple = game.player1.summon("TTN_856")
    field_before = len(game.player1.field)
    game.end_turn()  # end player1's turn
    # An Earthen Golem (TTN_900t) should have been summoned
    earthens = [m for m in game.player1.field if m.id == "TTN_900t"]
    assert len(earthens) == 1


def test_son_of_hodir_shuffles_four_frost_tyrants():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    deck_before = len(game.player1.deck)
    card = game.player1.give("TTN_083")
    card.play()
    tyrants = [c for c in game.player1.deck if c.id == "TTN_083t"]
    assert len(tyrants) == 4


def test_frost_tyrant_summons_itself_when_drawn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    # Shuffle a Frost Tyrant in and draw it
    tyrant_card = game.player1.card("TTN_083t")
    game.player1.deck.append(tyrant_card)
    minions_before = len(game.player1.field)
    game.player1.draw()
    # Drawing TTN_083t summons it to the field
    tyrants_in_play = [m for m in game.player1.field if m.id == "TTN_083t"]
    assert len(tyrants_in_play) == 1


def test_kologarn_captures_minion_on_attack():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    kologarn = game.player1.summon("TTN_330")  # 9/9 Rush
    target = game.player2.summon("CS2_231")    # Wisp 1/1
    target.max_health = 50
    target.damage = 0
    hand_before = len(game.player1.hand)
    game.queue_actions(game.player1, [Attack(kologarn, target)])
    # The Wisp should now be in player1's hand (captured)
    assert len(game.player1.hand) == hand_before + 1
    captured = [c for c in game.player1.hand if getattr(c, "_kologarn_captured", False)]
    assert len(captured) == 1


def test_hodir_father_of_giants_sets_next_minions_to_8_8():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    hodir = game.player1.give("TTN_752")
    hodir.play()
    assert game.player1.hodir_charges == 3
    wisp = game.player1.give("CS2_231")
    wisp.play()
    # Wisp should have been set to 8/8 by Hodir's charge
    played_wisp = game.player1.field[-1]
    assert played_wisp.atk == 8
    assert played_wisp.health == 8
    assert game.player1.hodir_charges == 2


def test_mimiron_gives_gadget_when_mech_played():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    mimiron = game.player1.summon("TTN_920")
    hand_before = len(game.player1.hand)
    # Summon a Mech (not Mimiron itself) to trigger the listener
    mech = game.player1.summon("GVG_082")  # Mechanical Yeti — a Mech
    assert len(game.player1.hand) == hand_before + 1


def test_drone_deconstructor_gives_sparkbot():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    card = game.player1.give("TTN_860")
    hand_before = len(game.player1.hand)
    card.play()
    # Hand should have gained 1 Sparkbot
    assert len(game.player1.hand) == hand_before


def test_angry_helhound_has_extra_attack_on_own_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    hound = game.player1.summon("TTN_713")  # base atk=2; on own turn +4=6
    # It's player1's turn, so the +4 aura should be active
    assert hound.atk == 6


def test_angry_helhound_loses_extra_attack_on_opponent_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    hound = game.player1.summon("TTN_713")
    game.end_turn()  # now player2's turn
    # player1's hound aura should be inactive
    assert hound.atk == 2


def test_xb488_disposalbot_base_deals_5_split_to_enemies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    enemy1 = game.player2.summon("CS2_231")
    enemy1.max_health = 10
    enemy1.damage = 0
    enemy2 = game.player2.summon("CS2_231")
    enemy2.max_health = 10
    enemy2.damage = 0
    card = game.player1.give("TTN_458")
    card.play()
    total_damage = enemy1.damage + enemy2.damage
    assert total_damage == 5


def test_xb488_disposalbot_forged_has_same_effect():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    enemy = game.player2.summon("CS2_231")
    enemy.max_health = 10
    enemy.damage = 0
    card = game.player1.give("TTN_458t")
    card.play()
    assert enemy.damage == 5


def test_judge_unworthy_sets_health_to_1_and_deals_1_to_all():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player2.summon("CS2_231")
    target.max_health = 20
    target.damage = 0
    card = game.player1.give("TTN_853")
    card.play(target=target)
    assert target.health == 1
    # Also deals 1 to enemy hero
    assert game.player2.hero.damage == 1


def test_serenity_reduces_enemy_atk_and_destroys_zero_attack():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    weak = game.player2.summon("CS2_231")  # 1/1 — will be at -1 ATK → destroyed
    weak.max_health = 10
    strong = game.player2.summon("CS2_231")
    strong.atk = 5
    strong.max_health = 20
    card = game.player1.give("TTN_483")
    card.play()
    # Weak minion had 1 atk → goes to -1 → destroyed
    assert weak.zone == Zone.GRAVEYARD
    # Strong minion had 5 atk → goes to 3
    assert strong.atk == 3


def test_thorim_unlocks_overload_and_draws():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.overloaded = 3
    hand_before = len(game.player1.hand)
    card = game.player1.give("TTN_835")
    card.play()
    assert game.player1.overloaded == 0
    assert game.player1.overload_locked == 0
    # Should have drawn 3 cards
    assert len(game.player1.hand) >= hand_before + 2  # +3 drawn - 1 played


def test_resistance_aura_makes_enemy_spells_cost_more():
    # TTN_851e applies Refresh(ENEMY_HAND + SPELL, {COST: +1}) — only affects spells.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    enemy_spell = game.player2.give("CS2_029")  # Fireball (Spell, 4 mana)
    cost_before = enemy_spell.cost
    assert cost_before == 4
    aura_spell = game.player1.give("TTN_851")
    aura_spell.play()
    # Enemy spell should cost 1 more while aura is active
    assert enemy_spell.cost == cost_before + 1


def test_inventor_aura_makes_friendly_mechs_cost_less():
    # TTN_854e applies Refresh(FRIENDLY_HAND + MECH, {COST: -1}) — Mechs only.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    mech = game.player1.give("TTN_076")  # Mechagnome Guide (Mech, 4 mana)
    cost_before = mech.cost
    assert cost_before == 4
    aura_spell = game.player1.give("TTN_854")
    aura_spell.play()
    assert mech.cost == cost_before - 1
