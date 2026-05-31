"""The Great Dark Beyond — DEMONHUNTER unit tests.

Covers every collectible Demon Hunter card:
  GDB_105 Shattershard Turret   (Starship Piece minion)
  GDB_110 Felfused Battery       (Starship Piece minion)
  GDB_116 Eldritch Being         (Outcast + Spellburst minion)
  GDB_117 Dirdra, Rebel Captain  (Crewmate shuffler/drawer)
  GDB_118 Xor'toth, Breaker of Stars (Stars)
  GDB_119 Emergency Meeting      (spell)
  GDB_471 Voronei Recruiter      (end-of-turn Crewmate)
  GDB_473 Headhunt               (spell)
  GDB_474 Warp Drive             (spell)
  GDB_902 Infiltrate             (spell)
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone, Race

import fireplace.cards as _cards


CREWMATES = [
    "GDB_471t", "GDB_471t2", "GDB_471t3", "GDB_471t4",
    "GDB_471t5", "GDB_471t6", "GDB_471t7", "GDB_471t8",
]


# GDB_105 — Shattershard Turret: Rush, Windfury, Starship Piece. 2/4.
def test_shattershard_turret_keywords_and_stats():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    m = game.player1.summon("GDB_105")
    assert (m.atk, m.max_health) == (2, 4)
    assert m.rush
    assert m.windfury
    # Starship Piece tag is carried by the data card (engine reads data.tags).
    assert m.data.tags.get(GameTag.STARSHIP_PIECE, 0) == 1


# GDB_110 — Felfused Battery: After this attacks, give your OTHER minions +1
# Attack. Starship Piece. 2/3.
def test_felfused_battery_buffs_other_minions_after_attack():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    battery = p1.summon("GDB_110")
    battery.charge = True  # let it attack this turn
    other1 = p1.summon(WISP)  # 1/1
    other2 = p1.summon(WISP)  # 1/1
    assert (battery.atk, battery.max_health) == (2, 3)
    pre_self = battery.atk
    battery.attack(p2.hero)
    # Other friendly minions gain +1 Attack; the battery itself does not.
    assert other1.atk == 2
    assert other2.atk == 2
    assert battery.atk == pre_self


# GDB_116 — Eldritch Being: Outcast and Spellburst: Shuffle your hand. 1/3.
def test_eldritch_being_outcast_shuffles_hand_into_deck():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    # Clear hand, then give Eldritch first so it is leftmost -> Outcast fires.
    for c in list(p1.hand):
        c.discard()
    being = p1.give("GDB_116")
    g1 = p1.give(WISP)
    g2 = p1.give(WISP)
    assert being.zone_position == 1  # leftmost -> Outcast
    pre_deck = len(p1.deck)
    being.play()
    # The two other hand cards are shuffled into the deck; hand is now empty.
    assert len(p1.hand) == 0
    assert len(p1.deck) == pre_deck + 2


def test_eldritch_being_spellburst_shuffles_hand():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Put Eldritch in the MIDDLE so its play is NOT an Outcast (Spellburst arms).
    left = p1.give(WISP)
    being = p1.give("GDB_116")
    right = p1.give(WISP)
    assert being.zone_position == 2  # not leftmost/rightmost
    being.play()
    assert being.has_spellburst
    # Now two filler cards remain in hand; cast a spell to trigger Spellburst.
    pre_deck = len(p1.deck)
    pre_hand = len(p1.hand)  # left + right wisps == 2
    assert pre_hand == 2
    spell = p1.give(MOONFIRE)
    spell.play(target=p1.hero)
    # Spellburst fired: the remaining hand (2 wisps) shuffled into deck.
    assert not being.has_spellburst
    assert len(p1.hand) == 0
    assert len(p1.deck) == pre_deck + 2


# GDB_117 — Dirdra, Rebel Captain: Rush. Battlecry: Shuffle all 8 Crewmates
# into your deck. Deathrattle: Draw two Crewmates. 5/4.
def test_dirdra_battlecry_shuffles_eight_crewmates():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    dirdra = p1.give("GDB_117")
    dirdra.play()
    assert dirdra.rush
    assert (dirdra.atk, dirdra.max_health) == (5, 4)
    deck_crew = [c for c in p1.deck if c.id in CREWMATES]
    # Exactly the 8 distinct Crewmates, one each.
    assert len(deck_crew) == 8
    assert sorted(c.id for c in deck_crew) == sorted(CREWMATES)


def test_dirdra_deathrattle_draws_two_crewmates():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    dirdra = p1.summon("GDB_117")  # bypass battlecry
    # Stack the deck with exactly two Crewmates so the draw is deterministic.
    for cid in (CREWMATES[0], CREWMATES[1]):
        c = p1.give(cid)
        c.zone = Zone.DECK
    pre_hand = len(p1.hand)
    dirdra.destroy()
    game.process_deaths()
    drawn = [c for c in p1.hand if c.id in CREWMATES]
    assert len(drawn) == 2
    assert len(p1.hand) == pre_hand + 2
    assert len([c for c in p1.deck if c.id in CREWMATES]) == 0


# GDB_118 — Xor'toth, Breaker of Stars: Battlecry: Add two Stars to both sides
# of your hand. When they collide, deal 5 damage to all enemies. 5/5 Demon.
def test_xortoth_adds_two_stars_to_hand():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    xortoth = p1.give("GDB_118")
    assert Race.DEMON in xortoth.races
    assert (xortoth.atk, xortoth.max_health) == (5, 5)
    xortoth.play()
    star_origin = [c for c in p1.hand if c.id == "GDB_118t"]
    star_conclusion = [c for c in p1.hand if c.id == "GDB_118t2"]
    assert len(star_origin) == 1
    assert len(star_conclusion) == 1


def test_xortoth_stars_collide_for_five_damage_to_all_enemies():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    for c in list(p1.hand):
        c.discard()
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    enemy = p2.summon("CS2_186")  # War Golem 7/7 — survives 5 to assert exactly
    xortoth = p1.summon("GDB_118")  # bypass battlecry
    # Place the two Stars adjacent in hand so the very first turn-start collides.
    origin = p1.give("GDB_118t")
    conclusion = p1.give("GDB_118t2")
    # Stars are adjacent (indices differ by 1) -> collide at start of next turn.
    pre_enemy_hp = p2.hero.health
    pre_golem = enemy.health
    game.end_turn()   # opponent's turn
    game.end_turn()   # back to us -> OWN_TURN_BEGIN fires _StarConverge
    # Both Stars left the hand, 5 damage hit every enemy character.
    assert not any(c.id in ("GDB_118t", "GDB_118t2") for c in p1.hand)
    assert p2.hero.health == pre_enemy_hp - 5
    assert enemy.health == pre_golem - 5


# GDB_119 — Emergency Meeting: Get two 4/4 Crewmates. Put a random Demon that
# costs (3) or less between them.
def test_emergency_meeting_adds_two_crewmates_and_a_cheap_demon():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    spell = p1.give("GDB_119")
    spell.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    hand = list(p1.hand)
    crew = [c for c in hand if c.id in CREWMATES]
    assert len(crew) == 2
    for c in crew:
        assert (c.atk, c.health) == (4, 4)
    # Exactly three cards added: two Crewmates + one demon between them.
    assert len(hand) == 3
    middle = hand[1]
    assert middle.id not in CREWMATES
    assert Race.DEMON in middle.races
    assert middle.cost <= 3
    # The demon sits between the two Crewmates.
    assert hand[0].id in CREWMATES and hand[2].id in CREWMATES


# GDB_471 — Voronei Recruiter: At the end of your turn, get a 4/4 Crewmate with
# a random Bonus Effect. 2/3.
def test_voronei_recruiter_gives_crewmate_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    rec = p1.summon("GDB_471")
    assert (rec.atk, rec.max_health) == (2, 3)
    assert len(p1.hand) == 0
    game.end_turn()
    crew = [c for c in p1.hand if c.id in CREWMATES]
    assert len(crew) == 1
    assert (crew[0].atk, crew[0].health) == (4, 4)


# GDB_473 — Headhunt: Deal $2 damage. Get a 4/4 Crewmate with a random Bonus
# Effect.
def test_headhunt_deals_two_and_gives_crewmate():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    for c in list(p1.hand):
        c.discard()
    target = p2.summon("CS2_186")  # War Golem 7/7 — survives 2
    spell = p1.give("GDB_473")
    spell.play(target=target)
    assert target.damage == 2
    crew = [c for c in p1.hand if c.id in CREWMATES]
    assert len(crew) == 1
    assert (crew[0].atk, crew[0].health) == (4, 4)


# GDB_474 — Warp Drive: Draw 2 cards. If you're building a Starship, they cost
# (2) less.
def test_warp_drive_draws_two_no_discount_when_not_building():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Two known cards in the deck (Fireballs, base cost 4).
    for _ in range(2):
        c = p1.give(FIREBALL)
        c.zone = Zone.DECK
    assert not p1.is_building_starship
    spell = p1.give("GDB_474")
    spell.play()
    drawn = [c for c in p1.hand if c.id == FIREBALL]
    assert len(drawn) == 2
    base = p1.card(FIREBALL).cost
    for c in drawn:
        assert c.cost == base  # no discount


def test_warp_drive_discounts_drawn_cards_while_building_starship():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    for _ in range(2):
        c = p1.give(FIREBALL)
        c.zone = Zone.DECK
    # Build a Starship: a Starship Piece dies and banks into the building ship.
    piece = p1.summon("GDB_105")  # Starship Piece
    piece.destroy()
    game.process_deaths()
    assert p1.is_building_starship
    spell = p1.give("GDB_474")
    spell.play()
    drawn = [c for c in p1.hand if c.id == FIREBALL]
    assert len(drawn) == 2
    base = p1.card(FIREBALL).cost
    for c in drawn:
        assert c.cost == base - 2


# GDB_902 — Infiltrate: Choose a minion. Deal $3 damage to all OTHER minions.
def test_infiltrate_hits_all_other_minions_not_the_chosen():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # Chosen minion: a beefy survivor we assert takes NO damage.
    chosen = p2.summon("CS2_186")  # War Golem 7/7
    chosen.max_health = 80
    chosen._max_health = 80
    chosen.damage = 0
    # Other minions on both sides — all take exactly 3.
    other_friendly = p1.summon("CS2_186")
    other_friendly.max_health = 80
    other_friendly._max_health = 80
    other_friendly.damage = 0
    other_enemy = p2.summon("CS2_186")
    other_enemy.max_health = 80
    other_enemy._max_health = 80
    other_enemy.damage = 0
    spell = p1.give("GDB_902")
    spell.play(target=chosen)
    assert chosen.damage == 0           # the chosen minion is spared
    assert other_friendly.damage == 3   # every OTHER minion takes 3
    assert other_enemy.damage == 3


# SC_009 — Lurker: After a friendly minion attacks, deal 1 damage to a random
# enemy (or 2 if your minion is a Zerg).
def test_lurker_nonzerg_attacker_deals_1_to_random_enemy():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # Single enemy so the "random enemy" is deterministic: the enemy hero.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    lurker = p1.summon("SC_009")
    attacker = p1.summon(WISP)  # 1/1, NOT a Zerg
    attacker.charge = True
    attacker.attack(p2.hero)
    # Wisp deals 1 in combat + Lurker triggers 1 more (non-Zerg) = 2 total.
    assert p2.hero.damage == 2


def test_lurker_zerg_attacker_deals_2_to_random_enemy():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    lurker = p1.summon("SC_009")
    attacker = p1.summon("SC_019t")  # 1/1 Baneling — a Zerg
    attacker.charge = True
    attacker.attack(p2.hero)
    # Baneling deals 1 in combat + Lurker triggers 2 (Zerg) = 3 total.
    assert p2.hero.damage == 3


# SC_011 — Creep Tumor: Your Zerg minions have +1 Attack and Rush. Lasts 3
# turns.
def test_creep_tumor_buffs_zerg_attack_and_rush():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    zerg = p1.summon("SC_006")  # 8/8 Zerg Ultralisk
    nonzerg = p1.summon(WISP)   # 1/1 non-Zerg
    base_zerg_atk = zerg.atk
    spell = p1.give("SC_011")
    spell.play()
    # Zerg gets +1 Attack and Rush; non-Zerg is untouched.
    assert zerg.atk == base_zerg_atk + 1
    assert zerg.rush
    assert nonzerg.atk == 1
    assert not nonzerg.rush


# SC_022 — Mutalisk: Also damages minions next to whomever this attacks (and
# the enemy hero if a neighbor is missing).
def test_mutalisk_splashes_both_neighbors():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    muta = p1.summon("SC_022")  # 5/2
    muta.charge = True
    left = p2.summon(TARGET_DUMMY)
    mid = p2.summon(TARGET_DUMMY)
    right = p2.summon(TARGET_DUMMY)
    for m in (left, mid, right):
        m.max_health = 80
        m._max_health = 80
    muta.attack(mid)
    # mid takes the combat 5; both neighbors take the 5 splash.
    assert mid.damage == 5
    assert left.damage == 5
    assert right.damage == 5


def test_mutalisk_missing_neighbor_hits_enemy_hero():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    muta = p1.summon("SC_022")  # 5/2
    muta.charge = True
    left = p2.summon(TARGET_DUMMY)
    target = p2.summon(TARGET_DUMMY)  # rightmost -> no right neighbor
    for m in (left, target):
        m.max_health = 80
        m._max_health = 80
    muta.attack(target)
    # target takes combat 5; left neighbor takes 5; missing right neighbor
    # routes its 5 to the enemy hero.
    assert target.damage == 5
    assert left.damage == 5
    assert p2.hero.damage == 5
