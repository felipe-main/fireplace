"""Across the Timeways — Druid (TIME_) card tests.

One tight test per collectible card (plus effect-bearing tokens/locations).
"""
from utils import *

from hearthstone.enums import CardClass, Zone, GameTag, SpellSchool, Race, CardType
from fireplace import enums


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# TIME_023 Contingency — Draw the bottom two cards from your deck.
# ---------------------------------------------------------------------------
def test_contingency_draws_bottom_two():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Build deck bottom->top: bottom0, bottom1, then a "top" card. deck[0] is
    # bottom; deck[-1] is the next normal draw.
    bottom0 = p1.card("CS2_171")   # Stonetusk Boar
    bottom0.zone = Zone.DECK
    bottom1 = p1.card("CS2_172")   # Bloodfen Raptor
    bottom1.zone = Zone.DECK
    top = p1.card("CS2_182")       # Chillwind Yeti (must stay in deck)
    top.zone = Zone.DECK
    assert p1.deck[0] is bottom0 and p1.deck[1] is bottom1
    spell = p1.give("TIME_023")
    spell.play()
    # Exactly the two bottom cards were drawn; the top card stays in deck.
    assert bottom0.zone == Zone.HAND
    assert bottom1.zone == Zone.HAND
    assert top.zone == Zone.DECK
    assert len(p1.deck) == 1


# ---------------------------------------------------------------------------
# TIME_701 Waveshaping — Discover a card from your deck. The others to bottom.
# ---------------------------------------------------------------------------
def test_waveshaping_picks_from_deck_and_bottoms_others():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    ids = ["CS2_171", "CS2_172", "CS2_182"]  # 3 distinct deck cards
    for cid in ids:
        c = p1.card(cid)
        c.zone = Zone.DECK
    spell = p1.give("TIME_701")
    spell.play()
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    pick_id = p1.choice.cards[0].id
    p1.choice.choose(p1.choice.cards[0])
    assert p1.choice is None
    # The picked card is now in hand; deck retains the other two.
    assert pick_id in [c.id for c in p1.hand]
    assert len(p1.deck) == 2
    assert pick_id not in [c.id for c in p1.deck]


# ---------------------------------------------------------------------------
# TIME_702 Ebb and Flow — Deal 3 damage. If you played a minion while holding
# this, gain 5 Armor.
# ---------------------------------------------------------------------------
def test_ebb_and_flow_no_minion_played_no_armor():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.hero.armor = 0
    target = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    spell = p1.give("TIME_702")
    spell.play(target=target)
    assert target.damage == 3
    assert p1.hero.armor == 0


def test_ebb_and_flow_minion_played_grants_armor():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.hero.armor = 0
    spell = p1.give("TIME_702")  # held in hand
    # Play a minion while Ebb and Flow is held -> arms the bonus.
    p1.give("CS2_182").play()
    target = game.player2.summon("CS2_182")  # 4/5, survives 3
    spell.play(target=target)
    assert target.damage == 3
    assert p1.hero.armor == 5


# ---------------------------------------------------------------------------
# TIME_707 Alternate Reality — Replace hand and deck with random Choose One
# cards from the past. They cost (1) less.
# ---------------------------------------------------------------------------
def test_alternate_reality_replaces_with_discounted_choose_one():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Seed a deck of 3 + a hand of 1 (besides the spell).
    for _ in range(3):
        c = p1.card("CS2_171")
        c.zone = Zone.DECK
    p1.give("CS2_172")  # a non-choose-one hand card
    pre_deck = len(p1.deck)
    pre_hand = len(p1.hand)  # includes the filler + (spell added next)
    spell = p1.give("TIME_707")
    # Hand now = filler + spell; after play the spell leaves hand.
    spell.play()
    _resolve_choices(p1)
    # Deck refilled to its prior size with Choose One cards, each discounted.
    assert len(p1.deck) == pre_deck
    for c in p1.deck:
        assert c.tags.get(GameTag.CHOOSE_ONE, 0) == 1
        assert c.cost == max(0, (c.data.cost or 0) - 1)
    # Hand also refilled with Choose One cards.
    for c in p1.hand:
        assert c.tags.get(GameTag.CHOOSE_ONE, 0) == 1


# ---------------------------------------------------------------------------
# TIME_033 Druid of Regrowth — Rewind Battlecry: Cast 2 random Nature spells.
# ---------------------------------------------------------------------------
def test_druid_of_regrowth_casts_two_nature_spells():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Count spells cast this game before/after; battlecry casts exactly 2.
    pre = len(p1.spells_cast_this_game)
    card = p1.give("TIME_033")
    card.play()
    _resolve_choices(p1)            # resolve any spell-internal choices
    _resolve_choices(game.player2)
    # Two Nature spells were cast as part of the battlecry.
    cast = p1.spells_cast_this_game[pre:]
    assert len(cast) >= 2
    for s in cast[:2]:
        assert s.data.spell_school == SpellSchool.NATURE


def test_druid_of_regrowth_rewind_recasts():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    card = p1.give("TIME_033")
    card.play()
    # After the battlecry, the engine offers the Rewind timeline choice.
    assert p1.choice is not None
    ids = sorted(c.id for c in p1.choice.cards)
    assert ids == ["TIME_000ta", "TIME_000tb"]
    pre = len(p1.spells_cast_this_game)
    rewind = next(c for c in p1.choice.cards if c.id == "TIME_000tb")
    p1.choice.choose(rewind)
    _resolve_choices(p1)
    _resolve_choices(game.player2)
    # Rewind re-ran the battlecry: 2 more Nature spells cast.
    assert len(p1.spells_cast_this_game) - pre >= 2


# ---------------------------------------------------------------------------
# TIME_703 Endangered Dodo — Taunt Battlecry: If you have 10 or less Health,
# gain +5/+5 and summon a copy of this.
# ---------------------------------------------------------------------------
def test_endangered_dodo_above_threshold_no_effect():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0       # 30 health > 10
    dodo = p1.give("TIME_703")
    dodo.play()
    assert dodo.taunt
    assert dodo.atk == 5 and dodo.health == 5
    # No extra copy summoned.
    assert len([m for m in p1.field if m.id == "TIME_703"]) == 1


def test_endangered_dodo_low_health_buffs_and_copies():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 22      # 8 health <= 10
    dodo = p1.give("TIME_703")
    dodo.play()
    # The played Dodo gained +5/+5 -> 10/10.
    assert dodo.atk == 10 and dodo.health == 10
    copies = [m for m in p1.field if m.id == "TIME_703"]
    assert len(copies) == 2
    # The summoned copy carries the +5/+5 too (copied from the buffed original).
    other = next(m for m in copies if m is not dodo)
    assert other.atk == 10 and other.health == 10


# ---------------------------------------------------------------------------
# TIME_704 Highborne Mentor — Battlecry: Get a 2/2 Pupil. Discover a spell
# costing 7+ to teach it. The Pupil's battlecry casts the taught spell.
# ---------------------------------------------------------------------------
def test_highborne_mentor_teaches_pupil():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    mentor = p1.give("TIME_704")
    mentor.play()
    # Discover offers 3 spells costing 7+.
    assert p1.choice is not None
    for c in p1.choice.cards:
        assert c.cost >= 7
    taught_id = p1.choice.cards[0].id
    p1.choice.choose(p1.choice.cards[0])
    # A 2/2 Pupil is now in hand, stamped with the taught spell.
    pupil = next(c for c in p1.hand if c.id == "TIME_704t")
    assert pupil.atk == 2 and pupil.health == 2
    assert pupil._taught_spell == taught_id


def test_highborne_pupil_casts_taught_spell():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    pupil = p1.give("TIME_704t")
    pupil._taught_spell = "CS2_029"  # Fireball: 6 damage to a target
    pre = len(p1.spells_cast_this_game)
    pupil.play()
    _resolve_choices(p1)
    _resolve_choices(game.player2)
    # The taught spell was cast as the Pupil's battlecry.
    assert any(s.id == "CS2_029" for s in p1.spells_cast_this_game[pre:])


# ---------------------------------------------------------------------------
# TIME_705 Krona, Keeper of Eons — Taunt Battlecry: Set the Costs of the
# bottom 5 cards of your deck to (1).
# ---------------------------------------------------------------------------
def test_krona_sets_bottom_five_costs_to_one():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # 6 deck cards, all expensive; only the bottom 5 (deck[:5]) get set to 1.
    cards = []
    for _ in range(6):
        c = p1.card("EX1_279")  # Pyroblast, cost 10
        c.zone = Zone.DECK
        cards.append(c)
    assert all(c.cost == 10 for c in cards)
    krona = p1.give("TIME_705")
    krona.play()
    assert krona.taunt
    # Bottom 5 are now cost 1; the topmost (deck[5]) untouched.
    for c in p1.deck[:5]:
        assert c.cost == 1
    assert p1.deck[5].cost == 10


# ---------------------------------------------------------------------------
# TIME_730 Kaldorei Cultivator — Battlecry: Discover 2 Beasts. Put them on the
# bottom of your deck with +5/+5.
# ---------------------------------------------------------------------------
def test_kaldorei_cultivator_bottoms_two_buffed_beasts():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    pre_deck = len(p1.deck)
    cult = p1.give("TIME_730")
    cult.play()
    # Two sequential Beast discovers.
    _resolve_choices(p1)
    # Exactly two Beasts added to the deck, each buffed +5/+5.
    assert len(p1.deck) == pre_deck + 2
    for c in p1.deck:
        assert c.race == Race.BEAST or Race.BEAST in c.races
        # base stats + 5/+5
        assert c.atk == (c.data.atk or 0) + 5
        assert c.max_health == (c.data.health or 0) + 5


# ---------------------------------------------------------------------------
# TIME_211 Lady Azshara — Fabled Choose One: Empower Zin-Azshari; or The Well
# of Eternity. (The other gets destroyed.)
# ---------------------------------------------------------------------------
def test_lady_azshara_choose_well_places_empowered_well():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    azshara = p1.give("TIME_211")
    assert sorted(c.id for c in azshara.choose_cards) == ["TIME_211a", "TIME_211b"]
    # Choose Empower the Well -> places the empowered Well location.
    azshara.play(choose="TIME_211b")
    assert p1.location is not None
    assert p1.location.id == "TIME_211t1t"


def test_lady_azshara_choose_zin_places_empowered_zin():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    azshara = p1.give("TIME_211")
    azshara.play(choose="TIME_211a")
    assert p1.location is not None
    assert p1.location.id == "TIME_211t2t"


# ---------------------------------------------------------------------------
# TIME_211t1 The Well of Eternity (base) — activate: fill hand with random
# Temporary spells.
# ---------------------------------------------------------------------------
def test_well_of_eternity_fills_hand_with_temporary_spells():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    loc = p1.summon("TIME_211t1")
    game.end_turn()
    game.end_turn()
    # Empty the hand right before use so the fill is observed precisely.
    for c in list(p1.hand):
        c.discard()
    loc.use()
    # Hand is now full, and every filled card is a Temporary spell.
    assert len(p1.hand) == p1.max_hand_size
    for c in p1.hand:
        assert c.type == CardType.SPELL
        assert c.tags.get(enums.TEMPORARY, 0)


# ---------------------------------------------------------------------------
# TIME_211t2 Zin-Azshari (base) — activate: summon a copy of a friendly minion.
# ---------------------------------------------------------------------------
def test_zin_azshari_summons_copy_of_friendly_minion():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Clear board, place exactly one friendly minion so the copy is deterministic.
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    orig = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    loc = p1.summon("TIME_211t2")
    game.end_turn()
    game.end_turn()
    loc.use()
    yetis = [m for m in p1.field if m.id == "CS2_182"]
    assert len(yetis) == 2
    for y in yetis:
        assert y.atk == 4 and y.max_health == 5


# ---------------------------------------------------------------------------
# TIME_211t2t Zin-Azshari (empowered) — summon a copy with doubled stats.
# ---------------------------------------------------------------------------
def test_zin_azshari_empowered_summons_doubled_copy():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    orig = p1.summon("CS2_182")  # 4/5
    loc = p1.summon("TIME_211t2t")
    game.end_turn()
    game.end_turn()
    loc.use()
    yetis = [m for m in p1.field if m.id == "CS2_182"]
    assert len(yetis) == 2
    copy = next(m for m in yetis if m is not orig)
    # Doubled: 8/10.
    assert copy.atk == 8 and copy.max_health == 10


# ---------------------------------------------------------------------------
# END_009 Splintered Reality — Summon two 2/2 Treants. They gain +1/+1 for
# each friendly Treant that died this game.
# ---------------------------------------------------------------------------
def test_splintered_reality_no_dead_treants_summons_vanilla():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    spell = p1.give("END_009")
    spell.play()
    treants = [m for m in p1.field if m.id == "END_009t"]
    assert len(treants) == 2
    # No friendly Treant died this game -> vanilla 2/2 each.
    for t in treants:
        assert t.atk == 2 and t.max_health == 2


def test_splintered_reality_buffs_per_dead_treant():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    # Kill three friendly Treant tokens this game.
    deaths = [p1.summon("END_009t") for _ in range(3)]
    for t in deaths:
        t.destroy()
    game.process_deaths()
    assert all(t.zone == Zone.GRAVEYARD for t in deaths)
    spell = p1.give("END_009")
    spell.play()
    treants = [m for m in p1.field if m.id == "END_009t"]
    assert len(treants) == 2
    # 3 dead Treants -> +3/+3 each -> 5/5.
    for t in treants:
        assert t.atk == 5 and t.max_health == 5
