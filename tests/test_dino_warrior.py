"""The Lost City of Un'Goro mini-set (Dinosaurs, DINO_) — Warrior card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Zone


def test_dino_400_barricade_basher():
    # Whenever you gain Armor, gain +2/+2 and attack a random enemy minion.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2

    basher = p1.summon("DINO_400")
    assert basher.atk == 4 and basher.max_health == 3

    # Single enemy minion with 0 attack (so it can't kill Basher back) and a
    # large health pool so it survives the forced attack — lets us assert the
    # exact damage = Basher's (buffed) attack.
    enemy = p2.summon("CS2_172")  # Bloodfen Raptor 3/2
    enemy.atk = 0
    enemy.max_health = 30
    enemy.damage = 0

    p1.hero.armor = 0
    game.queue_actions(p1.hero, [GainArmor(p1.hero, 1)])

    # +2/+2 applied: 4/3 -> 6/5.
    assert basher.atk == 6 and basher.max_health == 5
    # Basher attacked the only enemy minion for its post-buff attack (6).
    assert enemy.damage == 6
    # No friendly hero retaliation damage to Basher (enemy has 0 attack).
    assert basher.damage == 0


def test_dino_400_barricade_basher_no_enemy_minion():
    # Armor gain still grants the buff even with no enemy minion to attack.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1

    basher = p1.summon("DINO_400")
    assert basher.atk == 4 and basher.max_health == 3

    p1.hero.armor = 0
    game.queue_actions(p1.hero, [GainArmor(p1.hero, 5)])

    assert p1.hero.armor == 5
    assert basher.atk == 6 and basher.max_health == 5
    assert basher.damage == 0


def test_dino_401_dracorex_cleaves_other_enemy_minions():
    # Rush. After this attacks an enemy minion, it damages ALL other enemy
    # minions (for its Attack = 5).
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2

    drac = p1.summon("DINO_401")
    assert drac.atk == 5 and drac.max_health == 12
    assert drac.rush

    # Defender + two bystanders, all 0-attack and high-health so nothing dies
    # mid-effect and we can assert exact damage.
    defender = p2.summon("CS2_172")
    other1 = p2.summon("CS2_172")
    other2 = p2.summon("CS2_172")
    for m in (defender, other1, other2):
        m.atk = 0
        m.max_health = 30
        m.damage = 0

    drac.attack(defender)

    # Defender took only normal combat damage (5).
    assert defender.damage == 5
    # The two OTHER enemy minions each took the cleave for Dracorex's Attack (5).
    assert other1.damage == 5
    assert other2.damage == 5
    # Dracorex took no return damage (defenders have 0 attack).
    assert drac.damage == 0


def test_dino_433_guard_duty_summons_three_taunt_minions():
    # Summon a random 6, 4, and 2-Cost Taunt minion.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1

    pre = len(p1.field)
    p1.give("DINO_433").play()

    summoned = p1.field[pre:]
    assert len(summoned) == 3

    costs = sorted(m.cost for m in summoned)
    assert costs == [2, 4, 6]

    # Every summoned minion is a Taunt minion.
    for m in summoned:
        assert m.taunt
        assert m.type == CardType.MINION
