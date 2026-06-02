"""Cataclysm — Priest (CATA_) unit tests."""

from utils import prepare_game
from hearthstone.enums import CardClass, CardType, Zone, GameTag, Race


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# CATA_216 Cleansing Cleric — Battlecry: your healing restores more this game.
# Engine approximation: HEALING_DOUBLE (doubler) rather than additive +2.
# ---------------------------------------------------------------------------
def test_cleansing_cleric_amplifies_healing():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    cleric = game.player1.give("CATA_216")
    cleric.play()
    # healing_double slot prop should now be 1 on the controller.
    assert game.player1.healing_double == 1
    # APPROXIMATION: we model "+2 healing this game" as HEALING_DOUBLE, which
    # the engine applies to SPELL healing. Holy Light (restore 6) now restores
    # 12, clearing 12 damage.
    game.player1.hero.damage = 12
    holy = game.player1.give("CS2_089")  # Holy Light: restore 6
    holy.play(target=game.player1.hero)
    assert game.player1.hero.damage == 0


def test_cleansing_cleric_stats():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    cleric = game.player1.summon("CATA_216")
    assert cleric.atk == 4 and cleric.health == 5


# ---------------------------------------------------------------------------
# CATA_304 Injured Attendant — Lifesteal Battlecry: deal 4 damage to itself.
# ---------------------------------------------------------------------------
def test_injured_attendant_self_damage_and_lifesteal():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.hero.damage = 5
    card = game.player1.give("CATA_304")
    card.play()
    # 3/8 took 4 self-damage -> damage == 4, still alive.
    assert card.damage == 4
    assert card.zone == Zone.PLAY
    # Lifesteal on the self-hit healed the hero for 4 (5 -> 1).
    assert game.player1.hero.damage == 1


# ---------------------------------------------------------------------------
# CATA_305 Incensed Matriarch — end of turn at full HP -> +3 Health.
# ---------------------------------------------------------------------------
def test_incensed_matriarch_buffs_at_full_health():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    m = game.player1.summon("CATA_305")
    assert m.health == 3
    game.end_turn()
    # At full health at end of turn -> +3 Health.
    assert m.health == 6
    assert m.max_health == 6


def test_incensed_matriarch_no_buff_when_damaged():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    m = game.player1.summon("CATA_305")
    m.damage = 1  # not at full health
    game.end_turn()
    assert m.max_health == 3
    assert m.damage == 1


# ---------------------------------------------------------------------------
# CATA_302 Mend — restore a minion to full Health, draw a card.
# ---------------------------------------------------------------------------
def test_mend_full_heal_and_draw():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    target = game.player1.summon("CATA_305")  # 3/3
    target.damage = 2
    pre_hand = len(game.player1.hand)
    spell = game.player1.give("CATA_302")
    spell.play(target=target)
    assert target.damage == 0
    assert len(game.player1.hand) == pre_hand + 1


# ---------------------------------------------------------------------------
# CATA_303 Purifying Breath — 5 damage to a minion; if it dies heal enemy 5.
# ---------------------------------------------------------------------------
def test_purifying_breath_kills_and_heals_enemy():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player2.hero.damage = 10
    victim = game.player2.summon("CATA_305")  # 3/3 -> dies to 5
    spell = game.player1.give("CATA_303")
    spell.play(target=victim)
    assert victim.zone == Zone.GRAVEYARD
    # Enemy hero healed 5 (10 -> 5).
    assert game.player2.hero.damage == 5


def test_purifying_breath_survives_no_heal():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player2.hero.damage = 10
    # Big minion survives 5 damage -> no heal.
    victim = game.player2.summon("CATA_307")  # 8/8 Alexstrasza
    spell = game.player1.give("CATA_303")
    spell.play(target=victim)
    assert victim.zone == Zone.PLAY
    assert victim.damage == 5
    assert game.player2.hero.damage == 10


# ---------------------------------------------------------------------------
# CATA_308 Medivh's Triumph — 4 damage to all minions; costs (1) with a Legendary.
# ---------------------------------------------------------------------------
def test_medivhs_triumph_board_wipe():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    a = game.player1.summon("CATA_305")  # 3/3 -> dies
    b = game.player2.summon("CATA_305")  # 3/3 -> dies
    big = game.player2.summon("CATA_307")  # 8/8 -> survives at damage 4
    spell = game.player1.give("CATA_308")
    spell.play()
    assert a.zone == Zone.GRAVEYARD
    assert b.zone == Zone.GRAVEYARD
    assert big.zone == Zone.PLAY and big.damage == 4


def test_medivhs_triumph_cost_with_legendary():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    spell = game.player1.give("CATA_308")
    assert spell.cost == 5
    # Control a Legendary (Alexstrasza is ELITE/Legendary).
    game.player1.summon("CATA_307")
    assert spell.cost == 1


# ---------------------------------------------------------------------------
# CATA_307 Alexstrasza, Guardian of Life — set own HP to 15; full HP -> 15 to foe.
# ---------------------------------------------------------------------------
def test_alexstrasza_sets_own_health_to_15():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # Hero starts at 30. Battlecry sets remaining health to 15 => damage 15.
    card = game.player1.give("CATA_307")
    card.play()
    assert game.player1.hero.health == 15
    assert game.player1.hero.damage == 15


def test_alexstrasza_reprisal_on_full_health():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    card = game.player1.give("CATA_307")
    card.play()
    assert game.player1.hero.health == 15
    # Heal back to full -> deal 15 to opponent.
    from fireplace.actions import Heal
    game.queue_actions(game.player1.hero, [Heal(game.player1.hero, 15)])
    assert game.player1.hero.damage == 0
    assert game.player2.hero.damage == 15


# ---------------------------------------------------------------------------
# CATA_301 Ruby Sanctum (location) — this turn, healing deals damage instead.
# ---------------------------------------------------------------------------
def test_ruby_sanctum_converts_healing_to_damage():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    loc = game.player1.summon("CATA_301")
    assert loc.type == CardType.LOCATION
    loc.use()
    assert game.player1.healing_as_damage
    # Now a "heal" on an enemy minion deals damage instead.
    enemy = game.player2.summon("CATA_307")  # 8/8
    from fireplace.actions import Heal
    game.queue_actions(game.player1.hero, [Heal(enemy, 4)])
    assert enemy.damage == 4
    # Expires at end of the controller's turn.
    game.end_turn()
    assert not game.player1.healing_as_damage


# ---------------------------------------------------------------------------
# CATA_300 The Black Blood (Colossal +3) — limbs summoned; heal -> body attacks.
# ---------------------------------------------------------------------------
def test_black_blood_colossal_summons_limbs():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    bb = game.player1.give("CATA_300")
    bb.play()
    bodies = [m for m in game.player1.field if m.id.startswith("CATA_300t")]
    # Colossal +3: three Black Blood's Body limbs.
    assert len(bodies) == 3
    assert all(m.atk == 1 and m.health == 2 for m in bodies)


def test_black_blood_limb_end_of_turn_heal():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    limb = game.player1.summon("CATA_300t1")  # 1/2 body
    # A damaged friendly target for the limb to heal.
    ally = game.player1.summon("CATA_307")  # 8/8
    ally.damage = 5
    game.end_turn()
    # End of (player1's) turn: limb restores 3 to the damaged ally.
    assert ally.damage == 2


def test_black_blood_attacks_on_heal():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # Summon only the parent body (no limbs) so it is the sole heal-trigger.
    body = game.player1.summon("CATA_300")  # 4/8 parent
    # Pass a full round so the body loses summoning sickness and can attack.
    game.end_turn()
    game.end_turn()
    assert body.can_attack()
    enemy = game.player2.summon("CS2_182")  # 4/5 Chillwind Yeti
    enemy.max_health = 80
    enemy.damage = 0
    from fireplace.actions import Heal
    # Heal our (damaged) hero -> the parent swings at the random enemy minion.
    game.player1.hero.damage = 5
    game.queue_actions(game.player1.hero, [Heal(game.player1.hero, 2)])
    # Parent (4 atk) hits the only enemy minion for 4.
    assert enemy.damage == 4


# ---------------------------------------------------------------------------
# CATA_306 Schism (Shatter) — half tokens.
# t1: give a friendly minion +2/+3 and Elusive.
# t2: summon a copy of a friendly minion.
# ---------------------------------------------------------------------------
def test_schism_half1_buff_and_elusive():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    target = game.player1.summon("CATA_305")  # 3/3
    half = game.player1.give("CATA_306t1")
    half.play(target=target)
    assert target.atk == 5 and target.health == 6
    # Elusive: untargetable by spells / hero powers.
    assert target.cant_be_targeted_by_abilities
    assert target.cant_be_targeted_by_hero_powers


def test_schism_half2_summon_copy():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    target = game.player1.summon("CATA_305")  # 3/3
    pre = len([m for m in game.player1.field if m.id == "CATA_305"])
    half = game.player1.give("CATA_306t2")
    half.play(target=target)
    post = len([m for m in game.player1.field if m.id == "CATA_305"])
    assert post == pre + 1


def test_schism_shatter_splits_on_draw():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # A SHATTER card splits into BOTH half-cards when DRAWN. The full card is
    # discarded and replaced. Schism uniquely names its halves CATA_306t1 /
    # CATA_306t2 (other SHATTER cards use <id>t / <id>t2); the splitter probes
    # all three suffixes so BOTH halves arrive — not just the copy half.
    from fireplace.actions import Draw
    card = game.player1.card("CATA_306")
    card.zone = Zone.DECK
    game.queue_actions(game.player1, [Draw(game.player1)])
    ids = [c.id for c in game.player1.hand]
    assert "CATA_306" not in ids
    assert "CATA_306t1" in ids
    assert "CATA_306t2" in ids


def _draw_schism_with_filler(game, player):
    """Draw Schism into a hand that already holds a Coin, so the split leaves
    the two halves apart: [t1 (left-most), Coin, t2]. Returns the Coin."""
    from fireplace.actions import Draw
    player.discard_hand()
    coin = player.give("GAME_005")  # The Coin — a filler between the halves
    sch = player.card("CATA_306")
    sch.zone = Zone.DECK
    game.queue_actions(player, [Draw(player)])
    return coin


def test_schism_halves_recombine_when_they_meet_in_hand():
    # Shatter recombine: once the two halves become ADJACENT in hand they merge
    # back into the full card (which then never Shatters again).
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    coin = _draw_schism_with_filler(game, p)
    ids = [c.id for c in p.hand]
    assert ids[0] == "CATA_306t1"          # one half goes left-most
    assert "CATA_306t2" in ids
    assert "CATA_306" not in ids           # apart -> still split
    # Play the Coin sitting between them -> the halves meet -> recombine.
    coin.play()
    ids = [c.id for c in p.hand]
    assert "CATA_306" in ids
    assert "CATA_306t1" not in ids and "CATA_306t2" not in ids
    parent = next(c for c in p.hand if c.id == "CATA_306")
    assert getattr(parent, "_no_reshatter", False) is True


def test_schism_recombine_combines_cost_reductions():
    # The user's scenario: one half is reduced to 0, the other stays at the
    # printed 4. The recombined card carries the discount -> costs 0, NOT 4
    # (combine merges the halves' cost reductions, it does not sum displayed
    # costs).
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    coin = _draw_schism_with_filler(game, p)
    t1 = next(c for c in p.hand if c.id == "CATA_306t1")
    assert t1.cost == 4
    t1._cost = 0                            # reduce this half to 0
    assert t1.cost == 0
    coin.play()                             # halves meet -> recombine
    parent = next(c for c in p.hand if c.id == "CATA_306")
    assert parent.cost == 0                 # printed 4 minus the 4 discount


def test_schism_shatters_when_generated_into_hand():
    # Shatter also fires on GENERATION (Discover / "get a card"), not only on
    # draw: a Schism handed to hand splits into its two halves.
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    p.discard_hand()
    p.give("CATA_306")  # generate the whole card into hand
    ids = sorted(c.id for c in p.hand)
    assert ids == ["CATA_306t1", "CATA_306t2"]
    assert "CATA_306" not in ids


def test_schism_recombined_card_never_shatters_again():
    # The permanent "won't Shatter again" marker survives a shuffle back into
    # the deck: re-drawing the recombined card yields the whole card, not halves.
    from fireplace.actions import Draw
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p = game.player1
    coin = _draw_schism_with_filler(game, p)
    coin.play()
    parent = next(c for c in p.hand if c.id == "CATA_306")
    parent.zone = Zone.DECK                 # shuffle it back
    game.queue_actions(p, [Draw(p)])
    ids = [c.id for c in p.hand]
    assert "CATA_306" in ids
    assert "CATA_306t1" not in ids and "CATA_306t2" not in ids


# ---------------------------------------------------------------------------
# CATA_002 Calia Menethil — Battlecry: resurrect highest-Cost dead minion.
# ---------------------------------------------------------------------------
def test_calia_menethil_stats():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    calia = game.player1.summon("CORE_CATA_002")
    assert calia.atk == 4 and calia.health == 5 and calia.cost == 6


def test_calia_resurrects_highest_cost_dead_minion():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    # Two friendly minions of clearly different Cost die this game.
    low = p1.summon("CATA_305")   # 3/3, cost 4
    high = p1.summon("CATA_307")  # 8/8 Alexstrasza, cost 7
    assert (low.data.cost or 0) < (high.data.cost or 0)
    low.destroy()
    high.destroy()
    assert low.zone == Zone.GRAVEYARD and high.zone == Zone.GRAVEYARD
    calia = p1.give("CORE_CATA_002")
    calia.play()
    # The highest-Cost dead minion (Alexstrasza) is resurrected; only one
    # non-Calia minion is now on the field, and it is CATA_307.
    resurrected = [m for m in p1.field if m is not calia]
    assert len(resurrected) == 1
    assert resurrected[0].id == "CATA_307"


def test_calia_no_dead_minions_does_nothing():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.discard_hand()
    calia = p1.give("CORE_CATA_002")
    calia.play()
    # Nothing in the graveyard -> only Calia on the field.
    assert [m for m in p1.field] == [calia]
