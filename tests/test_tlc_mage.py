"""The Lost City of Un'Goro — Mage card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Zone


def _resolve_choices(player):
    """Auto-resolve any pending Discover / choice by taking the first option."""
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# TLC_220 Windswept Pageturner — After you summon an Elemental, deal 3 damage
# to a random enemy.
# ---------------------------------------------------------------------------

def test_windswept_pageturner():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Clear the opposing board so the only enemy is the hero; beef it so the
    # 3 damage lands exactly and doesn't end the game.
    p2.hero.max_health = 80
    p2.hero.damage = 0
    p1.summon("TLC_220")
    # Summon an Elemental — should deal 3 to the only enemy (the hero).
    p1.summon(ELEMENTAL)
    assert p2.hero.health == 77
    # A non-Elemental summon does nothing extra.
    p1.summon(WISP)
    assert p2.hero.health == 77


# ---------------------------------------------------------------------------
# TLC_226 Conjured Bookkeeper — Deathrattle: Draw a spell. Kindred: Summon a
# copy of this.
# ---------------------------------------------------------------------------

def test_conjured_bookkeeper_kindred_active():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Play an Elemental on the previous turn so Kindred is active (Bookkeeper
    # is an Elemental).
    p1.give(ELEMENTAL).play()
    game.end_turn(); game.end_turn()
    # Put a spell in deck AFTER the turn cycle so the begin-turn draws don't
    # consume it before the deathrattle fires.
    p1.give(FIREBALL).zone = Zone.DECK
    book = p1.summon("TLC_226")
    pre_hand = len(p1.hand)
    book.destroy()
    game.process_deaths()
    # Kindred summoned a copy; deathrattle also drew the spell.
    copies = [m for m in p1.field if m.id == "TLC_226"]
    assert len(copies) == 1
    assert len(p1.hand) == pre_hand + 1
    assert p1.hand[-1].id == FIREBALL


def test_conjured_bookkeeper_kindred_inactive():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give(FIREBALL).zone = Zone.DECK
    # No matching type played last turn -> Kindred inactive, no copy summoned.
    book = p1.summon("TLC_226")
    book.destroy()
    game.process_deaths()
    copies = [m for m in p1.field if m.id == "TLC_226"]
    assert len(copies) == 0
    # Deathrattle still drew the spell.
    assert p1.hand[-1].id == FIREBALL


# ---------------------------------------------------------------------------
# TLC_334 Relic of Kings — Discover a spell (any class) that costs (8)+. It
# costs (1).
# ---------------------------------------------------------------------------

def test_relic_of_kings():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("TLC_334").play()
    assert p1.choice
    for c in p1.choice.cards:
        assert c.data.cost >= 8
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    drawn = p1.hand[-1]
    assert drawn.id == chosen.id
    # Its cost is set to exactly 1.
    assert drawn.cost == 1


# ---------------------------------------------------------------------------
# TLC_364 Story of the Waygate — Reduce the cost of cards in your hand that
# didn't start in your deck by (1).
# ---------------------------------------------------------------------------

def test_story_of_the_waygate():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # A card given (not from starting deck) — should be reduced.
    created = p1.give(FIREBALL)   # base cost 4
    assert created.cost == 4
    p1.give("TLC_364").play()
    assert created.cost == 3


# ---------------------------------------------------------------------------
# TLC_365 Storage Scuffle — Deal 3 damage to a minion. Costs (0) if you've
# Discovered this turn.
# ---------------------------------------------------------------------------

def test_storage_scuffle_damage_and_cost():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(KOBOLD_GEOMANCER)  # 2/2
    target.max_health = 5
    target.damage = 0
    scuffle = p1.give("TLC_365")
    assert scuffle.cost == 3  # not discovered yet
    scuffle.play(target=target)
    assert target.damage == 3


def test_storage_scuffle_costs_zero_after_discover():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    scuffle = p1.give("TLC_365")
    assert scuffle.cost == 3
    # Discover something this turn (Scrappy Scavenger battlecry discovers).
    p1.give("TLC_461").play()
    _resolve_choices(p1)
    assert p1.discovers_this_turn == 1
    assert scuffle.cost == 0


# ---------------------------------------------------------------------------
# TLC_452 Titanographer Osk — 7/7/7 body (Titan-ability gimmick approximated).
# ---------------------------------------------------------------------------

def test_titanographer_osk_body():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    osk = game.player1.summon("TLC_452")
    assert osk.zone == Zone.PLAY
    # Stats read from data (rebalanced 7/7 -> 6/6 in Patch 33.2).
    assert osk.atk == osk.data.atk
    assert osk.health == osk.data.health


# ---------------------------------------------------------------------------
# TLC_460 The Forbidden Sequence — Quest: Discover 8 cards. Reward: The Origin
# Stone.
# ---------------------------------------------------------------------------

def test_forbidden_sequence_quest():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    quest = p1.give("TLC_460").play()
    assert quest.zone == Zone.SECRET
    assert quest.progress == 0
    # Quest total read from data (rebalanced 8 -> 7 in Patch 33.2).
    total = quest.data.tags[GameTag.QUEST_PROGRESS_TOTAL]
    # Each Scrappy Scavenger battlecry Discovers one card -> +1 progress.
    # Clear hand + field each iteration so the board/hand caps never block a
    # subsequent play.
    for i in range(total - 1):
        scrappy = p1.give("TLC_461")
        scrappy.play()
        _resolve_choices(p1)
        assert quest.progress == i + 1
        for c in list(p1.hand):
            c.discard()
        for m in list(p1.field):
            m.destroy()
        game.process_deaths()
    # Final discover completes the quest and grants the reward weapon.
    p1.give("TLC_461").play()
    _resolve_choices(p1)
    assert quest.zone == Zone.GRAVEYARD
    reward = [c for c in p1.hand if c.id == "TLC_460t"]
    assert len(reward) == 1
    # Reward is the 0/8/3 Origin Stone weapon (durability on the HEALTH tag).
    assert reward[0].data.health == 8


# ---------------------------------------------------------------------------
# TLC_461 Scrappy Scavenger — Battlecry: Discover a card with Cost equal to
# your remaining Mana Crystals.
# ---------------------------------------------------------------------------

def test_scrappy_scavenger_discover_by_mana():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Leave 5 mana before playing Scrappy (cost 1) -> 4 mana remaining at
    # battlecry resolution.
    p1.used_mana = p1.max_mana - 5
    p1.give("TLC_461").play()
    assert p1.mana == 4
    assert p1.choice
    for c in p1.choice.cards:
        assert c.data.cost == 4
    p1.choice.choose(p1.choice.cards[0])


# ---------------------------------------------------------------------------
# TLC_462 Unearthed Artifacts — Summon a random 2-Cost minion. If you've
# Discovered this turn, summon a random 4-Cost minion instead.
# ---------------------------------------------------------------------------

def test_unearthed_artifacts_no_discover():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert p1.discovers_this_turn == 0
    pre = len(p1.field)
    p1.give("TLC_462").play()
    assert len(p1.field) == pre + 1
    summoned = p1.field[-1]
    assert summoned.data.cost == 2


def test_unearthed_artifacts_after_discover():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Discover this turn first.
    p1.give("TLC_461").play()
    _resolve_choices(p1)
    assert p1.discovers_this_turn >= 1
    pre = len(p1.field)
    p1.give("TLC_462").play()
    assert len(p1.field) == pre + 1
    summoned = p1.field[-1]
    assert summoned.data.cost == 4


# ---------------------------------------------------------------------------
# TLC_483 Vault Breaker — After you Discover a card, reduce its Cost by (1).
# ---------------------------------------------------------------------------

def test_vault_breaker():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("TLC_483")
    # Discover via Scrappy Scavenger; the chosen card should cost 1 less.
    p1.give("TLC_461").play()
    chosen = p1.choice.cards[0]
    base_cost = chosen.data.cost
    p1.choice.choose(chosen)
    # `chosen` is the same entity that lands in hand.
    assert chosen.zone == Zone.HAND
    assert chosen.cost == max(0, base_cost - 1)
