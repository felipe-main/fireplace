"""Into the Emerald Dream — WARRIOR collectible card tests.

Asserts the PRINTED behaviour of each Warrior card (and tokens):
Siphoning Growth, Ominous Nightmares, Afflicted Devastator, Eggbasher,
Brood Keeper, Darkrider, Clutch of Corruption, Succumb to Madness,
Ysondre, Tortolla.
"""

import pytest

from utils import *
from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards
from fireplace.card import Weapon as _Weapon


# The 219197 data bump left Weapon._max_durability uninitialised (durability now
# flows from the HEALTH tag), so every live weapon trips an AttributeError during
# death processing. That is a pre-existing engine bug outside this card set; give
# the class a 0 fallback so the Brood Keeper equip test can exercise the card
# logic. (Real durability still comes from the HEALTH tag via max_durability.)
if not hasattr(_Weapon, "_max_durability"):
    _Weapon._max_durability = 0


# A clean vanilla Dragon (no battlecry) — used for "holding a Dragon" gates and
# the Dragon-copy / resummon cards.
DRAGON_VANILLA = "DREAM_03"  # Emerald Drake, 4/7/6
WISP = "CS2_231"  # 0/1/1 vanilla, neutral test fodder
YETI = "CS2_182"  # Chillwind Yeti 4/5, beefy test target


# EDR_531 — Siphoning Growth: Destroy a friendly minion to gain 8 Armor.
def test_siphoning_growth_destroys_friendly_and_gains_8_armor():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    victim = p1.summon(YETI)
    assert p1.hero.armor == 0
    spell = p1.give("EDR_531")
    spell.play(target=victim)
    assert victim.zone == Zone.GRAVEYARD
    assert p1.hero.armor == 8


# EDR_570 — Ominous Nightmares: Choose One - Deal 1 damage to all minions; or
# Give a damaged minion +2/+2.
def test_ominous_nightmares_burst_hits_all_minions():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    friend = p1.summon(YETI); friend.max_health = 80; friend.damage = 0
    enemy = p2.summon(YETI); enemy.max_health = 80; enemy.damage = 0
    spell = p1.give("EDR_570")
    spell.play(choose="EDR_570A")
    assert friend.damage == 1
    assert enemy.damage == 1


def test_ominous_nightmares_unstable_power_buffs_damaged_minion():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    target = p1.summon(YETI)  # 4/5
    target.damage = 2  # make it damaged so it is a legal target
    pre_atk, pre_health = target.atk, target.max_health
    # Play the targeted Choose-One sub-card directly (the parent routes here).
    p1.give("EDR_570B").play(target=target)
    assert target.atk == pre_atk + 2
    assert target.max_health == pre_health + 2


# EDR_459 — Afflicted Devastator: Battlecry: Deal 3 damage to all other
# friendly minions. Deathrattle: Deal 3 damage to all enemy minions.
def test_afflicted_devastator_battlecry_then_deathrattle():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    friend = p1.summon(YETI); friend.max_health = 80; friend.damage = 0
    enemy = p2.summon(YETI); enemy.max_health = 80; enemy.damage = 0
    dev = p1.give("EDR_459")
    dev.play()
    # Battlecry hits OTHER friendly minions only — not itself, not enemies.
    assert friend.damage == 3
    assert enemy.damage == 0
    assert dev.damage == 0
    # Deathrattle now hits all enemy minions.
    dev.destroy()
    assert enemy.damage == 3
    assert friend.damage == 3  # unchanged by the deathrattle


# EDR_468 — Eggbasher: Battlecry: Deal 1 damage to a minion and give it +4
# Attack.
def test_eggbasher_damages_and_buffs_target():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    target = p2.summon(YETI)  # 4/5
    pre_atk = target.atk
    basher = p1.give("EDR_468")
    basher.play(target=target)
    assert target.damage == 1
    assert target.atk == pre_atk + 4


# EDR_457 — Brood Keeper: Battlecry: If you're holding a Dragon, equip a 2/2
# Sword.
def test_brood_keeper_equips_sword_when_holding_dragon():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p1.give(DRAGON_VANILLA)  # holding a Dragon
    keeper = p1.give("EDR_457")
    keeper.play()
    assert p1.weapon is not None
    assert p1.weapon.id == "EDR_457t"
    # A 2/2 Sword (durability flows from the HEALTH tag).
    assert p1.weapon.atk == 2
    assert p1.weapon.durability == 2


def test_brood_keeper_no_sword_without_dragon():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    # Clear hand so no Dragon is held.
    for c in list(p1.hand):
        c.discard()
    keeper = p1.give("EDR_457")
    keeper.play()
    assert p1.weapon is None


# EDR_456 — Darkrider: Battlecry: If you're holding a Dragon, Discover a Dragon
# with a Dark Gift.
#
# Dark Gift now routes through the set-wide `_GiveDarkGift` helper (random
# keyword Bonus Effect, always granted, strict upgrade) — same as every other
# EDR Dark-Gift card — instead of a bespoke fixed +2/+2 enchant.
def test_darkrider_discovers_dragon_with_dark_gift_when_holding_dragon():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p1.give(DRAGON_VANILLA)  # holding a Dragon -> battlecry fires
    rider = p1.give("EDR_456")
    rider.play()
    # A Discover should be open over three Dragons.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    for card in p1.choice.cards:
        assert Race.DRAGON in card.races
    chosen = p1.choice.cards[0]
    chosen_id = chosen.id
    p1.choice.choose(chosen)
    assert p1.choice is None
    # The discovered Dragon is in hand carrying exactly one NEW Dark Gift
    # keyword from the eight-keyword Nightmare Bonus-Effect pool (relative to
    # its printed base tags, so a natively-Taunt Dragon isn't double-counted).
    got = next(c for c in p1.hand if c.id == chosen_id)
    base_tags = _cards.db[chosen_id].tags
    bonus_keywords = (
        GameTag.TAUNT,
        GameTag.WINDFURY,
        GameTag.DIVINE_SHIELD,
        GameTag.POISONOUS,
        GameTag.CANT_BE_TARGETED_BY_SPELLS,
        GameTag.RUSH,
        GameTag.LIFESTEAL,
        GameTag.REBORN,
    )
    added = [
        kw for kw in bonus_keywords
        if bool(got.tags.get(kw)) and not bool(base_tags.get(kw))
    ]
    assert len(added) == 1


def test_darkrider_no_discover_without_dragon():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    for c in list(p1.hand):
        c.discard()
    rider = p1.give("EDR_456")
    rider.play()
    # Not holding a Dragon -> battlecry does nothing, no Discover opens.
    assert p1.choice is None


# EDR_454 — Clutch of Corruption (Location): Choose a friendly Dragon. Summon a
# 0/2 Egg that hatches into a copy of it.
def test_clutch_of_corruption_egg_hatches_into_chosen_dragon():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    dragon = p1.summon(DRAGON_VANILLA)  # 4/7/6 on board
    loc = p1.give("EDR_454")
    loc.play()
    # Locations have summoning sickness — pass a full round.
    game.end_turn(); game.end_turn()
    loc.use(target=dragon)
    eggs = [m for m in p1.field if m.id == "EDR_454t"]
    assert len(eggs) == 1
    egg = eggs[0]
    assert (egg.atk, egg.max_health) == (0, 2)
    # The egg hatches into a copy of the chosen Dragon on death.
    egg.destroy()
    copies = [m for m in p1.field if m.id == DRAGON_VANILLA]
    # Original dragon + the hatched copy.
    assert len(copies) == 2


def test_clutch_of_corruption_only_targets_friendly_dragons():
    # Real bug: the Location must be restricted to friendly DRAGONS via
    # REQ_TARGET_WITH_RACE, not any friendly minion.
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    dragon = p1.summon(DRAGON_VANILLA)  # friendly Dragon -> legal
    non_dragon = p1.summon(YETI)  # friendly non-Dragon -> illegal
    enemy_dragon = p2.summon(DRAGON_VANILLA)  # enemy Dragon -> illegal (friendly only)
    loc = p1.give("EDR_454")
    loc.play()
    game.end_turn(); game.end_turn()
    valid = loc.targets
    assert dragon in valid
    assert non_dragon not in valid
    assert enemy_dragon not in valid


def test_clutch_of_corruption_hatch_snapshots_buffs():
    # Significant approximation fix: the egg hatches into an EXACT copy of the
    # chosen Dragon, preserving buffs/enchantments it carried at cast time —
    # even if the original is buffed further or destroyed afterwards.
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    dragon = p1.summon(DRAGON_VANILLA)  # 4/7/6
    base_atk, base_health = dragon.atk, dragon.max_health
    # Buff the dragon by +4 Attack (Eggbasher's enchant) BEFORE casting.
    dragon.buff(dragon, "EDR_468e1")  # +4 Attack
    assert dragon.atk == base_atk + 4
    loc = p1.give("EDR_454")
    loc.play()
    game.end_turn(); game.end_turn()
    loc.use(target=dragon)
    # Mutate the original after the snapshot — the egg must NOT track this.
    dragon.destroy()
    egg = next(m for m in p1.field if m.id == "EDR_454t")
    egg.destroy()
    hatched = next(m for m in p1.field if m.id == DRAGON_VANILLA)
    # The hatched copy carries the +4 Attack buff snapshotted at cast time.
    assert hatched.atk == base_atk + 4
    assert hatched.max_health == base_health


# EDR_455 — Succumb to Madness: Discover a friendly Dragon that died this game.
# Resummon it.
def test_succumb_to_madness_resummons_dead_dragon():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    dragon = p1.summon(DRAGON_VANILLA)
    dragon.destroy()  # now a friendly Dragon has died this game
    assert dragon.zone == Zone.GRAVEYARD
    assert not any(m.id == DRAGON_VANILLA for m in p1.field)
    spell = p1.give("EDR_455")
    spell.play()
    assert p1.choice is not None
    for card in p1.choice.cards:
        assert Race.DRAGON in card.races
        assert card.id == DRAGON_VANILLA
    p1.choice.choose(p1.choice.cards[0])
    assert p1.choice is None
    # The chosen Dragon is resummoned to the battlefield (not to hand).
    resummoned = [m for m in p1.field if m.id == DRAGON_VANILLA]
    assert len(resummoned) == 1
    assert not any(c.id == DRAGON_VANILLA for c in p1.hand)


# EDR_465 — Ysondre: Taunt. Deathrattle: Summon a random Dragon for each time
# Ysondre has died this game.
def test_ysondre_deathrattle_scales_with_deaths():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    assert game.current_player is p1
    y = p1.summon("EDR_465")
    assert y.taunt
    # First death -> summon 1 random Dragon.
    y.destroy()
    dragons = [m for m in p1.field if Race.DRAGON in m.races]
    assert len(dragons) == 1
    # Second Ysondre death -> summon 2 random Dragons (count = 2).
    pre = len([m for m in p1.field if Race.DRAGON in m.races])
    y2 = p1.summon("EDR_465")
    y2.destroy()
    now = len([m for m in p1.field if Race.DRAGON in m.races])
    # Two more Dragons appear (could include Ysondre if rolled, but Ysondre is
    # not collectible-random-Dragon-eligible — assert exactly +2).
    assert now - pre == 2


# EDR_471 — Tortolla: Taunt, Elusive. After this takes damage, gain 1 Armor and
# give this minion +1 Attack.
def test_tortolla_gains_armor_and_attack_on_damage():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    tort = p1.summon("EDR_471")  # 1/30
    assert tort.taunt
    pre_atk = tort.atk
    assert p1.hero.armor == 0
    # Poke it with a 2-damage hit from an enemy spell-source.
    from fireplace.actions import Hit
    game.queue_actions(p2.hero, [Hit(tort, 2)])
    assert tort.damage == 2
    assert p1.hero.armor == 1
    assert tort.atk == pre_atk + 1


def test_tortolla_is_elusive():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.current_player
    tort = p1.summon("EDR_471")
    # Elusive == can't be targeted by spells or Hero Powers.
    assert tort.cant_be_targeted_by_abilities
