"""Emerald Dream mini-set (Firelands, FIR_) — DEMONHUNTER unit tests.

Covers:
  FIR_902 Sigil of Cinder  (start-of-next-turn 6 damage split among enemies)
  FIR_904 Felfire Blaze     (after you cast a Fel spell: destroy + 2 AoE enemies)
  FIR_952 Scorchreaver      (Battlecry: Discover a Fel spell; -1 Fel spells in hand)
"""

from utils import *

from hearthstone.enums import CardType, Zone, SpellSchool


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# FIR_902 — Sigil of Cinder: at the start of your next turn, deal 6 damage
# randomly split among all enemies. With only the enemy hero alive (beefed so
# it absorbs all six shots), all 6 land on the hero, then the Sigil destroys
# itself.
def test_sigil_of_cinder_deals_six_to_lone_enemy_next_turn():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player  # the Sigil's controller plays it this turn
    p2 = p1.opponent
    p2.hero.max_health = 80
    p2.hero.damage = 0
    sigil = p1.give("FIR_902")
    sigil.play()
    # A Sigil lingers in the SECRET zone waiting for its controller's next turn.
    assert sigil.zone == Zone.SECRET
    # End our turn, opponent's turn, back to us -> trigger at start.
    game.end_turn()
    game.end_turn()
    # All six 1-damage shots hit the only living enemy (the hero).
    assert p2.hero.damage == 6
    # The Sigil destroyed itself after firing.
    assert sigil.zone == Zone.GRAVEYARD


# FIR_902 — split is exact: with a beefy enemy hero AND a beefy enemy minion
# alive, the six shots distribute across them and the TOTAL is exactly 6.
def test_sigil_of_cinder_total_damage_is_exactly_six():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    p2 = p1.opponent
    p2.hero.max_health = 80
    p2.hero.damage = 0
    enemy = p2.summon("CS2_186")  # War Golem 7/7
    enemy.max_health = 80
    enemy.damage = 0
    sigil = p1.give("FIR_902")
    sigil.play()
    game.end_turn()
    game.end_turn()
    assert p2.hero.damage + enemy.damage == 6
    assert sigil.zone == Zone.GRAVEYARD


# FIR_904 — Felfire Blaze: after you cast a Fel spell, destroy this and deal 2
# damage to all enemies. Casting a non-Fel spell must NOT trigger it.
def test_felfire_blaze_triggers_on_fel_spell():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    p2 = p1.opponent
    blaze = p1.summon("FIR_904")
    assert (blaze.atk, blaze.max_health) == (2, 3)
    p2.hero.max_health = 80
    p2.hero.damage = 0
    enemy = p2.summon("CS2_186")  # War Golem 7/7, survives 2 damage
    enemy.max_health = 80
    enemy.damage = 0
    # BT_035 Chaos Strike: a Fel spell that does NOT itself damage enemies
    # (gives hero +2 Attack, draws), so the only damage is Felfire Blaze's 2.
    chaos = p1.give("BT_035")
    assert chaos.spell_school == SpellSchool.FEL
    chaos.play()
    _resolve_choices(p1)
    # Destroyed itself.
    assert blaze.zone == Zone.GRAVEYARD
    # Dealt exactly 2 to all enemies (hero + minion).
    assert p2.hero.damage == 2
    assert enemy.damage == 2


def test_felfire_blaze_ignores_non_fel_spell():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    p2 = p1.opponent
    blaze = p1.summon("FIR_904")
    p2.hero.max_health = 80
    p2.hero.damage = 0
    # The Coin is a non-Fel spell (no spell school). Casting it must NOT trigger.
    coin = p1.give("GAME_005")
    assert coin.spell_school != SpellSchool.FEL
    coin.play()
    _resolve_choices(p1)
    assert blaze.zone == Zone.PLAY
    assert p2.hero.damage == 0


# FIR_952 — Scorchreaver: Battlecry: Discover a Fel spell; reduce the Cost of
# Fel spells in your hand by (1).
def test_scorchreaver_discovers_fel_spell_and_discounts_hand():
    game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.current_player
    for c in p1.hand[:]:
        c.discard()
    # Two Fel spells in hand (BT_753 Mana Burn cost 1, BT_035 Chaos Strike
    # cost 2) plus one NON-Fel spell (Coin) that must be untouched.
    mana_burn = p1.give("BT_753")
    chaos = p1.give("BT_035")
    coin = p1.give("GAME_005")
    assert mana_burn.spell_school == SpellSchool.FEL
    assert chaos.spell_school == SpellSchool.FEL
    assert (mana_burn.cost, chaos.cost) == (1, 2)
    coin_cost = coin.cost

    reaver = p1.give("FIR_952")
    assert (reaver.atk, reaver.max_health) == (4, 4)
    reaver.play()
    # A Discover of Fel spells opened: every option is a Fel spell.
    assert p1.choice is not None
    options = list(p1.choice.cards)
    assert len(options) == 3
    for opt in options:
        assert opt.spell_school == SpellSchool.FEL
    discovered = options[0]
    p1.choice.choose(discovered)

    # Fel spells already in hand are each (1) cheaper.
    assert mana_burn.cost == 0  # 1 - 1, clamped to 0
    assert chaos.cost == 1      # 2 - 1
    # The non-Fel Coin is untouched.
    assert coin.cost == coin_cost
    # The discovered Fel spell is in hand. (It was added AFTER the buff pass,
    # so it carries no discount — matches the printed "Fel spells in your hand"
    # snapshot at battlecry time.)
    assert any(h.id == discovered.id for h in p1.hand)
