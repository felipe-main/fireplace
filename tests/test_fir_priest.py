"""Emerald Dream mini-set (Firelands, FIR_) — PRIEST collectible cards.

One tight test per card:
  FIR_777 (Spirit of the Kaldorei), FIR_916 (Smoldering Ascent),
  FIR_918 (Light of the New Moon).
"""

from utils import *

from hearthstone.enums import CardClass, Zone


# ---------------------------------------------------------------------------
# FIR_777 — Spirit of the Kaldorei: Taunt, Lifesteal. Battlecry: If you used
# your Hero Power this turn, gain +2/+2.
# ---------------------------------------------------------------------------
def test_spirit_of_the_kaldorei_no_hero_power():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    assert p1.hero.power.activations_this_turn == 0
    c = p1.give("FIR_777")
    c.play()
    # No Hero Power used this turn -> base 1/3, but Taunt + Lifesteal present.
    assert c.atk == 1
    assert c.health == 3
    assert c.taunt
    assert c.lifesteal


def test_spirit_of_the_kaldorei_after_hero_power():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    # Use the Priest Hero Power (Lesser Heal) this turn.
    p1.hero.power.use(target=p1.hero)
    assert p1.hero.power.activations_this_turn == 1
    c = p1.give("FIR_777")
    c.play()
    # +2/+2 from the battlecry: 1/3 -> 3/5.
    assert c.atk == 3
    assert c.health == 5
    assert c.taunt
    assert c.lifesteal


# ---------------------------------------------------------------------------
# FIR_916 — Smoldering Ascent: Deal {0} damage to all enemy minions.
# (Upgrades each turn, but discards after {1}!)  Default smolder: base 1,
# +1 per held turn, discard after 3 turns.
# ---------------------------------------------------------------------------
def test_smoldering_ascent_base_one_damage():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    a = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    a.max_health = 80
    a.damage = 0
    b = p2.summon("CS2_171")  # Stonetusk Boar 1/1
    b.max_health = 80
    b.damage = 0
    friendly = p1.summon("CS2_182")  # not an enemy -> untouched
    friendly.max_health = 80
    friendly.damage = 0
    s = p1.give("FIR_916")
    s.play()
    # Base smolder level = 1 -> 1 damage to every enemy minion only.
    assert a.damage == 1
    assert b.damage == 1
    assert friendly.damage == 0


def test_smoldering_ascent_upgrades_in_hand():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    s = p1.give("FIR_916")
    # Two of the controller's turn-begins held in hand: level 1 -> 3.
    game.end_turn(); game.end_turn()   # back to p1: +1
    game.end_turn(); game.end_turn()   # back to p1: +1
    assert s.zone == Zone.HAND
    a = p2.summon("CS2_182")
    a.max_health = 80
    a.damage = 0
    s.play()
    assert a.damage == 3


def test_smoldering_ascent_discards_after_three_turns():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    s = p1.give("FIR_916")
    assert s.zone == Zone.HAND
    # Three of the controller's turn-begins -> discarded.
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    # discard() removes the card from the game.
    assert s.zone == Zone.REMOVEDFROMGAME
    assert s not in p1.hand


# ---------------------------------------------------------------------------
# FIR_918 — Light of the New Moon: Give a minion +3/+3. (Cast 4 spells to
# return this to your hand when played.)
# ---------------------------------------------------------------------------
def test_light_of_the_new_moon_base_buffs_no_bounce():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.discard_hand()
    target = p1.summon("CS2_182")  # 4/5
    l = p1.give("FIR_918")
    l.play(target=target)
    # +3/+3 -> 7/8.
    assert target.atk == 7
    assert target.health == 8
    # Fewer than 4 spells this game -> does NOT return to hand.
    assert l.zone == Zone.GRAVEYARD
    assert len(p1.hand) == 0


def test_light_of_the_new_moon_fourth_spell_bounces():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.discard_hand()
    target = p1.summon("CS2_182")  # 4/5
    # This is the player's 4th spell this game (counter not yet incremented
    # for the current spell at play-time).
    p1.spells_played_this_game = 3
    l = p1.give("FIR_918")
    l.play(target=target)
    # Still buffs +3/+3 -> 7/8.
    assert target.atk == 7
    assert target.health == 8
    # 4th spell -> a fresh copy returns to hand.
    assert len(p1.hand) == 1
    assert p1.hand[0].id == "FIR_918"
