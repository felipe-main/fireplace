"""The Lost City of Un'Goro mini-set (Dinosaurs, DINO_) — Druid card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Zone


def test_dino_130_longneck_egg_deathrattle():
    # Deathrattle: Summon a 3/3 Beast. Give your minions +1/+1.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # A bystander friendly minion that should receive the +1/+1.
    other = p1.summon("CS2_172")  # Bloodfen Raptor 3/2
    assert other.atk == 3 and other.max_health == 2

    egg = p1.summon("DINO_130")
    assert egg.atk == 0 and egg.max_health == 2

    egg.destroy()
    game.process_deaths()

    # Little Longneck token: a 3/3 Beast.
    tokens = [m for m in p1.field if m.id == "DINO_130t"]
    assert len(tokens) == 1
    token = tokens[0]
    # Little Longneck is a 3/3 Beast.
    assert Race.BEAST in token.races

    # "Give your minions +1/+1" lands on both the bystander and the freshly
    # summoned token (token summoned before the buff resolves): 3/3 -> 4/4.
    assert other.atk == 4 and other.max_health == 3
    assert token.atk == 4 and token.max_health == 4
    # The egg itself is dead and does not get buffed.
    assert egg.zone == Zone.GRAVEYARD


def test_dino_421_seismopod_keywords():
    # Taunt + Elusive (can't be targeted by spells or hero powers).
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    pod = p1.summon("DINO_421")
    assert pod.atk == 9 and pod.max_health == 9
    assert pod.taunt
    assert pod.cant_be_targeted_by_abilities
    assert pod.cant_be_targeted_by_hero_powers


def test_dino_421_seismopod_deathrattle_buffs_hand_and_deck():
    # Deathrattle: Give all minions in your hand and deck +3/+3.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.discard_hand()
    p1.deck.clear()

    in_hand = p1.give("CS2_172")  # Bloodfen Raptor 3/2 in hand
    in_deck = p1.give("CS2_186")  # War Golem 7/7 -> deck
    in_deck.zone = Zone.DECK
    # A spell in hand must NOT receive the minion enchant.
    spell_in_hand = p1.give("CS2_029")  # Fireball
    assert spell_in_hand.buffs == []

    pod = p1.summon("DINO_421")
    pod.destroy()
    game.process_deaths()

    # Hand minion +3/+3.
    assert in_hand.atk == 6 and in_hand.max_health == 5
    # Deck minion +3/+3.
    assert in_deck.atk == 10 and in_deck.max_health == 10
    # Spell untouched (no enchant applied).
    assert spell_in_hand.buffs == []


def test_dino_432_panther_mask_sets_stats_stealth_draws():
    # Set a minion's stats to 5/4 and give it Stealth. Draw 2 cards.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.discard_hand()
    p1.deck.clear()
    # Two known cards to draw, in a controlled order.
    d1 = p1.give("CS2_172")
    d1.zone = Zone.DECK
    d2 = p1.give("CS2_186")
    d2.zone = Zone.DECK

    target = p1.summon("CS2_186")  # War Golem 7/7 on board
    assert target.atk == 7 and target.max_health == 7
    assert not target.stealthed

    mask = p1.give("DINO_432")
    pre_hand = len(p1.hand)  # mask is in hand; will leave hand on play
    mask.play(target=target)

    # Stats set to exactly 5/4.
    assert target.atk == 5
    assert target.max_health == 4
    # Stealth granted.
    assert target.stealthed
    # Drew exactly 2 cards: hand goes from (mask) -> after playing mask and
    # drawing 2 = pre_hand - 1 (mask played) + 2 (drawn).
    assert len(p1.hand) == pre_hand - 1 + 2
    assert d1.zone == Zone.HAND
    assert d2.zone == Zone.HAND
