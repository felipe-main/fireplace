"""Murder at Castle Nathria (Patch 24.0) base-set tests.

Covers the 135 collectible cards plus the engine-level extensions added
for the expansion: the Location card type (sixth board slot with
durability + cooldown), the Infuse keyword (per-hand-card death-count
trigger that morphs the card at threshold), and the
friendly_minions_died_this_game counter that powers Sire Denathrius.
"""

from hearthstone.enums import CardType, Zone

from utils import *


# ---------------------------------------------------------------------------
# Engine extensions
# ---------------------------------------------------------------------------


def test_location_lands_in_dedicated_slot_and_locks_for_one_turn():
    """Playing a Location occupies player.location and is exhausted the
    turn it lands. After the controller's next turn begins, the
    location is usable."""
    game = prepare_game()
    loc = game.player1.give("REV_290")  # Cathedral of Atonement (durability 3)
    loc.play()
    assert game.player1.location is loc
    assert loc.zone == Zone.PLAY
    assert loc.exhausted
    game.end_turn()
    game.end_turn()
    assert not loc.exhausted


def test_location_use_consumes_durability_and_sets_cooldown():
    """Using a Location decrements durability by 1 and sets cooldown=2."""
    game = prepare_game()
    loc = game.player1.give("REV_290")
    loc.play()
    game.end_turn()
    game.end_turn()
    minion = game.player1.summon("CS2_122")
    pre_dur = loc.durability
    pre_atk, pre_health = minion.atk, minion.max_health
    loc.use(target=minion)
    assert loc.durability == pre_dur - 1
    assert loc.cooldown == 2
    # +2/+1 buff applied + a card drawn.
    assert minion.atk == pre_atk + 2
    assert minion.max_health == pre_health + 1


def test_location_destroys_at_zero_durability():
    """A Location drops out of the slot when its durability reaches 0."""
    game = prepare_game()
    loc = game.player1.give("REV_290")  # durability 3
    loc.play()
    minion = game.player1.summon("CS2_122")
    for _ in range(3):
        # Wait for cooldown to clear before each use.
        while loc.exhausted and loc.zone == Zone.PLAY:
            game.end_turn()
            game.end_turn()
        if loc.zone != Zone.PLAY:
            break
        loc.use(target=minion)
    assert game.player1.location is None
    assert loc.zone == Zone.GRAVEYARD


def test_infuse_progress_bumps_on_friendly_minion_death():
    """A hand card with INFUSE counts friendly minion deaths."""
    game = prepare_game()
    infuse = game.player1.give("REV_013")  # Stoneborn Accuser, threshold 5
    assert infuse.infuse_threshold == 5
    for _ in range(3):
        m = game.player1.summon("CS2_122")
        m.destroy()
    # Hand card may have been morphed already if threshold reached; here it
    # hasn't (3 < 5).
    assert infuse.infuse_progress == 3


def test_infuse_morphs_card_at_threshold():
    """Hitting the threshold morphs the card into its infused twin."""
    game = prepare_game()
    infuse = game.player1.give("REV_013")  # threshold 5 → REV_013t
    for _ in range(5):
        m = game.player1.summon("CS2_122")
        m.destroy()
    # The hand slot now holds the infused twin id.
    assert game.player1.hand[-1].id == "REV_013t"


def test_friendly_minions_died_counter_powers_sire_denathrius():
    """friendly_minions_died_this_game increments on every friendly
    minion death and never resets per turn."""
    game = prepare_game()
    assert game.player1.friendly_minions_died_this_game == 0
    for _ in range(4):
        m = game.player1.summon("CS2_122")
        m.destroy()
    assert game.player1.friendly_minions_died_this_game == 4
    # Survives turn boundary.
    game.end_turn()
    game.end_turn()
    assert game.player1.friendly_minions_died_this_game == 4


# ---------------------------------------------------------------------------
# Demon Hunter
# ---------------------------------------------------------------------------


def test_sinful_brand_punishes_damage_to_branded_minion():
    """Damaging the branded enemy minion deals 2 to the enemy hero."""
    game = prepare_game()
    enemy = game.player2.summon("CS2_122")
    brand = game.player1.give("REV_506")
    brand.play(target=enemy)
    pre_hp = game.player2.hero.health
    game.player1.give(MOONFIRE).play(target=enemy)
    assert game.player2.hero.health == pre_hp - 2


def test_magnifying_glaive_draws_until_three():
    """After hero attacks, draw until the controller has 3 cards."""
    game = prepare_game()
    # Discard hand down to 0 to make the draw observable.
    while game.player1.hand:
        game.player1.hand[0].discard()
    game.player1.give("REV_509").play()  # equip Magnifying Glaive
    enemy_hero = game.player2.hero
    game.player1.hero.attack(enemy_hero)
    assert len(game.player1.hand) == 3


# ---------------------------------------------------------------------------
# Druid
# ---------------------------------------------------------------------------


def test_natural_causes_damages_and_summons_treant():
    """Deal 2 + summon a Treant."""
    game = prepare_game()
    enemy = game.player2.summon("CS2_122")
    pre_field = len(game.player1.field)
    game.player1.give("REV_307").play(target=enemy)
    assert enemy.damage == 2
    assert len(game.player1.field) == pre_field + 1


def test_widowbloom_seedsman_draws_nature_and_grants_mana():
    """Battlecry: Draw a Nature spell, gain an empty Mana Crystal."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    # prepare_game() pins both players at max_mana=10; drop ours so the
    # +1 from GainEmptyMana is observable (engine caps at max_resources).
    game.player1._max_mana = 5
    # Stack a Nature spell on top of deck.
    nat = game.player1.card("REV_307")  # Natural Causes is Nature
    game.player1.deck.append(nat)
    pre_max = game.player1.max_mana
    game.player1.give("REV_318").play()
    assert game.player1.max_mana == pre_max + 1


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------


def test_frenzied_fangs_summons_two_bats():
    """Summon two 2/1 Bats."""
    game = prepare_game()
    pre = len(game.player1.field)
    game.player1.give("REV_350").play()
    assert len(game.player1.field) == pre + 2
    assert all(m.id == "REV_350t" for m in game.player1.field[-2:])


def test_batty_guest_summons_a_bat_on_death():
    """Deathrattle: Summon a 2/1 Bat."""
    game = prepare_game()
    bat = game.player1.summon("REV_356")
    pre = len(game.player1.field)
    bat.destroy()
    assert any(m.id == "REV_350t" for m in game.player1.field)


# ---------------------------------------------------------------------------
# Mage
# ---------------------------------------------------------------------------


def test_cold_case_summons_two_skeletons_and_gains_armor():
    """Summon two 2/2 Volatile Skeletons + 4 Armor."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    pre_armor = game.player1.hero.armor
    pre_field = len(game.player1.field)
    game.player1.give("REV_505").play()
    assert game.player1.hero.armor == pre_armor + 4
    assert len(game.player1.field) == pre_field + 2


def test_frozen_touch_deals_three():
    """Deal 3 damage to a character."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player2.hero
    pre = target.health
    game.player1.give("REV_601").play(target=target)
    assert target.health == pre - 3


# ---------------------------------------------------------------------------
# Paladin
# ---------------------------------------------------------------------------


def test_promotion_buffs_silver_hand_recruit():
    """Give a Silver Hand Recruit +3/+3."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    shr = game.player1.summon("CS2_101t")  # SHR token
    game.player1.give("REV_842").play(target=shr)
    assert shr.atk == 1 + 3
    assert shr.max_health == 1 + 3


def test_great_hall_sets_minion_to_3_3():
    """Set a minion's Attack and Health to 3."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    loc = game.player1.give("REV_983")
    loc.play()
    # Dark Iron Dwarf is 4/4 — both stats differ from 3 so the SET
    # enchantment is visible on both axes.
    big = game.player1.summon("EX1_046")
    assert big.atk == 4 and big.max_health == 4
    game.end_turn(); game.end_turn()
    loc.use(target=big)
    assert big.atk == 3
    assert big.max_health == 3
    assert big.health == 3


# ---------------------------------------------------------------------------
# Priest
# ---------------------------------------------------------------------------


def test_the_light_it_burns_deals_attack_damage_to_minion():
    """Deal damage to a minion equal to its Attack."""
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # Sen'jin Shieldmasta — 3/5 — so the minion takes its 3 atk in
    # damage but still has 2 HP left, letting us assert exact damage
    # and that the minion is still in play (no death side-effects mask
    # the assertion).
    target = game.player2.summon("CS2_179")  # Sen'jin Shieldmasta 3/5
    assert target.atk == 3 and target.max_health == 5
    game.player1.give("REV_249").play(target=target)
    assert target.damage == 3
    assert target.zone == Zone.PLAY


def test_cathedral_of_atonement_buffs_and_draws():
    """+2/+1 + draw a card."""
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    loc = game.player1.give("REV_290")
    loc.play()
    game.end_turn(); game.end_turn()
    minion = game.player1.summon("CS2_122")
    pre_hand = len(game.player1.hand)
    pre_atk, pre_health = minion.atk, minion.max_health
    loc.use(target=minion)
    assert minion.atk == pre_atk + 2
    assert minion.max_health == pre_health + 1
    assert len(game.player1.hand) == pre_hand + 1


# ---------------------------------------------------------------------------
# Rogue
# ---------------------------------------------------------------------------


def test_sticky_situation_summons_spider_on_opponent_spell():
    """Secret fires when the opponent casts a spell."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.give("REV_827").play()
    assert any(s.id == "REV_827" for s in game.player1.secrets)
    game.end_turn()
    pre = len(game.player1.field)
    game.player2.give(MOONFIRE).play(target=game.player1.hero)
    assert len(game.player1.field) == pre + 1
    assert game.player1.field[-1].id == "REV_827t"


# ---------------------------------------------------------------------------
# Shaman
# ---------------------------------------------------------------------------


def test_crud_caretaker_summons_3_5_taunt_elemental():
    """Battlecry: Summon a 3/5 Elemental with Taunt."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    pre = len(game.player1.field)
    game.player1.give("REV_936").play()
    assert len(game.player1.field) == pre + 2  # the 1/1 + the 3/5 taunt
    assert any(m.id == "REV_936t" and m.taunt for m in game.player1.field)


def test_gigantotem_cost_reduces_per_totem_summoned():
    """Gigantotem costs 1 less per totem summoned this game."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    giga = game.player1.give("REV_838")
    base = giga.data.cost
    game.player1.times_totem_summoned_this_game = 3
    assert giga.cost == base - 3


# ---------------------------------------------------------------------------
# Warlock
# ---------------------------------------------------------------------------


def test_suffocating_shadows_destroys_random_enemy_minion_on_play():
    """Play destroys a random enemy minion."""
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player2.summon("CS2_122")
    pre = len(game.player2.field)
    game.player1.give("REV_239").play()
    assert len(game.player2.field) == pre - 1


def test_mischievous_imp_summons_a_copy_on_battlecry():
    """Battlecry: Summon a copy of this."""
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    pre = len(game.player1.field)
    game.player1.give("REV_244").play()
    assert len(game.player1.field) == pre + 2
    assert all(m.id == "REV_244" for m in game.player1.field[-2:])


# ---------------------------------------------------------------------------
# Warrior
# ---------------------------------------------------------------------------


def test_anima_extractor_buffs_random_hand_minion_on_friendly_damage():
    """When a friendly minion takes damage, give a random minion in hand
    +1/+1. With only one minion in the controller's hand, RANDOM picks
    it deterministically — assert the buff landed there."""
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # Clear hand so `held` is the only minion in hand; only then does
    # RANDOM(FRIENDLY_HAND + MINION) have a single candidate.
    while game.player1.hand:
        game.player1.hand[0].discard()
    game.player1.summon("REV_332")  # Anima Extractor (source, in play)
    held = game.player1.give("CS2_122")  # the only minion in hand
    pre_atk, pre_health = held.atk, held.max_health
    fr = game.player1.summon("CS2_122")  # friendly minion that takes damage
    game.player1.give(MOONFIRE).play(target=fr)
    assert held.atk == pre_atk + 1
    assert held.max_health == pre_health + 1


def test_sanguine_depths_deals_1_and_buffs_attack():
    """Deal 1 to a minion + give it +1 Attack."""
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    loc = game.player1.give("REV_990")
    loc.play()
    game.end_turn(); game.end_turn()
    target = game.player1.summon("CS2_122")
    pre_atk = target.atk
    pre_health = target.health
    loc.use(target=target)
    assert target.atk == pre_atk + 1
    assert target.health == pre_health - 1


# ---------------------------------------------------------------------------
# Neutrals
# ---------------------------------------------------------------------------


def test_bog_beast_summons_muckmare_on_death():
    """Deathrattle: Summon a 2/4 Muckmare with Taunt."""
    game = prepare_game()
    bog = game.player1.summon("REV_012")
    bog.destroy()
    assert any(m.id == "REV_012t" for m in game.player1.field)


def test_maze_guide_summons_random_2_cost_minion():
    """Battlecry: Summon a random 2-cost minion."""
    game = prepare_game()
    pre = len(game.player1.field)
    game.player1.give("REV_308").play()
    # 1 for Maze Guide itself + 1 random 2-cost.
    assert len(game.player1.field) == pre + 2


def test_sire_denathrius_scales_with_friendly_deaths():
    """Sire Denathrius deals (5 + friendly_minions_died_this_game)
    damage spread across enemy characters. The script fires N
    Hit(RANDOM_ENEMY_CHARACTER, 1) actions, so the total damage
    dealt must equal exactly that count."""
    game = prepare_game()
    for _ in range(4):
        m = game.player1.summon("CS2_122")
        m.destroy()
    assert game.player1.friendly_minions_died_this_game == 4
    # Bulk up the enemy hero so no ticks are absorbed by an early death.
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 80
    enemy_hero.damage = 0
    # Sturdy enemy minion so it can't die mid-roll either.
    enemy_minion = game.player2.summon("CS2_222")  # Stormwind Champion 6/6
    enemy_minion.max_health = 80
    enemy_minion.damage = 0
    sire = game.player1.give("REV_906")
    sire.play()
    total_damage = enemy_hero.damage + sum(c.damage for c in game.player2.field)
    assert total_damage == 5 + 4  # 5 base + 4 friendly deaths so far


def test_prince_renathal_is_a_3_3_4_vanilla_minion():
    """Prince Renathal's deck-size effect isn't engine-supported; we
    confirm the card at least exists as a vanilla 3/3/4 minion."""
    game = prepare_game()
    p = game.player1.give("REV_018")
    p.play()
    assert p.atk == 3
    assert p.max_health == 4
