"""Lost City of Un'Goro mini-set (DINO_) — Warlock cards."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Zone


BLOODFEN_RAPTOR = "CS2_172"  # 3/3/2 Beast
WISP_ID = "CS2_231"          # 0/1/1, not a Beast
CHICKEN_BEAST = "GVG_092t"   # 1/1 Beast (Chicken)
BOULDERFIST = "CS2_200"      # 6/6/7 vanilla minion (set-stats target)


def test_dino_131_summons_lifesteal_beast_from_deck():
    # Deathrattle: Summon a random Beast from your deck. Give it Lifesteal.
    # Empty decks so the only Beast available is the one we plant.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Only one Beast in the deck so the summon is deterministic.
    p1.give(BLOODFEN_RAPTOR).shuffle_into_deck()
    animancer = p1.summon("DINO_131")
    assert len(p1.field) == 1
    animancer.destroy()
    game.process_deaths()
    # Animancer gone, the Beast pulled from deck and on board.
    assert len(p1.field) == 1
    beast = p1.field[0]
    assert beast.id == BLOODFEN_RAPTOR
    assert beast.lifesteal is True
    # It came out of the deck, not from nowhere.
    assert not any(c.id == BLOODFEN_RAPTOR for c in p1.deck)


def test_dino_131_no_beast_in_deck():
    # No Beast in deck -> nothing summoned (and no crash).
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.give(WISP_ID).shuffle_into_deck()  # not a Beast
    animancer = p1.summon("DINO_131")
    animancer.destroy()
    game.process_deaths()
    assert len(p1.field) == 0


def test_dino_132_end_of_turn_hits_random_enemy_minion():
    # Taunt. At the end of your turn, deal 5 damage to a random enemy minion.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    asphyx = p1.summon("DINO_132")
    assert asphyx.taunt is True
    # Single enemy minion with enough health to survive and show exactly 5.
    enemy = p2.summon(BOULDERFIST)  # 6/7
    enemy.max_health = 30
    enemy.damage = 0
    game.end_turn()  # p1 turn ends -> trigger fires
    assert enemy.damage == 5


def test_dino_132_no_enemy_minion_no_crash():
    # End-of-turn trigger with no enemy minions does nothing (no self/hero hit).
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    p1.summon("DINO_132")
    hero_hp = p2.hero.health
    game.end_turn()
    assert p2.hero.health == hero_hp
    assert len(p2.field) == 0


def test_dino_402_sets_stats_and_fills_board():
    # Set a friendly minion's stats to 1/1. Fill your board with copies of it.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    target = p1.summon(BOULDERFIST)  # 6/7
    assert target.atk == 6 and target.health == 7
    mask = p1.give("DINO_402")
    mask.play(target=target)
    # Board is full of 1/1 copies of the (now 1/1) target.
    assert len(p1.field) == game.MAX_MINIONS_ON_FIELD
    for m in p1.field:
        assert m.id == BOULDERFIST
        assert m.atk == 1
        assert m.health == 1
    # The original chosen minion was itself set to 1/1.
    assert target.atk == 1 and target.health == 1


def test_dino_402_overwrites_prior_buffs():
    # Set-to-1/1 must wipe a prior stat buff (true SET, not additive).
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    target = p1.summon(CHICKEN_BEAST)  # 1/1 Beast
    target.atk = 5
    target.max_health = 5
    target.damage = 0
    assert target.atk == 5 and target.health == 5
    mask = p1.give("DINO_402")
    mask.play(target=target)
    assert target.atk == 1 and target.health == 1
    for m in p1.field:
        assert m.atk == 1 and m.health == 1
