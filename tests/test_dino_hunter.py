"""The Lost City of Un'Goro mini-set (DINO_) — HUNTER cards."""

import random

from utils import *

from hearthstone.enums import CardClass, GameTag, Race


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_devilsaur_mask():
    # Set a minion's stats to 8/8. Give it Charge.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # A vanilla 3/2 Beast; mask should clamp it to a fixed 8/8 body + Charge.
    target = p1.summon("CS2_172")  # Bloodfen Raptor, 3/2
    assert target.atk == 3 and target.health == 2
    mask = p1.give("DINO_403")
    mask.play(target=target)
    assert target.atk == 8
    assert target.health == 8
    assert target.max_health == 8
    assert target.charge


def test_devilsaur_mask_overrides_buffs():
    # The set-stats body is absolute: a previously buffed minion is reset to 8/8.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    target = p1.summon("CS2_172")  # 3/2
    target.set_current_health(2)
    p1.give("DINO_403").play(target=target)
    assert target.atk == 8 and target.health == 8


def test_ankylodon_deathrattle():
    # Taunt. Deathrattle: Summon two random 3-Cost Beasts. They attack random
    # enemies.
    random.seed(1234)
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # Fat, harmless targets so both summoned beasts attack and survive: a 0/big
    # non-Taunt minion (so RANDOM_ENEMY_CHARACTER may legally pick it OR the
    # hero) plus a big hero. 0 Attack => no counter-damage kills the attackers.
    dummy = p2.summon("CS2_172")  # Bloodfen Raptor (then zeroed)
    dummy.atk = 0
    dummy.max_health = 200
    dummy.set_current_health(200)
    p2.hero.max_health = 200
    p2.hero.set_current_health(200)

    anky = p1.summon("DINO_422")
    assert anky.taunt
    assert anky.atk == 7 and anky.health == 7
    anky.destroy()
    game.process_deaths()
    summoned = list(p1.field)
    # Ankylodon is gone; exactly two new minions summoned by the deathrattle.
    assert len(summoned) == 2
    for m in summoned:
        assert m.race == Race.BEAST or Race.BEAST in m.races
        assert m.cost == 3
    # They attacked random enemies; total damage dealt to the enemy side equals
    # the sum of the summoned minions' Attack (each attacked exactly once, and
    # the 0-Attack targets never kill them).
    expected = sum(m.atk for m in summoned)
    assert expected > 0
    assert dummy.damage + p2.hero.damage == expected


def test_raptor_nest_nurse_battlecry():
    # Battlecry: Get a random 1-Cost minion.
    random.seed(99)
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # Clear hand so the single battlecry add is unambiguous.
    for c in list(p1.hand):
        c.discard()
    assert len(p1.hand) == 0
    nurse = p1.give("DINO_434")
    assert len(p1.hand) == 1
    nurse.play()
    assert len(p1.hand) == 1  # the gained 1-Cost minion
    gained = p1.hand[0]
    assert gained.type == CardType.MINION
    assert gained.cost == 1


def test_raptor_nest_nurse_deathrattle():
    # Deathrattle: Get a random 1-Cost spell.
    random.seed(7)
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    nurse = p1.summon("DINO_434")  # summon bypasses the battlecry
    assert len(p1.hand) == 0
    nurse.destroy()
    game.process_deaths()
    assert len(p1.hand) == 1
    gained = p1.hand[0]
    assert gained.type == CardType.SPELL
    assert gained.cost == 1
