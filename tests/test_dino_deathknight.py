"""The Lost City of Un'Goro mini-set (Dinosaurs, DINO_) — DEATHKNIGHT tests.

Cards under test:
  DINO_415 Story of Umbra — Discover a Deathrattle minion that costs (5) or
           more. Summon it and trigger its Deathrattle.
  DINO_416 Hollow Direhorn — Rush. After a friendly minion dies, spend 3
           Corpses to gain Reborn.
  DINO_417 Soulrest Ceremony — Give your minions +1 Attack and Rush. They die
           at the end of your turn.
Assertions follow the PRINTED card text.
"""

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone


CHILLWIND = "CS2_182"      # Chillwind Yeti 4/5 vanilla (no deathrattle)
WISP = "CS2_231"           # 1/1 vanilla (no deathrattle)


# ---------------------------------------------------------------------------
# DINO_415 — Story of Umbra
# ---------------------------------------------------------------------------

def test_story_of_umbra_discovers_only_costly_deathrattle_minions():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.discard_hand()
    spell = p1.give("DINO_415")
    spell.play()
    # A 3-card Discover opened; every option is a Deathrattle MINION that
    # costs (5) or more.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    for c in p1.choice.cards:
        assert c.type == CardType.MINION
        assert c.data.tags.get(GameTag.DEATHRATTLE)
        assert c.cost >= 5
    # Resolve the Discover so no in-flight choice leaks into the next test.
    p1.choice.choose(p1.choice.cards[0])
    assert p1.choice is None


def test_story_of_umbra_summons_choice_and_triggers_its_deathrattle():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    # Beef both heroes so no discovered deathrattle (which can hit a hero)
    # ends the game mid-test.
    for hero in (p1.hero, p2.hero):
        hero.max_health = 80
        hero.damage = 0
    # Seed the GAME rng (the Discover pool draws from game.random, NOT the
    # global random module). Seed 7 deterministically surfaces Cairne
    # Bloodhoof (CORE_EX1_110, a 6-Cost 5/5 with "Deathrattle: Summon Baine
    # Bloodhoof") as the first option.
    game.random.seed(7)
    spell = p1.give("DINO_415")
    spell.play()
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    assert chosen.id == "CORE_EX1_110"
    assert chosen.cost >= 5 and chosen.data.tags.get(GameTag.DEATHRATTLE)
    p1.choice.choose(chosen)
    # Cairne was summoned (5/5) AND its Deathrattle fired, summoning Baine
    # Bloodhoof (EX1_110t, 5/5). Both are on the board -> 2 minions total.
    ids = [m.id for m in p1.field]
    assert ids == ["CORE_EX1_110", "EX1_110t"]
    cairne = p1.field[0]
    baine = p1.field[1]
    assert (cairne.atk, cairne.max_health) == (5, 5)
    assert (baine.atk, baine.max_health) == (5, 5)


# ---------------------------------------------------------------------------
# DINO_416 — Hollow Direhorn
# ---------------------------------------------------------------------------

def test_hollow_direhorn_has_rush():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    horn = p1.summon("DINO_416")
    assert horn.rush  # Rush lives in data


# NOTE: a Death Knight passively gains 1 Corpse whenever a friendly minion
# dies (engine: Death.do), and that gain resolves BEFORE the Direhorn's
# Death listener. So a death with starting Corpses C leaves C+1 before the
# spend, and C+1-3 after.

def test_hollow_direhorn_spends_3_corpses_for_reborn_on_friendly_death():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    horn = p1.summon("DINO_416")
    assert not horn.reborn
    p1.corpses = 5
    # A friendly minion dies: +1 Corpse (5 -> 6), then 3 are spent -> 3.
    victim = p1.summon(WISP)
    victim.destroy()
    assert p1.corpses == 3
    assert horn.reborn


def test_hollow_direhorn_no_reborn_without_3_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    horn = p1.summon("DINO_416")
    p1.corpses = 1  # +1 on the death -> 2, still < 3
    victim = p1.summon(WISP)
    victim.destroy()
    # Only the passive +1 from the death; nothing spent, no Reborn granted.
    assert p1.corpses == 2
    assert not horn.reborn


def test_hollow_direhorn_does_not_spend_again_once_reborn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    horn = p1.summon("DINO_416")
    p1.corpses = 9
    # First friendly death: +1 (9 -> 10), pays 3 -> 7, gains Reborn.
    p1.summon(WISP).destroy()
    assert horn.reborn
    assert p1.corpses == 7
    # Second friendly death: +1 (7 -> 8), but already Reborn so no spend.
    p1.summon(WISP).destroy()
    assert p1.corpses == 8


# ---------------------------------------------------------------------------
# DINO_417 — Soulrest Ceremony
# ---------------------------------------------------------------------------

def test_soulrest_ceremony_buffs_attack_and_grants_rush():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    a = p1.summon(CHILLWIND)  # 4/5, no Rush natively
    b = p1.summon(WISP)       # 1/1
    assert not a.rush and not b.rush
    pre_a_atk, pre_b_atk = a.atk, b.atk
    spell = p1.give("DINO_417")
    spell.play()
    assert a.atk == pre_a_atk + 1
    assert b.atk == pre_b_atk + 1
    assert a.rush
    assert b.rush
    assert a.zone == Zone.PLAY
    assert b.zone == Zone.PLAY


def test_soulrest_ceremony_minions_die_at_end_of_turn():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    a = p1.summon(CHILLWIND)
    b = p1.summon(WISP)
    spell = p1.give("DINO_417")
    spell.play()
    assert a.zone == Zone.PLAY and b.zone == Zone.PLAY
    # End of the controller's turn: both buffed minions die.
    game.end_turn()
    assert a.zone == Zone.GRAVEYARD
    assert b.zone == Zone.GRAVEYARD


def test_soulrest_ceremony_only_affects_existing_minions():
    # Minions summoned AFTER the spell resolves are not given the dies-at-end
    # buff (the spell affects "your minions" at cast time only).
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    buffed = p1.summon(CHILLWIND)
    spell = p1.give("DINO_417")
    spell.play()
    later = p1.summon(WISP)  # summoned after the cast
    game.end_turn()
    assert buffed.zone == Zone.GRAVEYARD
    assert later.zone == Zone.PLAY
