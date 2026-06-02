"""The Lost City of Un'Goro — Druid card tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, SpellSchool, Zone


def test_tlc_230_treeees():
    # Summon four 2/2 Treants that attack a chosen minion.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    # 0-Attack Target Dummy, beefed up so it survives all four 2-attack hits
    # (4*2 = 8 < 30) and deals no retaliation back to the treants.
    target = p2.summon("GVG_093")  # Target Dummy 0/2
    target.max_health = 30
    target.damage = 0
    assert target.atk == 0
    game.end_turn()
    game.end_turn()

    spell = p1.give("TLC_230")
    spell.play(target=target)

    treants = [m for m in p1.field if m.id == "TLC_230t"]
    assert len(treants) == 4
    for t in treants:
        assert t.atk == 2 and t.max_health == 2
    # Four 2-attack hits = 8 damage onto the 30-health target.
    assert target.damage == 8
    # The 0-Attack target deals no retaliation: treants are unharmed.
    for t in treants:
        assert t.damage == 0


def test_tlc_231_story_of_barnabus_buffs_big_minion():
    # Draw a minion; if it has 5+ Attack, give +5 Health and gain 5 Armor.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.discard_hand()
    p1.deck.clear()
    # Stack the deck so the only minion to draw is a 7/7 (>=5 atk).
    big = p1.give("CS2_186")  # War Golem 7/7
    big.zone = Zone.DECK
    assert p1.hero.armor == 0

    spell = p1.give("TLC_231")
    spell.play()

    assert big.zone == Zone.HAND
    assert big.atk == 7
    # +5 Health: 7 base -> 12.
    assert big.max_health == 12
    assert p1.hero.armor == 5


def test_tlc_231_story_of_barnabus_no_buff_small_minion():
    # A minion with <5 Attack gets no buff and grants no Armor.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.discard_hand()
    p1.deck.clear()
    small = p1.give("CS2_172")  # Bloodfen Raptor 3/2 (<5 atk)
    small.zone = Zone.DECK

    spell = p1.give("TLC_231")
    spell.play()

    assert small.zone == Zone.HAND
    assert small.atk == 3
    assert small.max_health == 2  # unbuffed
    assert p1.hero.armor == 0


def test_tlc_232_ravenous_flock_delayed_summon():
    # At the start of your next turn, summon three 2/1 Hatchlings.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1

    p1.give("TLC_232").play()
    # Nothing summoned yet this turn.
    assert len([m for m in p1.field if m.id == "TLC_237t"]) == 0

    game.end_turn()  # opponent turn
    game.end_turn()  # back to p1 -> objective fires at turn begin

    hatchlings = [m for m in p1.field if m.id == "TLC_237t"]
    assert len(hatchlings) == 3
    for h in hatchlings:
        assert h.atk == 2 and h.max_health == 1
    # The objective destroyed itself; it doesn't fire again next turn.
    game.end_turn()
    game.end_turn()
    assert len([m for m in p1.field if m.id == "TLC_237t"]) == 3


def test_tlc_233_hatchery_helper_buffs_low_attack_minions():
    # Give your OTHER minions with 2 or less Attack +1/+2 and Taunt.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    low = p1.summon("CS2_231")  # Wisp 1/1 (atk<=2)
    high = p1.summon("CS2_186")  # War Golem 7/7 (atk>2)

    helper = p1.give("TLC_233")
    helper.play()

    # Low-attack minion buffed +1/+2 and gains Taunt: 1/1 -> 2/3.
    assert low.atk == 2
    assert low.max_health == 3
    assert low.taunt is True
    # High-attack minion untouched.
    assert high.atk == 7
    assert high.max_health == 7
    assert high.taunt is False
    # Helper itself (2/3) is excluded ("other") despite having 2 Attack: no
    # Taunt, base stats unchanged.
    assert helper.atk == 2
    assert helper.max_health == 3
    assert helper.taunt is False


def test_tlc_234_eternal_bloodpetal_deathrattle_chain():
    # Deathrattle: Summon a 0/1 Eternal Seedling (which resummons a 5/1 Bloodpetal).
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    petal = p1.summon("TLC_234")
    assert petal.atk == 5 and petal.max_health == 1

    petal.destroy()
    game.process_deaths()
    seedlings = [m for m in p1.field if m.id == "TLC_234t"]
    assert len(seedlings) == 1
    seedling = seedlings[0]
    assert seedling.atk == 0 and seedling.max_health == 1

    seedling.destroy()
    game.process_deaths()
    petals = [m for m in p1.field if m.id == "TLC_234"]
    assert len(petals) == 1
    assert petals[0].atk == 5 and petals[0].max_health == 1


def test_tlc_235_life_cycle_replaces_with_same_cost():
    # Destroy a minion. Summon a random minion of the same Cost to replace it.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    # Target a 4-cost minion. Replacement must also be 4-cost.
    target = p2.summon("CS2_182")  # Chillwind Yeti, cost 4
    assert target.cost == 4
    game.end_turn()
    game.end_turn()

    spell = p1.give("TLC_235")
    spell.play(target=target)
    game.process_deaths()

    # Original is gone.
    assert target.zone == Zone.GRAVEYARD
    # Net board count is unchanged: exactly one replacement, on the
    # opponent's board, of the same Cost, and it is a different minion.
    assert len(p2.field) == 1
    replacement = p2.field[0]
    assert replacement is not target
    assert replacement.cost == 4


def test_tlc_235_life_cycle_replacement_lands_in_vacated_slot():
    # The replacement should appear in the *destroyed minion's* position,
    # not tacked on to the end of the board. The old script summoned the
    # replacement before the destroy, so it landed at the end instead.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    left = p2.summon("CS2_171")        # Stonetusk Boar, cost 1 (index 0)
    target = p2.summon("CS2_182")      # Chillwind Yeti, cost 4 (index 1)
    right = p2.summon("CS2_171")       # Stonetusk Boar, cost 1 (index 2)
    assert p2.field.index(target) == 1
    game.end_turn()
    game.end_turn()

    spell = p1.give("TLC_235")
    spell.play(target=target)
    game.process_deaths()

    assert target.zone == Zone.GRAVEYARD
    assert len(p2.field) == 3
    # The two survivors keep their relative order; the replacement sits
    # between them in the slot the Yeti vacated (index 1).
    replacement = p2.field[1]
    assert replacement is not left and replacement is not right
    assert replacement.cost == 4
    assert p2.field[0] is left
    assert p2.field[2] is right


def test_tlc_235_life_cycle_works_on_full_board():
    # Edge case: the target's controller already has a full (7-minion)
    # board. The printed card destroys first, freeing a slot, so the
    # same-Cost replacement must still appear. The old "summon before
    # destroy" script silently dropped the replacement here, because a
    # 7-minion board makes the summon a no-op.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    # Seven minions; the 4-cost Yeti sits in the middle (index 3).
    minions = [p2.summon("CS2_171") for _ in range(3)]
    target = p2.summon("CS2_182")      # Chillwind Yeti, cost 4 (index 3)
    minions += [p2.summon("CS2_171") for _ in range(3)]
    assert len(p2.field) == 7
    assert p2.field.index(target) == 3
    game.end_turn()
    game.end_turn()

    spell = p1.give("TLC_235")
    spell.play(target=target)
    game.process_deaths()

    assert target.zone == Zone.GRAVEYARD
    # Still a full board (one out, one in) — the replacement was NOT
    # dropped, and it has the same Cost as the destroyed Yeti.
    assert len(p2.field) == 7
    replacement = p2.field[3]
    assert replacement not in minions
    assert replacement.cost == 4


def test_tlc_236_hybridization_draws_four_costs_no_kindred():
    # Draw a 1, 2, 3, and 4-Cost minion. Without Kindred they are full price.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    p1.deck.clear()
    # Seed exactly one minion of each cost 1-4.
    m1 = p1.give("CS2_171"); m1.zone = Zone.DECK  # Stonetusk Boar, 1 cost
    m2 = p1.give("CS2_120"); m2.zone = Zone.DECK  # River Crocolisk, 2 cost
    m3 = p1.give("CS2_124"); m3.zone = Zone.DECK  # Wolfrider, 3 cost
    m4 = p1.give("CS2_182"); m4.zone = Zone.DECK  # Chillwind Yeti, 4 cost
    assert (m1.cost, m2.cost, m3.cost, m4.cost) == (1, 2, 3, 4)

    spell = p1.give("TLC_236")
    spell.play()

    for m in (m1, m2, m3, m4):
        assert m.zone == Zone.HAND
    # No Kindred -> costs unchanged.
    assert m1.cost == 1
    assert m2.cost == 2
    assert m3.cost == 3
    assert m4.cost == 4


def test_tlc_236_hybridization_kindred_costs_one_less():
    # With Kindred active, the four drawn minions cost (1) less. TLC_236 is a
    # Nature spell, so Kindred triggers off a Nature card played last turn.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.give("EX1_169").play()  # Innervate, a Nature spell
    game.end_turn()
    game.end_turn()
    assert SpellSchool.NATURE in p1.schools_played_last_turn

    # Clear hand/deck and seed the four minions.
    for c in list(p1.hand):
        c.discard()
    p1.deck.clear()
    m1 = p1.give("CS2_171"); m1.zone = Zone.DECK  # 1
    m2 = p1.give("CS2_120"); m2.zone = Zone.DECK  # 2
    m3 = p1.give("CS2_124"); m3.zone = Zone.DECK  # 3
    m4 = p1.give("CS2_182"); m4.zone = Zone.DECK  # 4

    spell = p1.give("TLC_236")
    # TLC_236 is a Spell (Nature school) — and a Beast was played last turn,
    # so Kindred is satisfied by race; the spell itself doesn't matter here.
    spell.play()

    for m in (m1, m2, m3, m4):
        assert m.zone == Zone.HAND
    # Kindred -> each costs (1) less.
    assert m1.cost == 0
    assert m2.cost == 1
    assert m3.cost == 2
    assert m4.cost == 3


def test_tlc_237_skyscreamer_eggs_deathrattle():
    # Deathrattle: Summon four 2/1 Hatchlings.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    egg = p1.summon("TLC_237")
    assert egg.atk == 0 and egg.max_health == 2

    egg.destroy()
    game.process_deaths()
    hatchlings = [m for m in p1.field if m.id == "TLC_237t"]
    assert len(hatchlings) == 4
    for h in hatchlings:
        assert h.atk == 2 and h.max_health == 1


def test_tlc_239_restore_the_wild_quest_reward():
    # Quest: Fill your board on 3 of your turns. Reward: The Everbloom.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    quest = p1.give("TLC_239")
    quest.play()
    assert quest in p1.secrets

    def fill_and_end():
        # Fill to exactly 7 minions, then end the turn (quest ticks on end).
        while len(p1.field) < 7:
            p1.summon("CS2_231")  # Wisp
        assert len(p1.field) == 7
        game.end_turn()
        game.end_turn()

    fill_and_end()  # progress 1
    assert quest.progress == 1
    # Clear board so the next fill is a fresh "turn with a full board".
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()

    fill_and_end()  # progress 2
    assert quest.progress == 2
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()

    fill_and_end()  # progress 3 -> quest completes, reward summons
    game.process_deaths()

    # Reward is The Everbloom, a 2/5 weapon equipped on the hero.
    assert quest not in p1.secrets
    assert p1.hero.weapon is not None
    assert p1.hero.weapon.id == "TLC_239t"
    assert p1.hero.weapon.atk == 2
    assert p1.hero.weapon.durability == 5


def test_tlc_239t_everbloom_buffs_on_hero_attack():
    # The Everbloom is a 2/5 weapon: After your hero attacks, give your
    # minions +2/+2.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    bloom = p1.summon("TLC_239t")  # equips as the hero's weapon
    assert p1.hero.weapon is bloom
    assert bloom.atk == 2 and bloom.durability == 5
    ally = p1.summon("CS2_186")  # War Golem 7/7
    game.end_turn()
    game.end_turn()

    assert p1.hero.atk == 2  # attacking with the Everbloom weapon
    p1.hero.attack(p2.hero)
    game.process_deaths()

    # All friendly minions get +2/+2 after the hero swings.
    assert ally.atk == 9
    assert ally.max_health == 9


def test_tlc_257_loh_sets_minions_cost_five():
    # Battlecry: Your minions cost (5) this game.
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # A cheap minion and an expensive one in hand.
    cheap = p1.give("CS2_171")  # Stonetusk Boar, cost 1
    pricey = p1.give("CS2_186")  # War Golem, cost 7
    spell = p1.give("CS2_029")  # Fireball (a spell, should be unaffected)
    assert cheap.cost == 1 and pricey.cost == 7

    loh = p1.give("TLC_257")
    loh.play()

    # Both minions in hand now cost 5.
    assert cheap.cost == 5
    assert pricey.cost == 5
    # Spell cost unchanged.
    assert spell.cost == 4
    # A minion drawn later also costs 5 (persists this game).
    later = p1.give("CS2_182")  # Chillwind Yeti, cost 4
    assert later.cost == 5
