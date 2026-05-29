from utils import *
from fireplace.exceptions import GameOver

IMP_DEMON = "EX1_598"  # Imp, 1/1 Demon
WISP = "CS2_231"


# TOY_524 — Game Master Nemsy: Battlecry draw a Demon; Deathrattle swap places.
def test_game_master_nemsy_draw_and_swap():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Empty the deck, then seed exactly one Demon so the draw is deterministic.
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.discard()
    demon = game.player1.give(IMP_DEMON)
    demon.shuffle_into_deck()
    assert demon.zone == Zone.DECK

    nemsy = game.player1.give("TOY_524")
    nemsy.play()
    # Battlecry drew the demon into hand.
    assert demon.zone == Zone.HAND
    assert nemsy.zone == Zone.PLAY

    pre_field = len(game.player1.field)
    nemsy.destroy()
    game.process_deaths()
    # Deathrattle: the drawn demon is summoned into play (swap places).
    assert demon.zone == Zone.PLAY
    # Nemsy returned to hand (a fresh copy).
    assert any(c.id == "TOY_524" for c in game.player1.hand)


# TOY_526 — Malefic Rook: Battlecry Attack YOUR hero.
def test_malefic_rook_attacks_own_hero():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    hero = game.player1.hero
    hero.max_health = 40
    hero.damage = 0
    rook = game.player1.give("TOY_526")
    rook.play()
    # 5-attack minion hits own hero for 5.
    assert hero.damage == 5
    assert rook.zone == Zone.PLAY


# TOY_914 — Wretched Queen: Taunt. Deathrattle summon two 4/6 Knights w/ Taunt.
def test_wretched_queen_deathrattle():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    queen = game.player1.summon("TOY_914")
    assert queen.taunt
    queen.destroy()
    game.process_deaths()
    knights = [c for c in game.player1.field if c.id == "TOY_914t"]
    assert len(knights) == 2
    # Printed: "two 4/6 Knights with Taunt" — token TOY_914t is 4 atk / 6 hp.
    for k in knights:
        assert k.atk == 4
        assert k.max_health == 6
        assert k.taunt


# TOY_915 — Tabletop Roleplayer: Battlecry give friendly Demon +2 Atk + Immune.
def test_tabletop_roleplayer_buff():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    demon = game.player1.summon(IMP_DEMON)  # 1/1 Demon
    pre_atk = demon.atk
    rp = game.player1.give("TOY_915")
    rp.play(target=demon)
    assert demon.atk == pre_atk + 2
    assert demon.immune
    assert demon.cant_be_targeted_by_opponents


def test_tabletop_roleplayer_immune_clears_end_of_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    demon = game.player1.summon(IMP_DEMON)
    rp = game.player1.give("TOY_915")
    rp.play(target=demon)
    assert demon.immune
    game.end_turn()
    game.end_turn()
    # "this turn" effect — gone next turn.
    assert not demon.immune
    assert demon.atk == 1


# TOY_915t — Mini token: same battlecry.
def test_tabletop_roleplayer_mini_token():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    demon = game.player1.summon(IMP_DEMON)
    mini = game.player1.give("TOY_915t")
    assert mini.atk == 1 and mini.max_health == 1
    mini.play(target=demon)
    assert demon.atk == 3
    assert demon.immune


# TOY_527 — Cursed Campaign: give friendly minion "Deathrattle: summon two
# Dormant-for-2 copies of this minion".
def test_cursed_campaign_deathrattle():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    target = game.player1.summon(WISP)  # 1/1
    spell = game.player1.give("TOY_527")
    spell.play(target=target)
    target.destroy()
    game.process_deaths()
    copies = [c for c in game.player1.field if c.id == WISP]
    assert len(copies) == 2
    for c in copies:
        assert c.dormant
        assert c.dormant_turns == 2


# TOY_529 — Wheel of DEATH!!!: Destroy your deck. In 5 turns destroy enemy hero.
def test_wheel_of_death_destroys_deck():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    assert len(game.player1.deck) > 0
    wheel = game.player1.give("TOY_529")
    wheel.play()
    assert len(game.player1.deck) == 0


def test_wheel_of_death_kills_enemy_hero():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.cant_fatigue = True
    game.player2.cant_fatigue = True
    enemy_hero = game.player2.hero
    wheel = game.player1.give("TOY_529")
    wheel.play()
    assert not enemy_hero.dead
    # Counter ticks at the start of each of OUR turns. Need 5 own-turn-begins.
    # Turns 1-4 should NOT kill; the 5th own-turn-begin destroys the enemy hero
    # (which raises GameOver).
    died_on = None
    try:
        for i in range(1, 7):
            game.end_turn()  # our turn -> opp
            game.end_turn()  # opp -> our (OWN_TURN_BEGIN -> tick i)
            if enemy_hero.dead:
                died_on = i
                break
    except GameOver:
        died_on = i
    assert enemy_hero.dead
    # Exactly 5 ticks (5 own turns after the one it was played on).
    assert died_on == 5


# TOY_883 — Table Flip: Deal 3 to all enemy minions, costs (1) less per other
# card in hand.
def test_table_flip_damage():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    e1 = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    e2 = game.player2.summon("CS2_182")
    friendly = game.player1.summon("CS2_182")
    flip = game.player1.give("TOY_883")
    flip.play()
    assert e1.damage == 3
    assert e2.damage == 3
    assert friendly.damage == 0  # only ENEMY minions


def test_table_flip_cost_reduction():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    flip = game.player1.give("TOY_883")
    # No other cards in hand -> full cost 10.
    assert flip.cost == 10
    # Add 3 other cards.
    for _ in range(3):
        game.player1.give(WISP)
    assert flip.cost == 7


# TOY_884 — Crane Game: Summon copies of two Demons in your deck.
def test_crane_game_summons_two_demons():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    for c in list(game.player1.deck):
        c.discard()
    # Seed exactly 3 demons; expect two distinct summoned.
    d1 = game.player1.give(IMP_DEMON); d1.shuffle_into_deck()
    d2 = game.player1.give(IMP_DEMON); d2.shuffle_into_deck()
    d3 = game.player1.give(IMP_DEMON); d3.shuffle_into_deck()
    crane = game.player1.give("TOY_884")
    crane.play()
    summoned = [c for c in game.player1.field if c.id == IMP_DEMON]
    assert len(summoned) == 2


def test_crane_game_no_demons_does_nothing():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    for c in list(game.player1.deck):
        c.discard()
    game.player1.give(WISP).shuffle_into_deck()  # not a demon
    crane = game.player1.give("TOY_884")
    crane.play()
    assert len(game.player1.field) == 0


# TOY_886 — Endgame: Resurrect your last Demon that died.
def test_endgame_resurrects_last_demon():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Kill a non-demon, then a demon, then non-demon — last demon to die is imp.
    imp = game.player1.summon(IMP_DEMON)
    wisp = game.player1.summon(WISP)
    imp.destroy()
    game.process_deaths()
    wisp.destroy()
    game.process_deaths()
    spell = game.player1.give("TOY_886")
    spell.play()
    demons = [c for c in game.player1.field if c.id == IMP_DEMON]
    assert len(demons) == 1


# TOY_916 — Sketch Artist: Draw a Shadow spell; get a temporary copy of it.
def test_sketch_artist_draws_shadow_and_temp_copy():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.discard()
    # Mind Blast (CS2_022? ) — use a known Shadow spell. Use "Shadow Bolt" EX1_308? that's Fel.
    # Use Mind Blast = DS1_233 (Shadow). Seed one shadow spell in deck.
    shadow = game.player1.give("DS1_233")  # Mind Blast, Shadow spell
    shadow.shuffle_into_deck()
    artist = game.player1.give("TOY_916")
    artist.play()
    # The shadow spell was drawn to hand.
    drawn = [c for c in game.player1.hand if c.id == "DS1_233"]
    # One drawn original + one temporary copy.
    assert len(drawn) == 2
    temps = [c for c in drawn if c.temporary]
    assert len(temps) == 1
