from utils import *


# TOY_602 Chemical Spill — Summon the highest Cost minion from your hand,
# then deal $5 damage to it.
def test_chemical_spill():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.discard_hand()
    # Add a cheaper minion to ensure the highest-cost one is selected.
    low = p1.give("CS2_125")   # Ironfur Grizzly cost 3
    high = p1.give("TOY_606")  # Testing Dummy 6-cost 4/8
    spill = p1.give("TOY_602")
    spill.play()
    # The 6-cost Testing Dummy is summoned and takes 5 damage.
    summoned = [m for m in p1.field if m.id == "TOY_606"]
    assert len(summoned) == 1
    assert summoned[0].damage == 5
    assert summoned[0].health == 8 - 5
    # The cheaper minion stayed in hand.
    assert low in p1.hand


# TOY_605 Quality Assurance — Draw 2 Taunt minions.
def test_quality_assurance():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.discard_hand()
    # Empty the deck, then stock it with 2 taunt minions and 2 non-taunt.
    for c in p1.deck[:]:
        p1.deck.remove(c)
    t1 = p1.give("CS2_121")  # Frostwolf Grunt 2/2 Taunt
    t2 = p1.give("CS2_121")
    # move them to deck
    for c in (t1, t2):
        c.zone = Zone.DECK
    nontaunt = p1.give("CS2_182")  # Chillwind Yeti 4/5 no taunt
    nontaunt.zone = Zone.DECK
    qa = p1.give("TOY_605")
    qa.play()
    drawn = [c for c in p1.hand if c.id == "CS2_121"]
    assert len(drawn) == 2
    # Non-taunt minion stayed in deck.
    assert any(c.id == "CS2_182" for c in p1.deck)


# TOY_907 Safety Goggles — Gain 6 Armor. Costs (0) if you don't have any Armor.
def test_safety_goggles_cost_zero_no_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    assert p1.hero.armor == 0
    sg = p1.give("TOY_907")
    assert sg.cost == 0
    sg.play()
    assert p1.hero.armor == 6


def test_safety_goggles_cost_two_with_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.hero.armor = 3
    sg = p1.give("TOY_907")
    assert sg.cost == 2
    sg.play()
    assert p1.hero.armor == 9


# TOY_606 Testing Dummy — Taunt, Deathrattle: Deal 8 damage randomly split
# among all enemies.
def test_testing_dummy_taunt_and_deathrattle():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    dummy = p1.summon("TOY_606")
    assert dummy.taunt
    # Only the enemy hero is a valid enemy target; give it a huge health pool
    # so all 8 ticks land on it and we can assert exact total damage.
    p2.hero.max_health = 80
    dummy.destroy()
    assert p2.hero.damage == 8


# TOY_908 Fireworker — Deathrattle: Summon two 1/1 Boom Bots.
def test_fireworker_deathrattle():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    fw = p1.summon("TOY_908")
    pre = len(p1.field)
    fw.destroy()
    bots = [m for m in p1.field if m.id == "GVG_110t"]
    assert len(bots) == 2
    assert all(b.atk == 1 and b.health == 1 for b in bots)


# TOY_651 Lab Patron — The first time you gain Armor each turn, summon another
# Lab Patron.
def test_lab_patron_first_armor_gain():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    patron = p1.summon("TOY_651")
    assert p1.armor_gained_this_turn == 0
    # First armor gain this turn -> summon another Lab Patron.
    p1.give("TOY_907").play()  # Safety Goggles, gain 6 armor
    patrons = [m for m in p1.field if m.id == "TOY_651"]
    assert len(patrons) == 2


def test_lab_patron_only_first_armor_gain():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    patron = p1.summon("TOY_651")
    # First gain of the turn -> summons one extra Patron (2 total).
    game.queue_actions(p1.hero, [GainArmor(p1.hero, 1)])
    assert p1.armor_gained_this_turn == 1
    assert len([m for m in p1.field if m.id == "TOY_651"]) == 2
    # Second gain this turn — should NOT summon any more Patrons.
    game.queue_actions(p1.hero, [GainArmor(p1.hero, 5)])
    patrons = [m for m in p1.field if m.id == "TOY_651"]
    assert len(patrons) == 2


# TOY_906 Botface — Taunt. After this takes damage, get two random Minis.
def test_botface_taunt_and_minis_on_damage():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    bot = p1.summon("TOY_906")
    assert bot.taunt
    p1.discard_hand()
    assert len(p1.hand) == 0
    game.queue_actions(p1.hero, [Hit(bot, 2)])
    assert bot.damage == 2
    # Two random Minis added to hand.
    assert len(p1.hand) == 2
    for c in p1.hand:
        assert c.data.tags.get(GameTag.MINI) == 1


# TOY_603 Wreck'em and Deck'em — Choose a friendly Mech. Summon a copy of it
# that attacks a random enemy, then dies.
def test_wreckem_and_deckem():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # A friendly vanilla mech to copy (Spider Tank 3/4, no deathrattle).
    mech = p1.summon("GVG_044")
    # Only valid enemy is the hero; beef it up to absorb the attack exactly.
    p2.hero.max_health = 80
    pre_field = len(p1.field)
    spell = p1.give("TOY_603")
    spell.play(target=mech)
    # The copy attacked the hero for 3 then died — board count unchanged.
    assert len(p1.field) == pre_field
    assert p2.hero.damage == 3
    # Original mech still alive.
    assert mech in p1.field


# TOY_604 Boom Wrench — Deathrattle: Trigger the Deathrattle of a random
# friendly Mech.
def test_boom_wrench_triggers_mech_deathrattle():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # A friendly mech with a deathrattle: Fireworker (summon 2 Boom Bots).
    fw = p1.summon("TOY_908")
    weapon = p1.give("TOY_604")
    weapon.play()
    assert p1.weapon is weapon
    pre_bots = len([m for m in p1.field if m.id == "GVG_110t"])
    # Destroy the weapon -> its deathrattle triggers Fireworker's deathrattle.
    weapon.destroy()
    bots = [m for m in p1.field if m.id == "GVG_110t"]
    # Fireworker's deathrattle fired (summoned 2 bots) but Fireworker itself
    # is still alive on board.
    assert fw in p1.field
    assert len(bots) == pre_bots + 2


# TOY_607 Inventor Boom — Battlecry: Resurrect two friendly Mechs that cost (5)
# or more. They immediately attack random enemies.
def test_inventor_boom_resurrects_costly_mechs():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # Put two 5+ cost friendly mechs into the graveyard.
    m1 = p1.summon("TOY_606")  # Testing Dummy, 6-cost mech 4/8
    m2 = p1.summon("TOY_606")
    m1.destroy()
    m2.destroy()
    # Clear any board / resolve the deathrattle damage on hero.
    p2.hero.max_health = 200
    boom = p1.give("TOY_607")
    boom.play()
    # Two Testing Dummies resurrected; each immediately attacked (4 atk each).
    resurrected = [m for m in p1.field if m.id == "TOY_606"]
    assert len(resurrected) == 2
