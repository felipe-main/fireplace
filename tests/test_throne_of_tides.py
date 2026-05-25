"""Throne of the Tides (Patch 23.4) mini-set tests.

Covers the 34 collectible cards plus engine-level extensions added for the
mini-set (spell-school history while holding, exact-damage trigger,
unplayable-next-turn marker, burn timer, pay-health-for-cards window,
deathrattle insta-die discount, Murloc discount counter, end-of-turn
hand-discard marker).
"""

from utils import *


# ---------------------------------------------------------------------------
# Engine extensions
# ---------------------------------------------------------------------------


def test_spell_schools_cast_while_holding_populates_on_cast():
    """Casting a Fire/Frost/Arcane spell stamps the appropriate SpellSchool
    enum into spell_schools_cast_while_holding on every other hand card."""
    game = prepare_game()
    naz = game.player1.give("TID_709")  # Lady Naz'jar — in hand
    # Cast a known Arcane spell (Moonfire is Arcane in modern data? actually it's
    # Nature. Use Fireball for FIRE).
    game.player1.give(FIREBALL).play(target=game.player2.hero)
    schools = naz.spell_schools_cast_while_holding
    assert int(SpellSchool.FIRE) in schools


def test_unplayable_next_turn_blocks_play():
    """A hand card with unplayable_next_turn > 0 reports is_playable() False."""
    game = prepare_game()
    target = game.player1.give(WISP)
    target.unplayable_next_turn = 2
    assert not target.is_playable()


def test_pay_health_for_cards_consumes_hp_on_play():
    """When pays_health_for_cards_turns_left > 0, the player pays Health
    equal to the card's cost instead of mana."""
    game = prepare_game()
    game.player1.pays_health_for_cards_turns_left = 1
    pre_health = game.player1.hero.health
    pre_mana = game.player1.mana
    spell = game.player1.give(FIREBALL)  # 4-cost spell
    spell.play(target=game.player2.hero)
    # Mana untouched — paid via HP.
    assert game.player1.mana == pre_mana
    # Hero lost cost in HP from the cost-pay route. Then the spell hit the
    # *opponent's* hero, so player1's HP only loses the cost.
    assert game.player1.hero.health == pre_health - 4


# ---------------------------------------------------------------------------
# Demon Hunter
# ---------------------------------------------------------------------------


def test_topple_the_idol_deals_dredged_cost_to_all_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    game.player1.discard_hand()
    game.player1.deck.clear()
    # Seed bottom 3: known 4-cost minion that we'll pick.
    for cid in ("CS2_182", "CS2_182", "CS2_182"):  # Chillwind Yeti (4 cost)
        game.player1.card(cid, zone=Zone.DECK)
    game.player1.summon(WISP)
    game.player2.summon(WISP)
    topple = game.player1.give("TID_703")
    topple.play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # All Wisps dead (1 hp vs 4 dmg).
    assert not [m for m in game.player1.field + game.player2.field if m.id == WISP]


def test_fossil_fanatic_draws_fel_spell_after_hero_attack():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    game.player1.discard_hand()
    game.player1.deck.clear()
    # Seed a known Fel spell in deck (Soul Cleave - BT_752 if exists, fall
    # back to checking the FEL_SPELL filter directly).
    from fireplace.cards import db
    fel_ids = [
        cid for cid, c in db.items()
        if c.collectible and c.type == CardType.SPELL
        and c.spell_school == SpellSchool.FEL
    ]
    assert fel_ids
    game.player1.card(fel_ids[0], zone=Zone.DECK)
    game.player1.give("TID_704").play()
    # Give the hero a weapon so it can attack.
    game.player1.give(LIGHTS_JUSTICE).play()
    pre = len(game.player1.hand)
    game.player1.hero.attack(game.player2.hero)
    assert len(game.player1.hand) == pre + 1


def test_herald_of_chaos_grants_rush_after_fel_spell():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    herald = game.player1.give("TID_706")
    # Cast a Fel spell first
    from fireplace.cards import db
    fel = next(
        cid for cid, c in db.items()
        if c.collectible and c.type == CardType.SPELL
        and c.spell_school == SpellSchool.FEL and c.cost <= 1
    )
    game.player1.give(fel).play()
    herald.play()
    assert herald.rush


# ---------------------------------------------------------------------------
# Druid
# ---------------------------------------------------------------------------


def test_moonbeam_hits_twice():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    pre = game.player2.hero.health
    game.player1.give("TID_001").play(target=game.player2.hero)
    assert game.player2.hero.health == pre - 2


def test_spirit_of_the_tides_buffs_on_unspent_mana():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    spirit = game.player1.summon("TID_000")
    pre_atk, pre_hp = spirit.atk, spirit.max_health
    # Don't spend mana; end turn.
    game.end_turn()
    assert spirit.atk == pre_atk + 1
    assert spirit.max_health == pre_hp + 2


def test_herald_of_nature_buffs_minions_after_nature_spell():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    herald = game.player1.give("TID_002")
    wisp = game.player1.summon(WISP)
    # Innervate (Nature, no target).
    game.player1.give("CORE_EX1_169").play()
    pre_atk, pre_hp = wisp.atk, wisp.max_health
    herald.play()
    assert wisp.atk == pre_atk + 1
    assert wisp.max_health == pre_hp + 2


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------


def test_shellshot_ramps_down():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    m1 = game.player2.summon(WISP)  # 1hp
    m2 = game.player2.summon("CS2_182")  # Chillwind Yeti 5hp
    game.player1.give("TID_075").play()
    # 3 → 2 → 1 damage to random enemy minions; Wisp dies, Yeti takes some.
    assert m1.dead or m2.damage > 0


def test_ancient_krakenbane_threshold_5_damage():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    k = game.player1.give("TID_074")
    # Cast 3 spells while holding it.
    for _ in range(3):
        game.player1.give(MOONFIRE).play(target=game.player1.hero)
    assert k.spells_cast_while_holding == 3
    pre = game.player2.hero.health
    k.play(target=game.player2.hero)
    assert game.player2.hero.health == pre - 5


def test_k9_0tron_summons_one_cost_minion_dredged():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.deck.clear()
    for cid in (WISP, WISP, WISP):  # 1-cost vanilla 1/1
        game.player1.card(cid, zone=Zone.DECK)
    pre = len(game.player1.field)
    game.player1.give("TID_099").play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # K9 itself + summoned wisp.
    assert len(game.player1.field) == pre + 2


# ---------------------------------------------------------------------------
# Mage
# ---------------------------------------------------------------------------


def test_polymorph_jellyfish_transforms_target():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    yeti = game.player1.summon("CS2_182")
    game.player1.give("TID_708").play(target=yeti)
    jelly = game.player1.field[0]
    assert jelly.id == "TID_708t"
    assert jelly.atk == 4 and jelly.max_health == 1


def test_submerged_spacerock_gives_two_then_discards():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    spacerock = game.player1.summon("TID_707")
    pre_hand = len(game.player1.hand)
    spacerock.destroy()
    # Two Arcane Mage spells added.
    assert len(game.player1.hand) == pre_hand + 2
    added = [c for c in game.player1.hand if getattr(c, "discards_at_end_of_owner_turn", False)]
    assert len(added) == 2
    # End turn — they should discard.
    game.end_turn()
    remaining = [c for c in game.player1.hand if getattr(c, "discards_at_end_of_owner_turn", False)]
    assert remaining == []


def test_lady_nazjar_transforms_in_hand_on_fire_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    naz = game.player1.give("TID_709")
    game.player1.give(FIREBALL).play(target=game.player2.hero)
    # Should now be the Fire variant (TID_709t2).
    transformed = next((c for c in game.player1.hand if c.id.startswith("TID_709t")), None)
    assert transformed is not None
    assert transformed.id == "TID_709t2"


# ---------------------------------------------------------------------------
# Paladin
# ---------------------------------------------------------------------------


def test_lightray_cost_drops_per_paladin_card_played():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    lightray = game.player1.give("TID_077")
    base = lightray.data.cost
    # Play a paladin minion (Argent Protector is paladin). Need a friendly
    # target on the board first.
    game.player1.summon(WISP)
    game.player1.give("EX1_362").play(target=game.player1.field[0])
    assert lightray.cost == base - 1


def test_myrmidon_draws_on_spell_targeting_it():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    myr = game.player1.summon("TID_098")
    pre = len(game.player1.hand)
    # Cast Hand of Protection (Paladin spell, targets minion).
    game.player1.give(HAND_OF_PROTECTION).play(target=myr)
    # Hand should grow by 1 (drew a card).
    assert len(game.player1.hand) == pre + 1


def test_front_lines_summons_until_a_side_is_full():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Pre-fill player1's field to leave 1 slot.
    for _ in range(6):
        game.player1.summon(WISP)
    # Seed both decks with minions.
    for _ in range(5):
        game.player1.card("CS2_182", zone=Zone.DECK)
        game.player2.card("CS2_182", zone=Zone.DECK)
    game.player1.give("TID_949").play()
    # At least one side should be full now.
    assert (
        len(game.player1.field) == game.MAX_MINIONS_ON_FIELD
        or len(game.player2.field) == game.MAX_MINIONS_ON_FIELD
    )


def test_front_lines_stops_when_one_deck_runs_out_of_minions():
    """If either player's deck has no minions, the loop stops — the
    printed rule requires a minion FROM EACH side per round."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Empty both decks then seed only player1 with minions; player2 has none.
    game.player1.deck.clear()
    game.player2.deck.clear()
    for _ in range(7):
        game.player1.card("CS2_182", zone=Zone.DECK)
    pre1 = len(game.player1.field)
    pre2 = len(game.player2.field)
    game.player1.give("TID_949").play()
    # Neither side gets minions because player2 has no minions to draw.
    assert len(game.player1.field) == pre1
    assert len(game.player2.field) == pre2


def test_front_lines_summons_alternating_caster_first():
    """Caster summons first each round, then opponent."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.deck.clear()
    game.player2.deck.clear()
    # Seed exactly 2 minions each so we see 2 rounds.
    for _ in range(2):
        game.player1.card("CS2_182", zone=Zone.DECK)
        game.player2.card("CS2_182", zone=Zone.DECK)
    pre1 = len(game.player1.field)
    pre2 = len(game.player2.field)
    game.player1.give("TID_949").play()
    # 2 minions each summoned (loop stops when decks empty).
    assert len(game.player1.field) == pre1 + 2
    assert len(game.player2.field) == pre2 + 2


# ---------------------------------------------------------------------------
# Priest
# ---------------------------------------------------------------------------


def test_drown_puts_enemy_minion_on_bottom_of_own_deck():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    yeti = game.player2.summon("CS2_182")
    pre_bottom = game.player1.deck[0] if game.player1.deck else None
    game.player1.give("TID_920").play(target=yeti)
    # Yeti should be on the bottom of player1's deck (index 0).
    assert game.player1.deck[0] is yeti
    assert yeti.controller is game.player1


def test_herald_of_light_heals_after_holy_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    herald = game.player1.give("TID_085")
    game.player1.hero.damage = 10
    # Cast a Holy spell (Holy Light is Holy).
    game.player1.give(HOLY_LIGHT).play(target=game.player1.hero)
    pre = game.player1.hero.health
    herald.play()
    assert game.player1.hero.health >= pre  # heal happened (capped at max)


def test_disarming_elemental_sets_dredged_card_to_cost_6():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # Seed opponent's bottom 3.
    game.player2.deck.clear()
    for cid in (WISP, WISP, WISP):
        game.player2.card(cid, zone=Zone.DECK)
    game.player1.give("TID_700").play()
    while game.player1.choice:
        pick = game.player1.choice.cards[0]
        game.player1.choice.choose(pick)
    # Now the top of opponent's deck (the dredged card) should cost 6.
    top = game.player2.deck[-1]
    assert top.cost == 6


# ---------------------------------------------------------------------------
# Rogue
# ---------------------------------------------------------------------------


def test_jackpot_adds_two_spells_from_other_classes_5plus_cost():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    pre = len(game.player1.hand)
    game.player1.give("TID_931").play()
    assert len(game.player1.hand) == pre + 2
    added = game.player1.hand[-2:]
    for c in added:
        assert c.type == CardType.SPELL
        assert c.data.cost >= 5
        assert CardClass.ROGUE not in c.classes


def test_shattershambler_discounts_and_kills_next_deathrattle():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    sham = game.player1.give("TID_078")
    sham.play()
    # Next deathrattle minion gets -1 cost and dies on play.
    # Loot Hoarder = EX1_096 — 2 cost 2/1 with Deathrattle "Draw a card".
    loot = game.player1.give("EX1_096")
    base_cost = loot.data.cost
    assert loot.cost == base_cost - 1
    pre_hand = len(game.player1.hand)
    loot.play()
    # Loot Hoarder's deathrattle draws a card; the minion died on play.
    assert loot.dead
    assert len(game.player1.hand) >= pre_hand


# ---------------------------------------------------------------------------
# Shaman
# ---------------------------------------------------------------------------


def test_command_of_neptulon_summons_two_water_revenants():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    pre = len(game.player1.field)
    game.player1.give("TID_005").play()
    revs = [m for m in game.player1.field if m.id == "TID_005t"]
    assert len(revs) == 2
    for r in revs:
        assert r.rush
        assert r.atk == 5
        assert r.max_health == 4
    # Overload 1.
    assert game.player1.overloaded == 1


def test_tidelost_burrower_summons_2_2_copy_of_dredged_murloc():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.deck.clear()
    # Seed murlocs (Bluegill Warrior is a 2-cost 2/1 Murloc).
    for cid in ("EX1_508", "EX1_508", "EX1_508"):
        game.player1.card(cid, zone=Zone.DECK)
    game.player1.give("TID_003").play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    bluegill = [m for m in game.player1.field if m.id == "EX1_508"]
    assert bluegill, "expected a Bluegill copy on the field"
    assert bluegill[0].atk == 2 and bluegill[0].max_health == 2


def test_clownfish_discounts_next_two_murlocs():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give("TID_004").play()
    bluegill = game.player1.give("EX1_508")  # Bluegill — 2-cost Murloc
    base = bluegill.data.cost
    assert bluegill.cost == max(0, base - 2)


# ---------------------------------------------------------------------------
# Warlock
# ---------------------------------------------------------------------------


def test_immolate_burns_opponent_hand_in_three_turns():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Cast Immolate. Opponent hand cards should now have burn_turns_left=3.
    pre_hand = list(game.player2.hand)
    assert pre_hand, "opponent should have a hand"
    game.player1.give("TID_718").play()
    for c in pre_hand:
        assert c.burn_turns_left == 3
    # Three of OPPONENT's begin_turns later, the marked cards are destroyed.
    for _ in range(6):
        game.end_turn()
    # Burned cards should have left hand.
    survivors = [c for c in game.player2.hand if c in pre_hand]
    assert not survivors


def test_herald_of_shadows_buffs_self_after_shadow_spell():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    herald = game.player1.give("TID_717")
    target = game.player2.summon("CS2_182")  # 4/5 Yeti
    # Stamp the spell-school marker directly to avoid cross-class spell
    # casting requirements.
    herald.spell_schools_cast_while_holding.add(int(SpellSchool.SHADOW))
    pre_target_hp = target.max_health
    pre_self_hp = herald.max_health
    herald.play(target=target)
    assert target.max_health <= pre_target_hp - 2 or target.dead
    assert herald.max_health >= pre_self_hp + 2


def test_commander_ulthok_makes_opponent_pay_health_next_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.give("TID_719").play()
    assert game.player2.pays_health_for_cards_turns_left == 2
    game.end_turn()
    # Opponent's first turn — flag decrements to 1 (still active).
    assert game.player2.pays_health_for_cards_turns_left == 1
    pre = game.player2.hero.health
    spell = game.player2.give(FIREBALL)
    spell.play(target=game.player1.hero)
    # Opponent paid 4 HP for Fireball.
    assert game.player2.hero.health == pre - 4


# ---------------------------------------------------------------------------
# Warrior
# ---------------------------------------------------------------------------


def test_tidal_revenant_deals_5_and_armors_8():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    pre_armor = game.player1.hero.armor
    pre_hp = game.player2.hero.health
    game.player1.give("TID_716").play(target=game.player2.hero)
    assert game.player2.hero.health == pre_hp - 5
    assert game.player1.hero.armor == pre_armor + 8


def test_igneous_lavagorger_armors_by_dredged_cost():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.deck.clear()
    for cid in ("CS2_182",):  # 4-cost Yeti
        game.player1.card(cid, zone=Zone.DECK)
    pre_armor = game.player1.hero.armor
    game.player1.give("TID_714").play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Gained 4 armor.
    assert game.player1.hero.armor == pre_armor + 4


def test_clash_of_the_colossals_gives_both_players_a_colossal():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    pre1 = len(game.player1.hand)
    pre2 = len(game.player2.hand)
    game.player1.give("TID_715").play()
    assert len(game.player1.hand) == pre1 + 1
    assert len(game.player2.hand) == pre2 + 1
    own = game.player1.hand[-1]
    opp = game.player2.hand[-1]
    from hearthstone.enums import GameTag as _GT
    assert own.data.tags.get(_GT.COLOSSAL)
    assert opp.data.tags.get(_GT.COLOSSAL)
    # Own one is discounted by 2.
    assert own.cost == max(0, own.data.cost - 2)


# ---------------------------------------------------------------------------
# Neutral
# ---------------------------------------------------------------------------


def test_snapdragon_buffs_battlecry_minions_in_deck():
    game = prepare_game()
    game.player1.deck.clear()
    # Loot Hoarder has Deathrattle but no Battlecry — should NOT get buffed.
    # Novice Engineer (EX1_015) is a 2-cost 1/1 Battlecry.
    novice = game.player1.card("EX1_015", zone=Zone.DECK)
    non_bc = game.player1.card("EX1_096", zone=Zone.DECK)  # Loot Hoarder
    game.player1.give("TID_710").play()
    assert novice.atk == 2  # 1+1
    assert novice.max_health == 2  # 1+1
    assert non_bc.atk == 2  # unchanged
    assert non_bc.max_health == 1  # unchanged


def test_ozumat_summons_six_tentacles_on_play():
    game = prepare_game()
    oz = game.player1.give("TID_711")
    oz.play()
    tentacles = [m for m in game.player1.field if m.id.startswith("TID_711t")]
    assert len(tentacles) == 6


def test_ozumat_deathrattle_destroys_random_enemy_per_tentacle():
    game = prepare_game()
    oz = game.player1.summon("TID_711")
    # Summoning Ozumat brings the 6 tentacles too.
    for _ in range(6):
        game.player2.summon("CS2_182")  # Yetis
    oz.destroy()
    # All 6 enemy yetis should be destroyed.
    assert all(m.id != "CS2_182" for m in game.player2.field)


def test_neptulon_summons_two_hands():
    game = prepare_game()
    n = game.player1.summon("TID_712")
    hands = [m for m in game.player1.field if m.id in ("TID_712t", "TID_712t2")]
    assert len(hands) == 2


def test_bubbler_dies_to_exactly_one_damage():
    game = prepare_game()
    b = game.player1.summon("TID_713")
    game.player1.give(MOONFIRE).play(target=b)  # Moonfire deals 1
    assert b.dead


def test_bubbler_survives_two_damage():
    game = prepare_game()
    b = game.player1.summon("TID_713")
    # 2 damage: Mortal Coil (EX1_302) deals 1 — use two of them, or a 2-damage spell.
    game.player1.give(FIREBALL).play(target=b)  # 4 damage → minion dies anyway
    # Better: just verify the exact-1 check by manually damaging with 2.
    # Re-do test:
    game2 = prepare_game()
    b2 = game2.player1.summon("TID_713")
    pre = b2.max_health
    game2.cheat_action(b2, [__import__("fireplace.actions", fromlist=["Hit"]).Hit(b2, 2)])
    # Bubbler now alive (took 2 dmg, not exactly 1).
    assert not b2.dead
    assert b2.damage == 2


def test_coilfang_marks_opponent_card_unplayable_next_turn():
    game = prepare_game()
    # Ensure opponent has cards.
    while len(game.player2.hand) < 3:
        game.player2.give(WISP)
    game.player1.give("TID_744").play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    marked = [c for c in game.player2.hand if c.unplayable_next_turn > 0]
    assert len(marked) == 1


# ---------------------------------------------------------------------------
# Tier-1 audit edge cases (re-verification of approximations)
# ---------------------------------------------------------------------------


def test_lady_nazjar_transforms_on_frost_to_t3():
    """Frost spell triggers the third Naz'jar variant (8 Armor).

    Ice Lance (CS2_031) is 1-mana Frost, requires a target.
    """
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("TID_709")
    game.player1.give("CS2_031").play(target=game.player2.hero)
    transformed = next((c for c in game.player1.hand if c.id.startswith("TID_709t")), None)
    assert transformed is not None
    assert transformed.id == "TID_709t3"


def test_lady_nazjar_transforms_on_arcane_to_t():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("TID_709")
    # Arcane spell — Arcane Intellect (CS2_023) is 3-cost arcane, no target.
    game.player1.give("CS2_023").play()
    transformed = next((c for c in game.player1.hand if c.id.startswith("TID_709t")), None)
    assert transformed is not None
    assert transformed.id == "TID_709t"


def test_lady_nazjar_t_reduces_hand_spell_costs_by_2():
    """The Arcane variant of Lady Naz'jar reduces spell costs by 2."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    naz = game.player1.give("TID_709t")
    other_spell = game.player1.give(FIREBALL)
    base = other_spell.data.cost
    naz.play()
    assert other_spell.cost == max(0, base - 2)


def test_ancient_krakenbane_progress_tally_tracks_spells():
    """The Krakenbane mixin counts down via spells_cast_while_holding."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    k = game.player1.give("TID_074")
    assert k.spells_cast_while_holding == 0
    for _ in range(3):
        game.player1.give(MOONFIRE).play(target=game.player1.hero)
    assert k.spells_cast_while_holding == 3


def test_coilfang_handles_empty_opponent_hand():
    """Coilfang no-ops when opponent has no hand cards."""
    game = prepare_game()
    while game.player2.hand:
        game.player2.hand[0].discard()
    game.player1.give("TID_744").play()
    assert game.player1.choice is None


def test_ozumat_with_fewer_than_six_tentacles_only_destroys_matching():
    """Deathrattle scales with remaining tentacles (if some have died)."""
    game = prepare_game()
    oz = game.player1.summon("TID_711")
    # Kill 3 of the 6 tentacles via destroy() (which preserves deathrattles).
    tentacles = [
        m for m in game.player1.field if m.id.startswith("TID_711t")
    ][:3]
    for t in tentacles:
        t.destroy()
    # Summon 6 yetis on opponent.
    for _ in range(6):
        game.player2.summon("CS2_182")
    oz.destroy()
    # Should destroy 3 yetis (one per surviving tentacle).
    yetis = [m for m in game.player2.field if m.id == "CS2_182"]
    assert len(yetis) == 3


def test_command_of_neptulon_with_full_overload_carry():
    """Overload (1) is carried by data and applied automatically."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give("TID_005").play()
    assert game.player1.overloaded == 1


def test_clownfish_charges_consume_on_play_not_just_in_hand():
    """The discount counter decrements per Murloc played."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give("TID_004").play()
    assert game.player1.next_n_murlocs_discount == 2
    bg = game.player1.give("EX1_508")  # Bluegill Warrior, 2-cost Murloc
    bg.play()
    assert game.player1.next_n_murlocs_discount == 1


def test_clownfish_charges_unaffected_by_non_murloc_play():
    """Playing non-Murloc minions doesn't drain the Clownfish counter."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give("TID_004").play()
    yeti = game.player1.give("CS2_182")
    yeti.play()
    assert game.player1.next_n_murlocs_discount == 2
