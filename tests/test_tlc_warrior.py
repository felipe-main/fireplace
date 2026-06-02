"""The Lost City of Un'Goro — WARRIOR card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Zone


# A vanilla 1/1 Dragon token — used to arm Windpeak Wyrm's Kindred (Dragon).
WHELP_DRAGON = "ds1_whelptoken"
# A cheap vanilla minion with no shared type — used for negative Kindred cases.
WISP_NEUTRAL = "CS2_231"


def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


##
# TLC_478 — Axe of the Forefathers


def test_tlc_478_axe_of_the_forefathers():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # Two enemy minions to be hit by the after-attack AOE, plus a friendly one.
    enemy = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    enemy2 = game.player2.summon("CS2_182")
    friendly = p1.summon("CS2_182")
    axe = p1.give("TLC_478")
    axe.play()
    # Attack the enemy hero so combat doesn't muddy the AOE bookkeeping.
    p1.hero.attack(game.player2.hero)
    # After the hero attacks: 1 damage to ALL minions.
    assert enemy.damage == 1
    assert enemy2.damage == 1
    assert friendly.damage == 1


##
# TLC_600 — Windpeak Wyrm (Kindred: Costs 3 less)


def test_tlc_600_windpeak_wyrm_battlecry():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    target = game.player2.summon("CS2_182")  # 4/5 Yeti, beefed to survive 5
    target.max_health = 80
    target.damage = 0
    p1.hero.armor = 0
    wyrm = p1.give("TLC_600")
    wyrm.play(target=target)
    assert target.damage == 5
    assert p1.hero.armor == 5


def test_tlc_600_kindred_cost_reduction_active():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # Play a Dragon this turn so that NEXT turn the Kindred condition is met.
    p1.give(WHELP_DRAGON).play()
    game.end_turn(); game.end_turn()
    assert Race.DRAGON in p1.races_played_last_turn
    wyrm = p1.give("TLC_600")
    assert wyrm.cost == 8 - 3  # base 8, Kindred reduces by 3


def test_tlc_600_kindred_cost_reduction_inactive():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # Play a non-Dragon minion — Kindred does not arm.
    p1.give(WISP_NEUTRAL).play()
    game.end_turn(); game.end_turn()
    assert Race.DRAGON not in p1.races_played_last_turn
    wyrm = p1.give("TLC_600")
    assert wyrm.cost == 8  # no reduction


##
# TLC_606 — Latorvian Armorer


def test_tlc_606_armorer_kills_target_gains_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # A 1-health enemy minion: 2 damage kills it -> gain 5 Armor.
    target = game.player2.summon("CS2_171")  # Stonetusk Boar 1/1
    p1.hero.armor = 0
    armorer = p1.give("TLC_606")
    armorer.play(target=target)
    assert target.dead
    assert p1.hero.armor == 5


def test_tlc_606_armorer_target_survives_no_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # A 5-health enemy minion: 2 damage does NOT kill it -> no Armor.
    target = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    p1.hero.armor = 0
    armorer = p1.give("TLC_606")
    armorer.play(target=target)
    assert not target.dead
    assert target.damage == 2
    assert p1.hero.armor == 0


##
# TLC_601 — Shellnado


def test_tlc_601_shellnado_spends_up_to_5():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 8  # more than 5 -> spend exactly 5
    enemy = game.player2.summon("CS2_182")  # 4/5 Yeti, beefed to survive
    enemy.max_health = 80
    enemy.damage = 0
    friendly = p1.summon("CS2_182")
    friendly.max_health = 80
    friendly.damage = 0
    p1.give("TLC_601").play()
    assert p1.hero.armor == 3        # 8 - 5
    assert enemy.damage == 5
    assert friendly.damage == 5      # hits ALL minions


def test_tlc_601_shellnado_partial_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 3  # fewer than 5 -> spend all 3
    enemy = game.player2.summon("CS2_182")  # 4/5 Yeti
    p1.give("TLC_601").play()
    assert p1.hero.armor == 0
    assert enemy.damage == 3


def test_tlc_601_shellnado_no_armor_noop():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 0
    enemy = game.player2.summon("CS2_182")
    p1.give("TLC_601").play()
    assert p1.hero.armor == 0
    assert enemy.damage == 0


##
# TLC_620 — Fortify


def test_tlc_620_fortify():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 4
    # Target a high-HP minion so it absorbs all the damage.
    target = game.player2.summon("CS2_182")  # 4/5 Yeti
    target.max_health = 80
    target.damage = 0
    p1.give("TLC_620").play(target=target)
    # Gain 3 Armor first (4 -> 7), then deal damage equal to Armor (7).
    assert p1.hero.armor == 7
    assert target.damage == 7


##
# TLC_622 — City Defenses


def test_tlc_622_city_defenses_summons_two_security():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("TLC_622").play()
    security = [m for m in p1.field if m.id == "TLC_622t"]
    assert len(security) == 2
    for s in security:
        assert s.atk == 0
        assert s.health == 6
        assert s.taunt


def test_tlc_622t_security_gains_attack_when_damaged():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    sec = p1.summon("TLC_622t")
    assert sec.atk == 0
    # Damage it once (non-lethally) -> +1 Attack.
    p1.give("CS2_008").play(target=sec)  # Moonfire 1 dmg -> 6 health survives
    assert sec.atk == 1
    assert sec.damage == 1


##
# TLC_623 — Stonecarver


def test_tlc_623_stonecarver_buffs_damaged_minion_at_end_of_turn():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.summon("TLC_623")
    # One damaged friendly minion — the only legal target for the buff.
    damaged = p1.summon("CS2_182")  # 4/5 Yeti
    damaged.damage = 2
    pre_atk, pre_health = damaged.atk, damaged.max_health
    game.end_turn()
    assert damaged.atk == pre_atk + 2
    assert damaged.max_health == pre_health + 2


def test_tlc_623_stonecarver_no_damaged_minion_noop():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.summon("TLC_623")
    healthy = p1.summon("CS2_182")  # full health, not a legal target
    pre_atk = healthy.atk
    game.end_turn()
    assert healthy.atk == pre_atk  # nothing buffed


##
# TLC_624 — Nablya, the Watcher


def test_tlc_624_nablya_summons_rush_copies_of_damaged():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _clear_hand(p1)
    # One damaged friendly minion -> exactly one copy with Rush.
    damaged = p1.summon("CS2_182")  # 4/5 Yeti
    damaged.damage = 2
    healthy = p1.summon("CS2_171")  # 1/1 Boar, full health -> not copied
    nablya = p1.give("TLC_624")
    nablya.play()
    yetis = [m for m in p1.field if m.id == "CS2_182"]
    assert len(yetis) == 2  # original + one copy
    copy = [m for m in yetis if m is not damaged][0]
    assert copy.damage == 0       # the copy spawns at full health
    assert copy.rush
    # The healthy boar was not copied.
    assert len([m for m in p1.field if m.id == "CS2_171"]) == 1


##
# TLC_602 — Enter the Lost City (Quest)


def test_tlc_602_quest_rewards_latorvius_after_10_turns():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _clear_hand(p1)
    quest = p1.give("TLC_602")
    quest.play()
    assert quest.zone == Zone.SECRET  # quest sits in the secret zone
    # Survive (end) 10 of our turns.
    for _ in range(10):
        game.end_turn(); game.end_turn()
    # Reward Latorvius should now be in hand.
    assert any(c.id == "TLC_602t" for c in p1.hand)
    assert quest.zone == Zone.GRAVEYARD


def test_tlc_602t_latorvius_gives_two_rewards():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _clear_hand(p1)
    latorvius = p1.give("TLC_602t")
    latorvius.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 2
    pool = set(latorvius.entourage)
    for c in p1.hand:
        assert c.id in pool


def test_tlc_602t_latorvius_shuffles_the_rest_into_deck():
    # Printed: "Get 2 random 'Journey to Un'Goro' Quest Rewards. Shuffle the
    # rest into your deck." Verify BOTH halves: exactly 2 rewards enter hand,
    # and the remaining 7 entourage tokens are shuffled into the deck — with
    # the two sets disjoint (no token is both given and shuffled).
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    _clear_hand(p1)
    # Empty the deck so we can read off exactly what got shuffled in.
    for card in list(p1.deck):
        card.discard()
    assert len(p1.deck) == 0

    latorvius = p1.give("TLC_602t")
    entourage = list(latorvius.entourage)
    n_total = len(entourage)  # 9 UNG quest rewards

    latorvius.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])

    hand_ids = sorted(c.id for c in p1.hand)
    deck_ids = sorted(c.id for c in p1.deck)

    # Exactly 2 rewards in hand, exactly the rest shuffled into the deck.
    assert len(hand_ids) == 2
    assert len(deck_ids) == n_total - 2  # 7 shuffled in

    # Every card in hand and deck is a real entourage reward token.
    pool = sorted(entourage)
    for cid in hand_ids:
        assert cid in pool
    for cid in deck_ids:
        assert cid in pool

    # Given (hand) and shuffled (deck) are disjoint and together cover the
    # whole entourage exactly once (a multiset partition).
    assert set(hand_ids).isdisjoint(set(deck_ids))
    assert sorted(hand_ids + deck_ids) == pool


##
# TLC_632 — Story of Sulfuras (Hero Power swap)


def test_tlc_632_story_of_sulfuras_swaps_hero_power():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    original = p1.hero_power.id
    p1.give("TLC_632").play()
    assert p1.hero_power.id == "TLC_632t"
    # First use: deal 8 to a random enemy and downgrade to the last-use token.
    # (Target is random — hero or this minion — so we only assert the swap.)
    enemy = game.player2.summon("CS2_182")  # 4/5 Yeti, beefed to soak the hit
    enemy.max_health = 80
    enemy.damage = 0
    p1.hero_power.use()
    assert p1.hero_power.id == "TLC_632t2"  # now "last use"
    # Second use swaps back to the original Hero Power.
    game.end_turn(); game.end_turn()
    p1.hero_power.use()
    assert p1.hero_power.id == original


def test_tlc_632t_die_insect_deals_8():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.give("TLC_632").play()
    # Make the enemy hero the only legal random target by clearing the board,
    # then verify exactly 8 damage lands on it.
    pre = game.player2.hero.health
    p1.hero_power.use()
    assert game.player2.hero.health == pre - 8
