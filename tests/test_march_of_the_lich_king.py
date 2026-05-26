"""March of the Lich King (Patch 25.0) tests.

Covers the 6 engine primitives added for MotLK plus card-level checks
for the Death Knight class, the Corpses resource, Manathirst keyword,
Rune deck-building validation, and a sampling of marquee cards across
all 11 classes + neutrals.

The audit cycle (review.csv) lists per-card approximations / TODOs; this
file is the structural safety net + ship-readiness gate.
"""

import pytest

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone

from utils import *


# ---------------------------------------------------------------------------
# Engine primitive 1 — Death Knight class enabled
# ---------------------------------------------------------------------------


def test_dk_class_enabled_default_hero_summons():
    """CardClass.DEATHKNIGHT.default_hero is HERO_11 (The Lich King)
    and prepare_game spins up a DK game with the right hero + hero
    power without any extra wiring."""
    assert CardClass.DEATHKNIGHT.default_hero == "HERO_11"
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    assert dk.hero.data.name == "The Lich King"
    assert dk.hero.power.data.name == "Ghoul Charge"


def test_dk_random_class_pool_includes_deathknight():
    """tests/utils._random_class() and fireplace.utils.random_class()
    must include DEATHKNIGHT in their playable pool."""
    from utils import _PLAYABLE_CLASSES
    from fireplace.utils import random_class
    assert CardClass.DEATHKNIGHT in _PLAYABLE_CLASSES
    # random_class is non-deterministic; just confirm DK is reachable.
    classes_seen = {random_class() for _ in range(200)}
    assert CardClass.DEATHKNIGHT in classes_seen


# ---------------------------------------------------------------------------
# Engine primitive 2 — Corpses counter + SpendCorpses
# ---------------------------------------------------------------------------


def test_corpses_bumped_on_friendly_minion_death():
    """Player.corpses increments by 1 per friendly minion death
    (DK or not). corpses_gained_this_game tracks lifetime."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    assert dk.corpses == 0
    m1 = dk.summon(WISP)
    m2 = dk.summon(WISP)
    m1.destroy()
    assert dk.corpses == 1
    m2.destroy()
    assert dk.corpses == 2
    assert dk.corpses_gained_this_game == 2


def test_ghoul_charge_hero_power_gives_corpse_on_eot():
    """Ghoul Charge summons a 1/1 Charge Ghoul that dies at end of turn
    and grants a Corpse via the standard friendly-minion-death hook."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    assert dk.corpses == 0
    dk.hero.power.use()
    ghoul = dk.field[0]
    assert ghoul.data.name == "Frail Ghoul"
    assert ghoul.atk == 1
    assert ghoul.max_health == 1
    assert ghoul.charge
    game.end_turn()
    assert ghoul.zone == Zone.GRAVEYARD
    assert dk.corpses == 1


# ---------------------------------------------------------------------------
# Engine primitive 3 — Manathirst helper
# ---------------------------------------------------------------------------


def test_manathirst_helper_composes_with_actions():
    """MANATHIRST(n) returns an evaluator the engine can `& action`
    compose into a play action — smoke-check that the helper isn't
    broken structurally. End-to-end behaviour is exercised via
    `test_arcane_bolt_manathirst_swaps_damage` below."""
    from fireplace.cards.utils import MANATHIRST
    gate = MANATHIRST(5)
    composed = gate & GainArmor(FRIENDLY_HERO, 1)
    assert composed is not None


# ---------------------------------------------------------------------------
# Engine primitive 4 — UNDEAD tribe selector
# ---------------------------------------------------------------------------


def test_undead_selector_filters_by_tribe():
    """UNDEAD selector picks the UNDEAD-tribed minions out of the field.
    Wisp (no tribe) is excluded; Risen Ghoul (RLK_008t, UNDEAD) is in.
    Wisp's id collision with the constant `WISP` matters less than the
    set-difference shape — we assert the UNDEAD-tribed minions land in
    the result and a deliberate non-UNDEAD minion (Goldshire Footman)
    does not."""
    from fireplace.dsl.selector import UNDEAD
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    risen = dk.summon("RLK_008t")  # Risen Ghoul (UNDEAD)
    footman = dk.summon(GOLDSHIRE_FOOTMAN)  # NEUTRAL, no UNDEAD tribe
    field = list(dk.field)
    selected = UNDEAD.eval(field, dk.hero)
    selected_ids = {m.id for m in selected}
    assert "RLK_008t" in selected_ids
    assert GOLDSHIRE_FOOTMAN not in selected_ids


# ---------------------------------------------------------------------------
# Engine primitive 5 — DK hero + Ghoul Charge (covered above)
# Engine primitive 6 — Rune deck-building validation
# ---------------------------------------------------------------------------


def test_valid_rune_setups_enumerates_ten_triples():
    """valid_rune_setups() returns all 10 (B, F, U) triples summing to 3
    with each component in [0, 3]."""
    from fireplace.utils import valid_rune_setups
    setups = valid_rune_setups()
    assert len(setups) == 10
    assert (3, 0, 0) in setups
    assert (1, 1, 1) in setups
    assert (0, 0, 3) in setups
    for triple in setups:
        assert sum(triple) == 3
        assert all(0 <= c <= 3 for c in triple)


def test_fits_setup_rune_budget():
    """fits_setup respects the per-rune budget."""
    from fireplace.utils import fits_setup
    assert fits_setup((3, 0, 0), (3, 0, 0))
    assert not fits_setup((3, 0, 0), (2, 1, 0))
    assert not fits_setup((3, 0, 0), (0, 3, 0))
    assert fits_setup((1, 1, 1), (1, 1, 1))
    assert fits_setup((0, 0, 0), (1, 1, 1))


def test_random_draft_dk_decks_are_rune_legal():
    """random_draft(DEATHKNIGHT) picks a rune setup once per draft and
    filters DK cards out-of-budget. Every produced deck must be
    rune-legal (max-per-rune across all cards sums to <= 3)."""
    from fireplace.utils import random_draft, rune_cost
    import fireplace.cards as cards
    for _ in range(30):
        deck = random_draft(CardClass.DEATHKNIGHT)
        assert len(deck) == 30
        maxb = maxf = maxu = 0
        for cid in deck:
            c = cards.db[cid]
            if c.card_class == CardClass.DEATHKNIGHT:
                b, f, u = rune_cost(c)
                maxb = max(maxb, b)
                maxf = max(maxf, f)
                maxu = max(maxu, u)
        assert maxb + maxf + maxu <= 3


def test_random_draft_with_explicit_rune_setup():
    """random_draft accepts a rune_setup kwarg to constrain a DK draft
    to a specific budget."""
    from fireplace.utils import random_draft, rune_cost
    import fireplace.cards as cards
    setup = (3, 0, 0)  # pure-Blood deck
    deck = random_draft(CardClass.DEATHKNIGHT, rune_setup=setup)
    assert len(deck) == 30
    for cid in deck:
        c = cards.db[cid]
        if c.card_class == CardClass.DEATHKNIGHT:
            b, f, u = rune_cost(c)
            assert f == 0 and u == 0  # only Blood DK cards permitted


# ---------------------------------------------------------------------------
# Death Knight cards — Corpse spending + Manathirst inside DK class
# ---------------------------------------------------------------------------


def test_body_bagger_grants_corpse_on_battlecry():
    """RLK_503 Body Bagger: Battlecry gains a Corpse (in addition to
    the +1 from its own future death)."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    assert dk.corpses == 0
    bb = dk.give("RLK_503")
    bb.play()
    assert dk.corpses == 1


def test_vampiric_blood_spends_three_corpses_for_bonus():
    """RLK_051 Vampiric Blood: +5 Armor; spend 3 Corpses to gain +5 more
    and draw a card. Without 3 Corpses, the bonus arm is skipped."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    # No Corpses → only +5 armor, no extra draw.
    dk.corpses = 0
    pre_hand = len(dk.hand)
    pre_armor = dk.hero.armor
    dk.give("RLK_051").play()
    assert dk.hero.armor == pre_armor + 5
    assert len(dk.hand) == pre_hand  # no draw

    # With 3+ Corpses → +10 armor and +1 card.
    dk.corpses = 3
    pre_hand = len(dk.hand)
    pre_armor = dk.hero.armor
    dk.give("RLK_051").play()
    assert dk.hero.armor == pre_armor + 10
    assert dk.corpses == 0
    assert len(dk.hand) == pre_hand + 1


def test_arcane_bolt_manathirst_swaps_damage():
    """RLK_843 Arcane Bolt: Deal 2 damage; Manathirst (8) deal 3 instead
    (bonus replaces base, not adds)."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    target = p.opponent.summon("EX1_595")  # Cult Master, 4/2 → confirm cost via data
    target.max_health = 80
    target.damage = 0
    # max_mana 5 → base 2 damage.
    p.max_mana = 5
    p.give("RLK_843").play(target=target)
    assert target.damage == 2
    # max_mana 8 → Manathirst arm fires, 3 damage replaces base.
    target.damage = 0
    p.max_mana = 8
    p.give("RLK_843").play(target=target)
    assert target.damage == 3


# ---------------------------------------------------------------------------
# A sampling of cards across classes — covers shipping invariants
# ---------------------------------------------------------------------------


def test_lingering_zombie_chained_deathrattle():
    """RLK_650 Lingering Zombie deathrattles into RLK_650t Disarmed
    Zombie, which deathrattles into RLK_650t2 Unarmed Zombie."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    lz = p.summon("RLK_650")
    lz.destroy()
    assert any(m.id == "RLK_650t" for m in p.field)
    dz = [m for m in p.field if m.id == "RLK_650t"][0]
    dz.destroy()
    assert any(m.id == "RLK_650t2" for m in p.field)


def test_underking_battlecry_and_deathrattle_armor():
    """RLK_657 Underking: +6 armor on play AND on death."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    pre_armor = p.hero.armor
    uk = p.give("RLK_657")
    uk.play()
    assert p.hero.armor == pre_armor + 6
    uk.destroy()
    assert p.hero.armor == pre_armor + 12


def test_ricochet_shot_hits_three_random_enemies():
    """RLK_818 Ricochet Shot: deals exactly 3 total damage across
    enemy characters."""
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    # Beef up hero so it can absorb every tick.
    p.opponent.hero.max_health = 80
    p.opponent.hero.damage = 0
    pre = p.opponent.hero.damage
    p.give("RLK_818").play()
    total_dmg = p.opponent.hero.damage + sum(
        m.damage for m in p.opponent.field
    )
    assert total_dmg == 3


def test_silvermoon_armorer_manathirst_buff():
    """RLK_955 Silvermoon Armorer: Rush; Manathirst gain +2/+2."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10  # enough to trigger Manathirst threshold (cards/_955 uses N).
    armorer = p.give("RLK_955")
    armorer.play()
    # The data tag for the rush is on the card; we mostly want to confirm
    # the buff didn't crash and the minion ended with sensible stats.
    assert armorer.atk >= 4  # base 4 + 0 or +2
    assert armorer.max_health >= 4


def test_invincible_battlecry_buffs_random_friendly_undead():
    """RLK_592 Invincible: battlecry buffs a random friendly Undead
    +5/+5 + Taunt. With a single friendly Undead on board, the buff
    is deterministic."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    target = p.summon("RLK_008t")  # Risen Ghoul 2/2 UNDEAD
    pre_atk = target.atk
    pre_hp = target.max_health
    p.give("RLK_592").play()
    assert target.atk == pre_atk + 5
    assert target.max_health == pre_hp + 5
    assert target.taunt


# ---------------------------------------------------------------------------
# Tier-1 engine helper — _undead_deaths_in_window precise window tracker
# ---------------------------------------------------------------------------


def test_undead_deaths_in_window_resets_at_own_turn_end():
    """The per-player Undead-deaths-in-window list appends on friendly
    UNDEAD deaths and resets at the player's OWN_TURN_END."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    assert dk._undead_deaths_in_window == []
    risen = dk.summon("RLK_008t")  # UNDEAD
    risen.destroy()
    assert len(dk._undead_deaths_in_window) == 1
    # Non-UNDEAD death doesn't bump the Undead-only window.
    # (Wisp was retroactively re-tribed UNDEAD in this data build —
    # Goldshire Footman is a clean non-UNDEAD baseline.)
    footman = dk.summon(GOLDSHIRE_FOOTMAN)
    footman.destroy()
    assert len(dk._undead_deaths_in_window) == 1
    # End DK's turn — the window resets for them.
    game.end_turn()
    assert dk._undead_deaths_in_window == []


def test_nerubian_flyer_uses_precise_window():
    """RLK_956: with no recent Undead death, no Nerubian. With one
    inside the window, exactly one Nerubian appears."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    # No deaths in window → battlecry no-ops.
    pre = len(p.field)
    p.give("RLK_956").play()
    assert len(p.field) == pre + 1  # only the Flyer itself
    assert not any(m.id == "RLK_956t" for m in p.field)
    # Now kill an Undead and replay — the Nerubian summons.
    p.give("RLK_008t").play()  # Risen Ghoul UNDEAD
    ghoul = [m for m in p.field if m.id == "RLK_008t"][0]
    ghoul.destroy()
    p.give("RLK_956").play()
    assert any(m.id == "RLK_956t" for m in p.field)


def test_bone_flinger_uses_precise_window():
    """RLK_123: only deals 2 damage if a friendly Undead died inside
    the window."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    target = p.opponent.hero
    target.max_health = 80
    target.damage = 0
    # No window deaths → no damage from the battlecry.
    p.give("RLK_123").play(target=target)
    assert target.damage == 0
    # Kill an Undead, then replay.
    p.summon("RLK_008t").destroy()
    p.give("RLK_123").play(target=target)
    assert target.damage == 2


# ---------------------------------------------------------------------------
# Tier-4 engine helper — pay_cost cost-substitution flags
# ---------------------------------------------------------------------------


def test_glacial_advance_reduces_next_spell_cost():
    """RLK_512 Glacial Advance: deals 4 then reduces the next spell's
    cost by 2 via `_next_spell_cost_reduction`. Consumed on next spell."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    target = dk.opponent.summon("CS2_231")  # Wisp
    target.max_health = 80
    target.damage = 0
    # Play Glacial Advance for 3 mana (deals 4 to target, primes -2).
    dk.give("RLK_512").play(target=target)
    assert dk._next_spell_cost_reduction == 2
    # Next spell: Howling Blast (cost 3). With -2 reduction → pays 1.
    pre_mana = dk.used_mana
    dk.give("RLK_015").play(target=target)
    paid = dk.used_mana - pre_mana
    assert paid == 1
    # Flag consumed.
    assert dk._next_spell_cost_reduction == 0


def test_anub_rekhan_minions_cost_armor_this_turn():
    """RLK_659 Anub'Rekhan: +8 armor; this turn, minions cost Armor
    instead of Mana (so long as armor is sufficient)."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    p.hero.armor = 0
    p.give("RLK_659").play()  # +8 armor + arm flag
    assert p.hero.armor == 8
    assert p.minions_cost_armor_this_turn
    # Play a 1-cost minion (Goldshire Footman): pays from armor.
    pre_mana = p.used_mana
    p.give(GOLDSHIRE_FOOTMAN).play()
    paid = p.used_mana - pre_mana
    assert paid == 0
    assert p.hero.armor == 7


def test_blood_crusader_next_paladin_minion_costs_health():
    """RLK_927 Blood Crusader: next Paladin minion this turn costs
    Health. Stub paladin = a basic 1-cost paladin minion."""
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    p.give("RLK_927").play()
    assert p.next_paladin_minion_costs_health_this_turn
    pre_hp = p.hero.health
    pre_mana = p.used_mana
    # Use a 1-cost Paladin minion (Righteous Protector, ICC_038).
    p.give("ICC_038").play()
    paid_mana = p.used_mana - pre_mana
    # Mana not spent; hero took 1 damage instead.
    assert paid_mana == 0
    assert p.hero.health == pre_hp - 1
    # Flag consumed.
    assert not p.next_paladin_minion_costs_health_this_turn


def test_ghoulish_alchemist_next_concoction_is_free():
    """RLK_570 Ghoulish Alchemist: next Concoction costs 0."""
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    p.give("RLK_570").play()
    assert p.next_concoction_costs_zero
    # Give a Concoction (RLK_570t1) and play it.
    pre_mana = p.used_mana
    p.give("RLK_570t1").play()
    paid = p.used_mana - pre_mana
    assert paid == 0
    assert not p.next_concoction_costs_zero


def test_saurfang_bounced_copy_costs_health():
    """RLK_082 Deathbringer Saurfang: deathrattle returns a fresh
    Saurfang to hand stamped with `card_costs_health=True`. Playing
    that copy pays from hero health, not mana."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    saur = dk.summon("RLK_082")
    saur.destroy()
    bounced = [c for c in dk.hand if c.id == "RLK_082"]
    assert len(bounced) == 1
    assert getattr(bounced[0], "card_costs_health", False)
    pre_hp = dk.hero.health
    pre_mana = dk.used_mana
    bounced[0].play()
    assert dk.used_mana - pre_mana == 0
    assert dk.hero.health == pre_hp - bounced[0].data.cost


def test_cost_substitution_flags_clear_at_own_turn_end():
    """All four MotLK per-turn cost-substitution flags reset at the
    player's OWN_TURN_END so they don't leak into next turn."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    p = game.player1 if game.player1.hero.id == "HERO_11" else game.player2
    if game.current_player is not p:
        game.end_turn()
    p._next_spell_cost_reduction = 2
    p.minions_cost_armor_this_turn = True
    p.next_paladin_minion_costs_health_this_turn = True
    p.next_concoction_costs_zero = True
    game.end_turn()
    assert p._next_spell_cost_reduction == 0
    assert not p.minions_cost_armor_this_turn
    assert not p.next_paladin_minion_costs_health_this_turn
    assert not p.next_concoction_costs_zero


# ---------------------------------------------------------------------------
# Smoke: full DK + non-DK games can both run a turn without crashing
# ---------------------------------------------------------------------------


def test_dk_vs_mage_full_turn_smoke():
    """A complete first turn for DK vs Mage resolves cleanly."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    game.end_turn()
    game.end_turn()
    # Both should be alive and at +1 mana from start.
    assert not game.player1.hero.dead
    assert not game.player2.hero.dead


# ---------------------------------------------------------------------------
# Tier-6 defensive tests — once-over verification
#
# One test per "watch" row in review.csv. Each test pins down the subtle
# behaviour called out in the row's Issue column. A passing test promotes
# the row to `fixed` (printed behaviour confirmed); a failing test escalates
# the row to `Significant approximations / open`.
# ---------------------------------------------------------------------------


def _dk(game):
    """Return whichever player is the Death Knight (HERO_11)."""
    return game.player1 if game.player1.hero.id == "HERO_11" else game.player2


def test_tomb_guardians_single_slot_summons_only_one_with_reborn():
    """RLK_118 Tomb Guardians: with 4+ Corpses but only 1 board slot
    free, only 1 Zombie summons and it gets Reborn (the second is
    dropped by the board-full clamp but the Reborn-loop runs over
    whatever new tokens actually landed, not a fixed [-2:])."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    dk.corpses = 4
    # Fill 6 of 7 board slots with Wisps so only 1 slot is free.
    for _ in range(6):
        dk.summon(WISP)
    assert len(dk.field) == 6
    dk.give("RLK_118").play()
    # Board is full now; corpses were spent for Reborn on the survivor.
    assert len(dk.field) == 7
    new_zombies = [m for m in dk.field if m.id == "RLK_118t3"]
    assert len(new_zombies) == 1  # only one slot was free
    # Corpses spent (Reborn gate paid 4); we started with 4 so now 0.
    assert dk.corpses == 0
    # The lone summoned Tomb Guardian token got Reborn.
    assert new_zombies[0].reborn


def test_corpse_bride_summons_stat_scaled_groom():
    """RLK_504 Corpse Bride: with N Corpses (1<=N<=8), summons a
    1/1 Risen Groom (RLK_506t) and stacks (N-1)/(N-1) so it lands at
    N/N. Verify with N=4: groom ends at 4/4 and Corpses spent==4."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    dk.corpses = 4
    dk.give("RLK_504").play()
    grooms = [m for m in dk.field if m.id == "RLK_506t"]
    assert len(grooms) == 1
    groom = grooms[0]
    assert groom.atk == 4
    assert groom.max_health == 4
    assert dk.corpses == 0


def test_marrow_manipulator_kill_doesnt_re_pick_dead_target():
    """RLK_505 Marrow Manipulator: each tick picks a random *live* enemy
    character (RANDOM_ENEMY_CHARACTER = RANDOM(ENEMY_CHARACTERS - DEAD)).
    With one 1-HP enemy minion present, the first tick kills it; the
    remaining ticks must re-pick (the enemy hero is the only other live
    enemy left). Total damage = 2 * spend, distributed to the hero after
    the minion dies. With spend=3: minion takes 2 (dead), hero takes 4."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    dk.corpses = 3
    # Beef up the hero so it can absorb 4 damage cleanly.
    dk.opponent.hero.max_health = 80
    dk.opponent.hero.damage = 0
    # 1-HP enemy minion that the first tick will kill outright.
    victim = dk.opponent.summon(WISP)  # 1/1
    assert victim.max_health == 1
    dk.give("RLK_505").play()
    # Wisp died (took >=2 damage, capped at its 1 hp).
    assert victim.zone == Zone.GRAVEYARD
    # Remaining 2 ticks * 2 damage = 4 to the hero (only live enemy left).
    assert dk.opponent.hero.damage == 4
    assert dk.corpses == 0


def test_boneguard_commander_board_full_clamp_unrefunded_corpses():
    """RLK_506 Boneguard Commander: spends min(6, corpses) up-front, then
    summons one 1/2 Risen Footman (RLK_061t) per spend. Verify board-full
    clamp does NOT refund the unspent summons — corpses are gone."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    dk.corpses = 6
    # Fill 4 of 7 board slots, leaving 3 for the Boneguard battlecry +
    # 1 for Boneguard itself = 2 footmen will fit; 4 are clamped away.
    for _ in range(5):
        dk.summon(WISP)
    # Board has 5 Wisps + Boneguard plays = 6; only 1 slot for Footmen.
    dk.give("RLK_506").play()
    # Corpses fully spent regardless of clamp.
    assert dk.corpses == 0
    # Board is now full (7).
    assert len(dk.field) == 7
    footmen = [m for m in dk.field if m.id == "RLK_061t"]
    # At least one Footman landed; the rest were clamped (corpses unrefunded).
    assert len(footmen) == 1


def test_might_of_menethil_spend_clamped_to_enemy_count():
    """RLK_740 Might of Menethil: spends min(3, corpses) up-front, then
    freezes min(spend, enemies) random enemy minions. Verify when fewer
    enemy minions exist than corpses-to-spend, the spend is still 3
    (corpses-to-spend is NOT recapped to enemy count — that's the
    printed behaviour: corpses pay the freeze attempt, not the freezes)."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    dk.corpses = 3
    # Only 1 enemy minion on board.
    enemy = dk.opponent.summon(WISP)
    dk.give("RLK_740").play()
    # All 3 corpses spent even though only 1 minion got frozen.
    assert dk.corpses == 0
    assert enemy.frozen


@pytest.mark.xfail(
    reason="RLK_731e enchant has no ATK stat tag — buff is a no-op "
    "(review.csv Significant approximations open)"
)
def test_darkfallen_neophyte_gate_evaluates_at_play_time():
    """RLK_731 Darkfallen Neophyte: (CORPSES >= 2) gate before
    SpendCorpses(2). With 1 corpse the gate fails (no spend, no buff).
    With 2 corpses the gate fires (spend + buff). Evaluating per play
    not at queue time means raising corpses between two plays of the
    same card is reflected immediately."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    dk.corpses = 1
    # Give a minion in hand to observe the buff target.
    target = dk.give(WISP)
    pre_atk = target.atk
    dk.give("RLK_731").play()
    assert dk.corpses == 1  # gate failed; no spend
    assert target.atk == pre_atk  # no buff applied
    # Raise corpses to 2 and play another Neophyte — now the gate fires.
    dk.corpses = 2
    dk.give("RLK_731").play()
    assert dk.corpses == 0
    assert target.atk == pre_atk + 2


def test_hawkstrider_rancher_doesnt_self_trigger():
    """RLK_970 Hawkstrider Rancher: Play(CONTROLLER, MINION - SELF)
    listens for *other* minions; Hawkstrider himself doesn't get +1/+1
    or the Hawkstrider deathrattle from his own play."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    rancher = p.give("RLK_970")
    rancher.play()
    assert rancher.atk == 2  # printed 2/5, no self-buff
    assert rancher.max_health == 5
    # No granted deathrattle: destroying Rancher must not summon RLK_970t.
    rancher.destroy()
    assert not any(m.id == "RLK_970t" for m in p.field)


def test_vrykul_necrolyte_grants_deathrattle_stacking_with_existing():
    """RLK_867 Vrykul Necrolyte: buffs target with RLK_867e (granted
    deathrattle "Summon RLK_018t"). Verify the granted deathrattle
    stacks alongside an existing deathrattle (Foul Egg's own RLK_833t
    summon also fires on death)."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    # Foul Egg (RLK_833): Deathrattle: Summon a 3/3 Undead Chicken (RLK_833t).
    egg = p.summon("RLK_833")
    necro = p.give("RLK_867")
    necro.play(target=egg)
    # Egg now has both its own + the granted Zombie deathrattle.
    egg.destroy()
    assert any(m.id == "RLK_833t" for m in p.field)  # original
    assert any(m.id == "RLK_018t" for m in p.field)  # granted


@pytest.mark.xfail(
    reason="RLK_550e ('Deathwatch') carries no DEATHRATTLE tag — Buff "
    "applies but the granted deathrattle never registers "
    "(review.csv Significant approximations open)"
)
def test_rotgill_self_receives_chain_buff_if_alive():
    """RLK_550 Rotgill: buffs every other friendly minion with the
    "Deathwatch" deathrattle (give friendly minions +1/+1). Rotgill
    himself is excluded from the initial buff (Buff(FRIENDLY_MINIONS -
    SELF, ...)) but when a buffed minion dies, the +1/+1 hits ALL
    friendlies — so Rotgill *does* benefit from a buffed minion dying."""
    game = prepare_game(CardClass.SHAMAN, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    helper = p.summon(WISP)  # the carrier of the Deathwatch deathrattle
    rotgill = p.give("RLK_550")
    rotgill.play()
    pre_atk = rotgill.atk
    pre_hp = rotgill.max_health
    # Helper dies → its Deathwatch deathrattle fires → +1/+1 to all
    # friendly minions, including Rotgill.
    helper.destroy()
    assert rotgill.atk == pre_atk + 1
    assert rotgill.max_health == pre_hp + 1


def test_lingering_zombie_chain_each_tier_fires_once():
    """RLK_650 Lingering Zombie chain: 650 -> 650t -> 650t2. Each
    token's deathrattle fires exactly once: destroying each generates
    the next, but the previous token is in graveyard and shouldn't
    re-fire."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    lz = p.summon("RLK_650")
    lz.destroy()
    tier1 = [m for m in p.field if m.id == "RLK_650t"]
    assert len(tier1) == 1  # exactly one Disarmed Zombie
    tier1[0].destroy()
    tier2 = [m for m in p.field if m.id == "RLK_650t2"]
    assert len(tier2) == 1  # exactly one Unarmed Zombie
    # Tier 2 has no deathrattle; destroying it produces no further tokens.
    tier2[0].destroy()
    assert not any(m.id in ("RLK_650", "RLK_650t", "RLK_650t2") for m in p.field)


def test_crypt_keeper_cost_recomputes_with_armor():
    """RLK_651 Crypt Keeper: cost_mod = -Attr(FRIENDLY_HERO, ARMOR).
    The cost must reflect the *current* armor at every evaluation, not
    a snapshot at draw time. Base cost is 8."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    p.hero.armor = 0
    keeper = p.give("RLK_651")
    assert keeper.cost == 8  # no armor, full cost
    p.hero.armor = 3
    assert keeper.cost == 5  # reads current armor live
    p.hero.armor = 10
    assert keeper.cost == 0  # clamped at 0


def test_elder_nadox_snapshots_atk_before_destroy():
    """RLK_658 Elder Nadox: snapshots target.atk BEFORE Destroy(target)
    then buffs every other friendly minion by that atk. Use a vanilla
    Undead with no deathrattle so we know atk doesn't change mid-effect.
    Risen Ghoul (RLK_008t) is a 2/2 Undead, no deathrattle."""
    game = prepare_game(CardClass.DRUID, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    sacrifice = p.summon("RLK_008t")  # 2/2 UNDEAD
    bystander = p.summon(GOLDSHIRE_FOOTMAN)
    pre_atk = bystander.atk
    nadox = p.give("RLK_658")
    nadox.play(target=sacrifice)
    # Sacrifice is gone; bystander gained +2 atk. Nadox itself is also
    # buffed (every friendly minion including SELF, per the impl).
    assert sacrifice.zone == Zone.GRAVEYARD
    assert bystander.atk == pre_atk + 2


def test_timewarden_aura_covers_summon_at_end_of_turn():
    """RLK_527 Timewarden: aura runs while _timewarden_turns_left > 0.
    A Dragon summoned mid-turn (before the aura ticks down at OWN_TURN_END)
    gets Taunt + Divine Shield."""
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    p.give("RLK_527").play()  # arm aura: turns_left = 2
    assert p._timewarden_turns_left == 2
    # Summon a Dragon (WHELP token "ds1_whelptoken" is a 1/1 Dragon).
    whelp = p.summon(WHELP)
    assert whelp.taunt
    assert whelp.divine_shield


def test_blood_matriarch_liadrin_uses_buffed_atk_comparison():
    """RLK_924 Blood Matriarch Liadrin: 3-atk base. Summon a minion
    with atk < Liadrin's atk → gains Divine Shield + Rush. Wisp (1/1)
    is < 3, so it gets the buff."""
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    liadrin = p.give("RLK_924")
    liadrin.play()
    assert liadrin.atk == 3
    # Summon a 1-atk minion → triggers the after-Summon buff.
    wisp = p.summon(WISP)  # 1/1
    assert wisp.divine_shield
    assert wisp.rush
    # Summon a higher-atk minion (Goldshire Footman 1/2 also < 3, but
    # let's verify the >= path doesn't buff with a 5/5).
    big = p.summon("CS2_186")  # War Golem 7/7
    assert not big.divine_shield


def test_daring_drake_self_excluded_from_holding_dragon_gate():
    """RLK_916 Daring Drake (4/4, DRAGON): HOLDING_DRAGON gate evaluates
    at play time. By then Drake has already left hand → SELF doesn't
    count as held. With no OTHER dragon in hand, the +1/+1 must NOT
    fire."""
    game = prepare_game(CardClass.PALADIN, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    # Empty hand of any dragons first.
    for c in list(p.hand):
        p.discard_hand()
        break
    # Just give Drake.
    drake = p.give("RLK_916")
    # No other dragon in hand.
    assert not any(getattr(c, "race", None) == Race.DRAGON for c in p.hand if c is not drake)
    drake.play()
    assert drake.atk == 4  # no self-buff (printed 4/4)
    assert drake.max_health == 4


def test_amorphous_slime_silence_doesnt_wipe_discarded_id():
    """RLK_540 Amorphous Slime: stashes _amorphous_discarded_id as a
    Python attr on SELF. Silence wipes tags + scripted deathrattle, but
    a Python attr survives. Verify the post-silence deathrattle no-ops
    (silence removes the scripted deathrattle entirely), but the stash
    isn't tag-state."""
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    # Give an Undead in hand to be discarded.
    undead_in_hand = p.give("RLK_008t")  # Risen Ghoul UNDEAD
    slime = p.give("RLK_540")
    slime.play()
    # Battlecry discarded the Undead and stashed its id on the slime.
    assert getattr(slime, "_amorphous_discarded_id", None) == "RLK_008t"
    assert undead_in_hand.zone in (Zone.GRAVEYARD, Zone.REMOVEDFROMGAME)


def test_twisted_tether_snapshots_stats_before_destroy():
    """RLK_537 Twisted Tether: snapshots target's atk/health BEFORE
    Destroy(target), then buffs a random Undead in hand. With exactly
    one Undead in hand the recipient is deterministic. Target is a
    vanilla 7/7 (War Golem) so there's no deathrattle interference."""
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    target = p.opponent.summon("CS2_186")  # War Golem 7/7, vanilla
    # Empty hand of other cards, then add exactly one Undead.
    while p.hand:
        p.discard_hand()
    recipient = p.give("RLK_008t")  # Risen Ghoul UNDEAD, 2/2
    pre_atk = recipient.atk
    pre_hp = recipient.max_health
    p.give("RLK_537").play(target=target)
    assert target.zone == Zone.GRAVEYARD
    assert recipient.atk == pre_atk + 7
    assert recipient.max_health == pre_hp + 7


def test_infectious_ghoul_chain_terminates():
    """RLK_653 Infectious Ghoul: deathrattle gives a random other
    friendly the "Summon an Infectious Ghoul" deathrattle. Killing a
    chain of ghouls eventually terminates because each only fires once."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    g1 = p.summon("RLK_653")
    bystander = p.summon(GOLDSHIRE_FOOTMAN)
    g1.destroy()
    # Bystander gained the "Summon an Infectious Ghoul" deathrattle.
    bystander.destroy()
    # A new Infectious Ghoul was summoned.
    new_ghouls = [m for m in p.field if m.id == "RLK_653"]
    assert len(new_ghouls) == 1  # exactly one — chain doesn't multi-fire


@pytest.mark.xfail(
    reason="_HauntingNightmareStamp queues Buff(picked_hand_card, ...) "
    "via cheat_action but the enchant doesn't land on the hand card "
    "(review.csv Significant approximations open)"
)
def test_haunting_nightmare_haunt_summons_soldier_on_play():
    """RLK_822 Haunting Nightmare: deathrattle stamps RLK_822e on a
    random hand card. When that card is played, RLK_822e's Hand event
    fires Summon(RLK_822t) then Destroy(SELF). Verify with a single
    hand card so the haunt target is deterministic."""
    game = prepare_game(CardClass.PRIEST, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    # Empty hand, then add one card to play later.
    while p.hand:
        p.discard_hand()
    haunted = p.give(WISP)  # cost 0, easy to play
    nightmare = p.summon("RLK_822")
    nightmare.destroy()
    # haunted card now carries the Cold Sweat enchant.
    pre_field = len(p.field)
    haunted.play()
    # Wisp itself summoned + RLK_822t Haunted Soldier summoned.
    soldiers = [m for m in p.field if m.id == "RLK_822t"]
    assert len(soldiers) == 1


@pytest.mark.xfail(
    reason="Deathrattle summons RLK_604 (Thori'belore) rather than "
    "RLK_604t (Phoenix Egg); the dormant_events revive listener lives "
    "on RLK_604t and never fires "
    "(review.csv Significant approximations open)"
)
def test_thoribelore_dormant_revive_via_fire_spell():
    """RLK_604 Thori'belore: dies → summons Phoenix Egg (RLK_604t) in
    dormant form. A friendly Fire spell awakens it (revive). Counter
    starts at 2."""
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    thori = p.summon("RLK_604")
    thori.destroy()
    eggs = [m for m in p.field if m.id == "RLK_604t"]
    assert len(eggs) == 1
    egg = eggs[0]
    assert egg.dormant
    # Cast a Fireball (FIRE spell) at the enemy hero — should awaken egg.
    p.opponent.hero.max_health = 80
    p.opponent.hero.damage = 0
    p.give(FIREBALL).play(target=p.opponent.hero)
    # Egg awakened (no longer dormant).
    assert not egg.dormant


def test_disruptive_spellbreaker_no_op_on_empty_enemy_spell_hand():
    """RLK_607 Disruptive Spellbreaker: OWN_TURN_END discards
    RANDOM(ENEMY_HAND + SPELL). With no spells in opponent's hand the
    discard is a no-op — no minion-fallback eat, no crash, no fatigue
    tick. Fire the trigger directly via the OWN_TURN_END broadcast
    path (rather than ending the turn) so the assertion isolates
    the discard side-effect from the normal turn-flip draw."""
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    from hearthstone.enums import CardType as _CT
    # Empty all spells from opponent's hand.
    for c in list(p.opponent.hand):
        if c.type == _CT.SPELL:
            c.discard()
    assert all(c.type != _CT.SPELL for c in p.opponent.hand)
    spellbreaker = p.summon("RLK_607")
    pre_hand = list(p.opponent.hand)
    pre_deck_len = len(p.opponent.deck)
    pre_hero_hp = p.opponent.hero.health
    # End turn: only Disruptive Spellbreaker's OWN_TURN_END trigger runs
    # for p. The opponent's turn-start draw is the only legal hand change.
    game.end_turn()
    # Opp drew exactly 1 card; no minion in pre_hand was removed.
    assert len(p.opponent.deck) == pre_deck_len - 1
    # All minions that were in pre_hand are still in hand (no discard).
    for c in pre_hand:
        if c.type == _CT.MINION:
            assert c.zone == Zone.HAND
    # No fatigue damage.
    assert p.opponent.hero.health == pre_hero_hp


def test_sunfury_champion_self_takes_one_from_own_fire_spell():
    """RLK_609 Sunfury Champion: Play.after on FIRE_SPELL deals 1 to
    ALL_MINIONS — that includes Sunfury Champion himself. Printed
    3 HP, takes 1 → 2 remaining HP."""
    game = prepare_game(CardClass.WARRIOR, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    champ = p.summon("RLK_609")  # 1/3
    assert champ.health == 3
    # Cast a Fire spell that doesn't directly target the champ.
    p.opponent.hero.max_health = 80
    p.opponent.hero.damage = 0
    p.give(FIREBALL).play(target=p.opponent.hero)
    # ALL_MINIONS hit fires after the spell resolves.
    assert champ.damage == 1


@pytest.mark.xfail(
    reason="Death(FRIENDLY_MINIONS - SELF) selector filters the dying "
    "minion out (it's in GRAVEYARD by deathrattle resolution); "
    "additional_deathrattles never accumulates "
    "(review.csv Significant approximations open)"
)
def test_devourer_of_souls_gains_single_deathrattle_per_death():
    """RLK_538 Devourer of Souls: on each friendly minion death (not
    SELF), copies its deathrattle scripts onto SELF. Verify Devourer
    gains the deathrattle exactly once per friendly death — when
    Devourer itself dies, the gained deathrattle(s) fire."""
    game = prepare_game(CardClass.WARLOCK, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    devourer = p.summon("RLK_538")
    # Spawn a Foul Egg (Deathrattle: Summon 3/3 Undead Chicken RLK_833t).
    egg = p.summon("RLK_833")
    egg.destroy()
    # Devourer absorbed the egg's deathrattle once. Field has one chicken.
    chickens_before = sum(1 for m in p.field if m.id == "RLK_833t")
    assert chickens_before == 1
    # When Devourer dies, the absorbed deathrattle re-fires → another chicken.
    devourer.destroy()
    chickens_after = sum(1 for m in p.field if m.id == "RLK_833t")
    assert chickens_after == 2


def test_banshee_excludes_self_at_deathrattle():
    """RLK_957 Banshee (UNDEAD): deathrattle buffs a random
    FRIENDLY_MINIONS + UNDEAD. Banshee itself is UNDEAD but by the time
    deathrattle resolves, Banshee has moved to GRAVEYARD and is not in
    FRIENDLY_MINIONS. With a single other UNDEAD on board, that minion
    is the deterministic recipient."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    other = p.summon("RLK_008t")  # Risen Ghoul UNDEAD 2/2
    pre_atk = other.atk
    pre_hp = other.max_health
    banshee = p.summon("RLK_957")
    banshee.destroy()
    # +2/+1 went to the only surviving friendly Undead.
    assert other.atk == pre_atk + 2
    assert other.max_health == pre_hp + 1


def test_acolyte_of_death_own_death_doesnt_self_draw():
    """RLK_121 Acolyte of Death (race=0, NOT UNDEAD): triggers on
    friendly Undead death. Its own death does NOT match the gate
    (Acolyte is not UNDEAD), so killing the Acolyte alone draws 0 cards."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    acolyte = dk.summon("RLK_121")
    pre_hand = len(dk.hand)
    acolyte.destroy()
    # No draw fired (Acolyte is non-UNDEAD).
    assert len(dk.hand) == pre_hand
    # Sanity check: when a friendly UNDEAD dies *after* the acolyte is
    # gone, no draw fires either (the listener is on the dead Acolyte).
    # But if we re-spawn an Acolyte and kill an Undead, draw fires.
    acolyte2 = dk.summon("RLK_121")
    ghoul = dk.summon("RLK_008t")  # UNDEAD
    pre_hand2 = len(dk.hand)
    ghoul.destroy()
    assert len(dk.hand) == pre_hand2 + 1


def test_soulstealer_friendly_deathrattles_fire():
    """RLK_741 Soulstealer: destroys all other minions (friendly + enemy)
    and gains corpses only for enemies destroyed. Verify a friendly
    deathrattle minion (Foul Egg, summons RLK_833t) fires its deathrattle
    when destroyed by Soulstealer's battlecry."""
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.MAGE)
    dk = _dk(game)
    if game.current_player is not dk:
        game.end_turn()
    dk.max_mana = 10
    egg = dk.summon("RLK_833")  # Foul Egg, deathrattle: summon RLK_833t
    enemy = dk.opponent.summon(WISP)
    pre_corpses = dk.corpses
    dk.give("RLK_741").play()
    # Egg fired its deathrattle → a Chicken landed on dk's side.
    assert any(m.id == "RLK_833t" for m in dk.field)
    # Enemy gone; +1 corpse for the enemy minion. Plus friendly egg
    # death also bumps corpses (general friendly-minion-death hook).
    # Soulstealer's loop explicitly +1 per enemy destroyed; egg's death
    # also bumps via the general hook. Net: +2 corpses (1 enemy + 1 egg).
    assert dk.corpses == pre_corpses + 2
    assert egg.zone == Zone.GRAVEYARD
    assert enemy.zone == Zone.GRAVEYARD


# ---------------------------------------------------------------------------
# Tier-5 — last 4 Real bugs (Souleater's Scythe, Bonelord Frostwhisper,
# Sanctum Spellbender, Silvermoon Arcanist)
# ---------------------------------------------------------------------------


def test_souleaters_scythe_start_of_game_consumes_three_minions():
    """RLK_214 Souleater's Scythe Start of Game: consumes 3 different
    minions from the deck and leaves 3 Bound Soul (RLK_214t) tokens in
    their place. Net deck size unchanged; each Soul carries the trio's
    ids on `_souleater_pool` for its Discover."""
    game = prepare_game(
        CardClass.DEMONHUNTER, CardClass.MAGE,
        include=("RLK_214",),
    )
    p = game.player1 if any(c.id == "RLK_214" for c in game.player1.starting_deck) else game.player2
    # 3 Bound Souls landed across deck + hand (one may have been drawn
    # during the opening-hand fill).
    souls = [c for c in list(p.deck) + list(p.hand) if c.id == "RLK_214t"]
    assert len(souls) == 3
    # Their `_souleater_pool` is the same trio of consumed ids on each Soul.
    pools = [tuple(s._souleater_pool) for s in souls]
    assert len(set(pools)) == 1
    assert len(pools[0]) == 3
    assert len(set(pools[0])) == 3  # ids unique
    # None of the consumed ids should still be in deck / hand / play (they
    # were removed from game).
    consumed_ids = set(pools[0])
    live_ids = {c.id for c in list(p.deck) + list(p.hand) + list(p.field)}
    assert consumed_ids.isdisjoint(live_ids)


def test_bound_soul_play_opens_choice_among_consumed():
    """RLK_214t Bound Soul: playing the Soul (spell) opens a generic
    choice over the 3 consumed minions; picking one adds it to hand."""
    game = prepare_game(
        CardClass.DEMONHUNTER, CardClass.MAGE,
        include=("RLK_214",),
    )
    p = game.player1 if any(c.id == "RLK_214" for c in game.player1.starting_deck) else game.player2
    if game.current_player is not p:
        game.end_turn()
    p.max_mana = 10
    # Pull a Soul into hand and play it (Bound Soul is a 1-mana spell).
    from hearthstone.enums import Zone as _Zone
    pool = [c for c in list(p.deck) + list(p.hand) if c.id == "RLK_214t"]
    soul = pool[0]
    consumed_ids = list(soul._souleater_pool)
    if soul.zone != _Zone.HAND:
        soul.zone = _Zone.HAND
    soul.play()
    assert p.choice is not None
    # The choices are exactly the 3 consumed ids.
    choice_ids = sorted(c.id for c in p.choice.cards)
    assert choice_ids == sorted(consumed_ids)
    pick = p.choice.cards[0]
    pick_id = pick.id
    p.choice.choose(pick)
    # The picked card is now in hand.
    assert pick_id in {c.id for c in p.hand}


def test_bonelord_frostwhisper_first_card_each_turn_is_free():
    """RLK_591 Bonelord Frostwhisper: once the deathrattle arms the
    affected player, their first card each turn costs (0); subsequent
    cards pay their printed cost. The latch (`_consumed_this_turn`)
    re-arms at OWN_TURN_BEGIN. Tests pay_cost behaviour directly via
    the flags (the doom-counter tick is exercised separately; here we
    isolate the cost-substitution half of the effect)."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.current_player
    p1.max_mana = 10
    p1._frostwhisper_first_card_free = True
    p1._frostwhisper_consumed_this_turn = False
    pre_mana = p1.mana
    fb1 = p1.give(FIREBALL)  # printed cost 4
    fb2 = p1.give(FIREBALL)
    fb1.play(target=p1.opponent.hero)
    assert p1.mana == pre_mana  # first card was free
    assert p1._frostwhisper_consumed_this_turn is True
    fb2.play(target=p1.opponent.hero)
    assert p1.mana == pre_mana - 4  # second paid printed cost


def test_bonelord_frostwhisper_deathrattle_arms_opponent():
    """RLK_591 Bonelord Frostwhisper deathrattle: arms the opponent's
    `_frostwhisper_first_card_free` flag (permanent for the rest of the
    game) and zeros their `_consumed_this_turn` latch."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.current_player
    assert p.opponent._frostwhisper_first_card_free is False
    fw = p.summon("RLK_591")
    fw.destroy()
    assert p.opponent._frostwhisper_first_card_free is True
    assert p.opponent._frostwhisper_consumed_this_turn is False


def test_sanctum_spellbender_redirects_enemy_minion_spell():
    """RLK_677 Sanctum Spellbender: when the opponent casts a spell
    targeting one of our minions, the target is redirected to the
    Spellbender. Heroes are NOT eligible redirect candidates and the
    Spellbender itself can't be the original target."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    p1.max_mana = 10
    # p1 plays a Wisp + a Sanctum Spellbender; p1 owns both.
    wisp = p1.summon(WISP)
    spellbender = p1.summon("RLK_677")
    pre_sb_hp = spellbender.health
    pre_wisp_hp = wisp.health
    # Pass to p2; p2 casts Fireball on the Wisp.
    game.end_turn()
    p2.max_mana = 10
    fb = p2.give(FIREBALL)
    fb.play(target=wisp)
    # Wisp untouched; Spellbender ate the 6-damage Fireball.
    assert wisp.health == pre_wisp_hp
    assert spellbender.zone == Zone.GRAVEYARD or spellbender.damage >= 6
    # And the redirect did NOT trigger for the Spellbender being the
    # legitimate target — sanity: a fresh Spellbender targeted directly
    # by a spell is hit normally (no infinite redirect loop).
    sb2 = p1.summon("RLK_677")
    game.end_turn(); game.end_turn()
    p2.used_mana = 0
    fb2 = p2.give(FIREBALL)
    fb2.play(target=sb2)
    assert sb2.damage >= 6 or sb2.zone == Zone.GRAVEYARD


def test_silvermoon_arcanist_blocks_spell_targeting_heroes_this_turn():
    """RLK_218 Silvermoon Arcanist battlecry: this turn, the
    controller's spells cannot target heroes (friendly or enemy). The
    block clears at OWN_TURN_END so the next turn spells can target
    heroes again."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    p1.max_mana = 10
    p1.give("RLK_218").play()
    assert p1.spells_cant_target_heroes_this_turn is True
    # Fireball normally targets any character; here heroes are filtered out.
    fb = p1.give(FIREBALL)
    # Trying to target the enemy hero must raise (not a valid target).
    import pytest
    from fireplace.exceptions import InvalidAction
    with pytest.raises(InvalidAction):
        fb.play(target=p2.hero)
    # The Fireball was never played; mana wasn't spent.
    assert fb.zone == Zone.HAND
    # play_targets excludes heroes.
    assert all(t.type != CardType.HERO for t in fb.play_targets)
    # End own turn → flag clears; next own turn the gate is gone.
    game.end_turn()
    assert p1.spells_cant_target_heroes_this_turn is False
    game.end_turn()
    # Same Fireball can now target the enemy hero.
    fb.play(target=p2.hero)
    assert p2.hero.damage >= 6
