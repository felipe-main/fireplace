"""The Great Dark Beyond — WARLOCK collectible card tests.

Covers all 10 collectible Warlock cards:
  GDB_104 Felfire Thrusters, GDB_121 Foreboding Flame, GDB_122 Infernal Stratagem,
  GDB_123 Abduction Ray, GDB_124 Bad Omen, GDB_125 Healthstone, GDB_126 Black Hole,
  GDB_127 K'ara the Dark Star, GDB_128 Archimonde.
  (GDB_124t2 Felborne Overfiend token covered via Bad Omen.)
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards


# ---------------------------------------------------------------------------
# GDB_104 — Felfire Thrusters: Spellburst: Deal this minion's Attack damage to
# 2 random enemy minions. Starship Piece. (2/4)
# ---------------------------------------------------------------------------
def test_felfire_thrusters_spellburst_hits_two_enemy_minions():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    thruster = p1.summon("GDB_104")  # 2/4
    assert thruster.atk == 2
    # Exactly two enemy minions, each beefed so neither dies (so both take 2).
    e1 = p2.summon(WISP)
    e2 = p2.summon(WISP)
    for e in (e1, e2):
        e.max_health = 80
        e.damage = 0
    # Cast a spell to trigger Spellburst.
    spell = p1.give(MOONFIRE)
    spell.play(target=p1.hero)
    # With exactly two enemy minions, RANDOM(ENEMY_MINIONS)*2 hits both, 2 each.
    assert e1.damage == 2
    assert e2.damage == 2


def test_felfire_thrusters_is_starship_piece():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    thruster = game.player1.summon("GDB_104")
    assert thruster.has_spellburst
    assert thruster.data.tags.get(GameTag.STARSHIP_PIECE, 0)


# ---------------------------------------------------------------------------
# GDB_121 — Foreboding Flame: Battlecry: Demons that didn't start in your deck
# cost (1) less this game. (2/2/3)
# ---------------------------------------------------------------------------
def test_foreboding_flame_discounts_demons_not_from_deck():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # A Demon generated into hand (did NOT start in deck).
    demon = p1.give("EX1_598")  # Imp, 1-cost Demon
    assert Race.DEMON in demon.races
    base = demon.cost
    flame = p1.give("GDB_121")
    flame.play()
    assert p1.foreboding_flame == 1
    assert demon.cost == base - 1


def test_foreboding_flame_does_not_discount_non_demons():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    wisp = p1.give(WISP)  # not a Demon
    base = wisp.cost
    flame = p1.give("GDB_121")
    flame.play()
    assert wisp.cost == base


# ---------------------------------------------------------------------------
# GDB_122 — Infernal Stratagem: Give a minion +3/+3. If it's a Demon, your next
# one costs (2) less. (3 mana spell)
# ---------------------------------------------------------------------------
def test_infernal_stratagem_buffs_and_discounts_next_demon():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    target = p1.summon("EX1_598")  # Imp 1/1 Demon
    ba, bh = target.atk, target.max_health
    spell = p1.give("GDB_122")
    spell.play(target=target)
    assert target.atk == ba + 3
    assert target.max_health == bh + 3
    # Demon was buffed -> next Demon costs (2) less.
    assert p1.next_demon_discount == 2
    # Use a 4-cost Demon so the full -2 is visible (no clamp at 0).
    nextdemon = p1.give("AT_019")  # Dreadsteed, 4-cost Demon
    assert Race.DEMON in nextdemon.races
    assert nextdemon.cost == 4 - 2


def test_infernal_stratagem_non_demon_no_discount():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    target = p1.summon(WISP)  # 1/1, not a Demon
    ba, bh = target.atk, target.max_health
    spell = p1.give("GDB_122")
    spell.play(target=target)
    assert target.atk == ba + 3
    assert target.max_health == bh + 3
    assert p1.next_demon_discount == 0


# ---------------------------------------------------------------------------
# GDB_123 — Abduction Ray: Get a random Demon. Reduce its Cost by (2).
# Repeatable this turn. (2 mana spell)
# ---------------------------------------------------------------------------
def test_abduction_ray_gives_discounted_demon_and_repeats():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Clear hand so we can identify the generated cards.
    for c in list(p1.hand):
        c.discard()
    spell = p1.give("GDB_123")
    spell.play()
    # A random Demon minion was added to hand (the repeatable copy is a Spell).
    demons = [
        c for c in p1.hand
        if c.type == CardType.MINION and Race.DEMON in c.races
    ]
    assert len(demons) == 1
    demon = demons[0]
    # Its cost is reduced by 2 (GDB_123e, COST -2).
    assert any(b.id == "GDB_123e" for b in demon.buffs)
    assert demon.cost == max(0, demon.data.cost - 2)
    # A repeatable Echo copy of Abduction Ray is in hand (GIL_000 ghostly enchant;
    # it keeps its normal cost — "Repeatable this turn" just regenerates a copy).
    copies = [c for c in p1.hand if c.id == "GDB_123"]
    assert len(copies) == 1
    assert any(b.id == "GIL_000" for b in copies[0].buffs)
    assert copies[0].cost == copies[0].data.cost


# ---------------------------------------------------------------------------
# GDB_124 — Bad Omen: In 2 turns, summon two 6/6 Demons with Taunt. If you're
# building a Starship, summon them now. (6 mana spell)
# ---------------------------------------------------------------------------
def test_bad_omen_countdown_summons_after_two_turns():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    assert not p1.is_building_starship
    spell = p1.give("GDB_124")
    spell.play()
    # Not building a Starship: a countdown enchant lands on the hero, no demons yet.
    assert not [m for m in p1.field if m.id == "GDB_124t2"]
    assert any(b.id == "GDB_124countdown" for b in p1.hero.buffs)
    # Tick 1 (start of p1's next turn): still nothing.
    game.end_turn()
    game.end_turn()
    assert not [m for m in p1.field if m.id == "GDB_124t2"]
    # Tick 2: two 6/6 Taunt Demons summon.
    game.end_turn()
    game.end_turn()
    demons = [m for m in p1.field if m.id == "GDB_124t2"]
    assert len(demons) == 2
    for d in demons:
        assert (d.atk, d.max_health) == (6, 6)
        assert d.taunt
        assert Race.DEMON in d.races


def test_bad_omen_summons_now_when_building_starship():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Build a Starship by banking a piece on death.
    p1.summon("GDB_100").destroy()  # The Exile's Hope neutral piece
    game.process_deaths()
    assert p1.is_building_starship
    spell = p1.give("GDB_124")
    spell.play()
    # Building a Starship: the two demons summon immediately.
    demons = [m for m in p1.field if m.id == "GDB_124t2"]
    assert len(demons) == 2
    for d in demons:
        assert (d.atk, d.max_health) == (6, 6)
        assert d.taunt
    # No countdown enchant was added.
    assert not any(b.id == "GDB_124countdown" for b in p1.hero.buffs)


def test_felborne_overfiend_token_stats():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    d = game.player1.summon("GDB_124t2")
    assert (d.atk, d.max_health) == (6, 6)
    assert d.taunt
    assert Race.DEMON in d.races


# ---------------------------------------------------------------------------
# GDB_125 — Healthstone: Tradeable. Restore all damage your hero has taken this
# turn. (0 mana spell)
# ---------------------------------------------------------------------------
def test_healthstone_restores_damage_taken_this_turn():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    game.queue_actions(p1.hero, [Hit(p1.hero, 6)])
    assert p1.hero.damage == 6
    assert p1.hero_damage_taken_this_turn == 6
    stone = p1.give("GDB_125")
    stone.play()
    # All 6 damage restored.
    assert p1.hero.damage == 0


def test_healthstone_no_damage_no_heal():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 4  # pre-existing damage from a PREVIOUS turn
    p1.hero_damage_taken_this_turn = 0  # but none taken this turn
    stone = p1.give("GDB_125")
    stone.play()
    # Only this-turn damage is restored; prior damage stays.
    assert p1.hero.damage == 4


# ---------------------------------------------------------------------------
# GDB_126 — Black Hole: Destroy all minions except Demons. (8 mana spell)
# ---------------------------------------------------------------------------
def test_black_hole_destroys_non_demons_only():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    demon1 = p1.summon("EX1_598")   # Imp, Demon (friendly)
    nondemon1 = p1.summon(WISP)     # not a Demon (friendly)
    demon2 = p2.summon("EX1_598")   # Demon (enemy)
    nondemon2 = p2.summon(WISP)     # not a Demon (enemy)
    spell = p1.give("GDB_126")
    spell.play()
    game.process_deaths()
    assert demon1.zone == Zone.PLAY
    assert demon2.zone == Zone.PLAY
    assert nondemon1.zone == Zone.GRAVEYARD
    assert nondemon2.zone == Zone.GRAVEYARD


# ---------------------------------------------------------------------------
# GDB_127 — K'ara, the Dark Star: Spellburst: Steal 2 Health from a random
# enemy. (3/3/3)
# ---------------------------------------------------------------------------
def test_kara_spellburst_steals_two_health():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 0
    kara = p1.summon("GDB_127")
    # Exactly one enemy minion so the random pick is deterministic.
    victim = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    vmax = victim.max_health
    spell = p1.give(MOONFIRE)
    spell.play(target=p1.hero)
    # Victim loses 2 max Health; hero gains 2 max Health.
    assert victim.max_health == vmax - 2
    assert p1.hero.max_health == 30 + 2


def test_kara_spellburst_no_enemy_minion_noop():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    p1.summon("GDB_127")
    # No enemy minions -> ENEMY_MINIONS empty -> hero max Health unchanged.
    spell = p1.give(MOONFIRE)
    spell.play(target=p1.hero)
    assert p1.hero.max_health == 30


def test_kara_shadow_spell_does_not_remove_spellburst():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 0
    kara = p1.summon("GDB_127")
    assert kara.has_spellburst
    v1 = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    # A SHADOW spell (Mind Blast) fires the steal AND keeps the Spellburst.
    shadow = p1.give("DS1_233")
    assert int(shadow.spell_school) == 6  # SpellSchool.SHADOW
    shadow.play()
    assert v1.max_health == 2 - 2  # steal happened
    assert kara.has_spellburst  # re-armed: Shadow spell didn't remove it
    # A non-Shadow spell now consumes the Spellburst as normal.
    p2.summon(GOLDSHIRE_FOOTMAN)
    p1.give(MOONFIRE).play(target=p1.hero)
    assert kara.has_spellburst is False


# ---------------------------------------------------------------------------
# GDB_128 — Archimonde: Battlecry: Summon every Demon you played this game that
# didn't start in your deck. (7/7/7)
# ---------------------------------------------------------------------------
def test_archimonde_resummons_played_demons_not_from_deck():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Play a Demon from hand (it didn't start in deck since hand was hand-given).
    imp = p1.give("EX1_598")  # Imp, Demon
    imp.play()
    assert imp in p1.cards_played_this_game
    assert not getattr(imp, "_started_in_deck", False)
    # Clear the board so we can count the resummon precisely.
    imp.destroy()
    game.process_deaths()
    arch = p1.give("GDB_128")
    arch.play()
    # Archimonde resummons one copy of the Imp.
    imps = [m for m in p1.field if m.id == "EX1_598"]
    assert len(imps) == 1


def test_archimonde_ignores_demons_that_started_in_deck():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # A Demon that DID start in deck: simulate by playing one then marking it.
    imp = p1.give("EX1_598")
    imp._started_in_deck = True
    imp.play()
    imp.destroy()
    game.process_deaths()
    arch = p1.give("GDB_128")
    arch.play()
    # No deck-origin Demon is resummoned.
    assert not [m for m in p1.field if m.id == "EX1_598"]


# SC_019 — Ultralisk Cavern (Location): Deal 1 damage to all enemies.
# Deathrattle: Summon an 8/8 Ultralisk with Rush.
def test_ultralisk_cavern_activate_hits_all_enemies():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    enemy_minion = p2.summon(TARGET_DUMMY)
    enemy_minion.max_health = 80
    enemy_minion._max_health = 80
    loc = p1.give("SC_019")
    loc.play()
    assert loc.type == CardType.LOCATION
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    # Deal 1 to every enemy: hero and minion.
    assert p2.hero.damage == 1
    assert enemy_minion.damage == 1


def test_ultralisk_cavern_deathrattle_summons_ultralisk():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    loc = p1.give("SC_019")
    loc.play()
    # Drain its durability so destroying it fires the deathrattle.
    loc.destroy()
    game.process_deaths()
    ultras = [m for m in p1.field if m.id == "SC_006"]
    assert len(ultras) == 1
    ultra = ultras[0]
    assert (ultra.atk, ultra.max_health) == (8, 8)
    assert ultra.rush


# SC_020 — Consume: Remove 1 Durability from a friendly location to restore 8
# Health to your hero.
def test_consume_removes_durability_and_heals_8():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 80
    p1.hero._max_health = 80
    p1.hero.damage = 20
    loc = p1.give("SC_019")
    loc.play()
    dur_before = loc.durability
    spell = p1.give("SC_020")
    spell.play()
    # One durability removed; hero restored by 8 (20 -> 12 damage).
    assert loc.durability == dur_before - 1
    assert p1.hero.damage == 12


def test_consume_unplayable_without_a_friendly_location():
    # The printed REQ_FRIENDLY_LOCATION gate: with no friendly Location in play
    # the spell is NOT playable (can't be wasted to no effect).
    from fireplace.exceptions import InvalidAction
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 80
    p1.hero._max_health = 80
    p1.hero.damage = 20
    spell = p1.give("SC_020")
    assert not spell.is_playable()
    with pytest.raises(InvalidAction):
        spell.play()
    assert p1.hero.damage == 20  # nothing happened
    # Once a Location is in play, it becomes playable.
    p1.give("SC_019").play()
    assert spell.is_playable()


# SC_023 — Spine Crawler: Taunt. Can't attack. Has +3 Attack if you control a
# location.
def test_spine_crawler_gains_attack_with_location():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    crawler = p1.summon("SC_023")  # 1/6 Taunt, can't attack
    assert crawler.taunt
    assert crawler.cant_attack
    # No location yet -> base 1 Attack.
    assert crawler.atk == 1
    loc = p1.give("SC_019")
    loc.play()
    # Controlling a location -> +3 Attack = 4.
    assert crawler.atk == 4


def test_spine_crawler_loses_attack_when_location_gone():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    crawler = p1.summon("SC_023")
    loc = p1.give("SC_019")
    loc.play()
    assert crawler.atk == 4
    loc.destroy()
    game.process_deaths()
    # Location gone -> back to base 1 Attack.
    assert crawler.atk == 1
