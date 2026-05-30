"""The Great Dark Beyond — PRIEST collectible cards.

Tests assert the PRINTED card behaviour. One test (or cluster) per
collectible card:
  GDB_439 (Orbital Halo), GDB_440 (Mystified To'cha), GDB_441 (Anchorite),
  GDB_442 (K'ure, the Light Beyond), GDB_452 (Shield of Askara),
  GDB_454 (Overzealous Healer), GDB_455 (Askara), GDB_457 (Lightspeed),
  GDB_460 (Divine Star), GDB_464 (Gravity Lapse).
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone, Race

import fireplace.cards as _cards
from fireplace.actions import Hit, Heal


# ---------------------------------------------------------------------------
# GDB_439 — Orbital Halo: Give a minion +2/+1 and Divine Shield. Costs (0)
# if you played an adjacent card this turn.
# ---------------------------------------------------------------------------
def test_orbital_halo_buff_and_divine_shield():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    target = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    assert (target.atk, target.max_health) == (4, 5)
    assert not target.divine_shield
    halo = p1.give("GDB_439")
    halo.play(target=target)
    # +2/+1 and Divine Shield.
    assert (target.atk, target.max_health) == (6, 6)
    assert target.divine_shield


def test_orbital_halo_full_cost_without_adjacent_play():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    halo = p1.give("GDB_439")
    base = p1.card("GDB_439").cost
    assert base == 2
    # No adjacent card played this turn -> full cost.
    assert halo.adjacent_plays_this_turn == 0
    assert halo.cost == 2


def test_orbital_halo_costs_zero_after_adjacent_play():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    # Two cards adjacent in hand: a Wisp neighbour, then the Halo.
    neighbour = p1.give(WISP)        # hand index 0
    halo = p1.give("GDB_439")        # hand index 1 (adjacent to Wisp)
    assert halo.cost == 2
    # Playing the neighbour marks the Halo as having had an adjacent play.
    neighbour.play()
    assert halo.adjacent_plays_this_turn == 1
    # Costs (0) now.
    assert halo.cost == 0


# ---------------------------------------------------------------------------
# GDB_440 — Mystified To'cha: Battlecry: If the combined Health of both
# heroes is exactly 42, set your hero's Health to 42.
# ---------------------------------------------------------------------------
def test_mystified_tocha_sets_health_to_42_when_combined_is_42():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    # Combined health == 42 exactly: own hero 12 + enemy 30.
    # (Own hero's max raised to 42 so the "set to 42" can be observed —
    # the engine's SetCurrentHealth cannot exceed max_health.)
    p1.hero.max_health = 42
    p1.hero.damage = 30         # 12 health
    p2.hero.max_health = 30
    p2.hero.damage = 0          # 30 health  -> sum 42
    assert p1.hero.health + p2.hero.health == 42
    tocha = p1.give("GDB_440")
    tocha.play()
    # Own hero's Health set to 42.
    assert p1.hero.health == 42


def test_mystified_tocha_no_effect_when_combined_not_42():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 0          # 30
    p2.hero.max_health = 30
    p2.hero.damage = 0          # 30  -> sum 60, not 42
    tocha = p1.give("GDB_440")
    tocha.play()
    assert p1.hero.health == 30


# ---------------------------------------------------------------------------
# GDB_441 — Anchorite: Whenever another minion is Overhealed, give it that
# much extra Health.
# ---------------------------------------------------------------------------
def test_anchorite_grants_extra_health_on_overheal():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.summon("GDB_441")  # Anchorite on board
    other = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    other.damage = 2  # 3 current health
    # Heal for 5: actual heal = 2, overheal = 3 -> +3 max_health.
    game.queue_actions(p1.hero, [Heal(other, 5)])
    assert other.max_health == 5 + 3
    # Fully healed and the extra Health is real current health too.
    assert other.damage == 0
    assert other.health == 8


def test_anchorite_no_buff_without_overheal():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.summon("GDB_441")
    other = p1.summon("CS2_182")  # 4/5
    other.damage = 4  # 1 current health
    # Heal for exactly 4: no overheal -> no extra Health.
    game.queue_actions(p1.hero, [Heal(other, 4)])
    assert other.max_health == 5
    assert other.damage == 0


def test_anchorite_does_not_buff_itself():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    anchorite = p1.summon("GDB_441")  # 2/4
    anchorite.damage = 1  # 3 current health
    # Overheal the Anchorite itself: heal 5, overheal 2. "another minion"
    # excludes SELF, so no extra Health on itself.
    game.queue_actions(p1.hero, [Heal(anchorite, 5)])
    assert anchorite.max_health == 4
    assert anchorite.damage == 0


# ---------------------------------------------------------------------------
# GDB_442 — K'ure, the Light Beyond: Spellburst: Summon a random 3-Cost
# minion.
# ---------------------------------------------------------------------------
def test_kure_spellburst_summons_three_cost_minion():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    kure = p1.summon("GDB_442")
    assert kure.has_spellburst
    pre = len(p1.field)
    # Cast any spell to fire Spellburst.
    spell = p1.give(MOONFIRE)
    spell.play(target=p1.hero)
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Exactly one new minion summoned, and it is a 3-Cost minion.
    assert len(p1.field) == pre + 1
    summoned = [m for m in p1.field if m is not kure][0]
    assert summoned.data.cost == 3
    # Spellburst is one-shot.
    assert not kure.has_spellburst


# ---------------------------------------------------------------------------
# GDB_452 — Shield of Askara: Taunt, Divine Shield, Lifesteal (vanilla).
# ---------------------------------------------------------------------------
def test_shield_of_askara_keywords():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    m = game.player1.summon("GDB_452")
    assert (m.atk, m.max_health) == (4, 8)
    assert m.taunt
    assert m.divine_shield
    assert m.lifesteal


# ---------------------------------------------------------------------------
# GDB_454 — Overzealous Healer: Deathrattle: Restore 6 Health to the enemy
# hero. Spellburst: Silence this minion.
# ---------------------------------------------------------------------------
def test_overzealous_healer_deathrattle_heals_enemy_hero():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 30
    p2.hero.damage = 10  # 20 health
    healer = p1.summon("GDB_454")
    healer.destroy()
    game.process_deaths()
    # +6 to the enemy hero -> damage 10 - 6 = 4.
    assert p2.hero.damage == 4


def test_overzealous_healer_spellburst_silences_self():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 30
    p2.hero.damage = 10
    healer = p1.summon("GDB_454")
    assert healer.has_spellburst
    # Cast a spell -> Spellburst silences the Healer (removing its Deathrattle).
    spell = p1.give(MOONFIRE)
    spell.play(target=p1.hero)
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert healer.silenced
    assert not healer.has_deathrattle
    # Now dying no longer heals the enemy hero.
    healer.destroy()
    game.process_deaths()
    assert p2.hero.damage == 10


# ---------------------------------------------------------------------------
# GDB_455 — Askara: Battlecry: The next Draenei you play summons a copy of
# itself.
# ---------------------------------------------------------------------------
def test_askara_next_draenei_summons_copy():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    askara = p1.give("GDB_455")
    askara.play()
    assert len(p1.next_draenei_hooks) == 1
    # Play a Draenei: Velen, Leader of the Exiled (GDB_131). Refresh mana
    # (Askara already spent 4) so the 7-cost Velen is playable.
    p1.used_mana = 0
    velen = p1.give("GDB_131")
    assert Race.DRAENEI in velen.data.races
    velen.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # The Draenei itself + a summoned copy of it.
    copies = [m for m in p1.field if m.id == "GDB_131"]
    assert len(copies) == 2
    # Hook consumed.
    assert p1.next_draenei_hooks == []


def test_askara_hook_not_consumed_by_non_draenei():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    askara = p1.give("GDB_455")
    askara.play()
    assert len(p1.next_draenei_hooks) == 1
    # Play a non-Draenei minion: no copy, hook still pending.
    wisp = p1.give(WISP)
    wisp.play()
    assert len([m for m in p1.field if m.id == WISP]) == 1
    assert len(p1.next_draenei_hooks) == 1


# ---------------------------------------------------------------------------
# GDB_457 — Lightspeed: Give a minion +1/+2 and Rush. Repeatable this turn.
# ---------------------------------------------------------------------------
def test_lightspeed_buff_rush_and_echo_copy():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    target = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    assert not target.rush
    light = p1.give("GDB_457")
    light.play(target=target)
    # +1/+2 and Rush.
    assert (target.atk, target.max_health) == (5, 7)
    assert target.rush
    # Repeatable this turn -> an echo copy of Lightspeed is now in hand.
    copies = [c for c in p1.hand if c.id == "GDB_457"]
    assert len(copies) == 1


# ---------------------------------------------------------------------------
# GDB_460 — Divine Star: Deal $3 damage to a minion. Give a random minion in
# your hand +3 Health.
# ---------------------------------------------------------------------------
def test_divine_star_damage_and_hand_buff():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    target = p2.summon("CS2_182")  # 4/5 enemy minion
    target.max_health = 50
    target.damage = 0
    # Exactly one minion in hand so the +3 Health is deterministic.
    hand_minion = p1.give("CS2_182")  # Chillwind Yeti 4/5
    assert hand_minion.max_health == 5
    star = p1.give("GDB_460")
    star.play(target=target)
    # $3 to the targeted minion.
    assert target.damage == 3
    # The lone hand minion gets +3 Health.
    assert hand_minion.max_health == 8


# ---------------------------------------------------------------------------
# GDB_464 — Gravity Lapse: Set EVERY minion's Attack and Health to the lower
# of the two.
# ---------------------------------------------------------------------------
def test_gravity_lapse_sets_all_to_lower_stat():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    a = p1.summon("CS2_182")   # 4/5 -> lower is 4 -> 4/4
    b = p2.summon("CS2_172")   # Bloodfen Raptor 3/2 -> lower is 2 -> 2/2
    c = p1.summon("EX1_020")   # Scarlet Crusader 3/1 -> lower is 1 -> 1/1
    lapse = p1.give("GDB_464")
    lapse.play()
    assert (a.atk, a.max_health) == (4, 4)
    assert (b.atk, b.max_health) == (2, 2)
    assert (c.atk, c.max_health) == (1, 1)
    # Damage cleared by the effect.
    assert a.damage == 0 and b.damage == 0 and c.damage == 0
