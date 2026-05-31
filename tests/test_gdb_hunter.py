"""The Great Dark Beyond — HUNTER collectible cards.

Tight unit tests asserting the PRINTED card behaviour. One test (or cluster)
per collectible card:
  GDB_107 Specimen Claw, GDB_111 Biopod, GDB_237 Alien Encounters,
  GDB_840 Extraterrestrial Egg, GDB_841 Rangari Scout,
  GDB_842 Gorm the Worldeater, GDB_843 Parallax Cannon,
  GDB_844 Detailed Notes, GDB_845 Laser Barrage, GDB_846 Exarch Naielle.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards

from fireplace.actions import Hit, Discover, Give
from fireplace.dsl.random_picker import RandomBeast


def _make_building_starship(player):
    """Summon + destroy a Starship Piece so the player is building a ship."""
    piece = player.summon("GDB_100")  # The Exile's Hope (neutral piece)
    piece.destroy()
    player.game.process_deaths()
    assert player.is_building_starship


# GDB_107 — Specimen Claw: After your opponent plays a minion, attack it.
# Starship Piece.
def test_specimen_claw_attacks_opponent_minion_on_play():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    claw = p1.summon("GDB_107")
    a = claw.atk
    assert a > 0
    # Give the opponent a fat minion so it survives the attack and the exact
    # damage is measurable.
    game.end_turn()  # now p2's turn
    target = p2.give(GOLDSHIRE_FOOTMAN)  # 1/2
    target.max_health = 80
    target._max_health = 80
    target.damage = 0
    target.play()
    # After the opponent plays it, Specimen Claw attacks it for its Attack.
    assert target.damage == a
    # The claw took the 1 return damage from the 1/2 footman.
    assert claw.damage == target.atk


# GDB_111 — Biopod: Deathrattle: Deal damage equal to this minion's Attack to
# a random enemy. Starship Piece.
def test_biopod_deathrattle_hits_random_enemy_for_attack():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    biopod = p1.summon("GDB_111")
    a = biopod.atk
    assert a > 0
    # Only one enemy exists (the hero), so the random pick is deterministic.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    biopod.destroy()
    game.process_deaths()
    assert biopod.zone == Zone.GRAVEYARD
    assert p2.hero.health == 80 - a


# GDB_237 — Alien Encounters: Summon two 2/5 Beasts with Taunt. Costs (1) less
# for each card you Discovered this game.
def test_alien_encounters_summons_two_taunt_beasts():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    spell = p1.give("GDB_237")
    spell.play()
    tokens = [m for m in p1.field if m.id == "GDB_237t"]
    assert len(tokens) == 2
    for t in tokens:
        assert (t.atk, t.max_health) == (2, 4)
        assert t.taunt
        assert Race.BEAST in t.races


def test_alien_encounters_cost_reduced_per_discover():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    spell = p1.give("GDB_237")
    base = spell.data.cost
    assert spell.cost == base
    # Each Discover this game reduces the cost by (1).
    p1.discovers_this_game = 3
    assert spell.cost == base - 3
    # Never below 0.
    p1.discovers_this_game = 99
    assert spell.cost == 0


# GDB_840 — Extraterrestrial Egg: Deathrattle: Summon a 3/5 Beast that attacks
# the lowest Health enemy.
def test_extraterrestrial_egg_summons_beast_that_attacks_lowest_health():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # Two enemy minions: lowest-health one must be the attack target.
    high = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    high.max_health = 80
    high._max_health = 80
    high.damage = 0
    low = p2.summon(WISP)  # 1/1 -> lowest health
    egg = p1.summon("GDB_840")
    egg.destroy()
    game.process_deaths()
    # The 3/5 Eggburster is summoned.
    beasts = [m for m in p1.field if m.id == "GDB_840t"]
    assert len(beasts) == 1
    beast = beasts[0]
    assert (beast.atk, beast.max_health) == (3, 5)
    # It attacked the lowest-health enemy (the 1/1 Wisp) -> Wisp dies, the fat
    # footman is untouched.
    assert low.zone == Zone.GRAVEYARD
    assert high.damage == 0
    # The Wisp's 1 return damage hit the beast.
    assert beast.damage == 1


# GDB_841 — Rangari Scout: After you Discover a card, get a copy of it.
def test_rangari_scout_copies_discovered_card():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.summon("GDB_841")
    # Discover anything; Rangari Scout then puts a copy of the chosen card in
    # hand (so hand = the discovered card + its copy).
    game.queue_actions(p1.hero, [Discover(p1, RandomBeast()).then(
        Give(p1, Discover.CARD))])
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    in_hand = [c.id for c in p1.hand]
    # Exactly two copies of one beast in hand (the given card + Scout's copy).
    assert len(in_hand) == 2
    assert in_hand[0] == in_hand[1]


# GDB_842 — Gorm the Worldeater: Dormant for 5 turns. At the end of your turn,
# destroy the minion to the right of this to awaken 1 turn sooner.
def test_gorm_is_dormant_for_five_turns_on_play():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    gorm = p1.give("GDB_842")
    gorm.play()
    # Printed card: enters DORMANT for 5 turns.
    assert gorm.dormant
    assert gorm.dormant_turns == 5


def test_gorm_eats_right_neighbor_and_awakens_sooner():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    gorm = p1.give("GDB_842")
    gorm.play()
    assert gorm.dormant
    start = gorm.dormant_turns
    assert start == 5
    # Put a minion directly to the right of Gorm.
    victim = p1.summon(WISP)
    assert list(p1.field).index(victim) == list(p1.field).index(gorm) + 1
    game.end_turn()
    # End of your turn: the right neighbor is destroyed and Gorm awakens 1
    # sooner (an immediate extra -1 on top of the normal countdown).
    assert victim.zone == Zone.GRAVEYARD
    assert gorm.dormant_turns == start - 1
    # Back around to your next turn: the natural dormant tick fires too.
    game.end_turn()  # opponent's turn
    assert gorm.dormant_turns == start - 2


def test_gorm_base_stats():
    # Gorm the Worldeater is a 12/12 Beast (stats live in data).
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    gorm = game.player1.summon("GDB_842")
    assert (gorm.atk, gorm.max_health) == (12, 12)
    assert Race.BEAST in gorm.races


# GDB_843 — Parallax Cannon (Weapon): Has +2 Attack if you've Discovered this
# turn. Spellburst: Your hero is Immune this turn.
def test_parallax_cannon_plus2_when_discovered_this_turn():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    weapon = p1.give("GDB_843")
    weapon.play()
    base = weapon.data.atk  # 2
    assert weapon.atk == base
    # Discover a card this turn -> the aura grants +2 Attack.
    game.queue_actions(p1.hero, [Discover(p1, RandomBeast()).then(
        Give(p1, Discover.CARD))])
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert p1.discovers_this_turn == 1
    assert weapon.atk == base + 2
    # The bonus is conditional on the per-turn counter: clear it + refresh and
    # the weapon drops back to base.
    p1.discovers_this_turn = 0
    game.refresh_auras()
    assert weapon.atk == base


def test_parallax_cannon_spellburst_makes_hero_immune():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    weapon = p1.give("GDB_843")
    weapon.play()
    assert weapon.has_spellburst
    assert not p1.hero.cant_be_damaged
    # Cast a spell -> Spellburst makes the hero Immune this turn.
    p1.give(MOONFIRE).play(target=p2.hero)
    assert p1.hero.cant_be_damaged
    # Confirm the immunity actually absorbs damage.
    p1.hero.max_health = 30
    p1.hero._max_health = 30
    p1.hero.damage = 0
    game.queue_actions(p2.hero, [Hit(p1.hero, 5)])
    assert p1.hero.damage == 0


# GDB_844 — Detailed Notes: Discover a Beast that costs (5) or more. Reduce its
# Cost by (2).
def test_detailed_notes_discovers_expensive_beast_and_discounts():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    spell = p1.give("GDB_844")
    spell.play()
    assert p1.choice is not None
    # Every offered card is a Beast costing 5 or more.
    for cid in p1.choice.cards:
        c = _cards.db[cid]
        assert c.type == CardType.MINION
        assert Race.BEAST in c.races
        assert c.cost >= 5
    chosen_cost = _cards.db[p1.choice.cards[0]].cost
    p1.choice.choose(p1.choice.cards[0])
    got = p1.hand[-1]
    # The discovered beast's cost is reduced by 2.
    assert got.cost == chosen_cost - 2


# GDB_845 — Laser Barrage: Deal 3 damage to a minion. If you're building a
# Starship, also damage its neighbors.
def test_laser_barrage_hits_only_target_when_not_building():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    left = p2.summon(GOLDSHIRE_FOOTMAN)
    mid = p2.summon(GOLDSHIRE_FOOTMAN)
    right = p2.summon(GOLDSHIRE_FOOTMAN)
    for m in (left, mid, right):
        m.max_health = 80
        m._max_health = 80
        m.damage = 0
    assert not p1.is_building_starship
    spell = p1.give("GDB_845")
    spell.play(target=mid)
    # Not building a Starship -> only the target takes 3, neighbors untouched.
    assert mid.damage == 3
    assert left.damage == 0
    assert right.damage == 0


def test_laser_barrage_hits_neighbors_when_building_starship():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    _make_building_starship(p1)
    left = p2.summon(GOLDSHIRE_FOOTMAN)
    mid = p2.summon(GOLDSHIRE_FOOTMAN)
    right = p2.summon(GOLDSHIRE_FOOTMAN)
    for m in (left, mid, right):
        m.max_health = 80
        m._max_health = 80
        m.damage = 0
    spell = p1.give("GDB_845")
    spell.play(target=mid)
    # Building a Starship -> target and both neighbors take 3 each.
    assert mid.damage == 3
    assert left.damage == 3
    assert right.damage == 3


# GDB_846 — Exarch Naielle: Battlecry: Replace your Hero Power with Tracking
# (Discover a card from your deck).
def test_exarch_naielle_replaces_hero_power_with_tracking():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    assert p1.hero_power.id != "GDB_846hp"
    naielle = p1.give("GDB_846")
    naielle.play()
    assert p1.hero_power.id == "GDB_846hp"


# Tokens — base stats / keyword sit in data.
def test_snacking_scrunguk_token_stats():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    t = game.player1.summon("GDB_237t")
    assert (t.atk, t.max_health) == (2, 4)
    assert t.taunt
    assert Race.BEAST in t.races


def test_eggburster_token_stats():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    t = game.player1.summon("GDB_840t")
    assert (t.atk, t.max_health) == (3, 5)
    assert Race.BEAST in t.races


# SC_008 — Hydralisk: Battlecry: Deal 2 damage to a random enemy. Repeat for
# each other Zerg minion you control.
def test_hydralisk_no_other_zerg_deals_2_once():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # Lone enemy target so the random enemy is deterministic.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    hydra = p1.give("SC_008")
    hydra.play()
    # No other Zerg -> exactly one 2-damage hit.
    assert p2.hero.damage == 2


def test_hydralisk_repeats_per_other_zerg():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    # Two OTHER Zerg minions already in play.
    p1.summon("SC_006")  # Zerg
    p1.summon("SC_006")  # Zerg
    hydra = p1.give("SC_008")
    hydra.play()
    # 1 base + 2 repeats = 3 hits of 2 = 6 damage to the lone enemy hero.
    assert p2.hero.damage == 6


# SC_012 — Roach: When you draw this, get a copy of it. Battlecry: If you
# control another Zerg minion, gain +1/+2.
def test_roach_draw_makes_a_copy():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    p1.give("SC_012").shuffle_into_deck()
    roach = next(c for c in p1.deck if c.id == "SC_012")
    roach.draw()
    copies = [c for c in p1.hand if c.id == "SC_012"]
    # The drawn Roach plus a fresh copy = two in hand.
    assert len(copies) == 2


def test_roach_battlecry_buffs_with_another_zerg():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.summon("SC_006")  # another Zerg in play
    roach = p1.give("SC_012")
    roach.play()
    # 2/2 base + 1/2 = 3/4.
    assert (roach.atk, roach.max_health) == (3, 4)


def test_roach_battlecry_no_buff_without_another_zerg():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    roach = p1.give("SC_012")
    roach.play()
    # No other Zerg -> stays 2/2.
    assert (roach.atk, roach.max_health) == (2, 2)


# SC_021 — Evolution Chamber: Give your minions +1 Attack. Give your Zerg an
# extra +1/+1.
def test_evolution_chamber_buffs_minions_and_extra_for_zerg():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    zerg = p1.summon("SC_006")  # 8/8 Zerg
    nonzerg = p1.summon(WISP)   # 1/1 non-Zerg
    spell = p1.give("SC_021")
    spell.play()
    # Non-Zerg: +1 Attack only.
    assert (nonzerg.atk, nonzerg.max_health) == (2, 1)
    # Zerg: +1 Attack (all) + extra +1/+1 = +2/+1 total.
    assert (zerg.atk, zerg.max_health) == (10, 9)
