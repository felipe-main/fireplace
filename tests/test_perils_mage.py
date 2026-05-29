"""Perils in Paradise — MAGE collectible card tests.

Covers all 10 collectible mage cards (VAC_424, VAC_428, VAC_431, VAC_435,
VAC_443, VAC_509, VAC_520, VAC_522, VAC_524, VAC_953). Assertions pin the
PRINTED card behaviour.
"""

from utils import *

from fireplace import cards as _cards


# Stat-stable neutral minions used as deterministic targets / fodder.
WISP = "CS2_231"            # 0/1/1 vanilla
BLOODFEN = "CS2_172"        # 2/3/2 vanilla Bloodfen Raptor
CHILLWIND = "CS2_182"       # 4/4/5 vanilla Chillwind Yeti
MOONFIRE = "CS2_008"        # 0-cost spell (deal 1)
FIREBALL = "CS2_029"        # 4-cost spell (deal 6)


# VAC_424 — Raylla, Sand Sculptor: Paladin Tourist. After you cast a spell,
# summon a random 2-Cost minion and give it Divine Shield.
def test_raylla_sand_sculptor():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    game.player1.summon("VAC_424")
    pre = len(p1.field)
    # Cast any spell -> one random 2-Cost minion summoned with Divine Shield.
    p1.give(MOONFIRE).play(target=game.player2.hero)
    summoned = p1.field[pre:]
    assert len(summoned) == 1
    minion = summoned[0]
    assert minion.data.cost == 2
    assert minion.divine_shield


def test_raylla_no_trigger_without_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    game.player1.summon("VAC_424")
    pre = len(p1.field)
    # Summoning / playing a minion is not "casting a spell" -> no extra summon.
    p1.give(WISP).play()
    # Only the Wisp was added.
    assert len([m for m in p1.field[pre:] if m.id != WISP]) == 0


# VAC_428 — Go with the Flow: Choose a minion. If it's an enemy, Freeze it.
# If it's friendly, give it Spell Damage +1.
def test_go_with_the_flow_freezes_enemy():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(BLOODFEN)
    spell = p1.give("VAC_428")
    spell.play(target=enemy)
    assert enemy.frozen
    # Enemy minion is frozen, not buffed with spellpower.
    assert enemy.spellpower == 0


def test_go_with_the_flow_buffs_friendly():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    friendly = p1.summon(BLOODFEN)
    assert friendly.spellpower == 0
    spell = p1.give("VAC_428")
    spell.play(target=friendly)
    # Friendly minion gets Spell Damage +1 and is NOT frozen.
    assert friendly.spellpower == 1
    assert not friendly.frozen


# VAC_431 — Under the Sea: Draw a different spell. Summon a random minion of
# that spell's Cost.
def test_under_the_sea():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Stack exactly one spell in the deck with a known cost (Fireball = 4).
    fireball = p1.give(FIREBALL)
    fireball.zone = Zone.DECK
    pre = len(p1.field)
    spell = p1.give("VAC_431")
    spell.play()
    # The deck spell was drawn into hand.
    assert fireball.zone == Zone.HAND
    # Exactly one minion summoned, whose Cost equals the drawn spell's Cost (4).
    summoned = p1.field[pre:]
    assert len(summoned) == 1
    assert summoned[0].data.cost == 4


# VAC_435 — Marooned Archmage: Your first spell each turn costs (2) less.
def test_marooned_archmage_first_spell_discount():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    game.player1.summon("VAC_435")
    fb = p1.give(FIREBALL)
    # Fireball base cost 4 -> first spell this turn costs 2 less = 2.
    assert fb.cost == 2


def test_marooned_archmage_only_first_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    game.player1.summon("VAC_435")
    # Cast a spell first (consumes the "first spell" discount).
    p1.give(MOONFIRE).play(target=game.player2.hero)
    fb = p1.give(FIREBALL)
    # No discount remains -> full cost 4.
    assert fb.cost == 4


# VAC_443 — Surfalopod: Battlecry: The next spell you draw is Cast When Drawn.
def test_surfalopod_next_spell_casts_when_drawn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Arcane Explosion (CS2_025): deal 1 to all enemy minions — no target
    # required, so casting-on-draw is unambiguously observable.
    spell = p1.give("CS2_025")
    spell.zone = Zone.DECK
    victim = p2.summon(CHILLWIND)
    victim.max_health = 80
    victim._max_health = 80
    victim.damage = 0
    surf = p1.give("VAC_443")
    surf.play()
    p1.draw()
    # The spell was tagged Cast When Drawn...
    assert spell.tags.get(GameTag.CASTS_WHEN_DRAWN)
    # ...so on draw it resolved (1 dmg to enemy minion) and went to graveyard,
    # never entering the hand.
    assert spell.zone == Zone.GRAVEYARD
    assert victim.damage == 1


# VAC_509 — Tsunami: Summon three 3/6 Water Elementals that Freeze. They
# attack random enemies.
def test_tsunami_summons_three_water_elementals():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Beef hero so the three attacks land on face (no enemy minions) safely.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    pre = len(p1.field)
    spell = p1.give("VAC_509")
    spell.play()
    elems = [m for m in p1.field[pre:] if m.id == "VAC_509t"]
    assert len(elems) == 3
    # Token printed body is 3/6.
    for m in elems:
        assert m.atk == 3
        assert m.max_health == 6
    # Each attacked the only enemy (hero) for 3 -> 9 total.
    assert p2.hero.health == 80 - 9


def test_water_elemental_token_freezes():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    attacker = game.current_player
    defender = attacker.opponent
    elem = attacker.summon("VAC_509t")
    elem.turns_in_play = 1  # clear summoning sickness so it can attack
    target = defender.summon(CHILLWIND)  # 4/5 — survives a 3-damage hit
    elem.attack(target)
    # Anything damaged by the Water Elemental is frozen, and took exactly 3.
    assert target.damage == 3
    assert target.frozen


# VAC_520 — Seabreeze Chalice (Drink): Deal $2 damage randomly split among all
# enemies. Chains: 3 -> 2 -> Last Drink.
def test_seabreeze_chalice_damage_and_chain():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Single enemy character: a high-HP minion absorbs both split ticks so the
    # total is exactly measurable. Beef hero so no face damage skews things —
    # but the only enemy character is the minion when hero can't be hit? Hero
    # is also an enemy character, so give it huge HP and measure the minion.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    victim = p2.summon(CHILLWIND)
    victim.max_health = 80
    victim._max_health = 80
    victim.damage = 0
    chalice = p1.give("VAC_520")
    chalice.play()
    # 2 damage split among all enemies (hero + minion); total dealt is exactly 2.
    total = p2.hero.damage + victim.damage
    assert total == 2
    # Next Drink ("2 Drinks left") returned to hand.
    nxt = [c for c in p1.hand if c.id == "VAC_520t"]
    assert len(nxt) == 1


def test_seabreeze_chalice_last_drink_returns_nothing():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    last = p1.give("VAC_520t2")  # Last Drink
    last.play()
    # 2 damage dealt to the only enemy (hero).
    assert p2.hero.damage == 2
    # No further Chalice copy granted.
    assert not any(c.id in ("VAC_520", "VAC_520t", "VAC_520t2") for c in p1.hand)


# VAC_522 — Tide Pools (Location): Discover a spell that costs (3) or less.
# After you cast a spell, reopen this.
def test_tide_pools_discovers_cheap_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    loc = p1.give("VAC_522")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.type == CardType.SPELL
        assert (cdata.cost or 0) <= 3
    p1.choice.choose(p1.choice.cards[0])
    # Using set the standard 2-turn cooldown.
    assert loc.cooldown == 2


def test_tide_pools_reopens_after_spell_cast():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    loc = p1.give("VAC_522")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert loc.cooldown == 2
    # Casting a spell reopens the location -> cooldown cleared.
    p1.give(MOONFIRE).play(target=game.player2.hero)
    assert loc.cooldown == 0


# VAC_524 — King Tide: Battlecry: Both players' spells cost (5) until the end
# of your next turn.
def test_king_tide_sets_both_hands_spells_to_five():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    my_spell = p1.give(MOONFIRE)       # base 0-cost
    their_spell = p2.give(FIREBALL)    # base 4-cost
    king = p1.give("VAC_524")
    king.play()
    # Both players' spells in hand now cost (5).
    assert my_spell.cost == 5
    assert their_spell.cost == 5


def test_king_tide_expires_end_of_next_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    king = p1.give("VAC_524")
    king.play()
    my_spell = p1.give(MOONFIRE)
    assert my_spell.cost == 5
    # End my turn (tick 1), opponent's turn, then end my next turn (tick 2).
    game.end_turn()   # p1 OWN_TURN_END (tick 1)
    game.end_turn()   # p2 turn ends
    game.end_turn()   # p1 next OWN_TURN_END (tick 2) -> aura gone
    # Back on opponent's turn now; the aura has expired -> base cost restored.
    assert my_spell.cost == 0


# VAC_953 — Rising Waves: Deal $2 damage to all minions. If none die, deal $2
# more.
def test_rising_waves_double_when_none_die():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # All minions survive a single 2-damage tick -> second tick fires.
    a = p1.summon(CHILLWIND)  # 4/5
    b = p2.summon(CHILLWIND)  # 4/5
    spell = p1.give("VAC_953")
    spell.play()
    game.process_deaths()
    # None died after the first 2, so a second 2 lands: total 4 each.
    assert a.damage == 4
    assert b.damage == 4
    assert a.zone == Zone.PLAY
    assert b.zone == Zone.PLAY


def test_rising_waves_single_hit_when_one_dies():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    survivor = p1.summon(CHILLWIND)  # 4/5 — survives 2
    dies = p2.summon(BLOODFEN)       # 3/2 — dies to 2
    spell = p1.give("VAC_953")
    spell.play()
    game.process_deaths()
    # One minion died -> no second tick. Survivor took exactly 2.
    assert dies.zone == Zone.GRAVEYARD
    assert survivor.damage == 2
