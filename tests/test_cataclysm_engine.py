"""Cataclysm — engine primitives: Herald and Shatter."""
from utils import *

from hearthstone.enums import Zone

from fireplace.actions import Herald


def test_herald_bumps_per_game_counter():
    game = prepare_game()
    p1 = game.player1
    assert p1.heralds_this_game == 0
    game.queue_actions(p1.hero, [Herald(p1)])
    assert p1.heralds_this_game == 1
    game.queue_actions(p1.hero, [Herald(p1)])
    assert p1.heralds_this_game == 2


def test_shatter_card_splits_into_two_halves_on_draw():
    game = prepare_game()
    p1 = game.player1
    assert p1.shatters_this_game == 0
    # Seed a Shatter spell (Arcane Flow) directly onto the deck — use card()
    # (SETASIDE) not give(), since giving it to HAND would itself shatter it
    # via the generation hook. Then draw it.
    card = p1.card("CATA_489")  # Arcane Flow — Shatter
    card.zone = Zone.DECK
    p1.draw()
    # The full card shattered into its two "Shattered" halves.
    assert p1.shatters_this_game == 1
    ids = [c.id for c in p1.hand]
    assert "CATA_489t" in ids
    assert "CATA_489t2" in ids
    assert "CATA_489" not in ids


# ---------------------------------------------------------------------------
# Transform-boundary audit fixes (roadmap/transform_boundary_audit.md):
# enchantments/cost-mods must survive the Shatter split/recombine identity
# change instead of being stranded, lost, or doubled.
# ---------------------------------------------------------------------------


def _give_shatter_with_buff(game, player, enchant, **kw):
    """Give a Shatter spell (Wildwood Circle, base cost 3) with a chained buff on
    the generated card; the buff must land on the live halves, not the discarded
    parent. Returns the two halves."""
    for c in list(player.hand):
        c.discard()
    game.queue_actions(
        player.hero,
        [Give(player, "CATA_134").then(Buff(Give.CARD, enchant, **kw))],
    )
    return [c for c in player.hand if c.id in ("CATA_134t", "CATA_134t2")]


def test_shatter_on_generate_chained_buff_lands_on_both_halves():
    # A5: Horn of Plenty / Ashamane pattern — Give(...).then(Buff(Give.CARD, ...)).
    game = prepare_game()
    p1 = game.player1
    halves = _give_shatter_with_buff(game, p1, "EDR_950e", cost=-1)
    assert len(halves) == 2
    for h in halves:
        assert any(b.id == "EDR_950e" for b in h.buffs)
        assert h.cost == h.data.cost - 1  # base 3 -> 2


def test_shatter_on_generate_dual_effect_buff_lands_on_both_halves():
    # A5: Blessing of the Moon's EDR_449pe carries BOTH a cost cut AND the
    # "Temporary" self-destruct (its Hand.events Destroys the host at end of
    # turn). The single enchant reaching both halves carries both effects — the
    # audit's "loses a second effect too" case. Ending the turn destroys both
    # halves, proving the Temporary downside followed the cost cut.
    game = prepare_game()
    p1 = game.current_player
    halves = _give_shatter_with_buff(game, p1, "EDR_449pe", cost=-2)
    assert len(halves) == 2
    for h in halves:
        assert any(b.id == "EDR_449pe" for b in h.buffs)
        assert h.cost == h.data.cost - 2
    game.end_turn()
    # Both Temporary halves self-destructed at the controller's end of turn.
    assert not [c for c in p1.hand if c.id in ("CATA_134t", "CATA_134t2")]


def test_shatter_on_draw_chained_buff_lands_on_both_halves():
    # A5: Sharp-Eyed Lookout — Draw(...).then(Buff(Draw.CARD, cost=-1)); the
    # drawn card is a Shatter spell that splits, and the discount must follow.
    game = prepare_game()
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    seeded = p1.card("CATA_134")  # Shatter spell seeded on top of deck
    seeded.zone = Zone.DECK
    p1.give("EDR_950").play()  # Battlecry: draw a card, it costs (1) less
    halves = [c for c in p1.hand if c.id in ("CATA_134t", "CATA_134t2")]
    assert len(halves) == 2
    for h in halves:
        assert h.cost == h.data.cost - 1


def test_shatter_split_carries_parent_enchants_onto_halves():
    # A4: a full Shatter card that already carries an enchant migrates it onto
    # the halves (the split's discard would otherwise drop it).
    from fireplace.actions import _shatter_into_halves

    game = prepare_game()
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Build a full Shatter card in hand without auto-splitting, buff it, split it.
    card = p1.card("CATA_134")
    game._shattering = True
    card.zone = Zone.HAND
    game._shattering = False
    game.queue_actions(p1.hero, [Buff(card, "EDR_950e", cost=-1)])
    assert card.cost == card.data.cost - 1
    _shatter_into_halves(card, p1)
    halves = [c for c in p1.hand if c.id in ("CATA_134t", "CATA_134t2")]
    assert len(halves) == 2
    for h in halves:
        assert any(b.id == "EDR_950e" for b in h.buffs)
        assert h.cost == h.data.cost - 1


def _force_recombine(game, player, halves):
    for c in list(player.hand):
        if c not in halves:
            c.discard()
    for h in halves:
        h._shatter_separated = True
    process_shatter_recombine(player)


def test_shatter_recombine_conserves_cost_discount_without_doubling():
    # A3: each half carries a -1 cost enchant; the recombined card must be
    # discounted by the SUM (conservation) exactly once per half (base 3 -> 1),
    # never by re-applying enchants AND a separate total (which would give -4).
    from fireplace.actions import process_shatter_recombine  # noqa: F401

    game = prepare_game()
    p1 = game.player1
    halves = _give_shatter_with_buff(game, p1, "EDR_950e", cost=-1)
    assert [h.cost for h in halves] == [2, 2]
    _force_recombine(game, p1, halves)
    parent = [c for c in p1.hand if c.id == "CATA_134"]
    assert len(parent) == 1
    assert parent[0].cost == parent[0].data.cost - 2  # 3 - (1+1) = 1


def _recombined_parent(player, parent_id):
    """Build a recombined Shatter parent (the _no_reshatter, playable form)."""
    parent = player.card(parent_id)
    parent._no_reshatter = True
    parent.zone = Zone.HAND
    return parent


def test_recombined_arcane_flow_does_both_halves():
    # A6: CATA_489 — Deal 4 to a target AND 2 to all enemies.
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # 4/5
    target.max_health = 80
    target.damage = 0
    flow = _recombined_parent(p1, "CATA_489")
    flow.play(target=target)
    assert target.damage == 6  # 4 (targeted) + 2 (AoE)
    assert p2.hero.health == 30 - 2  # AoE hit the hero too


def test_recombined_wildwood_circle_does_both_halves():
    # A6: CATA_134 — summon two 2/2 Treants AND give your minions a deathrattle.
    game = prepare_game()
    p1 = game.player1
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    existing = p1.summon("CS2_182")
    _recombined_parent(p1, "CATA_134").play()
    treants = [m for m in p1.field if m.id == "CATA_134t3"]
    assert len(treants) == 2
    assert existing.has_deathrattle  # the deathrattle-granting half also ran


def test_recombined_flight_maneuvers_does_both_halves():
    # A6: CATA_479 — summon two 4/2 Drakes AND give your minions +1/+1 + DS.
    game = prepare_game()
    p1 = game.player1
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    pre = p1.summon("CS2_182")  # 4/5
    _recombined_parent(p1, "CATA_479").play()
    drakes = [m for m in p1.field if m.id == "CATA_479t3"]
    assert len(drakes) == 2
    assert (pre.atk, pre.max_health) == (5, 6) and pre.divine_shield


def test_recombined_schism_does_both_halves():
    # A6: CATA_306 — buff a friendly minion +2/+3 + Elusive AND summon a copy.
    game = prepare_game()
    p1 = game.player1
    for m in list(p1.field):
        m.destroy()
    game.process_deaths()
    target = p1.summon("CS2_182")  # 4/5
    _recombined_parent(p1, "CATA_306").play(target=target)
    assert (target.atk, target.max_health) == (6, 8)  # +2/+3
    copies = [m for m in p1.field if m.id == "CS2_182"]
    assert len(copies) == 2  # original + the summoned copy


def test_recombined_supply_run_does_both_halves():
    # A6: CATA_820 — draw 3 minions AND give minions in hand +2/+2. The draw is
    # RANDOM(FRIENDLY_DECK + MINION), so make Yeti the ONLY minions in the deck.
    game = prepare_game()
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    for c in list(p1.deck):
        if c.type == CardType.MINION:
            c.zone = Zone.SETASIDE
    for _ in range(3):
        c = p1.card("CS2_182")
        c.zone = Zone.DECK
    _recombined_parent(p1, "CATA_820").play()
    drawn = [c for c in p1.hand if c.id == "CS2_182"]
    assert len(drawn) == 3
    for c in drawn:
        assert (c.atk, c.max_health) == (6, 7)  # base 4/5 + 2/2 (buffed in hand)
