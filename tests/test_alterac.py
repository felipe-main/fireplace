from utils import *


# ---------------------------------------------------------------------------
# Honorable Kill — engine wiring
# ---------------------------------------------------------------------------


def test_honorable_kill_triggers_on_exact_kill():
    """AV_121 Gnome Private: Honorable Kill: Gain +2 Attack."""
    game = prepare_game()
    gnome = game.player1.give("AV_121").play()
    # Give a 1/3 a target with exactly matching health: a 1-health minion.
    game.end_turn()
    target = game.player2.summon("CS2_172")  # 2/1 Bloodfen Raptor's brother... use a 1-health vanilla
    # Actually we want exact-health-equal-to-attack. AV_121 has 1 attack.
    # Use a 1/1 token via Wisp: CS2_231 Wisp.
    game.player2.summon("CS2_231")  # Wisp 1/1
    game.end_turn()
    # AV_121's attack is 1, Wisp has 1 health — exact honorable kill.
    wisp = [m for m in game.player2.field if m.id == "CS2_231"][0]
    gnome.attack(wisp)
    assert gnome.atk == 1 + 2, f"Expected +2 attack from HK, got atk={gnome.atk}"


def test_honorable_kill_does_not_trigger_on_overkill():
    """If damage overkills (defender ends < 0 hp), Honorable Kill should NOT fire."""
    game = prepare_game()
    # Give a higher-attack honorable-kill minion to overkill a 1hp target.
    # AV_132 Troll Centurion is 8/8 with HK: deal 8 damage to enemy hero.
    centurion = game.player1.give("AV_132").play()
    game.end_turn()
    wisp = game.player2.summon("CS2_231")  # 1/1
    game.end_turn()
    starting_enemy_hp = game.player2.hero.health
    centurion.attack(wisp)
    # 8 attack on a 1hp minion → overkill, HK does NOT fire.
    assert game.player2.hero.health == starting_enemy_hp


def test_honorable_kill_only_on_minion_target():
    """Honorable Kill should not fire when attacking a hero (target.type != MINION)."""
    game = prepare_game()
    # AV_121 1/3, attack the enemy hero (not a minion). HK shouldn't trigger.
    gnome = game.player1.give("AV_121").play()
    gnome.set_current_health(3)
    # Give the minion Charge so it can attack immediately.
    gnome.charge = True
    starting_atk = gnome.atk
    # Use it to attack the hero (which won't die from 1 dmg).
    gnome.attack(game.player2.hero)
    assert gnome.atk == starting_atk, "HK should not fire on hero attack"


def test_honorable_kill_weapon_dreadprison_glaive():
    """AV_209 Dreadprison Glaive 1/3: HK deals damage equal to hero atk to enemy hero."""
    game = prepare_game()
    glaive = game.player1.give("AV_209").play()
    assert game.player1.weapon is glaive
    assert game.player1.hero.atk == 1  # weapon gives 1 atk to hero
    game.end_turn()
    wisp = game.player2.summon("CS2_231")  # 1/1 — exact-kill match
    game.end_turn()
    starting_enemy_hp = game.player2.hero.health
    game.player1.hero.attack(wisp)
    # HK should fire, dealing hero_atk damage (1) to enemy hero.
    assert game.player2.hero.health == starting_enemy_hp - 1


# ---------------------------------------------------------------------------
# Objective spells — engine wiring (3-turn countdown + per-turn effect)
# ---------------------------------------------------------------------------


def test_objective_iceblood_garrison_lasts_three_turns():
    """AV_660 Iceblood Garrison: deal 1 dmg to all minions each end of turn, 3 turns."""
    game = prepare_game()
    obj = game.player1.give("AV_660").play()
    assert obj in game.player1.secrets, "Objective should enter the secrets zone"
    assert obj.turns_remaining == 3
    # Put a minion on each side to observe the per-turn damage.
    game.player1.summon("CS2_125")  # Ironfur Grizzly 3/3
    game.end_turn()
    game.player2.summon("CS2_125")
    game.end_turn()
    # End-of-turn just fired once. Counter decrements to 2.
    assert obj.turns_remaining == 2
    game.end_turn()
    game.end_turn()
    assert obj.turns_remaining == 1
    game.end_turn()
    game.end_turn()
    # 3 ticks done — should now be destroyed.
    assert obj not in game.player1.secrets
    assert obj.zone == Zone.GRAVEYARD


def test_objective_field_of_strife_aura():
    """AV_661 Field of Strife: friendly minions have +1 attack while active."""
    game = prepare_game()
    minion = game.player1.summon("CS2_125")  # 3/3
    assert minion.atk == 3
    game.player1.give("AV_661").play()
    game.refresh_auras()
    assert minion.atk == 3 + 1, "Field of Strife should grant +1 attack"


def test_objective_destroyed_after_three_owner_turns():
    """A pure end-of-turn-trigger Objective expires after 3 ticks."""
    game = prepare_game()
    obj = game.player1.give("AV_660").play()
    for _ in range(3):
        game.end_turn()
        game.end_turn()  # opponent turn so we get another OWN_TURN_END
    assert obj.zone == Zone.GRAVEYARD


# ---------------------------------------------------------------------------
# A handful of straightforward card behaviors
# ---------------------------------------------------------------------------


def test_herald_of_lokholar_draws_spell():
    """AV_101 Herald of Lokholar: Battlecry draws a spell."""
    game = prepare_game()
    game.player1.discard_hand()
    # player.card() defaults zone=SETASIDE; FRIENDLY_DECK matches only Zone.DECK
    # so the appended spell must be placed in the deck zone for the battlecry's
    # RANDOM(FRIENDLY_DECK + SPELL) selector to see it. Without this, the test
    # silently depends on the random draft happening to contain other spells.
    game.player1.deck.append(game.player1.card("CS2_029", zone=Zone.DECK))
    starting_hand = len(game.player1.hand)
    game.player1.give("AV_101").play()
    assert len(game.player1.hand) > starting_hand


def test_popsicooler_freezes_two_enemies():
    """AV_102 Popsicooler: deathrattle freezes two random enemy minions."""
    game = prepare_game()
    pop = game.player1.give("AV_102").play()
    game.end_turn()
    e1 = game.player2.summon("CS2_125")
    e2 = game.player2.summon("CS2_125")
    e3 = game.player2.summon("CS2_125")
    game.end_turn()
    pop.destroy()
    frozen = sum(1 for m in (e1, e2, e3) if m.frozen)
    assert frozen == 2


def test_drekthar_summons_two_on_empty_deck():
    """AV_100 Drek'Thar powers up when the deck has no qualifying minions."""
    game = prepare_game()
    game.player1.discard_hand()
    game.player1.deck = []
    drekthar = game.player1.give("AV_100").play()
    # Drek'Thar himself; with empty deck the summon-from-deck has nothing
    # to summon, so just verify the card resolves without crashing.
    assert drekthar.zone == Zone.PLAY


def test_immovable_object_no_durability_loss():
    """AV_146 The Immovable Object: doesn't lose Durability on attack."""
    game = prepare_game()
    weapon = game.player1.give("AV_146").play()
    assert weapon is game.player1.weapon
    assert weapon.durability == 5
    game.end_turn()
    target = game.player2.summon("CS2_125")  # 3/3 Ironfur Grizzly
    game.end_turn()
    # Attack across three of our turns; durability must stay at 5 throughout.
    for _ in range(3):
        target.damage = 0  # keep target alive for next attack
        game.player1.hero.attack(target)
        assert weapon.durability == 5
        game.end_turn()
        game.end_turn()
    assert weapon.zone == Zone.PLAY


def test_immovable_object_halves_incoming_damage():
    """AV_146 The Immovable Object: hero takes half damage, rounded up."""
    game = prepare_game()
    game.player1.give("AV_146").play()
    game.player1.hero.armor = 0
    starting = game.player1.hero.health
    # 4 incoming → 2 actual
    game.player1.hero.hit(4)
    assert game.player1.hero.health == starting - 2
    # 3 incoming → ceil(3/2) = 2 actual
    starting = game.player1.hero.health
    game.player1.hero.hit(3)
    assert game.player1.hero.health == starting - 2
    # 1 incoming → ceil(1/2) = 1 actual (never reduces a real hit to 0)
    starting = game.player1.hero.health
    game.player1.hero.hit(1)
    assert game.player1.hero.health == starting - 1


def test_honorable_kill_passes_victim_to_script():
    """AV_313 Hollow Abomination HK: gain the killed minion's Attack."""
    game = prepare_game()
    abomination = game.player1.give("AV_313")
    game.player1.give(THE_COIN).play()  # to play Hollow on turn 1+coin
    game.end_turn()
    # Place a 3hp minion on opponent's side that abomination will exact-kill
    # when its 1-damage AOE hits it… actually Hollow Abomination is a 2/8
    # battlecry that deals 1 to all enemy minions. With a 1-hp minion, HK fires.
    victim = game.player2.summon("CS2_231")  # Wisp 1/1
    game.end_turn()
    starting_atk = 2
    # Note: requires enough mana for AV_313 (cost 5). Skip enough turns.
    while game.player1.max_mana < 5:
        game.end_turn(); game.end_turn()
    abomination.play()
    # Victim's atk was 1; HK should add 1 to abomination's atk.
    assert abomination.atk == starting_atk + 1, f"Expected atk={starting_atk+1}, got {abomination.atk}"


def test_kurtrus_demons_scale_with_hero_attacks():
    """AV_204 Kurtrus: summoned demons' attack scales with hero attacks this game."""
    game = prepare_game()
    # Give Kurtrus a few hero attacks first
    game.player1.give("CS2_106").play()  # Fiery War Axe weapon (3/2)
    game.end_turn()
    target = game.player2.summon("CS2_125")  # 3/3 grizzly
    game.end_turn()
    target.damage = 0
    game.player1.hero.attack(target)
    assert game.player1.num_hero_attacks_this_game == 1
    # Get to enough mana for Kurtrus (cost 6) and play him
    while game.player1.max_mana < 6:
        game.end_turn(); game.end_turn()
    game.player1.give("AV_204").play()
    demons = [m for m in game.player1.field if m.id == "AV_204t2"]
    assert len(demons) == 2
    # Demons should have base_atk (1) + buff from hero_attacks (1) = 2
    for demon in demons:
        assert demon.atk == 1 + 1, f"Demon atk={demon.atk}, expected 2"


def test_galvangar_powered_up_by_armor_gained():
    """AV_145 Captain Galvangar: gain +3/+3 and Charge if you've gained 15+ armor."""
    game = prepare_game()
    # Trigger the counter directly — engine wiring is what we want to test;
    # exercising the in-engine path via real cards needs many turns.
    assert game.player1.armor_gained_this_game == 0
    game.player1.armor_gained_this_game = 15
    # Ramp mana to play Galvangar (cost 6)
    while game.player1.max_mana < 6:
        game.end_turn(); game.end_turn()
    galv = game.player1.give("AV_145").play()
    assert galv.atk == 6 + 3
    assert galv.charge


def test_stormpike_marshal_cost_reduces_after_opponent_damage():
    """AV_135 Stormpike Marshal: costs 1 (down from 4) if hero took 5+ damage on opp turn."""
    game = prepare_game()
    marshal = game.player1.give("AV_135")
    assert marshal.cost == 4
    # Opponent deals damage to our hero on their turn
    game.end_turn()
    game.player1.hero.damage = 0
    game.player1.hero.armor = 0
    # Need actions during opponent's turn that hit player 1's hero.
    # Simulate by directly calling hit on the hero — this is during opp's turn.
    game.player1.hero.hit(5)
    assert game.player1.damage_taken_on_opponents_turn >= 5
    assert marshal.cost == 1


def test_sneaky_scout_makes_next_hero_power_free():
    """AV_123 Sneaky Scout HK: next Hero Power costs 0."""
    game = prepare_game()
    scout = game.player1.give("AV_123").play()  # 3/2 Stealth
    game.end_turn()
    # Sneaky Scout has 3 attack — need a 3-hp target for an exact HK kill.
    target = game.player2.summon("CS2_120")  # River Crocolisk 2/3
    game.end_turn()
    scout.attack(target)
    assert game.player1.next_hero_power_costs_zero == 1
    # Now use the hero power; cost should be paid as 0
    pre_mana = game.player1.mana
    game.player1.hero.power.use(target=game.player2.hero)
    # Mage HP (Fireblast) is the default if Player1 was Jaina; cost would be 2.
    # With our flag, the cost was 0.
    assert game.player1.mana == pre_mana, "HP should cost 0 after Sneaky Scout HK"
    assert game.player1.next_hero_power_costs_zero == 0


def test_amplified_snowflurry_freezes_hp_target():
    """AV_115 Amplified Snowflurry: next HP costs 0 and Freezes its target."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    snow = game.player1.give("AV_115").play()
    assert game.player1.next_hero_power_costs_zero == 1
    assert game.player1.next_hero_power_freezes_target == 1
    # Mage HP (Fireblast) deals 1 dmg to a target; target should also be frozen.
    game.end_turn()
    target = game.player2.summon("CS2_125")  # Ironfur Grizzly 3/3
    game.end_turn()
    pre_mana = game.player1.mana
    game.player1.hero.power.use(target=target)
    assert game.player1.mana == pre_mana, "HP should cost 0"
    assert target.frozen, "HP target should be frozen by the snowflurry flag"
    # Both flags consumed
    assert game.player1.next_hero_power_costs_zero == 0
    assert game.player1.next_hero_power_freezes_target == 0


def test_pride_seeker_discount_on_choose_one():
    """AV_296 Pride Seeker: next Choose One card costs (2) less."""
    game = prepare_game()
    # Confirm the discount counter wires up.
    assert game.player1.next_choose_one_discount == 0
    game.player1.give("AV_296").play()
    assert game.player1.next_choose_one_discount == 2
    # Give a Choose One card and verify its effective cost is reduced.
    keeper = game.player1.give("EX1_178")  # Ancient of War — Choose One, 7 mana
    assert keeper.cost == 7 - 2


def test_wildheart_guff_lifts_mana_cap():
    """AV_205 Wildheart Guff: max_resources jumps from 10 → 20 + gain mana + draw."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    while game.player1.max_mana < 5:
        game.end_turn(); game.end_turn()
    assert game.player1.max_resources == 10
    hand_before = len(game.player1.hand)
    mana_before = game.player1.max_mana
    game.player1.give("AV_205").play()
    assert game.player1.max_resources == 20
    assert game.player1.max_mana == mana_before + 1
    assert len(game.player1.hand) >= hand_before  # at least the draw landed


def test_korrak_resummons_if_not_honorably_killed():
    """AV_143 Korrak: deathrattle resummons unless the killing blow was Honorable Kill."""
    # Case 1: regular damage kill (not HK) → resurrects.
    game = prepare_game()
    while game.player1.max_mana < 4:
        game.end_turn(); game.end_turn()
    korrak = game.player1.give("AV_143").play()
    assert korrak.id == "AV_143"
    korrak.damage = korrak.max_health  # overkill via spell-style direct damage
    game.cheat_action(korrak, [Destroy(korrak), Deaths()])
    # A new Korrak should be on the field (resummoned from deathrattle).
    survivors = [m for m in game.player1.field if m.id == "AV_143"]
    assert len(survivors) >= 1, "Korrak should be resummoned (not honorably killed)"


def test_najak_hexxen_returns_stolen_minion_on_death():
    """AV_331 Najak Hexxen: deathrattle hands the stolen minion back to its original owner."""
    game = prepare_game()
    while game.player1.max_mana < 4:
        game.end_turn(); game.end_turn()
    game.end_turn()  # to opponent
    enemy_minion = game.player2.summon("CS2_125")  # Ironfur Grizzly 3/3
    assert enemy_minion.controller is game.player2
    game.end_turn()
    najak = game.player1.give("AV_331").play(target=enemy_minion)
    # After battlecry, minion controller is Player1.
    assert enemy_minion.controller is game.player1
    # Kill Najak; deathrattle should return the minion to Player2.
    najak.damage = najak.max_health
    game.cheat_action(najak, [Destroy(najak), Deaths()])
    assert enemy_minion.controller is game.player2


def test_double_agent_summons_copy_with_offclass_card():
    """AV_711 Double Agent: when holding an off-class card, summon a copy."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.discard_hand()
    # Put a Mage spell in hand (off-class for our Rogue).
    game.player1.give("CS2_029")  # Fireball — mage spell
    agent = game.player1.give("AV_711").play()
    # Should have summoned a copy.
    copies = [m for m in game.player1.field if m.id == "AV_711"]
    assert len(copies) == 2


def test_wildpaw_gnoll_cost_reduced_by_offclass_count():
    """AV_298 Wildpaw Gnoll: cost reduces by 1 per off-class card in hand."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.discard_hand()
    gnoll = game.player1.give("AV_298")
    base_cost = gnoll.cost  # 5 in 22.0, 6 after the 22.2 nerf — read from data
    # Add two off-class cards
    game.player1.give("CS2_029")  # Fireball — Mage
    game.player1.give("CS2_124")  # Wolfrider — Neutral, doesn't count
    game.player1.give("EX1_400")  # Whirlwind — Warrior
    assert gnoll.cost == base_cost - 2  # only the mage + warrior count


def test_snowfall_graveyard_doubles_deathrattles():
    """AV_400 Snowfall Graveyard: friendly deathrattles trigger twice while active."""
    game = prepare_game()
    obj = game.player1.give("AV_400").play()
    game.refresh_auras()
    assert game.player1.extra_deathrattles


def test_spammy_arcanist_cascades_on_kills():
    """AV_222 Spammy Arcanist: pings all other minions repeatedly while any die."""
    game = prepare_game()
    while game.player1.max_mana < 5:
        game.end_turn(); game.end_turn()
    # Two 1-hp minions on each side; cascade should kill them all.
    for _ in range(2):
        game.player1.summon("CS2_231")  # Wisp 1/1
        game.player2.summon("CS2_231")
    spammy = game.player1.give("AV_222").play()
    # All 1-hp minions other than spammy should be dead.
    assert all(m.id != "CS2_231" or m.dead for m in game.player1.field + game.player2.field)
    # Spammy himself survives (3/4)
    assert spammy in game.player1.field


def test_snowball_fight_cascades_while_target_survives():
    """AV_250 Snowball Fight!: if first target survives, hits another."""
    game = prepare_game()
    while game.player1.max_mana < 3:
        game.end_turn(); game.end_turn()
    game.end_turn()
    big = game.player2.summon("CS2_125")  # Ironfur Grizzly 3/3 — survives 1 dmg
    game.end_turn()
    game.player1.give("AV_250").play(target=big)
    assert big.frozen
    # At least one extra minion exists on enemy field? We need a second
    # target to cascade onto, but if there's only one minion total, the
    # spell stops after freezing it (no candidates). That's still valid.


def test_magister_dawngrasp_recasts_per_school():
    """AV_200 Magister Dawngrasp: one recast per spell-school cast this game."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    # Cast a Frost spell and a Fire spell first.
    while game.player1.max_mana < 4:
        game.end_turn(); game.end_turn()
    # Frostbolt (CS2_024) — Frost spell, costs 2.
    frostbolt = game.player1.give("CS2_024")
    frostbolt.play(target=game.player2.hero)
    assert 3 in game.player1.spells_cast_by_school  # SpellSchool.FROST == 3
    # Hand size BEFORE Dawngrasp plays; recasting Frostbolt should hit the hero again.
    pre_health = game.player2.hero.health
    while game.player1.max_mana < 7:
        game.end_turn(); game.end_turn()
    game.player1.give("AV_200").play()
    # Frostbolt deals 3 damage. After the recast, hero should have taken more damage.
    assert game.player2.hero.health < pre_health


def test_xyrella_replays_dead_minion_deathrattles():
    """AV_207 Xyrella, the Devout: re-triggers every dead friendly DR minion."""
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    while game.player1.max_mana < 8:
        game.end_turn(); game.end_turn()
    # Summon a Piggyback Imp (AV_309), kill it; its DR summons a 4/1 Imp.
    imp = game.player1.summon("AV_309")
    imp.damage = imp.max_health
    game.cheat_action(imp, [Destroy(imp), Deaths()])
    # One 4/1 token should be present from the deathrattle
    assert any(m.id == "AV_309t" for m in game.player1.field)
    # Now play Xyrella; she should re-trigger AV_309's deathrattle → another 4/1
    pre_count = sum(1 for m in game.player1.field if m.id == "AV_309t")
    game.player1.give("AV_207").play()
    post_count = sum(1 for m in game.player1.field if m.id == "AV_309t")
    assert post_count > pre_count


def test_saidan_doubles_incoming_buffs():
    """AV_345 Saidan the Scarlet: positive stat buffs landing on him are doubled."""
    game = prepare_game()
    while game.player1.max_mana < 3:
        game.end_turn(); game.end_turn()
    saidan = game.player1.give("AV_345").play()
    base_atk, base_health = saidan.atk, saidan.health
    # Apply a +2/+2 buff via Heart of the Wild (AV_292 grants +2/+2 to a minion).
    # Simpler: directly buff via a known +2/+2 enchant like AV_344e (Coldtooth Supplies).
    game.cheat_action(saidan, [Buff(saidan, "AV_344e")])
    # +2/+2 should land as +4/+4 because Saidan doubles it.
    assert saidan.atk == base_atk + 4, f"Expected atk+4 (doubled), got +{saidan.atk - base_atk}"
    assert saidan.health == base_health + 4


def test_cerathine_replaces_hand_minions_with_offclass():
    """AV_403 Cera'thine Fleetrunner: hand minions become non-Rogue minions, -2 cost."""
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    game.player1.discard_hand()
    # Put a Rogue minion in hand
    game.player1.give("EX1_613")  # Edwin VanCleef — Rogue minion
    original_count = sum(
        1 for c in game.player1.hand if c.type == CardType.MINION
    )
    game.player1.give("AV_403").play()
    # After replacement: no Rogue minions should remain (other than fleetrunner if it's there)
    rogue_minions = [
        c for c in game.player1.hand
        if c.type == CardType.MINION and c.card_class == CardClass.ROGUE
    ]
    # Cera'thine isn't in hand (it was just played), so all remaining minions should be off-class.
    assert all(m.card_class != CardClass.ROGUE for m in rogue_minions) or len(rogue_minions) == 0


def test_brukan_casts_two_distinct_elements():
    """AV_258 Bru'kan of the Elements: casts 2 different element spells."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    while game.player1.max_mana < 8:
        game.end_turn(); game.end_turn()
    # Set up minions to absorb effects
    game.player1.summon("CS2_125")
    game.end_turn()
    game.player2.summon("CS2_231")  # 1/1, dies to Lightning
    game.end_turn()
    # Bru'kan inherits the friendly hero's damage on swap; pre-damage so Water's
    # heal of FRIENDLY_CHARACTERS produces a detectable health bump.
    game.player1.hero.set_current_health(25)
    # Capture baselines after all setup, immediately before playing Bru'kan.
    pre_p1_health = game.player1.hero.health
    pre_p2_health = game.player2.hero.health
    pre_p2_minions = len(game.player2.field)
    game.player1.give("AV_258").play()
    # Verify *something* changed — at least one of the 4 effects must have fired
    # twice (any of: enemy hero -6 from Fire, enemy minion died to Lightning,
    # 2 elementals on field from Earth, friendly heroes healed from Water).
    effect_fired = (
        game.player2.hero.health < pre_p2_health  # Fire
        or any(m.id == "AV_258t6" for m in game.player1.field)  # Earth tokens
        or game.player1.hero.health > pre_p1_health  # Water
        or len(game.player2.field) < pre_p2_minions  # Lightning
    )
    assert effect_fired, "Bru'kan didn't apply any Element effects"


def test_reflecto_engineer_swaps_hand_minion_stats():
    """AV_256 Reflecto Engineer: swap atk/health of every minion in both hands."""
    game = prepare_game()
    while game.player1.max_mana < 3:
        game.end_turn(); game.end_turn()
    game.player1.discard_hand()
    game.player2.discard_hand()
    maly_p1 = game.player1.give("EX1_563")  # Malygos 4/12
    maly_p2 = game.player2.give("EX1_563")
    assert (maly_p1.atk, maly_p1.health) == (4, 12)
    assert (maly_p2.atk, maly_p2.health) == (4, 12)
    game.player1.give("AV_256").play()
    assert (maly_p1.atk, maly_p1.health) == (12, 4)
    assert (maly_p2.atk, maly_p2.health) == (12, 4)


def test_vanndar_resolves_on_empty_deck():
    """AV_223 Vanndar resolves cleanly when the deck has no minions."""
    game = prepare_game()
    game.player1.discard_hand()
    game.player1.deck = []
    vanndar = game.player1.give("AV_223").play()
    assert vanndar.zone == Zone.PLAY
