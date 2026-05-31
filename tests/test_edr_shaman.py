"""Into the Emerald Dream — SHAMAN collectible card tests.

Covers all 10 collectible Shaman cards (EDR_ prefix):
  EDR_031 Ohn'ahra, EDR_230 Beanstalk Brute, EDR_231 Aspect's Embrace,
  EDR_232 Typhoon, EDR_233 Spirits of the Forest, EDR_234 Emerald Bounty,
  EDR_238 Merithra, EDR_477 Glowroot Lure, EDR_518 Living Garden,
  EDR_529 Plucky Podling.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone


WISP = "CS2_231"  # 0/1/1 vanilla minion (deterministic deck filler)
FIREBALL = "CS2_029"


def _put_on_top(player, card_id):
    """Create a card and place it on TOP of the deck (deck[-1] = next draw /
    top). Returns the card."""
    card = player.card(card_id, zone=Zone.DECK)
    player.deck.remove(card)
    player.deck.append(card)
    return card


# EDR_031 — Ohn'ahra: At end of your turn, play the top 3 cards from your deck.
def test_ohnahra_plays_top_three_from_deck():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.cant_fatigue = True
    p1.deck = []
    # Bottom -> top: filler, then 3 Wisps on top (deck[-1] drawn first).
    for _ in range(3):
        _put_on_top(p1, WISP)
    ohn = p1.summon("EDR_031")
    assert len(p1.field) == 1  # just Ohn'ahra
    game.end_turn()
    # The 3 top Wisps were played from the deck onto the board.
    wisps = [c for c in p1.field if c.id == WISP]
    assert len(wisps) == 3
    assert len([c for c in p1.deck if c.id == WISP]) == 0


# EDR_230 — Beanstalk Brute: Battlecry: Give +4/+4 to the top 3 minions in
# your deck.
def test_beanstalk_brute_buffs_top_three_deck_minions():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.deck = []
    # 4 Wisps in deck; only the top 3 should get +4/+4.
    wisps = [_put_on_top(p1, WISP) for _ in range(4)]
    brute = p1.give("EDR_230")
    brute.play()
    # deck[-1] is top; top 3 = wisps[-3:] in draw order. Exactly 3 buffed.
    # Wisp is a 1/1, so +4/+4 -> 5/5.
    buffed = [c for c in p1.deck if c.atk == 5 and c.health == 5]
    assert len(buffed) == 3
    unbuffed = [c for c in p1.deck if c.atk == 1 and c.health == 1]
    assert len(unbuffed) == 1


# EDR_231 — Aspect's Embrace: Restore 4 Health. Draw a card. Imbue your Hero
# Power.
def test_aspects_embrace_heals_draws_and_imbues():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.cant_fatigue = True
    p1.deck = []
    _put_on_top(p1, WISP)
    p1.hero.damage = 5
    pre_imbues = p1.imbues_this_game
    pre_hand = len(p1.hand)
    embrace = p1.give("EDR_231")
    embrace.play(target=p1.hero)
    assert p1.hero.damage == 1  # 5 - 4 healed
    assert len(p1.hand) == pre_hand + 1  # drew 1 (embrace left hand, wisp drawn)
    assert p1.imbues_this_game == pre_imbues + 1
    # Imbued the Wind Hero Power (EDR_448p, the Shaman Imbued power).
    assert p1.hero.power.id == "EDR_448p"


# EDR_232 — Typhoon: Each minion gets shuffled into a random player's deck.
def test_typhoon_shuffles_all_minions_into_decks():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.cant_fatigue = True
    p2.cant_fatigue = True
    p1.deck = []
    p2.deck = []
    for _ in range(2):
        p1.summon(WISP)
        p2.summon(WISP)
    assert len(p1.field) == 2 and len(p2.field) == 2
    p1.give("EDR_232").play()
    # All 4 minions left the board, each into some player's deck.
    assert len(p1.field) == 0
    assert len(p2.field) == 0
    total_in_decks = len(p1.deck) + len(p2.deck)
    assert total_in_decks == 4


# EDR_233 — Spirits of the Forest: Choose One - three 2/3 Wolves w/ Taunt; or
# two 4/3 Falcons w/ Windfury.
def test_spirits_of_the_forest_wolves_option():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    card = p1.give("EDR_233")
    card.play(choose="EDR_233a")
    wolves = p1.field
    assert len(wolves) == 3
    for w in wolves:
        assert w.id == "EDR_233t1"
        assert w.atk == 2 and w.health == 3
        assert w.taunt


def test_spirits_of_the_forest_falcons_option():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    card = p1.give("EDR_233")
    card.play(choose="EDR_233b")
    falcons = p1.field
    assert len(falcons) == 2
    for f in falcons:
        assert f.id == "EDR_233t2"
        assert f.atk == 4 and f.health == 3
        assert f.windfury


# EDR_234 — Emerald Bounty: Draw 2 cards. (Lockout cosmetic-only.)
def test_emerald_bounty_draws_two():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.cant_fatigue = True
    p1.deck = []
    for _ in range(2):
        _put_on_top(p1, WISP)
    pre_hand = len(p1.hand)
    bounty = p1.give("EDR_234")
    bounty.play()
    # give Bounty (+1), play it (-1), draw 2 Wisps (+2): net +2 from pre_hand.
    assert len(p1.hand) == pre_hand + 2
    drawn = [c for c in p1.hand if c.id == WISP]
    assert len(drawn) == 2


# EDR_238 — Merithra: Battlecry: Resurrect all different friendly minions that
# cost (8) or more.
def test_merithra_resurrects_different_expensive_minions():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # Two different 8+ cost minions die, plus a duplicate and a cheap one.
    big1 = p1.summon("OG_142")    # Eldritch Horror (8-cost), no battlecry
    big2 = p1.summon("OG_141")    # Faceless Behemoth (10-cost), no battlecry
    big1_dup = p1.summon("OG_142")
    cheap = p1.summon(WISP)       # 0-cost, must NOT resurrect
    for m in (big1, big2, big1_dup, cheap):
        m.destroy()
    game.process_deaths()
    assert len(p1.field) == 0
    merithra = p1.give("EDR_238")
    merithra.play()
    # Merithra (1) + one of each distinct 8+ minion (2) = 3 on board.
    ids = sorted(c.id for c in p1.field)
    assert ids == sorted(["EDR_238", "OG_142", "OG_141"])
    assert WISP not in ids


# EDR_477 — Glowroot Lure: Taunt. Costs (1) less for each time you used your
# Hero Power this game.
def test_glowroot_lure_cost_drops_per_hero_power_use():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    lure = p1.give("EDR_477")
    base = lure.data.cost  # 6
    assert lure.cost == base
    p1.times_hero_power_used_this_game = 2
    assert lure.cost == base - 2
    p1.times_hero_power_used_this_game = 10
    assert lure.cost == 0  # clamped, never negative


# EDR_518 — Living Garden: Battlecry: Imbue your Hero Power. Reduce the Cost of
# a minion in your hand by (1).
def test_living_garden_imbues_and_discounts_hand_minion():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # Single minion in hand so the random pick is deterministic.
    target = p1.give("EX1_298")  # Ragnaros, 8-cost
    base_cost = target.cost
    pre_imbues = p1.imbues_this_game
    garden = p1.give("EDR_518")
    garden.play()
    assert p1.imbues_this_game == pre_imbues + 1
    assert p1.hero.power.id == "EDR_448p"
    assert target.cost == base_cost - 1


# EDR_529 — Plucky Podling: 1/1/2 body (transform-upgrade rider inert).
def test_plucky_podling_is_vanilla_body():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    podling = p1.give("EDR_529")
    assert podling.cost == 1
    podling.play()
    assert podling.atk == 1 and podling.health == 2
    assert len(p1.field) == 1
