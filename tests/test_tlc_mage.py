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


def test_titanographer_osk_rotates_ability_in_hand():
    # While in hand, Osk holds a valid Titan ability that is (re-)rolled at the
    # start of each of your turns.
    from fireplace.cards.the_lost_city.mage import OSK_ABILITY_IDS
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    osk = p1.give("TLC_452")
    game.end_turn()
    game.end_turn()  # back to p1 → OWN_TURN_BEGIN reroll fires
    assert getattr(osk, "_titan_ability", None) in OSK_ABILITY_IDS


def _play_osk(ability_id, setup=None):
    """Play Osk with a forced Titan ability, auto-resolving any choices."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if setup:
        setup(game, p1, p2)
    osk = p1.give("TLC_452")
    osk._titan_ability = ability_id
    osk.play()
    _resolve_choices(p1)
    _resolve_choices(p2)
    return game, p1, p2, osk


def test_titanographer_osk_every_ability_fires_without_crashing():
    # Force each of the 31 Titan abilities in turn and confirm Osk's battlecry
    # resolves cleanly (Osk lands in play, no exception).
    from fireplace.cards.the_lost_city.mage import OSK_ABILITY_IDS

    def setup(game, p1, p2):
        # Give both sides a couple of bodies so targeted/board abilities have
        # something to act on.
        for _ in range(2):
            m = p2.summon("CS2_182")  # Chillwind Yeti 4/5
            m.max_health = 40
            m.damage = 0
        p1.summon(WISP)

    for aid in OSK_ABILITY_IDS:
        game, p1, p2, osk = _play_osk(aid, setup)
        assert osk.zone == Zone.PLAY, "ability %s did not resolve" % aid


# --- exact-effect spot checks across a representative spread of abilities ---

def test_osk_t13_deal_5_to_enemy_face():
    # No enemy minions → the only enemy character is the hero; it takes 5.
    game, p1, p2, osk = _play_osk("TLC_452t13")
    assert p2.hero.health == 25


def test_osk_t17_buffs_other_minions():
    def setup(game, p1, p2):
        p1.summon(WISP)  # a 1/1 ally
    game, p1, p2, osk = _play_osk("TLC_452t17", setup)
    wisp = [m for m in p1.field if m.id == WISP][0]
    assert wisp.atk == 3 and wisp.health == 3  # +2/+2
    # Osk buffs "other" minions, not itself.
    assert osk.atk == osk.data.atk and osk.health == osk.data.health


def test_osk_t8_restores_hero_to_full():
    def setup(game, p1, p2):
        p1.hero.damage = 12
    game, p1, p2, osk = _play_osk("TLC_452t8", setup)
    assert p1.hero.health == 30


def test_osk_t30_gain_health_and_armor():
    game, p1, p2, osk = _play_osk("TLC_452t30")
    assert osk.health == osk.data.health + 5
    assert p1.hero.armor == 5


def test_osk_t3_summons_two_undead():
    game, p1, p2, osk = _play_osk("TLC_452t3")
    undead = [m for m in p1.field if m.id == "TLC_452t3t"]
    assert len(undead) == 2
    for m in undead:
        assert m.atk == 3 and m.health == 3
        assert m.taunt and m.reborn


def test_osk_t28_summons_two_infernals():
    game, p1, p2, osk = _play_osk("TLC_452t28")
    infernals = [m for m in p1.field if m.id == "EX1_tk34"]
    assert len(infernals) == 2
    for m in infernals:
        assert m.atk == 6 and m.health == 6


def test_osk_t9_refreshes_mana():
    def setup(game, p1, p2):
        p1.used_mana = p1.max_mana  # drain to 0
    game, p1, p2, osk = _play_osk("TLC_452t9")
    # After paying 7 for Osk then refreshing, mana is back to full.
    assert p1.mana == p1.max_mana


def test_osk_t35_steals_enemy_minion():
    def setup(game, p1, p2):
        p2.summon("CS2_182")  # lone enemy minion
    game, p1, p2, osk = _play_osk("TLC_452t35", setup)
    assert len(p2.field) == 0
    assert any(m.id == "CS2_182" for m in p1.field)


def test_osk_t16_sets_enemy_minions_to_2():
    def setup(game, p1, p2):
        p2.summon("CS2_182")  # 4/5 Yeti
        p2.summon("CS2_182")
    game, p1, p2, osk = _play_osk("TLC_452t16", setup)
    for m in p2.field:
        assert m.atk == 2 and m.health == 2


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
# TLC_460t The Origin Stone — quest-reward weapon.
# "After you Discover a card, this plays the other options. Lose 1 Durability."
# The engine now retains the un-chosen Discover options on
# player._discover_leftovers (Discover.choose); the weapon replays them and
# spends 1 durability per Discover.
# ---------------------------------------------------------------------------

WISP = "CS2_231"  # 1/1 vanilla, no battlecry — clean replay marker


def test_origin_stone_weapon_body():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    stone = p1.give("TLC_460t")
    stone.play()
    # Equips as the active weapon with 0 attack and full 8 durability.
    assert p1.weapon is stone
    assert stone.zone == Zone.PLAY
    assert stone.atk == 0
    assert stone.durability == 8
    assert stone.max_durability == 8


def test_discover_retains_unchosen_options():
    # Engine primitive: after a Discover resolves, the two un-chosen options
    # are retained on player._discover_leftovers (no Origin Stone needed).
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("TLC_461").play()  # Scrappy Scavenger → Discover
    assert p1.choice
    offered = list(p1.choice.cards)
    chosen = offered[0]
    p1.choice.choose(chosen)
    assert p1._discover_leftovers == [offered[1], offered[2]]


def test_origin_stone_plays_other_options_and_drains_durability():
    # The two un-chosen options are played (here: two Wisps summoned) and the
    # weapon loses exactly 1 durability.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    stone = p1.give("TLC_460t")
    stone.play()
    assert stone.durability == 8
    assert len(p1.field) == 0
    # Simulate the leftovers from a just-resolved Discover, then fire the
    # Discovered event the weapon listens for.
    leftovers = [p1.card(WISP), p1.card(WISP)]
    for c in leftovers:
        c.controller = p1
    p1._discover_leftovers = leftovers
    game.cheat_action(stone, [Discovered(p1, p1.card(WISP))])
    # Both un-chosen Wisps are summoned; durability drops by exactly 1.
    assert len(p1.field) == 2
    assert all(m.id == WISP for m in p1.field)
    assert stone.durability == 7
    # Leftovers are consumed (not replayed again on the next Discover).
    assert p1._discover_leftovers == []


def test_origin_stone_end_to_end_drains_on_real_discover():
    # Full path through a real Discover: durability drops by 1 and the retained
    # leftovers are consumed by the weapon.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    stone = p1.give("TLC_460t")
    stone.play()
    assert stone.durability == 8
    p1.give("TLC_461").play()  # Scrappy Scavenger → Discover
    _resolve_choices(p1)
    assert p1.discovers_this_turn == 1
    assert stone.durability == 7
    assert p1._discover_leftovers == []


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
