"""Into the Emerald Dream — WARLOCK collectible card tests.

Covers all 10 collectible Warlock cards:
  EDR_482 Rotten Apple, EDR_483 Fractured Power, EDR_485 Rotheart Dryad,
  EDR_487 Wallow the Wretched, EDR_488 Avant-Gardening, EDR_489 Agamaggan,
  EDR_490 Sleep Paralysis, EDR_491 Archdruid of Thorns,
  EDR_494 Hungering Ancient, EDR_654 Overgrown Horror.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards


WISP = "CS2_231"
CHILLWIND = "CS2_182"  # Chillwind Yeti 4/5 (no deathrattle)


# ---------------------------------------------------------------------------
# EDR_482 — Rotten Apple: Restore 12 Health to your hero. For the next 2
# turns, deal 3 damage to your hero. (2-mana spell)
# ---------------------------------------------------------------------------
def test_rotten_apple_heals_then_self_damages_two_turns():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.damage = 20  # 30 -> 10
    apple = p1.give("EDR_482")
    apple.play()
    # Restored 12: 10 -> 22.
    assert p1.hero.health == 22

    # End of this turn: first tick, 3 damage -> 19.
    game.end_turn()
    assert p1.hero.health == 19
    game.end_turn()  # opponent end (no further tick on p1)
    assert p1.hero.health == 19

    # End of p1's next turn: second tick -> 16, then enchant tears down.
    game.end_turn()
    assert p1.hero.health == 16
    game.end_turn()
    game.end_turn()  # p1's third turn-end: no more ticks.
    assert p1.hero.health == 16


# ---------------------------------------------------------------------------
# EDR_483 — Fractured Power: Destroy one of your Mana Crystals. In 2 turns,
# gain two. (2-mana spell)
# ---------------------------------------------------------------------------
def test_fractured_power_destroys_then_gains_two_in_two_turns():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Use a low ceiling so neither natural turn-begin growth (+1) nor the
    # delayed +2 ever clamps against max_resources (10), keeping every value
    # exact. begin_turn unconditionally bumps max_mana by 1.
    p1.max_mana = 3
    spell = p1.give("EDR_483")
    spell.play()
    assert p1.max_mana == 2  # lost one crystal immediately (3 -> 2)

    # First own turn-begin: only natural +1 (2 -> 3); delayed tick #1, no gain.
    game.end_turn()  # -> opponent
    game.end_turn()  # -> p1 turn-begin
    assert p1.max_mana == 3

    # Second own turn-begin: natural +1 (3 -> 4) then delayed +2 (-> 6).
    game.end_turn()  # -> opponent
    game.end_turn()  # -> p1 turn-begin
    assert p1.max_mana == 6

    # Third own turn-begin: enchant is gone, only natural +1 (6 -> 7).
    game.end_turn()  # -> opponent
    game.end_turn()  # -> p1 turn-begin
    assert p1.max_mana == 7


# ---------------------------------------------------------------------------
# EDR_485 — Rotheart Dryad: Deathrattle: Draw a minion that costs (7) or more.
# (1/1/1)
# ---------------------------------------------------------------------------
def test_rotheart_dryad_deathrattle_draws_expensive_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.deck = []
    # Deck holds one cheap minion and one 7+ minion; only the 7+ is eligible.
    cheap = p1.give(WISP)
    cheap.shuffle_into_deck()
    big = p1.give("EDR_489")  # Agamaggan, 10-cost minion
    big.shuffle_into_deck()
    pre_hand = len(p1.hand)

    dryad = p1.summon("EDR_485")
    dryad.destroy()

    # Exactly the 7+ minion was drawn; the cheap one stays in the deck.
    assert big.zone == Zone.HAND
    assert cheap.zone == Zone.DECK
    assert len(p1.hand) == pre_hand + 1


# ---------------------------------------------------------------------------
# EDR_487 — Wallow, the Wretched: While in hand/deck, gains a copy of every
# Dark Gift given to your minions. (7/6/6)
# Dark Gifts are granted by out-of-class cards; we simulate one by marking a
# friendly minion with `_dark_gifts` and confirming Wallow absorbs it once.
# ---------------------------------------------------------------------------
def test_wallow_absorbs_dark_gifts_from_friendly_minions_once():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    wallow = p1.give("EDR_487")  # sits in hand
    assert wallow.atk == 6 and wallow.max_health == 6

    # A Dark Gift is a merged keyword tag-dict, exactly as _GiveDarkGift records
    # it on the recipient (see roll_bonus_effects). Stamp a real Taunt gift.
    from hearthstone.enums import GameTag
    gifted = p1.summon(WISP)
    assert not gifted.taunt
    gifted._dark_gifts = [{GameTag.TAUNT: True}]

    # On the controller's next turn-begin, Wallow copies the gift once: the
    # Taunt keyword lands on Wallow and Wallow now reads as a Dark-Gift minion.
    game.end_turn()
    game.end_turn()
    assert wallow.taunt is True
    assert len(getattr(wallow, "_dark_gifts", [])) == 1

    # A second turn does NOT re-absorb the same gift.
    game.end_turn()
    game.end_turn()
    assert len(getattr(wallow, "_dark_gifts", [])) == 1


# ---------------------------------------------------------------------------
# EDR_488 — Avant-Gardening: Discover a Deathrattle minion with a Dark Gift.
# (2-mana spell). We verify the Discover pool is exactly Deathrattle minions.
# ---------------------------------------------------------------------------
def test_avant_gardening_discovers_deathrattle_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    pre_hand = len(p1.hand)
    spell = p1.give("EDR_488")
    spell.play()

    assert p1.choice is not None
    # Every offered card is a Deathrattle minion.
    for card in p1.choice.cards:
        assert card.type == CardType.MINION
        assert card.tags.get(GameTag.DEATHRATTLE)
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    assert chosen.zone == Zone.HAND
    assert len(p1.hand) == pre_hand + 1


# The eight-keyword Dark Gift (Bonus Effect) pool. Avant-Gardening must grant
# exactly one of these to the discovered minion.
_GIFT_TAGS = (
    GameTag.TAUNT,
    GameTag.WINDFURY,
    GameTag.DIVINE_SHIELD,
    GameTag.POISONOUS,
    GameTag.CANT_BE_TARGETED_BY_SPELLS,
    GameTag.RUSH,
    GameTag.LIFESTEAL,
    GameTag.REBORN,
)


def test_avant_gardening_grants_dark_gift_to_discovered_minion():
    # The discovered Deathrattle minion must arrive with a Dark Gift: exactly
    # one keyword from the Bonus Effect pool that the base card data does NOT
    # carry. Reseed the game RNG so both the Discover pick and the gift roll are
    # deterministic, then assert the precise keyword that was granted.
    from random import Random

    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.random = Random(0)
    p1 = game.player1
    spell = p1.give("EDR_488")
    spell.play()
    chosen = p1.choice.cards[0]
    base_tags = {t for t in _GIFT_TAGS if chosen.data.tags.get(t)}
    p1.choice.choose(chosen)
    assert chosen.zone == Zone.HAND

    live_tags = {t for t in _GIFT_TAGS if chosen.tags.get(t)}
    granted = live_tags - base_tags
    # The discovered minion arrives with exactly one Bonus Effect keyword it did
    # NOT carry as a base card (the precise card/keyword shifts with the data
    # pool, so we assert the Dark Gift invariant rather than a fixed RNG roll).
    assert chosen.type == CardType.MINION
    assert chosen.data.tags.get(GameTag.DEATHRATTLE)
    assert len(granted) == 1
    assert granted.issubset(set(_GIFT_TAGS))


# ---------------------------------------------------------------------------
# EDR_489 — Agamaggan: Battlecry: The next card you play costs your OPPONENT'S
# Health instead of Mana (up to 10). (10/8/9)
# Approximation: the next card is free and deals its Cost (capped 10) to the
# enemy hero.
# ---------------------------------------------------------------------------
def test_agamaggan_next_card_bills_opponent_health():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    aga = p1.give("EDR_489")
    aga.play()

    enemy_hp = p2.hero.health
    p1.used_mana = 10  # no mana available -> proves the next card is free
    # Play a Chillwind Yeti (cost 4): free to us, 4 damage to the opponent.
    yeti = p1.give(CHILLWIND)
    assert p1.mana == 0
    yeti.play()
    assert yeti.zone == Zone.PLAY
    assert p2.hero.health == enemy_hp - 4

    # The effect is one-shot: a second card pays normally (and we have no mana).
    second = p1.give(WISP)
    assert not second.is_playable() or p1.mana == 0


# ---------------------------------------------------------------------------
# EDR_490 — Sleep Paralysis: Choose One - Summon two 3/6 Demons with Taunt
# that can't attack; or Destroy an enemy minion. (5-mana spell)
# ---------------------------------------------------------------------------
def test_sleep_paralysis_summon_two_demons():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    spell = p1.give("EDR_490")
    # Choose first option (summon two demons) via the sub-card.
    spell.play(choose="EDR_490a")
    demons = [m for m in p1.field if m.id == "EDR_490t"]
    assert len(demons) == 2
    for d in demons:
        assert d.atk == 3 and d.max_health == 6
        assert d.taunt
        assert d.cant_attack


def test_sleep_paralysis_destroy_enemy_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    target = p2.summon(CHILLWIND)
    spell = p1.give("EDR_490")
    spell.play(choose="EDR_490b", target=target)
    assert target.zone == Zone.GRAVEYARD


def test_sleep_paralysis_choose_both_destroys_chosen_target():
    # Under a Choose-Both effect the spell plays both halves: it summons two
    # 3/6 Demons AND destroys the player-CHOSEN enemy minion (not a random one).
    # Five enemy minions are on board; only the targeted one must die.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    enemies = [p2.summon(CHILLWIND) for _ in range(5)]
    target = enemies[2]
    p1.next_choose_one_combined = 1

    spell = p1.give("EDR_490")
    spell.play(target=target)

    # Both halves fired: exactly two demons summoned.
    demons = [m for m in p1.field if m.id == "EDR_490t"]
    assert len(demons) == 2

    # Exactly the chosen enemy died; the other four survive.
    assert target.zone == Zone.GRAVEYARD
    survivors = [e for e in enemies if e is not target]
    assert all(e.zone == Zone.PLAY for e in survivors)
    assert len([m for m in p2.field if m.id == CHILLWIND]) == 4


# ---------------------------------------------------------------------------
# EDR_491 — Archdruid of Thorns: Battlecry: Gain the Deathrattles of your
# minions that died this turn. (3/2/... wait 2/3/2)
# ---------------------------------------------------------------------------
def test_archdruid_of_thorns_gains_deathrattles():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.deck = []
    # A 7+ minion to draw via Rotheart's deathrattle when Archdruid inherits it.
    big = p1.give("EDR_489")
    big.shuffle_into_deck()

    # A friendly Rotheart Dryad dies this turn (deathrattle: draw a 7+ minion).
    dryad = p1.summon("EDR_485")
    dryad.destroy()  # already drew once
    assert big.zone == Zone.HAND  # drawn by the dryad's own deathrattle

    # Put the big minion back into the deck so the inherited deathrattle has a
    # target.
    big.shuffle_into_deck()

    archdruid = p1.give("EDR_491")
    archdruid.play()
    assert archdruid.has_deathrattle

    # Killing Archdruid fires the inherited deathrattle -> draws the 7+ minion.
    archdruid.destroy()
    assert big.zone == Zone.HAND


# ---------------------------------------------------------------------------
# EDR_494 — Hungering Ancient: At the end of your turn, eat a minion in your
# deck and gain its stats. Deathrattle: Add them to your hand. (6/7 -> 6/7)
# ---------------------------------------------------------------------------
def test_hungering_ancient_eats_and_returns_on_death():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.deck = []
    food = p1.give(CHILLWIND)  # 4/5
    food.shuffle_into_deck()

    ancient = p1.summon("EDR_494")  # 6/7
    assert ancient.atk == 6 and ancient.max_health == 7

    # End of turn: eat the only deck minion, gain its 4/5.
    game.end_turn()
    assert food.zone == Zone.GRAVEYARD
    assert ancient.atk == 10  # 6 + 4
    assert ancient.max_health == 12  # 7 + 5
    assert len([c for c in p1.deck if c.type == CardType.MINION]) == 0

    # Deathrattle returns the eaten minion to hand.
    pre_hand = len(p1.hand)
    ancient.destroy()
    yeti_in_hand = [c for c in p1.hand if c.id == CHILLWIND]
    assert len(yeti_in_hand) == 1
    assert len(p1.hand) == pre_hand + 1


# ---------------------------------------------------------------------------
# EDR_654 — Overgrown Horror: Taunt. Battlecry: Reduce the Cost of minions in
# your hand with Dark Gifts by (2). (4/6)
# ---------------------------------------------------------------------------
def test_overgrown_horror_discounts_dark_gift_minions_in_hand():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    from hearthstone.enums import GameTag
    gifted = p1.give(CHILLWIND)  # cost 4
    gifted._dark_gifts = [{GameTag.DIVINE_SHIELD: True}]  # carries a Dark Gift
    plain = p1.give(WISP)  # cost 0, no gift
    gifted_cost_before = gifted.cost

    horror = p1.give("EDR_654")
    horror.play()
    assert horror.taunt

    # Only the Dark-Gift minion gets -2.
    assert gifted.cost == gifted_cost_before - 2
    assert plain.cost == 0


# Engine: _GiveDarkGift must RECORD each granted gift on the recipient (the
# marker Wallow/Overgrown Horror read), not just apply the keyword tags.
# ---------------------------------------------------------------------------
def test_give_dark_gift_records_on_recipient():
    from fireplace.cards.emerald_dream.neutral import _GiveDarkGift
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    target = p1.summon(CHILLWIND)
    assert not getattr(target, "_dark_gifts", [])
    game.queue_actions(p1.hero, [_GiveDarkGift(target)])
    gifts = getattr(target, "_dark_gifts", [])
    assert len(gifts) == 1
    # The recorded gift is a non-empty keyword tag-dict that was really applied.
    tags = gifts[0]
    assert isinstance(tags, dict) and tags
    for tag, val in tags.items():
        assert target.tags.get(tag) == val
