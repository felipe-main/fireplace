"""Perils in Paradise — WARRIOR collectible card tests.

Asserts the PRINTED behaviour of each Warrior card (and its tokens):
Line Cook, Cup o' Muscle (Drink chain), Muensterosity, Hamm the Hungry
(Druid Tourist), Undercooked Calamari, Char, Draconic Delicacy,
The Ryecleaver (+ Slice of Bread / Minion Sandwich), All You Can Eat,
Food Fight (+ Entrée).
"""

from utils import *
from fireplace import cards as _cards


# VAC_337 — Line Cook: Tradeable. Taunt. When you draw this, get a copy of it.
def test_line_cook_draw_gives_copy():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    cook = p1.card("VAC_337")
    cook.zone = Zone.DECK
    pre = len(p1.hand)
    p1.draw()
    # Drew Line Cook itself, plus an exact copy granted by the draw trigger.
    cooks_in_hand = [c for c in p1.hand if c.id == "VAC_337"]
    assert len(cooks_in_hand) == 2
    assert len(p1.hand) == pre + 2


def test_line_cook_taunt():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    cook = game.player1.summon("VAC_337")
    assert cook.taunt


# VAC_338 — Cup o' Muscle (Drink): Give a minion in your hand +2/+1. (3 Drinks left!)
def test_cup_o_muscle_buffs_hand_minion():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # Exactly one minion in hand so the random pick is deterministic.
    target = p1.give(WISP)  # 1/1
    base_atk, base_health = target.atk, target.max_health
    spell = p1.give("VAC_338")
    spell.play()
    assert target.atk == base_atk + 2
    assert target.max_health == base_health + 1


def test_cup_o_muscle_drink_chain():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    p1.give(WISP)  # a hand minion to receive each buff
    # First Drink -> next copy (VAC_338t, "2 Drinks left") enters hand.
    spell = p1.give("VAC_338")
    spell.play()
    t1 = [c for c in p1.hand if c.id == "VAC_338t"]
    assert len(t1) == 1
    # Second Drink -> last copy (VAC_338t2, "Last Drink") enters hand.
    t1[0].play()
    t2 = [c for c in p1.hand if c.id == "VAC_338t2"]
    assert len(t2) == 1
    assert not any(c.id == "VAC_338t" for c in p1.hand)
    # Last Drink -> nothing further returns to hand.
    t2[0].play()
    assert not any(c.id in ("VAC_338", "VAC_338t", "VAC_338t2") for c in p1.hand)


# VAC_339 — Muensterosity: Taunt. End of turn, summon an Elemental with stats
# equal to this minion's.
def test_muensterosity_taunt():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    m = game.player1.summon("VAC_339")
    assert m.taunt


def test_muensterosity_summons_matching_elemental():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    m = p1.summon("VAC_339")  # printed 6/9
    assert (m.atk, m.health) == (6, 9)
    pre = len(p1.field)
    game.end_turn()
    cheese = [c for c in p1.field if c.id == "VAC_339t"]
    assert len(cheese) == 1
    # Cheese Elemental stats equal Muensterosity's current stats (6/9), not 1/1.
    assert (cheese[0].atk, cheese[0].max_health) == (6, 9)
    assert Race.ELEMENTAL in cheese[0].races
    assert len(p1.field) == pre + 1


# VAC_340 — Hamm, the Hungry: Druid Tourist, Taunt. End of turn, eat a minion in
# enemy's deck to gain +2/+2.
def test_hamm_taunt_and_stats():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    hamm = game.player1.summon("VAC_340")
    assert hamm.taunt
    assert (hamm.atk, hamm.max_health) == (3, 3)


def test_hamm_eats_enemy_deck_minion():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    hamm = p1.summon("VAC_340")
    # Put exactly one minion in the enemy deck.
    victim = p2.card(WISP)
    victim.zone = Zone.DECK
    assert len(p2.deck) == 1
    game.end_turn()  # p1's end of turn fires Hamm
    # The minion was eaten (removed from enemy deck) and Hamm gained +2/+2.
    assert len(p2.deck) == 0
    assert (hamm.atk, hamm.max_health) == (3 + 2, 3 + 2)


def test_hamm_no_minion_no_buff():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    hamm = p1.summon("VAC_340")
    # Enemy deck has no minions (only spells) -> nothing to eat, no buff.
    # Seed two spells so p2's turn-start draw still leaves the deck spell-only.
    for _ in range(2):
        s = p2.card(MOONFIRE)
        s.zone = Zone.DECK
    game.end_turn()  # p1's end of turn fires Hamm (before p2 draws)
    # No enemy-deck minion existed when Hamm triggered -> Hamm stays 3/3.
    assert (hamm.atk, hamm.max_health) == (3, 3)


def test_hamm_tourist_unlocks_druid():
    # Druid Tourist: a Warrior deck built with the Druid tourist unlock should
    # contain Druid cards plus a Tourist card.
    from fireplace.utils import random_draft
    deck = random_draft(CardClass.WARRIOR, tourist=CardClass.DRUID)
    classes_seen = set()
    has_tourist = False
    for cid in deck:
        cdata = _cards.db[cid]
        cc = cdata.card_class
        classes_seen.add(cc)
        if getattr(cdata, "tourist", None) or "VAC_340" == cid:
            has_tourist = True
    assert CardClass.DRUID in classes_seen
    assert has_tourist


# VAC_341 — Undercooked Calamari: Battlecry: Destroy an enemy minion with Attack
# <= this minion's (4).
def test_undercooked_calamari_destroys_low_attack():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_172")  # Bloodfen Raptor 3/2, atk 3 <= 4
    cal = p1.give("VAC_341")  # 3/4, atk 3... printed atk 3? data says 4/3/4 -> atk 3
    cal.play(target=victim)
    assert victim.zone == Zone.GRAVEYARD


def test_undercooked_calamari_cannot_destroy_higher_attack():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # A minion with attack strictly greater than Calamari's is not a legal
    # target (the printed "Attack <= this minion's" gate, via REQ_TARGET_MAX_ATTACK).
    big = p2.summon("CS2_172")
    cal = p1.give("VAC_341")  # printed atk 4
    big.atk = cal.atk + 5  # well above Calamari's attack
    # And a low-attack minion that IS a legal target, to prove the gate is the
    # discriminator (not "no targets at all").
    small = p2.summon(WISP)  # atk 1
    targets = cal.play_targets
    assert big not in targets
    assert small in targets


# VAC_526 — Char: Deal 7 to a minion; give a minion in your hand stats equal to
# the excess damage.
def test_char_deals_7_and_buffs_excess():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # Target with 4 health -> 7 damage = 3 excess.
    target = p2.summon("CS2_172")
    target.max_health = 4
    target.damage = 0
    # Exactly one minion in hand to receive the excess buff (deterministic).
    hand_minion = p1.give(WISP)  # 1/1
    spell = p1.give("VAC_526")
    spell.play(target=target)
    # 7 damage destroys the 4-health target.
    assert target.zone == Zone.GRAVEYARD
    # Excess = 7 - 4 = 3 -> hand minion gets +3/+3.
    assert hand_minion.atk == 1 + 3
    assert hand_minion.max_health == 1 + 3


def test_char_no_excess_no_buff():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # Target with 10 health -> 7 damage, no excess.
    target = p2.summon("CS2_172")
    target.max_health = 10
    target.damage = 0
    hand_minion = p1.give(WISP)
    spell = p1.give("VAC_526")
    spell.play(target=target)
    assert target.health == 10 - 7
    # No excess -> hand minion unbuffed.
    assert (hand_minion.atk, hand_minion.max_health) == (1, 1)


# VAC_527 — Draconic Delicacy: Rush, Elusive. Can only take 1 damage at a time.
def test_draconic_delicacy_keywords():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    m = p1.summon("VAC_527")
    assert m.rush
    # Elusive: a targeted spell (Fireball) cannot target this minion.
    fireball = p1.give(FIREBALL)
    assert m not in fireball.play_targets
    # A non-Elusive minion IS a valid Fireball target (proves the gate is Elusive,
    # not "no minion targets at all").
    plain = p1.summon(WISP)
    assert plain in fireball.play_targets


def test_draconic_delicacy_caps_damage_at_1():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    m = p1.summon("VAC_527")  # 6/6
    # A 7-damage Fireball-equivalent hit should be capped to 1.
    fireball = p1.give(FIREBALL)
    # Fireball targets minions; Elusive blocks spells, so hit directly instead.
    p1.game.cheat_action(p1.hero, [Hit(m, 7)])
    assert m.damage == 1


# VAC_525 — The Ryecleaver (Weapon): Battlecry and Deathrattle: Get a Slice of Bread.
def test_ryecleaver_battlecry_gives_slice():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    weapon = p1.give("VAC_525")
    weapon.play()
    slices = [c for c in p1.hand if c.id == "VAC_525t1"]
    assert len(slices) == 1


def test_ryecleaver_deathrattle_gives_slice():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    weapon = p1.give("VAC_525")
    weapon.play()
    # Clear the battlecry slice so we measure the deathrattle one.
    for c in [c for c in p1.hand if c.id == "VAC_525t1"]:
        c.discard()
    p1.hero.weapon.destroy()
    game.process_deaths()
    slices = [c for c in p1.hand if c.id == "VAC_525t1"]
    assert len(slices) == 1


def test_slice_of_bread_sandwich_packs_and_resummons():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # First slice: marks the board.
    slice1 = p1.give("VAC_525t1")
    slice1.play()
    assert p1._ryecleaver_slice == 0
    # Summon two minions between the slices.
    a = p1.summon("CS2_172")  # Bloodfen Raptor
    b = p1.summon(WISP)
    # Second slice: stuffs the two minions into a Minion Sandwich token.
    slice2 = p1.give("VAC_525t1")
    slice2.play()
    assert p1._ryecleaver_slice is None
    assert a.zone == Zone.REMOVEDFROMGAME
    assert b.zone == Zone.REMOVEDFROMGAME
    sandwich = [c for c in p1.hand if c.id == "VAC_525t2"]
    assert len(sandwich) == 1
    assert sandwich[0].cost == 2
    # Playing the sandwich re-summons the two stuffed minions.
    pre = len(p1.field)
    sandwich[0].play()
    assert len(p1.field) == pre + 2
    ids = sorted(m.id for m in p1.field[pre:])
    assert ids == sorted(["CS2_172", WISP])


# VAC_528 — All You Can Eat: Draw three minions of different minion types.
def test_all_you_can_eat_draws_three_distinct_types():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1 = game.player1
    # Seed deck: 2 Beasts, 1 Murloc, 1 Dragon, 1 Mech. Three distinct-typed
    # minions should be drawn (never two of the same race).
    for cid in ["CS2_172", "CS2_172", "EX1_506", "NEW1_023", "BOT_309"]:
        # CS2_172 Bloodfen Raptor (Beast), EX1_506 Murloc Tidehunter (Murloc),
        # NEW1_023 Faerie Dragon (Dragon), BOT_309 Annoy-o-Tron (Mech).
        c = p1.card(cid)
        c.zone = Zone.DECK
    spell = p1.give("VAC_528")
    spell.play()
    drawn = [c for c in p1.hand if c.type == CardType.MINION and c.id != "VAC_528"]
    assert len(drawn) == 3
    # All drawn minions have pairwise-distinct race sets (different types).
    racesets = [frozenset(getattr(c, "races", []) or []) for c in drawn]
    for i in range(len(racesets)):
        for j in range(i + 1, len(racesets)):
            # No shared race between any two drawn minions.
            assert not (racesets[i] & racesets[j])


# VAC_533 — Food Fight: Summon a 0/6 Entrée for your opponent. When it dies,
# summon a minion from your deck.
def test_food_fight_summons_entree_for_opponent():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    spell = p1.give("VAC_533")
    spell.play()
    entrees = [m for m in p2.field if m.id == "VAC_533t"]
    assert len(entrees) == 1
    assert (entrees[0].atk, entrees[0].max_health) == (0, 6)
    assert entrees[0].controller is p2


def test_food_fight_entree_deathrattle_summons_for_caster():
    game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p1, p2 = game.player1, game.player2
    # Caster (p1) has exactly one minion in deck to be summoned on the
    # Entrée's death ("your opponent summons a minion from their deck", from the
    # Entrée's view = p1).
    seed = p1.card(WISP)
    seed.zone = Zone.DECK
    spell = p1.give("VAC_533")
    spell.play()
    entree = [m for m in p2.field if m.id == "VAC_533t"][0]
    pre_p1_field = len(p1.field)
    entree.destroy()
    game.process_deaths()
    # The seeded Wisp was summoned onto the caster's (p1) board.
    assert seed.zone == Zone.PLAY
    assert len(p1.field) == pre_p1_field + 1


# VAC_338 Cup o' Muscle (Tier-2 faithful): player CHOOSES which hand minion
# gets +2/+1 (modelled as an ENTITY_CHOICE over friendly hand minions).
def test_cup_o_muscle_buffs_chosen_hand_minion():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    m1 = p.give("CS2_172")  # Bloodfen Raptor 3/2
    m2 = p.give("CS2_182")  # Chillwind Yeti 4/5
    p.give("VAC_338").play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    buffed = [m for m in (m1, m2) if m.atk != m.data.atk]
    assert len(buffed) == 1            # exactly one hand minion buffed
    assert buffed[0].atk == buffed[0].data.atk + 2
    # Drink chain still returns the next copy.
    assert any(c.id == "VAC_338t" for c in p.hand)
