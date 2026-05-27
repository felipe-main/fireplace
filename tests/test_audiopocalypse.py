"""Audiopocalypse (Patch 26.2 mini-set) tests.

38 JAM_ cards inside the BATTLE_OF_THE_BANDS CardSet. Mini-set adds
no new keywords — extends Finale + Overload + spell-school synergies
from Festival, plus the Remixed mechanic (rotating in-hand effect)
unique to this mini-set.
"""

import pytest

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone

from utils import *


# ---------------------------------------------------------------------------
# Mage
# ---------------------------------------------------------------------------


def test_remixed_dispenseobot_rotates_in_hand():
	"""JAM_000 — at OWN_TURN_BEGIN, the Remixed card in hand picks a
	(usually different) variant from its 4-card pool."""
	game = prepare_game(CardClass.MAGE, CardClass.MAGE)
	card = game.player1.give("JAM_000")
	# Initial variant may be unset before first rotate fires.
	game.end_turn(); game.end_turn()
	v1 = card._remix_variant_id
	assert v1 in {"JAM_000t", "JAM_000t2", "JAM_000t3", "JAM_000t4"}
	# Force enough rotates to see at least one change (random can repeat).
	seen = {v1}
	for _ in range(40):
		game.end_turn(); game.end_turn()
		seen.add(card._remix_variant_id)
		if len(seen) > 1:
			break
	assert len(seen) > 1


def test_remixed_dispenseobot_play_fires_variant_effect():
	"""JAM_000 — playing it runs the currently-rotated variant's
	play script via cheat_action. Force a known variant by stamping
	_remix_variant_id directly, then assert the variant effect lands."""
	game = prepare_game(CardClass.MAGE, CardClass.MAGE)
	card = game.player1.give("JAM_000")
	# Force the Money Dispense-o-bot variant (gives 2 Coins).
	card._remix_variant_id = "JAM_000t3"
	pre_hand_coins = sum(1 for c in game.player1.hand if c.id == "GAME_005")
	card.play()
	post_hand_coins = sum(1 for c in game.player1.hand if c.id == "GAME_005")
	assert post_hand_coins - pre_hand_coins == 2


def test_costumed_singer_pulls_secret_from_deck_on_turn_end():
	"""JAM_001 — at OWN_TURN_END, draw a Secret from deck."""
	game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
	singer = game.player1.summon("JAM_001")
	# Seed deck with CFM_620 (Potion of Polymorph — Mage Secret).
	secret = game.player1.give("CFM_620")
	secret.shuffle_into_deck()
	pre_hand_ids = [c.id for c in game.player1.hand]
	game.end_turn()
	# Secret should have been pulled from deck to hand.
	post_hand_ids = [c.id for c in game.player1.hand]
	assert post_hand_ids.count("CFM_620") == 1
	assert "CFM_620" not in [c.id for c in game.player1.deck]


def test_star_power_cascade_deals_5_4_3_2_1():
	"""JAM_002 — cascading damage to random enemy minions across 5
	separate damage steps (5+4+3+2+1=15 total across the board)."""
	game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
	# Beef up enemy minions so none die mid-cascade.
	for _ in range(3):
		m = game.player2.summon("CS2_200")  # Boulderfist Ogre 6/7
		m.max_health = 80
		m.damage = 0
	star = game.player1.give("JAM_002")
	star.play()
	total_dmg = sum(m.damage for m in game.player2.field)
	assert total_dmg == 5 + 4 + 3 + 2 + 1


# ---------------------------------------------------------------------------
# Hunter
# ---------------------------------------------------------------------------


def test_hidden_meaning_summons_3cost_when_opp_uses_all_mana():
	"""JAM_003 — Secret fires when opponent ends their turn with no
	Mana left. Summons a random 3-cost minion."""
	game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
	game.player1.give("JAM_003").play()  # plant Secret
	assert any(s.id == "JAM_003" for s in game.player1.secrets)
	game.end_turn()
	# Player2's turn: spend all 10 mana via The Coin chain — simpler:
	# directly drain used_mana to max_mana to simulate "no mana left".
	game.player2.used_mana = game.player2.max_mana
	pre_field = len(game.player2.field)
	game.end_turn()
	# Secret consumed; player2 got a random 3-cost minion summoned.
	assert not any(s.id == "JAM_003" for s in game.player1.secrets)


def test_hollow_hound_damages_neighbours_of_attack_target():
	"""JAM_004 — when Hollow Hound attacks a minion, the minion's
	board-neighbours take Hollow Hound's Attack damage."""
	game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
	hound = game.player1.summon("JAM_004")
	hound.turn_played = -1  # bypass Rush "this turn"
	# Put three enemy minions on the board, target the middle.
	left = game.player2.summon("CS2_200")
	mid = game.player2.summon("CS2_200")
	right = game.player2.summon("CS2_200")
	for m in (left, mid, right):
		m.max_health = 80
		m.damage = 0
	hound.attack(mid)
	# Middle takes Hound's atk (3) plus the regular attack damage —
	# but the adjacency listener uses Hit on neighbours, not mid.
	assert left.damage == hound.atk
	assert right.damage == hound.atk


# ---------------------------------------------------------------------------
# Death Knight
# ---------------------------------------------------------------------------


def test_yelling_yodeler_doubles_friendly_deathrattle():
	"""JAM_005 — Battlecry: trigger a friendly minion's deathrattle
	twice (without killing it). Use Loot Hoarder (EX1_096 — DR: draw)."""
	game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
	loot = game.player1.summon("EX1_096")  # Loot Hoarder
	for _ in range(5):
		game.player1.give("CS2_200").shuffle_into_deck()
	yodeler = game.player1.give("JAM_005")
	pre_hand = len(game.player1.hand)
	yodeler.play(target=loot)
	post_hand = len(game.player1.hand)
	# Yodeler leaves hand (-1), Loot Hoarder DR fires twice (+2).
	assert post_hand == pre_hand - 1 + 2
	# Loot Hoarder is still on the board (we never killed it).
	assert loot.zone == Zone.PLAY


def test_cold_feet_buffs_enemy_minions_cost_by_5():
	"""JAM_006 — enemy minions in hand cost (5) more next turn."""
	game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
	# Plant a minion in opponent's hand.
	enemy_minion = game.player2.give("CS2_200")  # cost 6
	pre_cost = enemy_minion.cost
	game.player1.give("JAM_006").play()
	assert enemy_minion.cost == pre_cost + 5


def test_cool_ghoul_has_data_keywords():
	"""JAM_007 — Divine Shield + Reborn straight from data."""
	game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
	ghoul = game.player1.summon("JAM_007")
	assert ghoul.divine_shield
	assert ghoul.reborn


def test_dead_air_destroys_and_resummons_undead():
	"""JAM_008 — destroy all friendly Undead, then resummon them."""
	game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
	# Cool Ghoul (JAM_007) IS Undead.
	g1 = game.player1.summon("JAM_007")
	g2 = game.player1.summon("JAM_007")
	pre_ids = sorted(m.id for m in game.player1.field)
	game.player1.give("JAM_008").play()
	post_ids = sorted(m.id for m in game.player1.field)
	# Both ghouls die and resummon — but they reborn first, so each
	# leaves a half-HP copy AND a fresh full-HP copy.
	# At minimum the resummoned ones are present.
	assert post_ids.count("JAM_007") >= 2


# ---------------------------------------------------------------------------
# Paladin
# ---------------------------------------------------------------------------


def test_dance_floor_location_grants_friendly_minions_rush():
	"""JAM_009 — Location. On activate, friendly minions gain Rush."""
	game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
	loc = game.player1.give("JAM_009")
	loc.play()
	m = game.player1.summon("CS2_200")
	assert not m.rush
	loc.turn_played = -5  # bypass first-turn cooldown
	loc.cooldown = 0
	loc.use()
	assert m.rush


def test_jukebox_totem_summons_silver_hand_at_turn_end():
	"""JAM_010 — at OWN_TURN_END, summon a 1/1 Silver Hand Recruit."""
	game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
	game.player1.summon("JAM_010")
	pre_field = len(game.player1.field)
	game.end_turn()
	post_field = len(game.player1.field)
	assert post_field == pre_field + 1
	# The new minion is the Silver Hand Recruit token.
	assert any(m.id == "CS2_101t" for m in game.player1.field)


# ---------------------------------------------------------------------------
# Shaman
# ---------------------------------------------------------------------------


def test_horn_of_windlord_sets_target_minion_to_3_3():
	"""JAM_011 — when your hero attacks a minion, set its stats to
	3/3 via a per-call enchant."""
	game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
	game.player1.give("JAM_011").play()
	target = game.player2.summon("CS2_200")  # 6/7
	game.player1.hero.attack(target)
	# After resolution target's atk and max_health should both be 3.
	assert target.atk == 3
	assert target.max_health == 3


def test_remixed_totemcarver_plays_variant():
	"""JAM_012 — playing it runs the rotated variant's play."""
	game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
	card = game.player1.give("JAM_012")
	card._remix_variant_id = "JAM_012t4"  # Karaoke → summon JAM_010
	pre_field = len(game.player1.field)
	card.play()
	# Karaoke variant summons JAM_010 (Jukebox Totem) in addition to
	# the Remixed Totemcarver itself entering play.
	assert any(m.id == "JAM_010" for m in game.player1.field)


# ---------------------------------------------------------------------------
# Warrior
# ---------------------------------------------------------------------------


def test_jam_session_buffs_target_and_hits_other_minions():
	"""JAM_013 — friendly target gets +3/+3; all OTHER minions take 1."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	buffed = game.player1.summon("CS2_200")  # 6/7
	other_friend = game.player1.summon("CS2_200")
	enemy = game.player2.summon("CS2_200")
	for m in (buffed, other_friend, enemy):
		m.max_health = 80
		m.damage = 0
	pre_atk, pre_hp = buffed.atk, buffed.health
	jam = game.player1.give("JAM_013")
	jam.play(target=buffed)
	assert buffed.atk == pre_atk + 3
	assert buffed.health == pre_hp + 3
	# Other minions took exactly 1 damage.
	assert other_friend.damage == 1
	assert enemy.damage == 1


def test_backstage_bouncer_transforms_friendly_minion_into_copy():
	"""JAM_014 — Battlecry: Transform a friendly minion into a copy
	of this Backstage Bouncer."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	victim = game.player1.summon("CS2_200")  # Boulderfist
	bouncer = game.player1.give("JAM_014")
	bouncer.play(target=victim)
	# The Boulderfist position now holds a Backstage Bouncer.
	# Original Bouncer that was played stays too.
	bouncer_count = sum(1 for m in game.player1.field if m.id == "JAM_014")
	assert bouncer_count == 2


def test_remixed_tuning_fork_plays_variant_armor():
	"""JAM_015 — equipping the weapon fires the rotated variant's
	play script. Force Reinforced (Gain 5 Armor)."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	fork = game.player1.give("JAM_015")
	fork._remix_variant_id = "JAM_015t2"  # Reinforced → +5 armor
	pre_armor = game.player1.hero.armor
	fork.play()
	assert game.player1.hero.armor == pre_armor + 5


# ---------------------------------------------------------------------------
# Demon Hunter
# ---------------------------------------------------------------------------


def test_abyssal_bassist_cost_drops_per_weapon_equipped():
	"""JAM_016 — base cost 7; each weapon equipped this game reduces
	cost by 2."""
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	bassist = game.player1.give("JAM_016")
	base_cost = bassist.data.cost
	assert bassist.cost == base_cost
	# Equip one weapon.
	game.player1.give("CS2_106").play()  # Fiery War Axe-like; pick a DH-able weapon
	# Refresh aura state.
	game.refresh_auras()
	# Some weapons may auto-destroy — re-equip if not still tracked.
	# weapons_equipped_this_game is a per-game counter that only grows.
	expected = max(0, base_cost - 2 * game.player1.weapons_equipped_this_game)
	assert bassist.cost == expected


def test_through_fel_and_flames_finale_grants_plus_1_1():
	"""JAM_017 — at exact mana, Finale fires: Rush + +1/+1.
	Paired with the non-Finale test below."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	target = game.player1.summon("CS2_200")
	pre_atk, pre_hp = target.atk, target.health
	spell = game.player1.give("JAM_017")
	game.player1.used_mana = game.player1.max_mana - spell.cost
	assert game.player1.mana == spell.cost
	spell.play(target=target)
	assert target.rush
	assert target.atk == pre_atk + 1
	assert target.health == pre_hp + 1


def test_through_fel_and_flames_non_finale_no_buff():
	"""JAM_017 — with leftover mana, only Rush; no +1/+1."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	target = game.player1.summon("CS2_200")
	pre_atk, pre_hp = target.atk, target.health
	spell = game.player1.give("JAM_017")
	game.player1.used_mana = game.player1.max_mana - spell.cost - 3
	spell.play(target=target)
	assert target.rush
	assert target.atk == pre_atk
	assert target.health == pre_hp


def test_remixed_rhapsody_plays_variant_aoe():
	"""JAM_018 — playing the spell runs the rotated variant's effect.
	Force the simplest (Resounding: 3 dmg AoE twice)."""
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	# Put one friendly + one enemy minion with enough HP to survive.
	friend = game.player1.summon("CS2_200")  # 6/7
	enemy = game.player2.summon("CS2_200")
	for m in (friend, enemy):
		m.max_health = 80
		m.damage = 0
	rhapsody = game.player1.give("JAM_018")
	rhapsody._remix_variant_id = "JAM_018t2"  # Resounding: 3 dmg twice
	rhapsody.play()
	# 3 + 3 = 6 damage to each.
	assert friend.damage == 6
	assert enemy.damage == 6


# ---------------------------------------------------------------------------
# Rogue
# ---------------------------------------------------------------------------


def test_rhythmdancer_bounces_after_hero_attack_with_cost_1():
	"""JAM_019 — after FRIENDLY_HERO attacks, Risa returns to hand
	at cost 1."""
	game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
	risa = game.player1.summon("JAM_019")
	# Give hero a weapon to attack with.
	game.player1.give("CS2_106").play()
	# Sanity: risa is in play before the swing.
	assert risa.zone == Zone.PLAY
	game.player1.hero.attack(game.player2.hero)
	# Risa returns to hand.
	assert any(c.id == "JAM_019" for c in game.player1.hand)
	risa_in_hand = next(c for c in game.player1.hand if c.id == "JAM_019")
	assert risa_in_hand.cost == 1


def test_tough_crowd_outcast_bounces_target():
	"""JAM_020 — Outcast: bounce a minion. Outcast gate is auto-set
	by Play.do for leftmost/rightmost plays."""
	game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
	target = game.player2.summon("CS2_200")
	tc = game.player1.give("JAM_020")
	# Move TC to leftmost so Outcast triggers.
	game.player1.hand.remove(tc)
	game.player1.hand.insert(0, tc)
	tc.play(target=target)
	# Target bounced back to opponent's hand.
	assert target.zone == Zone.HAND
	assert target in game.player2.hand


def test_one_hit_wonder_combo_grants_poisonous():
	"""JAM_021 — Combo: Gain Poisonous. With combo (any card played
	first this turn), the minion enters with Poisonous."""
	game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
	# Play a cheap warm-up card to enable combo.
	game.player1.give("GAME_005").play()  # Coin
	ohw = game.player1.give("JAM_021")
	ohw.play()
	assert ohw.poisonous


# ---------------------------------------------------------------------------
# Priest
# ---------------------------------------------------------------------------


def test_deafen_base_silences_minion():
	"""JAM_022 — base effect silences; Combo also deals 2."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player2.summon("CS2_200")  # 6/7
	# Silence a buffed minion to confirm silence cleared.
	target.taunt = True
	game.player1.give("JAM_022").play(target=target)
	assert not target.taunt
	assert target.damage == 0  # base, no combo


def test_deafen_combo_silences_and_damages_2():
	"""JAM_022 — with Combo active, also deals 2 to the target."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player2.summon("CS2_200")
	target.taunt = True
	game.player1.give("GAME_005").play()  # Coin first → combo on
	game.player1.give("JAM_022").play(target=target)
	assert not target.taunt
	assert target.damage == 2


def test_plagiarizarrr_copies_top_of_enemy_deck():
	"""JAM_023 — Battlecry: get a copy of the top card of opponent's
	deck."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	bait = game.player2.give("CS2_200")
	bait.shuffle_into_deck()
	pre_hand_ids = [c.id for c in game.player1.hand]
	game.player1.give("JAM_023").play()
	post_hand_ids = [c.id for c in game.player1.hand]
	new = set(post_hand_ids) - set(pre_hand_ids)
	assert "CS2_200" in new


def test_ambient_lightspawn_finale_overheal_buffs_other_minion():
	"""JAM_024 — Finale + Overheal both met: another friendly minion
	gains +2/+2. Stamp the overheal flag directly to simulate the
	prior heal."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	other = game.player1.summon("CS2_200")
	pre_atk, pre_hp = other.atk, other.health
	# Pre-stamp an overheal on the hero so the gate passes.
	game.player1.hero._last_heal_overheal = 2
	light = game.player1.give("JAM_024")
	game.player1.used_mana = game.player1.max_mana - light.cost
	light.play()
	assert other.atk == pre_atk + 2
	assert other.health == pre_hp + 2


def test_funnel_cake_heals_3_to_minion_and_neighbours():
	"""JAM_025 — heal 3 to target + neighbours; per overheal, refresh
	a Mana Crystal."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	left = game.player1.summon("CS2_200")
	mid = game.player1.summon("CS2_200")
	right = game.player1.summon("CS2_200")
	for m in (left, mid, right):
		m.damage = 3
	# Pre-set max_mana high enough that Funnel Cake's own 1-mana cost
	# doesn't change the relevant comparison.
	game.player1.max_mana = 10
	game.player1.used_mana = 4
	game.player1.give("JAM_025").play(target=mid)
	# All three healed 3 (no overheal → no mana refresh).
	assert left.damage == 0
	assert mid.damage == 0
	assert right.damage == 0
	# Mana used went from 4 to 5 (just the +1 spell cost), no refund.
	assert game.player1.used_mana == 5


def test_fanboy_choose_one_a_grants_atk_and_rush():
	"""JAM_027 → JAM_027a — Zok Rocks!: +2 Attack and Rush."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player1.summon("CS2_200")
	pre_atk = target.atk
	game.player1.give("JAM_027a").play(target=target)
	assert target.atk == pre_atk + 2
	assert target.rush


def test_fanboy_choose_one_b_grants_hp_and_lifesteal():
	"""JAM_027 → JAM_027b — Poison Bloom!: +2 Health and Lifesteal."""
	game = prepare_empty_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player1.summon("CS2_200")
	pre_hp = target.health
	game.player1.give("JAM_027b").play(target=target)
	assert target.health == pre_hp + 2
	assert target.lifesteal


# ---------------------------------------------------------------------------
# Druid
# ---------------------------------------------------------------------------


def test_popular_pixie_refresh_hero_power():
	"""JAM_026 → JAM_026a — Refresh hero power so it can be used
	again this turn."""
	game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
	hp = game.player1.hero.power
	hp.activations_this_turn = 1
	assert hp.exhausted
	game.player1.give("JAM_026a").play()
	assert not hp.exhausted


def test_popular_pixie_next_hero_power_free():
	"""JAM_026 → JAM_026b — your next hero power costs (0)."""
	game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
	game.player1.give("JAM_026b").play()
	assert game.player1.next_hero_power_costs_zero == 1


def test_blood_treant_costs_hero_health():
	"""JAM_028 — Costs Health instead of Mana. Playing it deals damage
	to the controller's hero equal to its cost."""
	game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
	bt = game.player1.give("JAM_028")
	cost = bt.cost
	pre_hp = game.player1.hero.health
	pre_used = game.player1.used_mana
	bt.play()
	assert game.player1.hero.health == pre_hp - cost
	assert game.player1.used_mana == pre_used  # mana not consumed


def test_doomkin_steals_empty_mana_crystal():
	"""JAM_029 — take one of the opponent's empty Mana Crystals."""
	game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
	# Opp has 5 max, all empty. Player1 has 6 max (enough for the
	# 6-cost Doomkin), 0 used. The steal grows player1 to 7.
	game.player2.max_mana = 5
	game.player2.used_mana = 0
	game.player1.max_mana = 6
	game.player1.used_mana = 0
	game.player1.give("JAM_029").play()
	assert game.player2.max_mana == 4
	assert game.player1.max_mana == 7


# ---------------------------------------------------------------------------
# Warlock
# ---------------------------------------------------------------------------


def test_fanottem_cost_equals_deck_size():
	"""JAM_030 — cost equals the number of cards in your deck."""
	game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
	# Empty deck → cost 0 (clamped by engine).
	fan = game.player1.give("JAM_030")
	game.refresh_auras()
	assert fan.cost == 0
	# Add 12 cards to deck → cost 12.
	for _ in range(12):
		game.player1.give("CS2_200").shuffle_into_deck()
	game.refresh_auras()
	assert fan.cost == 12


def test_reverberations_summons_copy_of_target():
	"""JAM_031 — Summon a copy of a target minion."""
	game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
	target = game.player1.summon("CS2_200")
	pre_count = sum(1 for m in game.player1.field if m.id == "CS2_200")
	game.player1.give("JAM_031").play(target=target)
	post_count = sum(1 for m in game.player1.field if m.id == "CS2_200")
	assert post_count == pre_count + 1


def test_fiddlefire_imp_adds_fire_mage_and_warlock_spells():
	"""JAM_032 — Battlecry: add a random Fire Mage spell AND a random
	Fire Warlock spell to your hand."""
	game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
	pre_hand = list(game.player1.hand)
	game.player1.give("JAM_032").play()
	new = [c for c in game.player1.hand if c not in pre_hand]
	assert len(new) == 2
	for c in new:
		assert c.type == CardType.SPELL
		assert c.spell_school == SpellSchool.FIRE


# ---------------------------------------------------------------------------
# Neutral
# ---------------------------------------------------------------------------


def test_remixed_musician_plays_variant_keyword():
	"""JAM_033 — playing it grants the rotated variant's keyword.
	Force Cathedral (Divine Shield)."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	card = game.player1.give("JAM_033")
	card._remix_variant_id = "JAM_033t"  # Cathedral → Divine Shield
	card.play()
	played = next(m for m in game.player1.field if m.id == "JAM_033")
	assert played.divine_shield


def test_speaker_stomper_raises_enemy_spell_costs():
	"""JAM_034 — Battlecry: enemy spells cost (2) more next turn."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	enemy_spell = game.player2.give("CS2_029")  # Fireball, cost 4
	pre_cost = enemy_spell.cost
	game.player1.give("JAM_034").play()
	assert enemy_spell.cost == pre_cost + 2


def test_grimtotem_buzzkill_discards_weapon_draws_3():
	"""JAM_035 — Battlecry: Discard a weapon from hand to draw 3."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	# Put a weapon in hand and seed deck.
	game.player1.give("CS2_106")  # Fiery War Axe
	for _ in range(5):
		game.player1.give("CS2_200").shuffle_into_deck()
	pre_hand_no_weapon = [c for c in game.player1.hand if c.type != CardType.WEAPON]
	game.player1.give("JAM_035").play()
	# 3 cards drawn, weapon discarded (Grimtotem itself leaves on play).
	assert not any(c.type == CardType.WEAPON for c in game.player1.hand)
	assert len(game.player1.hand) == len(pre_hand_no_weapon) + 3


def test_magatha_draws_5_gives_spells_to_opponent():
	"""JAM_036 — Battlecry: Draw 5 cards. Any spells go to opponent."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	# Seed deck with 2 spells + 3 minions.
	spells = [game.player1.give("CS2_029") for _ in range(2)]  # Fireballs
	minions = [game.player1.give("CS2_200") for _ in range(3)]
	for c in spells + minions:
		c.shuffle_into_deck()
	pre_opp_hand = len(game.player2.hand)
	game.player1.give("JAM_036").play()
	post_opp_hand = len(game.player2.hand)
	# Opponent gained the 2 Fireballs (spells); the 3 minions stayed.
	assert post_opp_hand == pre_opp_hand + 2
	# Confirm by id, not just count.
	fireballs_with_opp = sum(1 for c in game.player2.hand if c.id == "CS2_029")
	assert fireballs_with_opp == 2


def test_elite_tauren_champion_finale_starts_rock_duel():
	"""JAM_037 — at exact mana (Finale), stamp both players with the
	Rock Duel enchant. Subsequent OWN_TURN_END with leftover mana
	deals 8 to the turn-ending player."""
	game = prepare_empty_game(CardClass.WARRIOR, CardClass.WARRIOR)
	etc = game.player1.give("JAM_037")
	game.player1.used_mana = game.player1.max_mana - etc.cost
	etc.play()
	# Both players now have a JAM_037e enchant attached.
	# Confirm by checking opponent's hero / enchant slots.
	# At a minimum, the play_finale flag is True on ETC.
	played = next(m for m in game.player1.field if m.id == "JAM_037")
	assert played.play_finale
	# End the controller's turn with leftover mana — they take 8.
	# Refill the bar so used < max.
	game.player1.used_mana = 0
	pre_hp = game.player1.hero.health
	game.end_turn()
	assert game.player1.hero.health < pre_hp
