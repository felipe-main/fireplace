"""The Lost City of Un'Goro mini-set (DINO_ / Dinosaurs) — Shaman tests."""

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone


ELEMENTAL = "UNG_809t1"   # Flame Elemental (1/2, Race.ELEMENTAL)
BEAST = "CS2_172"         # Bloodfen Raptor (3/2 Beast)
WISP = "CS2_231"          # 1/1, no tribe
CHILLWIND = "CS2_182"     # Chillwind Yeti 4/5, no tribe (durable target)


def _clear_board(game, player):
    for m in list(player.field):
        m.destroy()
    game.process_deaths()


def _play_type_last_turn(game, player, card_id):
    """Play `card_id` from hand, advance two turns so its minion type counts
    as 'played last turn' for Kindred."""
    player.give(card_id).play()
    game.end_turn(); game.end_turn()


# ---------------------------------------------------------------------------
# DINO_406 Fire Breath — Deal $4 damage. Give your Elementals +1/+1.
# ---------------------------------------------------------------------------

def test_fire_breath_damage_and_elemental_buff():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    _clear_board(game, p1)
    # Clear the enemy board so the only enemy is the hero -> the random 4
    # damage lands deterministically on it. Beef it so the game doesn't end.
    _clear_board(game, p2)
    p2.hero.max_health = 80
    p2.hero.damage = 0

    # Two friendly Elementals + one non-Elemental (Wisp) that must NOT be buffed.
    ele1 = p1.summon(ELEMENTAL)   # 1/2 Elemental
    ele2 = p1.summon(ELEMENTAL)   # 1/2 Elemental
    wisp = p1.summon(WISP)        # 1/1, no tribe

    p1.give("DINO_406").play()

    # Exactly 4 damage to the only enemy (the hero).
    assert p2.hero.health == 76

    # Both friendly Elementals get exactly +1/+1.
    assert ele1.atk == 2 and ele1.health == 3
    assert ele2.atk == 2 and ele2.health == 3
    # The non-Elemental is untouched.
    assert wisp.atk == 1 and wisp.health == 1


# ---------------------------------------------------------------------------
# DINO_412 Tortotem — At the end of your turn, get a random minion with
# multiple minion types.
# ---------------------------------------------------------------------------

def test_tortotem_gets_multitype_minion_at_turn_end():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.summon("DINO_412")

    # Empty the hand so we can identify exactly the card we got.
    for c in list(p1.hand):
        c.discard()
    assert len(p1.hand) == 0

    game.end_turn()  # Tortotem's end-of-turn trigger fires here

    assert len(p1.hand) == 1
    got = p1.hand[0]
    # The fetched card is a minion with 2+ distinct minion types.
    races = {r for r in got.races if r != Race.INVALID}
    assert got.type == CardType.MINION
    assert len(races) >= 2


# ---------------------------------------------------------------------------
# DINO_413 Chillspine Stegodon — Battlecry: Deal 2 damage to two random enemy
# minions. Kindred: And Freeze them.
# ---------------------------------------------------------------------------

def test_chillspine_no_kindred_hits_two_no_freeze():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    _clear_board(game, p2)

    # Exactly two enemy minions -> both get hit; deterministic.
    m1 = p2.summon(CHILLWIND)   # 4/5
    m2 = p2.summon(CHILLWIND)   # 4/5

    # No matching type played last turn -> Kindred inactive.
    p1.give("DINO_413").play()

    assert m1.damage == 2 and m2.damage == 2
    # Without Kindred, neither is frozen.
    assert not m1.frozen
    assert not m2.frozen


def test_chillspine_kindred_freezes_the_two_it_hit():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2

    # Chillspine Stegodon is a Beast (Race tag 20). Play a Beast last turn to
    # activate Kindred.
    stego = p1.give("DINO_413")
    assert Race.BEAST in stego.races
    _play_type_last_turn(game, p1, BEAST)
    assert Race.BEAST in p1.races_played_last_turn

    _clear_board(game, p2)
    m1 = p2.summon(CHILLWIND)   # 4/5
    m2 = p2.summon(CHILLWIND)   # 4/5

    stego = p1.give("DINO_413")
    stego.play()

    # The same two minions take 2 damage AND are frozen.
    assert m1.damage == 2 and m2.damage == 2
    assert m1.frozen
    assert m2.frozen
