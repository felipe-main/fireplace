"""The Great Dark Beyond — PALADIN.

Tight unit tests asserting the printed behaviour of every collectible Paladin
card in the GDB_ (SPACE) set. 10 collectible cards covered.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards


# GDB_144 — Lumia: Lifesteal. After a hero takes damage, they become Immune for
# the rest of the turn.
def test_lumia_has_lifesteal():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    m = game.player1.summon("GDB_144")
    assert m.lifesteal
    assert (m.atk, m.max_health) == (9, 9)


def test_lumia_hero_becomes_immune_after_taking_damage():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    game.player1.summon("GDB_144")
    # Damage p1's hero once: it takes the hit, then becomes Immune.
    p1.hero.max_health = 30
    p1.hero.damage = 0
    from fireplace.actions import Hit
    game.queue_actions(p2.hero, [Hit(p1.hero, 5)])
    assert p1.hero.health == 25
    assert p1.hero.immune
    # A second hit lands on an Immune hero -> no further damage.
    game.queue_actions(p2.hero, [Hit(p1.hero, 5)])
    assert p1.hero.health == 25


# GDB_721 — Interstellar Wayfarer: Divine Shield. Battlecry: Reduce the Cost of
# your Librams by (1) this game.
def test_interstellar_wayfarer_divine_shield_and_libram_discount():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    libram = p1.give("GDB_139")  # Libram of Faith, base cost 6
    assert libram.cost == 6
    wayfarer = p1.give("GDB_721")
    wayfarer.play()
    assert wayfarer.divine_shield
    # Librams now cost (1) less for the game.
    assert libram.cost == 5
    assert p1.libram_discount == 1


# GDB_728 — Interstellar Researcher: Battlecry and Spellburst: Draw a Libram.
def test_interstellar_researcher_battlecry_draws_libram():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    libram = p1.give("GDB_137")  # Libram of Clarity (LIBRAM tag)
    libram.zone = Zone.DECK
    decoy = p1.give("CS2_029")   # Fireball, not a Libram
    decoy.zone = Zone.DECK
    researcher = p1.give("GDB_728")
    researcher.play()
    # Battlecry draws the Libram only.
    assert libram.zone == Zone.HAND
    assert decoy.zone == Zone.DECK


def test_interstellar_researcher_spellburst_draws_libram():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    researcher = p1.summon("GDB_728")  # bypass battlecry, no draw yet
    libram = p1.give("GDB_137")
    libram.zone = Zone.DECK
    decoy = p1.give("CS2_029")
    decoy.zone = Zone.DECK
    # Cast any spell -> Spellburst triggers and draws the Libram.
    p1.give("CS2_008").play(target=p1.hero)  # Moonfire on own hero
    assert libram.zone == Zone.HAND
    assert decoy.zone == Zone.DECK


# GDB_726 — Interstellar Starslicer (Weapon): Battlecry and Deathrattle: Reduce
# the Cost of your Librams by (1) this game.
def test_interstellar_starslicer_battlecry_and_deathrattle_discount():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    libram = p1.give("GDB_139")  # cost 6
    weapon = p1.give("GDB_726")
    weapon.play()
    # Battlecry: -1
    assert p1.libram_discount == 1
    assert libram.cost == 5
    # Destroy the weapon -> Deathrattle: another -1
    weapon.destroy()
    game.process_deaths()
    assert p1.libram_discount == 2
    assert libram.cost == 4


# GDB_137 — Libram of Clarity: Draw 2 minions. If this costs (0), give them
# +2/+1.
def test_libram_of_clarity_draws_two_minions():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    m1 = p1.give("CS2_172"); m1.zone = Zone.DECK  # Bloodfen Raptor 3/2
    m2 = p1.give("CS2_182"); m2.zone = Zone.DECK  # Chillwind Yeti 4/5
    spell_decoy = p1.give("CS2_029"); spell_decoy.zone = Zone.DECK  # Fireball
    clarity = p1.give("GDB_137")
    assert clarity.cost == 3  # not free -> no buff
    clarity.play()
    assert m1.zone == Zone.HAND
    assert m2.zone == Zone.HAND
    assert spell_decoy.zone == Zone.DECK
    # Not free -> no +2/+1 buff.
    assert m1.atk == 3 and m1.max_health == 2
    assert m2.atk == 4 and m2.max_health == 5


def test_libram_of_clarity_free_buffs_drawn_minions():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    m1 = p1.give("CS2_172"); m1.zone = Zone.DECK  # 3/2
    m2 = p1.give("CS2_182"); m2.zone = Zone.DECK  # 4/5
    clarity = p1.give("GDB_137")
    # Drive the COST tag to 0 (the value the "If this costs (0)" check reads).
    clarity.tags[GameTag.COST] = 0
    assert clarity.cost == 0
    clarity.play()
    assert m1.zone == Zone.HAND and m2.zone == Zone.HAND
    # Free -> +2/+1 on both drawn minions.
    assert m1.atk == 5 and m1.max_health == 3
    assert m2.atk == 6 and m2.max_health == 6


# GDB_138 — Libram of Divinity: Give a minion +3/+3. If this costs (0), return
# this to your hand at the end of your turn. (Approximation: the engine gives a
# copy immediately when free — tracked in review.csv.)
def test_libram_of_divinity_buffs_minion():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    target = p1.summon("CS2_172")  # 3/2
    spell = p1.give("GDB_138")
    assert spell.cost == 4
    spell.play(target=target)
    assert target.atk == 6
    assert target.max_health == 5
    # Not free -> no copy returned to hand.
    assert not any(c.id == "GDB_138" for c in p1.hand)


def test_libram_of_divinity_free_returns_copy():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    target = p1.summon("CS2_172")  # 3/2
    spell = p1.give("GDB_138")
    spell.tags[GameTag.COST] = 0  # the value "If this costs (0)" reads
    assert spell.cost == 0
    spell.play(target=target)
    assert target.atk == 6 and target.max_health == 5
    # Free -> a fresh GDB_138 copy is back in hand.
    assert len([c for c in p1.hand if c.id == "GDB_138"]) == 1


# GDB_139 — Libram of Faith: Summon three 3/3 Draenei with Divine Shield. If
# this costs (0), give them Rush.
def test_libram_of_faith_summons_three_shielded_draenei():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    spell = p1.give("GDB_139")
    assert spell.cost == 6
    spell.play()
    summoned = [m for m in p1.field if m.id == "GDB_139t"]
    assert len(summoned) == 3
    for m in summoned:
        assert (m.atk, m.max_health) == (3, 3)
        assert m.divine_shield
        assert Race.DRAENEI in m.races
        # Not free -> no Rush.
        assert not m.rush


def test_libram_of_faith_free_grants_rush():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    spell = p1.give("GDB_139")
    spell.tags[GameTag.COST] = 0  # the value "If this costs (0)" reads
    assert spell.cost == 0
    spell.play()
    summoned = [m for m in p1.field if m.id == "GDB_139t"]
    assert len(summoned) == 3
    for m in summoned:
        assert m.divine_shield
        assert m.rush


# GDB_140 — Celestial Aura: While you have exactly 1 minion in play, its Attack
# and Health are 10. Lasts 2 turns. (Engine approximates as a one-shot set on
# cast — tracked in review.csv.)
def test_celestial_aura_sets_lone_minion_to_ten_ten():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    m = p1.summon("CS2_172")  # 3/2, the only minion
    aura = p1.give("GDB_140")
    aura.play()
    assert m.atk == 10
    assert m.max_health == 10
    assert m.health == 10


def test_celestial_aura_no_effect_with_two_minions():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    a = p1.summon("CS2_172")  # 3/2
    b = p1.summon("CS2_182")  # 4/5
    aura = p1.give("GDB_140")
    aura.play()
    # More than one minion -> no minion is set to 10/10.
    assert a.atk == 3 and a.max_health == 2
    assert b.atk == 4 and b.max_health == 5


# GDB_141 — Yrel, Beacon of Hope: Rush. Deathrattle: Get three different Librams
# from an older timeline!
def test_yrel_has_rush():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    m = game.player1.summon("GDB_141")
    assert m.rush
    assert Race.DRAENEI in m.races


def test_yrel_deathrattle_gives_three_different_librams():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    yrel = p1.summon("GDB_141")
    pre = [c.id for c in p1.hand]
    yrel.destroy()
    game.process_deaths()
    # Three cards added.
    assert len(p1.hand) == len(pre) + 3
    libs = p1.hand[-3:]
    for c in libs:
        assert c.libram, f"{c.id} is not a Libram"
    # Three *different* Librams.
    assert len({c.id for c in libs}) == 3


# GDB_462 — Orbital Satellite: Discover a Draenei. If you played an adjacent
# card this turn, Discover another.
def test_orbital_satellite_discovers_a_draenei():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    pre = len(p1.hand)
    sat = p1.give("GDB_462")
    sat.play()
    # Resolve the Discover; the offered cards must all be Draenei.
    assert p1.choice is not None
    for card in p1.choice.cards:
        assert Race.DRAENEI in card.races
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    # No adjacent play this turn -> exactly one Discover.
    assert p1.choice is None
    assert any(c.id == chosen.id for c in p1.hand)


def test_orbital_satellite_no_second_discover_without_adjacent_play():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    sat = p1.give("GDB_462")
    pre_hand = len(p1.hand) - 1  # exclude the satellite itself
    sat.play()
    n = 0
    while p1.choice:
        n += 1
        p1.choice.choose(p1.choice.cards[0])
    assert n == 1  # only one Discover (no adjacent card played first)
    assert len(p1.hand) == pre_hand + 1


def test_orbital_satellite_double_discover_with_adjacent_play():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    # Give the satellite and a neighbor, then play the neighbor first so the
    # satellite registers an adjacent play this turn.
    sat = p1.give("GDB_462")
    neighbor = p1.give("CS2_231")  # Wisp 1/1, sits adjacent in hand
    # Play the neighbor minion; this bumps sat.adjacent_plays_this_turn.
    neighbor.play()
    assert sat.adjacent_plays_this_turn >= 1
    pre_hand = len(p1.hand) - 1  # exclude the satellite itself
    sat.play()
    n = 0
    while p1.choice:
        n += 1
        for card in p1.choice.cards:
            assert Race.DRAENEI in card.races
        p1.choice.choose(p1.choice.cards[0])
    assert n == 2  # adjacent play -> two Discovers
    assert len(p1.hand) == pre_hand + 2
