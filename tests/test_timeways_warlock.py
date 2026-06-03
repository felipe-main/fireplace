"""Across the Timeways — Warlock.

One tight test per collectible (and per effect-bearing Rafaam token). Random
effects are pinned by controlling deck contents / beefing up HP so assertions
are exact.
"""
import pytest

from utils import *
from fireplace.exceptions import GameOver


def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


def _deck_card(player, cid):
    return player.card(cid, zone=Zone.DECK)


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# Timethief Rafaam (TIME_005) + Rafaam tokens
# ---------------------------------------------------------------------------


def test_timethief_rafaam_destroys_only_when_rest_played():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Not all 9 other Rafaams played yet -> battlecry does nothing.
    rafaam = p1.give("TIME_005")
    rafaam.cost = 0
    rafaam.play()
    assert game.player2.hero.health == 30

    # Now actually play every other Rafaam this game so they register in
    # cards_played_this_game. Destroy each after to keep the board open.
    for cid in ["TIME_005t1", "TIME_005t2", "TIME_005t3", "TIME_005t4",
                "TIME_005t5", "TIME_005t6", "TIME_005t7", "TIME_005t8",
                "TIME_005t9"]:
        c = p1.give(cid)
        c.cost = 0  # bypass mana so each high-Cost Rafaam is playable
        c.play()
        _resolve_choices(p1)
        for m in list(p1.field):
            m.destroy()
    assert game.player2.hero.health == 30  # still alive before the trigger

    rafaam2 = p1.give("TIME_005")
    rafaam2.cost = 0
    # Destroying the enemy hero ends the game.
    with pytest.raises(GameOver):
        rafaam2.play()
    assert game.player2.hero.dead


def test_tiny_rafaam_deathrattle_draws_a_rafaam():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    # Only a single Rafaam in the deck so the draw is deterministic.
    target = _deck_card(p1, "TIME_005t9")
    tiny = p1.summon("TIME_005t1")
    tiny.destroy()
    assert target.zone == Zone.HAND
    assert len(p1.hand) == 1


def test_green_rafaam_buffs_rafaams_in_hand():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    raf = p1.give("TIME_005t7")   # Giant Rafaam 8/8 (a Rafaam)
    other = p1.give("TIME_025")   # Twilight Timehopper (NOT a Rafaam)
    green = p1.give("TIME_005t2")
    green.play()
    assert raf.atk == 10 and raf.health == 10
    assert other.atk == 4 and other.health == 4  # untouched


def test_explorer_rafaam_discovers_from_deck():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    _deck_card(p1, "TIME_005t4")
    explorer = p1.give("TIME_005t3")
    explorer.play()
    assert p1.choice is not None
    # Every offered card is a Rafaam; choosing gives a copy to hand.
    assert all(c.id in (
        "TIME_005", "TIME_005t1", "TIME_005t2", "TIME_005t3", "TIME_005t4",
        "TIME_005t5", "TIME_005t6", "TIME_005t7", "TIME_005t8", "TIME_005t9",
    ) for c in p1.choice.cards)
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    assert any(c.id == chosen.id for c in p1.hand)


def test_warchief_rafaam_armor_with_and_without_other_rafaam():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.armor = 0
    w1 = p1.give("TIME_005t4")
    w1.play()
    assert p1.hero.armor == 5  # no other Rafaam on board

    p1.summon("TIME_005t1")  # another Rafaam in play
    w2 = p1.give("TIME_005t4")
    w2.play()
    assert p1.hero.armor == 15  # 5 + (5 + 5)


def test_mindflayer_summons_copy_when_holding_rafaam():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("TIME_005t1")  # holding another Rafaam
    mind = p1.give("TIME_005t5")
    mind.play()
    flayers = [m for m in p1.field if m.id == "TIME_005t5"]
    assert len(flayers) == 2


def test_mindflayer_no_copy_without_held_rafaam():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    mind = p1.give("TIME_005t5")
    mind.play()
    assert len([m for m in p1.field if m.id == "TIME_005t5"]) == 1


def test_calamitous_rafaam_damages_non_rafaam_only():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    rafaam = p1.summon("TIME_005t9")   # Archmage Rafaam 9/9 (a Rafaam)
    victim = game.player2.summon("TIME_025")  # 4/4 Twilight Timehopper
    cal = p1.give("TIME_005t6")
    cal.play()
    assert rafaam.health == 9         # Rafaam untouched
    assert victim.dead                # 6 dmg killed the 4/4


def test_giant_rafaam_cost_reduction():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    giant = p1.give("TIME_005t7")
    assert giant.cost == 8
    # Play two other Rafaams this game.
    for cid in ["TIME_005t1", "TIME_005t2"]:
        c = p1.give(cid)
        c.play()
        _resolve_choices(p1)
    assert giant.cost == 6  # 8 - 2


def test_murloc_rafaam_next_rafaam_costs_3_less():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    next_raf = p1.give("TIME_005t9")  # Archmage Rafaam, base cost 9
    nonraf = p1.give("TIME_025")      # base cost 2
    murloc = p1.give("TIME_005t8")
    murloc.play()
    assert next_raf.cost == 6   # 9 - 3
    assert nonraf.cost == 2     # non-Rafaam unaffected


def test_murloc_rafaam_single_realized_discount_net_invariant():
    # Row 578 watch (accepted, net-correct): the discount enchant's
    # `update = Refresh(FRIENDLY_HAND + RAFAAM, {COST: -3})` visually shows -3
    # on EVERY held Rafaam at once, but the discount is realized only once —
    # consumed when the next Rafaam is played. This regression pins the NET
    # invariant: holding TWO Rafaams, the total realized discount is exactly 3
    # (the first one pays 3 less, the second then pays full), never 6.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    r1 = p1.give("TIME_005t9")   # Archmage Rafaam, base cost 9
    r2 = p1.give("TIME_005t9")   # second Archmage Rafaam, base cost 9
    murloc = p1.give("TIME_005t8")
    murloc.play()
    # Visual over-display: both currently read -3 (cosmetic, accepted).
    assert r1.cost == 6 and r2.cost == 6
    # Play the first Rafaam — it pays 9 - 3 = 6, then the discount is consumed.
    r1.cost = 0  # bypass mana; play() still fires the consume event
    r1.play()
    _resolve_choices(p1)
    # The SECOND Rafaam now pays full: total realized discount is exactly 3.
    assert r2.cost == 9


def test_murloc_rafaam_self_does_not_consume_discount():
    # The enchant's creator (Murloc Rafaam itself) must NOT consume the
    # discount when it resolves its own Play — only the *next* Rafaam does.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    nxt = p1.give("TIME_005t9")   # base cost 9
    murloc = p1.give("TIME_005t8")
    murloc.play()
    _resolve_choices(p1)
    # Discount survives Murloc's own play and still applies to the next Rafaam.
    assert nxt.cost == 6


def test_archmage_rafaam_transforms_non_rafaam_to_sheep():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    rafaam = p1.summon("TIME_005t7")          # Giant Rafaam (a Rafaam)
    sheep_target = game.player2.summon("TIME_025")  # 4/4 non-Rafaam
    arch = p1.give("TIME_005t9")
    arch.play()
    assert rafaam.id == "TIME_005t7"          # Rafaam not transformed
    new = game.player2.field[0]
    assert new.id == "TIME_005t9t" and new.atk == 1 and new.health == 1


# ---------------------------------------------------------------------------
# Standalone collectibles
# ---------------------------------------------------------------------------


def test_bygone_doomspeaker_both_discard():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _clear_hand(p2)
    p1_card = p1.give("TIME_025")
    p2_card = p2.give("TIME_025")
    doom = p1.give("TIME_008")
    doom.play()
    # Keep the offered Rewind timeline (re-runs effect); first pick Keep.
    keep = next(c for c in p1.choice.cards if c.id == "TIME_000ta")
    p1.choice.choose(keep)
    # Discard removes the card from the game.
    assert p1_card.zone == Zone.REMOVEDFROMGAME
    assert p2_card.zone == Zone.REMOVEDFROMGAME


def test_bygone_doomspeaker_rewind_reruns():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _clear_hand(p2)
    # Two cards each: base play discards one, Rewind discards the second.
    p1.give("TIME_025"); p1.give("TIME_025")
    p2.give("TIME_025"); p2.give("TIME_025")
    doom = p1.give("TIME_008")
    doom.play()
    assert len(p1.hand) == 1  # base play discarded one from p1
    rewind = next(c for c in p1.choice.cards if c.id == "TIME_000tb")
    p1.choice.choose(rewind)
    _resolve_choices(p1)
    assert len(p1.hand) == 0
    assert len(p2.hand) == 0


def test_twilight_timehopper_shuffles_two_shreds():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    hopper = p1.give("TIME_025")
    hopper.play()
    shreds = [c for c in p1.deck if c.id == "TIME_025t"]
    assert len(shreds) == 2


def test_shred_of_time_casts_when_drawn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    assert p1.hero.health == 30
    shred = _deck_card(p1, "TIME_025t")
    game.queue_actions(p1.hero, [Draw(p1)])
    # Cast-when-drawn fired: 3 damage to own hero, card not lingering in hand.
    assert p1.hero.health == 27
    assert shred.zone != Zone.HAND


def test_entropic_continuity_buffs_and_shuffles():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    m1 = p1.summon("TIME_025")  # 4/4
    cont = p1.give("TIME_026")
    cont.play()
    assert m1.atk == 5 and m1.health == 5
    assert len([c for c in p1.deck if c.id == "TIME_025t"]) == 2


def test_tachyon_barrage_split_damage_and_shuffle():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    # Single enemy character (hero) — no enemy minions, so all 6 ticks land on
    # the hero (30 HP absorbs all 6).
    barrage = p1.give("TIME_027")
    barrage.play()
    assert p2.hero.health == 24  # exactly 6 damage total
    assert len([c for c in p1.deck if c.id == "TIME_025t"]) == 2


def test_fatebreaker_casts_shred_and_buffs():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    assert p1.hero.health == 30
    _deck_card(p1, "TIME_025t")
    fate = p1.give("TIME_028")
    fate.play()
    # The Shred (cast from deck) deals 3 to our own hero.
    assert p1.hero.health == 27
    assert fate.atk == 7 and fate.health == 7  # 4/4 + 3/3


def test_fatebreaker_no_shred_no_buff():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    fate = p1.give("TIME_028")
    fate.play()
    assert fate.atk == 4 and fate.health == 4  # unbuffed, no Shred in deck


def test_ruinous_velocidrake_casts_shred_and_summons_copy():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    assert p1.hero.health == 30
    _deck_card(p1, "TIME_025t")
    drake = p1.give("TIME_029")
    drake.play()
    assert p1.hero.health == 27  # Shred hit hero for 3
    assert len([m for m in p1.field if m.id == "TIME_029"]) == 2


def test_ruinous_velocidrake_no_shred_no_copy():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    drake = p1.give("TIME_029")
    drake.play()
    assert len([m for m in p1.field if m.id == "TIME_029"]) == 1


def test_divergence_splits_minion_in_hand():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    # Only one minion in hand -> deterministic target. Giant Rafaam 8/8 cost 8.
    p1.give("TIME_005t7")
    div = p1.give("TIME_030")
    div.play()
    halves = [c for c in p1.hand if c.id == "TIME_005t7"]
    assert len(halves) == 2
    for h in halves:
        assert h.atk == 4 and h.health == 4  # 8 -> 4 (half)
        assert h.cost == 4                   # 8 -> 4 (half)


def test_rafaam_ladder_draws_three_distinct_costs():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    _clear_hand(p1)
    # Deck with costs 1,2,2,3 (top to bottom). Should draw the 1, a 2, the 3.
    _deck_card(p1, "TIME_026")   # cost 1
    _deck_card(p1, "TIME_027")   # cost 2
    _deck_card(p1, "TIME_025")   # cost 2 (skipped — duplicate cost)
    _deck_card(p1, "TIME_028")   # cost 4
    ladder = p1.give("TIME_031")
    ladder.play()
    drawn_costs = sorted(c.cost for c in p1.hand)
    assert len(p1.hand) == 3
    assert len(set(drawn_costs)) == 3  # all distinct costs


def test_chronogor_splits_high_and_low():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _clear_hand(p2)
    for c in list(p1.deck):
        c.zone = Zone.REMOVEDFROMGAME
    lo1 = _deck_card(p1, "TIME_026")  # cost 1
    lo2 = _deck_card(p1, "TIME_027")  # cost 2
    hi1 = _deck_card(p1, "TIME_032")  # cost 6
    hi2 = _deck_card(p1, "TIME_005")  # cost 10
    chrono = p1.give("TIME_032")
    chrono.play()
    # 2 highest to me, 2 lowest to opponent.
    assert hi1.zone == Zone.HAND and hi1.controller is p1
    assert hi2.zone == Zone.HAND and hi2.controller is p1
    assert lo1.zone == Zone.HAND and lo1.controller is p2
    assert lo2.zone == Zone.HAND and lo2.controller is p2


def test_chronogor_net_outcome_exact_ids_and_costs():
    # Row 579 watch (accepted, net-correct): the opponent's two drawn cards are
    # relocated via SETASIDE rather than the real draw pipeline (no draw
    # triggers / fatigue / overdraw-burn for the opponent), and the controller's
    # own two highest use ForceDraw. Only those edge draw-trigger/fatigue
    # semantics differ — the NET hand state is correct. This regression pins the
    # exact NET result by controlling the whole deck: controller gains its two
    # HIGHEST-cost cards, opponent gains the controller's two LOWEST-cost cards.
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _clear_hand(p2)
    for c in list(p1.deck):
        c.zone = Zone.REMOVEDFROMGAME
    # Distinct, well-separated costs so the high/low split is unambiguous.
    lo1 = _deck_card(p1, "TIME_026")  # cost 1
    lo2 = _deck_card(p1, "TIME_027")  # cost 2
    hi1 = _deck_card(p1, "TIME_032")  # cost 6
    hi2 = _deck_card(p1, "TIME_005")  # cost 10
    assert (lo1.cost, lo2.cost, hi1.cost, hi2.cost) == (1, 2, 6, 10)
    pre_drawn = p2.cards_drawn_this_turn
    chrono = p1.give("TIME_032")
    chrono.play()
    # The opponent genuinely DREW their two cards (real draw pipeline fired).
    assert p2.cards_drawn_this_turn == pre_drawn + 2
    # Controller's hand == exactly the two highest-cost cards.
    assert sorted(c.id for c in p1.hand) == ["TIME_005", "TIME_032"]
    assert sorted(c.cost for c in p1.hand) == [6, 10]
    assert all(c.controller is p1 for c in p1.hand)
    # Opponent's hand == exactly the controller's two lowest-cost cards.
    assert sorted(c.id for c in p2.hand) == ["TIME_026", "TIME_027"]
    assert sorted(c.cost for c in p2.hand) == [1, 2]
    assert all(c.controller is p2 for c in p2.hand)
    # The relocated cards left the controller's deck entirely.
    assert hi1 in p1.hand and hi2 in p1.hand
    assert lo1 in p2.hand and lo2 in p2.hand
