"""Into the Emerald Dream — ROGUE collectible card tests.

Covers all 10 collectible Rogue cards:
  EDR_521 Tricky Satyr, EDR_522 Mimicry, EDR_523 Web of Deception,
  EDR_524 Shadowcloaked Assailant, EDR_525 Barbed Thorn,
  EDR_526 Renferal the Malignant, EDR_527 Ashamane, EDR_528 Nightmare Fuel,
  EDR_540 Twisted Webweaver, EDR_781 Harbinger of the Blighted.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards

from fireplace.cards.emerald_dream.rogue import _HarbingerSummon


def _to_deck(player, card_id):
    c = player.give(card_id)
    c.zone = Zone.DECK
    return c


def _give_weapon(player, card_id):
    """Give a weapon, compensating for the pre-existing engine bug where the
    219197 data build tags weapons with HEALTH instead of DURABILITY, so the
    CardManager never populates Weapon._max_durability (engine-owned; not
    fixable from a card file)."""
    w = player.give(card_id)
    w._max_durability = w.data.tags.get(GameTag.HEALTH, 0)
    return w


# EDR_521 — Tricky Satyr | MINION 3/4/3:
# Battlecry: Get a copy of the lowest Cost card in your opponent's hand.
def test_tricky_satyr_copies_lowest_cost_in_enemy_hand():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    # Opponent holds a 5-cost (CS2_213 is not 5; use a known mix).
    p2.discard_hand()
    high = p2.give("GVG_021")   # Mukla's Champion — 5 cost
    low = p2.give("CS2_231")    # Wisp — 0 cost
    assert high.cost > low.cost
    p1.discard_hand()
    satyr = p1.give("EDR_521")
    satyr.play()
    # Exactly one card copied into my hand, and it is the Wisp (lowest cost).
    assert len(p1.hand) == 1
    assert p1.hand[0].id == low.id
    # Original opponent cards untouched.
    assert {c.id for c in p2.hand} == {high.id, low.id}


def test_tricky_satyr_breaks_cost_tie_randomly():
    # Two distinct cards tie for lowest cost (both 0). The old impl always took
    # the leftmost (Wisp). With RNG tie-breaking, seed 0 selects the rightmost
    # of the tied pair (random.choice([a, b]) == b), which a leftmost-only impl
    # could never produce.
    import random as _random

    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.discard_hand()
    p1.discard_hand()
    a = p2.give("CS2_231")  # Wisp — 0 cost (leftmost)
    b = p2.give("ICC_023")  # Snowflipper Penguin — 0 cost (rightmost)
    assert a.cost == b.cost == 0
    satyr = p1.give("EDR_521")
    # game.random.choice over the tied list [a, b]; seed 0 -> picks b.
    game.random = _random.Random(0)
    satyr.play()
    assert len(p1.hand) == 1
    assert p1.hand[0].id == b.id  # rightmost tied card — proves non-leftmost RNG


# EDR_522 — Mimicry | SPELL 1:
# Your opponent draws 2 cards. You get copies of them.
def test_mimicry_opponent_draws_two_you_copy():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.discard_hand()
    # Top two of opponent deck are the next draws (deck[-1] drawn first).
    a = _to_deck(p2, "CS2_182")   # Chillwind Yeti
    b = _to_deck(p2, "CS2_186")   # War Golem
    # Order in deck: [a, b]; b (deck[-1]) drawn first, then a.
    p1.discard_hand()
    spell = p1.give("EDR_522")
    spell.play()
    # Opponent drew exactly the two cards.
    assert {c.id for c in p2.hand} == {"CS2_182", "CS2_186"}
    # I hold copies of both (same ids, different entities).
    assert sorted(c.id for c in p1.hand) == ["CS2_182", "CS2_186"]
    assert all(c not in p2.hand for c in p1.hand)


# EDR_523 — Web of Deception | SPELL 2:
# Return a friendly minion to your hand to summon a 4/4 Spider with Stealth.
def test_web_of_deception_returns_minion_and_summons_spider():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    target = p1.summon("CS2_182")  # Chillwind Yeti
    spell = p1.give("EDR_523")
    spell.play(target=target)
    # The Yeti is back in hand; the only minion on board is the Spider.
    assert target.zone == Zone.HAND
    assert len(p1.field) == 1
    spider = p1.field[0]
    assert spider.id == "EDR_523t"
    assert spider.atk == 4
    assert spider.health == 4
    assert spider.stealthed


# EDR_524 — Shadowcloaked Assailant | MINION 4/3/5:
# Battlecry: If you're holding one of the same cards as your opponent,
# shuffle theirs into their deck.
def test_shadowcloaked_shuffles_matching_card_into_enemy_deck():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    p2.discard_hand()
    # Shared card id between the two hands.
    p1.give("CS2_182")          # I hold a Yeti
    opp_match = p2.give("CS2_182")  # opponent also holds a Yeti
    opp_other = p2.give("CS2_186")  # War Golem — not shared
    assert len(p2.deck) == 0
    assassin = p1.give("EDR_524")
    assassin.play()
    # The opponent's Yeti was shuffled into their deck; the War Golem stayed.
    assert opp_match.zone == Zone.DECK
    assert opp_other.zone == Zone.HAND
    assert [c.id for c in p2.hand] == ["CS2_186"]
    assert [c.id for c in p2.deck] == ["CS2_182"]


def test_shadowcloaked_shuffles_all_matching_copies():
    # Once-over (audit watch): wording "shuffle theirs" is ambiguous on count.
    # The accepted reading shuffles every opponent copy that matches a card in
    # your hand. Defensive test pins that behaviour: opponent holds two Yetis,
    # both go to deck when you hold a Yeti.
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    p2.discard_hand()
    p1.give("CS2_182")              # I hold one Yeti
    m1 = p2.give("CS2_182")         # opponent holds two Yetis
    m2 = p2.give("CS2_182")
    other = p2.give("CS2_186")      # War Golem — not shared
    assassin = p1.give("EDR_524")
    assassin.play()
    assert m1.zone == Zone.DECK
    assert m2.zone == Zone.DECK
    assert other.zone == Zone.HAND
    assert sorted(c.id for c in p2.deck) == ["CS2_182", "CS2_182"]


def test_shadowcloaked_no_match_does_nothing():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    p2.discard_hand()
    p1.give("CS2_182")
    p2.give("CS2_186")  # no shared id
    assassin = p1.give("EDR_524")
    assassin.play()
    assert [c.id for c in p2.hand] == ["CS2_186"]
    assert len(p2.deck) == 0


# EDR_525 — Barbed Thorn | WEAPON 3/1/0:
# Choose One - Gain Poisonous this turn; or Gain "Deathrattle: Deal 2 damage
# to all enemies."
def test_barbed_thorn_choose_poisonous_this_turn():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    weapon = _give_weapon(p1, "EDR_525")
    weapon.play(choose="EDR_525A")  # Extra Eyes — Gain Poisonous this turn
    w = p1.weapon
    assert w.id == "EDR_525"
    # The weapon is Poisonous (the enchant also carries TAG_ONE_TURN_EFFECT so
    # it will fade at turn end once the engine sweeps weapon buffs — see
    # EDR_525e1; player.entities currently skips the weapon, an engine gap).
    assert w.poisonous
    toxins = next(b for b in w.buffs if b.id == "EDR_525e1")
    assert toxins.one_turn_effect


def test_barbed_thorn_choose_deathrattle_hits_all_enemies():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    weapon = _give_weapon(p1, "EDR_525")
    weapon.play(choose="EDR_525B")  # Extra Thorns — gain the Deathrattle
    w = p1.weapon
    assert w.id == "EDR_525"
    assert w.has_deathrattle
    enemy = p2.summon("CS2_182")  # 4/5 Yeti
    enemy.max_health = 80
    enemy.damage = 0
    start_hp = p2.hero.health
    # Destroy the weapon -> deathrattle deals 2 to all enemies.
    w.destroy()
    assert enemy.damage == 2
    assert p2.hero.health == start_hp - 2


# EDR_526 — Renferal, the Malignant | MINION 3/3/3:
# Battlecry: Trap @ random card(s) in your opponent's hand for a turn.
# (Improved for each time you've played this.)
def test_renferal_traps_one_card_first_play():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.discard_hand()
    trapped = p2.give("CS2_182")
    renferal = p1.give("EDR_526")
    renferal.play()
    # First play traps exactly one card.
    assert trapped.unplayable_next_turn == 2
    assert any(b.id == "EDR_526e" for b in trapped.buffs)
    assert not trapped.is_playable()


def test_renferal_scales_with_times_played():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.discard_hand()
    p2.give("CS2_182")
    p2.give("CS2_186")
    p2.give("CS2_213")
    # Pretend a Renferal was already played this game.
    p1.cards_played_this_game.append(p1.give("EDR_526"))
    renferal = p1.give("EDR_526")
    renferal.play()
    # Second play traps 2 cards.
    trapped = [c for c in p2.hand if c.unplayable_next_turn == 2]
    assert len(trapped) == 2


# EDR_527 — Ashamane | MINION 9/7/7:
# Battlecry: Fill your hand with copies of cards from your opponent's deck.
# They cost (3) less.
def test_ashamane_fills_hand_with_discounted_enemy_deck_copies():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    for _ in range(3):
        _to_deck(p2, "CS2_186")  # War Golem, base cost 7
    base = p1.card("CS2_186").cost
    ashamane = p1.give("EDR_527")
    ashamane.play()
    copies = [c for c in p1.hand if c.id == "CS2_186"]
    # Hand filled to 10 with copies (started empty, Ashamane left hand on play).
    assert len(copies) == 10
    assert all(c.cost == base - 3 for c in copies)
    # Opponent's deck untouched.
    assert len([c for c in p2.deck if c.id == "CS2_186"]) == 3


# EDR_528 — Nightmare Fuel | SPELL 1:
# Discover a copy of a minion in your opponent's deck. Combo: With a Dark Gift.
def test_nightmare_fuel_discovers_copy_of_enemy_deck_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    _to_deck(p2, "CS2_182")  # Chillwind Yeti — only minion in enemy deck
    spell = p1.give("EDR_528")
    spell.play()
    assert p1.choice is not None
    # Every option is the only enemy-deck minion.
    assert all(cid == "CS2_182" for cid in p1.choice.cards)
    p1.choice.choose(p1.choice.cards[0])
    held = [c for c in p1.hand if c.id == "CS2_182"]
    assert len(held) == 1
    # No combo: base stats, no Dark Gift buff.
    assert not held[0].buffs


def test_nightmare_fuel_combo_grants_dark_gift():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    _to_deck(p2, "CS2_182")
    base_atk = p1.card("CS2_182").atk
    base_health = p1.card("CS2_182").health
    # Trigger Combo by playing a card first this turn.
    p1.give("CS2_231").play()  # Wisp
    spell = p1.give("EDR_528")
    spell.play()
    assert p1.choice is not None
    p1.choice.choose(p1.choice.cards[0])
    held = next(c for c in p1.hand if c.id == "CS2_182")
    # Combo attaches a Dark Gift via the shared set-wide _GiveDarkGift helper
    # (random keyword Bonus Effect, applied with SetTags), NOT the old one-off
    # flat +1/+1. Stats are unchanged; exactly one Bonus Effect is granted.
    assert held.atk == base_atk
    assert held.health == base_health
    from fireplace.cards.delve_into_deepholm._bonus import BONUS_EFFECTS

    granted = [spec for spec in BONUS_EFFECTS
               if all(held.tags.get(tag) for tag in spec)]
    # roll_bonus_effects(rng, 1) merges exactly one of the eight specs.
    assert len(granted) == 1


def test_nightmare_fuel_no_combo_no_dark_gift():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    _to_deck(p2, "CS2_182")
    base_atk = p1.card("CS2_182").atk
    base_health = p1.card("CS2_182").health
    spell = p1.give("EDR_528")
    spell.play()  # no card played before -> no Combo
    assert p1.choice is not None
    p1.choice.choose(p1.choice.cards[0])
    held = next(c for c in p1.hand if c.id == "CS2_182")
    # Plain copy: base stats, no keyword Dark Gift.
    assert held.atk == base_atk
    assert held.health == base_health
    assert not held.taunt and not held.divine_shield and not held.rush


# EDR_540 — Twisted Webweaver | MINION 1/1/3:
# Whenever you play another minion you've already played, draw a card.
def test_twisted_webweaver_draws_on_repeat_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    # A card to draw.
    drawme = _to_deck(p1, "CS2_186")
    p1.summon("EDR_540")  # Webweaver on board
    # Play a Yeti the first time — no repeat yet, no draw.
    first = p1.give("CS2_182")
    first.play()
    assert drawme.zone == Zone.DECK
    # Play a second Yeti — it's a repeat, draw a card.
    second = p1.give("CS2_182")
    second.play()
    assert drawme.zone == Zone.HAND


def test_twisted_webweaver_no_draw_on_first_play():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    drawme = _to_deck(p1, "CS2_186")
    p1.summon("EDR_540")
    p1.give("CS2_182").play()  # first time this minion is played
    assert drawme.zone == Zone.DECK


# EDR_781 — Harbinger of the Blighted | MINION 2/2/3:
# Whenever this enters your hand from the battlefield, summon two random
# 2-Cost minions. (Trigger awaits an engine bounce event; effect verified.)
def test_harbinger_summons_two_two_cost_minions():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    harbinger = p1.summon("EDR_781")
    pre = len(p1.field)
    game.cheat_action(harbinger, [_HarbingerSummon(harbinger)])
    summoned = p1.field[pre:]
    assert len(summoned) == 2
    assert all(m.cost == 2 for m in summoned)
