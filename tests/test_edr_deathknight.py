"""Into the Emerald Dream — DEATHKNIGHT collectible card tests.

One test per collectible Death Knight card:
  EDR_810 Hideous Husk, EDR_811 Rite of Atrocity, EDR_812 Grotesque Runeblade,
  EDR_813 Morbid Swarm, EDR_814 Infested Breath, EDR_815 Corpse Flower,
  EDR_816 Monstrous Mosquito, EDR_817 Sanguine Infestation, EDR_818 Nythendra,
  EDR_819 Ursoc.
Assertions follow the PRINTED card text.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone, Race


# EDR_810 — Hideous Husk: Your Leeches steal 1 more Health from their victims.
# Battlecry: Summon two 0/2 Leeches.
def test_hideous_husk_summons_two_leeches():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    husk = p1.give("EDR_810")
    husk.play()
    leeches = [m for m in p1.field if m.id == "EDR_810t"]
    assert len(leeches) == 2
    for lc in leeches:
        assert (lc.atk, lc.max_health) == (0, 2)


def test_hideous_husk_leech_steals_extra_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # One Husk in play -> Leeches steal 2 + 1 = 3.
    p1.summon("EDR_810")
    leech = p1.summon("EDR_810t")
    # Single enemy minion as the lowest-Health target; beef hero so the
    # lowest-Health character is the minion.
    victim = p2.summon(TARGET_DUMMY)  # 0/4 Taunt
    victim.max_health = 30
    victim.damage = 0
    # Damage our own hero so the heal is observable (heal up to 3).
    p1.hero.max_health = 30
    p1.hero.damage = 10
    pre_hero_dmg = p1.hero.damage
    game.end_turn()  # p1's OWN_TURN_END fires the Leech
    # Steal 3: victim took exactly 3, hero healed exactly 3.
    assert victim.damage == 3
    assert p1.hero.damage == pre_hero_dmg - 3


# EDR_811 — Rite of Atrocity: Discover an Undead. Spend 2 Corpses to give it
# a Dark Gift.
def test_rite_of_atrocity_discovers_undead_no_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 0
    spell = p1.give("EDR_811")
    spell.play()
    assert p1.choice is not None
    # Every Discover option is an Undead minion.
    for c in p1.choice.cards:
        assert Race.UNDEAD in c.races
    chosen_id = p1.choice.cards[0].id
    p1.choice.choose(p1.choice.cards[0])
    assert p1.choice is None
    found = [c for c in p1.hand if c.id == chosen_id]
    assert len(found) == 1
    # No corpses -> no Dark Gift buff (stats unchanged).
    card = found[0]
    assert not card.buffs


def test_rite_of_atrocity_spends_corpses_for_dark_gift():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 2
    spell = p1.give("EDR_811")
    spell.play()
    chosen = p1.choice.cards[0]
    chosen_id = chosen.id
    p1.choice.choose(chosen)
    card = [c for c in p1.hand if c.id == chosen_id][0]
    # 2 Corpses spent, the Undead got a Dark Gift (+2/+2 approximation).
    assert p1.corpses == 0
    assert len(card.buffs) == 1
    assert card.buffs[0].id == "EDR_811e"


# EDR_812 — Grotesque Runeblade: Battlecry: If the last card you played had an
# Unholy rune, gain +1 Attack. Repeat for Blood and +1 Durability.
#
# NOTE: this branch has a pre-existing engine bug (Weapon._max_durability is
# never initialized), so equipping ANY weapon crashes. We therefore drive the
# battlecry action directly on the weapon while it is in hand (no equip) and
# assert the resulting enchantments — Unholy -> EDR_812e (+1 Attack), Blood ->
# EDR_812e1 (+1 Durability).
from fireplace.actions import Hit
from fireplace.cards.emerald_dream.deathknight import _GrotesqueRuneblade


def test_grotesque_runeblade_no_rune_last_card():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    # Last card played has no runes (Wisp).
    p1.give(WISP).play()
    weapon = p1.give("EDR_812")
    base_atk = weapon.atk
    game.cheat_action(weapon, [_GrotesqueRuneblade(weapon)])
    assert weapon.atk == base_atk
    assert weapon.buffs == []


def test_grotesque_runeblade_unholy_only_last_card():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    # Nythendra (EDR_818) carries an Unholy rune but no Blood rune.
    nyth = p1.give("EDR_818")
    p1.last_card_played = nyth
    weapon = p1.give("EDR_812")
    base_atk = weapon.atk
    game.cheat_action(weapon, [_GrotesqueRuneblade(weapon)])
    # Unholy -> +1 Attack only; no Blood -> no Durability buff.
    assert weapon.atk == base_atk + 1
    assert [b.id for b in weapon.buffs] == ["EDR_812e"]


def test_grotesque_runeblade_unholy_and_blood_last_card():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    # Grotesque Runeblade itself carries BOTH an Unholy and a Blood rune.
    dual = p1.give("EDR_812")
    p1.last_card_played = dual
    weapon = p1.give("EDR_812")
    base_atk = weapon.atk
    game.cheat_action(weapon, [_GrotesqueRuneblade(weapon)])
    # Unholy -> +1 Attack (EDR_812e), Blood -> +1 Durability (EDR_812e1).
    assert weapon.atk == base_atk + 1
    assert sorted(b.id for b in weapon.buffs) == ["EDR_812e", "EDR_812e1"]


# EDR_813 — Morbid Swarm: Choose One - Summon two 1/1 Ants; or Spend 2 Corpses
# to deal 4 damage to a minion.
def test_morbid_swarm_first_mode_summons_two_ants():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    spell = p1.give("EDR_813")
    # Play the first Choose One option (Contaminated Colony).
    spell.play(choose="EDR_813a")
    ants = [m for m in p1.field if m.id == "EDR_813at"]
    assert len(ants) == 2
    for a in ants:
        assert (a.atk, a.max_health) == (1, 1)


def test_morbid_swarm_second_mode_spends_corpses_deals_four():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p1.corpses = 2
    target = p2.summon(TARGET_DUMMY)  # 0/4 Taunt
    target.max_health = 30
    target.damage = 0
    spell = p1.give("EDR_813")
    spell.play(choose="EDR_813b", target=target)
    assert target.damage == 4
    assert p1.corpses == 0


# EDR_814 — Infested Breath: Deal 2 damage. Summon a 0/2 Leech.
def test_infested_breath_damages_and_summons_leech():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    target = p2.summon(TARGET_DUMMY)  # 0/4 Taunt
    target.max_health = 30
    target.damage = 0
    spell = p1.give("EDR_814")
    spell.play(target=target)
    assert target.damage == 2
    leeches = [m for m in p1.field if m.id == "EDR_810t"]
    assert len(leeches) == 1
    assert (leeches[0].atk, leeches[0].max_health) == (0, 2)


# EDR_815 — Corpse Flower: After your opponent summons a minion, spend 2
# Corpses to deal 3 damage to it.
def test_corpse_flower_no_corpses_does_nothing():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p1.summon("EDR_815")
    p1.corpses = 0
    # Target Dummy is 0/4 — summoning it triggers Corpse Flower, but with no
    # Corpses nothing happens.
    summoned = p2.summon(TARGET_DUMMY)
    assert summoned.damage == 0
    assert p1.corpses == 0


def test_corpse_flower_spends_corpses_and_zaps_summoned_minion():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p1.summon("EDR_815")
    p1.corpses = 2
    # Animated Statue (10/10) survives the 3 damage so we can read it exactly.
    # The trigger fires on summon, so assert immediately (no post-reset).
    summoned = p2.summon(ANIMATED_STATUE)
    assert summoned.damage == 3
    assert p1.corpses == 0


# EDR_816 — Monstrous Mosquito: At the end of your turn, give your other
# minions +1 Attack.
def test_monstrous_mosquito_buffs_other_minions_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    mosquito = p1.summon("EDR_816")
    ally = p1.summon(WISP)
    pre_ally_atk = ally.atk
    pre_self_atk = mosquito.atk
    game.end_turn()
    # Other minion gained +1 Attack; the Mosquito itself did not.
    assert ally.atk == pre_ally_atk + 1
    assert mosquito.atk == pre_self_atk


# EDR_818 — Nythendra: Taunt. Deathrattle: Split into 1/1 Beetles. At the
# start of your turn, reform with any remaining.
def test_nythendra_splits_into_beetles_equal_to_health():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    nyth = p1.summon("EDR_818")  # 7/7
    assert nyth.taunt
    # Deal 4 real damage so it splits into exactly 3 Beetles. (Use a real Hit
    # so the SELF_DAMAGE tracker records the remaining Health = 3.)
    game.cheat_action(p1.hero, [Hit(nyth, 4)])
    assert nyth.health == 3
    nyth.destroy()
    game.process_deaths()
    beetles = [m for m in p1.field if m.id == "EDR_818t"]
    assert len(beetles) == 3
    for b in beetles:
        assert (b.atk, b.max_health) == (1, 1)


def test_nythendra_reforms_at_start_of_turn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    # Three Beetles in play -> at start of p1's turn they reform a Nythendra
    # with 3 Health.
    for _ in range(3):
        p1.summon("EDR_818t")
    game.end_turn()  # opponent's turn
    game.end_turn()  # back to p1: OWN_TURN_BEGIN fires the reform
    beetles = [m for m in p1.field if m.id == "EDR_818t"]
    nyths = [m for m in p1.field if m.id == "EDR_818"]
    assert len(beetles) == 0
    assert len(nyths) == 1
    assert nyths[0].health == 3


# EDR_819 — Ursoc: Battlecry: Attack ALL other minions. Deathrattle: Resurrect
# any this killed.
def test_ursoc_attacks_all_other_minions_on_battlecry():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Two enemy minions that each die to Ursoc's 6 attack, plus a beefy enemy
    # that survives so we can read the dealt damage exactly.
    weakling = p2.summon(WISP)  # 0/1, dies
    tank = p2.summon(TARGET_DUMMY)  # 0/4 Taunt
    tank.max_health = 80
    tank.damage = 0
    ursoc = p1.give("EDR_819")  # 6/14
    ursoc.play()
    game.process_deaths()
    # Wisp died; tank took exactly 6.
    assert weakling.zone == Zone.GRAVEYARD
    assert tank.damage == 6
    # Ursoc recorded the kill.
    assert any(cid == WISP for cid, _ in getattr(ursoc, "_ursoc_killed", []))


def test_ursoc_deathrattle_resurrects_what_it_killed():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    victim = p2.summon(WISP)  # dies to Ursoc
    ursoc = p1.summon("EDR_819")  # 6/14 (summon: battlecry does NOT fire)
    # Manually run the battlecry attack-all by playing a fresh Ursoc instead.
    ursoc.destroy()
    game.process_deaths()
    # The summoned Ursoc had no battlecry kills recorded -> nothing resurrected.
    # Re-run with a played Ursoc to exercise the full pipeline.
    game2 = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    q1, q2 = game2.player1, game2.player2
    enemy = q2.summon(WISP)
    played = q1.give("EDR_819")
    played.play()
    game2.process_deaths()
    assert enemy.zone == Zone.GRAVEYARD
    pre = set(q2.field)
    played.destroy()
    game2.process_deaths()
    # The Wisp Ursoc killed is resurrected under its original controller (q2).
    new = [m for m in q2.field if m not in pre and m.id == WISP]
    assert len(new) == 1


# EDR_817 — Sanguine Infestation: Draw 2 cards. Summon two 0/2 Leeches.
def test_sanguine_infestation_draws_two_and_summons_two_leeches():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    # Seed exactly two known cards on top of the deck.
    for _ in range(2):
        c = p1.give(CHICKEN)
        c.zone = Zone.DECK
    spell = p1.give("EDR_817")
    spell.play()
    drawn = [c for c in p1.hand if c.id == CHICKEN]
    assert len(drawn) == 2
    leeches = [m for m in p1.field if m.id == "EDR_810t"]
    assert len(leeches) == 2
    for lc in leeches:
        assert (lc.atk, lc.max_health) == (0, 2)
