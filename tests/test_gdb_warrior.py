"""The Great Dark Beyond — WARRIOR collectible card tests.

Asserts the PRINTED behaviour of each Warrior card (and tokens):
Hostile Invader, Jettison, Captain's Log, Expedition Sergeant,
Stalwart Avenger, Crystalline Greatmace, Unyielding Vindicator,
Dwarf Planet, Spore Empress Moldara, Exarch Akama.
"""

import pytest

from utils import *
from utils import _empty_mulligan
from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards

from fireplace.actions import Hit, Buff


# A vanilla Draenei minion (Taunt/Lifesteal, no battlecry) — clean test subject
# for the "next Draenei you play …" payoffs.
DRAENEI_VANILLA = "BT_423"  # Ashtongue Battlelord, 4/3/5


# GDB_226 — Hostile Invader: Battlecry, Spellburst, and Deathrattle:
# Deal 2 damage to all other minions.
def test_hostile_invader_battlecry_hits_all_other_minions():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    friend = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    friend.max_health = 80
    friend.damage = 0
    enemy = p2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    invader = p1.give("GDB_226")
    invader.play()
    # 2 damage to every OTHER minion, never to itself.
    assert friend.damage == 2
    assert enemy.damage == 2
    assert invader.damage == 0


def test_hostile_invader_spellburst_hits_all_other_minions():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    invader = p1.summon("GDB_226")  # summon => battlecry skipped
    other = p1.summon("CS2_182")
    other.max_health = 80
    other.damage = 0
    assert invader.has_spellburst
    # Playing any spell triggers the Spellburst.
    moonfire = p1.give(MOONFIRE)
    moonfire.play(target=p2.hero)
    assert other.damage == 2
    assert invader.damage == 0
    assert not invader.has_spellburst


def test_hostile_invader_deathrattle_hits_all_other_minions():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    invader = p1.summon("GDB_226")
    other = p2.summon("CS2_182")
    other.max_health = 80
    other.damage = 0
    invader.destroy()
    game.process_deaths()
    assert other.damage == 2


# GDB_227 — Jettison: Discover a spell. Spend 2 Armor to Discover another.
def test_jettison_with_armor_discovers_two_spells():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 5
    spell = p1.give("GDB_227")
    spell.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Two Discovers => two spells gained; 2 armor spent on the second.
    gained = [c for c in p1.hand if c.type == CardType.SPELL and c.id != "GDB_227"]
    assert len(gained) == 2
    assert p1.hero.armor == 5 - 2


def test_jettison_without_armor_discovers_one_spell():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 1  # < 2, so the second Discover never triggers
    spell = p1.give("GDB_227")
    spell.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    gained = [c for c in p1.hand if c.type == CardType.SPELL and c.id != "GDB_227"]
    assert len(gained) == 1
    assert p1.hero.armor == 1  # no armor spent


# GDB_228 — Captain's Log: Draw 2 cards. Costs (1) less for each Draenei you control.
def test_captains_log_draws_two():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    for cid in (WISP, WISP):
        c = p1.card(cid)
        c.zone = Zone.DECK
    spell = p1.give("GDB_228")
    pre = len([c for c in p1.hand if c.id == WISP])
    spell.play()
    drawn = [c for c in p1.hand if c.id == WISP]
    assert len(drawn) == pre + 2


def test_captains_log_cost_reduced_per_draenei():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    base = p1.card("GDB_228").cost  # 4
    spell = p1.give("GDB_228")
    assert spell.cost == base
    p1.summon(DRAENEI_VANILLA)  # 1 Draenei in play -> -1
    assert spell.cost == base - 1
    p1.summon(DRAENEI_VANILLA)  # 2 Draenei -> -2
    assert spell.cost == base - 2
    # A non-Draenei minion does not reduce it.
    p1.summon(WISP)
    assert spell.cost == base - 2


# GDB_229 — Expedition Sergeant: Battlecry: The next Draenei you play
# immediately attacks a random enemy.
def test_expedition_sergeant_next_draenei_attacks_random_enemy():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # Exactly one legal enemy: the enemy hero (no enemy minions), so the
    # random pick is forced.
    sergeant = p1.give("GDB_229")
    sergeant.play()
    assert len(p1.next_draenei_hooks) == 1
    pre_hero = p2.hero.health
    draenei = p1.give(DRAENEI_VANILLA)  # 4/3/5
    draenei.play()
    # The Draenei immediately attacked the only enemy (the hero) for its Attack.
    assert p2.hero.health == pre_hero - draenei.atk
    assert p1.next_draenei_hooks == []


# GDB_230 — Stalwart Avenger: At the end of EACH turn, swap Attack and Health.
def test_stalwart_avenger_swaps_stats_each_turn_end():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    avenger = p1.summon("GDB_230")  # printed 7/2
    assert (avenger.atk, avenger.health) == (7, 2)
    game.end_turn()  # p1's turn end -> swap to 2/7
    assert (avenger.atk, avenger.max_health) == (2, 7)
    assert avenger.damage == 0
    game.end_turn()  # p2's turn end (EACH turn) -> swap back to 7/2
    assert (avenger.atk, avenger.max_health) == (7, 2)


# GDB_231 — Crystalline Greatmace (Weapon): After your hero attacks, give all
# Draenei in your hand +2 Attack.
def test_crystalline_greatmace_buffs_draenei_in_hand_after_hero_attack():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # A Draenei and a non-Draenei waiting in hand.
    draenei = p1.give(DRAENEI_VANILLA)  # 4/3/5
    base_atk = draenei.atk
    wisp = p1.give(WISP)
    weapon = p1.give("GDB_231")
    weapon.play()
    # Hero attacks the enemy hero (weapon equipped -> hero has attack).
    p1.hero.attack(p2.hero)
    # Draenei in hand gains +2 Attack; non-Draenei untouched.
    assert draenei.atk == base_atk + 2
    assert wisp.atk == p1.card(WISP).atk


# GDB_232 — Unyielding Vindicator: Battlecry: The next Draenei you play gives
# your hero its Attack for that turn.
def test_unyielding_vindicator_next_draenei_gives_hero_attack():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    vindicator = p1.give("GDB_232")
    vindicator.play()
    assert len(p1.next_draenei_hooks) == 1
    assert p1.hero.atk == 0
    draenei = p1.give(DRAENEI_VANILLA)  # 4/3/5, Attack 4
    draenei.play()
    # Hero gains the Draenei's Attack (4) for the turn.
    assert p1.hero.atk == draenei.atk
    assert p1.next_draenei_hooks == []


# GDB_233 — Dwarf Planet: Fill your board with random 2-Cost minions that
# attack random enemies.
def test_dwarf_planet_fills_board_with_2cost_minions():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # The only enemy is the hero (no enemy minions). Beef its HP huge so every
    # summoned minion can attack the hero (no retaliation, no lethal) and the
    # board stays full at 7.
    p2.hero.max_health = 20000
    p2.hero.damage = 0
    spell = p1.give("GDB_233")
    spell.play()
    game.process_deaths()
    # Board is filled to the cap (7 slots from empty).
    assert len(p1.field) == 7
    # Every summoned minion is a collectible 2-Cost minion.
    for m in p1.field:
        assert m.data.cost == 2
        assert m.type == CardType.MINION
    # The enemy hero took the brunt of all the summoned attacks.
    assert p2.hero.damage > 0


# GDB_234 — Spore Empress Moldara: Start of Game: Shuffle 7 Replicating Spores
# into your deck.
def test_spore_empress_moldara_shuffles_seven_spores():
    # Start-of-Game fires for cards that begin in the DECK. Build a deck with
    # one Moldara plus filler; a fixed seed keeps Moldara out of the opening
    # hand so the Deck event fires exactly once.
    deck = ["GDB_234"] + [WISP] * 20
    player1 = Player("Player1", deck, CardClass.WARRIOR.default_hero)
    player1.cant_fatigue = True
    player2 = Player("Player2", [], CardClass.WARRIOR.default_hero)
    player2.cant_fatigue = True
    game = BaseTestGame(players=(player1, player2), seed=0)
    game.start()
    _empty_mulligan(game)
    # Precondition: the single Moldara stayed in the deck (not the opening hand),
    # so its Start of Game must have fired.
    assert any(c.id == "GDB_234" for c in player1.deck)
    assert not any(c.id == "GDB_234" for c in player1.hand)
    spores = [c for c in player1.deck if c.id == "GDB_234t"]
    # Exactly 7 Replicating Spores shuffled into the owner's deck at game start.
    assert len(spores) == 7


# GDB_235 — Exarch Akama: After this attacks, all other friendly minions can
# attack again (except Exarch Akama).
def test_exarch_akama_refreshes_other_friendly_minions():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    akama = p1.summon("GDB_235")  # 3/6
    ally = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    # Clear summoning sickness so both can act this turn.
    akama.turns_in_play = 1
    ally.turns_in_play = 1
    # Spend the ally's attack first so it is exhausted.
    ally.num_attacks = 1
    assert ally.exhausted
    # Akama attacks the enemy hero; its trigger refreshes the ally.
    akama.attack(p2.hero)
    assert ally.num_attacks == 0
    assert not ally.exhausted
    assert ally.can_attack(p2.hero)
    # Akama itself is NOT refreshed (it just attacked).
    assert akama.num_attacks == 1
    assert akama.exhausted
