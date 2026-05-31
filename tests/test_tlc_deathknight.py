"""The Lost City of Un'Goro — DEATHKNIGHT collectible card tests.

One tight test (plus negative cases for Kindred) per collectible card:
  TLC_401 Bonechill Stegodon, TLC_432 Dread Raptor, TLC_433 Reanimate the
  Terror, TLC_434 Paleomancy, TLC_435 Crypt Map, TLC_436 Reanimated
  Pterrordax, TLC_439 Wave of Tar, TLC_440 Cryosleep, TLC_443 Reluctant
  Wrangler, TLC_810 High Cultist Herenn.
Assertions follow the PRINTED card text.
"""

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Race, SpellSchool, Zone


CHILLWIND = "CS2_182"  # Chillwind Yeti 4/5 vanilla minion
WISP = "CS2_231"       # 1/1 vanilla minion (no deathrattle)
HARVEST_GOLEM = "EX1_556"  # 2/3 Deathrattle: Summon a 2/1 Damaged Golem (cost 3)
LEPER_GNOME = "EX1_029"    # 2/1 Deathrattle: Deal 2 to enemy hero (cost 1)


# TLC_401 — Deathrattle: Deal 6 damage to three random enemies.
def test_bonechill_stegodon_deathrattle_deals_18_total():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    stego = p1.summon("TLC_401")
    # Single enemy character (the hero) that can soak all three 6-damage
    # ticks, so total damage is exactly 18 regardless of which "random"
    # enemy each tick rolls (only one exists).
    p2.hero.max_health = 80
    p2.hero.damage = 0
    stego.destroy()
    assert p2.hero.damage == 18


# TLC_432 — Battlecry: Draw a Deathrattle minion that costs (3) or less.
# Kindred: It costs (0).
def test_dread_raptor_draws_cheap_deathrattle_minion():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    # Only one eligible card in deck: a cost-3 deathrattle minion.
    target = p1.card(HARVEST_GOLEM, zone=Zone.DECK)
    p1.card(CHILLWIND, zone=Zone.DECK)  # not a deathrattle, ineligible
    p1.races_played_last_turn = set()   # Kindred inactive
    raptor = p1.give("TLC_432")
    raptor.play()
    assert target.zone == Zone.HAND
    # Kindred inactive -> normal cost.
    assert target.cost == 3


def test_dread_raptor_kindred_makes_drawn_minion_cost_zero():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    target = p1.card(HARVEST_GOLEM, zone=Zone.DECK)
    # Dread Raptor is an UNDEAD; playing an Undead last turn arms Kindred.
    p1.races_played_last_turn = {Race.UNDEAD}
    raptor = p1.give("TLC_432")
    raptor.play()
    assert target.zone == Zone.HAND
    assert target.cost == 0


# TLC_433 — Quest: Spend 18 Corpses. Reward: Tyrax, Bone Terror.
def test_reanimate_the_terror_quest_rewards_tyrax():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    quest = p1.give("TLC_433")
    quest.play()
    assert quest.zone == Zone.SECRET
    assert quest.progress == 0
    # Spend exactly 18 corpses; the reward should resolve. cheat_action runs
    # through an action block so process_reward() fires on the empty stack.
    p1.corpses = 18
    game.cheat_action(p1.hero, [SpendCorpses(p1, 18)])
    # Reward fired: Tyrax (8/8) is now on the board.
    tyrax = [m for m in p1.field if m.id == "TLC_433t"]
    assert len(tyrax) == 1
    assert (tyrax[0].atk, tyrax[0].max_health) == (8, 8)


def test_reanimate_the_terror_partial_spend_no_reward():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    quest = p1.give("TLC_433")
    quest.play()
    p1.corpses = 17
    game.cheat_action(p1.hero, [SpendCorpses(p1, 17)])
    assert quest.zone == Zone.SECRET
    assert quest.progress == 17
    assert not [m for m in p1.field if m.id == "TLC_433t"]


# TLC_434 — Discover an Undead. Spend 5 Corpses to keep all 3 instead.
def test_paleomancy_keeps_all_three_with_five_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 5
    spell = p1.give("TLC_434")
    spell.play()
    # No Discover choice opened; all three Undead landed in hand and 5
    # Corpses were spent.
    assert p1.choice is None
    assert len(p1.hand) == 3
    assert all(Race.UNDEAD in c.races for c in p1.hand)
    assert p1.corpses == 0


def test_paleomancy_discovers_one_without_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 4  # not enough
    spell = p1.give("TLC_434")
    spell.play()
    # A Discover choice opened with three Undead.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    assert all(Race.UNDEAD in c.races for c in p1.choice.cards)
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 1
    assert p1.corpses == 4  # nothing spent


# TLC_435 — Discover a Frost Rune card.
def test_crypt_map_discovers_frost_rune_card():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    spell = p1.give("TLC_435")
    spell.play()
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    # Every option is a DK card with at least one Frost Rune.
    for c in p1.choice.cards:
        assert c.data.tags.get(GameTag.COST_FROST, 0) >= 1
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 1


# TLC_436 — Rush, Lifesteal. Costs Corpses instead of Mana.
def test_reanimated_pterrordax_costs_corpses_not_mana():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    p1.corpses = 3
    p1.used_mana = p1.max_mana  # no mana available
    assert p1.mana == 0
    ptero = p1.give("TLC_436")
    # Mana cost is zeroed (paid in Corpses), so it is playable at 0 mana.
    assert ptero.cost == 0
    ptero.play()
    assert ptero.zone == Zone.PLAY
    # 3 Corpses spent (the CARD_ALTERNATE_COST, not the mana cost of 5).
    assert p1.corpses == 0
    # Rush + Lifesteal live in data.
    assert ptero.rush
    assert ptero.lifesteal


# TLC_439 — Deal 2 damage to all enemy minions. Enemy minions cost (2) more
# next turn.
def test_wave_of_tar_damages_board_and_taxes_hand():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Two enemy minions on board with enough health to survive 2 damage.
    a = p2.summon(CHILLWIND)  # 4/5
    b = p2.summon(HARVEST_GOLEM)  # 2/3
    a.damage = 0
    b.damage = 0
    # An enemy minion in hand to receive the +2 cost.
    hand_minion = p2.give(CHILLWIND)
    base_cost = hand_minion.cost
    spell = p1.give("TLC_439")
    spell.play()
    assert a.damage == 2
    assert b.damage == 2
    assert hand_minion.cost == base_cost + 2


# TLC_440 — Deal 4 damage and draw a card. Kindred: Draw another.
def test_cryosleep_deals_four_and_draws_one_without_kindred():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    for _ in range(3):
        p1.card(WISP, zone=Zone.DECK)
    target = p2.summon(CHILLWIND)  # 4/5
    target.damage = 0
    p1.schools_played_last_turn = set()  # Kindred inactive
    spell = p1.give("TLC_440")
    spell.play(target=target)
    assert target.damage == 4
    assert len(p1.hand) == 1  # drew exactly one


def test_cryosleep_kindred_draws_two():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    for _ in range(3):
        p1.card(WISP, zone=Zone.DECK)
    target = p2.summon(CHILLWIND)
    target.damage = 0
    # Cryosleep is a FROST spell; a Frost spell played last turn arms Kindred.
    p1.schools_played_last_turn = {SpellSchool.FROST}
    spell = p1.give("TLC_440")
    spell.play(target=target)
    assert target.damage == 4
    assert len(p1.hand) == 2  # drew two


# TLC_443 — Reborn. Deathrattle: Summon a 2/2 Undead Beast with Taunt.
def test_reluctant_wrangler_deathrattle_summons_ossodon():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    wrangler = p1.summon("TLC_443")
    assert wrangler.reborn  # Reborn lives in data
    wrangler.destroy()
    # Deathrattle summons the 2/2 Taunt token; Reborn also brings back a 1/1
    # copy of the Wrangler. Verify the Ossodon token specifically.
    ossodon = [m for m in p1.field if m.id == "TLC_443t"]
    assert len(ossodon) == 1
    oss = ossodon[0]
    assert (oss.atk, oss.max_health) == (2, 2)
    assert oss.taunt
    assert Race.UNDEAD in oss.races


# TLC_810 — Battlecry: Summon two Deathrattle minions from your deck. They
# fight!
def test_high_cultist_herenn_summons_two_deathrattle_and_they_fight():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    # Beef our hero so the Leper Gnome deathrattles (deal 2 to enemy hero,
    # which is our opponent — irrelevant) can't end the game.
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0
    # Exactly two eligible Deathrattle minions in deck. Leper Gnome is a 2/1:
    # when the two fight, each takes 2 -> both die. They draw nothing, so the
    # deck keeps its non-deathrattle decoy.
    p1.card(LEPER_GNOME, zone=Zone.DECK)
    p1.card(LEPER_GNOME, zone=Zone.DECK)
    # A non-deathrattle minion that must NOT be summoned.
    p1.card(CHILLWIND, zone=Zone.DECK)
    herenn = p1.give("TLC_810")
    herenn.play()
    # Both 2/1 Leper Gnomes fought and died; only Herenn remains on board.
    assert not [m for m in p1.field if m.id == LEPER_GNOME]
    assert "TLC_810" in [m.id for m in p1.field]
    # The Chillwind (no deathrattle) was never pulled from the deck.
    assert CHILLWIND in [c.id for c in p1.deck]
