"""Perils in Paradise — NEUTRAL collectible cards.

Tight unit tests asserting the PRINTED behaviour of every collectible
NEUTRAL card (VAC_ prefix) in the Island Vacation set.
"""

from utils import *

from fireplace import cards as _cards


# ---------------------------------------------------------------------------
# VAC_304 — Tidepool Pupil: Battlecry: If you've cast 3 spells while holding
# this, Discover one of them.
# ---------------------------------------------------------------------------
def test_tidepool_pupil_discovers_held_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pupil = p1.give("VAC_304")
    # Cast 3 spells while holding Tidepool Pupil.
    cast_ids = []
    for _ in range(3):
        mf = p1.give(MOONFIRE)  # 0-cost spell, no target requirement issue
        mf.play(target=p1.hero)
        cast_ids.append(mf.id)
    assert getattr(pupil, "spells_cast_while_holding", 0) == 3
    pre = len(p1.hand)
    pupil.play()
    # A Discover should pop offering only the spells cast while holding.
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert cid in cast_ids
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    assert any(c.id == chosen for c in p1.hand)


def test_tidepool_pupil_no_discover_under_3_spells():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pupil = p1.give("VAC_304")
    mf = p1.give(MOONFIRE)
    mf.play(target=p1.hero)
    assert getattr(pupil, "spells_cast_while_holding", 0) == 1
    pupil.play()
    assert p1.choice is None


# ---------------------------------------------------------------------------
# VAC_321 — Incindius: Battlecry: Shuffle 5 Eruptions in your deck. End of
# turn, upgrade your Eruptions.
# VAC_321t — Eruption: Casts When Drawn. Deal $@ damage to all enemies.
# ---------------------------------------------------------------------------
def test_incindius_shuffles_5_eruptions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    inc = p1.give("VAC_321")
    inc.play()
    eruptions = [c for c in p1.deck if c.id == "VAC_321t"]
    assert len(eruptions) == 5
    # Each starts at damage level 1.
    for e in eruptions:
        assert getattr(e, "_eruption_damage", 1) == 1


def test_incindius_upgrades_eruptions_at_end_of_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    inc = p1.give("VAC_321")
    inc.play()
    game.end_turn()  # OWN_TURN_END fires for p1 -> upgrade
    eruptions = [c for c in p1.deck if c.id == "VAC_321t"]
    assert len(eruptions) == 5
    for e in eruptions:
        assert getattr(e, "_eruption_damage", 1) == 2


def test_eruption_casts_when_drawn_deals_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Enemy hero soaks the AoE; enemy minion measures exact hit.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    erupt = p1.give("VAC_321t")
    erupt.zone = Zone.DECK
    p1.draw()
    # Casts When Drawn: deals 1 (base) to all enemies.
    assert p2.hero.health == 80 - 1
    assert enemy.damage == 1


# ---------------------------------------------------------------------------
# VAC_327 — Cryopractor: Battlecry: Give a minion +3/+3 and Freeze it.
# ---------------------------------------------------------------------------
def test_cryopractor_buffs_and_freezes():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    target = p1.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    base_atk, base_health = target.atk, target.max_health
    cryo = p1.give("VAC_327")
    cryo.play(target=target)
    assert target.atk == base_atk + 3
    assert target.max_health == base_health + 3
    assert target.frozen


# ---------------------------------------------------------------------------
# VAC_406 — Sleepy Resident: Taunt. Deathrattle: ALL other minions fall asleep.
# ---------------------------------------------------------------------------
def test_sleepy_resident_taunt_and_deathrattle_freezes_all():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    res = p1.summon("VAC_406")
    assert res.taunt
    ally = p1.summon(WISP)
    enemy = p2.summon(WISP)
    res.destroy()
    game.process_deaths()
    # ALL other minions asleep (frozen), the resident itself is gone.
    assert ally.frozen
    assert enemy.frozen


# ---------------------------------------------------------------------------
# VAC_421 — Snoozin' Zookeeper: Battlecry: Summon an 8/8 Beast for your
# opponent. It attacks all of their minions.
# ---------------------------------------------------------------------------
def test_zookeeper_summons_beast_for_opponent_attacks_their_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Two enemy minions that can absorb the beast attacks.
    a = p2.summon(GOLDSHIRE_FOOTMAN)
    a.max_health = 80
    a.damage = 0
    b = p2.summon(GOLDSHIRE_FOOTMAN)
    b.max_health = 80
    b.damage = 0
    zk = p1.give("VAC_421")
    zk.play()
    beast = [m for m in p2.field if m.id == "VAC_421t"]
    assert len(beast) == 1
    assert (beast[0].atk, beast[0].max_health) == (8, 8)
    # The 8/8 attacked all of its controller's (p2's) other minions: 8 each.
    assert a.damage == 8
    assert b.damage == 8


# ---------------------------------------------------------------------------
# VAC_430 — Bloodsail Recruiter: Battlecry: Discover a Pirate.
# ---------------------------------------------------------------------------
def test_bloodsail_recruiter_discovers_pirate():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    rec = p1.give("VAC_430")
    rec.play()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert Race.PIRATE in _cards.db[cid].races
    p1.choice.choose(p1.choice.cards[0])


# ---------------------------------------------------------------------------
# VAC_432 — Resort Valet: Battlecry: Discover a card from the newest expansion.
# ---------------------------------------------------------------------------
def test_resort_valet_discovers_island_vacation_card():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    valet = p1.give("VAC_432")
    valet.play()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert _cards.db[cid].card_set == CardSet.ISLAND_VACATION
    p1.choice.choose(p1.choice.cards[0])


# ---------------------------------------------------------------------------
# VAC_438 — Travel Agent: Battlecry: Discover a location from any class.
# ---------------------------------------------------------------------------
def test_travel_agent_discovers_location():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    agent = p1.give("VAC_438")
    agent.play()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert _cards.db[cid].type == CardType.LOCATION
    p1.choice.choose(p1.choice.cards[0])


# ---------------------------------------------------------------------------
# VAC_439 — Seaside Giant: Costs (1) less for each time you've used a location
# this game.
# ---------------------------------------------------------------------------
def test_seaside_giant_cost_reduction_per_location_use():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    giant = p1.give("VAC_439")
    base = _cards.db["VAC_439"].cost  # base cost from data (9 as of build 219197)
    assert base == 9
    assert giant.cost == base  # base, no locations used yet
    # The cost_mod reads the per-game "locations used" counter.
    p1.locations_used_this_game = 2
    assert giant.cost == base - 2 * 1  # 2 uses -> -2 -> 7


# ---------------------------------------------------------------------------
# Once-over defensive test (review.csv: VAC_439 Seaside Giant + VAC_956
# Housekeeper). Edge: both read a per-game locations-used counter driven by
# REAL UseLocation events. Drive two genuine location activations and assert
# the cost drops by exactly 1 per use and Housekeeper grants exactly 3 armor
# per use.
# ---------------------------------------------------------------------------
def test_seaside_giant_and_housekeeper_track_real_location_uses():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    giant = p1.give("VAC_439")
    base = _cards.db["VAC_439"].cost  # base cost from data (9 as of build 219197)
    assert base == 9
    p1.summon("VAC_956")  # XB-931 Housekeeper
    p1.hero.armor = 0
    assert giant.cost == base
    assert getattr(p1, "locations_used_this_game", 0) == 0

    loc = p1.give("TOY_512")  # The Crystal Cove location
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0

    # First real location use.
    loc.use()
    assert p1.locations_used_this_game == 1
    assert giant.cost == base - 1  # one use -> -1 -> 8
    assert p1.hero.armor == 3    # Housekeeper: +3 armor per use

    # Second real location use (reopen by clearing cooldown).
    loc.cooldown = 0
    loc.use()
    assert p1.locations_used_this_game == 2
    assert giant.cost == base - 2  # two uses -> -2 -> 7
    assert p1.hero.armor == 6    # exactly +3 more


# ---------------------------------------------------------------------------
# VAC_440 — Customs Enforcer: Enemy cards that didn't start in their deck cost
# (2) more.
# ---------------------------------------------------------------------------
def test_customs_enforcer_taxes_non_starting_enemy_cards():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("VAC_440")
    # A card GIVEN to the opponent (not from their starting deck): +2 cost.
    given = p2.give(GOLDSHIRE_FOOTMAN)  # base 1-cost
    assert given.cost == 1 + 2


# ---------------------------------------------------------------------------
# VAC_441 — Package Dealer: After you draw a card, 50% chance to draw another.
# ---------------------------------------------------------------------------
def test_package_dealer_chains_extra_draw_on_coinflip(monkeypatch):
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("VAC_441")
    # Stock deck with two extra cards so a chained draw has fuel.
    for _ in range(3):
        c = p1.give(WISP)
        c.zone = Zone.DECK
    # Force the coinflip to always succeed -> one draw cascades to another,
    # which cascades again, until the re-entrancy guard / deck runs dry.
    real_randint = game.random.randint

    def always_one(a, b):
        if (a, b) == (0, 1):
            return 1
        return real_randint(a, b)

    monkeypatch.setattr(game.random, "randint", always_one)
    pre = len(p1.hand)
    p1.draw()  # initial draw -> Package Dealer cascade
    # Printed: "After you draw a card, 50% chance to draw another." With the
    # coinflip forced to succeed, the cascade continues until the deck is dry
    # (an empty draw fatigues and draws no card, so it can't re-trigger). The
    # initial draw plus the cascade therefore pull all 3 stocked cards.
    assert len(p1.hand) == pre + 3
    assert len(p1.deck) == 0


# ---------------------------------------------------------------------------
# VAC_442 — Lamplighter: Battlecry: Deal damage equal to turns in a row you've
# played an Elemental (Lamplighter counts as this turn's Elemental).
# ---------------------------------------------------------------------------
def test_lamplighter_deals_streak_damage():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    if game.current_player is not p1:
        game.end_turn()
    # Prior 2-turn streak, and another Elemental already played this turn so
    # the current turn is counted: 2 + 1 = 3 damage.
    p1.azerite_elemental_streak = 2
    p1.give("UNG_809t1").play()  # an Elemental, bumps elemental_played_this_turn
    assert p1.elemental_played_this_turn == 1
    lamp = p1.give("VAC_442")
    lamp.play(target=p2.hero)
    assert p2.hero.health == 80 - 3


def test_lamplighter_uses_prior_elemental_streak():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    # Build a 2-turn completed streak.
    p1.azerite_elemental_streak = 2
    lamp = p1.give("VAC_442")
    lamp.play(target=p2.hero)
    # streak 2 + this turn (Lamplighter is an elemental) = 3 damage.
    assert p2.hero.health == 80 - 3


# ---------------------------------------------------------------------------
# VAC_444 — Overplanner: Battlecry: Discover 3 cards in your deck to put on top
# in that order.
# ---------------------------------------------------------------------------
def test_overplanner_puts_chosen_on_top():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Seed deck with three distinct minions.
    ids = [GOLDSHIRE_FOOTMAN, KOBOLD_GEOMANCER, TARGET_DUMMY]
    for cid in ids:
        c = p1.give(cid)
        c.zone = Zone.DECK
    op = p1.give("VAC_444")
    op.play()
    # Three sequential discovers; auto-pick the first offered each time.
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # All three remain in the deck (re-ordered, not drawn).
    deck_ids = [c.id for c in p1.deck]
    for cid in ids:
        assert cid in deck_ids
    assert len(p1.deck) == 3


# ---------------------------------------------------------------------------
# VAC_446 — A. F. Kay: At end of turn, give all other friendly minions that
# didn't attack +2/+2.
# ---------------------------------------------------------------------------
def test_afkay_buffs_nonattacking_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    afkay = p1.summon("VAC_446")
    idle = p1.summon(GOLDSHIRE_FOOTMAN)  # 1/2, won't attack
    attacker = p1.summon("CS2_146")  # Southsea Deckhand 2/1, will attack
    attacker.turns_in_play = 1  # wake it so it can attack
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    attacker.attack(p2.hero)
    game.end_turn()  # A.F. Kay end-of-turn buff
    # Idle minion got +2/+2; the attacker did NOT.
    assert idle.atk == 1 + 2
    assert idle.max_health == 2 + 2
    assert attacker.atk == 2
    # A.F. Kay buffs "other" minions only, not itself.
    assert afkay.atk == 0


# ---------------------------------------------------------------------------
# VAC_447 — Dread Deserter: Has Charge if this didn't start in your deck.
# ---------------------------------------------------------------------------
def test_dread_deserter_charge_when_not_from_deck():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Given to hand (not in starting deck) -> Charge.
    deserter = p1.give("VAC_447")
    deserter.play()
    assert deserter.charge


# ---------------------------------------------------------------------------
# VAC_461 — Drink Server: Deathrattle: Get a random Drink spell.
# ---------------------------------------------------------------------------
def test_drink_server_deathrattle_gives_drink_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    server = p1.summon("VAC_461")
    pre = len(p1.hand)
    server.destroy()
    game.process_deaths()
    drink_ids = {"VAC_323", "VAC_338", "VAC_404", "VAC_520", "VAC_916", "VAC_951"}
    got = [c for c in p1.hand if c.id in drink_ids]
    assert len(got) == 1


# ---------------------------------------------------------------------------
# VAC_463 — Concierge: Your cards from another class cost (1) less.
# ---------------------------------------------------------------------------
def test_concierge_discounts_other_class_cards():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("VAC_463")
    # A Rogue card in a Mage hand = "another class" -> -1.
    rogue = p1.give("CS2_075")  # Sinister Strike, Rogue, base cost 1 -> 0
    assert rogue.cost == 0
    # A Mage card (same class) is NOT discounted.
    mage = p1.give(FIREBALL)  # Mage, base cost 4 -> unchanged
    assert mage.cost == 4


# ---------------------------------------------------------------------------
# VAC_521 — Bumbling Bellhop: Taunt. Battlecry: If holding a spell costing 5+,
# summon a copy of this.
# ---------------------------------------------------------------------------
def test_bumbling_bellhop_copies_with_expensive_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give(PYROBLAST)  # 10-cost spell in hand
    bellhop = p1.give("VAC_521")
    bellhop.play()
    assert bellhop.taunt
    assert len([m for m in p1.field if m.id == "VAC_521"]) == 2


def test_bumbling_bellhop_no_copy_without_expensive_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.give(MOONFIRE)  # 0-cost spell only
    bellhop = p1.give("VAC_521")
    bellhop.play()
    assert len([m for m in p1.field if m.id == "VAC_521"]) == 1


# ---------------------------------------------------------------------------
# VAC_523 — Mixologist: Battlecry: Craft a custom 1-Cost Potion.
# ---------------------------------------------------------------------------
def test_mixologist_crafts_potion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    mix = p1.give("VAC_523")
    mix.play()
    # Crafting picks two effects (Kazakus-style); resolve the choices.
    steps = 0
    while p1.choice and steps < 6:
        p1.choice.choose(p1.choice.cards[0]); steps += 1
    potions = [c for c in p1.hand if c.id == "VAC_523t"]
    assert len(potions) == 1
    assert potions[0].cost == 1


# ---------------------------------------------------------------------------
# VAC_529 — Scrapbooking Student: Battlecry: Summon a copy of a friendly
# location.
# ---------------------------------------------------------------------------
def test_scrapbooking_student_copies_friendly_location():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Place a friendly location first (The Crystal Cove location token).
    loc = p1.give("TOY_512")  # The Crystal Cove (location)
    loc.play()

    def locations():
        return [
            c for c in game.entities
            if getattr(c, "controller", None) is p1
            and c.type == CardType.LOCATION
            and c.zone == Zone.PLAY
        ]

    assert len(locations()) == 1
    student = p1.give("VAC_529")
    student.play()
    # Hearthstone allows only one location at a time: summoning a COPY of the
    # friendly location replaces the original. So a fresh TOY_512 entity is in
    # play and the original has been destroyed.
    live = locations()
    assert len(live) == 1
    assert live[0].id == "TOY_512"
    assert live[0] is not loc  # a genuine copy, not the original
    assert loc.zone == Zone.GRAVEYARD


# ---------------------------------------------------------------------------
# VAC_531 — Bayfin Bodybuilder: After a minion is summoned for your opponent
# during your turn, Silence and destroy it.
# ---------------------------------------------------------------------------
def test_bayfin_destroys_opponent_summons_on_your_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Bayfin only triggers on the CONTROLLER's turn; make it p1's turn.
    if game.current_player is not p1:
        game.end_turn()
    assert game.current_player is p1
    p1.summon("VAC_531")
    # During p1's turn, a minion is summoned for the opponent (p2).
    victim = p2.summon(GOLDSHIRE_FOOTMAN)
    game.process_deaths()
    assert victim.dead
    assert victim not in p2.field


# ---------------------------------------------------------------------------
# VAC_532 — Coconut Cannoneer: After an adjacent minion attacks, deal 1 damage
# to a random enemy.
# ---------------------------------------------------------------------------
def test_coconut_cannoneer_pings_on_adjacent_attack():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    cannon = p1.summon("VAC_532")
    adjacent = p1.summon("CS2_146")  # Southsea Deckhand 2/1, adjacent to cannon
    adjacent.turns_in_play = 1  # wake it so it can attack
    # Only enemy is the hero; adjacent attacks face for 2, cannon pings 1.
    adjacent.attack(p2.hero)
    assert p2.hero.health == 80 - 2 - 1


# ---------------------------------------------------------------------------
# VAC_702 — Marin the Manager: Battlecry: Choose a fantastic treasure. Shuffle
# the other 3 into your deck.
# ---------------------------------------------------------------------------
def test_marin_chooses_treasure_shuffles_rest():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    treasures = {"VAC_702t", "VAC_702t2", "VAC_702t3", "VAC_702t4"}
    marin = p1.give("VAC_702")
    marin.play()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert cid in treasures
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    # Resolve any further choices the chosen treasure may trigger? No — the
    # treasure is added to hand, not played. Chosen in hand, other 3 in deck.
    in_hand = [c for c in p1.hand if c.id in treasures]
    in_deck = [c for c in p1.deck if c.id in treasures]
    assert len(in_hand) == 1
    assert in_hand[0].id == chosen
    assert len(in_deck) == 3
    assert {c.id for c in in_deck} == treasures - {chosen}


# VAC_702t — Zarog's Crown: Discover a Legendary minion. Summon two copies.
def test_zarogs_crown_summons_two_copies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    crown = p1.give("VAC_702t")
    crown.play()
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    assert _cards.db[chosen].rarity == Rarity.LEGENDARY
    p1.choice.choose(chosen)
    copies = [m for m in p1.field if m.id == chosen]
    assert len(copies) == 2


# VAC_702t2 — Tolin's Goblet: Draw a card. Fill your hand with copies of it.
def test_tolins_goblet_fills_hand_with_copies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    seed = p1.give(WISP)
    seed.zone = Zone.DECK
    goblet = p1.give("VAC_702t2")
    goblet.play()
    # Drew the Wisp, then filled hand with Wisp copies up to max hand size.
    wisps = [c for c in p1.hand if c.id == WISP]
    assert len(p1.hand) == p1.max_hand_size
    assert len(wisps) == len(p1.hand)


# VAC_702t3 — Wondrous Wand: Draw 3 cards. Reduce their Costs to (0).
def test_wondrous_wand_draws_three_at_zero_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    for _ in range(3):
        c = p1.give(GOLDSHIRE_FOOTMAN)  # base 1-cost
        c.zone = Zone.DECK
    wand = p1.give("VAC_702t3")
    wand.play()
    drawn = [c for c in p1.hand if c.id == GOLDSHIRE_FOOTMAN]
    assert len(drawn) == 3
    for c in drawn:
        assert c.cost == 0


# VAC_702t4 — Golden Kobold: Battlecry: Replace your hand with Legendary
# minions.
def test_golden_kobold_replaces_hand_with_legendaries():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Clear and stock the hand with 3 known non-legendary cards.
    for c in list(p1.hand):
        c.discard()
    for _ in range(3):
        p1.give(WISP)
    kobold = p1.give("VAC_702t4")
    assert kobold.taunt
    kobold.play()
    # The 3 held cards are replaced with 3 Legendary minions; kobold not in hand.
    remaining = [c for c in p1.hand]
    assert all(c.id != WISP for c in remaining)
    assert len(remaining) == 3
    for c in remaining:
        assert c.type == CardType.MINION
        assert c.rarity == Rarity.LEGENDARY


# ---------------------------------------------------------------------------
# VAC_924 — Weapons Attendant: Battlecry: If you control another Pirate, equip a
# random weapon from your deck.
# ---------------------------------------------------------------------------
def test_weapons_attendant_equips_with_pirate():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("CS2_146")  # Southsea Deckhand (another Pirate)
    weapon = p1.give(LIGHTS_JUSTICE)  # 1/4 weapon
    weapon.zone = Zone.DECK
    attendant = p1.give("VAC_924")
    attendant.play()
    assert p1.weapon is not None
    assert p1.weapon.id == LIGHTS_JUSTICE


def test_weapons_attendant_no_equip_without_pirate():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    weapon = p1.give(LIGHTS_JUSTICE)
    weapon.zone = Zone.DECK
    attendant = p1.give("VAC_924")
    attendant.play()
    assert p1.weapon is None


# ---------------------------------------------------------------------------
# VAC_934 — Beached Whale: Taunt. Battlecry: Deal 10 damage to this minion.
# ---------------------------------------------------------------------------
def test_beached_whale_self_damage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    whale = p1.give("VAC_934")
    whale.play()
    assert whale.taunt
    assert whale.damage == 10
    assert whale.health == 20 - 10


# ---------------------------------------------------------------------------
# VAC_935 — Carry-On Grub: Battlecry: Get a 1-Cost Suitcase. Pack the top 2
# cards of your deck into it.
# VAC_935t — Carry-On Suitcase: Get {0} and {1}.
# ---------------------------------------------------------------------------
def test_carry_on_grub_packs_top_two():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Two known cards on top of deck.
    bottom = p1.give(WISP)
    bottom.zone = Zone.DECK
    top1 = p1.give(GOLDSHIRE_FOOTMAN)
    top1.zone = Zone.DECK
    top2 = p1.give(KOBOLD_GEOMANCER)
    top2.zone = Zone.DECK
    grub = p1.give("VAC_935")
    grub.play()
    suitcases = [c for c in p1.hand if c.id == "VAC_935t"]
    assert len(suitcases) == 1
    suitcase = suitcases[0]
    assert suitcase.cost == 1
    packed = [c.id for c in getattr(suitcase, "_packed_cards", [])]
    assert top1.id in packed and top2.id in packed
    assert len(packed) == 2
    # Packed cards removed from deck.
    assert top1.zone == Zone.SETASIDE
    assert top2.zone == Zone.SETASIDE


def test_carry_on_suitcase_delivers_packed_cards():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    top1 = p1.give(GOLDSHIRE_FOOTMAN)
    top1.zone = Zone.DECK
    top2 = p1.give(KOBOLD_GEOMANCER)
    top2.zone = Zone.DECK
    grub = p1.give("VAC_935")
    grub.play()
    suitcase = [c for c in p1.hand if c.id == "VAC_935t"][0]
    suitcase.play()
    hand_ids = [c.id for c in p1.hand]
    assert GOLDSHIRE_FOOTMAN in hand_ids
    assert KOBOLD_GEOMANCER in hand_ids


# ---------------------------------------------------------------------------
# VAC_936 — Octo-masseuse: Deals octuple damage to minions.
# ---------------------------------------------------------------------------
def test_octomasseuse_octuple_damage_to_minion():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    octo = p1.summon("VAC_936")  # 1/8 (cost 4, atk 1, health 8)
    octo.turns_in_play = 1  # wake it so it can attack
    assert octo.atk == 1
    target = p2.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    octo.attack(target)
    # 1 attack x8 = 8 damage to the minion.
    assert target.damage == 8


# ---------------------------------------------------------------------------
# VAC_937 — Sailboat Captain: Battlecry: Give a friendly Pirate Windfury.
# ---------------------------------------------------------------------------
def test_sailboat_captain_grants_windfury():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pirate = p1.summon("CS2_146")  # Southsea Deckhand (Pirate)
    assert not pirate.windfury
    captain = p1.give("VAC_937")
    captain.play(target=pirate)
    assert pirate.windfury


# ---------------------------------------------------------------------------
# VAC_938 — Hozen Roughhouser: Whenever another friendly Pirate attacks, give
# it +1/+1.
# ---------------------------------------------------------------------------
def test_hozen_roughhouser_buffs_attacking_pirate():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p1.summon("VAC_938")
    pirate = p1.summon("CS2_146")  # 2/1 Pirate
    pirate.turns_in_play = 1  # wake it
    base_atk, base_health = pirate.atk, pirate.max_health
    pirate.attack(p2.hero)
    assert pirate.atk == base_atk + 1
    assert pirate.max_health == base_health + 1


def test_hozen_roughhouser_ignores_nonpirate():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p1.summon("VAC_938")
    nonpirate = p1.summon("CS2_182")  # Chillwind Yeti 4/5 (not a Pirate)
    nonpirate.turns_in_play = 1  # wake it
    base_atk = nonpirate.atk
    nonpirate.attack(p2.hero)
    assert nonpirate.atk == base_atk


# ---------------------------------------------------------------------------
# VAC_946 — Terrible Chef: Battlecry: Summon a 0/2 Nerubian Egg. Deathrattle:
# Destroy it.
# ---------------------------------------------------------------------------
def test_terrible_chef_summons_and_destroys_egg():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    chef = p1.give("VAC_946")
    chef.play()
    eggs = [m for m in p1.field if m.id == "FP1_007"]
    assert len(eggs) == 1
    egg = eggs[0]
    assert (egg.atk, egg.max_health) == (0, 2)
    chef.destroy()
    game.process_deaths()
    # Deathrattle destroyed the specific egg it summoned.
    assert egg.dead
    assert egg not in p1.field


# ---------------------------------------------------------------------------
# VAC_947 — Wave Pool Thrasher: Battlecry: Give all other minions -1/-1.
# Deathrattle: Give all other minions +1/+1.
# ---------------------------------------------------------------------------
def test_wave_pool_thrasher_battlecry_and_deathrattle():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    ally = p1.summon("CS2_182")  # Chillwind Yeti 4/5
    enemy = p2.summon("CS2_182")
    thrasher = p1.give("VAC_947")
    thrasher.play()
    assert ally.atk == 3 and ally.max_health == 4
    assert enemy.atk == 3 and enemy.max_health == 4
    thrasher.destroy()
    game.process_deaths()
    # Deathrattle restores +1/+1 to all other minions.
    assert ally.atk == 4 and ally.max_health == 5
    assert enemy.atk == 4 and enemy.max_health == 5


# ---------------------------------------------------------------------------
# VAC_955 — Gorgonzormu: Battlecry: Get a 2-Cost Cheese that summons three
# 1-Cost minions. It upgrades each turn.
# VAC_955t — Delicious Cheese: Summon three random @-Cost minions.
# ---------------------------------------------------------------------------
def test_gorgonzormu_gives_cheese():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    gorg = p1.give("VAC_955")
    gorg.play()
    cheese = [c for c in p1.hand if c.id == "VAC_955t"]
    assert len(cheese) == 1
    assert cheese[0].cost == 2
    assert getattr(cheese[0], "_cheese_cost", 1) == 1


def test_delicious_cheese_summons_three_minions_at_level_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    cheese = p1.give("VAC_955t")
    cheese.play()
    summoned = [m for m in p1.field]
    assert len(summoned) == 3
    # At level 1, summons 1-Cost minions.
    for m in summoned:
        assert m.data.cost == 1


def test_delicious_cheese_upgrades_each_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    cheese = p1.give("VAC_955t")
    game.end_turn()  # Hand OWN_TURN_END upgrade
    assert getattr(cheese, "_cheese_cost", 1) == 2


# ---------------------------------------------------------------------------
# VAC_956 — XB-931 Housekeeper: After you use a location, gain 3 Armor.
# ---------------------------------------------------------------------------
def test_housekeeper_gains_armor_on_location_use():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("VAC_956")
    p1.hero.armor = 0
    loc = p1.give("TOY_512")  # The Crystal Cove location
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    assert p1.hero.armor == 3


# ---------------------------------------------------------------------------
# VAC_958 — Adaptive Amalgam: All minion types. Deathrattle: Shuffle this into
# your deck (keeps enchantments).
# ---------------------------------------------------------------------------
def test_adaptive_amalgam_all_types_and_reshuffle():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    amalgam = p1.summon("VAC_958")
    # Has all minion types (engine expands Race.ALL to the classic tribes).
    for race in (Race.MURLOC, Race.DEMON, Race.MECHANICAL, Race.BEAST,
                 Race.PIRATE, Race.DRAGON, Race.ELEMENTAL, Race.TOTEM):
        assert race in amalgam.races
    pre_deck = len(p1.deck)
    amalgam.destroy()
    game.process_deaths()
    shuffled = [c for c in p1.deck if c.id == "VAC_958"]
    assert len(shuffled) == 1
    assert len(p1.deck) == pre_deck + 1


# ---------------------------------------------------------------------------
# Once-over defensive test (review.csv: VAC_958 Adaptive Amalgam)
# Edge (a): counts as ALL minion types simultaneously (multiple distinct
# tribes at once). Edge (b): a buffed Amalgam shuffled back by its deathrattle
# RETAINS its enchantment ("It keeps any enchantments").
# ---------------------------------------------------------------------------
def test_adaptive_amalgam_satisfies_multiple_distinct_tribes():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    amalgam = p1.summon("VAC_958")
    # It is simultaneously a Murloc AND a Dragon AND a Mech (distinct tribes).
    assert Race.MURLOC in amalgam.races
    assert Race.DRAGON in amalgam.races
    assert Race.MECHANICAL in amalgam.races


def test_adaptive_amalgam_keeps_enchantment_on_reshuffle():
    from fireplace.actions import Buff

    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    amalgam = p1.summon("VAC_958")  # 1/2
    assert amalgam.atk == 1
    # Buff it +3 Attack via an enchant, then kill it.
    game.queue_actions(p1.hero, [Buff(amalgam, "CS2_087e")])  # +3 Attack
    assert amalgam.atk == 1 + 3
    amalgam.destroy()
    game.process_deaths()
    # The same minion is shuffled into the deck and KEEPS the enchant.
    shuffled = [c for c in p1.deck if c.id == "VAC_958"]
    assert len(shuffled) == 1
    copy = shuffled[0]
    assert any(b.id == "CS2_087e" for b in copy.buffs)
    assert copy.atk == 1 + 3


# ---------------------------------------------------------------------------
# VAC_959 — Griftah, Trusted Vendor: Battlecry: Discover an amazing Amulet to
# give to both players (the enemy's is a phony version).
# ---------------------------------------------------------------------------
def test_griftah_gives_real_to_you_phony_to_enemy():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    griftah = p1.give("VAC_959")
    griftah.play()
    assert p1.choice is not None
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    # The controller gets the real version (the chosen id).
    assert any(c.id == chosen for c in p1.hand)
    # The opponent gets the phony version.
    phony = {
        "VAC_959t01": "VAC_959t01t",
        "VAC_959t05": "VAC_959t05t",
        "VAC_959t06": "VAC_959t06t",
        "VAC_959t07": "VAC_959t07t",
        "VAC_959t08": "VAC_959t08t",
        "VAC_959t09": "VAC_959t09t",
        "VAC_959t10": "VAC_959t10t",
    }[chosen]
    assert any(c.id == phony for c in p2.hand)


# VAC_523 Mixologist (Tier-2 faithful): crafts a 1-Cost potion combining two
# effects from the Kazakus 1-Cost pool (Mixologist's Special, VAC_523t).
def test_mixologist_crafts_combined_potion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    p.give("VAC_523").play()
    steps = 0
    while p.choice and steps < 6:
        p.choice.choose(p.choice.cards[0]); steps += 1
    potions = [c for c in p.hand if c.id == "VAC_523t"]
    assert len(potions) == 1
    potion = potions[0]
    assert potion.cost == 1
    # Two effects combined into a real play script; placeholders filled.
    assert potion.data.scripts.play is not None
    assert "{0}" not in potion.description and "{1}" not in potion.description
