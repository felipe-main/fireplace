from utils import *


# TOY_505 — Toy Boat: After you summon a Pirate, draw a card.
def test_toy_boat_draws_on_pirate_summon():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.summon("TOY_505")
    pre = len(game.player1.hand)
    # Summon a Pirate -> should draw exactly one card.
    game.player1.summon("CS2_146")  # Southsea Deckhand (Pirate)
    assert len(game.player1.hand) == pre + 1


def test_toy_boat_no_draw_on_nonpirate():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.summon("TOY_505")
    pre = len(game.player1.hand)
    game.player1.summon("CS2_231")  # Wisp (not a Pirate)
    assert len(game.player1.hand) == pre


# TOY_510 — Dig for Treasure: Draw a minion. If it's a Pirate, get a Coin.
def test_dig_for_treasure_pirate_gives_coin():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Stack the deck with a single Pirate minion so the draw is deterministic.
    pirate = p1.give("CS2_146")  # Southsea Deckhand
    pirate.zone = Zone.DECK
    spell = p1.give("TOY_510")
    spell.play()
    assert pirate.zone == Zone.HAND
    coins = [c for c in p1.hand if c.id == "GAME_005"]
    # Drew a Pirate -> exactly one Coin granted.
    assert len(coins) == 1


def test_dig_for_treasure_is_minion_restricted():
    # "Draw a minion" is minion-restricted. With only a spell in the deck, the
    # minion selector matches nothing, so the spell is NOT drawn (stays in deck).
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    spell_in_deck = p1.give("CS2_008")  # Moonfire (a SPELL, not a minion)
    spell_in_deck.zone = Zone.DECK
    spell = p1.give("TOY_510")
    spell.play()
    # The spell remains in the deck because the draw is minion-restricted.
    assert spell_in_deck.zone == Zone.DECK


def test_dig_for_treasure_nonpirate_no_coin():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    minion = p1.give("CS2_231")  # Wisp (not a Pirate)
    minion.zone = Zone.DECK
    spell = p1.give("TOY_510")
    spell.play()
    assert minion.zone == Zone.HAND
    coins = [c for c in p1.hand if c.id == "GAME_005"]
    assert len(coins) == 0


# TOY_511 — Shoplifter Goldbeard: After you summon a Pirate, summon a copy of
# it that attacks a random enemy, then dies.
def test_goldbeard_summons_attacking_copy_that_dies():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    # Beef up the enemy hero so the copy's attack can't end the game and the
    # damage is exactly measurable.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    game.player1.summon("TOY_511")
    pre_board = len(p1.field)
    # Summon a 5/1 Pirate -> Goldbeard makes a copy that attacks then dies.
    pirate = p1.summon("CS2_146")  # Southsea Deckhand 2/1 Pirate, atk 2
    # Original pirate remains; copy is created and destroyed.
    assert pirate in p1.field
    # Board should be Goldbeard + original pirate only (copy died).
    assert len([m for m in p1.field if m.id == "CS2_146"]) == 1
    # The transient copy attacked a random enemy. Only enemy target available
    # is the hero (no enemy minions). It dealt its attack (2) to the hero.
    assert p2.hero.health == 80 - 2


# TOY_512 — The Crystal Cove (Location): The next minion you summon this turn
# has its stats set to 4/4.
def test_crystal_cove_sets_next_minion_to_4_4():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    loc = p1.give("TOY_512")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    # Bloodfen Raptor is a 3/2 -> becomes 4/4.
    raptor = p1.summon("CS2_172")
    assert raptor.atk == 4
    assert raptor.health == 4
    assert raptor.max_health == 4


def test_crystal_cove_only_affects_first_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    loc = p1.give("TOY_512")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    first = p1.summon("CS2_172")  # 3/2 -> 4/4
    second = p1.summon("CS2_172")  # unaffected
    assert (first.atk, first.health) == (4, 4)
    assert (second.atk, second.health) == (3, 2)


# TOY_514 — Thistle Tea Set: Discover a spell from another class. Get a copy.
def test_thistle_tea_set_discovers_other_class_spell():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    card = p1.give("TOY_514")
    pre = len(p1.hand)
    card.play()
    assert p1.choice is not None
    # Every offered card is a spell from a class other than Rogue (and not pure
    # Neutral). choice.cards are string ids -> look up in the card db.
    from fireplace import cards as _cards
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.type == CardType.SPELL
        classes = list(getattr(cdata, "classes", None) or [cdata.card_class])
        assert CardClass.ROGUE not in classes
        assert classes != [CardClass.NEUTRAL]
    chosen_id = p1.choice.cards[0]
    p1.choice.choose(chosen_id)
    # Got a copy of the chosen spell into hand.
    assert any(c.id == chosen_id for c in p1.hand)


# TOY_515 — Sonya Waterdancer: After you play a 1-Cost card, get a copy of it
# that costs (0).
def test_sonya_gives_zero_cost_copy_of_one_cost():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    game.player1.summon("TOY_515")
    played = p1.give("CS2_146")  # Southsea Deckhand, 1-Cost Pirate
    pre = len(p1.hand)
    played.play()
    # A copy of Southsea Deckhand should be in hand, costing 0.
    copies = [c for c in p1.hand if c.id == "CS2_146"]
    assert len(copies) == 1
    assert copies[0].cost == 0


def test_sonya_no_copy_for_two_cost():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    game.player1.summon("TOY_515")
    played = p1.give("CS2_172")  # Bloodfen Raptor, 2-Cost
    played.play()
    assert not any(c.id == "CS2_172" for c in p1.hand)


# TOY_516 — Bargain Bin Buccaneer: Rush. Combo: Summon a copy of this.
def test_buccaneer_has_rush():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    m = game.player1.summon("TOY_516")
    assert m.rush


def test_buccaneer_combo_summons_copy():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Trigger Combo: play another card first this turn.
    p1.give("CS2_231").play()  # Wisp
    pre = len(p1.field)
    bucc = p1.give("TOY_516")
    bucc.play()
    # Buccaneer itself + a summoned copy = +2 minions.
    assert len([m for m in p1.field if m.id == "TOY_516"]) == 2


def test_buccaneer_no_combo_no_copy():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    # Clear hand so playing Buccaneer is the first card this turn (no combo).
    for c in list(p1.hand):
        c.discard()
    bucc = p1.give("TOY_516")
    bucc.play()
    assert len([m for m in p1.field if m.id == "TOY_516"]) == 1


# TOY_519 — Everything Must Go!: Summon two random 4-Cost minions. Costs (1)
# less for each card you've drawn this turn.
def test_everything_must_go_summons_two_4cost():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    card = p1.give("TOY_519")
    pre = len(p1.field)
    card.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    summoned = p1.field[pre:]
    assert len(summoned) == 2
    for m in summoned:
        assert m.data.cost == 4


def test_everything_must_go_cost_reduction_per_draw():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    card = p1.give("TOY_519")
    base = p1.card("TOY_519").cost
    assert card.cost == base
    # Draw 3 cards this turn -> cost reduced by 3.
    for _ in range(3):
        p1.give("CS2_231").zone = Zone.DECK
    p1.draw(3)
    assert p1.cards_drawn_this_turn == 3
    assert card.cost == base - 3


# TOY_521 — Sandbox Scoundrel: Battlecry: Your next card this turn costs (3)
# less.
def test_sandbox_scoundrel_next_card_cost_reduction():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    scoundrel = p1.give("TOY_521")
    scoundrel.play()
    nxt = p1.give("CS2_172")  # Bloodfen Raptor, base 2-Cost -> 2-3 clamped to 0
    assert nxt.cost == 0


def test_sandbox_scoundrel_reduction_consumed_after_one_card():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    scoundrel = p1.give("TOY_521")
    scoundrel.play()
    first = p1.give("CS2_172")  # gets the discount -> 0
    assert first.cost == 0
    first.play()
    # After playing one card, discount expires; next card at full cost.
    second = p1.give("CS2_172")
    assert second.cost == 2


# TOY_521t1 — Sandbox Scoundrel (Mini token): same battlecry.
def test_sandbox_scoundrel_mini_cost_reduction():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    mini = p1.give("TOY_521t1")
    mini.play()
    nxt = p1.give("CS2_172")  # base 2 -> 0
    assert nxt.cost == 0


# TOY_522 — Watercannon (Weapon): After your hero attacks, summon a 1/1 Pirate
# that attacks a random enemy.
def test_watercannon_summons_pirate_that_attacks_on_hero_attack():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    weapon = p1.give("TOY_522")
    weapon.play()
    assert p1.hero.atk == 3
    pre_board = len(p1.field)
    # Hero attacks the enemy hero. Hero deals 3; weapon spawns a 1/1 Waterslider
    # that then attacks the (only) enemy = hero for 1 more.
    p1.hero.attack(p2.hero)
    # Hero attack (3) + Waterslider attack (1) = 4 damage to enemy hero.
    assert p2.hero.health == 80 - 4
    # The Waterslider survived (took no return damage from a face attack) and
    # remains on board.
    sliders = [m for m in p1.field if m.id == "TOY_522t"]
    assert len(sliders) == 1
    assert (sliders[0].atk, sliders[0].health) == (1, 1)


def test_waterslider_token_is_pirate():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    m = game.player1.summon("TOY_522t")
    assert Race.PIRATE in m.races
    assert (m.atk, m.health) == (1, 1)
