"""Emerald Dream mini-set (Firelands, FIR_) — WARRIOR collectible card tests.

Tight per-card assertions for:
  FIR_928 Keeper of Flame, FIR_939 Shadowflame Suffusion, FIR_956 Dragon Turtle.
"""

from utils import *
from hearthstone.enums import CardType, GameTag, CardClass, Zone

import fireplace.cards as _cards
from fireplace.cards.emerald_dream.neutral import _GiveDarkGift
from fireplace.actions import Hit


WISP = "CS2_231"  # 0/1/1 vanilla neutral minion (test fodder)
YETI = "CS2_182"  # Chillwind Yeti 4/5 (beefy target)


def _clear_hand(player):
    for c in list(player.hand):
        c.discard()


# FIR_928 — Keeper of Flame: Battlecry: Give all minions in your hand +3/+3.
# They are discarded in 3 turns.
def test_keeper_of_flame_buffs_all_hand_minions_plus_3_3():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    _clear_hand(p1)
    wisp = p1.give(WISP)          # 1/1
    yeti = p1.give(YETI)          # 4/5
    spell_fodder = p1.give("EDR_531")  # a non-minion in hand (must be untouched)
    keeper = p1.give("FIR_928")
    keeper.play()
    # Battlecry gives every minion in hand +3/+3 (not the Keeper itself — it has
    # already left the hand to be played).
    assert (wisp.atk, wisp.max_health) == (4, 4)
    assert (yeti.atk, yeti.max_health) == (7, 8)
    # The non-minion spell is untouched and still in hand.
    assert spell_fodder.zone == Zone.HAND
    assert spell_fodder.type == CardType.SPELL


def test_keeper_of_flame_discards_buffed_minion_after_3_turns():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    _clear_hand(p1)
    wisp = p1.give(WISP)
    keeper = p1.give("FIR_928")
    keeper.play()
    assert wisp.zone == Zone.HAND
    assert wisp._keeper_burn_turns == 0
    # Each of the controller's OWN_TURN_BEGIN ticks the Burning Up timer.
    # Pass exactly 3 of p1's turns; the 3rd tick discards it.
    game.end_turn(); game.end_turn()  # p1's turn 2 begins -> tick 1
    assert wisp.zone == Zone.HAND
    assert wisp._keeper_burn_turns == 1
    game.end_turn(); game.end_turn()  # p1's turn 3 begins -> tick 2
    assert wisp.zone == Zone.HAND
    assert wisp._keeper_burn_turns == 2
    game.end_turn(); game.end_turn()  # p1's turn 4 begins -> tick 3 -> discard
    # A discarded hand card is removed from the game (not a graveyard death).
    assert wisp.zone == Zone.REMOVEDFROMGAME
    assert wisp not in p1.hand


# FIR_939 — Shadowflame Suffusion: Deal 3 damage. Discover a Warrior minion
# with a Dark Gift.
def test_shadowflame_suffusion_deals_3_then_discovers_warrior_dark_gift():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    _clear_hand(p1)
    target = p2.summon(YETI)  # 4/5 -> exactly 3 damage, survives
    spell = p1.give("FIR_939")
    spell.play(target=target)
    assert target.damage == 3
    # A Discover over three Warrior minions should be open.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    for card in p1.choice.cards:
        assert card.type == CardType.MINION
        classes = getattr(card, "classes", None) or [card.card_class]
        assert CardClass.WARRIOR in classes
    chosen = p1.choice.cards[0]
    chosen_id = chosen.id
    base_tags = _cards.db[chosen_id].tags
    p1.choice.choose(chosen)
    assert p1.choice is None
    # The discovered Warrior minion is in hand carrying exactly one NEW Dark Gift
    # keyword from the eight-keyword Nightmare Bonus-Effect pool.
    got = next(c for c in p1.hand if c.id == chosen_id)
    assert got._dark_gifts  # marker recorded
    bonus_keywords = (
        GameTag.TAUNT, GameTag.WINDFURY, GameTag.DIVINE_SHIELD, GameTag.POISONOUS,
        GameTag.CANT_BE_TARGETED_BY_SPELLS, GameTag.RUSH, GameTag.LIFESTEAL,
        GameTag.REBORN,
    )
    added = [
        kw for kw in bonus_keywords
        if bool(got.tags.get(kw)) and not bool(base_tags.get(kw))
    ]
    assert len(added) == 1


# FIR_956 — Dragon Turtle: Battlecry: If you're holding a minion with a Dark
# Gift, give your hero +3 Attack this turn and 6 Armor.
def test_dragon_turtle_buffs_hero_when_holding_dark_gift_minion():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    _clear_hand(p1)
    # Hold a minion carrying a Dark Gift (mark via the shared set-wide helper).
    gifted = p1.give(YETI)
    game.queue_actions(p1.hero, [_GiveDarkGift(gifted)])
    assert gifted._dark_gifts
    assert p1.hero.atk == 0
    assert p1.hero.armor == 0
    turtle = p1.give("FIR_956")
    turtle.play()
    assert p1.hero.atk == 3   # +3 Attack this turn
    assert p1.hero.armor == 6  # +6 Armor


def test_dragon_turtle_no_buff_without_dark_gift():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    _clear_hand(p1)
    # Hold a plain minion (no Dark Gift) — battlecry must not fire.
    p1.give(YETI)
    turtle = p1.give("FIR_956")
    turtle.play()
    assert p1.hero.atk == 0
    assert p1.hero.armor == 0


def test_dragon_turtle_attack_buff_expires_end_of_turn():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    _clear_hand(p1)
    gifted = p1.give(YETI)
    game.queue_actions(p1.hero, [_GiveDarkGift(gifted)])
    turtle = p1.give("FIR_956")
    turtle.play()
    assert p1.hero.atk == 3
    # "+3 Attack this turn" — the Attack is gone next turn (Armor persists).
    game.end_turn(); game.end_turn()
    assert p1.hero.atk == 0
    assert p1.hero.armor == 6
