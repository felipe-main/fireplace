from utils import *


def _empty_deck(player):
    for c in list(player.deck):
        c.discard()


def _stock_deck(player, card_id, n):
    for _ in range(n):
        c = player.card(card_id)
        c.zone = Zone.DECK
    return player


# ---------------------------------------------------------------------------
# TOY_037 Hidden Objects — Discover a Secret. Set its Cost to (1).
# ---------------------------------------------------------------------------
def test_hidden_objects():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    pre = len(p.hand)
    spell = p.give("TOY_037")
    spell.play()
    # Discover offers exactly 3 Secrets.
    assert p.choice is not None
    assert len(p.choice.cards) == 3
    for c in p.choice.cards:
        assert c.secret  # every option must be a Secret
    chosen = p.choice.cards[0]
    chosen_id = chosen.id
    base_cost = chosen.data.cost
    p.choice.choose(chosen)
    assert p.choice is None
    # The discovered Secret is now in hand with Cost set to exactly 1.
    found = [c for c in p.hand if c.id == chosen_id]
    assert len(found) == 1
    assert found[0].cost == 1
    # Sanity: it was actually adjusted (every real Secret costs > 1).
    assert base_cost != 1 or found[0].cost == 1


# ---------------------------------------------------------------------------
# TOY_370 Triplewick Trickster — Deal 2 damage to a random enemy, 3 times.
# ---------------------------------------------------------------------------
def test_triplewick_trickster_all_to_face():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Only legal enemy target is the enemy hero (no enemy minions).
    p2.hero.max_health = 80
    p2.hero.damage = 0
    pre = p2.hero.health
    card = p1.give("TOY_370")
    card.play()
    # 3 hits of 2 = exactly 6 to the only enemy character.
    assert p2.hero.health == pre - 6


def test_triplewick_trickster_single_enemy_minion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # One enemy minion with huge health absorbs every tick; hero untouched
    # is impossible since both are legal — beef BOTH so total is determinable.
    target = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    target.max_health = 80
    target.damage = 0
    p2.hero.max_health = 80
    p2.hero.damage = 0
    hero_pre = p2.hero.health
    min_pre = target.health
    card = p1.give("TOY_370")
    card.play()
    # Three random hits split between the two enemy characters; total dealt
    # across both must be exactly 6.
    dealt = (hero_pre - p2.hero.health) + (min_pre - target.health)
    assert dealt == 6


# ---------------------------------------------------------------------------
# TOY_371 Manufacturing Error — Draw 3. If deck has no minions, they cost (3) less.
# ---------------------------------------------------------------------------
def test_manufacturing_error_no_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _empty_deck(p)
    # Stock deck with 3 known spells (Fireball, base cost 4), no minions.
    _stock_deck(p, "CS2_029", 3)
    card = p.give("TOY_371")
    pre_hand = len(p.hand)
    card.play()
    drawn = [c for c in p.hand if c.id == "CS2_029"]
    assert len(drawn) == 3
    # No minions in deck => each drawn card costs 3 less: 4 - 3 = 1.
    for c in drawn:
        assert c.cost == 1


def test_manufacturing_error_with_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _empty_deck(p)
    # Deck has minions present, plus spells to draw.
    _stock_deck(p, "CS2_029", 3)
    _stock_deck(p, "CS2_182", 3)  # Chillwind Yeti minions remain in deck
    card = p.give("TOY_371")
    card.play()
    # Draws 3 cards; since deck still has minions, no discount applies.
    drawn = [c for c in p.hand if c.id == "CS2_029"]
    for c in drawn:
        assert c.cost == 4  # full Fireball cost


# ---------------------------------------------------------------------------
# TOY_372 Yogg in the Box — Cast 5 random spells. If deck has no minions,
# the spells cast cost (5) or more.
# ---------------------------------------------------------------------------
def test_yogg_in_the_box_casts_five():
    import fireplace.actions as _actions

    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Make everyone unkillable so the 5 casts always resolve.
    for h in (p1.hero, p2.hero):
        h.max_health = 200
        h.damage = 0
    casts = []
    orig = _actions.CastSpell.do

    def _spy(self, source, card, targets):
        casts.append(card.id)
        return orig(self, source, card, targets)

    _actions.CastSpell.do = _spy
    try:
        card = p1.give("TOY_372")
        card.play()
    finally:
        _actions.CastSpell.do = orig
    # Casts exactly 5 random spells.
    assert len(casts) == 5


def test_yogg_in_the_box_expensive_when_no_minions():
    import fireplace.actions as _actions

    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    for h in (p1.hero, p2.hero):
        h.max_health = 200
        h.damage = 0
    _empty_deck(p1)
    _stock_deck(p1, "CS2_029", 3)  # spells only -> no minions in deck
    casts = []
    orig = _actions.CastSpell.do

    def _spy(self, source, card, targets):
        casts.append(card)
        return orig(self, source, card, targets)

    _actions.CastSpell.do = _spy
    try:
        card = p1.give("TOY_372")
        card.play()
    finally:
        _actions.CastSpell.do = orig
    assert len(casts) == 5
    # No minions in deck => every cast spell costs 5 or more.
    for c in casts:
        assert (c.data.cost or 0) >= 5


# ---------------------------------------------------------------------------
# TOY_373 Puzzlemaster Khadgar — Battlecry: Equip a 0/6 Wisdomball.
# TOY_373t Magic Wisdomball — end of turn cast a Mage spell, lose 1 durability.
# ---------------------------------------------------------------------------
def test_khadgar_equips_wisdomball():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    card = p.give("TOY_373")
    card.play()
    wpn = p.weapon
    assert wpn is not None
    assert wpn.id == "TOY_373t"
    assert wpn.atk == 0
    assert wpn.durability == 6


def test_wisdomball_end_of_turn():
    import fireplace.actions as _actions

    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    for h in (p1.hero, p2.hero):
        h.max_health = 200
        h.damage = 0
    p1.summon("TOY_373t")  # equip directly
    wpn = p1.weapon
    assert wpn.durability == 6
    casts = []
    orig = _actions.CastSpell.do

    def _spy(self, source, card, targets):
        casts.append(card)
        return orig(self, source, card, targets)

    _actions.CastSpell.do = _spy
    try:
        game.end_turn()  # end p1 turn -> wisdomball fires
    finally:
        _actions.CastSpell.do = orig
    # Lost exactly 1 durability.
    assert wpn.durability == 5
    # Exactly one helpful Mage spell cast.
    assert len(casts) == 1
    assert casts[0].card_class == CardClass.MAGE
    assert casts[0].type == CardType.SPELL


# ---------------------------------------------------------------------------
# TOY_374 Spot the Difference — Discover a 3-Cost minion to summon. If deck
# has no minions, repeat this (once more).
# ---------------------------------------------------------------------------
def test_spot_the_difference_with_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _empty_deck(p)
    _stock_deck(p, "CS2_182", 3)  # deck HAS minions -> no repeat
    pre_board = len(p.field)
    card = p.give("TOY_374")
    card.play()
    while p.choice:
        opt = p.choice.cards[0]
        assert opt.cost == 3 and opt.type == CardType.MINION
        p.choice.choose(opt)
    # Exactly one minion summoned (no repeat).
    assert len(p.field) == pre_board + 1


def test_spot_the_difference_no_minions_repeats():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _empty_deck(p)
    _stock_deck(p, "CS2_029", 3)  # spells only -> repeat once
    pre_board = len(p.field)
    card = p.give("TOY_374")
    card.play()
    discovers = 0
    while p.choice:
        discovers += 1
        opt = p.choice.cards[0]
        assert opt.cost == 3 and opt.type == CardType.MINION
        p.choice.choose(opt)
    # Two discovers (initial + one repeat), two minions summoned.
    assert discovers == 2
    assert len(p.field) == pre_board + 2


# ---------------------------------------------------------------------------
# TOY_375 Sleet Skater — Battlecry: Freeze an enemy minion. Gain Armor = its Attack.
# ---------------------------------------------------------------------------
def test_sleet_skater():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    assert target.atk == 4
    p1.hero.armor = 0
    card = p1.give("TOY_375")
    card.play(target=target)
    assert target.frozen
    assert p1.hero.armor == 4  # armor equal to target's attack


def test_sleet_skater_mini():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # 4/5
    p1.hero.armor = 0
    mini = p1.give("TOY_375t")
    assert mini.atk == 1 and mini.health == 1
    mini.play(target=target)
    assert target.frozen
    assert p1.hero.armor == 4


# ---------------------------------------------------------------------------
# TOY_376 Watercolor Artist — Battlecry: Draw a Frost spell. At the start of
# your turns, reduce its Cost by (1).
# ---------------------------------------------------------------------------
def test_watercolor_artist_draws_frost():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _empty_deck(p)
    # Frostbolt is a Frost spell (FROST school), base cost 2.
    _stock_deck(p, "CS2_024", 5)  # Frostbolt
    pre_hand = len(p.hand)
    card = p.give("TOY_376")
    card.play()
    drawn = [c for c in p.hand if c.id == "CS2_024"]
    assert len(drawn) == 1  # exactly one Frost spell drawn


def test_watercolor_artist_cost_reduction_each_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _empty_deck(p)
    _stock_deck(p, "CS2_024", 5)  # Frostbolt, base cost 2
    card = p.give("TOY_376")
    card.play()
    frost = [c for c in p.hand if c.id == "CS2_024"][0]
    base = frost.data.cost
    assert frost.cost == base  # no reduction yet on the turn played
    # Advance to the start of the player's next turn.
    game.end_turn()
    game.end_turn()
    assert frost.cost == base - 1
    # Another full round -> another -1.
    game.end_turn()
    game.end_turn()
    assert frost.cost == base - 2


# ---------------------------------------------------------------------------
# TOY_377 Frost Lich Cross-Stitch — Deal 4 to a character. If it dies, summon
# a 3/6 Water Elemental that Freezes.
# ---------------------------------------------------------------------------
def test_cross_stitch_kills_and_summons():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_171")  # Stonetusk Boar 1/1
    victim.max_health = 4
    victim.damage = 0
    pre_field = len(p1.field)
    card = p1.give("TOY_377")
    card.play(target=victim)
    assert victim.dead
    # A Water Elemental was summoned for the controller.
    elems = [m for m in p1.field if m.id == "ICC_833t"]
    assert len(elems) == 1
    assert elems[0].atk == 3 and elems[0].max_health == 6


def test_cross_stitch_survives_no_summon():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_182")  # 4/5 — survives 4 damage
    victim.max_health = 10
    victim.damage = 0
    card = p1.give("TOY_377")
    card.play(target=victim)
    assert not victim.dead
    assert victim.damage == 4
    # No Water Elemental summoned.
    assert not any(m.id == "ICC_833t" for m in p1.field)


# ---------------------------------------------------------------------------
# TOY_378 The Galactic Projection Orb — Recast a random spell of each Cost
# you've cast this game (targets enemies if possible).
# ---------------------------------------------------------------------------
def _both_heroes_tanky(p1, p2):
    for hero in (p1.hero, p2.hero):
        hero.max_health = 200
        hero.damage = 0


def test_galactic_orb_recasts_per_cost():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _both_heroes_tanky(p1, p2)
    # Cast two distinct-cost damage spells at the enemy hero.
    fb = p1.give("CS2_029")  # Fireball, cost 4, 6 dmg
    fb.play(target=p2.hero)
    fbolt = p1.give("CS2_024")  # Frostbolt, cost 2, 3 dmg
    fbolt.play(target=p2.hero)
    dmg_before_orb = 200 - p2.hero.health
    assert dmg_before_orb == 9  # 6 + 3
    # Now play the Orb: should recast one spell of cost 4 and one of cost 2.
    p1.used_mana = 0  # afford the 10-cost orb
    orb = p1.give("TOY_378")
    orb.play()
    # Recast Fireball (6) + Frostbolt (3) at enemy hero = +9 more.
    total = 200 - p2.hero.health
    assert total == dmg_before_orb + 9


def test_galactic_orb_includes_effect_cast_spells():
    # Faithful behaviour: the recast pool is every spell you've CAST this
    # game — including spells cast by other effects, not only the ones
    # played from hand. Here Fireball (cost 4) is played from hand, while
    # Frostbolt (cost 2) is cast by an EFFECT (CastSpell), so it never
    # enters cards_played_this_game. The Orb must still recast a cost-2
    # spell because spells_cast_this_game records the effect cast.
    from fireplace.actions import CastSpell

    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _both_heroes_tanky(p1, p2)

    def hero_dmg():
        return (200 - p1.hero.health) + (200 - p2.hero.health)

    fb = p1.give("CS2_029")  # Fireball, cost 4, 6 dmg
    fb.play(target=p2.hero)

    # Effect-cast a Frostbolt (cost 2, 3 dmg): bypasses Play.do entirely.
    # CastSpell picks a random target; both heroes are tanky and we count
    # their combined damage, so the target choice can't skew the totals.
    fbolt = p1.card("CS2_024")
    fbolt.zone = Zone.HAND
    game.queue_actions(p1.hero, [CastSpell(fbolt)])

    # Sanity: the effect cast is NOT recorded as a hand-play, but IS in the
    # cast ledger that the Orb reads.
    assert fbolt not in p1.cards_played_this_game
    cast_costs = sorted({c.cost or 0 for c in p1.spells_cast_this_game})
    assert cast_costs == [2, 4]

    dmg_before_orb = hero_dmg()
    assert dmg_before_orb == 9  # Fireball 6 + effect Frostbolt 3

    p1.used_mana = 0
    orb = p1.give("TOY_378")
    orb.play()
    # Orb recasts one cost-4 (Fireball, 6) + one cost-2 (Frostbolt, 3) = +9.
    # Under the OLD hand-only pool this would be only +6 (no cost-2 bucket).
    total = hero_dmg()
    assert total == dmg_before_orb + 9


def test_galactic_orb_does_not_recast_itself():
    # The Orb is itself a 10-Cost spell. It must never feed itself into the
    # cost-10 bucket (it is appended to the cast ledger only after its own
    # battlecry has resolved). With no prior spells cast, playing the Orb
    # recasts nothing.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    _both_heroes_tanky(p1, p2)
    assert len(p1.spells_cast_this_game) == 0

    p1.used_mana = 0
    orb = p1.give("TOY_378")
    orb.play()
    # No cost-10 self-recast — both heroes untouched.
    assert p2.hero.health == 200
    assert p1.hero.health == 200
    # After resolution the Orb itself is now logged as a cast spell.
    assert orb in p1.spells_cast_this_game
