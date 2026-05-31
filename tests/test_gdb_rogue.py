"""The Great Dark Beyond — ROGUE collectible card tests.

Covers all 10 collectible Rogue cards:
  GDB_102 Starship Schematic, GDB_465 Barrel Roll,
  GDB_466 The Gravitational Displacer, GDB_467 Quasar, GDB_472 Talgath,
  GDB_870 Eredar Skulker, GDB_873 Lucky Comet, GDB_875 Spacerock Collector,
  GDB_876 Scrounging Shipwright, GDB_881 Pressure Points.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards

from fireplace.actions import LaunchStarship


def _other_class_pieces(player):
    cls = getattr(player.hero, "card_class", None)
    return {
        cid
        for cid, c in _cards.db.items()
        if c.collectible
        and c.tags.get(GameTag.STARSHIP_PIECE, 0)
        and c.card_class != cls
    }


# GDB_102 — Starship Schematic | SPELL 1:
# Discover a Starship Piece from another class. It costs (1) less.
def test_starship_schematic_discovers_foreign_piece_discounted():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    pool = _other_class_pieces(p1)
    spell = p1.give("GDB_102")
    spell.play()
    assert p1.choice is not None
    # A Discover offers 3 options, all foreign Starship Pieces.
    assert len(p1.choice.cards) == 3
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.tags.get(GameTag.STARSHIP_PIECE, 0)
        assert cdata.card_class != p1.hero.card_class
        assert cid in pool
    chosen_id = p1.choice.cards[0]
    base_cost = p1.card(chosen_id).cost
    p1.choice.choose(p1.choice.cards[0])
    held = next(c for c in p1.hand if c.id == chosen_id)
    # The discovered piece costs (1) less.
    assert held.cost == base_cost - 1


# GDB_465 — Barrel Roll | SPELL 3:
# Deal $5 damage to an undamaged character. Costs (1) if you're building a
# Starship.
def test_barrel_roll_deals_5_to_undamaged():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_231")  # Wisp 1/1
    victim.max_health = 80
    victim._max_health = 80
    victim.damage = 0
    spell = p1.give("GDB_465")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.damage == 5


def test_barrel_roll_full_price_when_not_building_starship():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    assert not p1.is_building_starship
    spell = p1.give("GDB_465")
    assert spell.cost == 3  # base


def test_barrel_roll_costs_one_while_building_starship():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Bank a piece to start building a Starship.
    piece = p1.summon("GDB_100")
    piece.destroy()
    game.process_deaths()
    assert p1.is_building_starship
    spell = p1.give("GDB_465")
    # 3 - 2 = 1 while building.
    assert spell.cost == 1


# GDB_466 — The Gravitational Displacer | MINION 5/5/4:
# Starship Piece. When this is launched, summon a copy of the Starship.
def test_gravitational_displacer_banks_as_piece_and_launches():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    piece = p1.summon("GDB_466")
    a, h = p1.card("GDB_466").atk, p1.card("GDB_466").health
    assert piece.data.tags.get(GameTag.STARSHIP_PIECE, 0)
    piece.destroy()
    game.process_deaths()
    ship = p1.starship
    assert ship is not None
    assert ship.id == "GDB_100t8"  # Rogue's ship
    assert (ship.atk, ship.max_health) == (a, h)

    game.queue_actions(p1.hero, [LaunchStarship(p1)])
    game.process_deaths()
    # The ship launches into a real, attackable minion with the piece's stats.
    launched = [m for m in p1.field if m.id == "GDB_100t8"]
    assert len(launched) >= 1
    assert (launched[0].atk, launched[0].max_health) == (a, h)
    assert not launched[0].dormant


def test_gravitational_displacer_launch_summons_copy():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    piece = p1.summon("GDB_466")
    a, h = p1.card("GDB_466").atk, p1.card("GDB_466").health
    piece.destroy()
    game.process_deaths()

    game.queue_actions(p1.hero, [LaunchStarship(p1)])
    game.process_deaths()
    # Launched ship + the summoned copy = two ships on the board.
    ships = [m for m in p1.field if m.id == "GDB_100t8"]
    assert len(ships) == 2
    for s in ships:
        assert (s.atk, s.max_health) == (a, h)


# GDB_467 — Quasar | SPELL 8:
# Shuffle your hand into your deck. Reduce the Cost of cards in your deck
# by (3).
def test_quasar_shuffles_hand_and_discounts_deck():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # One pre-existing card sitting in the deck (Fireball, base 4).
    deck_card = p1.give("CS2_029")
    deck_card.zone = Zone.DECK
    # A hand card that will get shuffled in then discounted (Fireball, base 4).
    hand_card = p1.give("CS2_029")
    assert hand_card.zone == Zone.HAND
    assert hand_card.cost == 4

    quasar = p1.give("GDB_467")
    quasar.play()
    game.process_deaths()

    # Hand is empty of the shuffled card; both Fireballs now live in the deck.
    assert hand_card.zone == Zone.DECK
    assert deck_card.zone == Zone.DECK
    # Both deck cards cost (3) less.
    assert deck_card.cost == 4 - 3
    assert hand_card.cost == 4 - 3


# GDB_472 — Talgath | MINION 3/3/3:
# Undamaged enemy minions take double damage. Combo: Get a Backstab.
def test_talgath_combo_gives_backstab():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Trigger Combo: play another card first this turn.
    p1.give("CS2_231").play()
    pre = len([c for c in p1.hand if c.id == "CS2_072"])
    talgath = p1.give("GDB_472")
    talgath.play()
    game.process_deaths()
    backstabs = [c for c in p1.hand if c.id == "CS2_072"]
    assert len(backstabs) == pre + 1


def test_talgath_no_combo_no_backstab():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # First card of the turn -> no Combo.
    talgath = p1.give("GDB_472")
    talgath.play()
    game.process_deaths()
    assert not any(c.id == "CS2_072" for c in p1.hand)


def test_talgath_doubles_damage_to_undamaged_enemy_minions():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.summon("GDB_472")  # Talgath aura
    foe = p2.summon("CS2_201")
    foe.max_health = 30
    foe.damage = 0
    game.refresh_auras()
    # First hit lands while undamaged -> doubled (3 -> 6).
    game.queue_actions(p1.hero, [Hit(foe, 3)])
    assert foe.damage == 6
    # Now it is damaged, so a second hit is NOT doubled (+3 -> 9, not 12).
    game.queue_actions(p1.hero, [Hit(foe, 3)])
    assert foe.damage == 9


def test_talgath_does_not_double_friendly_or_damaged():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.summon("GDB_472")
    friendly = p1.summon("CS2_201")
    friendly.max_health = 30
    friendly.damage = 0
    game.refresh_auras()
    # Talgath only affects ENEMY minions; a friendly takes normal damage.
    game.queue_actions(p1.hero, [Hit(friendly, 3)])
    assert friendly.damage == 3


# GDB_870 — Eredar Skulker | MINION 2/1/3:
# Combo and Spellburst: Gain +2 Attack and Stealth.
def test_eredar_skulker_combo_buffs_and_stealths():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    base_atk = p1.card("GDB_870").atk
    # Trigger Combo: play another card first this turn.
    p1.give("CS2_231").play()
    skulker = p1.give("GDB_870")
    skulker.play()
    game.process_deaths()
    assert skulker.atk == base_atk + 2
    assert skulker.stealthed


def test_eredar_skulker_no_combo_no_buff():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    base_atk = p1.card("GDB_870").atk
    # First card of the turn -> no Combo, no buff.
    skulker = p1.give("GDB_870")
    skulker.play()
    game.process_deaths()
    assert skulker.atk == base_atk
    assert not skulker.stealthed


def test_eredar_skulker_combo_grants_stealth():
    # The Stealth half of "Combo: Gain +2 Attack and Stealth" works today.
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.give("CS2_231").play()  # arm Combo
    skulker = p1.give("GDB_870")
    assert not skulker.stealthed
    skulker.play()
    game.process_deaths()
    assert skulker.stealthed


def test_eredar_skulker_spellburst_buffs_and_stealths():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    base_atk = p1.card("GDB_870").atk
    # Summon (bypass combo / battlecry) so only Spellburst can fire.
    skulker = p1.summon("GDB_870")
    assert skulker.atk == base_atk
    assert not skulker.stealthed
    # Play a spell -> Spellburst: +2 Attack and Stealth.
    p1.give("CS2_029").play(target=p2.hero)  # Fireball
    game.process_deaths()
    assert skulker.atk == base_atk + 2
    assert skulker.stealthed


# GDB_873 — Lucky Comet | SPELL 2:
# Discover a Combo minion. The next one you play triggers its Combo twice.
def test_lucky_comet_discovers_combo_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    spell = p1.give("GDB_873")
    spell.play()
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.type == CardType.MINION
        assert cdata.tags.get(GameTag.COMBO, 0)
    chosen_id = p1.choice.cards[0]
    p1.choice.choose(p1.choice.cards[0])
    assert any(c.id == chosen_id for c in p1.hand)
    # The next Combo minion you play triggers its Combo twice -> counter armed.
    assert p1.next_combo_triggers_twice == 1


def test_lucky_comet_next_combo_minion_triggers_twice():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.next_combo_triggers_twice = 1  # as Lucky Comet would arm it
    foe = p2.summon("CS2_201")
    foe.max_health = 30
    foe.damage = 0
    p1.give(WISP).play()  # arm Combo (a card was played this turn)
    si7 = p1.give("EX1_134")  # SI:7 Agent, Combo: deal 2 damage
    si7.play(target=foe)
    # Combo fired twice -> 2 + 2 = 4 damage, and the charge is consumed.
    assert foe.damage == 4
    assert p1.next_combo_triggers_twice == 0


def test_lucky_comet_charge_unused_without_combo():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p1.next_combo_triggers_twice = 1
    foe = p2.summon("CS2_201")
    foe.max_health = 30
    foe.damage = 0
    # No card played first -> no Combo, so SI:7's Combo doesn't fire at all.
    si7 = p1.give("EX1_134")
    si7.play(target=foe)
    assert foe.damage == 0
    # The charge is not consumed (it only spends on an actual Combo trigger).
    assert p1.next_combo_triggers_twice == 1


# GDB_875 — Spacerock Collector | MINION 1/2/1:
# Battlecry: Your next Combo card costs (1) less.
def test_spacerock_collector_discounts_next_combo_card():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    collector = p1.give("GDB_875")
    collector.play()
    # A Combo card in hand now costs (1) less. Eviscerate (EX1_124) is a
    # 2-cost Rogue Combo spell.
    combo_card = p1.give("EX1_124")
    assert combo_card.data.tags.get(GameTag.COMBO, 0)
    assert combo_card.cost == 2 - 1
    # A non-Combo card is unaffected.
    plain = p1.give("CS2_029")  # Fireball, no Combo
    assert plain.cost == 4


def test_spacerock_collector_discount_consumed_after_one_combo_card():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    collector = p1.give("GDB_875")
    collector.play()
    first = p1.give("EX1_124")  # Eviscerate, 2 -> 1
    assert first.cost == 1
    first.play(target=p2.hero)
    game.process_deaths()
    # Discount consumed: a second Combo card is full price.
    second = p1.give("EX1_124")
    assert second.cost == 2


# GDB_876 — Scrounging Shipwright | MINION 2/3/2:
# Battlecry: Get a random Starship Piece from another class.
def test_scrounging_shipwright_gives_foreign_piece():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    pool = _other_class_pieces(p1)
    # Clear hand so the gained piece is identifiable.
    for c in list(p1.hand):
        c.discard()
    shipwright = p1.give("GDB_876")
    shipwright.play()
    game.process_deaths()
    # Exactly one new card in hand: a foreign Starship Piece.
    assert len(p1.hand) == 1
    gained = p1.hand[0]
    assert gained.id in pool
    assert gained.data.tags.get(GameTag.STARSHIP_PIECE, 0)
    assert gained.data.card_class != p1.hero.card_class


# GDB_881 — Pressure Points | SPELL 3:
# Deal $3 damage to a minion. Reduce the Cost of Combo cards in your hand
# by (1).
def test_pressure_points_deals_3_and_discounts_combo_in_hand():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_231")  # Wisp 1/1
    victim.max_health = 80
    victim._max_health = 80
    victim.damage = 0
    # A Combo card and a non-Combo card in hand to verify the discount scope.
    combo_card = p1.give("EX1_124")  # Eviscerate, 2-cost Combo
    plain = p1.give("CS2_029")       # Fireball, 4-cost, no Combo
    assert combo_card.cost == 2
    assert plain.cost == 4

    spell = p1.give("GDB_881")
    spell.play(target=victim)
    game.process_deaths()

    assert victim.damage == 3
    # Combo card in hand cost reduced by (1); non-Combo unchanged.
    assert combo_card.cost == 2 - 1
    assert plain.cost == 4


# SC_752 — Dark Templar (6/5/3): Stealth. Battlecry: Destroy an enemy minion.
# Play another Templar to merge into an Archon!
def test_dark_templar_destroys_and_is_stealthed():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.current_player
    p2 = p1.opponent
    victim = p2.summon("CS2_182")  # 4/5
    dt = p1.give("SC_752")
    dt.cost = 0
    dt.play(target=victim)
    assert victim.dead
    assert dt.stealthed
    assert dt.id == "SC_752"  # no merge with only one Templar


# SC_765 — High Templar (6/3/5): Battlecry: Deal 2 damage to all enemies.
# Play another Templar to merge into an Archon!
def test_high_templar_aoe():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.current_player
    p2 = p1.opponent
    e1 = p2.summon("CS2_182")  # 4/5
    e1.max_health = 80
    e1.damage = 0
    ht = p1.give("SC_765")
    ht.cost = 0
    ht.play()
    assert e1.damage == 2
    assert p2.hero.health == 30 - 2
    assert ht.id == "SC_765"  # no merge alone


# SC_752 + SC_765 — playing a second Templar while you control one merges both
# into an Archon (SC_671t1).
def test_two_templars_merge_into_archon():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.current_player
    p2 = p1.opponent
    # First Templar on board (no enemy minion needed; Dark Templar battlecry
    # only fires when played from hand — summon bypasses it).
    first = p1.summon("SC_765")  # High Templar 3/5
    assert [m.id for m in p1.field] == ["SC_765"]
    # Play the second Templar: its battlecry resolves, then both merge.
    second = p1.give("SC_765")
    second.cost = 0
    second.play()
    ids = [m.id for m in p1.field]
    assert ids == ["SC_671t1"]  # exactly one Archon, both Templars gone
    archon = p1.field[0]
    assert archon.atk == 8 and archon.max_health == 8


def test_archon_end_of_turn_damage():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.current_player
    p2 = p1.opponent
    enemy = p2.summon("CS2_182")  # 4/5
    enemy.max_health = 80
    enemy.damage = 0
    p1.summon("SC_671t1")
    game.end_turn()
    # End of your turn: 8 to enemy hero, 2 to enemy minions.
    assert p2.hero.health == 30 - 8
    assert enemy.damage == 2


# SC_761 — Blink (spell, 2): Draw a Protoss minion. Combo: It costs (2) less.
def test_blink_draws_protoss_minion_no_combo():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.current_player
    # Stock the deck with exactly one Protoss minion + some non-Protoss noise.
    proto = p1.give("SC_762")  # Mothership
    proto.zone = Zone.DECK
    noise = p1.give("CS2_182")
    noise.zone = Zone.DECK
    p1.combo = False
    blink = p1.give("SC_761")
    blink.play()
    # The Protoss minion is drawn into hand; no combo -> full cost.
    drawn = [c for c in p1.hand if c.id == "SC_762"]
    assert len(drawn) == 1
    assert drawn[0].cost == 12


def test_blink_combo_discounts_drawn_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.current_player
    proto = p1.give("SC_762")  # Mothership, base 12
    proto.zone = Zone.DECK
    p1.combo = True  # a card was already played this turn
    blink = p1.give("SC_761")
    blink.play()
    drawn = [c for c in p1.hand if c.id == "SC_762"]
    assert len(drawn) == 1
    assert drawn[0].cost == 12 - 2  # Combo: (2) less
