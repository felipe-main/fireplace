"""Across the Timeways mini-set (END_) — Tier-1 audit fixes.

  * END_012 Hand of Infinity — "Can't attack heroes" must restrict the wielding
    hero to minion targets (engine: Hero aggregates the weapon's
    cannot_attack_heroes).
  * END_004 Remnant of Rage — costs (1) less per minion that died this turn,
    counting BOTH players' deaths (engine: game.minions_killed_this_turn).
"""
from utils import *


def test_hand_of_infinity_cannot_attack_heroes():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    weapon = p1.give("END_012")
    weapon.play()
    # Battlecry set Attack to INFINITY this turn.
    assert p1.hero.atk >= 2147483647
    # The "Can't attack heroes" clause: the enemy hero is NOT a legal target,
    # but an enemy minion is.
    enemy_minion = p2.summon("CS2_182")  # Chillwind Yeti
    assert p1.hero.cannot_attack_heroes
    assert p2.hero not in p1.hero.attack_targets
    assert enemy_minion in p1.hero.attack_targets


def test_remnant_of_rage_cost_counts_both_sides_deaths():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    remnant = p1.give("END_004")
    assert remnant.cost == 7  # printed base cost, no deaths yet

    # One friendly and two enemy minions die this turn → 3 deaths total.
    friendly = p1.summon("CS2_171")  # 1/1
    e1 = p2.summon("CS2_171")
    e2 = p2.summon("CS2_171")
    for m in (friendly, e1, e2):
        m.destroy()
    game.process_deaths()

    # 7 - 3 = 4, counting both sides (not just the controller's one death).
    assert remnant.cost == 4
