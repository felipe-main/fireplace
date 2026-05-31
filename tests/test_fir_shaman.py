"""Firelands mini-set (FIR_ prefix) — SHAMAN collectible card tests.

Covers the 3 Firelands Shaman cards that fold into the Into the Emerald
Dream package:
  FIR_778 Avatar of Destruction, FIR_923 Flames of the Firelord,
  FIR_927 Emberscarred Whelp.
"""

from utils import *

from hearthstone.enums import CardType, Zone


WISP = "CS2_231"  # 0/1/1 vanilla minion
CHILLWIND = "CS2_182"  # 4/3/5 Chillwind Yeti — durable test target
BIG = "EX1_298"  # Ragnaros the Firelord — 8-cost (for the "holding 8+" branch)


# FIR_778 — Avatar of Destruction: Taunt. Deathrattle: Deal 9 damage to all
# enemy minions.
def test_avatar_of_destruction_deathrattle_wipes_enemy_minions():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    avatar = p1.summon("FIR_778")
    assert avatar.taunt
    assert avatar.atk == 9 and avatar.max_health == 9
    # Enemy board: a plain 5-health minion (no deathrattle) dies to 9 damage;
    # a high-HP enemy survives so we can read exact 9 damage. A friendly minion
    # must be untouched (only ENEMY minions are hit).
    enemy_dies = p2.summon(CHILLWIND)  # 4/5 — 9 damage kills it
    enemy_lives = p2.summon(CHILLWIND)
    enemy_lives.max_health = 30
    enemy_lives.damage = 0
    friendly = p1.summon(CHILLWIND)  # friendly — must survive untouched
    avatar.destroy()
    game.process_deaths()
    # Avatar gone; its deathrattle dealt 9 to all enemy minions.
    assert avatar.zone == Zone.GRAVEYARD
    assert enemy_dies.zone == Zone.GRAVEYARD
    assert enemy_lives in p2.field
    assert enemy_lives.damage == 9
    assert friendly in p1.field
    assert friendly.damage == 0


# FIR_923 — Flames of the Firelord: Deal 4 damage to a random enemy minion.
# If you're holding a card that costs (8) or more, deal 8 instead.
def test_flames_deals_four_without_expensive_card():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.hand = []  # nothing held -> 4-damage branch
    # Single enemy minion so the random pick is deterministic; beef HP so it
    # survives and we can read exact damage.
    target = p2.summon(CHILLWIND)
    target.max_health = 30
    target.damage = 0
    flames = p1.give("FIR_923")
    assert len(p1.hand) == 1  # only Flames itself (cost 2, not 8+)
    flames.play()
    assert target.damage == 4


def test_flames_deals_eight_when_holding_expensive_card():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.hand = []
    p1.give(BIG)  # Ragnaros, cost 8 -> triggers the 8-damage branch
    target = p2.summon(CHILLWIND)
    target.max_health = 30
    target.damage = 0
    flames = p1.give("FIR_923")
    flames.play()
    assert target.damage == 8


# FIR_927 — Emberscarred Whelp: Battlecry: Discover a 5-Cost card. Gain 1 Mana
# Crystal next turn only.
def test_emberscarred_whelp_discovers_five_cost_and_grants_next_turn_mana():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.cant_fatigue = True
    p2.cant_fatigue = True
    pre_hand = len(p1.hand)
    whelp = p1.give("FIR_927")
    assert whelp.atk == 3 and whelp.max_health == 2
    whelp.play()
    # Discover popped — pick the first option; it must be a 5-cost card.
    assert p1.choice is not None
    for c in p1.choice.cards:
        assert c.cost == 5
    discovered = p1.choice.cards[0]
    p1.choice.choose(discovered)
    assert p1.choice is None
    # give Whelp (+1), play it (-1), discovered card added (+1): net +1.
    assert len(p1.hand) == pre_hand + 1

    # No bonus mana yet this turn (it's "next turn only").
    assert p1.temp_mana == 0

    # Advance to the controller's next turn. The enchant fires on p1's
    # turn-begin and grants +1 temporary Mana. We lower p1's max_mana during
    # p2's turn so there's headroom (a player already at 10 Mana can't exceed
    # the cap, so the grant would clamp to 0 — matching real Hearthstone).
    game.end_turn()  # p1 -> p2
    p1.max_mana = 3  # headroom below the 10 cap
    game.end_turn()  # p2 -> p1 (begin_turn fires the enchant)
    # _begin_turn bumps max_mana 3 -> 4; the enchant added +1 temp Mana.
    assert p1.temp_mana == 1
    assert p1.max_mana == 4
    assert p1.mana == 5  # 4 max - 0 used + 1 temp

    # One-shot: the enchant destroyed itself, so no further temp Mana, and
    # the temp Mana is cleared at end of the turn it was granted.
    game.end_turn()  # p1 -> p2 (temp_mana reset to 0 on turn end)
    assert p1.temp_mana == 0
    p1.max_mana = 3
    game.end_turn()  # p2 -> p1 (no enchant -> no new temp Mana)
    assert p1.temp_mana == 0
