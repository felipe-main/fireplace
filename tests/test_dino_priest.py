"""The Lost City of Un'Goro mini-set — Priest unit tests (DINO_)."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Zone


WISP = "CS2_231"            # 1/1 vanilla minion
BOULDERFIST = "CS2_200"     # 6/6/7 vanilla minion (no Taunt)


def test_ritual_of_life_summons_2_2_copy():
    # Discover a 3-Cost minion. Summon a 2/2 copy of it.
    # The Discovered option is added to the board as a 2/2 copy; it is NOT
    # placed in hand.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    # Clear the board so we can read the summoned copy unambiguously.
    assert len(p1.field) == 0
    pre_hand = len(p1.hand)

    ritual = p1.give("DINO_426")
    ritual.play()

    # A Discover choice should be open with three 3-Cost minions.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    for c in p1.choice.cards:
        assert c.cost == 3
        assert c.type == CardType.MINION
    chosen = p1.choice.cards[0]
    chosen_id = chosen.id
    p1.choice.choose(chosen)

    # The copy is on the board, set to 2/2, and the Discovered minion was NOT
    # added to hand (only the spell itself left hand, then returned to baseline:
    # give +1, play -1 -> net zero vs. pre_hand).
    assert len(p1.field) == 1
    copy = p1.field[0]
    assert copy.id == chosen_id
    assert copy.atk == 2
    assert copy.max_health == 2
    assert copy.health == 2
    assert len(p1.hand) == pre_hand
    assert chosen_id not in [c.id for c in p1.hand]


def test_behemoth_mask_sets_stats_and_forces_attack():
    # Set a minion's stats to 8/10 and give it Lifesteal. Force a random
    # enemy minion to attack it.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2

    # Friendly target: a damaged Wisp (1/1) becomes 8/10 with full Health.
    target = p1.summon(WISP)
    # One enemy minion that will be forced to attack: a 6/7 Boulderfist.
    enemy = p2.summon(BOULDERFIST)
    assert enemy.atk == 6

    mask = p1.give("DINO_428")
    mask.play(target=target)

    # Stats set to 8/10, Lifesteal granted.
    assert target.atk == 8
    assert target.max_health == 10
    assert target.lifesteal

    # The single enemy minion was forced to attack the masked target.
    # Boulderfist (6 atk) dealt 6 to the 8/10 target -> 4 remaining health.
    assert target.health == 4
    assert target.damage == 6
    # The masked target struck back for 8, killing the 6/7 Boulderfist.
    assert enemy.dead
    # Lifesteal: the 8-damage swing healed our hero (started at 30, undamaged).
    # Hero was full, so heal overflow is wasted — assert no hero damage instead.
    assert p1.hero.health == 30


def test_behemoth_mask_lifesteal_heals_hero():
    # When the masked minion deals combat damage, Lifesteal heals the hero.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2

    p1.hero.damage = 10
    assert p1.hero.health == 20

    target = p1.summon(WISP)
    enemy = p2.summon(BOULDERFIST)

    mask = p1.give("DINO_428")
    mask.play(target=target)

    # Masked target (8 atk, Lifesteal) hit the Boulderfist for 8 -> heals 8.
    assert target.lifesteal
    assert p1.hero.health == 28


def test_atlasaurus_taunt_and_deathrattle_summons_taunt():
    # Taunt. Deathrattle: Summon a random Taunt minion that costs (5) or more.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1

    atlas = p1.summon("DINO_431")
    assert atlas.taunt
    assert atlas.atk == 5
    assert atlas.max_health == 10

    assert len(p1.field) == 1
    atlas.destroy()
    game.process_deaths()

    # Exactly one minion summoned: a Taunt minion costing 5 or more.
    assert len(p1.field) == 1
    summoned = p1.field[0]
    assert summoned.taunt
    assert (summoned.data.cost or 0) >= 5
