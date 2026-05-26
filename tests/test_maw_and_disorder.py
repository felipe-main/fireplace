"""Maw and Disorder (Patch 24.4) mini-set tests.

Covers the 35 mini-set cards. The mini-set leans entirely on engine
primitives that landed with Castle Nathria (Infuse, Locations,
Manathirst, Relics), so engine-extension tests live in
test_castle_nathria.py; here we focus on card-level behaviour.
"""

from hearthstone.enums import CardClass, CardType, Race, Zone

from utils import *


# ---------------------------------------------------------------------------
# Engine — MAW_012 Infuse-by-twin-tag detection
# ---------------------------------------------------------------------------


def test_all_fel_breaks_loose_infuse_threshold_recognized():
    """MAW_012 ships without the legacy INFUSE tag; the engine's
    infuse_threshold property falls back to recognizing the target
    twin's INFUSED tag.  Without this fallback, the card never morphs."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    fel = game.player1.give("MAW_012")
    assert fel.infuse_threshold == 3
    assert fel.infused_card_id == "MAW_012t"


def test_afterlife_attendant_advances_infuse_in_deck():
    """While Afterlife Attendant is on the board, Infuse cards in the
    controller's deck also tick on friendly minion deaths."""
    game = prepare_game()
    game.player1.summon("MAW_031")  # Afterlife Attendant
    # Place an Infuse card in player1's deck via shuffle (engine-tracked).
    sylv = game.player1.give("MAW_033")
    sylv.shuffle_into_deck()
    assert sylv.zone == Zone.DECK
    assert sylv in game.player1.deck
    # Kill 7 friendly minions to trigger the morph.
    for _ in range(7):
        m = game.player1.summon(WISP)
        m.destroy()
    # The MAW_033 entry in the deck should now be a MAW_033t.
    deck_ids = [c.id for c in game.player1.deck]
    assert "MAW_033t" in deck_ids
    assert "MAW_033" not in deck_ids


# ---------------------------------------------------------------------------
# Demon Hunter
# ---------------------------------------------------------------------------


def test_sightless_magistrate_both_players_draw_to_5():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    # Trim hands to known counts.
    for p in (game.player1, game.player2):
        while len(p.hand) > 2:
            p.hand[-1].discard()
    game.player1.give("MAW_008").play()
    assert len(game.player1.hand) == 5
    assert len(game.player2.hand) == 5


def test_all_fel_breaks_loose_resurrects_demon():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    # Kill a Demon so the friendly graveyard has a target.
    demon = game.player1.summon("CS2_065")  # Voidwalker (Demon)
    demon.destroy()
    pre_field = len(game.player1.field)
    game.player1.give("MAW_012").play()
    assert len(game.player1.field) == pre_field + 1
    assert game.player1.field[-1].race == Race.DEMON


def test_prosecutor_meltranix_locks_opponent_middle_hand_next_turn():
    """Tier-4 fix: while the opponent is under Mel'tranix lockdown,
    middle hand cards are unplayable (only leftmost and rightmost can
    be played).  Lockdown lasts exactly the opponent's next turn."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    # Cast Mel'tranix on player1's turn.
    game.player1.give("MAW_014").play()
    game.end_turn()
    # P2's turn — read the hand AFTER the turn-begin draw.
    hand = game.player2.hand
    assert len(hand) >= 3
    assert hand[0].is_playable() or hand[0].cost > game.player2.mana
    assert hand[-1].is_playable() or hand[-1].cost > game.player2.mana
    # Middle cards: unplayable purely due to position (cost ignored).
    middle_idx = len(hand) // 2
    middle = hand[middle_idx]
    # If cost > mana, that's a different reason — so force mana to max.
    game.player2.max_mana = 10
    game.player2.used_mana = 0
    assert middle.is_playable() is False
    # End the lockdown turn — next P2 turn cycle clears it.
    game.end_turn()
    game.end_turn()
    # Now the same middle card should be playable (if cost OK).
    if middle in game.player2.hand:
        game.player2.max_mana = 10
        game.player2.used_mana = 0
        assert middle.is_playable() is True


def test_all_fel_breaks_loose_infused_summons_three():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    for _ in range(3):
        demon = game.player1.summon("CS2_065")
        demon.destroy()
    pre = len(game.player1.field)
    game.player1.give("MAW_012t").play()
    assert len(game.player1.field) == pre + 3


# ---------------------------------------------------------------------------
# Druid
# ---------------------------------------------------------------------------


def test_dew_process_both_players_draw_extra_on_turn_begin():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    game.player1.give("MAW_024").play()
    pre_p1 = len(game.player1.hand)
    pre_p2 = len(game.player2.hand)
    game.end_turn()  # P1 -> P2 (P2 begin: draws normal + extra)
    assert len(game.player2.hand) == pre_p2 + 2
    game.end_turn()  # P2 -> P1 (P1 begin: draws normal + extra)
    assert len(game.player1.hand) == pre_p1 + 2


def test_incarceration_dormants_target_for_three_turns():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    wisp = game.player2.summon(WISP)
    game.player1.give("MAW_026").play(target=wisp)
    assert wisp.dormant_turns >= 1
    # Cycle 3 friendly turns; the dormant minion should awaken in time.
    for _ in range(6):
        game.end_turn()
    assert wisp.dormant_turns == 0


def test_attorney_at_maw_silence_chooses_first_sub():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    wisp = game.player2.summon(WISP)
    silenced = game.player1.give("MAW_025a")  # Guilty! sub
    silenced.play(target=wisp)
    assert wisp.silenced


def test_attorney_at_maw_immune_chooses_second_sub():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    target = game.player1.summon("CS2_182")  # Chillwind Yeti (4/5)
    game.player1.give("MAW_025b").play(target=target)
    # MAW_025e tags grant Immune via Refresh-style aura; verify via
    # the engine's cant_be_damaged flag which Immune routes through.
    assert target.cant_be_damaged or target.immune


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------


def test_motion_denied_fires_when_opponent_plays_third_card():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    sec = game.player1.give("MAW_010")
    sec.play()
    game.end_turn()  # P2 begins
    pre_hp = game.player2.hero.health
    # Opponent plays 3 cheap cards.  The secret damages the "enemy
    # hero" from the secret-owner's perspective — that's Player2's hero.
    game.player2.give(WISP).play()
    game.player2.give(WISP).play()
    assert game.player2.hero.health == pre_hp  # only 2 played
    game.player2.give(WISP).play()  # 3rd play fires the secret
    assert game.player2.hero.health == pre_hp - 6


def test_shadehound_attack_buffs_other_beasts():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    sd = game.player1.summon("MAW_009")
    other = game.player1.summon("CS2_172")  # Bloodfen Raptor (Beast)
    pre_atk = other.atk
    pre_hp = other.max_health
    # Force Shadehound to be able to attack on its own turn.
    sd.charge = True
    sd.attack(game.player2.hero)
    assert other.atk == pre_atk + 2
    assert other.max_health == pre_hp + 2


def test_shadehound_infused_keeps_attack_trigger_and_has_rush():
    """Tier-2 verification: the Infused twin (MAW_009t) gains Rush from
    its data tag and retains the same attack-buff trigger in events."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    twin = game.player1.summon("MAW_009t")
    other = game.player1.summon("CS2_172")  # Bloodfen Raptor (Beast)
    enemy = game.player2.summon("CS2_172")   # Beast for Rush to attack
    pre_atk = other.atk
    pre_hp = other.max_health
    assert twin.rush
    # Rush minions can attack other minions the turn played.
    twin.attack(enemy)
    assert other.atk == pre_atk + 2
    assert other.max_health == pre_hp + 2


def test_defense_attorney_nathanos_copies_deathrattle():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # Kill a friendly Deathrattle minion (Loot Hoarder draws a card on DR).
    dr_minion = game.player1.summon("EX1_096")  # Loot Hoarder
    dr_minion.destroy()
    pre_hand = len(game.player1.hand)
    nathanos = game.player1.give("MAW_011")
    nathanos.play()
    # Battlecry opens a real Discover; auto-pick the only DR minion.
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Trigger fires DR once; should be +1 draw.
    assert len(game.player1.hand) == pre_hand + 1
    # Nathanos gains the deathrattle: killing him should draw again.
    pre_hand = len(game.player1.hand)
    nathanos.destroy()
    assert len(game.player1.hand) == pre_hand + 1


# ---------------------------------------------------------------------------
# Mage
# ---------------------------------------------------------------------------


def test_objection_counters_opponent_minion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("MAW_006").play()
    game.end_turn()
    target = game.player2.give(WISP)
    target.play()
    # Wisp should have been counted — not in play.
    assert target.zone != Zone.PLAY


def test_objection_skips_battlecry():
    """Tier-4 verification: Objection! must cancel the battlecry, not
    just bounce the minion. Counter sets cant_play=True which gates
    the battlecry branch in Play.do, so Novice Engineer (Draw 1)
    should NOT draw a card."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("MAW_006").play()
    game.end_turn()
    ne = game.player2.give("EX1_015")  # Novice Engineer: Battlecry Draw 1
    pre_hand = len(game.player2.hand)  # after give
    ne.play()
    # Hand: pre -1 (play out of hand) +1 (bounce back) +0 (battlecry skipped)
    assert len(game.player2.hand) == pre_hand
    assert ne.zone == Zone.HAND


def test_life_sentence_removes_minion_from_game():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    wisp = game.player2.summon(WISP)
    game.player1.give("MAW_013").play(target=wisp)
    assert wisp.zone == Zone.REMOVEDFROMGAME


def test_contract_conjurer_cost_drops_by_three_per_secret():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    cc = game.player1.give("MAW_101")
    assert cc.cost == 6
    # Play a Mage secret to drop the cost.
    game.player1.give("EX1_287").play()  # Counterspell
    assert cc.cost == 3


# ---------------------------------------------------------------------------
# Paladin
# ---------------------------------------------------------------------------


def test_jury_duty_summons_two_recruits_with_plus_one_one():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    pre = len(game.player1.field)
    game.player1.give("MAW_015").play()
    new = [m for m in game.player1.field if m.id == "CS2_101t"]
    assert len(new) == 2
    # Both recruits should be 2/2 (base 1/1 + Jury Summons +1/+1).
    for m in new:
        assert m.atk == 2
        assert m.max_health == 2


def test_order_in_the_court_sorts_deck_and_draws():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Stuff deck with predictable costs.
    p = game.player1
    p.deck.clear()
    for cost_card in ("CS2_125", "EX1_310", "CS2_222", "CS2_122"):
        c = p.give(cost_card)
        c.zone = Zone.DECK
        p.deck.append(c)
    pre = len(p.hand)
    p.give("MAW_016").play()
    # Drew exactly one card.
    assert len(p.hand) == pre + 1
    # Top draw was the highest-cost card (Voidcaller/Stormwind Champion).
    drawn = p.hand[-1]
    remaining = sorted(c.cost for c in p.deck)
    # Drawn cost should be >= max of remaining (sorted-descending semantics).
    assert all(drawn.cost >= rc for rc in remaining)


def test_class_action_lawyer_only_fires_if_no_neutrals():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    # Force player1's *current* deck to be all-class (no neutrals).
    from hearthstone.enums import CardClass as CC
    game.player1.deck = [c for c in game.player1.deck
                         if c.card_class != CC.NEUTRAL]
    game.player1.give("MAW_017").play(target=target)
    assert target.atk == 1
    assert target.max_health == 1


def test_class_action_lawyer_no_op_if_deck_has_neutrals():
    """Tier-1 fix: the check is on the CURRENT deck, not starting."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player2.summon("CS2_182")  # 4/5
    pre_atk, pre_hp = target.atk, target.max_health
    # Ensure current deck has at least one neutral.
    from hearthstone.enums import CardClass as CC
    has_neutral = any(c.card_class == CC.NEUTRAL for c in game.player1.deck)
    if not has_neutral:
        n = game.player1.give(WISP)  # Wisp is neutral
        n.shuffle_into_deck()
    game.player1.give("MAW_017").play(target=target)
    # Battlecry condition fails; target stats unchanged.
    assert target.atk == pre_atk
    assert target.max_health == pre_hp


# ---------------------------------------------------------------------------
# Priest
# ---------------------------------------------------------------------------


def test_clear_conscience_buffs_and_protects():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    m = game.player1.summon("CS2_182")
    pre_atk, pre_hp = m.atk, m.max_health
    game.player1.give("MAW_021").play(target=m)
    assert m.atk == pre_atk + 2
    assert m.max_health == pre_hp + 3
    assert m.cant_be_targeted_by_opponents


def test_theft_accusation_fires_only_on_copied_card():
    """Tier-4 fix: Theft Trial now gates on
    `_copied_from_opponent`.  Playing a non-copied card should NOT
    trigger the destroy; playing one stamped via Incriminating
    Psychic's deathrattle should."""
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    target = game.player2.summon("CS2_182")
    game.player1.give("MAW_023").play(target=target)
    # First — play a non-copied card. Accused must survive.
    game.player1.give(WISP).play()
    assert target.zone == Zone.PLAY
    # Now stamp a hand card as copied-from-opponent and play it.
    fake_copy = game.player1.give(WISP)
    fake_copy._copied_from_opponent = True
    fake_copy.play()
    assert target.zone == Zone.GRAVEYARD


def test_incriminating_psychic_copies_opponent_card_on_death():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    # Ensure opponent's hand has at least one card.
    if not game.player2.hand:
        game.player2.give(WISP)
    pre = len(game.player1.hand)
    psy = game.player1.summon("MAW_022")
    psy.destroy()
    assert len(game.player1.hand) == pre + 1


# ---------------------------------------------------------------------------
# Rogue
# ---------------------------------------------------------------------------


def test_perjury_casts_secret_from_another_class_on_turn_start():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    sec = game.player1.give("MAW_018")
    sec.play()
    game.end_turn()
    game.end_turn()
    # Perjury opens a real 3-Secret Discover on own turn begin; pick
    # the first offered.  Resulting secret enters secrets[].
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Perjury is revealed (gone), one new non-Rogue Secret is armed.
    assert "MAW_018" not in [s.id for s in game.player1.secrets]
    assert len(game.player1.secrets) == 1
    from hearthstone.enums import CardClass as CC
    assert game.player1.secrets[0].card_class != CC.ROGUE


def test_murder_accusation_destroys_after_enemy_minion_dies():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    target = game.player2.summon("CS2_182")
    bystander = game.player2.summon(WISP)
    game.player1.give("MAW_019").play(target=target)
    assert target.zone == Zone.PLAY
    # Kill an unrelated enemy minion; the accused should die.
    bystander.destroy()
    assert target.zone == Zone.GRAVEYARD


def test_murder_accusation_self_exclusion_no_re_fire():
    """Tier-1 fix verification: the accused minion's own death should
    not re-trigger Murder Accusation (the printed text says ""another
    enemy minion dies"").  Verified by checking that on direct-damage
    kill of the accused, no extra Destroy is queued (other enemy
    minions survive)."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    target = game.player2.summon("CS2_182")
    other = game.player2.summon(WISP)
    game.player1.give("MAW_019").play(target=target)
    # Direct-kill the accused; the other enemy minion must survive
    # because the accused's own death is excluded from "another minion".
    target.destroy()
    assert other.zone == Zone.PLAY


def test_scribbling_stenographer_cost_drops_per_card_played():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    steno = game.player1.give("MAW_020")
    base = steno.cost
    # Play two cheap cards to drop steno's cost by 2.
    game.player1.give(WISP).play()
    game.player1.give(WISP).play()
    assert steno.cost == base - 2


# ---------------------------------------------------------------------------
# Shaman
# ---------------------------------------------------------------------------


def test_totemic_evidence_summons_basic_totem():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    pre = len(game.player1.field)
    game.player1.give("MAW_003").play()
    # Opens a real Choose-One over basic Totems.
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert len(game.player1.field) == pre + 1
    assert game.player1.field[-1].id in BASIC_TOTEMS


def test_totemic_evidence_infused_summons_all_four_basic_totems():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    pre = len(game.player1.field)
    game.player1.give("MAW_003t").play()
    summoned_ids = {m.id for m in game.player1.field[pre:]}
    assert summoned_ids == set(BASIC_TOTEMS)


def test_framester_shuffles_three_framed_into_opponent_deck():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    pre = sum(1 for c in game.player2.deck if c.id == "MAW_005t")
    game.player1.give("MAW_005").play()
    post = sum(1 for c in game.player2.deck if c.id == "MAW_005t")
    assert post == pre + 3


def test_torghast_custodian_buffs_per_enemy_minion():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    for _ in range(3):
        game.player2.summon(WISP)
    tc = game.player1.give("MAW_030")
    tc.play()
    # Three enemy minions => three buff applications.  Each grants one
    # of Rush / Divine Shield / Windfury — sum of the booleans
    # (counting per-application, not distinct keywords) is at most 3.
    keyword_count = int(tc.rush) + int(tc.divine_shield) + int(tc.windfury)
    assert keyword_count >= 1
    # And no extra buffs beyond the three enemies.
    assert keyword_count <= 3


# ---------------------------------------------------------------------------
# Warlock
# ---------------------------------------------------------------------------


def test_imp_oster_morphs_into_other_imp():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.summon("BRM_006")  # Imp Gang Boss (an Imp/Demon)
    pre_field_ids = [m.id for m in game.player1.field]
    impo = game.player1.give("MAW_000")
    impo.play()
    # Opens a real Choose over friendly Imps; auto-pick the only Imp.
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Morph creates a new entity in Imp-oster's slot.
    field_ids = [m.id for m in game.player1.field]
    assert field_ids.count("BRM_006") == pre_field_ids.count("BRM_006") + 1
    assert "MAW_000" not in field_ids


def test_arson_accusation_destroys_after_hero_takes_damage():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    target = game.player2.summon("CS2_182")
    game.player1.give("MAW_001").play(target=target)
    assert target.zone == Zone.PLAY
    # Damage friendly hero with a queued Hit so the engine fires the
    # damage event the Arson Trial enchantment listens for.
    from fireplace.actions import Hit
    game.queue_actions(game.player1.hero, [Hit(game.player1.hero, 1)])
    assert target.zone == Zone.GRAVEYARD


def test_arson_accusation_silenced_accused_breaks_deathlink():
    """Tier-2 fix: silencing the accused should remove the kill-link.
    The trial puts a paired enchantment on the accused; silence wipes
    the enchantment and the hero-side trigger then skips that accused."""
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    target = game.player2.summon("CS2_182")
    game.player1.give("MAW_001").play(target=target)
    # Silence the accused — should remove the MAW_001e2 mark.
    from fireplace.actions import Silence
    game.queue_actions(target, [Silence(target)])
    # Now damage friendly hero; accused should survive.
    from fireplace.actions import Hit
    game.queue_actions(game.player1.hero, [Hit(game.player1.hero, 1)])
    assert target.zone == Zone.PLAY


def test_habeas_corpses_resurrects_friendly_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    m = game.player1.summon(WISP)
    m.destroy()
    pre = len(game.player1.field)
    game.player1.give("MAW_002").play()
    # Opens a real 3-card Discover over the friendly graveyard.
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert len(game.player1.field) == pre + 1
    rezzed = game.player1.field[-1]
    assert rezzed.charge or rezzed.rush  # Rush keyword applied
    # Goes away at end of turn.
    game.end_turn()
    assert rezzed.zone == Zone.GRAVEYARD


# ---------------------------------------------------------------------------
# Warrior
# ---------------------------------------------------------------------------


def test_call_to_the_stand_opp_summons_from_hand():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # Clear opp hand then give one minion.
    while game.player2.hand:
        game.player2.hand[-1].discard()
    game.player2.give(WISP)
    pre_field = len(game.player2.field)
    game.player1.give("MAW_027").play()
    assert len(game.player2.field) == pre_field + 1


def _max_minions(player):
    """Engine doesn't expose a max_minions attribute; the field cap is
    the hardcoded 7 used throughout."""
    return 7


def test_mawsworn_bailiff_gains_plus_four_four_with_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.hero.armor = 5
    bailiff = game.player1.give("MAW_028")
    bailiff.play()
    # Base 4/4 + (4/4) = 8/8.
    assert bailiff.atk == 8
    assert bailiff.max_health == 8


def test_mawsworn_bailiff_no_bonus_with_low_armor():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.hero.armor = 0
    bailiff = game.player1.give("MAW_028")
    bailiff.play()
    assert bailiff.atk == 4
    assert bailiff.max_health == 4


def test_weapons_expert_buffs_equipped_weapon():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # Equip a weapon first (Fiery War Axe, base 3/2).
    game.player1.give("CS2_106").play()
    weapon = game.player1.weapon
    pre_atk = weapon.atk
    pre_dur = weapon.max_durability
    game.player1.give("MAW_029").play()
    assert game.player1.weapon.atk == pre_atk + 1
    assert game.player1.weapon.max_durability == pre_dur + 1


def test_weapons_expert_draws_weapon_when_no_weapon_equipped():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # Ensure no weapon equipped + a weapon in deck.
    assert game.player1.weapon is None
    axe = game.player1.give("CS2_106")
    axe.zone = Zone.DECK
    game.player1.deck.append(axe)
    pre_hand = len(game.player1.hand)
    game.player1.give("MAW_029").play()
    # Should have drawn the weapon.
    assert any(c.id == "CS2_106" for c in game.player1.hand)


# ---------------------------------------------------------------------------
# Neutral
# ---------------------------------------------------------------------------


def test_soul_seeker_swaps_with_opponent_deck_minion():
    """Tier-1 fix: true cross-zone swap.  After Soul Seeker plays, the
    picked opp-deck minion is on the caster's side, Soul Seeker is in
    the opp's deck, and the picked card is NO LONGER in opp's deck."""
    game = prepare_game()
    target_id = "CS2_182"  # Chillwind Yeti
    m = game.player2.give(target_id)
    m.shuffle_into_deck()
    game.player2.deck = [m]
    pre_field_ids = [x.id for x in game.player1.field]
    game.player1.give("MAW_004").play()
    field_ids = [x.id for x in game.player1.field]
    # Yeti now on caster's side.
    assert field_ids.count(target_id) == pre_field_ids.count(target_id) + 1
    assert "MAW_004" not in field_ids
    # Soul Seeker now in opp's deck (the original entity).
    assert any(c.id == "MAW_004" for c in game.player2.deck)
    # The picked card object is no longer in opp's deck.
    assert m not in game.player2.deck


def test_tight_lipped_witness_blocks_secret_reveal():
    """Tier-4 fix: while a TLW is on the board, Secrets can't be
    revealed.  Counterspell (EX1_287) should NOT trigger when its
    owner controls a TLW."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.give("EX1_287").play()  # Counterspell secret
    game.player1.summon("MAW_032")        # Tight-Lipped Witness
    game.end_turn()
    pre_secrets = len(game.player1.secrets)
    fb = game.player2.give("CS2_024")    # Frostbolt — would normally counter
    fb.play(target=game.player1.hero)
    # Secret stays armed; Frostbolt resolves normally.
    assert len(game.player1.secrets) == pre_secrets
    assert game.player1.hero.health < 30


def test_sylvanas_the_accused_destroys_enemy():
    game = prepare_game()
    target = game.player2.summon("CS2_182")
    syl = game.player1.give("MAW_033")
    syl.play(target=target)
    assert target.zone == Zone.GRAVEYARD


def test_sylvanas_the_accused_infused_steals_enemy():
    game = prepare_game()
    target = game.player2.summon("CS2_182")
    syl = game.player1.give("MAW_033t")
    syl.play(target=target)
    assert target.controller is game.player1


def test_the_jailer_destroys_own_deck_and_grants_immune():
    game = prepare_game()
    pre_deck = len(game.player1.deck)
    assert pre_deck > 0
    jailer = game.player1.give("MAW_034")
    jailer.play()
    assert len(game.player1.deck) == 0
    # Friendly minions become immune (the aura sets CANT_BE_DAMAGED).
    wisp = game.player1.summon(WISP)
    pre_hp = wisp.health
    from fireplace.actions import Hit
    game.queue_actions(wisp, [Hit(wisp, 3)])
    assert wisp.health == pre_hp
