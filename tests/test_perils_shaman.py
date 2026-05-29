"""Perils in Paradise — SHAMAN collectible card tests.

Covers all 10 collectible Shaman cards (VAC_ prefix):
  VAC_301 Razzle-Dazzler, VAC_305 Frosty Decor, VAC_308 Siren Song,
  VAC_323 Malted Magma (Drink), VAC_324 Matching Outfits,
  VAC_328 Meltemental, VAC_329 Natural Talent,
  VAC_449 Carress, Cabaret Star, VAC_450 Carefree Cookie (Tourist),
  VAC_954 Cabaret Headliner.
"""

from utils import *

from hearthstone.enums import SpellSchool

import fireplace.cards as _cards

FIREBALL = "CS2_029"          # FIRE  (school 2)
FROSTBOLT = "CS2_024"         # FROST (school 3)
ARCANE_INTELLECT = "CS2_023"  # ARCANE (school 1)


# VAC_301 — Razzle-Dazzler: Battlecry: Summon a random 5-Cost minion.
# Repeat for each spell school you've cast this game.
def test_razzle_dazzler_one_summon_when_no_schools_cast():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    assert len(p1.spells_cast_by_school) == 0
    pre = len(p1.field)
    p1.give("VAC_301").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    summoned = p1.field[pre:]
    # Razzle-Dazzler itself + exactly one random 5-Cost minion (1 + 0 schools).
    dazzler = [m for m in summoned if m.id == "VAC_301"]
    others = [m for m in summoned if m.id != "VAC_301"]
    assert len(dazzler) == 1
    assert len(others) == 1
    assert others[0].data.cost == 5


def test_razzle_dazzler_repeats_per_distinct_school():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # Cast two spells of two distinct schools (FIRE + FROST) -> 2 schools.
    p1.give(FIREBALL).play(target=game.player2.hero)
    p1.give(FROSTBOLT).play(target=game.player2.hero)
    assert len(p1.spells_cast_by_school) == 2
    p1.used_mana = 0  # refill so the 7-cost Razzle-Dazzler is playable
    pre = len(p1.field)
    p1.give("VAC_301").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    summoned = [m for m in p1.field[pre:] if m.id != "VAC_301"]
    # 1 base + 2 distinct schools = 3 random 5-Cost minions.
    assert len(summoned) == 3
    for m in summoned:
        assert m.data.cost == 5


# VAC_305 — Frosty Decor: Summon two 2/4 Elementals with Taunt and
# "Deathrattle: Gain 4 Armor".
def test_frosty_decor_summons_two_ice_sculptures():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    pre = len(p1.field)
    p1.give("VAC_305").play()
    sculptures = [m for m in p1.field[pre:] if m.id == "VAC_305t"]
    assert len(sculptures) == 2
    for m in sculptures:
        assert (m.atk, m.max_health) == (2, 4)
        assert m.taunt
        assert Race.ELEMENTAL in m.races


def test_ice_sculpture_deathrattle_gains_4_armor():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    assert p1.hero.armor == 0
    sculpture = p1.summon("VAC_305t")
    sculpture.destroy()
    game.process_deaths()
    assert p1.hero.armor == 4


# VAC_308 — Siren Song: Get two random spells from spell schools you
# haven't cast this game.
def test_siren_song_gives_two_spells():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give("VAC_308").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Exactly two spells handed to the player.
    assert len(p1.hand) == 2
    for c in p1.hand:
        assert c.type == CardType.SPELL


def test_siren_song_spells_from_uncast_schools():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Cast a FIRE spell first; the two Siren Song spells must not be FIRE.
    p1.give(FIREBALL).play(target=game.player2.hero)
    assert set(p1.spells_cast_by_school.keys()) == {int(SpellSchool.FIRE)}
    pre = len(p1.hand)
    p1.give("VAC_308").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    gained = p1.hand[pre:]
    assert len(gained) == 2
    for c in gained:
        assert int(c.spell_school) != int(SpellSchool.FIRE)


# VAC_323 — Malted Magma (Drink): Deal 1 damage to all enemies. (3 Drinks left!)
def test_malted_magma_deals_1_to_all_enemies_and_chains():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(WISP)  # 1/1
    enemy2 = p2.summon("CS2_172")  # Bloodfen Raptor 3/2
    pre_hero = p2.hero.health
    p1.give("VAC_323").play()
    # 1 damage to all enemies (hero + both minions).
    assert p2.hero.health == pre_hero - 1
    assert enemy.dead  # 1/1 took 1 -> dead
    game.process_deaths()
    assert enemy2.health == 2 - 1
    # Next Drink (2 Drinks left) appears in hand.
    nexts = [c for c in p1.hand if c.id == "VAC_323t"]
    assert len(nexts) == 1


def test_malted_magma_drink_chain_to_last():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # Second copy (2 Drinks left) -> hands the last copy.
    p1.give("VAC_323t").play()
    last = [c for c in p1.hand if c.id == "VAC_323t2"]
    assert len(last) == 1
    # Clear hand then play the LAST drink -> returns nothing.
    for c in list(p1.hand):
        if c.id != "VAC_323t2":
            c.discard()
    last_card = [c for c in p1.hand if c.id == "VAC_323t2"][0]
    last_card.play()
    # No further copies of any Malted Magma variant in hand.
    assert not any(c.id in ("VAC_323", "VAC_323t", "VAC_323t2") for c in p1.hand)


# VAC_324 — Matching Outfits: Transform a minion into a random one that
# costs (1) more, then summon a copy of it.
def test_matching_outfits_transforms_and_summons_copy():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    target = p1.summon("CS2_172")  # Bloodfen Raptor, 2-Cost
    p1.give("VAC_324").play(target=target)
    field_ids = [m.id for m in p1.field]
    # Original Raptor was transformed away.
    assert "CS2_172" not in field_ids
    # Board is exactly the morphed minion + one summoned copy = two identical
    # minions and nothing else.
    assert len(field_ids) == 2
    assert field_ids[0] == field_ids[1]
    morphed_id = field_ids[0]
    # The transformed minion costs (1) more than the original 2-Cost target.
    assert _cards.db[morphed_id].cost == 3


# VAC_328 — Meltemental: Taunt. This is permanently Frozen.
def test_meltemental_is_taunt_and_frozen():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    m = p1.summon("VAC_328")
    assert m.taunt
    assert m.frozen


def test_meltemental_refreezes_at_turn_begin():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    m = p1.summon("VAC_328")
    # Force-thaw it, then cycle turns. The TURN_BEGIN trigger re-applies FROZEN
    # so a permanently-frozen Meltemental never stays thawed.
    m.frozen = False
    game.end_turn()
    game.end_turn()  # back to player1's turn-begin
    assert m.frozen


# VAC_329 — Natural Talent: Get a random Naga and a random spell. They
# cost (1) less.
def test_natural_talent_gives_naga_and_spell_discounted():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give("VAC_329").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Exactly two cards: one Naga minion and one spell.
    assert len(p1.hand) == 2
    nagas = [c for c in p1.hand if c.type == CardType.MINION and Race.NAGA in c.races]
    spells = [c for c in p1.hand if c.type == CardType.SPELL]
    assert len(nagas) == 1
    assert len(spells) == 1
    # Each costs (1) less than its base cost (clamped at 0).
    for c in p1.hand:
        assert c.cost == max(0, c.data.cost - 1)


# VAC_449 — Carress, Cabaret Star: While in hand, play two different spell
# schools to transform into a combined-effect variant.
def test_carress_vanilla_until_two_schools():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    carress = p1.give("VAC_449")
    # Cast a single FIRE spell -> only one distinct school -> no transform.
    p1.give(FIREBALL).play(target=game.player2.hero)
    assert carress.id == "VAC_449"
    assert int(SpellSchool.FIRE) in carress.spell_schools_cast_while_holding
    assert len(carress.spell_schools_cast_while_holding) == 1


def test_carress_transforms_after_two_distinct_schools():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    carress = p1.give("VAC_449")
    # Cast ARCANE (1) then FIRE (2) -> variant for schools {1,2} = VAC_449t
    # (Draw 2 + Deal 6 to enemy hero).
    p1.give(ARCANE_INTELLECT).play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    p1.give(FIREBALL).play(target=game.player2.hero)
    # The held card morphed; the hand card object now carries the variant id.
    held = [c for c in p1.hand if c.id.startswith("VAC_449t")]
    assert len(held) == 1
    assert held[0].id == "VAC_449t"


# VAC_450 — Carefree Cookie (Demon Hunter Tourist): After a friendly minion
# dies, summon a random minion that costs (1) more.
def test_carefree_cookie_summons_cost_plus_one_on_friendly_death():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.summon("VAC_450")
    victim = p1.summon("CS2_172")  # Bloodfen Raptor, 2-Cost
    pre = len(p1.field)
    victim.destroy()
    game.process_deaths()
    # Cookie + (raptor removed) + one new random 3-Cost minion.
    summoned = [m for m in p1.field if m.id not in ("VAC_450",)]
    assert len(summoned) == 1
    assert summoned[0].data.cost == 3


def test_carefree_cookie_tourist_unlocks_demonhunter():
    # Deckbuilding-only Tourist keyword: a Shaman deck built with a Demon
    # Hunter tourist may include Demon Hunter cards.
    from fireplace.utils import random_draft
    deck = random_draft(CardClass.SHAMAN, tourist=CardClass.DEMONHUNTER)
    classes = set()
    has_tourist = False
    for cid in deck:
        c = _cards.db[cid]
        cls = list(getattr(c, "classes", None) or [c.card_class])
        classes.update(cls)
        if c.id == "VAC_450" or getattr(c, "tourist_class", None) == CardClass.DEMONHUNTER:
            has_tourist = True
    assert CardClass.DEMONHUNTER in classes


# VAC_954 — Cabaret Headliner: Battlecry: Reduce the Cost of a spell of each
# school in your hand by (2).
def test_cabaret_headliner_reduces_one_spell_per_school():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Two FIRE spells + one FROST spell in hand. Only ONE per school discounted.
    fire1 = p1.give(FIREBALL)       # FIRE, base 4
    fire2 = p1.give(FIREBALL)       # FIRE, base 4
    frost = p1.give(FROSTBOLT)      # FROST, base 2
    p1.give("VAC_954").play()
    fire_costs = sorted([fire1.cost, fire2.cost])
    # Exactly one FIRE spell discounted by 2 (4 -> 2); the other stays 4.
    assert fire_costs == [2, 4]
    # The single FROST spell discounted by 2 (2 -> 0).
    assert frost.cost == 0
