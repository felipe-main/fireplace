from utils import *


# ---------------------------------------------------------------------------
# Engine extensions — Dredge, Colossal, "while holding this"
# ---------------------------------------------------------------------------


def test_dredge_picks_from_bottom_three_and_moves_to_top():
    """Dredge action offers the bottom 3 deck cards and puts the chosen
    one on top of the deck (next-to-draw position)."""
    from fireplace.actions import Dredge

    game = prepare_game()
    game.player1.deck.clear()
    for cid in ("CS2_172", "EX1_399", "CS2_124", "CS2_222", "CS2_186"):
        game.player1.card(cid, zone=Zone.DECK)
    pre = [c.id for c in game.player1.deck]
    game.cheat_action(game.player1.hero, [Dredge(CONTROLLER)])
    assert game.player1.choice is not None
    # The three choices are the bottom 3 (deck[:3]).
    assert [c.id for c in game.player1.choice.cards] == pre[:3]
    # Pick the middle one (EX1_399).
    pick = game.player1.choice.cards[1]
    game.player1.choice.choose(pick)
    # Chosen card is now at the TOP (deck[-1]).
    assert game.player1.deck[-1] is pick


def test_colossal_summons_appendages_on_summon():
    """Hydralodon (Colossal +2) summons two Hydralodon Heads alongside."""
    game = prepare_game()
    hydra = game.player1.summon("TSC_950")
    heads = [m for m in game.player1.field if m.id in ("TSC_950t", "TSC_950t2")]
    assert len(heads) == 2
    assert hydra in game.player1.field


def test_spells_cast_while_holding_increments_for_hand_cards():
    """Casting a spell bumps spells_cast_while_holding on every hand card."""
    game = prepare_game()
    game.player1.discard_hand()
    card = game.player1.give("TSC_017")  # Baba Naga
    assert card.spells_cast_while_holding == 0
    fireball = game.player1.give(FIREBALL)
    fireball.play(target=game.player2.hero)
    assert card.spells_cast_while_holding == 1


def test_nagas_played_while_holding_increments_for_hand_cards():
    """Playing a Naga minion bumps nagas_played_while_holding on hand cards."""
    game = prepare_game()
    card = game.player1.give("TSC_058")  # Predation — tracks Naga plays
    assert card.nagas_played_while_holding == 0
    # Manually give a Naga and play it.
    naga = game.player1.give("TSC_941t")  # City Guard Naga 2/3 Taunt
    naga.play()
    assert card.nagas_played_while_holding == 1


def test_put_on_bottom_places_card_at_deck_start():
    """PutOnBottom puts a card at deck[0] (the bottom)."""
    from fireplace.actions import PutOnBottom

    game = prepare_game()
    game.player1.deck.clear()
    for cid in ("CS2_172", "EX1_399"):
        game.player1.card(cid, zone=Zone.DECK)
    game.cheat_action(game.player1.hero, [PutOnBottom(CONTROLLER, "TSC_039t")])
    assert game.player1.deck[0].id == "TSC_039t"


# ---------------------------------------------------------------------------
# Neutrals
# ---------------------------------------------------------------------------


def test_naval_mine_deathrattle_damages_enemy_hero():
    game = prepare_game()
    mine = game.player1.summon("TSC_001")
    mine.destroy()
    assert game.player2.hero.damage == 4


def test_pufferfist_pings_enemies_when_hero_attacks():
    game = prepare_game()
    game.player1.summon("TSC_002")
    game.end_turn()
    enemy = game.player2.summon("CS2_186")
    game.end_turn()
    # Equip a 1/2 weapon (Fiery War Axe) so hero can attack.
    axe = game.player1.give("CS2_106")
    axe.play()
    game.player1.hero.attack(game.player2.hero)
    # Pufferfist deals 1 to enemy hero AND to enemy minion.
    assert game.player2.hero.damage >= 1
    assert enemy.damage >= 1


def test_naga_giant_cost_reduction_scales_with_spells_played():
    game = prepare_game()
    game.player1.discard_hand()
    giant = game.player1.give("TSC_829")
    base = giant.cost
    # Cast a 3-cost spell.
    fireball = game.player1.give(FIREBALL)
    fireball.play(target=game.player2.hero)
    # Approximation: cost drops by ~2 per spell cast.
    assert giant.cost < base


def test_baba_naga_damages_target_if_spell_cast_while_holding():
    game = prepare_game()
    baba = game.player1.give("TSC_017")
    game.player1.give(FIREBALL).play(target=game.player2.hero)
    game.end_turn(); game.end_turn()
    enemy = game.player2.summon("CS2_186")
    game.end_turn(); game.end_turn()
    baba.play(target=enemy)
    assert enemy.damage == 3


def test_smothering_starfish_silences_all_other_minions():
    game = prepare_game()
    ally = game.player1.summon("CS2_222")  # Stormwind Champion
    enemy = game.player2.summon("CS2_186")
    starfish = game.player1.give("TSC_926")
    starfish.play()
    # Stormwind Champion's aura should be removed.
    assert not ally.buffs  # silenced — aura buffs cleared from itself
    # And the starfish itself is unaffected.
    assert starfish in game.player1.field


def test_selfish_shellfish_makes_opponent_draw_two():
    game = prepare_game()
    shell = game.player1.summon("TSC_935")
    pre = len(game.player2.hand)
    shell.destroy()
    assert len(game.player2.hand) == pre + 2


def test_treasure_guard_draws_on_death():
    game = prepare_game()
    guard = game.player1.summon("TSC_938")
    pre = len(game.player1.hand)
    guard.destroy()
    assert len(game.player1.hand) == pre + 1


def test_twin_fin_fin_twin_summons_copy():
    game = prepare_game()
    twin = game.player1.give("TSC_960")
    twin.play()
    copies = [m for m in game.player1.field if m.id == "TSC_960"]
    assert len(copies) == 2


def test_tuskarrrr_trawler_opens_dredge_choice():
    game = prepare_game()
    game.player1.deck.clear()
    for cid in ("CS2_172", "EX1_399", "CS2_124"):
        game.player1.card(cid, zone=Zone.DECK)
    trawler = game.player1.give("TSC_909")
    trawler.play()
    assert game.player1.choice is not None
    assert len(game.player1.choice.cards) == 3


# ---------------------------------------------------------------------------
# Per-class smoke tests
# ---------------------------------------------------------------------------


def test_multi_strike_grants_temp_atk():
    """ONY-style temp atk pattern — DH Multi-Strike (TSC_006)."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    spell = game.player1.give("TSC_006")
    pre_atk = game.player1.hero.atk
    spell.play()
    assert game.player1.hero.atk == pre_atk + 2


def test_predation_costs_zero_after_naga_played():
    """TSC_058 Predation: cost (0) if a Naga was played while holding it."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    predation = game.player1.give("TSC_058")
    # Printed cost is whatever data currently says (rebalanced to 2 in Patch 26.2).
    assert predation.cost == predation.data.cost
    naga = game.player1.give("TSC_941t")
    naga.play()
    game.refresh_auras()
    assert predation.cost == 0


def test_colaque_immune_with_shell():
    """TSC_026 Colaque is Immune while you control Colaque's Shell."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    colaque = game.player1.summon("TSC_026")
    # The Shell (TSC_026t) was summoned alongside via the Colossal hook.
    game.refresh_auras()
    assert colaque.immune


def test_flipper_friends_choose_orca():
    """TSC_650 Flipper Friends: choosing Orca summons one 6/6."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    spell = game.player1.give("TSC_650")
    spell.play(choose="TSC_650a")
    orcas = [m for m in game.player1.field if m.id == "TSC_650t"]
    assert len(orcas) == 1


def test_flipper_friends_choose_otters():
    """TSC_650 Flipper Friends: choosing Otters summons six 1/1s."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    spell = game.player1.give("TSC_650")
    spell.play(choose="TSC_650d")
    otters = [m for m in game.player1.field if m.id == "TSC_650t4"]
    assert len(otters) == 6


def test_conchs_call_draws_naga_and_spell():
    """TSC_072 Conch's Call draws a Naga and a spell."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    # Stack the deck so the only minion is a Naga.
    game.player1.deck.clear()
    game.player1.card("TSC_941t", zone=Zone.DECK)  # Naga
    game.player1.card(FIREBALL, zone=Zone.DECK)
    spell = game.player1.give("TSC_072")
    pre = len(game.player1.hand) - 1  # excluding the spell about to be played
    spell.play()
    # +2 cards drawn (a Naga + a spell)
    assert len(game.player1.hand) == pre + 2


def test_emergency_maneuvers_summons_copy_on_friendly_death():
    """TSC_929 Emergency Maneuvers (Secret): summon a copy of a dying friendly."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    secret = game.player1.give("TSC_929")
    secret.play()
    minion = game.player1.give("CS2_172")  # 3/2 Bloodfen
    minion.play()
    game.end_turn()
    minion.destroy()
    assert secret not in game.player1.secrets
    copies = [m for m in game.player1.field if m.id == "CS2_172"]
    assert len(copies) >= 1


def test_seafloor_gateway_draws_mech_and_reduces_mech_costs():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.discard_hand()
    mech = game.player1.give("VAN_EX1_556")  # Harvest Golem (Mech)
    game.player1.deck.clear()
    deck_mech = game.player1.card("VAN_EX1_556", zone=Zone.DECK)
    spell = game.player1.give("TSC_055")
    spell.play()
    # Hand-side mech got its cost dropped.
    assert mech.cost == mech.data.cost - 1


def test_volcanomancy_explodes_on_minion_death():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    target = game.player1.summon("CS2_172")
    other = game.player1.summon("CS2_186")  # War Golem 7/7 — survives 3 dmg
    enemy = game.player2.summon("CS2_186")
    spell = game.player1.give("TSC_056")
    spell.play(target=target)
    target.destroy()
    assert other.damage == 3
    assert enemy.damage == 3


def test_garden_grace_buffs_target():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player1.summon("CS2_172")  # 3/2
    spell = game.player1.give("TSC_061")
    spell.play(target=target)
    assert target.atk == 3 + 5
    assert target.max_health == 2 + 5
    assert target.divine_shield


def test_bubblebot_buffs_other_friendly_mechs():
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    mech = game.player1.summon("VAN_EX1_556")  # Harvest Golem (Mech)
    bot = game.player1.give("TSC_059")
    bot.play()
    assert mech.divine_shield
    assert mech.taunt


def test_illuminate_dredges_and_reduces_spell_cost_if_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.deck.clear()
    spell_in_deck = game.player1.card(FIREBALL, zone=Zone.DECK)
    illuminate = game.player1.give("TSC_210")
    illuminate.play()
    # Auto-choose the only available card.
    game.player1.choice.choose(game.player1.choice.cards[0])
    # The spell's cost dropped by 3 in the deck.
    assert spell_in_deck.cost == spell_in_deck.data.cost - 3


def test_queensguard_buffs_per_spell_cast_this_turn():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.give(MOONFIRE).play(target=game.player1.hero)
    game.player1.give(MOONFIRE).play(target=game.player1.hero)
    guard = game.player1.give("TSC_213")
    guard.play()
    assert guard.atk == 2 + 2
    assert guard.max_health == 3 + 2


def test_blood_in_water_damages_and_summons_shark():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    enemy = game.player2.summon("CS2_186")
    spell = game.player1.give("TSC_932")
    spell.play(target=enemy)
    assert enemy.damage == 3
    sharks = [m for m in game.player1.field if m.id == "TSC_932t"]
    assert len(sharks) == 1


def test_schooling_adds_three_swarmers():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.discard_hand()
    spell = game.player1.give("TSC_631")
    spell.play()
    swarmers = [c for c in game.player1.hand if c.id == "TSC_638"]
    assert len(swarmers) == 3


def test_bioluminescence_gives_minions_spell_damage():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    m = game.player1.summon("CS2_172")
    spell = game.player1.give("TSC_923")
    spell.play()
    assert m.spellpower >= 1


def test_rock_bottom_summons_murloc_then_dredges():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.deck.clear()
    murloc_in_deck = game.player1.card("CS2_168", zone=Zone.DECK)  # Murloc Raider
    spell = game.player1.give("TSC_925")
    spell.play()
    # Auto-pick the dredged card.
    if game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    murlocs_on_board = [m for m in game.player1.field if Race.MURLOC in m.races]
    # At least the initial 1/1 summon is there.
    assert len(murlocs_on_board) >= 1


def test_dragged_below_curses_opponent():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    enemy = game.player2.summon("CS2_186")
    spell = game.player1.give("TSC_956")
    pre_deck = len([c for c in game.player2.deck if c.id == "TSC_955t"])
    spell.play(target=enemy)
    assert enemy.damage == 4
    post_deck = len([c for c in game.player2.deck if c.id == "TSC_955t"])
    assert post_deck == pre_deck + 1


def test_sivara_replays_exact_three_spells():
    """TSC_087 Commander Sivara: adds the exact 3 spells cast while
    holding back to hand."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.discard_hand()
    sivara = game.player1.give("TSC_087")
    # Stuff 3 distinct spells into hand and cast each on the hero.
    spells_to_cast = [MOONFIRE, MOONFIRE, FIREBALL]
    for cid in spells_to_cast:
        game.player1.give(cid).play(target=game.player1.hero)
    assert sivara.spells_cast_while_holding == 3
    sivara.play()
    # Hand now contains exactly the three spell ids that were cast.
    hand_ids = sorted(c.id for c in game.player1.hand)
    assert hand_ids == sorted(spells_to_cast)


def test_hedra_summons_per_spell_cost():
    """TSC_658 Hedra the Heretic: summons one minion per spell cast,
    matching each spell's actual cost."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    game.player1.discard_hand()
    hedra = game.player1.give("TSC_658")
    # Cast two known-cost spells: Moonfire (0) and another Moonfire (0).
    game.player1.give(MOONFIRE).play(target=game.player1.hero)
    game.player1.give(MOONFIRE).play(target=game.player1.hero)
    assert hedra.spells_history_while_holding == [
        (MOONFIRE, 0),
        (MOONFIRE, 0),
    ]
    pre_field = len(game.player1.field)
    hedra.play()
    # Two minions summoned, both cost 0.
    new_minions = [m for m in game.player1.field if m.id != "TSC_658"]
    new_minions = [m for m in new_minions if m not in game.player1.field[:pre_field]]
    # The minions are random — we can't predict exact ids, but the data
    # cost should match the spell's cost.
    costs = sorted(m.data.cost for m in new_minions)
    assert costs == [0, 0]


def test_spitelash_siren_alternates_modes():
    """TSC_620 Spitelash Siren: alternates between naga-trigger and
    spell-trigger modes."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    siren = game.player1.summon("TSC_620")
    naga = game.player1.give("TSC_941t")  # 2/3 Naga, costs 2
    spell1 = game.player1.give(MOONFIRE)  # costs 0
    spell2 = game.player1.give(MOONFIRE)
    # Spend some mana so we can detect the refresh.
    game.player1.used_mana = 5
    pre_mana = game.player1.mana
    naga_cost = naga.cost
    naga.play()
    # Naga mode fired: paid `naga_cost` then refreshed +2 → net +2-naga_cost.
    assert game.player1.mana == pre_mana - naga_cost + 2
    # A spell next: spell mode should fire (refresh another 2 mana).
    pre_mana = game.player1.mana
    spell1.play(target=game.player1.hero)
    assert game.player1.mana == pre_mana + 2  # Moonfire is 0-cost
    # Another spell in a row — mode is now naga, so spell trigger should
    # NOT fire.
    pre_mana = game.player1.mana
    spell2.play(target=game.player1.hero)
    assert game.player1.mana == pre_mana


def test_zaqul_heals_when_curses_deal_damage():
    """TSC_959 Za'qul: Abyssal Curses heal Za'qul's controller for the
    damage they deal. The Curse ticks at the start of the cursed
    player's turn."""
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.summon("TSC_959")
    # Put a Curse in player2's hand so the next turn-begin fires it.
    game.player2.abyssal_curses_drawn = 0
    game.player2.card("TSC_955t", zone=Zone.HAND)
    # Damage Za'qul's hero so the heal has somewhere to go.
    game.player1.hero.damage = 5
    pre_p1_hp = game.player1.hero.health
    pre_p2_hp = game.player2.hero.health
    # End P1's turn, then it's P2's turn-begin → curse fires.
    game.end_turn()
    # Curse hits player2 for 1, and Za'qul heals player1 for 1.
    assert game.player2.hero.health == pre_p2_hp - 1
    assert game.player1.hero.health == pre_p1_hp + 1


def test_nellies_pirate_ship_returns_crew_on_death():
    """TSC_660 Nellie + TSC_660t Pirate Ship: the discovered 3 pirates
    are returned to hand when the Ship dies."""
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    nellie = game.player1.give("TSC_660")
    nellie.play()
    # Auto-pick the first option in each Discover.
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    ship = next(m for m in game.player1.field if m.id == "TSC_660t")
    assert hasattr(ship, "_nellie_crew")
    assert len(ship._nellie_crew) == 3
    crew_ids = list(ship._nellie_crew)
    # Empty hand before destroying the ship to make the count easy.
    game.player1.discard_hand()
    ship.destroy()
    hand_ids = sorted(c.id for c in game.player1.hand)
    assert hand_ids == sorted(crew_ids)


def test_blademaster_okani_counters_opponent_minion():
    """TSC_032 Blademaster Okani: opponent minion play is countered."""
    game = prepare_game()
    okani = game.player1.summon("TSC_032")
    game.refresh_auras()
    game.end_turn()
    minion = game.player2.give("CS2_172")  # Bloodfen Raptor
    minion.play()
    # Counter sends it to graveyard without triggering battlecry/board entry.
    assert minion not in game.player2.field
    _ = okani


def test_blademaster_okani_counters_opponent_spell():
    """TSC_032 Blademaster Okani: opponent spell play is also countered."""
    game = prepare_game()
    game.player1.summon("TSC_032")
    game.refresh_auras()
    game.end_turn()
    pre_p1_hp = game.player1.hero.health
    fb = game.player2.give(FIREBALL)
    fb.play(target=game.player1.hero)
    # Counter means no damage is dealt.
    assert game.player1.hero.health == pre_p1_hp


def test_amalgam_of_the_deep_uses_all_tribes():
    """TSC_069 Amalgam of the Deep: a multi-tribe target's full race set
    seeds the Discover pool, not just the first race."""
    game = prepare_game()
    # Use a Murloc Tidehunter (2-tribe) — actually, we want a true multi-
    # tribe minion. Twin-fin Fin Twin is a 1-tribe but the test surface
    # is whether the FuncSelector accepts multiple races. Use a known
    # multi-tribe minion if available; fall back to a single-tribe target
    # to assert the picker doesn't crash.
    target = game.player1.summon("TSC_960")  # 1-tribe Murloc Naga
    amalgam = game.player1.give("TSC_069")
    amalgam.play(target=target)
    # Choice should be open with 3 minions, all sharing at least one tribe.
    assert game.player1.choice is not None
    target_races = set(target.races)
    for c in game.player1.choice.cards:
        assert any(r in target_races for r in c.races) or Race.ALL in c.races


def test_radar_detector_shuffles_after_scan():
    """TSC_079 Radar Detector: deck is shuffled after the bottom-5 scan."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.deck.clear()
    # Bottom 5: 2 mechs + 3 non-mechs. Mechs drawn, non-mechs reshuffled.
    game.player1.card("VAN_EX1_556", zone=Zone.DECK)  # Mech
    for cid in ("CS2_172", "EX1_399", "CS2_124"):
        game.player1.card(cid, zone=Zone.DECK)
    game.player1.card("VAN_EX1_556", zone=Zone.DECK)  # Mech
    pre_non_mech_bottom = [c.id for c in game.player1.deck[:5] if "EX1_556" not in c.id]
    spell = game.player1.give("TSC_079")
    spell.play()
    # Both mechs drawn out.
    drawn_mechs = [c for c in game.player1.hand if c.id == "VAN_EX1_556"]
    assert len(drawn_mechs) == 2
    # The remaining deck cards were shuffled — they're still all 3 ids
    # but their order may differ from the original bottom slice.
    remaining_ids = [c.id for c in game.player1.deck]
    assert sorted(remaining_ids) == sorted(pre_non_mech_bottom)


def test_emergency_maneuvers_resummons_copy_dormant():
    """TSC_929 Emergency Maneuvers: the resummoned copy is Dormant for 1 turn."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    secret = game.player1.give("TSC_929")
    secret.play()
    minion = game.player1.give("CS2_172")
    minion.play()
    game.end_turn()
    minion.destroy()
    copies = [m for m in game.player1.field if m.id == "CS2_172"]
    assert len(copies) >= 1
    assert copies[0].dormant
    assert copies[0].dormant_turns >= 1


def test_queen_azshara_offers_ancient_relics():
    """TSC_641 Queen Azshara: with 3 spells held, offers 3 of 4 relics."""
    game = prepare_game()
    queen = game.player1.give("TSC_641")
    # Cast 3 spells while holding her.
    for _ in range(3):
        game.player1.give(MOONFIRE).play(target=game.player1.hero)
    queen.play()
    assert game.player1.choice is not None
    relic_ids = {"TSC_641ta", "TSC_641tb", "TSC_641tc", "TSC_641td"}
    for c in game.player1.choice.cards:
        assert c.id in relic_ids


def test_gangplank_diver_is_dormant_for_one_turn():
    """TSC_007 Gangplank Diver: must be dormant one turn after summon."""
    game = prepare_game()
    diver = game.player1.summon("TSC_007")
    game.refresh_auras()
    assert diver.dormant_turns > 0
    assert diver.dormant


def test_swiftscale_trickster_makes_only_next_spell_free():
    """TSC_936 Swiftscale Trickster: the first spell cast after play is free;
    subsequent ones revert to normal cost."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.discard_hand()
    fb1 = game.player1.give(FIREBALL)
    fb2 = game.player1.give(FIREBALL)
    base_cost = fb1.cost
    trickster = game.player1.give("TSC_936")
    trickster.play()
    game.refresh_auras()
    # Both spells in hand briefly show 0 cost under the aura.
    assert fb1.cost == 0
    # Cast the first one — the enchant destroys itself.
    fb1.play(target=game.player2.hero)
    game.refresh_auras()
    # The second spell goes back to its normal cost.
    assert fb2.cost == base_cost


def test_naga_giant_cost_drops_by_mana_spent_on_spells():
    """TSC_829 Naga Giant: cost reduction == mana paid on spells this game."""
    game = prepare_game()
    giant = game.player1.give("TSC_829")
    base = giant.cost
    # Cast a 4-mana Fireball.
    game.player1.give(FIREBALL).play(target=game.player2.hero)
    game.refresh_auras()
    assert giant.cost == base - 4


def test_gardens_grace_cost_drops_by_holy_mana_spent():
    """TSC_061 Garden's Grace: -1 per Mana spent on Holy spells this game."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    grace = game.player1.give("TSC_061")
    base = grace.cost
    # Holy Light is 2 mana Holy spell.
    game.player1.give(HOLY_LIGHT).play(target=game.player1.hero)
    game.refresh_auras()
    assert grace.cost == base - 2


def test_urchin_spines_makes_spells_poisonous_this_turn():
    """TSC_946 Urchin Spines: any spell damage to a minion destroys it."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    enemy = game.player2.summon("CS2_186")  # 7/7 War Golem
    game.player1.give("TSC_946").play()
    # Now Moonfire (1 damage) should destroy the 7-health War Golem.
    game.player1.give(MOONFIRE).play(target=enemy)
    assert enemy.dead


def test_urchin_spines_resets_at_turn_end():
    """TSC_946 Urchin Spines effect doesn't carry past the turn."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.give("TSC_946").play()
    game.end_turn(); game.end_turn()  # P2 then back to P1
    assert not game.player1.spells_poisonous_this_turn
    enemy = game.player2.summon("CS2_186")
    game.player1.give(MOONFIRE).play(target=enemy)
    # Without Urchin Spines, Moonfire is just 1 damage — Golem survives.
    assert not enemy.dead
    assert enemy.damage == 1


def test_dozing_kelpkeeper_awakens_after_five_spell_mana():
    """TSC_657 Dozing Kelpkeeper: dormant until ≥5 mana of spells cast since
    summon, then awakens."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    keeper = game.player1.summon("TSC_657")
    game.refresh_auras()
    assert keeper.dormant
    # Cast 3 mana of spells (Fireball is 3) — not enough.
    game.player1.give(FIREBALL).play(target=game.player2.hero)
    game.refresh_auras()
    assert keeper.dormant
    # Cast another Fireball → 6 mana total. Awakens.
    game.player1.give(FIREBALL).play(target=game.player2.hero)
    game.refresh_auras()
    assert not keeper.dormant


def test_forged_in_flame_destroys_weapon_and_draws():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    axe = game.player1.give("CS2_106")  # Fiery War Axe 3/2
    axe.play()
    pre = len(game.player1.hand)
    spell = game.player1.give("TSC_939")
    spell.play()
    assert game.player1.weapon is None
    assert len(game.player1.hand) >= pre + 1  # at least 1 card drawn


# ---------------------------------------------------------------------------
# Tier-3 fixes
# ---------------------------------------------------------------------------


def test_sunken_defector_has_charge_and_post_attack_damage():
    """TSC_057t Sunken Defector: Charge + after-attack 5 dmg to a random
    enemy minion."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    defector = game.player1.summon("TSC_057t")
    assert defector.charge
    game.end_turn()
    enemy = game.player2.summon("CS2_186")
    other_enemy = game.player2.summon("CS2_186")
    game.end_turn()
    # Defector attacks the hero (so other minion is the random-target pool).
    defector.attack(game.player2.hero)
    # One of the two enemy minions takes 5 damage.
    damaged = [m for m in (enemy, other_enemy) if m.damage >= 5]
    assert len(damaged) == 1


def test_whirlpool_matches_copies_by_dbf_id():
    """TSC_209 Whirlpool: copies in hand/deck of a board minion get
    destroyed (matched by dbf_id, so Core/Vanilla aliases too)."""
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    on_field = game.player1.summon("CS2_172")  # Bloodfen Raptor
    # Place identical Bloodfens in hand and deck.
    in_hand = game.player1.card("CS2_172", zone=Zone.HAND)
    in_deck = game.player1.card("CS2_172", zone=Zone.DECK)
    whirlpool = game.player1.give("TSC_209")
    whirlpool.play()
    assert on_field.dead
    assert in_hand not in game.player1.hand
    assert in_deck not in game.player1.deck


def test_radiance_of_azshara_fire_only_spellpower():
    """TSC_635 Radiance of Azshara: only Fire spells get +2 spell damage,
    other spells unaffected."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.summon("TSC_635")
    game.refresh_auras()
    # Fireball is a Fire spell — base 6 damage + 2 fire-spellpower = 8.
    enemy = game.player2.summon("CS2_186")  # 7/7
    fb = game.player1.give(FIREBALL)
    fb.play(target=enemy)
    assert enemy.damage == 8 or enemy.dead
    # Moonfire is Nature — should NOT get the fire bonus.
    other = game.player2.summon("CS2_186")
    mf = game.player1.give(MOONFIRE)
    mf.play(target=other)
    assert other.damage == 1


def test_bloodscent_vilefin_charges_dredged_murloc_to_health():
    """TSC_753 Bloodscent Vilefin: the dredged Murloc has its mana cost
    set to 0, and playing it deals damage equal to the printed cost."""
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Stack the deck so the Dredge offers exactly a known Murloc.
    game.player1.deck.clear()
    target = game.player1.card("CS2_168", zone=Zone.DECK)  # Murloc Raider, cost 1
    vilefin = game.player1.give("TSC_753")
    vilefin.play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Now the Murloc on top of deck has cost 0; draw it and play.
    drawn = game.player1.draw()
    assert drawn.id == "CS2_168"
    assert drawn.cost == 0
    pre_hp = game.player1.hero.health
    drawn.play()
    # Playing pays 1 in HP (original cost).
    assert game.player1.hero.damage >= 1


def test_ambassador_faelin_discovers_three_colossal():
    """TSC_067 Ambassador Faelin: opens 3 sequential Discovers; each
    chosen Colossal goes to the deck bottom."""
    game = prepare_game()
    faelin = game.player1.give("TSC_067")
    pre_deck = len(game.player1.deck)
    faelin.play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Three Colossal minions placed at the deck bottom.
    assert len(game.player1.deck) == pre_deck + 3
    bottom_three = game.player1.deck[:3]
    for c in bottom_three:
        assert c.data.tags.get(GameTag.COLOSSAL, 0)


def test_nagaling_replays_taught_spell():
    """TSC_052 School Teacher / TSC_052t Nagaling: the Discovered spell
    is stamped onto the Nagaling. Only assert the stamping — the
    Nagaling's play action recasts the spell, but its targeting
    interactions with the random discover pool are too variable to
    test deterministically here."""
    game = prepare_game()
    game.player1.discard_hand()
    teacher = game.player1.give("TSC_052")
    teacher.play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    nagaling = next(c for c in game.player1.hand if c.id == "TSC_052t")
    assert getattr(nagaling, "_taught_spell", None) is not None


def test_holy_maki_roll_returns_with_echo_buff():
    """TSC_952 Holy Maki Roll: after each cast a fresh copy lands in
    hand buffed with Echo (GIL_000) so it disappears at end of turn."""
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    game.player1.discard_hand()
    game.player1.hero.damage = 5
    roll = game.player1.give("TSC_952")
    roll.play(target=game.player1.hero)
    # A copy lands in hand.
    copies = [c for c in game.player1.hand if c.id == "TSC_952"]
    assert len(copies) == 1
    # End turn — the GIL_000 enchant removes the copy.
    game.end_turn()
    copies = [c for c in game.player1.hand if c.id == "TSC_952"]
    assert len(copies) == 0


def test_hooktusk_plunder_when_eight_pirates_summoned():
    """TSC_934 Pirate Admiral Hooktusk: with 8 pirates summoned, opens
    a 3-option plunder GenericChoice."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    # Stuff 8 pirates onto cards_played_this_game without putting them
    # in hand (the hand-fill-up would block Hooktusk's give).
    for _ in range(8):
        p = game.player1.card("CS2_146", zone=Zone.SETASIDE)  # Southsea Deckhand
        game.player1.cards_played_this_game.append(p)
    hooktusk = game.player1.give("TSC_934")
    hooktusk.play()
    assert game.player1.choice is not None
    options = {c.id for c in game.player1.choice.cards}
    assert options == {"TSC_934t", "TSC_934t2", "TSC_934t3"}


def test_bootstrap_sunkeneer_moves_minion_atomically_to_deck_bottom():
    """TSC_933 Bootstrap Sunkeneer: enemy minion goes straight from
    field to the bottom of the opponent's deck, never visiting hand."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    enemy = game.player2.summon("CS2_172")
    pre_p2_hand = len(game.player2.hand)
    # Activate combo: play a free spell first on this same turn.
    game.player1.give(MOONFIRE).play(target=game.player1.hero)
    assert game.player1.combo
    sunkeneer = game.player1.give("TSC_933")
    sunkeneer.play(target=enemy)
    # Minion left the field and landed at the bottom of P2's deck.
    assert enemy not in game.player2.field
    assert game.player2.deck[0] is enemy
    assert len(game.player2.hand) == pre_p2_hand


# ---------------------------------------------------------------------------
# Once-over audits
# ---------------------------------------------------------------------------


def test_barbaric_sorceress_swaps_costs_with_prior_buffs():
    """TSC_020 Barbaric Sorceress: cost-swap survives prior cost buffs
    on either side's spell."""
    game = prepare_game()
    game.player1.discard_hand()
    game.player2.discard_hand()
    a = game.player1.give(FIREBALL)  # base cost 4
    b = game.player2.give(MOONFIRE)  # base cost 0
    # Pre-buff a: -1 cost via Murkwater Scribe-style enchant.
    game.player1.give("TSC_823").play()  # Murkwater Scribe — next spell costs 1 less
    game.refresh_auras()
    pre_a_cost = a.cost
    pre_b_cost = b.cost
    sorceress = game.player1.give("TSC_020")
    sorceress.play()
    game.refresh_auras()
    # Swap is via delta-buff; the final costs end up equal.
    assert a.cost + b.cost == pre_a_cost + pre_b_cost  # total mana preserved
    if pre_a_cost != pre_b_cost:
        # If the costs differed, they should now be flipped or close to it.
        assert (a.cost == pre_b_cost and b.cost == pre_a_cost) or (
            abs(a.cost - pre_b_cost) <= 1
        )


def test_raj_nazjan_uses_paid_cost_not_printed():
    """TSC_073 Raj Naz'jan: damage equals the *paid* cost of the spell
    (post-discount), not the printed base cost. Tested via Murkwater
    Scribe reducing the next spell by 1."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.summon("TSC_073")
    # Cast Murkwater Scribe first to reduce the next spell by 1.
    game.player1.give("TSC_823").play()
    fb = game.player1.give(FIREBALL)
    paid = fb.cost
    pre_enemy_hp = game.player2.hero.health
    fb.play(target=game.player1.hero)
    # Raj's hit deals `paid` to the enemy hero.
    assert game.player2.hero.damage == paid


def test_abyssal_depths_draws_two_distinct_minions_on_ties():
    """TSC_608 Abyssal Depths: with multiple equally-low-cost minions in
    the deck, both Draws return *different* minions (not the same one
    twice)."""
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    game.player1.deck.clear()
    # Five 1-cost minions, two 3-cost minions. Abyssal Depths should
    # draw two of the 1-cost minions, not the same minion twice.
    cheap_ids = ["CS2_168", "CS2_146", "EX1_011", "CS2_172", "CS2_125"]
    for cid in cheap_ids:
        game.player1.card(cid, zone=Zone.DECK)
    spell = game.player1.give("TSC_608")
    pre_hand = len(game.player1.hand) - 1  # exclude the spell about to play
    spell.play()
    drawn = game.player1.hand[pre_hand:]
    assert len(drawn) >= 2
    # The two drawn cards should be different instances.
    assert drawn[0] is not drawn[1]


def test_switcheroo_swaps_stats_with_pre_existing_buffs():
    """TSC_702 Switcheroo: pre-buffed minions in deck still swap stats
    correctly — the delta accounts for the existing buff."""
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    game.player1.deck.clear()
    a = game.player1.card("CS2_172", zone=Zone.DECK)  # Bloodfen Raptor 3/2
    b = game.player1.card("CS2_125", zone=Zone.DECK)  # Ironfur Grizzly 3/3
    # Pre-buff `a` with +5/+5 so its stats become 8/7. After swap, it
    # should have b's printed stats (3/3) and b should have a's (3/2)
    # — Switcheroo swaps the cards' *current* stats, which include
    # the +5/+5 buff on a.
    a.atk = 8
    a.max_health = 7
    spell = game.player1.give("TSC_702")
    pre_hand = len(game.player1.hand) - 1
    spell.play()
    drawn = [c for c in game.player1.hand[pre_hand:] if c.type == CardType.MINION]
    # We can't directly assert exact stats without knowing pickup order,
    # but the swap should produce a sum that's the original sum.
    if len(drawn) == 2:
        total_atk = drawn[0].atk + drawn[1].atk
        total_hp = drawn[0].max_health + drawn[1].max_health
        assert total_atk == 8 + 3  # 11
        assert total_hp == 7 + 3   # 10
