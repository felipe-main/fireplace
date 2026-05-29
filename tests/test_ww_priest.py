from utils import *


# TOY_380 — Clay Matriarch: Miniaturize. Taunt. Deathrattle: Summon a 4/4 Whelp with Elusive.
def test_clay_matriarch_deathrattle():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    matriarch = game.player1.summon("TOY_380")
    assert matriarch.taunt
    assert matriarch.atk == 3 and matriarch.max_health == 7
    matriarch.destroy()
    game.process_deaths()
    whelps = [m for m in game.player1.field if m.id == "TOY_380t2"]
    assert len(whelps) == 1
    whelp = whelps[0]
    assert whelp.atk == 4 and whelp.max_health == 4
    # Elusive — cannot be targeted by spells / hero powers
    assert whelp.cant_be_targeted_by_abilities
    assert whelp.cant_be_targeted_by_hero_powers


# TOY_380t — Mini Clay Matriarch (1/1/1) deathrattle summons the 4/4 Whelp
def test_clay_matriarch_mini_deathrattle():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    mini = game.player1.summon("TOY_380t")
    assert mini.atk == 1 and mini.max_health == 1
    assert mini.taunt
    mini.destroy()
    game.process_deaths()
    whelps = [m for m in game.player1.field if m.id == "TOY_380t2"]
    assert len(whelps) == 1


# TOY_381 — Papercraft Angel: Your Hero Power costs (0).
def test_papercraft_angel():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    hp = game.player1.hero.power
    base_cost = hp.cost
    assert base_cost == 2
    game.player1.summon("TOY_381")
    assert hp.cost == 0
    # Aura is ongoing — removing the angel restores cost
    game.player1.field[0].destroy()
    game.process_deaths()
    assert hp.cost == 2


# TOY_382 — Careless Crafter: Deathrattle: Get two 0-Cost Bandages that restore 3 Health.
def test_careless_crafter_deathrattle():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    pre_hand = len(game.player1.hand)
    crafter = game.player1.summon("TOY_382")
    crafter.destroy()
    game.process_deaths()
    bandages = [c for c in game.player1.hand if c.id == "TOY_382t"]
    assert len(bandages) == 2
    assert all(b.cost == 0 for b in bandages)


# TOY_382t — Bandage: Restore #3 Health.
def test_bandage_heals_3():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.hero.max_health = 30
    game.player1.hero.damage = 10
    bandage = game.player1.give("TOY_382t")
    bandage.play(target=game.player1.hero)
    assert game.player1.hero.damage == 7


# TOY_383 — Raza the Resealed: Battlecry: For the rest of the game, your Hero
# Power refreshes whenever you play a card.
def test_raza_resealed_refreshes_hero_power():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    raza = game.player1.give("TOY_383")
    raza.play()
    # Use the hero power so it becomes exhausted (Lesser Heal needs a target)
    game.player1.hero.power.use(target=game.player1.hero)
    assert game.player1.hero.power.exhausted
    # Playing another card should refresh (un-exhaust) the hero power
    wisp = game.player1.give(WISP)
    wisp.play()
    assert not game.player1.hero.power.exhausted


# TOY_384 — Purifying Power: Silence all friendly minions, then give them +1/+2.
def test_purifying_power():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # A friendly minion with a buff that will be silenced away.
    footman = game.player1.summon(GOLDSHIRE_FOOTMAN)  # 1/2 Taunt
    assert footman.taunt
    base_atk, base_health = footman.atk, footman.max_health
    power = game.player1.give("TOY_384")
    power.play()
    # Silence removes Taunt, then +1/+2 applied
    assert not footman.taunt
    assert footman.atk == base_atk + 1
    assert footman.max_health == base_health + 2


# TOY_385 — Timewinder Zarimi: Battlecry: Once per game, if you've summoned 5
# other Dragons, take an extra turn.
def test_zarimi_extra_turn_after_5_dragons():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    zarimi = game.player1.give("TOY_385")
    # Summon 5 dragons while Zarimi is in hand (bumps the per-card counter).
    for _ in range(5):
        game.player1.summon("TOY_380t2")  # Clay Whelp is a Dragon
    assert getattr(zarimi, "_dragons_summoned", 0) == 5
    pre_extra = list(game.next_players)
    zarimi.play()
    assert game.player1._zarimi_used is True
    assert game.next_players == pre_extra + [game.player1]


def test_zarimi_no_extra_turn_under_5():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    zarimi = game.player1.give("TOY_385")
    for _ in range(4):
        game.player1.summon("TOY_380t2")
    assert getattr(zarimi, "_dragons_summoned", 0) == 4
    zarimi.play()
    assert getattr(game.player1, "_zarimi_used", False) is False
    assert game.player1 not in game.next_players


# TOY_387 — Scale Replica: Draw your lowest and highest Cost Dragon.
def test_scale_replica_draws_lowest_and_highest_dragon():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    # Plant three dragons of distinct cost; only the lowest (1) and highest
    # (6) should be drawn, the middle one (2) stays in the deck.
    cheap = p.card("BRM_004")  # Twilight Whelp, cost 1 (Dragon)
    cheap.zone = Zone.DECK
    middle = p.card("NEW1_023")  # Faerie Dragon, cost 2 (Dragon)
    middle.zone = Zone.DECK
    pricey = p.card("AT_008")  # Coldarra Drake, cost 6 (Dragon)
    pricey.zone = Zone.DECK
    replica = p.give("TOY_387")
    replica.play()
    hand_ids = [c.id for c in p.hand]
    assert "BRM_004" in hand_ids   # lowest cost dragon drawn
    assert "AT_008" in hand_ids    # highest cost dragon drawn
    # The middle-cost dragon was NOT drawn.
    assert "NEW1_023" not in hand_ids
    assert any(c.id == "NEW1_023" for c in p.deck)


# TOY_388 — Chalk Artist: Battlecry: Draw a minion. Transform it into a random
# Legendary one (keeping its original stats and Cost).
def test_chalk_artist_transforms_drawn_minion():
    game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    # Seed the deck with exactly one minion of known stats/cost.
    # Target Dummy: 0-cost, 0 atk, 2 health.
    seed = p.card("GVG_093")
    seed.zone = Zone.DECK
    artist = p.give("TOY_388")
    artist.play()
    # The drawn minion is transformed into a random Legendary minion.
    morphed = [c for c in p.hand if c.id != "TOY_388"]
    assert len(morphed) == 1
    m = morphed[0]
    assert m.type == CardType.MINION
    assert m.rarity == Rarity.LEGENDARY
    # "keeping its original stats and Cost": the drawn Target Dummy (0-cost 0/2)
    # transforms into a random Legendary that retains cost 0, atk 0, health 2.
    assert m.id != "GVG_093"  # it really transformed into something else
    assert m.cost == 0
    assert m.atk == 0
    assert m.health == 2
    assert m.max_health == 2
    # The chalk enchants are attached to the morphed card (not the discarded
    # original): stats persist + the cost override is present while in hand.
    assert any(b.id == "TOY_388e2" for b in m.buffs)
    assert any(b.id == "TOY_388e3" for b in m.buffs)
    # The Legendary's own natural stats differ from the preserved 0/0/2 (proves
    # the stats are actually being overridden, not coincidentally equal).
    natural = game.player1.card(m.id)
    assert not (natural.cost == 0 and natural.atk == 0 and natural.health == 2)


# TOY_714 — Fly Off the Shelves: Deal $1 damage to all enemy minions. Repeat
# for each Dragon you're holding.
def test_fly_off_the_shelves_base():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    enemy = game.player2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    enemy.max_health = 80
    enemy.damage = 0
    spell = game.player1.give("TOY_714")
    # No dragons in hand -> 1 hit of 1 damage
    spell.play()
    assert enemy.damage == 1


def test_fly_off_the_shelves_with_dragons():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    enemy = game.player2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    # Hold 3 dragons -> 1 + 3 = 4 hits of 1 damage each.
    for _ in range(3):
        game.player1.give("TOY_380t2")  # Clay Whelp, a Dragon
    spell = game.player1.give("TOY_714")
    spell.play()
    assert enemy.damage == 4


# TOY_879 — Repackage: Stuff all minions into a 2-Cost Box, then shuffle it
# into the opponent's deck.  TOY_879t — Repackaged Box: Add the resealed
# minions to your hand.
def test_repackage_shuffles_box_into_opponent_deck():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    a = p1.summon(GOLDSHIRE_FOOTMAN)
    b = p2.summon(WISP)
    pre_deck = len(p2.deck)
    spell = p1.give("TOY_879")
    spell.play()
    # All minions removed from the board.
    assert len(p1.field) == 0
    assert len(p2.field) == 0
    # A 2-cost box was shuffled into the opponent's (p2) deck.
    boxes = [c for c in p2.deck if c.id == "TOY_879t"]
    assert len(boxes) == 1
    assert boxes[0].cost == 2
    assert len(p2.deck) == pre_deck + 1


def test_repackaged_box_returns_minions_to_owner_hand():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p1.summon(GOLDSHIRE_FOOTMAN)
    p2.summon(WISP)
    spell = p1.give("TOY_879")
    spell.play()
    box = [c for c in p2.deck if c.id == "TOY_879t"][0]
    # p2 plays the box from hand (must be p2's turn for is_playable).
    game.end_turn()
    box.zone = Zone.HAND
    box.play()
    # The box owner (p2) gets the resealed minions added to their hand.
    hand_ids = [c.id for c in p2.hand]
    assert GOLDSHIRE_FOOTMAN in hand_ids
    assert WISP in hand_ids


# ---------------------------------------------------------------------------
# TOY_385 Timewinder Zarimi — cosmetic countdown placeholder
# ---------------------------------------------------------------------------
def test_timewinder_zarimi_renders_countdown_and_ready():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    z = game.player1.give("TOY_385")
    # Below threshold: render the "({0} left!)" tail with the remaining count.
    assert "@" not in z.description
    assert "5 left" in z.description
    assert "Ready" not in z.description
    # At/above threshold: render the "(Ready!)" tail instead.
    z._dragons_summoned = 5
    assert "Ready!" in z.description
    assert "left" not in z.description
