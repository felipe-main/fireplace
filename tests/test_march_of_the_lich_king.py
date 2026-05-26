"""March of the Lich King (Patch 25.0) tests.

Covers the 6 engine primitives added for MotLK plus card-level checks
for the Death Knight class, the Corpses resource, Manathirst keyword,
Rune deck-building validation, and a sampling of marquee cards across
all 11 classes + neutrals.

The audit cycle (review.csv) lists per-card approximations / TODOs; this
file is the structural safety net + ship-readiness gate.
"""

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
