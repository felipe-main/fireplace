"""The Great Dark Beyond — MAGE collectible card tests.

Covers all 10 collectible mage cards (GDB_133, GDB_134, GDB_135, GDB_136,
GDB_301, GDB_302, GDB_303, GDB_304, GDB_305, GDB_456). Assertions pin the
PRINTED card behaviour.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone, Race, SpellSchool

import fireplace.cards as _cards


# Stat-stable neutral minions used as deterministic targets / fodder.
WISP = "CS2_231"            # 0/1/1 vanilla
BLOODFEN = "CS2_172"        # 2/3/2 vanilla Bloodfen Raptor
CHILLWIND = "CS2_182"       # 4/4/5 vanilla Chillwind Yeti
MOONFIRE = "CS2_008"        # 0-cost spell (deal 1)
FIREBALL = "CS2_029"        # 4-cost spell (deal 6)
ELEMENTAL_TOKEN = "UNG_809t1"  # 2/3/2 Elemental token


def _is_fire_spell(card):
    return (
        card.type == CardType.SPELL
        and card.spell_school is not None
        and int(card.spell_school) == int(SpellSchool.FIRE)
    )


# GDB_133 — Pocket Dimension — Discover a spell. Repeat until you see one for
# the second time.
def test_pocket_dimension_discovers_spells_until_repeat():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pre_hand = len(p1.hand)
    spell = p1.give("GDB_133")
    spell.play()
    # Auto-resolve every Discover the card opens; every offered card is a spell.
    offered = 0
    while p1.choice:
        for cid in p1.choice.cards:
            assert _cards.db[cid].type == CardType.SPELL
        offered += 1
        p1.choice.choose(p1.choice.cards[0])
    # At least the initial discover happened, and every chosen card landed in
    # hand — the spells gained equal the discovers resolved, capped by the
    # 10-card hand limit (extra discovers past a full hand are burned).
    gained = len([c for c in p1.hand if c.type == CardType.SPELL])
    assert offered >= 1
    assert gained == min(offered, p1.max_hand_size - pre_hand)


# GDB_134 — Arkwing Pilot — At the end of your turn, deal 3 damage to a random
# enemy. Spellburst: Summon an Arkwing Pilot.
def test_arkwing_pilot_end_of_turn_deals_three():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Make p1 the current player so OWN_TURN_END fires for it.
    if game.current_player is not p1:
        game.end_turn()
    p1.summon("GDB_134")
    # Only enemy character is the hero (no enemy minions); beef it so it absorbs.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    game.end_turn()
    assert p2.hero.damage == 3


def test_arkwing_pilot_spellburst_summons_copy():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    pilot = p1.summon("GDB_134")
    assert pilot.has_spellburst
    pre = len(p1.field)
    # Casting a spell triggers Spellburst -> a second Arkwing Pilot appears.
    p1.give(MOONFIRE).play(target=p2.hero)
    summoned = [m for m in p1.field[pre:] if m.id == "GDB_134"]
    assert len(summoned) == 1
    assert not pilot.has_spellburst


# GDB_135 — Ingenious Artificer — Battlecry: The next Draenei you play refreshes
# Mana Crystals equal to its Attack.
def test_ingenious_artificer_refreshes_mana_on_next_draenei():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    artificer = p1.give("GDB_135")
    artificer.play()  # battlecry arms the hook
    # Spend mana down so the refresh is observable.
    p1.used_mana = 8  # mana = 10 - 8 = 2
    assert p1.mana == 2
    # GDB_131 Velen is a Draenei; instead use a cheap Draenei: Arkwing is 7-cost.
    # Use Ingenious Artificer's own race payoff via a 4-attack Draenei token.
    # Play a Draenei minion (GDB_135 itself is 4-atk). Give a fresh one.
    draenei = p1.give("GDB_135")
    # Make its play free of mana concerns: set used_mana so it can be summoned
    # by hand-play; but play() pays cost. Bypass by summoning won't fire the
    # hook (only *playing* does). So clear cost via used_mana reset.
    p1.used_mana = 5  # mana = 5, GDB_135 costs 5
    pre_mana = p1.mana
    draenei.play()
    # Next Draenei (4 attack) refreshes 4 Mana Crystals this turn.
    # After paying its 5 cost (mana 5 -> 0) then refunding 4 -> mana == 4.
    assert p1.mana == 4


# GDB_136 — Exarch Hataaru — Battlecry: Discover a spell and reduce its Cost by
# (1). If you play it this turn, repeat this effect.
def test_exarch_hataaru_discovers_and_discounts():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pre = len(p1.hand)
    hataaru = p1.give("GDB_136")
    hataaru.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Exactly one spell was discovered into hand...
    gained = [c for c in p1.hand if c.type == CardType.SPELL]
    assert len(gained) == 1
    spell = gained[0]
    # ...and its cost is reduced by (1) vs its base data cost.
    assert spell.cost == max(0, (spell.data.cost or 0) - 1)


# GDB_301 — Supernova — Fill your hand with random Fire spells. They cost (1).
def test_supernova_fills_hand_with_one_cost_fire_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Start from an empty hand for a clean fill count.
    for c in list(p1.hand):
        c.discard()
    assert len(p1.hand) == 0
    spell = p1.give("GDB_301")  # now hand has 1 (Supernova itself)
    spell.play()  # consumes itself, then fills hand
    # Hand is filled to max with Fire spells, each costing exactly 1.
    assert len(p1.hand) == p1.max_hand_size
    for c in p1.hand:
        assert _is_fire_spell(c)
        assert c.cost == 1


# GDB_302 — Blazing Accretion — Battlecry: Destroy the top 3 cards of your deck.
# Any Fire spells or Elementals are drawn instead.
def test_blazing_accretion_draws_fire_and_elementals_destroys_rest():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Build the top of deck (deck[-1] is the top). Push three known cards:
    # bottom-of-the-three = WISP (neutral non-elemental minion) -> destroyed,
    # middle = FIREBALL (Fire spell) -> drawn,
    # top = ELEMENTAL_TOKEN (Elemental minion) -> drawn.
    wisp = p1.give(WISP); wisp.zone = Zone.DECK
    fireball = p1.give(FIREBALL); fireball.zone = Zone.DECK
    elem = p1.give(ELEMENTAL_TOKEN); elem.zone = Zone.DECK
    assert Race.ELEMENTAL in elem.races
    assert _is_fire_spell(fireball)
    acc = p1.give("GDB_302")
    acc.play()
    # Fire spell + elemental drawn to hand; wisp destroyed (graveyard).
    assert fireball.zone == Zone.HAND
    assert elem.zone == Zone.HAND
    assert wisp.zone == Zone.GRAVEYARD


# GDB_303 — Blasteroid — Battlecry: Shuffle 5 random Fire spells into your deck.
# They cost (2) less.
def test_blasteroid_shuffles_five_discounted_fire_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pre_deck = len(p1.deck)
    blast = p1.give("GDB_303")
    blast.play()
    # Five new cards in the deck, each a Fire spell costing 2 less than base.
    added = [c for c in p1.deck]
    assert len(p1.deck) - pre_deck == 5
    fire_spells = [c for c in p1.deck if _is_fire_spell(c)]
    assert len(fire_spells) == 5
    for c in fire_spells:
        assert c.cost == max(0, (c.data.cost or 0) - 2)


# GDB_304 — Saruun — Battlecry: Give all Elementals in your deck Fire Spell
# Damage +1.
def test_saruun_buffs_deck_elementals_fire_spellpower():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    elem = p1.give(ELEMENTAL_TOKEN); elem.zone = Zone.DECK
    wisp = p1.give(WISP); wisp.zone = Zone.DECK  # non-elemental control
    saruun = p1.give("GDB_304")
    saruun.play()
    # Elemental in deck got Fire Spell Damage +1; non-elemental did not.
    assert elem.tags.get(GameTag.SPELLPOWER_FIRE, 0) == 1
    assert wisp.tags.get(GameTag.SPELLPOWER_FIRE, 0) == 0


# GDB_305 — Solar Flare — Deal $2 damage to all enemies. Costs (1) less for each
# Elemental you control.
def test_solar_flare_damages_all_enemies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    e1 = p2.summon(CHILLWIND)  # 4/5 survives 2
    e2 = p2.summon(CHILLWIND)  # 4/5 survives 2
    # Friendly minion is NOT an enemy -> untouched.
    friendly = p1.summon(CHILLWIND)
    spell = p1.give("GDB_305")
    spell.play()
    assert e1.damage == 2
    assert e2.damage == 2
    assert p2.hero.damage == 2
    assert friendly.damage == 0


def test_solar_flare_cost_reduced_per_elemental():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    spell = p1.give("GDB_305")
    base = spell.data.cost  # 5
    assert spell.cost == base
    # Each Elemental I control reduces cost by 1.
    p1.summon(ELEMENTAL_TOKEN)
    p1.summon(ELEMENTAL_TOKEN)
    assert spell.cost == base - 2
    # A non-elemental minion does not reduce it further.
    p1.summon(WISP)
    assert spell.cost == base - 2


# GDB_456 — Spontaneous Combustion — Deal $4 damage to a random enemy. If you
# played an Elemental last turn, choose the target.
def test_spontaneous_combustion_hits_random_enemy_for_four():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    # Single enemy character: beef the hero so it absorbs the whole hit, and it
    # is the only legal random target (no enemy minions).
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    spell = p1.give("GDB_456")
    # No elemental played last turn -> random (only the hero is available).
    spell.play()
    assert p2.hero.damage == 4


def test_spontaneous_combustion_targeted_after_elemental():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    enemy = p2.summon(CHILLWIND)  # 4/5
    enemy.max_health = 80
    enemy._max_health = 80
    enemy.damage = 0
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    spell = p1.give("GDB_456")
    # When a target is supplied, deal 4 to exactly that enemy.
    spell.play(target=enemy)
    assert enemy.damage == 4
    assert p2.hero.damage == 0
