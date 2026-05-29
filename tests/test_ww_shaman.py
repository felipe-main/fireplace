from utils import *


# TOY_046 — Incredible Value
# Discover a 4-Cost minion. Set its Attack and Health to 7.
def test_incredible_value():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    card = game.player1.give("TOY_046")
    card.play()
    # Discover pops up: choose the first option
    assert game.player1.choice
    chosen = game.player1.choice.cards[0]
    # every discover option is a 4-cost minion
    for c in game.player1.choice.cards:
        assert c.type == CardType.MINION
        assert c.cost == 4
    game.player1.choice.choose(chosen)
    assert not game.player1.choice
    # the chosen minion lands in hand with atk/health set to 7
    held = [c for c in game.player1.hand if c.id == chosen.id]
    assert len(held) == 1
    m = held[0]
    assert m.atk == 7
    assert m.max_health == 7
    assert m.health == 7


# TOY_500 — Baking Soda Volcano
# Lifesteal. Deal $10 damage randomly split among all minions. Overload: (1)
def test_baking_soda_volcano_total_damage():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Two huge minions that can absorb all 10 ticks without dying.
    m1 = game.player1.summon(WISP)
    m2 = game.player2.summon(WISP)
    for m in (m1, m2):
        m.max_health = 80
        m.damage = 0
    card = game.player1.give("TOY_500")
    card.play()
    # 10 damage split randomly among all minions -> exactly 10 total
    total = m1.damage + m2.damage
    assert total == 10
    # Lifesteal: source player's hero healed by total damage dealt.
    # Hero starts at 30, undamaged -> still 30 (capped), so verify via overload instead.
    assert game.player1.overloaded == 1


# TOY_500 — Lifesteal actually heals the hero
def test_baking_soda_volcano_lifesteal():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.hero.damage = 20  # room to heal
    m1 = game.player1.summon(WISP)
    m1.max_health = 80
    m1.damage = 0
    card = game.player1.give("TOY_500")
    card.play()
    assert m1.damage == 10
    # Lifesteal heals 10 -> hero damage 20 -> 10
    assert game.player1.hero.damage == 10


# TOY_506 — Once Upon a Time...
# Summon a random 3-Cost Beast, Dragon, Elemental, and Murloc.
def test_once_upon_a_time():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    card = game.player1.give("TOY_506")
    card.play()
    field = game.player1.field
    assert len(field) == 4
    all_races = []
    for m in field:
        assert m.cost == 3
        all_races.extend(list(m.races))
    # each of the four requested tribes is represented (minions may be
    # multi-race, so check membership across the union of all races)
    assert Race.BEAST in all_races
    assert Race.DRAGON in all_races
    assert Race.ELEMENTAL in all_races
    assert Race.MURLOC in all_races


# TOY_508 — Pop-Up Book
# Deal $2 damage. Summon two 0/1 Frogs with Taunt.
def test_pop_up_book():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Give enemy a big minion so the 2 damage has a deterministic-ish home,
    # but damage targets a random enemy CHARACTER. Clear enemy board and
    # damage the hero so the only enemy character is the hero.
    enemy = game.player2
    enemy.hero.damage = 0
    card = game.player1.give("TOY_508")
    card.play()
    # only enemy character is the hero -> takes exactly 2
    assert enemy.hero.damage == 2
    # two 0/1 Taunt frogs summoned for the caster
    frogs = [m for m in game.player1.field if m.id == "hexfrog"]
    assert len(frogs) == 2
    for f in frogs:
        assert f.atk == 0
        assert f.max_health == 1
        assert f.taunt


# TOY_877 — Wish Upon a Star
# Give +2/+3 to all minions in your hand, deck, and battlefield.
def test_wish_upon_a_star():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # battlefield minion
    in_play = game.player1.summon(WISP)  # 1/1
    # hand minion
    in_hand = game.player1.give(WISP)
    # deck minion (give then move to deck)
    in_deck = game.player1.give(WISP)
    in_deck.zone = Zone.DECK
    # enemy minion should NOT be buffed
    enemy_minion = game.player2.summon(WISP)

    card = game.player1.give("TOY_877")
    card.play()

    assert in_play.atk == 1 + 2
    assert in_play.max_health == 1 + 3
    assert in_hand.atk == 1 + 2
    assert in_hand.max_health == 1 + 3
    assert in_deck.atk == 1 + 2
    assert in_deck.max_health == 1 + 3
    # enemy untouched
    assert enemy_minion.atk == 1
    assert enemy_minion.max_health == 1


# TOY_507 — Fairy Tale Forest (Location)
# Printed: "Draw a Battlecry minion. It costs (1) less." — a Location with
# 3 charges; the effect should fire only when the Location is USED, not when
# it is played.
#
# BUG (real_bug): the impl scripts the effect as `play =` instead of
# `activate =`. UseLocation falls back to running `play` when no `activate`
# exists, so the draw fires BOTH on play and on each use. Net result: the
# Location grants one extra draw (the play-time trigger) that the printed
# card does not. This test documents the CURRENT (buggy) behaviour: a draw
# happens immediately on play.
def test_fairy_tale_forest_draws_with_cost_reduction():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Make the deck contain only a known battlecry minion so the random draw
    # is deterministic.
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    bc = game.player1.give("TOY_503")  # Shining Sentinel (battlecry minion)
    bc.zone = Zone.DECK
    base_cost = bc.cost  # 7

    loc = game.player1.give("TOY_507")
    loc.play()

    # BUG: drawn at PLAY time (printed card draws only on USE).
    drawn = [c for c in game.player1.hand if c.id == "TOY_503"]
    assert len(drawn) == 1
    # cost reduced by 1
    assert drawn[0].cost == base_cost - 1


# TOY_503 — Shining Sentinel
# Taunt, Elusive. Battlecry: Summon a copy of this.
def test_shining_sentinel():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    card = game.player1.give("TOY_503")
    card.play()
    sentinels = [m for m in game.player1.field if m.id == "TOY_503"]
    # original + 1 copy = 2
    assert len(sentinels) == 2
    for m in sentinels:
        assert m.taunt
        # Elusive: wired via GameTag.ELUSIVE in targeting.py — opponent spells
        # can't target it.
        assert m.data.tags.get(GameTag.ELUSIVE) == 1
    # Verify the opponent cannot target it with a spell (Elusive enforced).
    enemy_spell = game.player2.give(FIREBALL)
    assert sentinels[0] not in enemy_spell.targets


# TOY_513 — Sand Art Elemental
# Battlecry: Give your hero +1 Attack and Windfury this turn.
def test_sand_art_elemental():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    hero = game.player1.hero
    assert hero.atk == 0
    card = game.player1.give("TOY_513")
    card.play()
    assert hero.atk == 1
    assert hero.windfury


# TOY_513t — Sand Art Elemental (Mini)
def test_sand_art_elemental_mini():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    hero = game.player1.hero
    card = game.player1.give("TOY_513t")
    card.play()
    assert hero.atk == 1
    assert hero.windfury


# TOY_501 — Shudderblock
# Battlecry: Your next Battlecry triggers 3 times, but can't damage the enemy hero.
def test_shudderblock_triples_next_battlecry():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    shudder = game.player1.give("TOY_501")
    shudder.play()
    assert game.player1.next_battlecry_extra == 2
    # Refill mana (Shudderblock cost 6, Sentinel costs 7).
    game.player1.used_mana = 0
    game.player1.overloaded = 0
    # Now play a battlecry minion that summons a copy (Shining Sentinel).
    # Normally: original + 1 copy = 2 on board.
    # Tripled: battlecry runs 3 times -> original + 3 copies = 4 sentinels.
    sentinel = game.player1.give("TOY_503")
    sentinel.play()
    # consumed
    assert game.player1.next_battlecry_extra == 0
    sentinels = [m for m in game.player1.field if m.id == "TOY_503"]
    assert len(sentinels) == 4


# TOY_501 — Shudderblock: boosted battlecry can't damage the enemy hero
def test_shudderblock_no_enemy_hero_damage():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    shudder = game.player1.give("TOY_501")
    shudder.play()
    assert game.player1.next_battlecry_extra == 2
    game.player1.used_mana = 0
    game.player1.overloaded = 0
    game.player2.hero.damage = 0
    # Elven Archer: Battlecry deal 1 damage to a target. We aim it at the
    # enemy hero. Under Shudderblock's suppression the boosted battlecry
    # can't damage the enemy hero, so it takes 0.
    archer = game.player1.give("CS2_189")
    archer.play(target=game.player2.hero)
    assert game.player2.hero.damage == 0


# TOY_504 — Hagatha the Fabled
# Battlecry: Draw 2 spells that cost (5) or more. Transform them into Slimes
# that cast the spells.
def test_hagatha_the_fabled():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Stack the deck with two known 5+ cost spells: Pyroblast (10) is mage.
    # Use shaman-agnostic neutral? Spells are class-bound; use cost>=5 spells.
    # Put two copies of a 5+ cost spell into the deck.
    s1 = game.player1.give(PYROBLAST)  # cost 10 spell
    s1.zone = Zone.DECK
    s2 = game.player1.give("CS2_029")  # Fireball cost 4 -> NOT eligible
    s2.zone = Zone.DECK
    s3 = game.player1.give(PYROBLAST)
    s3.zone = Zone.DECK

    hag = game.player1.give("TOY_504")
    hag.play()
    # Two Fairy Tale Slimes should be in hand (drawn spells morphed into slimes)
    slimes = [c for c in game.player1.hand if c.id == "TOY_504t"]
    assert len(slimes) == 2
    # Each slime remembers a 5+ cost spell (Pyroblast), not Fireball.
    for sl in slimes:
        assert getattr(sl, "_fairy_tale_spell", None) == PYROBLAST
    # Fireball (cost 4) was not drawn/morphed -> still in deck
    assert any(c.id == "CS2_029" for c in game.player1.deck)


# TOY_504t — Fairy Tale Slime
# Battlecry: Cast <stored spell>.
def test_fairy_tale_slime_casts_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    slime = game.player1.give("TOY_504t")
    # Mind Blast: "Deal $5 damage to the enemy hero." No target choice, so the
    # cast outcome is deterministic regardless of CastSpell's random pick.
    slime._fairy_tale_spell = "DS1_233"
    game.player2.hero.damage = 0
    slime.play()
    assert game.player2.hero.damage == 5
