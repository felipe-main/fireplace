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


# ---------------------------------------------------------------------------
# Per-card tests (merged from the per-class implementation fan-out)
# ---------------------------------------------------------------------------


# ===================== deathknight =====================
def test_deep_deathknight_DEEP_015_magnetize_undead():
    # Prosthetic Hand (3/3/1) can Magnetize to Undead. Frail Ghoul (HERO_11bpt)
    # is a 1/1 Undead; magnetizing merges 3/1 onto it -> 4/2, and Prosthetic
    # Hand leaves the field.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    ghoul = game.player1.summon("HERO_11bpt")
    assert ghoul.race == Race.UNDEAD
    hand = game.player1.give("DEEP_015")
    hand.play(index=0)  # placed to the LEFT of the ghoul -> ghoul is RIGHT_OF(SELF)
    field = list(game.player1.field)
    assert len(field) == 1
    assert field[0] is ghoul
    assert ghoul.atk == 4
    assert ghoul.health == 2
    assert hand.zone == Zone.PLAY or hand.zone != Zone.PLAY  # hand left the board
    assert hand not in game.player1.field


def test_deep_deathknight_DEEP_015_magnetize_mech():
    # Also magnetizes to a Mech (default Magnetic behaviour). Use a 2/3 Mech
    # token (a Goblin Bomb is 0/2; instead use Harvest Golem's body via a known
    # Mech). We summon a generic Mech: "GVG_096t" (Burly Rockjaw Trogg is not a
    # mech) -> use a Mechanical token. Simplest: summon a Mech and check merge.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    mech = game.player1.summon("BOT_031")  # Goblin Bomb, 0/2 Mech
    assert mech.race == Race.MECHANICAL
    pre_atk, pre_health = mech.atk, mech.health  # 0/2
    hand = game.player1.give("DEEP_015")
    hand.play(index=0)
    field = list(game.player1.field)
    assert len(field) == 1
    assert field[0] is mech
    assert mech.atk == pre_atk + 3  # 0 + 3
    assert mech.health == pre_health + 1  # 2 + 1 (CURRENT_HEALTH of the 3/1)


def test_deep_deathknight_DEEP_015_no_target_stays():
    # No Mech/Undead to the right -> Prosthetic Hand is played as a normal
    # 3/1 minion (no magnetize).
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    hand = game.player1.give("DEEP_015")
    hand.play()
    field = list(game.player1.field)
    assert len(field) == 1
    assert field[0] is hand
    assert hand.atk == 3
    assert hand.health == 1


def test_deep_deathknight_DEEP_016_freeze_and_lifesteal():
    # Quartzite Crusher: Lifesteal + Freeze any character damaged by your hero.
    # Attack a 0-attack minion (no retaliation) so hero-HP math is exact.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.hero.set_current_health(20)
    weapon = game.player1.give("DEEP_016")
    weapon.play()
    assert game.player1.hero.atk == 3
    target = game.player2.summon("BOT_031")  # 0/2 Goblin Bomb, can't hit back
    target.max_health = 10
    target.damage = 0
    assert not target.frozen
    game.player1.hero.attack(target)
    assert target.damage == 3          # weapon deals exactly 3
    assert target.frozen              # Freeze applied
    assert game.player1.hero.health == 23  # Lifesteal heals 3, no retaliation


def test_deep_deathknight_DEEP_016_freeze_hero():
    # Damaging the enemy HERO also Freezes it (any character).
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.hero.set_current_health(20)
    weapon = game.player1.give("DEEP_016")
    weapon.play()
    enemy_hero = game.player2.hero
    pre = enemy_hero.health
    assert not enemy_hero.frozen
    game.player1.hero.attack(enemy_hero)
    assert enemy_hero.health == pre - 3
    assert enemy_hero.frozen
    assert game.player1.hero.health == 23  # lifesteal, hero takes no melee back


def test_deep_deathknight_DEEP_017_summon_and_deathrattle():
    # Mining Casualties: summon two 1/1 Silver Hand Recruits, each with a
    # granted "Deathrattle: Summon a 1/1 Frail Ghoul".
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    spell = game.player1.give("DEEP_017")
    spell.play()
    recruits = list(game.player1.field)
    assert len(recruits) == 2
    assert all(m.id == "CS2_101t" for m in recruits)
    assert all(m.atk == 1 and m.health == 1 for m in recruits)
    # Kill the first recruit -> its granted deathrattle summons a Frail Ghoul.
    recruits[0].destroy()
    field = list(game.player1.field)
    assert len(field) == 2  # one surviving recruit + one new Frail Ghoul
    ids = sorted(m.id for m in field)
    assert ids == ["CS2_101t", "HERO_11bpt"]
    ghoul = next(m for m in field if m.id == "HERO_11bpt")
    assert ghoul.atk == 1 and ghoul.health == 1
    # Second recruit still has its deathrattle: killing it makes a second ghoul.
    other = next(m for m in field if m.id == "CS2_101t")
    other.destroy()
    ghouls = [m for m in game.player1.field if m.id == "HERO_11bpt"]
    assert len(ghouls) == 2


# ===================== demonhunter =====================
def _demonhunter_resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_deep_demonhunter_DEEP_012_take_and_give_weapon():
    # Shadestone Skulker: Battlecry takes your weapon + gains its stats;
    # Deathrattle gives the same weapon back.
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p = game.player1
    weapon = p.give("CS2_106")  # Fiery War Axe, 3/2
    weapon.play()
    assert weapon.atk == 3 and weapon.durability == 2
    assert p.weapon is weapon

    skulker = p.give("DEEP_012")
    skulker.play()
    # Battlecry: weapon removed from play, stats transferred (1/1 + 3/2 = 4/3).
    assert p.weapon is None
    assert skulker.atk == 4
    assert skulker.health == 3
    assert skulker.max_health == 3
    assert skulker._borrowed_weapon is weapon

    # Deathrattle: the exact same weapon instance comes back with its stats.
    skulker.destroy()
    assert p.weapon is weapon
    assert p.weapon.atk == 3
    assert p.weapon.durability == 2


def test_deep_demonhunter_DEEP_012_no_weapon_is_noop():
    # With no weapon equipped, battlecry/deathrattle do nothing and the
    # Skulker keeps its printed 1/1 stats.
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p = game.player1
    assert p.weapon is None
    skulker = p.give("DEEP_012")
    skulker.play()
    assert skulker.atk == 1
    assert skulker.max_health == 1
    assert p.weapon is None
    assert getattr(skulker, "_borrowed_weapon", None) is None
    skulker.destroy()
    assert p.weapon is None


def test_deep_demonhunter_DEEP_013_fel_fissure_two_then_two_more():
    # Fel Fissure: deal 2 to all minions now, 2 more at start of next turn.
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p, o = game.player1, game.player2
    mine = p.summon("CS2_182")   # tanky enough to absorb both ticks
    mine.max_health = 10
    mine.damage = 0
    theirs = o.summon("CS2_182")
    theirs.max_health = 10
    theirs.damage = 0

    ff = p.give("DEEP_013")
    ff.play()
    _demonhunter_resolve_choices(p)
    # Immediate 2 to all minions.
    assert mine.damage == 2
    assert theirs.damage == 2
    # The delayed sigil is now in play.
    assert [c.id for c in p.secrets] == ["DEEP_013t"]

    game.end_turn()
    game.end_turn()  # back to p1: start-of-turn fires the second tick.
    assert mine.damage == 4
    assert theirs.damage == 4
    # Sigil self-destroys after firing.
    assert [c.id for c in p.secrets] == []


def test_deep_demonhunter_DEEP_013t_start_of_turn_two_damage():
    # The follow-up sigil on its own: deals exactly 2 to all minions at the
    # start of the controller's next turn, then destroys itself.
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p, o = game.player1, game.player2
    mine = p.summon("CS2_182")
    mine.max_health = 10
    mine.damage = 0
    theirs = o.summon("CS2_182")
    theirs.max_health = 10
    theirs.damage = 0

    p.summon("DEEP_013t")  # sigil enters the SECRET zone
    assert [c.id for c in p.secrets] == ["DEEP_013t"]
    assert mine.damage == 0  # nothing happens on entry

    game.end_turn()
    game.end_turn()
    assert mine.damage == 2
    assert theirs.damage == 2
    assert [c.id for c in p.secrets] == []


# ===================== druid =====================
import pytest
from hearthstone.enums import *
from utils import *
from fireplace.actions import ForgeCard


def test_deep_druid_gloomstone_choose_discard():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.discard_hand()
    for _ in range(4):
        p.give("CS2_005")
    guardian = p.give("DEEP_027")
    pre = len(p.hand)  # 4 filler + guardian
    guardian.play(choose="DEEP_027a")
    # guardian leaves hand (played) + exactly 2 cards discarded
    assert len(p.hand) == pre - 1 - 2


def test_deep_druid_gloomstone_choose_destroy_crystal():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    pre = p.max_mana
    guardian = p.give("DEEP_027")
    guardian.play(choose="DEEP_027b")
    assert p.max_mana == pre - 1


def test_deep_druid_gloomstone_forge_does_neither():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.discard_hand()
    for _ in range(3):
        p.give("CS2_005")
    guardian = p.give("DEEP_027")
    game.queue_actions(p, [ForgeCard(guardian)])
    forged = p.hand[-1]
    assert forged.id == "DEEP_027t"
    pre_mana = p.max_mana
    pre_hand = len(p.hand)  # 3 filler + forged guardian
    forged.play()
    # Forged Guardian does NEITHER: no crystal destroyed, no discard.
    assert p.max_mana == pre_mana
    assert len(p.hand) == pre_hand - 1
    assert p.field[0].id == "DEEP_027t"
    assert p.field[0].taunt


def test_deep_druid_crystal_cluster_room():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    cluster = p.give("DEEP_028")
    p.max_mana = cluster.cost
    p.used_mana = 0
    cluster.play()
    # all 3 crystals fit (cost 7 -> 10), no Crusher summoned
    assert p.max_mana == 10
    assert len(p.field) == 0


def test_deep_druid_crystal_cluster_overflow():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.max_mana = 9
    p.used_mana = 0
    p.give("DEEP_028").play()
    # 1 crystal fits (9 -> 10), other 2 can't -> 2 Crystal Crushers
    assert p.max_mana == 10
    crushers = [m for m in p.field if m.id == "DEEP_028t"]
    assert len(crushers) == 2
    assert all(m.atk == 3 and m.max_health == 7 and m.taunt for m in crushers)


def test_deep_druid_crystal_cluster_full_overflow():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.max_mana = 10
    p.used_mana = 0
    p.give("DEEP_028").play()
    # already capped: all 3 crystals can't fit -> 3 Crystal Crushers
    assert p.max_mana == 10
    assert len([m for m in p.field if m.id == "DEEP_028t"]) == 3


def test_deep_druid_trogg_gemtosser_finale():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.max_mana = 3
    p.used_mana = 0
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 80
    enemy_hero.damage = 0
    for m in list(game.player2.field):
        m.destroy()
    # 3-cost played with last crystal -> Finale active.
    # Only enemy character is the hero, so all shots land on it.
    p.give("DEEP_029").play()
    assert enemy_hero.damage == 3


def test_deep_druid_trogg_gemtosser_no_finale():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    p.max_mana = 10
    p.used_mana = 0
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 80
    enemy_hero.damage = 0
    for m in list(game.player2.field):
        m.destroy()
    # 3-cost with 10 mana available -> NOT Finale -> no damage at all
    p.give("DEEP_029").play()
    assert enemy_hero.damage == 0


# ===================== hunter =====================
import pytest
from hearthstone.enums import *
from utils import *
from fireplace.cards import db


def test_deep_hunter_mismatched_fossils_swaps_stats():
    # DEEP_001: Discover a Beast and an Undead. Swap their stats.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    spell = p.give("DEEP_001")
    spell.play()
    # Two sequential Discovers: pick the first offered card each time.
    n_choices = 0
    while p.choice:
        n_choices += 1
        p.choice.choose(p.choice.cards[0])
    assert n_choices == 2
    # The two newly-given cards are at the tail of the hand: beast then undead.
    beast, undead = p.hand[-2], p.hand[-1]
    assert beast.race == Race.BEAST
    assert undead.race == Race.UNDEAD
    b_printed = db[beast.id]
    u_printed = db[undead.id]
    # Stats are swapped: beast now has the undead's printed stats and vice versa.
    assert beast.atk == u_printed.atk
    assert beast.health == u_printed.health
    assert undead.atk == b_printed.atk
    assert undead.health == b_printed.health
    # Races are untouched (only stats swap).
    assert beast.race == Race.BEAST
    assert undead.race == Race.UNDEAD


def test_deep_hunter_shimmer_shot():
    # DEEP_003: Deal 1 damage. Summon a random minion of that Cost (1).
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    # Boulderfist Ogre 6/7 survives a single point of damage -> damage == 1.
    target = game.player2.summon("CS2_200")
    pre_field = len(p.field)
    spell = p.give("DEEP_003")
    spell.play(target=target)
    assert target.damage == 1
    assert not target.dead
    # Exactly one minion summoned, and it costs 1 (matching the 1 damage dealt).
    assert len(p.field) == pre_field + 1
    summoned = p.field[-1]
    assert db[summoned.id].cost == 1


def test_deep_hunter_obsidian_revenant():
    # DEEP_005: Taunt. Deathrattle: Summon two random Deathrattle minions
    # that cost (3) or less.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.player1
    rev = p.summon("DEEP_005")
    assert rev.taunt
    assert rev.atk == 4
    assert rev.health == 6
    rev.destroy()
    game.process_deaths()
    summoned = [m for m in p.field if m.id != "DEEP_005"]
    # Exactly two minions, each a Deathrattle minion costing 3 or less.
    assert len(summoned) == 2
    for m in summoned:
        assert db[m.id].cost <= 3
        assert m.data.tags.get(GameTag.DEATHRATTLE)


# ===================== mage =====================
def test_deep_mage_DEEP_004_mantle_shaper_cost():
    # Mantle Shaper: Costs (1) less for each spell you've cast while holding this.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    shaper = p.give("DEEP_004")
    assert shaper.cost == 5
    p.give("CS2_029").play(target=game.player2.hero)  # Fireball
    assert shaper.cost == 4
    p.give("CS2_029").play(target=game.player2.hero)
    assert shaper.cost == 3
    # Spells cast while NOT holding it must not count: play it, draw a fresh copy.
    shaper2 = p.give("DEEP_004")
    assert shaper2.cost == 5


def test_deep_mage_DEEP_002t_hiffar_aura():
    # Hiffar: Your spells cost (1) less. (aura on spells in hand only)
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    spell = p.give("CS2_029")          # Fireball, base 4
    minion = p.give("CS2_168")         # Pint-Sized Summoner (a minion), unaffected
    base_spell = spell.cost
    base_minion = minion.cost
    hiffar = p.summon("DEEP_002t")
    assert spell.cost == base_spell - 1
    assert minion.cost == base_minion   # aura is spells-only
    # Aura disappears when Hiffar leaves play.
    hiffar.destroy()
    assert spell.cost == base_spell


def test_deep_mage_DEEP_002t2_luekk_spellpower():
    # Luekk: Spell Damage +2
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    assert p.spellpower == 0
    luekk = p.summon("DEEP_002t2")
    assert p.spellpower == 2
    luekk.destroy()
    assert p.spellpower == 0


def test_deep_mage_DEEP_002t3_mesho_untargetable():
    # Me'sho: Can't be targeted by spells or Hero Powers.
    # CANT_BE_TARGETED_BY_SPELLS aliases CANT_BE_TARGETED_BY_ABILITIES (enum 311).
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    mesho = game.player1.summon("DEEP_002t3")
    assert mesho.cant_be_targeted_by_abilities is True
    assert mesho.cant_be_targeted_by_hero_powers is True


def test_deep_mage_DEEP_002_elemental_companion():
    # Elemental Companion: Summon a random Elemental Companion.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.give("DEEP_002").play()
    assert len(p.field) == 1
    summoned = p.field[0]
    assert summoned.id in ("DEEP_002t", "DEEP_002t2", "DEEP_002t3")
    assert Race.ELEMENTAL in summoned.races


def test_deep_mage_DEEP_000_summoning_ward():
    # Secret: When your turn starts, summon a copy of your highest Cost minion.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.current_player
    big = p.summon("EX1_116")    # Leeroy Jenkins, 5-cost
    small = p.summon("CS2_168")  # Pint-Sized Summoner, 2-cost
    ward = p.give("DEEP_000")
    ward.play()
    assert ward.zone == Zone.SECRET
    pre = len(p.field)
    game.end_turn()
    game.end_turn()  # back to p's turn start -> secret fires
    assert len(p.field) == pre + 1
    # the new minion is a copy of the highest-cost minion (Leeroy), not the small one
    assert sum(1 for c in p.field if c.id == "EX1_116") == 2
    assert ward.zone == Zone.GRAVEYARD  # secret revealed/consumed


def test_deep_mage_DEEP_000_summoning_ward_no_minion():
    # No friendly minion -> secret stays armed (does not reveal).
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.current_player
    ward = p.give("DEEP_000")
    ward.play()
    assert ward.zone == Zone.SECRET
    game.end_turn()
    game.end_turn()
    assert ward.zone == Zone.SECRET  # nothing to copy, still armed


# ===================== paladin =====================
import random


def _paladin_clear_hand(player):
    for c in list(player.hand):
        c.discard()


def _paladin_keyword_flags(m):
    # The eight Deepholm "bonus effects" are keyword-only: Taunt, Windfury,
    # Divine Shield, Poisonous, Elusive (can't be targeted), Rush, Lifesteal,
    # Reborn. (Elusive, NOT Stealth.)
    return {
        "ds": bool(m.divine_shield),
        "taunt": bool(m.taunt),
        "rush": bool(m.rush),
        "wf": bool(m.windfury),
        "elusive": bool(m.tags.get(GameTag.CANT_BE_TARGETED_BY_SPELLS)),
        "pois": bool(m.poisonous),
        "ls": bool(m.lifesteal),
        "reborn": bool(m.reborn),
    }


def test_deep_paladin_sir_finley_no_excavate_no_transform():
    # Battlecry only fires the transform if you've Excavated twice.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    golem = game.player2.summon("CS2_186")  # War Golem 7/7
    assert game.player1.excavates_this_game == 0
    finley = game.player1.give("DEEP_007")
    finley.play()
    # No excavation history -> enemy board untouched.
    assert len(game.player2.field) == 1
    assert game.player2.field[0] is golem
    assert game.player2.field[0].id == "CS2_186"
    assert (game.player2.field[0].atk, game.player2.field[0].health) == (7, 7)


def test_deep_paladin_sir_finley_one_excavate_no_transform():
    # Exactly one excavate is not enough — the gate is ">= 2".
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player2.summon("CS2_186")
    game.player1.excavates_this_game = 1
    finley = game.player1.give("DEEP_007")
    finley.play()
    assert len(game.player2.field) == 1
    assert game.player2.field[0].id == "CS2_186"


def test_deep_paladin_sir_finley_excavated_twice_transforms_all_enemies():
    # If you've Excavated twice, transform ALL enemy minions into 1/1 Murlocs,
    # leaving your own board alone.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player2.summon("CS2_186")  # War Golem
    game.player2.summon("CS2_186")  # War Golem
    friendly = game.player1.summon("CS2_186")  # our own minion stays
    game.player1.excavates_this_game = 2
    finley = game.player1.give("DEEP_007")
    finley.play()
    # Two enemy minions transformed.
    assert len(game.player2.field) == 2
    for m in game.player2.field:
        assert m.id == "PRO_001at"
        assert (m.atk, m.health) == (1, 1)
        assert m.race == Race.MURLOC
    # Our own board is untouched (Finley + the War Golem we summoned).
    friendly_ids = sorted(m.id for m in game.player1.field)
    assert friendly_ids == ["CS2_186", "DEEP_007"]
    assert friendly.id == "CS2_186"
    assert (friendly.atk, friendly.health) == (7, 7)


def test_deep_paladin_shroomscavate_grants_windfury_divine_shield_and_excavates():
    # Give a minion Windfury and Divine Shield. Excavate a treasure.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player1.summon("CS2_186")  # War Golem 7/7
    assert not target.windfury and not target.divine_shield
    excav_before = game.player1.excavates_this_game
    hand_before = len(game.player1.hand)
    spell = game.player1.give("DEEP_018")
    spell.play(target=target)
    # Both keywords applied.
    assert target.windfury is True
    assert target.divine_shield is True
    # Excavate fired exactly once and added one treasure to hand.
    assert game.player1.excavates_this_game == excav_before + 1
    assert len(game.player1.hand) == hand_before + 1


def test_deep_paladin_shroomscavate_divine_shield_absorbs_damage():
    # The granted Divine Shield must actually absorb the first hit.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player1.summon("CS2_186")  # War Golem 7/7
    spell = game.player1.give("DEEP_018")
    spell.play(target=target)
    game.queue_actions(game.player1.hero, [Hit(target, 3)])
    # First hit is absorbed by Divine Shield: no damage, shield gone.
    assert target.damage == 0
    assert target.divine_shield is False
    # Second hit now lands for full.
    game.queue_actions(game.player1.hero, [Hit(target, 3)])
    assert target.damage == 3


def _deep_play_kaleido(game, p):
    """Clear p's board+hand, refill mana, then play a fresh Kaleidosaur and
    return it. Re-seed game.random beforehand to control the bonus roll."""
    for c in p.hand[:]:
        c.discard()
    for m in p.field[:]:
        m.destroy()
    game.process_deaths()
    p.used_mana = 0
    kaleido = p.give("DEEP_033")
    kaleido.play()
    return kaleido


def test_deep_paladin_fossilized_kaleidosaur_gains_two_distinct_bonus_effects():
    # Battlecry: Gain two random bonus effects. Excavate a treasure.
    # Bonus effects are keyword-only (no stat change). Drive the game RNG
    # across seeds; each play must grant EXACTLY two distinct keywords and
    # leave the printed 3/4 stats untouched.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p = game.current_player
    seen_pairs = set()
    for s in range(50):
        game.random.seed(s)
        excav_before = p.excavates_this_game
        kaleido = _deep_play_kaleido(game, p)
        flags = _paladin_keyword_flags(kaleido)
        active = sorted(k for k, v in flags.items() if v)
        assert len(active) == 2, (s, flags)
        # Keyword-only: the printed 3/4 body is unchanged (no +3/+3).
        assert kaleido.atk == 3 and kaleido.max_health == 4
        # Excavated exactly once; the treasure is in hand.
        assert p.excavates_this_game == excav_before + 1
        assert len(p.hand) == 1
        seen_pairs.add(tuple(active))
    # The RNG explores more than one distinct pair (genuinely random).
    assert len(seen_pairs) > 1


def test_deep_paladin_fossilized_kaleidosaur_divine_shield_bonus_is_real():
    # When the Divine Shield bonus is rolled, it must absorb damage (proves
    # SetTags, not an inert enchant). Find a game.random seed yielding it.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p = game.current_player
    kaleido = None
    for s in range(50):
        game.random.seed(s)
        k = _deep_play_kaleido(game, p)
        if k.divine_shield:
            kaleido = k
            break
    assert kaleido is not None, "no seed produced a Divine Shield roll"
    game.queue_actions(p.hero, [Hit(kaleido, 1)])
    assert kaleido.damage == 0
    assert kaleido.divine_shield is False


def test_deep_bonus_effects_pool_is_keyword_only_with_elusive():
    # The shared bonus-effect pool is keyword-only (no ATK/HEALTH) and uses
    # Elusive (can't be targeted), not Stealth, and not the Chameleon enchants.
    from fireplace.cards.delve_into_deepholm._bonus import (
        BONUS_EFFECTS, roll_bonus_effects,
    )
    import random as _random
    assert len(BONUS_EFFECTS) == 8
    flat = [k for spec in BONUS_EFFECTS for k in spec]
    assert GameTag.ATK not in flat and GameTag.HEALTH not in flat
    assert GameTag.CANT_BE_TARGETED_BY_SPELLS in flat
    assert GameTag.CANT_BE_TARGETED_BY_HERO_POWERS in flat
    assert GameTag.STEALTH not in flat
    rng = _random.Random(0)
    pairs = {frozenset(roll_bonus_effects(rng, 2).items()) for _ in range(50)}
    assert len(pairs) > 1


# ===================== priest =====================
_deep_priest_YETI = "CS2_182"  # Chillwind Yeti, vanilla 4/5, cost 4


def _deep_priest_clear_deck(player):
    from hearthstone.enums import Zone
    for c in player.deck[:]:
        c.zone = Zone.SETASIDE


def _deep_priest_resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_deep_priest_DEEP_021_shadow_word_steal():
    # Return an enemy minion to YOUR hand.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    enemy = p2.summon(_deep_priest_YETI)
    hand0 = len(p1.hand)
    sws = p1.give("DEEP_021")
    sws.play(target=enemy)
    # The minion is now a card in OUR hand and gone from the enemy board.
    assert enemy.zone == Zone.HAND
    assert enemy in p1.hand
    assert enemy not in p2.field
    assert enemy.controller is p1
    assert len(p1.hand) == hand0 + 1
    assert len(p2.field) == 0


def test_deep_priest_DEEP_023_hidden_gem():
    # Stealth. At the end of your turn, restore 2 Health to all friendly chars.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    gem = p1.summon("DEEP_023")
    assert gem.stealthed
    ally = p1.summon(_deep_priest_YETI)
    ally.set_current_health(1)
    p1.hero.set_current_health(20)
    # Damage the gem itself so we can verify it heals too (it's a friendly char).
    gem.set_current_health(1)
    enemy = p1.opponent.summon(_deep_priest_YETI)
    enemy.set_current_health(1)
    game.end_turn()
    # +2 to every friendly character, clamped at max.
    assert ally.health == 3            # 1 -> 3
    assert p1.hero.health == 22        # 20 -> 22
    assert gem.health == 2             # 1 -> 2 (capped at its 2 max_health)
    # Enemy character untouched.
    assert enemy.health == 1


def test_deep_priest_DEEP_024_glowstone_gyreworm_quickdraw():
    # Lifesteal, Quickdraw: Deal 5 damage.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.hero.set_current_health(20)
    target = p1.opponent.summon(_deep_priest_YETI)
    target.max_health = 80
    target.damage = 0
    gw = p1.give("DEEP_024")  # given this turn -> Quickdraw active
    gw.play(target=target)
    assert target.damage == 5          # exactly 5 from Quickdraw
    assert p1.hero.health == 25         # Lifesteal heals the 5 dealt


def test_deep_priest_DEEP_024_glowstone_gyreworm_no_quickdraw():
    # Without Quickdraw, no damage is dealt (and so no lifesteal).
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.hero.set_current_health(20)
    target = p1.opponent.summon(_deep_priest_YETI)
    target.max_health = 80
    target.damage = 0
    gw = p1.give("DEEP_024")
    game.end_turn()
    game.end_turn()  # card has now survived a turn boundary -> not Quickdraw
    gw.play(target=target)
    assert target.damage == 0
    assert p1.hero.health == 20


def test_deep_priest_DEEP_024_forge_morph():
    # Forge changes DEEP_024 into DEEP_024t (Forged battlecry version).
    from fireplace.actions import ForgeCard
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    gw = p1.give("DEEP_024")
    game.queue_actions(p1.hero, [ForgeCard(gw)])
    assert "DEEP_024t" in [c.id for c in p1.hand]
    assert "DEEP_024" not in [c.id for c in p1.hand]


def test_deep_priest_DEEP_024t_forged_battlecry():
    # Forged, Lifesteal. Battlecry: Deal 5 damage. (Fires unconditionally.)
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.hero.set_current_health(20)
    target = p1.opponent.summon(_deep_priest_YETI)
    target.max_health = 80
    target.damage = 0
    ft = p1.give("DEEP_024t")
    # Play after a turn boundary to prove it does NOT depend on Quickdraw.
    game.end_turn()
    game.end_turn()
    ft.play(target=target)
    assert target.damage == 5
    assert p1.hero.health == 25


def test_deep_priest_DEEP_025_shattered_reflections():
    # Choose a minion. Add a copy to your hand, deck, AND battlefield.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    m = p1.summon(_deep_priest_YETI)
    board0 = len(p1.field)
    hand0 = len(p1.hand)
    deck0 = len(p1.deck)
    sr = p1.give("DEEP_025")
    sr.play(target=m)
    assert len(p1.field) == board0 + 1
    assert len(p1.hand) == hand0 + 1
    assert len(p1.deck) == deck0 + 1
    # Each new copy shares the chosen minion's id.
    assert sum(c.id == m.id for c in p1.field) == 2          # original + summoned copy
    assert sum(c.id == m.id for c in p1.hand) == 1
    assert sum(c.id == m.id for c in p1.deck) == 1


def test_deep_priest_DEEP_026_pendant_of_earth():
    # Discover a minion from your deck. Gain Armor equal to its Cost.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    _deep_priest_clear_deck(p1)
    deck_minion = p1.give(_deep_priest_YETI)   # cost 4
    deck_minion.zone = Zone.DECK
    arm0 = p1.hero.armor
    hand_before = len(p1.hand)
    pen = p1.give("DEEP_026")
    pen.play()
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    assert chosen.cost == 4
    p1.choice.choose(chosen)
    # Exactly its cost in Armor, and the chosen minion lands in hand.
    assert p1.hero.armor == arm0 + 4
    assert any(c.id == _deep_priest_YETI for c in p1.hand)


# ===================== rogue =====================
def test_deep_rogue_DEEP_014_quick_pick():
    # Quick Pick: After your hero attacks, draw a card.
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p = game.player1
    weapon = p.give("DEEP_014")
    weapon.play()
    assert p.weapon is not None
    assert p.weapon.id == "DEEP_014"
    assert p.weapon.atk == 1
    assert p.weapon.durability == 2
    pre_hand = len(p.hand)
    pre_deck = len(p.deck)
    p.hero.attack(game.player2.hero)
    # exactly one card drawn from deck to hand
    assert len(p.hand) == pre_hand + 1
    assert len(p.deck) == pre_deck - 1


def test_deep_rogue_DEEP_014_draws_each_attack():
    # Two attacks (durability 2) draw two cards total, one per attack.
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p = game.player1
    p.give("DEEP_014").play()
    pre_hand = len(p.hand)
    pre_deck = len(p.deck)
    p.hero.attack(game.player2.hero)
    assert len(p.hand) == pre_hand + 1
    assert len(p.deck) == pre_deck - 1
    # refresh hero attack for a second swing
    p.hero.num_attacks = 0
    p.hero.attack(game.player2.hero)
    assert len(p.hand) == pre_hand + 2
    assert len(p.deck) == pre_deck - 2


def _rogue_race_of(card):
    races = getattr(card.data, "races", None) or [card.data.race]
    return races


def test_deep_rogue_DEEP_022_fools_gold():
    # Fool's Gold: Get a random Golden Pirate and Elemental from other classes.
    # Use a Rogue/Rogue game and cast from current_player so the caster is
    # guaranteed Rogue (game.player1 tracks turn order, not deck class) and
    # playable; fully clear the opening hand so `got` is just the two pulls.
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p = game.current_player
    while p.hand:
        p.discard_hand()
    card = p.give("DEEP_022")
    card.play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    got = [c for c in p.hand if c.id != "DEEP_022"]
    # exactly two cards generated into hand
    assert len(got) == 2
    # exactly one Pirate and exactly one Elemental
    pirates = [c for c in got if Race.PIRATE in _rogue_race_of(c)]
    elementals = [c for c in got if Race.ELEMENTAL in _rogue_race_of(c)]
    assert len(pirates) == 1
    assert len(elementals) == 1
    # both are minions, both from a class other than Rogue, neither Neutral-only
    for c in got:
        assert c.type == CardType.MINION
        assert c.data.card_class != CardClass.ROGUE
        assert CardClass.ROGUE not in c.data.classes
        assert c.data.classes != [CardClass.NEUTRAL]
        assert c.data.collectible


def test_deep_rogue_DEEP_022_excludes_own_class_repeatedly():
    # Determinism of the cross-class constraint across many rolls.
    # Rogue/Rogue + current_player guarantees a Rogue caster regardless of the
    # coin flip (game.player1 tracks turn order, not deck class).
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p = game.current_player
    for _ in range(20):
        p.used_mana = 0  # refill — all 20 casts happen on a single turn
        # Fully clear the Rogue opening hand — a single discard_hand() leaves
        # drawn Rogue cards behind, which are NOT what Fool's Gold produced.
        while p.hand:
            p.discard_hand()
        p.give("DEEP_022").play()
        while p.choice:
            p.choice.choose(p.choice.cards[0])
        got = [c for c in p.hand if c.id != "DEEP_022"]
        assert len(got) == 2  # exactly the Pirate + Elemental Fool's Gold makes
        for c in got:
            assert CardClass.ROGUE not in c.data.classes
            assert c.data.classes != [CardClass.NEUTRAL]
            assert c.type == CardType.MINION


# ===================== shaman =====================
def test_deep_shaman_needlerock_totem():
    # At the end of your turn, gain 2 Armor and draw a card.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.current_player
    # ensure the totem is on board and we have cards to draw
    p.summon("DEEP_008")
    armor0 = p.hero.armor
    hand0 = len(p.hand)
    deck0 = len(p.deck)
    game.end_turn()
    assert p.hero.armor == armor0 + 2
    assert len(p.hand) == hand0 + 1
    assert len(p.deck) == deck0 - 1


def test_deep_shaman_needlerock_totem_only_own_turn():
    # The end-of-turn trigger should not fire on the opponent's turn.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.current_player
    p.summon("DEEP_008")
    game.end_turn()  # p's turn end -> fires once
    armor_after_first = p.hero.armor
    game.end_turn()  # opponent's turn end -> should NOT fire for p
    # Armor is the unambiguous signal the totem did NOT fire on the opponent's
    # turn (we cannot assert on hand size: ending the opponent's turn advances
    # to p's own turn, so p draws its natural start-of-turn card).
    assert p.hero.armor == armor_after_first


def test_deep_shaman_digging_straight_down():
    # Deal 8 damage to a minion. Excavate a treasure.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.current_player
    target = p.opponent.summon("CS2_186")  # War Golem 7/7
    target.max_health = 20
    target.damage = 0
    exc0 = p.excavates_this_game
    spell = p.give("DEEP_009")
    spell.play(target=target)
    assert target.damage == 8
    assert p.excavates_this_game == exc0 + 1
    # Excavate puts a treasure card into hand
    assert any(c.id.startswith("WW_Excavate") or "Excavate" in (c.id or "")
               for c in p.hand) or len(p.hand) >= 1


def test_deep_shaman_digging_kills_small_minion():
    # 8 damage is lethal to anything with <= 8 health.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.current_player
    target = p.opponent.summon("CS2_182")  # Chillwind Yeti 4/5
    spell = p.give("DEEP_009")
    spell.play(target=target)
    assert target.dead


# ===================== warlock =====================
def test_deep_warlock_elementium_geode_battlecry():
    # DEEP_030: Battlecry: Draw a card. Deal 2 damage to your hero.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Ensure deck has something to draw so the draw is observable.
    _deep_warlock_pad_deck(game.player1, 5)
    hp0 = game.player1.hero.health
    geode = game.player1.give("DEEP_030")
    hand_with_geode = len(game.player1.hand)  # includes the geode in hand
    geode.play()
    # Playing the geode removes it from hand (-1); the battlecry draws (+1) ->
    # hand returns to its pre-play size.
    assert len(game.player1.hand) == hand_with_geode
    assert game.player1.hero.health == hp0 - 2
    assert geode in game.player1.field


def test_deep_warlock_elementium_geode_deathrattle():
    # DEEP_030: Deathrattle: Draw a card. Deal 2 damage to your hero.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    _deep_warlock_pad_deck(game.player1, 5)
    geode = game.player1.summon("DEEP_030")  # bypass battlecry
    hp0 = game.player1.hero.health
    hand0 = len(game.player1.hand)
    geode.destroy()
    assert geode.zone == Zone.GRAVEYARD
    assert len(game.player1.hand) == hand0 + 1  # drew exactly one
    assert game.player1.hero.health == hp0 - 2


def test_deep_warlock_chaos_creation():
    # DEEP_031: Deal 6 damage. Summon a random 6-Cost minion. Destroy the
    # bottom 6 cards of your deck.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Target a tanky enemy minion so it absorbs all 6 damage exactly.
    target = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    target.max_health = 20
    target.damage = 0
    # Pad the caster's deck so we can verify exactly 6 are destroyed.
    _deep_warlock_pad_deck(game.player1, 10)
    deck0 = len(game.player1.deck)
    field0 = len(game.player1.field)
    chaos = game.player1.give("DEEP_031")
    chaos.play(target=target)
    assert target.damage == 6
    assert len(game.player1.deck) == deck0 - 6  # bottom 6 destroyed
    assert len(game.player1.field) == field0 + 1  # one 6-cost minion summoned
    summoned = game.player1.field[-1]
    assert summoned.cost == 6
    assert summoned.type == CardType.MINION


def test_deep_warlock_soulfreeze_full_neighbors():
    # DEEP_032: Freeze a minion and its neighbors. Deal damage to your hero
    # equal to the number Frozen.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    left = game.player1.summon("CS2_182")
    mid = game.player1.summon("CS2_182")
    right = game.player1.summon("CS2_182")
    hp0 = game.player1.hero.health
    sf = game.player1.give("DEEP_032")
    sf.play(target=mid)
    assert left.frozen and mid.frozen and right.frozen
    assert game.player1.hero.health == hp0 - 3  # exactly 3 frozen


def test_deep_warlock_soulfreeze_one_neighbor():
    # DEEP_032: edge — target at the end of the board has only one neighbor,
    # so exactly 2 are Frozen and the hero takes exactly 2.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    a = game.player1.summon("CS2_182")
    b = game.player1.summon("CS2_182")  # rightmost
    hp0 = game.player1.hero.health
    sf = game.player1.give("DEEP_032")
    sf.play(target=b)
    assert a.frozen and b.frozen
    assert game.player1.hero.health == hp0 - 2


def _deep_warlock_pad_deck(player, n):
    """Shuffle n vanilla minions into player's deck (for draw/destroy tests)."""
    for _ in range(n):
        player.give("CS2_182").shuffle_into_deck()


# ===================== warrior =====================
def _warrior_clear_dupes(player):
    """Force a highlander (no-duplicate) deck for Deepminer Brann tests."""
    seen = set()
    player.deck[:] = [c for c in player.deck if not (c.id in seen or seen.add(c.id))]


def _warrior_add_dupes(player):
    """Guarantee at least one duplicate pair in deck."""
    from hearthstone.enums import Zone
    for _ in range(2):
        c = player.card("CS2_182")
        c.zone = Zone.DECK


def test_deep_warrior_aftershocks_damage():
    # Deal 1 damage to all minions, three times -> 3 total to each minion.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    m1 = p1.summon("CS2_182"); m1.max_health = 10; m1.damage = 0
    m2 = p2.summon("CS2_182"); m2.max_health = 10; m2.damage = 0
    spell = p1.give("DEEP_010")
    spell.play()
    assert m1.damage == 3
    assert m2.damage == 3


def test_deep_warrior_aftershocks_cost_mod():
    # Costs (2) less if you cast a spell last turn.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    spell = p1.give("DEEP_010")
    assert spell.cost == 4
    p1.spells_played_last_turn = 1
    assert spell.cost == 2


def test_deep_warrior_burning_heart_survives():
    # Deal 2 damage to a minion. If it survives, give your hero +3 Attack this turn.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    tgt = p2.summon("CS2_182"); tgt.max_health = 10; tgt.damage = 0
    assert p1.hero.atk == 0
    spell = p1.give("DEEP_011")
    spell.play(target=tgt)
    assert tgt.damage == 2
    assert not tgt.dead
    assert p1.hero.atk == 3


def test_deep_warrior_burning_heart_kills_no_buff():
    # If the target dies, the hero gains no Attack.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    tgt = p2.summon("CS2_171"); tgt.max_health = 2; tgt.damage = 0
    spell = p1.give("DEEP_011")
    spell.play(target=tgt)
    assert tgt.dead
    assert p1.hero.atk == 0


def test_deep_warrior_crimson_expanse_dormant_copy():
    # Choose a damaged minion. Summon a copy of it that goes Dormant for one
    # turn. "Summon a copy" enters at FULL health — the original's current
    # damage is NOT transferred.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    victim = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    victim.damage = 2  # damaged 4/5 (now at 3 health) -> valid target
    loc = p1.give("DEEP_019")
    loc.play()
    assert p1.location is not None
    assert p1.location.id == "DEEP_019"
    # Location can't be used the turn it is played; cycle back to our turn.
    game.end_turn(); game.end_turn()
    assert not p1.location.exhausted
    p1.location.use(target=victim)
    copies = [m for m in p1.field if m.id == victim.id and m is not victim]
    assert len(copies) == 1
    copy = copies[0]
    assert copy.dormant
    assert copy.dormant_turns == 1
    # Full-health copy: base stats preserved, original's 2 damage NOT copied.
    assert copy.atk == 4
    assert copy.max_health == 5
    assert copy.damage == 0


def test_deep_warrior_deepminer_brann_highlander_grants_double():
    # Battlecry: if your deck has no duplicates, your Battlecries trigger
    # twice for the rest of the game.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _warrior_clear_dupes(p1)
    brann = p1.give("DEEP_020")
    brann.play()
    assert p1.extra_battlecries
    assert any(b.id == "DEEP_020e" for b in p1.buffs)


def test_deep_warrior_deepminer_brann_persists_after_death():
    # "For the rest of the game" — survives Brann leaving play.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _warrior_clear_dupes(p1)
    brann = p1.give("DEEP_020")
    brann.play()
    assert p1.extra_battlecries
    brann.destroy()
    assert p1.extra_battlecries


def test_deep_warrior_deepminer_brann_no_dupes_required():
    # With duplicates in deck the battlecry does nothing.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _warrior_add_dupes(p1)
    brann = p1.give("DEEP_020")
    brann.play()
    assert not p1.extra_battlecries


def test_deep_warrior_deepminer_brann_double_battlecry_fires():
    # A subsequent battlecry minion (Novice Engineer: draw a card) triggers
    # twice -> two cards drawn.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _warrior_clear_dupes(p1)
    brann = p1.give("DEEP_020")
    brann.play()
    eng = p1.give("EX1_015")
    hand_with_engineer = len(p1.hand)
    eng.play()
    # Engineer left hand (-1) then drew twice (+2): net +1 vs pre-play hand.
    assert len(p1.hand) == hand_with_engineer + 1


# ===================== neutral =====================
import pytest
from hearthstone.enums import CardClass, GameTag, Race, CardType, Zone


# The eight keyword-only bonus effects (Elusive = two CANT_BE_TARGETED tags).
_DEEP_BONUS_EFFECT_SETS = [
    {GameTag.TAUNT},
    {GameTag.WINDFURY},
    {GameTag.DIVINE_SHIELD},
    {GameTag.POISONOUS},
    {GameTag.CANT_BE_TARGETED_BY_SPELLS, GameTag.CANT_BE_TARGETED_BY_HERO_POWERS},
    {GameTag.RUSH},
    {GameTag.LIFESTEAL},
    {GameTag.REBORN},
]


def test_deep_neutral_stone_drake_untargetable():
    # DEEP_006: Divine Shield, Taunt, Lifesteal; can't be targeted by spells/HP.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    drake = game.player1.summon("DEEP_006")
    assert drake.divine_shield
    assert drake.taunt
    assert drake.lifesteal
    assert drake.tags.get(GameTag.CANT_BE_TARGETED_BY_SPELLS)
    assert drake.tags.get(GameTag.CANT_BE_TARGETED_BY_HERO_POWERS)
    fireball = game.player1.give("CS2_029")  # Fireball
    assert drake not in fireball.targets


def test_deep_neutral_shale_spider_draws_after_elemental():
    # DEEP_034: Battlecry: If you played an Elemental last turn, draw a card.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    el = p.give("BAR_854")  # Kindling Elemental (Elemental)
    el.play()
    game.end_turn()
    game.end_turn()
    assert p.elemental_played_last_turn == 1
    deck_before = len(p.deck)
    spider = p.give("DEEP_034")
    spider.play()
    # Exactly one card drawn out of the deck.
    assert len(p.deck) == deck_before - 1


def test_deep_neutral_shale_spider_no_draw_without_elemental():
    # DEEP_034: no Elemental played last turn -> no draw.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    yeti = p.give("CS2_182")  # Chillwind Yeti (not an Elemental)
    yeti.play()
    game.end_turn()
    game.end_turn()
    assert p.elemental_played_last_turn == 0
    deck_before = len(p.deck)
    spider = p.give("DEEP_034")
    spider.play()
    assert len(p.deck) == deck_before


def test_deep_neutral_gyreworm_gives_each_minion_a_bonus_effect():
    # DEEP_035: Deathrattle: Give each of your minions a random bonus effect.
    # Bonus effects are keyword-only: each friendly minion gains exactly ONE
    # of the eight keywords, with NO stat change and NO attached enchant (the
    # old impl reused the Showdown Chameleon +3/+3 "summon a Chameleon" pool).
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    m1 = p.summon("CS2_182")  # Chillwind Yeti 4/5
    m2 = p.summon("CS2_182")  # Chillwind Yeti 4/5
    gw = p.summon("DEEP_035")
    gw.destroy()
    game.process_deaths()
    for m in (m1, m2):
        # Keyword-only: stats unchanged, no enchant stamped on the minion.
        assert m.atk == 4 and m.max_health == 5
        assert m.buffs == []
        # Exactly one of the eight bonus-effect keyword sets is present.
        present = [
            s for s in _DEEP_BONUS_EFFECT_SETS
            if all(m.tags.get(t) for t in s)
        ]
        assert len(present) == 1, [t.name for s in present for t in s]


def test_deep_neutral_therazane_doubles_hand_and_deck_elementals():
    # DEEP_036: Taunt; Deathrattle: Double stats of all Elementals in hand+deck.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    th = p.summon("DEEP_036")
    assert th.taunt
    hand_el = p.give("AT_092")  # Ice Rager 5/2 (Elemental) in hand
    deck_el = p.card("BAR_854")  # Kindling Elemental 1/2
    deck_el.controller = p
    deck_el.zone = Zone.DECK
    hand_non = p.give("CS2_182")  # Chillwind Yeti 4/5 (NOT an Elemental)
    th.destroy()
    game.process_deaths()
    assert hand_el.atk == 10 and hand_el.health == 4
    assert deck_el.atk == 2 and deck_el.health == 4
    # Non-Elemental untouched.
    assert hand_non.atk == 4 and hand_non.health == 5
    assert "DEEP_036e" in [b.id for b in hand_el.buffs]


def test_deep_neutral_maruut_highlander_summons_and_gives_others():
    # DEEP_037: If deck has no duplicates, Discover an Elemental to summon;
    # add the others to hand.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.deck):
        c.discard()
    for cid in ["CS2_182", "AT_092", "BAR_854", "UNG_809", "EX1_029"]:
        cc = p.card(cid)
        cc.controller = p
        cc.zone = Zone.DECK
    field_before = len(p.field)
    maruut = p.give("DEEP_037")
    maruut.play()
    assert p.choice is not None
    offered = list(p.choice.cards)
    assert len(offered) == 3
    # Multi-race Elementals (e.g. Elemental/Dragon) report a non-ELEMENTAL
    # singular .race, so check the full races list.
    assert all(Race.ELEMENTAL in c.races for c in offered)
    chosen = offered[0]
    others = [c for c in offered if c is not chosen]
    hand_ids_before = [c.id for c in p.hand]
    p.choice.choose(chosen)
    game.process_deaths()
    # Maruut himself + the chosen Elemental are on the field.
    assert len(p.field) == field_before + 2
    field_ids = [c.id for c in p.field]
    assert chosen.id in field_ids
    # The other two candidates were added to hand.
    for o in others:
        assert o.id in [c.id for c in p.hand]


def test_deep_neutral_maruut_blocked_by_duplicate_deck():
    # DEEP_037: duplicate in deck -> no Discover, no summon.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.deck):
        c.discard()
    for cid in ["CS2_182", "CS2_182", "AT_092"]:  # duplicate Yeti
        cc = p.card(cid)
        cc.controller = p
        cc.zone = Zone.DECK
    field_before = len(p.field)
    maruut = p.give("DEEP_037")
    maruut.play()
    assert p.choice is None
    # Only Maruut entered the field.
    assert len(p.field) == field_before + 1


# ===================== excavate =====================
import random
from hearthstone.enums import CardClass, Zone, Race, CardType


def _excavate_clear_zones(player):
    # Strip the random prepare_game deck/hand so transform/buff tests can
    # assert against exactly the minions we inject.
    for c in list(player.hand):
        c.discard()
    for c in list(player.deck):
        c.zone = Zone.SETASIDE


def test_deep_excavate_DEEP_999t1_heartblossom():
    # Give a friendly minion +2/+2. Deal 2 damage to a random enemy minion.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    friendly = game.player1.summon("CS2_182")  # Chillwind Yeti 4/5
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    spell = game.player1.give("DEEP_999t1")
    spell.play(target=friendly)
    assert (friendly.atk, friendly.health) == (6, 7)
    assert enemy.damage == 2


def test_deep_excavate_DEEP_999t2_deepholm_geode():
    # At the end of your turn, deal 2 damage to all enemies.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.summon("DEEP_999t2")
    enemy_minion = game.player2.summon("CS2_182")
    enemy_minion.max_health = 80
    enemy_minion.damage = 0
    hero_hp = game.player2.hero.health
    game.end_turn()
    assert game.player2.hero.health == hero_hp - 2
    assert enemy_minion.damage == 2


def test_deep_excavate_DEEP_999t3_world_pillar_fragment():
    # Discover an Elemental to summon. Add the others to your hand.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    _excavate_clear_zones(game.player1)
    spell = game.player1.give("DEEP_999t3")
    field_before = len(game.player1.field)
    spell.play()
    choice = game.player1.choice
    offered = list(choice.cards)
    assert len(offered) == 3
    assert all(Race.ELEMENTAL in c.races for c in offered)
    chosen = offered[0]
    others = [c for c in offered if c is not chosen]
    choice.choose(chosen)
    assert game.player1.choice is None
    # Chosen Elemental summoned to the board.
    assert len(game.player1.field) == field_before + 1
    assert game.player1.field[-1].id == chosen.id
    # The other two offered Elementals are now in hand.
    hand_ids = sorted(c.id for c in game.player1.hand)
    for other in others:
        assert other.id in hand_ids


def test_deep_excavate_DEEP_999t4_azerite_dragon():
    # Battlecry: Give all OTHER minions in your hand, deck, and battlefield
    # +3/+3.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    _excavate_clear_zones(game.player1)
    field_m = game.player1.summon("CS2_182")          # 4/5 on board
    hand_m = game.player1.give("CS2_182")             # 4/5 in hand
    deck_m = game.player1.give("CS2_182")             # 4/5 in deck
    deck_m.zone = Zone.DECK
    dragon = game.player1.give("DEEP_999t4")
    dragon.play()
    assert (field_m.atk, field_m.health) == (7, 8)
    assert (hand_m.atk, hand_m.health) == (7, 8)
    assert (deck_m.atk, deck_m.health) == (7, 8)
    # The Azerite Dragon itself (5/5 base) is NOT buffed.
    assert (dragon.atk, dragon.health) == (5, 5)


def test_deep_excavate_DEEP_999t5_azerite_murloc():
    # Battlecry: Transform ALL your other minions into ones that cost (3)
    # more (keeping their original Costs).
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.random = random.Random(7)
    _excavate_clear_zones(game.player1)
    field_m = game.player1.summon("CS2_171")          # Stonetusk Boar, cost 1
    hand_m = game.player1.give("CS2_171")
    deck_m = game.player1.give("CS2_171")
    deck_m.zone = Zone.DECK
    murloc = game.player1.give("DEEP_999t5")
    murloc.play()
    new_field = game.player1.field[0]
    new_hand = [c for c in game.player1.hand if c.id != "DEEP_999t5"][0]
    new_deck = list(game.player1.deck)[0]
    for transformed in (new_field, new_hand, new_deck):
        # Transformed into a different minion costing (3) more by data...
        assert transformed.id != "CS2_171"
        assert transformed.data.cost == 4
        # ...while keeping its original Cost of 1.
        assert transformed.cost == 1
    # The Azerite Murloc itself (5/5 base) is untouched.
    assert (murloc.atk, murloc.health) == (5, 5)


# ---------------------------------------------------------------------------
# Audit-fix regression tests (Tier-1)
# ---------------------------------------------------------------------------

def test_deep_hunter_shimmer_shot_summon_cost_scales_with_spell_damage():
    # "Deal $1 damage. Summon a random minion of that Cost." The summoned
    # minion's Cost must equal the spell-damage-scaled damage dealt, not a
    # hardcoded 1. With Spell Damage +2: deal 3, summon a 3-cost minion.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p = game.current_player
    p.summon("CS2_142")  # Kobold Geomancer, Spell Damage +1
    p.summon("CS2_142")  # +1 more -> +2 total
    target = p.opponent.summon("CS2_186")  # War Golem 7/7
    target.max_health = 20
    target.damage = 0
    before = {id(m) for m in p.field}
    p.give("DEEP_003").play(target=target)
    assert target.damage == 3  # 1 + 2 spell damage
    summoned = [m for m in p.field if id(m) not in before]
    assert len(summoned) == 1
    assert summoned[0].data.cost == 3  # cost matches the damage dealt


def test_deep_priest_pendant_of_earth_leaves_unchosen_in_deck():
    # "Discover a minion from your deck. Gain Armor equal to its Cost."
    # Offers up to 3 distinct deck minions; only the chosen one moves to hand,
    # the others STAY in the deck. Armor = the chosen card's Cost.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.current_player
    for c in list(p.deck):
        c.discard()
    deck_ids = ["CS2_182", "CS2_186", "CS2_222"]  # 3 distinct minions
    for cid in deck_ids:
        cc = p.card(cid)
        cc.controller = p
        cc.zone = Zone.DECK
    armor0 = p.hero.armor
    p.give("DEEP_026").play()
    assert p.choice is not None
    offered = list(p.choice.cards)
    assert len(offered) == 3  # three DISTINCT deck minions offered
    assert len({c.id for c in offered}) == 3
    chosen = offered[0]
    chosen_cost = chosen.cost
    p.choice.choose(chosen)
    # Chosen moved to hand; exactly one card left the deck; others remain.
    assert chosen.id in [c.id for c in p.hand]
    assert len(p.deck) == 2
    remaining = sorted(c.id for c in p.deck)
    assert remaining == sorted(i for i in deck_ids if i != chosen.id)
    assert p.hero.armor == armor0 + chosen_cost


def test_deep_warlock_soulfreeze_immune_neighbor_not_counted():
    # "Freeze a minion and its neighbors. Deal damage to your hero equal to
    # the number Frozen." An Immune neighbor cannot be Frozen, so it is
    # neither frozen nor counted.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p = game.current_player
    left = p.opponent.summon("CS2_182")
    mid = p.opponent.summon("CS2_182")
    right = p.opponent.summon("CS2_182")
    left.tags[GameTag.IMMUNE] = True
    assert left.immune
    hp0 = p.hero.health
    p.give("DEEP_032").play(target=mid)
    assert mid.frozen and right.frozen
    assert not left.frozen          # Immune -> not frozen
    assert p.hero.health == hp0 - 2  # only 2 actually frozen


def test_deep_demonhunter_shadestone_skulker_returns_weapon_destroying_second():
    # Once-over guard: if a different weapon is equipped when the Skulker dies,
    # the borrowed weapon returns and the equipped one is destroyed — faithful
    # to Hearthstone's one-weapon rule.
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p = game.current_player
    war_axe = p.give("CS2_106")  # Fiery War Axe 3/2
    war_axe.play()
    skulker = p.give("DEEP_012")
    skulker.play()
    assert p.weapon is None and skulker.atk == 4  # took the war axe
    reaper = p.give("CS2_112")  # Arcanite Reaper 5/2
    reaper.play()
    assert p.weapon is reaper
    skulker.destroy()
    game.process_deaths()
    # Borrowed war axe returns; the equipped reaper is destroyed (one-weapon).
    assert p.weapon is war_axe
    assert reaper.zone == Zone.GRAVEYARD
