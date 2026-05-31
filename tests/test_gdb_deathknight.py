"""The Great Dark Beyond — DEATHKNIGHT collectible card tests.

One (or a small cluster of) tests per collectible Death Knight card:
  GDB_106 Guiding Figure, GDB_112 Soulbound Spire, GDB_113 Airlock Breach,
  GDB_468 Wakener of Souls, GDB_469 Auchenai Death-Speaker,
  GDB_470 Exarch Maladaar, GDB_475 Orbital Moon, GDB_476 Suffocate,
  GDB_477 The 8 Hands From Beyond, GDB_478 Assimilating Blight.
Assertions follow the PRINTED card text.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards


# GDB_106 — Guiding Figure: Spellburst: Trigger a random friendly minion's
# Deathrattle. Starship Piece.
def test_guiding_figure_spellburst_triggers_a_deathrattle():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    figure = p1.summon("GDB_106")
    assert figure.has_spellburst
    # The only other friendly Deathrattle minion is Loot Hoarder (draws a card
    # on death). Seed a card so its Deathrattle has something to draw, then
    # casting a spell triggers Guiding Figure's Spellburst on it.
    dr = p1.summon("EX1_096")  # Loot Hoarder, 2/1 Deathrattle: Draw a card
    # Seed the deck with a unique marker card (Chicken) so the Loot Hoarder
    # Deathrattle draw is observable and unambiguous.
    seed = p1.give(CHICKEN)
    seed.zone = Zone.DECK
    pre_dr_health = dr.health
    spell = p1.give(MOONFIRE)
    spell.play(target=p2.hero)
    # Spellburst consumed.
    assert not figure.has_spellburst
    # The only friendly Deathrattle minion is Loot Hoarder -> its Deathrattle
    # fired, drawing the seeded card into hand.
    assert seed.zone == Zone.HAND
    assert seed in p1.hand
    # Loot Hoarder itself is NOT destroyed by triggering its deathrattle.
    assert dr.zone == Zone.PLAY
    assert dr.health == pre_dr_health


# GDB_112 — Soulbound Spire: Deathrattle: Summon a minion with Cost equal to
# this minion's Attack (up to 10). Starship Piece.
def test_soulbound_spire_summons_minion_costing_its_attack():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    spire = p1.summon("GDB_112")  # base 2 atk
    # Pin the cost: buff Attack to a value whose minion pool is well-populated.
    # Set Attack to 1 so the summoned minion costs exactly 1.
    spire.atk = 1
    assert spire.atk == 1
    spire.destroy()
    game.process_deaths()
    # Soulbound Spire is a Starship Piece, so on death it also banks into a
    # building Starship (a dormant Permanent). Exclude the ship and the spire
    # itself; what remains is the Deathrattle summon.
    ship = p1.starship
    summoned = [m for m in p1.field if m is not spire and m is not ship]
    assert len(summoned) == 1
    # Cost equals the spire's Attack (1).
    assert summoned[0].cost == 1


# GDB_113 — Airlock Breach: Summon a 5/5 Undead with Taunt and give your hero
# +5 Health. Spend 5 Corpses to do it again.
def test_airlock_breach_summons_5_5_taunt_and_heros_health():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 0  # not enough to repeat
    base_max_health = p1.hero.max_health
    spell = p1.give("GDB_113")
    spell.play()
    souls = [m for m in p1.field if m.id == "GDB_113t"]
    assert len(souls) == 1
    soul = souls[0]
    assert (soul.atk, soul.max_health) == (5, 5)
    assert soul.taunt
    assert Race.UNDEAD in soul.races
    # Hero gained +5 max Health.
    assert p1.hero.max_health == base_max_health + 5


def test_airlock_breach_repeats_when_5_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 5
    base_max_health = p1.hero.max_health
    spell = p1.give("GDB_113")
    spell.play()
    # Two 5/5 Taunts summoned, hero gained +10 Health, 5 corpses spent.
    souls = [m for m in p1.field if m.id == "GDB_113t"]
    assert len(souls) == 2
    for s in souls:
        assert (s.atk, s.max_health) == (5, 5)
        assert s.taunt
    assert p1.hero.max_health == base_max_health + 10
    assert p1.corpses == 0


# GDB_468 — Wakener of Souls: Taunt, Reborn. Deathrattle: Resurrect a different
# friendly Deathrattle minion.
def test_wakener_of_souls_resurrects_a_different_deathrattle_minion():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    wakener = p1.summon("GDB_468")
    assert wakener.taunt and wakener.reborn
    # A different friendly Deathrattle minion must have died first.
    hoarder = p1.summon("EX1_096")  # Loot Hoarder, Deathrattle
    hoarder.destroy()
    game.process_deaths()
    # Wakener has Reborn — silence it so its own death is final (Reborn would
    # otherwise resurrect Wakener itself, muddying the board). Strip Reborn.
    wakener.reborn = False
    field_before = set(p1.field)
    wakener.destroy()
    game.process_deaths()
    # Wakener's Deathrattle resurrected a friendly Deathrattle minion that
    # died (Loot Hoarder), not itself.
    new = [m for m in p1.field if m not in field_before]
    assert len(new) == 1
    assert new[0].id == "EX1_096"


# GDB_469 — Auchenai Death-Speaker: After another friendly minion is Reborn,
# summon a copy of it.
def test_auchenai_summons_copy_when_friendly_minion_reborns():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.summon("GDB_469")
    # A friendly Reborn minion dies -> it Reborns (1 health copy) AND Auchenai
    # summons a copy of it. Use a plain Reborn minion (Wisp + Reborn tag).
    reborn_minion = p1.summon(WISP)
    reborn_minion.reborn = True
    reborn_minion.destroy()
    game.process_deaths()
    # Board now: Auchenai + the Reborn-token + Auchenai's copy = 3.
    wisps = [m for m in p1.field if m.id == WISP]
    assert len(wisps) == 2  # the Reborn token + Auchenai's copy


# GDB_470 — Exarch Maladaar: Battlecry: The next card you play this turn costs
# Corpses instead of Mana.
def test_exarch_maladaar_next_card_costs_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.summon("GDB_470")  # battlecry doesn't fire on summon; trigger via play
    # Use a real play so the battlecry runs.
    exarch = p1.give("GDB_470")
    exarch.play()
    assert p1.next_card_costs_corpses == 1
    # Now play a spell. It should pay Corpses, not Mana.
    p1.corpses = 10
    p1.used_mana = 0
    pre_mana = p1.mana
    target = p1.give("CS2_029")  # Fireball, cost 4
    cost = target.cost
    target.play(target=game.player2.hero)
    # Mana untouched, 4 corpses spent.
    assert p1.mana == pre_mana
    assert p1.corpses == 10 - cost
    # Flag consumed.
    assert p1.next_card_costs_corpses == 0


# GDB_475 — Orbital Moon: Give a minion Taunt and Lifesteal. If you played an
# adjacent card this turn, also give it Reborn.
def test_orbital_moon_gives_taunt_and_lifesteal_no_reborn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    target = p1.summon(WISP)
    spell = p1.give("GDB_475")
    # No adjacent card was played this turn (give doesn't count as play).
    assert spell.adjacent_plays_this_turn == 0
    spell.play(target=target)
    assert target.taunt
    assert target.lifesteal
    assert not target.reborn


def test_orbital_moon_gives_reborn_when_adjacent_card_played():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    target = p1.summon(WISP)
    # Put Orbital Moon in hand with a neighbor, then play the neighbor so
    # Orbital Moon registers an adjacent play this turn.
    spell = p1.give("GDB_475")
    neighbor = p1.give(MOONFIRE)
    # Ensure they are adjacent in hand.
    assert abs(p1.hand.index(spell) - p1.hand.index(neighbor)) == 1
    neighbor.play(target=game.player2.hero)
    assert spell.adjacent_plays_this_turn >= 1
    spell.play(target=target)
    assert target.taunt
    assert target.lifesteal
    assert target.reborn


# GDB_476 — Suffocate: Destroy a minion. If you're building a Starship, also
# destroy a random neighbor.
def test_suffocate_destroys_single_target_when_not_building():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    left = p2.summon(WISP)
    target = p2.summon(GOLDSHIRE_FOOTMAN)
    right = p2.summon(WISP)
    assert not p1.is_building_starship
    spell = p1.give("GDB_476")
    spell.play(target=target)
    game.process_deaths()
    assert target.zone == Zone.GRAVEYARD
    # Neighbors untouched when not building a Starship.
    assert left.zone == Zone.PLAY
    assert right.zone == Zone.PLAY


def test_suffocate_also_destroys_a_neighbor_when_building_starship():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Make p1 build a Starship: bank a piece by killing a Starship Piece.
    piece = p1.summon("GDB_100")  # Starship Piece
    piece.destroy()
    game.process_deaths()
    assert p1.is_building_starship
    # Two enemy minions, adjacent. Suffocate one -> the other (its only
    # neighbor) is also destroyed.
    a = p2.summon(GOLDSHIRE_FOOTMAN)
    b = p2.summon(GOLDSHIRE_FOOTMAN)
    spell = p1.give("GDB_476")
    spell.play(target=a)
    game.process_deaths()
    assert a.zone == Zone.GRAVEYARD
    assert b.zone == Zone.GRAVEYARD


# GDB_477 — The 8 Hands From Beyond: Battlecry: Destroy both players' decks
# EXCEPT the 8 highest Cost cards in each.
def test_eight_hands_keeps_top_8_cost_in_each_deck():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Build a deck of 12 cards with distinct, known costs for p1.
    # Use Wisps (cost 0) for the low cards and Fireballs (cost 4) for high.
    lows = []
    highs = []
    for _ in range(7):
        c = p1.give(WISP)  # cost 0
        c.zone = Zone.DECK
        lows.append(c)
    for _ in range(8):
        c = p1.give("CS2_029")  # Fireball, cost 4
        c.zone = Zone.DECK
        highs.append(c)
    # Same for p2.
    p2_lows = []
    for _ in range(5):
        c = p2.give(WISP)
        c.zone = Zone.DECK
        p2_lows.append(c)
    p2_highs = []
    for _ in range(8):
        c = p2.give("CS2_029")
        c.zone = Zone.DECK
        p2_highs.append(c)
    hands = p1.give("GDB_477")
    hands.play()
    # p1: only the 8 Fireballs (highest cost) survive; the 7 Wisps are gone.
    assert all(c.zone == Zone.GRAVEYARD for c in lows)
    assert all(c.zone == Zone.DECK for c in highs)
    assert len(p1.deck) == 8
    # p2: 8 Fireballs survive; the 5 Wisps are destroyed.
    assert all(c.zone == Zone.GRAVEYARD for c in p2_lows)
    assert all(c.zone == Zone.DECK for c in p2_highs)
    assert len(p2.deck) == 8


# GDB_478 — Assimilating Blight: Discover a 3-Cost Deathrattle minion. Summon
# it with Reborn.
def test_assimilating_blight_summons_discovered_minion_with_reborn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    spell = p1.give("GDB_478")
    spell.play()
    # Auto-resolve the Discover.
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Exactly one minion was summoned, it's a 3-cost Deathrattle minion with
    # Reborn.
    field = list(p1.field)
    assert len(field) == 1
    summoned = field[0]
    assert summoned.cost == 3
    assert summoned.has_deathrattle
    assert summoned.reborn


# SC_001 — Baneling Barrage: Get a 1/1 Baneling that explodes. If you control
# a Zerg minion, get another Baneling.
def test_baneling_barrage_no_zerg_one_token():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    spell = p1.give("SC_001")
    spell.play()
    banelings = [c for c in p1.hand if c.id == "SC_019t"]
    assert len(banelings) == 1


def test_baneling_barrage_with_zerg_two_tokens():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.summon("SC_006")  # an 8/8 Zerg Ultralisk in play
    spell = p1.give("SC_001")
    spell.play()
    banelings = [c for c in p1.hand if c.id == "SC_019t"]
    assert len(banelings) == 2


# SC_002 — Infestor: Deathrattle: Your Zerg minions have +1/+1 for the rest of
# the game.
def test_infestor_deathrattle_buffs_current_and_future_zerg():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    existing = p1.summon("SC_006")  # 8/8 Zerg already on board
    infestor = p1.summon("SC_002")
    assert (existing.atk, existing.health) == (8, 8)
    infestor.destroy()
    game.process_deaths()
    # Existing Zerg gets +1/+1.
    assert (existing.atk, existing.health) == (9, 9)
    # A Zerg summoned AFTER the deathrattle also gets +1/+1 (rest of game aura).
    later = p1.summon("SC_006")
    assert (later.atk, later.health) == (9, 9)


# SC_018 — Viper: Battlecry: Summon a minion from your opponent's hand. Your
# other Zerg minions gain Reborn and attack it.
def test_viper_summons_from_opponent_hand_and_other_zerg_reborn_attack():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p2.discard_hand()
    # The only minion in p2's hand is the target; give it big health so it
    # survives the attack and we can read the damage exactly.
    victim_card = p2.give(TARGET_DUMMY)  # 0/4 Taunt
    victim_card.max_health = 80
    # One friendly Zerg minion already in play (the "other" that attacks).
    ally = p1.summon("SC_006")  # 8/8 Zerg
    assert not ally.reborn
    viper = p1.give("SC_018")
    viper.play()
    # The opponent's minion was summoned to p2's board (left their hand).
    assert victim_card.zone == Zone.PLAY
    assert victim_card.controller is p2
    # The other Zerg gained Reborn...
    assert ally.reborn
    # ...and attacked the summoned minion: the 8-atk Ultralisk dealt exactly 8.
    assert victim_card.damage == 8
