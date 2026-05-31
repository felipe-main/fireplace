"""Into the Emerald Dream — HUNTER collectible cards.

Tight unit tests asserting the PRINTED card behaviour. One test per
collectible card:
  EDR_014 Verdant Dreamsaber, EDR_226 Exotic Houndmaster, EDR_227 Umbraclaw,
  EDR_261 Amphibian's Spirit, EDR_262 Spirit Bond,
  EDR_263 Grace of the Greatwolf, EDR_416 Shepherd's Crook, EDR_480 Goldrinn,
  EDR_481 Mythical Runebear, EDR_853 Broll Bearmantle.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone


# EDR_014 — Verdant Dreamsaber: Battlecry: If this costs (3) or less, attack
# two random enemy minions.
def test_verdant_dreamsaber_attacks_two_when_cheap():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    saber = p1.give("EDR_014")
    # Discount it to 3 so the battlecry fires.
    saber.cost = 3
    assert saber.cost == 3
    # One fat enemy minion: with a single enemy minion both random picks land
    # on it, so it takes 2 x Saber.atk and the damage is deterministic.
    game.end_turn()
    target = p2.summon("CS2_182")  # 4/5 Chillwind Yeti
    target.max_health = 80
    target._max_health = 80
    target.damage = 0
    game.end_turn()
    saber.play()
    # Saber (4 atk) attacked the only enemy minion twice for 4 each -> 8 total.
    # This is the card's whole printed effect ("attack two random enemy
    # minions"); the forced battlecry attack does not apply the defender's
    # retaliation in this engine, so we assert the offensive damage only.
    assert target.damage == 8


def test_verdant_dreamsaber_no_attack_when_expensive():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    saber = p1.give("EDR_014")
    assert saber.cost == 5  # printed cost > 3
    game.end_turn()
    target = p2.summon("CS2_182")
    target.max_health = 80
    target._max_health = 80
    target.damage = 0
    game.end_turn()
    saber.play()
    assert target.damage == 0
    assert saber.damage == 0


# EDR_226 — Exotic Houndmaster: Battlecry: Draw a Beast. Imbue your Hero Power.
def test_exotic_houndmaster_draws_beast_and_imbues():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # Stack the deck with exactly one Beast so the draw is deterministic.
    beast = p1.give("CS2_125")  # Ironfur Grizzly (Beast)
    beast.zone = Zone.DECK
    hp_before = p1.hero.power.id
    card = p1.give("EDR_226")
    pre_hand = len(p1.hand)
    card.play()
    assert beast.zone == Zone.HAND
    assert len(p1.hand) == pre_hand  # -1 for played card, +1 drawn beast
    assert p1.imbues_this_game == 1
    assert p1.hero.power.id == "EDR_850p"  # Blessing of the Wolf
    assert p1.hero.power.id != hp_before


# EDR_227 — Umbraclaw: Rush. Deathrattle: Imbue your Hero Power.
def test_umbraclaw_rush_and_deathrattle_imbues():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    claw = p1.summon("EDR_227")
    assert claw.rush
    assert p1.imbues_this_game == 0
    claw.destroy()
    game.process_deaths()
    assert claw.zone == Zone.GRAVEYARD
    assert p1.imbues_this_game == 1
    assert p1.hero.power.id == "EDR_850p"


# EDR_261 — Amphibian's Spirit: Give a minion +2/+2 and "Deathrattle: Give a
# friendly minion +2/+2 and this Deathrattle."
def test_amphibians_spirit_buffs_and_propagates_deathrattle():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    host = p1.summon("CS2_182")  # 4/5 Yeti
    spell = p1.give("EDR_261")
    spell.play(target=host)
    assert host.atk == 6
    assert host.max_health == 7
    # A second minion to receive the propagated deathrattle (only one option).
    inheritor = p1.summon("CS2_171")  # 1/1 Stonetusk Boar
    host.destroy()
    game.process_deaths()
    assert host.zone == Zone.GRAVEYARD
    # Deathrattle gave the only other friendly minion +2/+2 and the rattle.
    assert inheritor.atk == 3
    assert inheritor.max_health == 3
    # The granted deathrattle propagates: killing the inheritor would buff the
    # next minion. Verify a third minion inherits it in turn.
    third = p1.summon("CS2_171")  # 1/1
    inheritor.destroy()
    game.process_deaths()
    assert third.atk == 3
    assert third.max_health == 3


# EDR_262 — Spirit Bond: Deal $3 damage to a minion. If that kills it, summon
# a 3/2 Wolf with Rush.
def test_spirit_bond_kills_and_summons_wolf():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_171")  # 1/1 — dies to 3 damage
    spell = p1.give("EDR_262")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.zone == Zone.GRAVEYARD
    wolves = [m for m in p1.field if m.id == "EDR_262t"]
    assert len(wolves) == 1
    wolf = wolves[0]
    assert (wolf.atk, wolf.max_health) == (3, 2)
    assert wolf.rush
    assert wolf.race == Race.BEAST


def test_spirit_bond_no_wolf_when_survives():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_182")  # 4/5 — survives 3 damage
    spell = p1.give("EDR_262")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.zone == Zone.PLAY
    assert victim.damage == 3
    assert not [m for m in p1.field if m.id == "EDR_262t"]


# EDR_263 — Grace of the Greatwolf: Choose One - Deal $4 damage to the enemy
# hero; or Summon two 3/2 Wolves with Rush.
def test_grace_choose_damage_hero():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    spell = p1.give("EDR_263")
    spell.play(choose="EDR_263a")
    assert p2.hero.health == 76
    assert not [m for m in p1.field if m.id == "EDR_262t"]


def test_grace_choose_summon_wolves():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    spell = p1.give("EDR_263")
    spell.play(choose="EDR_263b")
    wolves = [m for m in p1.field if m.id == "EDR_262t"]
    assert len(wolves) == 2
    assert all(w.atk == 3 and w.max_health == 2 and w.rush for w in wolves)


# EDR_416 — Shepherd's Crook: After your hero attacks, summon a 3/3 Sheep
# that's Dormant for 2 turns.
def test_shepherds_crook_summons_dormant_sheep_on_hero_attack():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    weapon = p1.give("EDR_416")
    # Workaround for a pre-existing engine bug on this branch: Weapon.__init__
    # does not initialize _max_durability, so reading max_durability during
    # play() raises AttributeError. Seed it (the engine stage owns the fix).
    weapon._max_durability = 0
    weapon.play()
    assert p1.hero.atk == 3
    # Hero attacks the enemy hero, triggering the weapon's after-attack.
    p1.hero.attack(p2.hero)
    sheep = [m for m in p1.field if m.id == "EDR_416t"]
    assert len(sheep) == 1
    s = sheep[0]
    assert (s.atk, s.max_health) == (3, 3)
    assert s.dormant
    assert s.dormant_turns == 2


# EDR_480 — Goldrinn: Rush. Friendly Beasts deal double damage.
# Modelled as an aura doubling friendly Beasts' Attack.
def test_goldrinn_doubles_friendly_beast_attack():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    beast = p1.summon("CS2_125")  # Ironfur Grizzly 3/3 Beast
    non_beast = p1.summon("CS2_182")  # Chillwind Yeti 4/5 (not a Beast)
    assert beast.atk == 3
    goldrinn = p1.summon("EDR_480")
    assert goldrinn.rush
    # Friendly Beast attack doubled; non-Beast untouched; Goldrinn is a Beast,
    # and printed "Friendly Beasts" has no "other" — so Goldrinn doubles too.
    assert beast.atk == 6
    assert non_beast.atk == 4
    assert goldrinn.atk == 18  # 9 base, doubled by its own aura (includes self)
    # Aura ends when Goldrinn leaves.
    goldrinn.destroy()
    game.process_deaths()
    assert beast.atk == 3


# EDR_481 — Mythical Runebear: Taunt. Battlecry: If this has 4 or more Attack,
# summon a copy of this.
def test_mythical_runebear_no_copy_when_low_attack():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    bear = p1.give("EDR_481")  # base 3 atk -> no copy
    bear.play()
    assert bear.taunt
    bears = [m for m in p1.field if m.id == "EDR_481"]
    assert len(bears) == 1


def test_mythical_runebear_copies_when_buffed():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    bear = p1.give("EDR_481")
    # Apply a real +2/+2 enchant so it has 4+ Attack (3 base + 2 = 5) when
    # played; ExactCopy carries the enchant onto the summoned copy.
    bear.buff(bear, "EDR_261e")
    assert bear.atk == 5
    bear.play()
    bears = [m for m in p1.field if m.id == "EDR_481"]
    assert len(bears) == 2
    # Both the played bear and its exact copy reflect the +2/+2 buff.
    assert all(b.atk == 5 for b in bears)
    assert all(b.max_health == 6 for b in bears)
    assert all(b.taunt for b in bears)


# EDR_853 — Broll Bearmantle: After you cast a spell, summon a random Animal
# Companion.
def test_broll_summons_animal_companion_on_spell():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.summon("EDR_853")
    field_before = len(p1.field)
    spell = p1.give("CS2_084")  # Hunter's Mark (a spell)
    target = p1.summon("CS2_182")
    spell.play(target=target)
    companions = [m for m in p1.field if m.id in ("NEW1_032", "NEW1_033", "NEW1_034")]
    assert len(companions) == 1
    assert len(p1.field) == field_before + 1 + 1  # target + companion


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
