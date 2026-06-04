"""The Lost City of Un'Goro — Dinosaurs mini-set, Demon Hunter unit tests."""

from utils import *

from hearthstone.enums import CardClass, GameTag, Race, Zone

from fireplace.dsl.evaluator import kindred_active

# Vanilla helpers
BEAST = "CS2_172"     # Bloodfen Raptor — 3/2 Beast (Diabolus Rex shares BEAST)
MURLOC = "CS2_168"    # Murloc Raider — 2/3 Murloc (non-matching type)
WISP = "CS2_231"      # 0/1/1 vanilla filler
YETI = "CS2_182"      # Chillwind Yeti — 4/5, no race


def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


# --------------------------------------------------------------------------
# DINO_136 — Horn of Feasting
# --------------------------------------------------------------------------


def test_horn_of_feasting_summons_three_rush_raptors_no_outcast():
    """Played from a middle slot (not an edge) → only the base effect:
    three 2/1 Raptors with Rush, NO Immune-while-attacking."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    # Sandwich the Horn between two filler cards so it plays from a middle slot.
    p1.give(WISP)
    horn = p1.give("DINO_136")
    p1.give(WISP)
    assert p1.hand[1] is horn
    horn.play()
    raptors = [m for m in p1.field if m.id == "DINO_136t"]
    assert len(raptors) == 3
    for r in raptors:
        assert (r.atk, r.health) == (2, 1)
        assert r.rush is True
        # No Outcast → no Immune-while-attacking.
        assert r.immune_while_attacking is False


def test_horn_of_feasting_outcast_gives_immune_while_attacking():
    """Played from the rightmost slot → Outcast: the three Raptors gain
    Immune while attacking this turn (on top of the base summon)."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    horn = p1.give("DINO_136")  # only card → leftmost == rightmost == edge
    assert p1.hand[-1] is horn
    horn.play()
    raptors = [m for m in p1.field if m.id == "DINO_136t"]
    assert len(raptors) == 3
    for r in raptors:
        assert (r.atk, r.health) == (2, 1)
        assert r.rush is True
        assert r.immune_while_attacking is True


# --------------------------------------------------------------------------
# DINO_137 — Skittish Saucier
# --------------------------------------------------------------------------


def test_skittish_saucier_reduces_adjacent_hand_costs():
    """Battlecry reduces the Cost of the two cards adjacent in hand by (1)
    each; non-adjacent cards are untouched."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    far_left = p1.give(YETI)     # index 0 — not adjacent
    left = p1.give(YETI)         # index 1 — left neighbour
    saucier = p1.give("DINO_137")  # index 2
    right = p1.give(YETI)        # index 3 — right neighbour
    far_right = p1.give(YETI)    # index 4 — not adjacent
    base = far_left.cost
    assert left.cost == base and right.cost == base
    saucier.play()
    # Both immediate neighbours dropped by exactly 1.
    assert left.cost == base - 1
    assert right.cost == base - 1
    # The cards two slots away are untouched.
    assert far_left.cost == base
    assert far_right.cost == base


def test_skittish_saucier_single_neighbor_edge():
    """When the Saucier sits at the left edge it has only a right neighbour;
    only that card is discounted."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    saucier = p1.give("DINO_137")  # index 0 (left edge)
    right = p1.give(YETI)          # index 1 — only neighbour
    other = p1.give(YETI)          # index 2 — not adjacent
    base = right.cost
    saucier.play()
    assert right.cost == base - 1
    assert other.cost == base


# --------------------------------------------------------------------------
# DINO_138 — Diabolus Rex (Kindred)
# --------------------------------------------------------------------------


def test_diabolus_rex_kindred_active_hits_outermost_enemies():
    """Kindred active (a Beast played last turn) → deal 6 to the opponent's
    left- and right-most minions; the middle one is untouched."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p2 = game.player2
    # Set up Kindred: play a Beast this turn, then return to p1's next turn.
    p1.give(BEAST).play()
    game.end_turn()
    # Opponent fills its board with three sturdy minions so all survive 6 dmg.
    leftmost = p2.summon(YETI)
    middle = p2.summon(YETI)
    rightmost = p2.summon(YETI)
    for m in (leftmost, middle, rightmost):
        m.max_health = 80
        m.damage = 0
    game.end_turn()  # back to p1
    assert Race.BEAST in p1.races_played_last_turn
    rex = p1.give("DINO_138")
    assert kindred_active(rex)
    rex.play()
    assert leftmost.damage == 6
    assert rightmost.damage == 6
    assert middle.damage == 0


def test_diabolus_rex_kindred_doubled_by_primalfin_challenger():
    """Primalfin Challenger's "next Kindred triggers twice" → Diabolus Rex
    deals 6 to each outermost enemy TWICE (12 total), and the charge is spent."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p2 = game.player2
    # Beast last turn arms Kindred for Diabolus Rex.
    p1.give(BEAST).play()
    game.end_turn()
    leftmost = p2.summon(YETI)
    middle = p2.summon(YETI)
    rightmost = p2.summon(YETI)
    for m in (leftmost, middle, rightmost):
        m.max_health = 80
        m.damage = 0
    game.end_turn()  # back to p1
    assert Race.BEAST in p1.races_played_last_turn
    # Arm the doubling, then play Diabolus Rex.
    p1.give("TLC_251").play()
    assert p1.next_kindred_double == 1
    rex = p1.give("DINO_138")
    assert kindred_active(rex)
    rex.play()
    # 6 damage applied twice to each outermost enemy; middle untouched.
    assert leftmost.damage == 12
    assert rightmost.damage == 12
    assert middle.damage == 0
    # The charge is consumed exactly once.
    assert p1.next_kindred_double == 0


def test_diabolus_rex_kindred_inactive_no_damage():
    """Kindred inactive (no matching type played last turn) → no damage."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    p2 = game.player2
    # Play a non-matching type (Murloc) last turn so Kindred does NOT activate.
    p1.give(MURLOC).play()
    game.end_turn()
    leftmost = p2.summon(YETI)
    middle = p2.summon(YETI)
    rightmost = p2.summon(YETI)
    for m in (leftmost, middle, rightmost):
        m.max_health = 80
        m.damage = 0
    game.end_turn()
    assert Race.BEAST not in p1.races_played_last_turn
    rex = p1.give("DINO_138")
    assert not kindred_active(rex)
    rex.play()
    assert leftmost.damage == 0
    assert middle.damage == 0
    assert rightmost.damage == 0
