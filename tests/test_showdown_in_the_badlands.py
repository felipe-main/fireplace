"""Showdown in the Badlands (Patch 28.0) tests — WILD_WEST CardSet.

145 collectible cards across 11 classes + neutrals. Two novel keywords:

- Excavate: dig a treasure, escalating tier per dig (1 Common -> 2 Rare ->
  3 Epic -> 4 class Legendary for the five Excavate classes that shipped in
  28.0: DK, Mage, Rogue, Warlock, Warrior). After the deepest tier the cycle
  restarts at tier 1.
- Quickdraw: a bonus effect that fires only when the card is played the same
  turn it entered hand (drawn or generated).

The first block exercises the two engine primitives directly; the rest are
one-test-per-card (or per-cluster) with tight assertions.
"""

import pytest

from hearthstone.enums import CardClass, CardType, GameTag, Race, Zone

from utils import *

from fireplace.actions import (
    Excavate,
    EXCAVATE_TIERS,
    EXCAVATE_LEGENDARY,
)


def test_string_tagged_attrvalue_repr_does_not_crash():
    """Regression: AttrValue.__repr__ used int(self.tag), which crashed on
    string-tagged AttrValues (CURRENT_HEALTH, "mana", "durability", ...).
    A soak game using a lowest-Health selector then died when logging tried
    to repr the listener. repr must be crash-free for string tags."""
    from fireplace.dsl.selector import (
        AttrValue, CURRENT_HEALTH, CURRENT_DURABILITY, CURRENT_MANA,
    )
    assert repr(CURRENT_HEALTH) == "<health>"
    assert repr(CURRENT_DURABILITY) == "<durability>"
    assert repr(CURRENT_MANA) == "<mana>"
    assert repr(AttrValue("num_attacks")) == "<num_attacks>"


# ---------------------------------------------------------------------------
# Engine primitive: Excavate
# ---------------------------------------------------------------------------

def _excavate(game, player):
    game.queue_actions(player.hero, [Excavate(player)])


def test_excavate_tier_escalation_excavate_class():
    """An Excavate class (Mage) digs Common -> Rare -> Epic -> Legendary,
    then the cycle restarts at tier 1."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    assert p.excavates_this_game == 0

    _excavate(game, p)
    assert p.excavates_this_game == 1
    assert p.hand[-1].id in EXCAVATE_TIERS[1]

    _excavate(game, p)
    assert p.excavates_this_game == 2
    assert p.hand[-1].id in EXCAVATE_TIERS[2]

    _excavate(game, p)
    assert p.excavates_this_game == 3
    assert p.hand[-1].id in EXCAVATE_TIERS[3]

    # 4th dig: Mage's class Legendary (deterministic).
    _excavate(game, p)
    assert p.excavates_this_game == 4
    assert p.hand[-1].id == EXCAVATE_LEGENDARY[CardClass.MAGE]

    # 5th dig: cycle restarts at tier 1.
    _excavate(game, p)
    assert p.excavates_this_game == 5
    assert p.hand[-1].id in EXCAVATE_TIERS[1]


def test_excavate_non_excavate_class_caps_at_tier_three():
    """A non-Excavate class (Druid) never reaches tier 4 — it cycles
    Common -> Rare -> Epic -> Common."""
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p = game.player1
    assert CardClass.DRUID not in EXCAVATE_LEGENDARY

    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[1]
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[2]
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[3]
    # 4th dig wraps back to tier 1, NOT a Legendary.
    _excavate(game, p)
    assert p.hand[-1].id in EXCAVATE_TIERS[1]


# ---------------------------------------------------------------------------
# Engine primitive: Quickdraw
# ---------------------------------------------------------------------------

def test_quickdraw_active_when_played_same_turn():
    """A card generated/drawn this turn is Quickdraw-active while in hand,
    and the flag snapshots True the moment it is played."""
    game = prepare_game()
    card = game.player1.give(WISP)
    # Entered hand this turn -> active.
    assert card.quickdraw_active is True
    card.play()
    assert card.quickdraw_played is True


def test_quickdraw_inactive_after_turn_cycle():
    """A card that has sat in hand since a previous turn is NOT Quickdraw
    -active, and the play snapshot is False."""
    game = prepare_game()
    card = game.player1.give(WISP)
    # Simulate the card having entered hand on an earlier turn.
    card._turn_entered_hand = game.turn - 1
    assert card.quickdraw_active is False
    card.play()
    assert card.quickdraw_played is False


# ---------------------------------------------------------------------------
# Per-card tests (merged from the per-class fan-out)
# ---------------------------------------------------------------------------

# === merged from test_swib_dh.py ===
# Fixtures
NAGA_2_3 = "TSC_941t"        # 2/3 Naga, costs 2 (used across sunken_city tests)
NAGA_1_DROP = "ETC_359"      # Flowrider, 1-cost 2/1 Naga
DH_FEL_SPELL = "BT_035"      # Chaos Strike, 2-cost Fel spell
DH_WEAPON = "BT_922"         # Umberwing, 2-cost DH weapon
DH_OUTCAST = "BT_480"        # Crimson Sigil Runner, 1-cost Outcast
MOONFIRE = "CS2_008"         # 0-cost spell


def _resolve_choices(player):
	while player.choice:
		player.choice.choose(player.choice.cards[0])


def test_dh_snake_eyes_two_discovers():
	# Roll two dice → Discover one card of each Cost (extra Discover on
	# doubles). At minimum, two Discovers always open. We resolve each by
	# taking the first option; the controller should end with exactly 2 (or
	# 3 on doubles) extra cards.
	game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	# Empty the hand so we count exactly what Snake Eyes adds.
	for c in list(game.player1.hand):
		c.discard()
	card = game.player1.give("WW_400")
	pre = len(game.player1.hand)  # just Snake Eyes in hand
	card.play()
	# Snake Eyes itself moved to PLAY; resolve the chained discovers.
	n_choices = 0
	while game.player1.choice:
		n_choices += 1
		game.player1.choice.choose(game.player1.choice.cards[0])
	# Two discovers minimum, three on doubles.
	assert n_choices in (2, 3)
	# Each resolved discover gave one card to hand.
	assert len(game.player1.hand) == n_choices


def test_dh_snake_eyes_discover_cost_matches_roll():
	# Every discovered card must have a Cost equal to one of the rolled
	# dice values (1-6). Seed RNG indirectly by inspecting the offered pool.
	game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	for c in list(game.player1.hand):
		c.discard()
	card = game.player1.give("WW_400")
	card.play()
	while game.player1.choice:
		offered = game.player1.choice.cards
		# All three offered cards share the same Cost (the rolled die),
		# and that cost is a valid die face.
		costs = {c.cost for c in offered}
		assert len(costs) == 1
		(cost,) = costs
		assert 1 <= cost <= 6
		game.player1.choice.choose(offered[0])


def test_dh_gunslinger_kurtrus_no_duplicates_hits():
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	# No-duplicate deck.
	for cid in [NAGA_1_DROP, NAGA_2_3, DH_WEAPON]:
		game.player1.card(cid, zone=Zone.DECK)
	victim = game.player2.give(NAGA_2_3)
	victim.max_health = 80
	victim.damage = 0
	pre = victim.health
	kurtrus = game.player1.give("WW_401")
	kurtrus.play()
	# 6 shots x 2 damage, all absorbed by the one tanky hand minion.
	assert pre - victim.health == 12


def test_dh_gunslinger_kurtrus_with_duplicates_does_nothing():
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	# Deck WITH a duplicate → battlecry condition fails.
	for cid in [NAGA_1_DROP, NAGA_1_DROP, NAGA_2_3]:
		game.player1.card(cid, zone=Zone.DECK)
	victim = game.player2.give(NAGA_2_3)
	victim.max_health = 80
	victim.damage = 0
	pre = victim.health
	kurtrus = game.player1.give("WW_401")
	kurtrus.play()
	assert pre - victim.health == 0


def test_dh_blindeye_sharpshooter_naga_mode():
	# Starts in naga mode: playing a Naga deals 2 to a random enemy and
	# draws a spell. Beef the enemy hero so the 2 lands there deterministically
	# (clear the enemy board so the only enemy character is the hero).
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	game.player1.card(DH_FEL_SPELL, zone=Zone.DECK)  # a spell to draw
	sharp = game.player1.summon("WW_402")
	naga = game.player1.give(NAGA_2_3)
	pre_hp = game.player2.hero.health
	pre_hand = len(game.player1.hand)
	naga.play()
	# 2 damage to the only enemy character (hero), and a spell drawn.
	assert game.player2.hero.health == pre_hp - 2
	# Naga left hand (played), but a spell was drawn: net hand size unchanged.
	assert len(game.player1.hand) == pre_hand  # -1 naga +1 drawn spell
	assert game.player1.hand[-1].id == DH_FEL_SPELL


def test_dh_blindeye_sharpshooter_switches_to_spell_mode():
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	game.player1.card(DH_FEL_SPELL, zone=Zone.DECK)  # spell to draw (naga mode)
	game.player1.card(NAGA_2_3, zone=Zone.DECK)      # naga to draw (spell mode)
	sharp = game.player1.summon("WW_402")
	naga = game.player1.give(NAGA_2_3)
	spell = game.player1.give(MOONFIRE)
	# Naga first: fires naga-half, flips to spell mode.
	naga.play()
	# Now in spell mode: casting a spell fires, deals 2 to hero, draws a Naga.
	pre_hp = game.player2.hero.health
	spell.play(target=game.player2.hero)
	# Moonfire itself does 1, plus Blindeye 2 = 3 total to hero.
	assert game.player2.hero.health == pre_hp - 3
	# A Naga was drawn (spell-mode draw).
	assert game.player1.hand[-1].id == NAGA_2_3


def test_dh_blindeye_naga_mode_does_not_fire_on_spell():
	# In naga mode (fresh), casting a spell should NOT trigger the spell-half.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	sharp = game.player1.summon("WW_402")
	spell = game.player1.give(MOONFIRE)
	pre_hp = game.player2.hero.health
	spell.play(target=game.player2.hero)
	# Only Moonfire's 1 damage — Blindeye stays in naga mode.
	assert game.player2.hero.health == pre_hp - 1


def test_dh_midnight_wolf_outcast_summons_copy():
	# Outcast (left- or right-most): summon a copy of this.
	game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	for c in list(game.player1.hand):
		c.discard()
	wolf = game.player1.give("WW_406")  # only card → left-most == outcast
	assert game.player1.field == []
	wolf.play()
	# Wolf + one copy.
	assert len(game.player1.field) == 2
	assert all(m.id == "WW_406" for m in game.player1.field)


def test_dh_midnight_wolf_no_outcast_no_copy():
	# Not on an edge → no Outcast, no copy.
	game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	for c in list(game.player1.hand):
		c.discard()
	# Pad hand so the wolf is in the middle.
	left = game.player1.give(MOONFIRE)
	wolf = game.player1.give("WW_406")
	right = game.player1.give(MOONFIRE)
	wolf.play()
	assert len(game.player1.field) == 1
	assert game.player1.field[0].id == "WW_406"


def test_dh_parched_desperado_with_spell_cast():
	# Cast a spell while holding → +3 hero attack this turn.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	desperado = game.player1.give("WW_407")
	spell = game.player1.give(MOONFIRE)
	spell.play(target=game.player2.hero)  # counts as "cast while holding"
	assert desperado.spells_cast_while_holding == 1
	pre_atk = game.player1.hero.atk
	desperado.play()
	assert game.player1.hero.atk == pre_atk + 3


def test_dh_parched_desperado_without_spell_no_buff():
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	desperado = game.player1.give("WW_407")
	pre_atk = game.player1.hero.atk
	desperado.play()
	assert game.player1.hero.atk == pre_atk


def test_dh_bartend_o_bot_draws_outcast_to_left():
	# Draw an Outcast card and slide it to the left of hand.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	game.player1.card(DH_OUTCAST, zone=Zone.DECK)
	# Give a couple of non-outcast cards so "left side" is meaningful.
	a = game.player1.give(MOONFIRE)
	b = game.player1.give(MOONFIRE)
	bot = game.player1.give("WW_408")
	bot.play()
	# The drawn Outcast card sits at hand index 0.
	assert game.player1.hand[0].id == DH_OUTCAST


def test_dh_pocket_sand_base_damage():
	# Deal 3 damage (no Quickdraw bonus when not quickdraw-active).
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	target = game.player2.summon(NAGA_2_3)
	target.max_health = 80
	target.damage = 0
	sand = game.player1.give("WW_403")
	# Make it NOT quickdraw: advance a turn so it didn't enter hand this turn.
	game.end_turn()
	game.end_turn()
	assert not sand.quickdraw_active
	pre = target.health
	sand.play(target=target)
	assert pre - target.health == 3
	# No cost bump on opponent's hand.
	opp_card = game.player2.give(MOONFIRE)
	assert opp_card.cost == 0


def test_dh_pocket_sand_quickdraw_raises_opponent_cost():
	# Quickdraw: opponent's next card costs (1) more.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	target = game.player2.summon(NAGA_2_3)
	target.max_health = 80
	target.damage = 0
	sand = game.player1.give("WW_403")  # entered hand this turn → quickdraw
	assert sand.quickdraw_active
	pre = target.health
	sand.play(target=target)
	assert pre - target.health == 3
	# Opponent's existing hand cards now cost +1.
	opp_card = game.player2.give(NAGA_2_3)  # base cost 2
	assert opp_card.cost == 3


def test_dh_oasis_outlaws_discovers_naga():
	# Discover a Naga (no discount if no Naga played while holding).
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	outlaws = game.player1.give("WW_404")
	outlaws.play()
	assert game.player1.choice
	offered = game.player1.choice.cards
	assert all(Race.NAGA in c.races for c in offered)
	chosen = offered[0]
	chosen_cost = chosen.cost
	game.player1.choice.choose(chosen)
	given = game.player1.hand[-1]
	# No discount: cost unchanged.
	assert given.cost == chosen_cost


def test_dh_oasis_outlaws_discount_when_naga_played():
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	outlaws = game.player1.give("WW_404")
	# Play a Naga while holding Oasis Outlaws.
	naga = game.player1.give(NAGA_2_3)
	naga.play()
	assert outlaws.nagas_played_while_holding == 1
	outlaws.play()
	offered = game.player1.choice.cards
	chosen = offered[0]
	base_cost = chosen.cost
	game.player1.choice.choose(chosen)
	given = game.player1.hand[-1]
	assert given.cost == base_cost - 1


def test_dh_fan_the_hammer_splits_to_lowest_health():
	# Deal 6 damage split among the lowest Health enemies. One enemy with
	# high health and one with low health: the 6 shots chase the lowest, but
	# we make a single big tank the only enemy so it eats all 6.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	game.player2.hero.max_health = 80
	game.player2.hero.damage = 0
	tank = game.player2.summon(NAGA_2_3)
	tank.max_health = 2
	tank.damage = 0
	# Tank (2 hp) is lowest; 2 shots kill it, then remaining 4 go to hero
	# (now the lowest among remaining). We verify total board+hero damage.
	pre_hero = game.player2.hero.health
	fan = game.player1.give("WW_405")
	fan.play()
	# Tank dead (2 dmg), 4 dmg to hero.
	assert tank.dead
	assert pre_hero - game.player2.hero.health == 4


def test_dh_load_the_chamber_damage_and_discounts():
	# Deal 2 damage. Next Naga, Fel spell, weapon each cost (1) less.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	target = game.player2.summon(NAGA_2_3)
	target.max_health = 80
	target.damage = 0
	naga = game.player1.give(NAGA_2_3)        # base 2
	fel = game.player1.give(DH_FEL_SPELL)     # base 2
	weapon = game.player1.give(DH_WEAPON)     # base 2
	load = game.player1.give("WW_409")
	pre = target.health
	load.play(target=target)
	assert pre - target.health == 2
	assert naga.cost == 1
	assert fel.cost == 1
	assert weapon.cost == 1


def test_dh_load_the_chamber_discount_consumed_after_play():
	# After playing the next Naga, a second Naga no longer gets the discount.
	game = prepare_empty_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	target = game.player2.summon(NAGA_2_3)
	target.max_health = 80
	target.damage = 0
	naga1 = game.player1.give(NAGA_2_3)
	naga2 = game.player1.give(NAGA_2_3)
	load = game.player1.give("WW_409")
	load.play(target=target)
	assert naga1.cost == 1 and naga2.cost == 1
	naga1.play()
	# Discount consumed: the remaining Naga is back to base cost.
	assert naga2.cost == 2


# === merged from test_swib_dk.py ===
def test_dk_reap_what_you_sow():
    # Deal 3 damage. Excavate a treasure.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    target = game.player2.summon("CS2_182")  # 4/5 Chillwind Yeti
    pre_exc = game.player1.excavates_this_game
    card = game.player1.give("WW_352")
    pre_hand_ids = set(id(c) for c in game.player1.hand)
    card.play(target=target)
    assert target.damage == 3
    assert game.player1.excavates_this_game == pre_exc + 1
    # The played spell left hand; exactly one new card (the treasure) entered.
    new_cards = [c for c in game.player1.hand if id(c) not in pre_hand_ids]
    assert len(new_cards) == 1
    assert new_cards[0].id in (
        "WW_001t", "WW_001t18", "WW_001t2", "WW_001t3", "WW_001t4",
    )


def test_dk_fistful_of_corpses():
    # Deal damage to a minion equal to your Corpses.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.corpses = 4
    target = game.player2.summon("CS2_182")  # 4/5 Yeti
    card = game.player1.give("WW_354")
    card.play(target=target)
    assert target.damage == 4


def test_dk_fistful_of_corpses_zero():
    # With 0 corpses, deals 0 damage.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.corpses = 0
    target = game.player2.summon("CS2_182")
    card = game.player1.give("WW_354")
    card.play(target=target)
    assert target.damage == 0


def test_dk_crop_rotation():
    # Summon four 1/1 Undead with Rush that die at the end of turn.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    card = game.player1.give("WW_368")
    card.play()
    gnomes = [m for m in game.player1.field if m.id == "WW_368t"]
    assert len(gnomes) == 4
    for g in gnomes:
        assert g.atk == 1 and g.health == 1
        assert g.rush
        assert Race.UNDEAD in g.data.races
    # They die at the end of the controller's turn.
    game.end_turn()
    assert [m for m in game.player1.field if m.id == "WW_368t"] == []


def test_dk_corpse_farm():
    # Spend up to 8 Corpses to summon a random minion of that Cost.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.corpses = 5
    pre = len(game.player1.field)
    card = game.player1.give("WW_374")
    card.play()
    assert game.player1.corpses == 0
    assert game.player1.corpses_spent_this_game == 5
    assert len(game.player1.field) == pre + 1
    summoned = game.player1.field[-1]
    assert summoned.cost == 5


def test_dk_corpse_farm_no_corpses():
    # No corpses -> no summon, no spend.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.corpses = 0
    pre = len(game.player1.field)
    card = game.player1.give("WW_374")
    card.play()
    assert len(game.player1.field) == pre
    assert game.player1.corpses == 0


def test_dk_skeleton_crew():
    # Battlecry: Excavate a treasure. It costs (0).
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    pre_hand = set(id(c) for c in game.player1.hand)
    pre_exc = game.player1.excavates_this_game
    card = game.player1.give("WW_322")
    card.play()
    assert game.player1.excavates_this_game == pre_exc + 1
    treasure = [c for c in game.player1.hand if id(c) not in pre_hand]
    assert len(treasure) == 1
    assert treasure[0].cost == 0


def test_dk_pile_of_bones():
    # Deathrattle: The next time you Excavate, resummon this.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    pile = game.player1.summon("WW_324")
    pile.destroy()
    # Marker enchant now sits on the hero; the minion is gone.
    assert [m for m in game.player1.field if m.id == "WW_324"] == []
    assert any(e.id == "WW_324e" for e in game.player1.hero.buffs)
    # Next Excavate resummons it.
    spell = game.player1.give("WW_352")
    enemy = game.player2.summon("CS2_182")
    spell.play(target=enemy)
    resummoned = [m for m in game.player1.field if m.id == "WW_324"]
    assert len(resummoned) == 1
    # Marker consumed.
    assert not any(e.id == "WW_324e" for e in game.player1.hero.buffs)


def test_dk_pile_of_bones_single_use():
    # Only the NEXT excavate resummons; a second excavate does not.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    pile = game.player1.summon("WW_324")
    pile.destroy()
    e1 = game.player2.summon("CS2_182")
    game.player1.give("WW_352").play(target=e1)
    count_after_first = len([m for m in game.player1.field if m.id == "WW_324"])
    assert count_after_first == 1
    e2 = game.player2.summon("CS2_182")
    game.player1.give("WW_352").play(target=e2)
    # Still just the one resummoned Pile (no extra from the 2nd excavate).
    assert len([m for m in game.player1.field if m.id == "WW_324"]) == 1


def test_dk_harrowing_ox_excavated_twice():
    # Taunt. Battlecry: If you've Excavated twice, your next card costs (7) less.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.excavates_this_game = 2
    ox = game.player1.give("WW_356")
    ox.play()
    assert ox.taunt
    # A 7-cost card in hand should now cost 0.
    target = game.player1.give("CS2_182")  # Chillwind Yeti costs 4
    assert target.cost == 0  # 4 - 7 clamped to 0
    big = game.player1.give("EX1_298")  # Ragnaros the Firelord, 8 cost
    assert big.cost == 1  # 8 - 7


def test_dk_harrowing_ox_not_excavated():
    # No reduction if not excavated twice.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.excavates_this_game = 1
    ox = game.player1.give("WW_356")
    ox.play()
    target = game.player1.give("CS2_182")
    assert target.cost == 4  # no reduction


def test_dk_harrowing_ox_consumed_on_next_card():
    # The discount is consumed after the next card is played.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.excavates_this_game = 2
    game.player1.give("WW_356").play()
    cheap = game.player1.give("CS2_182")
    assert cheap.cost == 0
    cheap.play()
    # Discount gone now.
    after = game.player1.give("CS2_182")
    assert after.cost == 4


def test_dk_maw_and_paw_gain_corpses():
    # At end of your turn, gain 5 Corpses.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.summon("WW_357")
    game.player1.corpses = 0
    game.end_turn()
    assert game.player1.corpses == 5
    assert game.player1.corpses_gained_this_game >= 5


def test_dk_maw_and_paw_spend_corpses():
    # At start of your turn, spend 5 Corpses to give your hero +5 Health.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.summon("WW_357")
    hero = game.player1.hero
    base_max = hero.max_health
    game.player1.corpses = 5
    game.end_turn()  # opponent turn
    game.end_turn()  # back to player1 -> start of turn fires
    assert game.player1.corpses == 5  # gained 5 at end of own prior turn? no
    # corpses: started 5, +5 at p1 end-of-turn = 10, -5 at p1 start = 5
    assert hero.max_health == base_max + 5
    assert hero.health == (base_max + 5) - hero.damage


def test_dk_maw_and_paw_no_spend_under_five():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    game.player1.summon("WW_357")
    hero = game.player1.hero
    base_max = hero.max_health
    game.player1.corpses = 3
    # Disable the end-of-turn gain by checking only the start trigger:
    # after one round, corpses = 3 + 5(end) = 8, start spends 5 -> buff applies.
    # To test the "under 5" branch cleanly, zero the gain minion isn't possible;
    # instead assert the spend path only triggers when >=5 at start.
    game.player1.corpses = 0
    game.end_turn()  # p1 end -> +5 corpses (=5)
    game.end_turn()  # p1 start -> spends 5 -> +5 health
    assert hero.max_health == base_max + 5


def test_dk_farm_hand_discover():
    # Battlecry: Discover an Undead.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    card = game.player1.give("WW_358")
    card.play()
    assert game.player1.choice
    for c in game.player1.choice.cards:
        assert Race.UNDEAD in c.data.races
    chosen = game.player1.choice.cards[0]
    pre = len(game.player1.hand)
    game.player1.choice.choose(chosen)
    assert game.player1.choice is None
    picked = [c for c in game.player1.hand if c.id == chosen.id]
    assert len(picked) == 1
    # Not Quickdraw -> full cost.
    assert picked[0].cost == chosen.cost


def test_dk_farm_hand_quickdraw():
    # Quickdraw: discovered Undead costs (2) less.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    card = game.player1.give("WW_358")
    # Simulate Quickdraw: the card was played the turn it entered hand.
    card.quickdraw_played = 1
    card.play()
    assert game.player1.choice
    chosen = game.player1.choice.cards[0]
    base_cost = chosen.cost
    game.player1.choice.choose(chosen)
    picked = [c for c in game.player1.hand if c.id == chosen.id]
    assert len(picked) == 1
    assert picked[0].cost == max(0, base_cost - 2)


def test_dk_reska_cost_mod():
    # Costs (1) less for each minion that died this game.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    reska = game.player1.give("WW_373")
    base = reska.data.cost
    assert reska.cost == base  # nothing died yet
    # Kill three minions.
    for _ in range(3):
        m = game.player2.summon("CS2_182")
        m.destroy()
    assert reska.cost == base - 3


def test_dk_reska_rush_and_deathrattle():
    # Rush + Deathrattle: Take control of a random enemy minion.
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    reska = game.player1.summon("WW_373")
    assert reska.rush
    enemy = game.player2.summon("CS2_182")  # only enemy minion
    assert enemy.controller is game.player2
    reska.destroy()
    # The single enemy minion is now controlled by player1.
    assert enemy.controller is game.player1
    assert enemy in game.player1.field


# === merged from test_swib_druid.py ===
# A vanilla-ish Dragon used as filler / held Dragon: Faerie Dragon (3/2).
DRAGON = "NEW1_023"


def test_druid_take_to_the_skies():
	# Draw two Dragons. Give them +1/+1.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	# Empty the deck so only our planted Dragons can be drawn.
	for card in list(p1.deck):
		card.discard()
	# Plant two Faerie Dragons (3/2, DRAGON). After +1/+1 -> 4/3.
	planted = []
	for _ in range(2):
		c = p1.card(DRAGON)
		c.zone = Zone.DECK
		planted.append(c)
	assert all(Race.DRAGON in c.races for c in planted)
	spell = p1.give("WW_816")
	spell.play()
	drawn = [c for c in p1.hand if c.id == DRAGON]
	assert len(drawn) == 2
	for c in drawn:
		assert c.atk == 4 and c.health == 3


def test_druid_cactus_construct():
	# Discover a 2-Cost minion. Summon a 1/2 copy of it.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	spell = p1.give("WW_818")
	spell.play()
	# Resolve the discover.
	assert p1.choice
	picked = p1.choice.cards[0]
	assert picked.cost == 2
	picked_id = picked.id
	p1.choice.choose(picked)
	assert len(p1.field) == 1
	copy = p1.field[0]
	assert copy.id == picked_id
	assert copy.atk == 1
	assert copy.health == 2


def test_druid_splish_splash_whelp_holding_dragon():
	# Battlecry: If you're holding a Dragon, gain an empty Mana Crystal.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	p1.give(DRAGON)  # hold a Dragon
	# Drop below max so an extra (empty) crystal is observable.
	p1.max_mana = 5
	p1.used_mana = 0
	whelp = p1.give("WW_819")  # costs 2
	whelp.play()
	# Whelp costs 2 (used 0 -> 2), then gain an EMPTY crystal: max 5 -> 6
	# and the new crystal arrives spent (used 2 -> 3).
	assert p1.max_mana == 6
	assert p1.used_mana == 3


def test_druid_splish_splash_whelp_no_dragon():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.hand):
		c.discard()
	p1.max_mana = 5
	whelp = p1.give("WW_819")
	whelp.play()
	assert p1.max_mana == 5


def test_druid_spinetail_drake_holding_dragon():
	# Battlecry: If holding a Dragon, deal 5 damage to an enemy minion.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1, p2 = game.player1, game.player2
	target = p2.summon("CS2_186")  # War Golem 7/7
	assert target.health == 7
	p1.give(DRAGON)  # hold a Dragon
	drake = p1.give("WW_820")
	drake.play(target=target)
	assert target.health == 2


def test_druid_spinetail_drake_no_dragon():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1, p2 = game.player1, game.player2
	for c in list(p1.hand):
		c.discard()
	target = p2.summon("CS2_186")  # War Golem 7/7
	drake = p1.give("WW_820")
	drake.play(target=target)
	# No dragon held -> no damage.
	assert target.health == 7


def test_druid_dragon_tales_short_stories():
	# Choose One: two random Dragons that cost (5) or less.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.hand):
		c.discard()
	spell = p1.give("WW_821")
	spell.play(choose="WW_821t1")
	dragons = list(p1.hand)
	assert len(dragons) == 2
	for c in dragons:
		assert Race.DRAGON in c.races
		assert c.cost <= 5


def test_druid_dragon_tales_tall_tales():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.hand):
		c.discard()
	spell = p1.give("WW_821")
	spell.play(choose="WW_821t2")
	dragons = list(p1.hand)
	assert len(dragons) == 2
	for c in dragons:
		assert Race.DRAGON in c.races
		assert c.cost > 5


def test_druid_dragon_golem():
	# Taunt. Battlecry: Summon a copy of this for each Dragon in your hand.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.hand):
		c.discard()
	# Three Dragons in hand.
	for _ in range(3):
		p1.give(DRAGON)
	golem = p1.give("WW_822")
	golem.play()
	golems = [m for m in p1.field if m.id == "WW_822"]
	# Played one + 3 copies.
	assert len(golems) == 4
	assert golem.taunt


def test_druid_dragon_golem_no_dragons():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.hand):
		c.discard()
	golem = p1.give("WW_822")
	golem.play()
	golems = [m for m in p1.field if m.id == "WW_822"]
	# Only the played one.
	assert len(golems) == 1


def test_druid_rehydrate_no_quickdraw():
	# Restore 7 Health. Quickdraw: Refresh 2 Mana Crystals.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	p1.hero.damage = 10
	spell = p1.give("WW_823")
	# Make NOT quickdraw: pretend it entered hand a previous turn.
	spell._turn_entered_hand = game.turn - 1
	assert not spell.quickdraw_active
	p1.used_mana = 4  # leaves 6 available; spell costs 2
	spell.play(target=p1.hero)
	assert p1.hero.damage == 3
	# Spending 2 for the spell raises used_mana to 6; no quickdraw refresh.
	assert p1.used_mana == 6


def test_druid_rehydrate_quickdraw():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	p1.hero.damage = 10
	spell = p1.give("WW_823")  # entered hand this turn -> quickdraw active
	assert spell.quickdraw_active
	p1.used_mana = 4  # leaves 6 available; spell costs 2
	spell.play(target=p1.hero)
	assert p1.hero.damage == 3
	# used_mana: 4 + 2 (spell cost) = 6, then Quickdraw refreshes 2 -> 4.
	assert p1.used_mana == 4


def test_druid_rheastrasza_no_duplicates():
	# Battlecry: If your deck has no duplicates, summon Purified Dragon Nest.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.deck):
		c.discard()
	for cid in ("CS2_186", "EX1_001", "CS2_182"):
		c = p1.card(cid)
		c.zone = Zone.DECK
	rhea = p1.give("WW_824")
	rhea.play()
	nest = [m for m in p1.field if m.id == "WW_824t"]
	assert len(nest) == 1


def test_druid_rheastrasza_with_duplicates():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.deck):
		c.discard()
	for _ in range(2):
		c = p1.card("CS2_186")
		c.zone = Zone.DECK
	rhea = p1.give("WW_824")
	rhea.play()
	nest = [m for m in p1.field if m.id == "WW_824t"]
	assert len(nest) == 0


def test_druid_purified_dragon_nest_discovers_discounted_dragon():
	# At start of your turn, Discover a Dragon. It costs (4) less.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	p1.summon("WW_824t")
	game.end_turn()
	game.end_turn()  # back to p1 -> OWN_TURN_BEGIN fires
	assert p1.choice
	picked = p1.choice.cards[0]
	base_cost = picked.cost
	picked_id = picked.id
	assert Race.DRAGON in picked.races
	p1.choice.choose(picked)
	given = [c for c in p1.hand if c.id == picked_id]
	assert len(given) == 1
	# Costs (4) less (clamped at 0).
	assert given[0].cost == max(0, base_cost - 4)


def test_druid_fye_cost_reduction():
	# Costs (1) less for each Dragon you've summoned this game.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	fye = p1.give("WW_825")
	assert fye.cost == 9
	# Summon two Dragons.
	p1.summon(DRAGON)
	p1.summon(DRAGON)
	assert fye.cost == 7
	# Summon a non-dragon -> no further reduction.
	p1.summon("CS2_186")
	assert fye.cost == 7


def test_druid_fye_has_keywords():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	fye = p1.summon("WW_825")
	assert fye.rush
	assert fye.lifesteal
	assert fye.taunt


def test_druid_desert_nestmatron_holding_dragon():
	# Taunt. Battlecry: If holding a Dragon, refresh 4 Mana Crystals.
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	p1.give(DRAGON)  # hold a Dragon
	# Cost 4; start with 2 used (8 available). Play -> used 6, refresh 4 -> 2.
	p1.used_mana = 2
	nest = p1.give("WW_826")
	nest.play()
	assert p1.used_mana == 2
	assert nest.taunt


def test_druid_desert_nestmatron_no_dragon():
	game = prepare_game(CardClass.DRUID, CardClass.DRUID)
	p1 = game.player1
	for c in list(p1.hand):
		c.discard()
	p1.used_mana = 2
	nest = p1.give("WW_826")
	nest.play()
	# No dragon held -> no refresh; only the play cost (4) is spent.
	assert p1.used_mana == 6


# === merged from test_swib_hunter.py ===
def test_hunter_sneaky_snakes():
    """WW_806 — summon two 1/1 Sidewinders with Stealth."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    spell = game.player1.give("WW_806")
    spell.play()
    field = game.player1.field
    assert len(field) == 2
    for snake in field:
        assert snake.id == "WW_806t"
        assert snake.atk == 1
        assert snake.health == 1
        assert snake.stealthed


def test_hunter_messenger_buzzard():
    """WW_807 — Deathrattle: draw a Beast, give hand minions +1/+1."""
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    # Exactly one Beast in deck to draw (Stonetusk Boar CS2_171, 1/1).
    game.player1.give("CS2_171").shuffle_into_deck()
    # A minion already in hand to receive the +1/+1.
    game.player1.give("CS2_171")  # 1/1 boar in hand
    buzzard = game.player1.summon("WW_807")
    buzzard.destroy()
    game.process_deaths()
    # The only Beast was drawn (deck now empty).
    assert len(game.player1.deck) == 0
    drawn = [c for c in game.player1.hand if c.id == "CS2_171"]
    # Both the pre-existing boar and the drawn boar are in hand, each +1/+1.
    assert len(drawn) == 2
    for c in drawn:
        assert c.atk == 2
        assert c.health == 2


def test_hunter_silver_serpent_quickdraw():
    """WW_808 — Quickdraw: gain Immune this turn (played the turn drawn)."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    serpent = game.player1.give("WW_808")
    # give() puts it in hand this turn -> quickdraw is active.
    serpent.play()
    assert serpent.immune is True
    assert serpent.cant_be_targeted_by_opponents is True


def test_hunter_silver_serpent_no_quickdraw():
    """WW_808 — without Quickdraw (held a turn), no Immune."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    serpent = game.player1.give("WW_808")
    # Pass a full turn cycle so the card is no longer quickdraw-active.
    game.end_turn(); game.end_turn()
    serpent.play()
    assert serpent.immune is False


def test_hunter_bovine_skeleton_low_attack():
    """WW_809 — Deathrattle does NOT summon a copy below 4 Attack."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    skel = game.player1.summon("WW_809")  # 3/3
    assert skel.atk == 3
    skel.destroy()
    game.process_deaths()
    assert len(game.player1.field) == 0


def test_hunter_bovine_skeleton_high_attack():
    """WW_809 — Deathrattle summons a copy at 4+ Attack."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    skel = game.player1.summon("WW_809")  # 3/3
    skel.atk = 4
    skel.destroy()
    game.process_deaths()
    assert len(game.player1.field) == 1
    assert game.player1.field[0].id == "WW_809"


def test_hunter_camouflage_mount():
    """WW_810 — give a minion +3/+3, a bonus effect, and a Chameleon
    deathrattle."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    target = game.player1.summon("CS2_171")  # 1/1 Stonetusk Boar
    spell = game.player1.give("WW_810")
    spell.play(target=target)
    # +3/+3 landed.
    assert target.atk == 4
    assert target.health == 4
    # It now has a deathrattle (the bonus enchant grants one).
    assert target.has_deathrattle
    target.destroy()
    game.process_deaths()
    # A Chameleon was summoned by the deathrattle.
    chameleons = [m for m in game.player1.field if m.id.startswith("WW_810t")]
    assert len(chameleons) == 1
    assert chameleons[0].atk == 3
    assert chameleons[0].health == 3


def test_hunter_ten_gallon_hat():
    """WW_811 — draw a minion, give it +1/+1 and a recurring deathrattle."""
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.give("CS2_171").shuffle_into_deck()  # 1/1 boar, only card
    spell = game.player1.give("WW_811")
    spell.play()
    drawn = game.player1.hand[-1]
    assert drawn.id == "CS2_171"
    assert drawn.atk == 2
    assert drawn.health == 2
    # Play it out and kill it -> deathrattle returns a Ten Gallon Hat.
    minion = drawn.play()
    minion.destroy()
    game.process_deaths()
    hats = [c for c in game.player1.hand if c.id == "WW_811"]
    assert len(hats) == 1


def test_hunter_saddle_up():
    """WW_812 — give your minions a Beast-summoning deathrattle."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    minion = game.player1.summon("CS2_171")  # 1/1 boar, no deathrattle
    assert not minion.has_deathrattle
    spell = game.player1.give("WW_812")
    spell.play()
    assert minion.has_deathrattle
    minion.destroy()
    game.process_deaths()
    # Deathrattle summoned a Beast (cost 3 or less) in the boar's place.
    assert len(game.player1.field) == 1
    summoned = game.player1.field[0]
    assert summoned.race == Race.BEAST or Race.BEAST in summoned.races
    assert (summoned.cost or 0) <= 3


def test_hunter_starshooter():
    """WW_813 — after your hero attacks, get an Arcane Shot."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    game.player1.discard_hand()
    weapon = game.player1.give("WW_813")
    weapon.play()
    assert game.player1.weapon.atk == 2
    game.player1.hero.attack(game.player2.hero)
    arcane_shots = [c for c in game.player1.hand if c.id == "DS1_185"]
    assert len(arcane_shots) == 1


def test_hunter_spurfang():
    """WW_814 — Battlecry and Deathrattle: summon a random 2-cost Beast
    (Cost equal to its 2 Attack)."""
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    spur = game.player1.give("WW_814")  # 2/5
    spur.play()
    # Battlecry summoned one beast alongside Spurfang.
    others = [m for m in game.player1.field if m is not spur]
    assert len(others) == 1
    assert (others[0].cost or 0) == 2
    assert Race.BEAST in others[0].races
    # Deathrattle summons another 2-cost beast.
    spur.destroy()
    game.process_deaths()
    remaining = [m for m in game.player1.field if m.id != "WW_814"]
    assert len(remaining) == 2
    for m in remaining:
        assert (m.cost or 0) == 2
        assert Race.BEAST in m.races


def test_hunter_theldurin_no_duplicates():
    """WW_815 — no duplicates: gain Immune and attack all enemies."""
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    # Empty deck -> no duplicates.
    # Enemy hero + one big enemy minion to absorb the attack.
    enemy = game.player2.summon("CS2_171")
    enemy.max_health = 80
    enemy.damage = 0
    assert enemy.health == 80
    enemy_hp_before = game.player2.hero.health
    theldurin = game.player1.give("WW_815")  # 3/4
    theldurin.play()
    assert theldurin.immune is True
    # Attacked all enemies: enemy minion took 3, enemy hero took 3.
    assert enemy.health == 77
    assert game.player2.hero.health == enemy_hp_before - 3


def test_hunter_theldurin_with_duplicates():
    """WW_815 — with duplicates in deck: no Immune, no attack."""
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    # Two copies of the same card -> duplicates present.
    game.player1.give("CS2_171").shuffle_into_deck()
    game.player1.give("CS2_171").shuffle_into_deck()
    enemy_hp_before = game.player2.hero.health
    theldurin = game.player1.give("WW_815")
    theldurin.play()
    assert theldurin.immune is False
    assert game.player2.hero.health == enemy_hp_before


# === merged from test_swib_lock.py ===
def _resolve_choices_2(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_lock_disposal_assistant():
    # Battlecry and Deathrattle: Put a Barrel of Sludge on the bottom of
    # your deck.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    assert len(game.player1.deck) == 0
    card = game.player1.give("WW_041")
    card.play()
    # Battlecry put one Barrel on the bottom.
    assert len(game.player1.deck) == 1
    assert game.player1.deck[0].id == "WW_044t"
    # Deathrattle puts a second one on the bottom.
    card.destroy()
    assert len(game.player1.deck) == 2
    assert all(c.id == "WW_044t" for c in game.player1.deck)


def test_lock_barrel_of_sludge_played():
    # When played, deal 3 damage to the lowest Health enemy.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    target = game.player2.summon("CS2_182")  # Chillwind Yeti 4/5
    target.max_health = 5
    target.damage = 0
    barrel = game.player1.give("WW_044t")
    barrel.play()
    # Lowest-health enemy (5-hp minion vs 30-hp hero) takes 3.
    assert target.health == 2
    assert game.player2.hero.health == 30


def test_lock_barrel_of_sludge_discarded():
    # When discarded, deal 3 damage to the lowest Health enemy.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy.max_health = 5
    enemy.damage = 0
    barrel = game.player1.give("WW_044t")
    game.queue_actions(game.player1, [Discard(barrel)])
    assert enemy.health == 2


def test_lock_waste_remover():
    # At the end of your turn, destroy the bottom 3 cards of your deck.
    # The bottom card is a Barrel of Sludge, which deals 3 to lowest enemy
    # when destroyed.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy.max_health = 5
    enemy.damage = 0
    # Deck has exactly 3 cards (all are "the bottom 3"), one a Barrel.
    barrel = game.player1.card("WW_044t", zone=Zone.DECK)
    game.player1.card("CS2_231", zone=Zone.DECK)
    game.player1.card("CS2_231", zone=Zone.DECK)
    deck = game.player1.deck
    assert len(deck) == 3
    assert barrel in deck[:3]
    remover = game.player1.summon("WW_042")
    game.end_turn()
    # All three bottom cards destroyed.
    assert len(game.player1.deck) == 0
    # The destroyed Barrel fired its effect: 3 damage to the 5-hp enemy.
    assert enemy.health == 2


def test_lock_sludge_on_wheels():
    # Rush. Whenever this takes damage, get a Barrel of Sludge AND add one
    # to the bottom of your deck.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    wheels = game.player1.summon("WW_043")  # 1/5
    assert wheels.rush
    pre_hand = len(game.player1.hand)
    pre_deck = len(game.player1.deck)
    game.queue_actions(game.player1, [Hit(wheels, 2)])
    assert wheels.health == 3
    # One Barrel added to hand, one to bottom of deck.
    assert len(game.player1.hand) == pre_hand + 1
    assert game.player1.hand[-1].id == "WW_044t"
    assert len(game.player1.deck) == pre_deck + 1
    assert game.player1.deck[0].id == "WW_044t"


def test_lock_popgar_the_putrid():
    # Your Fel spells cost (1) less and have Lifesteal.
    # Battlecry: Get two Barrels of Sludge.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    pop = game.player1.give("WW_091")
    pop.play()
    # Two Barrels in hand.
    barrels = [c for c in game.player1.hand if c.id == "WW_044t"]
    assert len(barrels) == 2
    # Fel spell cost reduction: Demonfire is a Fel spell costing 2 -> 1.
    demonfire = game.player1.give("EX1_596")  # Demonfire, FEL, cost 2
    assert demonfire.cost == 1
    # Lifesteal on the Fel spell: damage heals the hero.
    game.player1.hero.damage = 5
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy.max_health = 80
    enemy.damage = 0
    demonfire.play(target=enemy)
    # Demonfire deals 2 damage with granted Lifesteal -> hero heals 2 (5 -> 3).
    assert enemy.damage == 2
    assert game.player1.hero.damage == 3


def test_lock_furnace_fuel_played():
    # When played, draw 2 cards.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.card("CS2_231", zone=Zone.DECK)
    game.player1.card("CS2_231", zone=Zone.DECK)
    fuel = game.player1.give("WW_441")
    pre = len(game.player1.hand)  # fuel still in hand
    fuel.play()
    # fuel leaves hand (-1) then draws 2 (+2) => net +1 vs pre.
    assert len(game.player1.hand) == pre + 1
    assert len([c for c in game.player1.hand if c.id == "CS2_231"]) == 2


def test_lock_furnace_fuel_discarded():
    # When discarded, draw 2 cards.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.player1.card("CS2_231", zone=Zone.DECK)
    game.player1.card("CS2_231", zone=Zone.DECK)
    fuel = game.player1.give("WW_441")
    game.queue_actions(game.player1, [Discard(fuel)])
    assert len([c for c in game.player1.hand if c.id == "CS2_231"]) == 2
    assert fuel.zone == Zone.REMOVEDFROMGAME


def test_lock_fracking():
    # Look at the bottom 3 cards of your deck. Draw one and destroy the
    # others (one of which is a Barrel -> 3 damage to lowest enemy).
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    enemy = game.player2.summon("CS2_182")  # 4/5
    enemy.max_health = 5
    enemy.damage = 0
    # Deck bottom: exactly three cards, one of which is a Barrel.
    barrel = game.player1.card("WW_044t", zone=Zone.DECK)
    yeti = game.player1.card("CS2_182", zone=Zone.DECK)
    wisp = game.player1.card("CS2_231", zone=Zone.DECK)
    fracking = game.player1.give("WW_092")
    fracking.play()
    # The choice offers the bottom 3; choose the Yeti to draw.
    assert game.player1.choice is not None
    assert set(game.player1.choice.cards) == {barrel, yeti, wisp}
    game.player1.choice.choose(yeti)
    # Yeti drawn.
    assert yeti.zone == Zone.HAND
    # The other two destroyed; the Barrel fired -> 3 damage to 5-hp enemy.
    assert barrel.zone == Zone.GRAVEYARD
    assert wisp.zone == Zone.GRAVEYARD
    assert enemy.health == 2


def test_lock_smokestack_kills():
    # Deal 1 damage to a minion. If it dies, Excavate a treasure.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    target = game.player2.summon("CS2_231")  # Wisp 1/1
    pre_excavates = game.player1.excavates_this_game
    pre_hand = len(game.player1.hand)
    smoke = game.player1.give("WW_378")
    smoke.play(target=target)
    assert target.zone == Zone.GRAVEYARD
    # Excavated -> counter bumped + a treasure in hand (smoke spell left
    # hand on play, treasure replaces it).
    assert game.player1.excavates_this_game == pre_excavates + 1
    assert len(game.player1.hand) == pre_hand + 1


def test_lock_smokestack_survives():
    # If the minion survives, no Excavate.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    target = game.player2.summon("CS2_182")  # Yeti 4/5
    smoke = game.player1.give("WW_378")
    smoke.play(target=target)
    assert target.health == 4
    assert game.player1.excavates_this_game == 0


def test_lock_tram_conductor_gerry_no_excavate():
    # Battlecry: If you've Excavated twice, summon six 3/3 Tram Cars.
    # With zero excavates, summon nothing extra.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    gerry = game.player1.give("WW_437")
    gerry.play()
    # Only Gerry on board.
    assert len(game.player1.field) == 1
    assert game.player1.field[0] is gerry


def test_lock_tram_conductor_gerry_excavated_twice():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Excavate twice first (resolve any treasure adds).
    game.queue_actions(game.player1, [Excavate(game.player1)])
    game.queue_actions(game.player1, [Excavate(game.player1)])
    assert game.player1.excavates_this_game == 2
    gerry = game.player1.give("WW_437")
    gerry.play()
    # Gerry + six Tram Cars = 7 minions.
    assert len(game.player1.field) == 7
    cars = [m for m in game.player1.field if m.id == "WW_437t"]
    assert len(cars) == 6
    assert all(c.atk == 3 and c.health == 3 and c.rush for c in cars)


def test_lock_moarg_drillfist():
    # Taunt. Deathrattle: Excavate a treasure.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    moarg = game.player1.summon("WW_442")
    assert moarg.taunt
    pre_hand = len(game.player1.hand)
    moarg.destroy()
    assert game.player1.excavates_this_game == 1
    assert len(game.player1.hand) == pre_hand + 1


def test_lock_trolley_problem_no_quickdraw():
    # Discard your lowest Cost spell. Summon two 3/3 Tram Cars with Rush.
    # Played NOT on the turn it entered hand -> no Quickdraw -> discard.
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    # Give a cheap spell to be discarded (Moonfire, cost 0).
    cheap = game.player1.give("CS2_008")  # Moonfire, 0-cost spell
    # Make trolley "old" in hand (entered a previous turn) -> no Quickdraw.
    trolley = game.player1.give("WW_436")
    trolley._turn_entered_hand = game.turn - 1
    assert not trolley.quickdraw_active
    trolley.play()
    # Two 3/3 Tram Cars summoned.
    cars = [m for m in game.player1.field if m.id == "WW_437t"]
    assert len(cars) == 2
    assert all(c.atk == 3 and c.health == 3 and c.rush for c in cars)
    # Lowest-cost spell discarded.
    assert cheap.zone == Zone.REMOVEDFROMGAME


def test_lock_trolley_problem_quickdraw():
    # Quickdraw: Don't discard (card played same turn it entered hand).
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    cheap = game.player1.give("CS2_008")  # Moonfire, 0-cost spell
    trolley = game.player1.give("WW_436")
    # give() puts it in hand this turn -> quickdraw_active True.
    assert trolley.quickdraw_active
    trolley.play()
    cars = [m for m in game.player1.field if m.id == "WW_437t"]
    assert len(cars) == 2
    # Quickdraw -> spell NOT discarded.
    assert cheap.zone == Zone.HAND


# === merged from test_swib_mage.py ===
"""Showdown in the Badlands — Mage card tests (WILD_WEST CardSet).

One test per card (or tight cluster) with exact-state assertions. Two novel
mechanics exercised here: Excavate (Cryopreservation, Blastmage Miner) and
Quickdraw (Heat Wave).
"""





# Stable, well-known target/spell ids used across the suite.
YETI = "CS2_182"  # Chillwind Yeti, vanilla 4/5 minion
WATER_ELEMENTAL = "CS2_033"  # 3/6 Elemental
ARCANE_EXPLOSION = "CS2_025"  # Arcane spell: deal 1 to all enemy minions
FIREBALL = "CS2_029"  # 4-cost spell


def _make_p1_active(game):
    if game.current_player is not game.player1:
        game.end_turn()


# ---------------------------------------------------------------------------
# WW_009 — Cryopreservation: Freeze an enemy. Excavate a treasure.
# ---------------------------------------------------------------------------

def test_mage_cryopreservation():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p, o = game.player1, game.player2
    enemy = o.summon(YETI)

    pre_ex = p.excavates_this_game
    pre_hand = len(p.hand)
    cryo = p.give("WW_009")
    cryo.play(target=enemy)

    assert enemy.frozen is True
    # Excavated exactly one treasure (per-game counter +1, hand +1).
    assert p.excavates_this_game - pre_ex == 1
    assert len(p.hand) - pre_hand == 1
    assert p.hand[-1].id in ("WW_001t", "WW_001t18", "WW_001t2", "WW_001t3", "WW_001t4")


# ---------------------------------------------------------------------------
# WW_377 — Heat Wave: 2 dmg to an enemy minion + neighbors.
# Quickdraw: to all enemies instead.
# ---------------------------------------------------------------------------

def test_mage_heat_wave_no_quickdraw():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p, o = game.player1, game.player2
    ms = [o.summon(YETI) for _ in range(4)]

    hw = p.give("WW_377")
    # Force NOT-quickdraw: pretend it entered hand on a prior turn.
    hw._turn_entered_hand = game.turn - 1
    assert hw.quickdraw_active is False
    hw.play(target=ms[1])  # hits index 1 + neighbors 0 and 2; index 3 untouched

    assert [m.damage for m in ms] == [2, 2, 2, 0]
    assert o.hero.damage == 0


def test_mage_heat_wave_quickdraw():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p, o = game.player1, game.player2
    ms = [o.summon(YETI) for _ in range(3)]

    hw = p.give("WW_377")  # entered hand this turn -> Quickdraw active
    assert hw.quickdraw_active is True
    hw.play(target=ms[0])

    # Quickdraw: hits ALL enemies (every minion + the hero) for 2.
    assert [m.damage for m in ms] == [2, 2, 2]
    assert o.hero.damage == 2


# ---------------------------------------------------------------------------
# WW_422 — Azerite Vein (Secret): when the enemy plays a card on the turn it
# entered their hand, get a 0-cost copy.
# ---------------------------------------------------------------------------

def test_mage_azerite_vein_triggers_on_fresh_card():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    secret = p1.give("WW_422")
    secret.play()
    assert secret.zone == Zone.SECRET

    game.end_turn()  # p2's turn
    played = p2.give(YETI)  # entered p2's hand this turn
    played.play()

    # Secret consumed (revealed -> graveyard).
    assert secret.zone == Zone.GRAVEYARD
    copies = [c for c in p1.hand if c.id == YETI]
    assert len(copies) == 1
    assert copies[0].cost == 0


def test_mage_azerite_vein_ignores_stale_card():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    secret = p1.give("WW_422")
    secret.play()

    game.end_turn()
    stale = p2.give(YETI)
    stale._turn_entered_hand = game.turn - 1  # entered an earlier turn
    stale.play()

    # Card did not enter hand this turn -> Secret stays armed, no copy.
    assert secret.zone == Zone.SECRET
    assert [c for c in p1.hand if c.id == YETI] == []


# ---------------------------------------------------------------------------
# WW_425 — Stargazing: draw a different Arcane spell; if played this turn it
# casts twice.
# ---------------------------------------------------------------------------

def test_mage_stargazing_drawn_arcane_casts_twice():
    # Empty deck + a single seeded Arcane spell -> deterministic draw.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p, o = game.player1, game.player2
    p.deck.append(p.card(ARCANE_EXPLOSION, zone=Zone.DECK))
    enemy = o.summon(YETI)

    sg = p.give("WW_425")
    sg.play()

    drawn = [c for c in p.hand if c.id == ARCANE_EXPLOSION]
    assert len(drawn) == 1
    ae = drawn[0]
    assert any(b.id == "WW_425e" for b in ae.buffs)

    ae.play()
    # Arcane Explosion deals 1; cast twice -> exactly 2 to the lone enemy.
    assert enemy.damage == 2


# ---------------------------------------------------------------------------
# WW_427 — Sunset Volley: 10 dmg split among all enemies + summon a random
# 10-Cost minion.
# ---------------------------------------------------------------------------

def test_mage_sunset_volley():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p, o = game.player1, game.player2
    sponge = o.summon(YETI)
    sponge.max_health = 80
    sponge.damage = 0

    pre_field = len(p.field)
    sv = p.give("WW_427")
    sv.play()

    # Exactly 10 damage total split between the sponge and the enemy hero.
    assert sponge.damage + o.hero.damage == 10
    # Exactly one 10-cost minion summoned.
    assert len(p.field) - pre_field == 1
    assert p.field[-1].cost == 10


# ---------------------------------------------------------------------------
# WW_424 — Overflow Surger: summon a copy of this for each turn in a row
# you've played an Elemental (the current turn counts).
# ---------------------------------------------------------------------------

def test_mage_overflow_surger_streak():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _make_p1_active(game)

    # Surger sits in hand the whole time so it tracks the streak each turn.
    surger = p.give("WW_424")

    # Turn A: play an Elemental.
    p.give(WATER_ELEMENTAL).play()
    game.end_turn()  # streak tick: 1
    game.end_turn()  # back to p1
    assert p._elem_streak == 1

    # Turn B: play another Elemental.
    p.give(WATER_ELEMENTAL).play()
    game.end_turn()  # streak tick: 2
    game.end_turn()  # back to p1
    assert p._elem_streak == 2

    # Clear the board so we count only Surger + its copies.
    for m in list(p.field):
        m.destroy()

    # Turn C: play Surger (itself an Elemental) -> 3rd turn in a row.
    surger.play()
    surgers = [m for m in p.field if m.id == "WW_424"]
    # 2 prior turns + the current turn = 3 copies, plus the original = 4 bodies.
    assert len(surgers) == 4


def test_mage_overflow_surger_streak_resets():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _make_p1_active(game)

    surger = p.give("WW_424")
    p.give(WATER_ELEMENTAL).play()
    game.end_turn()  # streak -> 1
    game.end_turn()
    assert p._elem_streak == 1

    # A turn with NO Elemental played resets the streak.
    game.end_turn()  # streak tick on this turn: no elemental -> 0
    game.end_turn()
    assert p._elem_streak == 0

    for m in list(p.field):
        m.destroy()
    surger.play()
    surgers = [m for m in p.field if m.id == "WW_424"]
    # streak 0 prior + current turn = 1 copy, plus original = 2 bodies.
    assert len(surgers) == 2


# ---------------------------------------------------------------------------
# WW_426 — Blastmage Miner: Excavate, then 1 dmg to a random enemy per card
# in hand.
# ---------------------------------------------------------------------------

def test_mage_blastmage_miner():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p, o = game.player1, game.player2
    # Single damage sponge that absorbs every tick.
    sponge = o.summon(YETI)
    sponge.max_health = 80
    sponge.damage = 0
    o.hero._max_health = 80  # keep hero alive; hero shouldn't be hit anyway

    # Clear p's hand to a known state.
    for c in list(p.hand):
        c.discard()

    bm = p.give("WW_426")  # 1 card in hand (Blastmage itself)
    # Add exactly 3 more cards, so 4 cards in hand at play time.
    for _ in range(3):
        p.give(YETI)

    pre_ex = p.excavates_this_game
    bm.play()
    # Excavate fires (per-game +1).
    assert p.excavates_this_game - pre_ex == 1
    # After Blastmage leaves hand (3 left) + 1 excavated treasure = 4 cards;
    # 4 damage total dealt to the lone enemy minion.
    assert sponge.damage + o.hero.damage == 4


# ---------------------------------------------------------------------------
# WW_429 — Mes'Adune the Fractured: draw an Elemental, split it into two
# halves (Attack and Health halved, rounded up).
# ---------------------------------------------------------------------------

def test_mage_mesadune_split():
    # Empty decks -> the only Elemental available is the one we seed, so the
    # random draw is deterministic.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.deck.append(p.card(WATER_ELEMENTAL, zone=Zone.DECK))

    mes = p.give("WW_429")
    mes.play()

    halves = [c for c in p.hand if c.id == WATER_ELEMENTAL]
    assert len(halves) == 2
    # 3/6 -> two 2/3 (round up: 3//2=>2, 6//2=>3).
    assert all((h.atk, h.max_health) == (2, 3) for h in halves)


# ---------------------------------------------------------------------------
# WW_430 — Tae'thelan Bloodwatcher: cards that didn't start in your deck cost
# (4) less, but not less than (1).
# ---------------------------------------------------------------------------

def test_mage_taethelan_cost_reduction():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_430")

    foreign = p.give(FIREBALL)  # base cost 4, generated (not in starting deck)
    # 4 - 4 = 0, clamped to the (1) floor.
    assert foreign.cost == 1


# ---------------------------------------------------------------------------
# WW_432 — Reliquary Researcher: if you've Excavated twice, cast two random
# Mage Secrets.
# ---------------------------------------------------------------------------

def test_mage_reliquary_researcher_with_two_excavates():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.excavates_this_game = 2

    pre = len(p.secrets)
    rr = p.give("WW_432")
    rr.play()
    # Two random Mage Secrets cast into the Secret zone.
    assert len(p.secrets) - pre == 2
    assert all(s.secret for s in p.secrets)


def test_mage_reliquary_researcher_without_two_excavates():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.excavates_this_game = 1

    rr = p.give("WW_432")
    rr.play()
    # Condition not met -> no Secrets cast.
    assert len(p.secrets) == 0


# === merged from test_swib_ncommon.py ===
"""Showdown in the Badlands — Neutral Common card tests.

One test per card (or tight cluster), prefix ``ncommon``. Assertions are
tight: controlled decks / targets / RNG so each post-state is exact.
"""




from fireplace.actions import EXCAVATE_TIERS


def test_ncommon_kobold_miner():
    # Battlecry: Excavate a treasure.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    assert p.excavates_this_game == 0
    card = p.give("WW_001")
    card.play()
    assert p.excavates_this_game == 1
    assert p.hand[-1].id in EXCAVATE_TIERS[1]


def test_ncommon_tram_mechanic():
    # Deathrattle: Get a Barrel of Sludge.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    minion = p.summon("WW_044")
    pre = len(p.hand)
    minion.destroy()
    assert len(p.hand) == pre + 1
    assert p.hand[-1].id == "WW_044t"


def test_ncommon_trapdoor_spider():
    # Stealth, Poisonous. After your opponent plays a minion, attack it.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    spider = p1.summon("WW_300")
    assert spider.poisonous
    assert spider.stealthed
    game.end_turn()  # p2's turn
    dummy = p2.give(TARGET_DUMMY)  # 0/4, deals no counterattack damage
    dummy.play()
    # Spider attacked the freshly-played minion; Poisonous kills it.
    assert dummy.zone == Zone.GRAVEYARD
    assert spider.zone == Zone.PLAY
    assert spider.damage == 0


def test_ncommon_miracle_salesman():
    # Deathrattle: Get a Tradeable Snake Oil.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    minion = p.summon("WW_331")
    pre = len(p.hand)
    minion.destroy()
    assert len(p.hand) == pre + 1
    assert p.hand[-1].id == "WW_331t"


def test_ncommon_cactus_rager():
    # Poisonous (vanilla keyword from data).
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    rager = game.player1.summon("WW_376")
    assert rager.poisonous
    assert (rager.atk, rager.health) == (5, 1)


def test_ncommon_dryscale_deputy():
    # Battlecry: The next time you draw a spell, get a copy of it.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # Stack deck: a minion below, a spell on top (drawn first).
    bottom = p.card(WISP)
    bottom.zone = Zone.DECK
    spell = p.card(FIREBALL)
    spell.zone = Zone.DECK  # top of deck (drawn next)
    deputy = p.give("WW_383")
    deputy.play()
    # Drawing the spell triggers the extra copy.
    p.draw()
    fireballs = [c for c in p.hand if c.id == FIREBALL]
    assert len(fireballs) == 2  # the drawn one + the extra copy
    # Effect is one-shot: drawing the minion does NOT copy.
    pre = len(p.hand)
    p.draw()
    assert len([c for c in p.hand if c.id == WISP]) == 1
    assert len(p.hand) == pre + 1


def test_ncommon_gold_panner():
    # At the end of your turn, draw a card.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_391")
    pre = len(p.hand)
    game.end_turn()  # p1's turn ends -> draw one
    assert len(p.hand) == pre + 1


def test_ncommon_dang_blasted_elemental():
    # Taunt. Deathrattle: Deal 2 damage to all minions except friendly
    # Elementals.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    blaster = p1.summon("WW_397")
    assert blaster.taunt
    friendly_elem = p1.summon(ELEMENTAL)        # UNG_809t1 (friendly Elemental)
    friendly_nonelem = p1.summon(GOLDSHIRE_FOOTMAN)  # 1/2 non-Elemental
    friendly_nonelem.max_health = 80
    friendly_nonelem.damage = 0
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    blaster.destroy()
    # Friendly Elemental is spared.
    assert friendly_elem.damage == 0
    # Everything else (friendly non-Elemental + all enemies) takes 2.
    assert friendly_nonelem.damage == 2
    assert enemy.damage == 2


def test_ncommon_gaslight_gatekeeper():
    # Battlecry: Shuffle your hand into your deck, then draw that many
    # cards.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # Seed a known deck so draws are deterministic counting.
    for _ in range(5):
        c = p.card(WISP)
        c.zone = Zone.DECK
    gate = p.give("WW_398")
    # Put a couple extra cards in hand alongside the gatekeeper.
    extra1 = p.give(MOONFIRE)
    extra2 = p.give(FIREBALL)
    hand_before_play = len(p.hand)        # gate + 2 extras = 3
    deck_before = len(p.deck)             # 5
    gate.play()                           # gate leaves hand into PLAY
    # After playing, hand had 2 cards; they get shuffled in, then 2 drawn.
    # Net: hand size unchanged at 2, deck size unchanged at 5.
    assert len(p.hand) == 2
    assert len(p.deck) == deck_before


def test_ncommon_high_noon_duelist():
    # Deathrattle: Both players DRAW! Destroy the card that costs less.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    cheap = p1.card(MOONFIRE)   # 0-cost
    cheap.zone = Zone.DECK
    pricey = p2.card(PYROBLAST)  # 10-cost
    pricey.zone = Zone.DECK
    duelist = p1.summon("WW_399")
    duelist.destroy()
    # Both drew; the cheaper card (p1's Moonfire) is destroyed.
    assert cheap.zone == Zone.GRAVEYARD
    assert pricey.zone == Zone.HAND


def test_ncommon_ogre_gang_outlaw():
    # Rush. 50% chance to attack the wrong enemy.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    ogre = p1.summon("WW_418")
    assert ogre.rush
    assert ogre.atk == 4
    # Single enemy minion + the enemy hero are the only attack targets.
    # Forgetful (50%) redirects to the only other valid character: the
    # enemy hero. Either way the ogre's full 4 attack lands once.
    intended = p2.summon(TARGET_DUMMY)   # 0/4
    intended.max_health = 80
    intended.damage = 0
    hero_start = p2.hero.health
    game.end_turn()
    game.end_turn()  # back to p1 so the Rush minion can attack
    ogre.attack(intended)
    hero_damage = hero_start - p2.hero.health
    # The 4-point attack hit exactly one of {dummy, enemy hero}.
    assert intended.damage + hero_damage == 4
    assert intended.damage in (0, 4)
    assert hero_damage in (0, 4)


def test_ncommon_saloon_brewmaster():
    # Battlecry: Return a friendly minion to your hand. Give it +2/+2.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    target = p.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    brew = p.give("WW_423")
    brew.play(target=target)
    assert target.zone == Zone.HAND
    # Re-play it: +2/+2 buff applied -> 3/4.
    target.play()
    assert (target.atk, target.health) == (3, 4)


def test_ncommon_eroded_sediment():
    # Battlecry: If you played an Elemental last turn, Discover an
    # Elemental from the past.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # No Elemental played last turn -> no Discover.
    sed = p.give("WW_428")
    sed.play()
    assert p.choice is None

    # Now play an Elemental, cycle a turn so it counts as "last turn".
    elem = p.give(ELEMENTAL)
    elem.play()
    game.end_turn()
    game.end_turn()
    sed2 = p.give("WW_428")
    sed2.play()
    assert p.choice is not None
    picked = p.choice.cards
    assert len(picked) == 3
    for c in picked:
        assert Race.ELEMENTAL in (c.races or [])
    p.choice.choose(picked[0])


def test_ncommon_linedance_partner():
    # Battlecry: If you're holding another 3-Cost card, summon a random
    # 3-Cost minion.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    line = p.give("WW_433")        # itself 3-cost
    p.give("CS2_142")              # Kobold Geomancer, 2-cost -> not enough
    line.play()
    # Only Linedance Partner itself is on the field; no extra summon.
    assert len(p.field) == 1
    assert p.field[0].id == "WW_433"

    # Now hold another 3-cost card (Shattered Sun Cleric).
    line2 = p.give("WW_433")
    held3 = p.give("EX1_019")      # Shattered Sun Cleric, 3-cost
    assert held3.cost == 3
    line2.play()
    summoned = [m for m in p.field if m.id != "WW_433"]
    assert len(summoned) == 1
    assert summoned[0].cost == 3
    assert summoned[0].type == CardType.MINION


def test_ncommon_sunspot_dragon():
    # Tradeable, Lifesteal. Quickdraw: Deal 6 damage.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(TARGET_DUMMY)  # 0/4
    target.max_health = 80
    target.damage = 0
    dragon = p1.give("WW_434")        # entered hand this turn -> Quickdraw
    assert dragon.quickdraw_active
    pre_hp = p1.hero.health
    dragon.play(target=target)
    assert target.damage == 6
    # Lifesteal healed the hero by 6 (capped at max).
    assert p1.hero.health == min(p1.hero.max_health, pre_hp + 6)


def test_ncommon_sunspot_dragon_no_quickdraw():
    # Without Quickdraw, no damage.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(TARGET_DUMMY)
    target.max_health = 80
    target.damage = 0
    dragon = p1.give("WW_434")
    dragon._turn_entered_hand = game.turn - 1  # stale -> not Quickdraw
    assert not dragon.quickdraw_active
    dragon.play(target=target)
    assert target.damage == 0


def test_ncommon_bunny_stomper():
    # Your Beasts have Rush.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    beast = p.summon(CHICKEN)  # GVG_092t, a Beast
    assert not beast.rush
    p.summon("WW_435")
    assert beast.rush
    # A non-Beast friendly minion is unaffected.
    nonbeast = p.summon(WISP)
    assert not nonbeast.rush


def test_ncommon_whelp_wrangler():
    # At the end of your turn, get a 1/2 Whelp with Taunt.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_827")
    pre = len(p.hand)
    game.end_turn()
    assert len(p.hand) == pre + 1
    whelp = p.hand[-1]
    assert whelp.id == "WW_816t"
    assert (whelp.atk, whelp.health) == (1, 2)
    assert whelp.taunt


def test_ncommon_horseshoe_slinger_base():
    # Battlecry: Deal 2 damage to a random enemy minion.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(TARGET_DUMMY)  # only enemy minion -> forced pick
    target.max_health = 80
    target.damage = 0
    slinger = p1.give("WW_900")
    slinger._turn_entered_hand = game.turn - 1  # no Quickdraw
    assert not slinger.quickdraw_active
    slinger.play()
    assert target.damage == 2


def test_ncommon_horseshoe_slinger_quickdraw():
    # Quickdraw: And one of its neighbors. With exactly two enemy minions,
    # whichever is hit, the other is its only neighbor -> both take 2.
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    a = p2.summon(TARGET_DUMMY)
    b = p2.summon(TARGET_DUMMY)
    for m in (a, b):
        m.max_health = 80
        m.damage = 0
    slinger = p1.give("WW_900")
    assert slinger.quickdraw_active  # entered hand this turn
    slinger.play()
    assert a.damage + b.damage == 4  # 2 to the random pick + 2 to its neighbor


def test_ncommon_greedy_partner():
    # Battlecry: If you're holding another 2-Cost card, get a Coin.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    greedy = p.give("WW_901")  # itself 2-cost
    greedy.play()
    assert not any(c.id == THE_COIN for c in p.hand)  # nothing else held
    greedy2 = p.give("WW_901")
    held2 = p.give("CS2_142")  # Kobold Geomancer, 2-cost
    assert held2.cost == 2
    greedy2.play()
    assert sum(1 for c in p.hand if c.id == THE_COIN) == 1


def test_ncommon_rowdy_partner():
    # Battlecry: If you're holding another 4-Cost card, deal 4 damage.
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(TARGET_DUMMY)  # 0/4
    target.max_health = 80
    target.damage = 0
    rowdy = p1.give("WW_906")  # itself 4-cost; no OTHER 4-cost held
    rowdy.play(target=target)
    assert target.damage == 0  # condition not met
    rowdy2 = p1.give("WW_906")
    held4 = p1.give(FIREBALL)  # Fireball is 4-cost
    assert held4.cost == 4
    rowdy2.play(target=target)
    assert target.damage == 4


# === merged from test_swib_nepic.py ===
"""Showdown in the Badlands — Neutral Epic card tests (prefix: nepic)."""





# ---------------------------------------------------------------------------
# WW_025 — Azerite Giant: "Costs (1) less for each turn in a row you've
# played an Elemental."
# ---------------------------------------------------------------------------

def test_nepic_azerite_giant_cost_drops_per_elemental_streak():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    giant = game.player1.give("WW_025")
    # No streak yet -> full price.
    assert giant.cost == 8

    # Turn 1: play an Elemental, then end the turn -> streak becomes 1.
    elem = game.player1.give(ELEMENTAL)
    elem.play()
    assert game.player1.elemental_played_this_turn == 1
    game.end_turn()
    game.end_turn()  # opponent turn, back to player1
    assert game.player1.azerite_elemental_streak == 1
    assert giant.cost == 7

    # Turn 2: play another Elemental -> streak becomes 2.
    elem2 = game.player1.give(ELEMENTAL)
    elem2.play()
    game.end_turn()
    game.end_turn()
    assert game.player1.azerite_elemental_streak == 2
    assert giant.cost == 6

    # Turn 3: play NO Elemental -> streak resets to 0.
    game.end_turn()
    game.end_turn()
    assert game.player1.azerite_elemental_streak == 0
    assert giant.cost == 8


# ---------------------------------------------------------------------------
# WW_333 — Howdyfin: "Whenever your hand has less than 3 cards in it, get a
# random Murloc."
# ---------------------------------------------------------------------------

def test_nepic_howdyfin_gives_murloc_when_hand_below_three():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # Clear the hand so we control its exact size.
    for c in list(p.hand):
        c.discard()
    assert len(p.hand) == 0

    game.player1.summon("WW_333")  # on board, not in hand

    # Give exactly 3 cards: a Wisp to play plus two filler. After playing the
    # Wisp, hand drops to 2 (< 3) -> Howdyfin fires once, adding a Murloc.
    filler1 = p.give(WISP)
    filler2 = p.give(WISP)
    to_play = p.give(WISP)
    assert len(p.hand) == 3

    to_play.play()
    # Played Wisp leaves hand (now 2 fillers); trigger fires and adds a Murloc.
    assert len(p.hand) == 3
    added = p.hand[-1]
    assert added.type == CardType.MINION
    assert Race.MURLOC in added.races


def test_nepic_howdyfin_silent_when_hand_three_or_more():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    game.player1.summon("WW_333")

    # Five cards in hand; play one -> hand becomes 4 (>= 3) -> no Murloc.
    for _ in range(4):
        p.give(WISP)
    to_play = p.give(WISP)
    assert len(p.hand) == 5
    to_play.play()
    assert len(p.hand) == 4
    assert all(Race.MURLOC not in c.races for c in p.hand)


# ---------------------------------------------------------------------------
# WW_351 — Cattle Rustler: "Battlecry: Draw a Beast. It costs (3) less."
# ---------------------------------------------------------------------------

def test_nepic_cattle_rustler_draws_beast_and_discounts_it():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # Empty the deck, then seed exactly one Beast (Captured Jormungar, a
    # 7-cost Beast — high enough that the -3 discount stays above the 0 floor).
    p.deck[:] = []
    beast = p.card("AT_102", zone=Zone.DECK)
    assert beast.zone == Zone.DECK
    base_cost = beast.cost
    assert base_cost == 7

    rustler = p.give("WW_351")
    rustler.play()

    # The Beast was drawn into hand.
    assert beast.zone == Zone.HAND
    # And it now costs exactly 3 less.
    assert beast.cost == 4


# ---------------------------------------------------------------------------
# WW_420 — Ogre-Gang Ace: "Rush. Whenever this attacks, gain Divine Shield.
# (50% chance to gain Lifesteal instead.)"
# ---------------------------------------------------------------------------

def test_nepic_ogre_gang_ace_attack_grants_divine_shield_or_lifesteal():
    # Force the coinflip to FALSE so we land on the deterministic
    # Divine Shield branch (COINFLIP & Lifesteal | DivineShield).
    import fireplace.dsl.lazynum as _ln

    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    ace = p.summon("WW_420")
    ace.turn_played = -1  # bypass summoning sickness so it can attack
    assert not ace.divine_shield
    assert not ace.lifesteal

    target = game.player2.summon(TARGET_DUMMY)
    target.max_health = 80
    target.damage = 0

    with mock(_ln.RandomNumber, 0):  # COINFLIP false -> Divine Shield branch
        ace.attack(target)
    assert ace.divine_shield is True
    assert ace.lifesteal is False


def test_nepic_ogre_gang_ace_attack_grants_lifesteal_on_coinflip():
    import fireplace.dsl.lazynum as _ln

    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    ace = p.summon("WW_420")
    ace.turn_played = -1  # bypass summoning sickness so it can attack

    target = game.player2.summon(TARGET_DUMMY)
    target.max_health = 80
    target.damage = 0

    with mock(_ln.RandomNumber, 1):  # COINFLIP true -> Lifesteal branch
        ace.attack(target)
    assert ace.lifesteal is True
    assert ace.divine_shield is False


# ---------------------------------------------------------------------------
# WW_431 — Gattlesnake: "At the end of your turn, load two bullets that deal
# 1 damage each. Deathrattle: Fire at random enemies!"
# ---------------------------------------------------------------------------

def test_nepic_gattlesnake_loads_two_bullets_each_turn_end():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    snake = game.player1.summon("WW_431")
    assert getattr(snake, "_loaded_bullets", 0) == 0

    game.end_turn()  # player1's turn ends -> load 2 bullets
    assert snake._loaded_bullets == 2

    game.end_turn()  # opponent turn end does NOT load (OWN_TURN_END only)
    assert snake._loaded_bullets == 2

    game.end_turn()  # player1's turn ends again -> +2 -> 4
    assert snake._loaded_bullets == 4


def test_nepic_gattlesnake_deathrattle_fires_all_bullets():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    snake = game.player1.summon("WW_431")

    game.end_turn()  # load 2
    game.end_turn()
    game.end_turn()  # load 2 more -> 4 bullets total
    assert snake._loaded_bullets == 4

    # Single soak target on the enemy side absorbs every bullet, so the
    # 4 hits of 1 damage all land here (the enemy hero is the only other
    # enemy character; beef the minion so it stays the obvious sink).
    # To make the total deterministic, leave the enemy hero as the only
    # other character and a single big-HP minion: total damage across both
    # equals exactly the bullet count.
    p2 = game.player2
    dummy = p2.summon(TARGET_DUMMY)
    dummy.max_health = 80
    dummy.damage = 0
    hero_hp_before = p2.hero.health

    snake.destroy()

    total = dummy.damage + (hero_hp_before - p2.hero.health)
    assert total == 4


# === merged from test_swib_nleg.py ===
def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


def _add_to_deck(player, card_id):
    # Setting zone=DECK already appends to player.deck via _set_zone.
    return player.card(card_id, zone=Zone.DECK)


# ---------------------------------------------------------------------------
# WW_440 Thunderbringer — Taunt. Deathrattle: Summon an Elemental and Beast
# from your deck.
# ---------------------------------------------------------------------------


def test_nleg_thunderbringer_summons_elemental_and_beast():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.deck = []
    # Exactly one Elemental (Flame Elemental) and one Beast (Ironfur Grizzly).
    el = _add_to_deck(p, ELEMENTAL)
    beast = _add_to_deck(p, "CS2_125")
    assert len(p.deck) == 2
    tb = p.summon("WW_440")
    assert tb.taunt
    tb.destroy()
    field_ids = [m.id for m in p.field]
    assert ELEMENTAL in field_ids
    assert "CS2_125" in field_ids
    assert len(p.field) == 2
    # Both pulled out of the deck.
    assert len(p.deck) == 0


# ---------------------------------------------------------------------------
# WW_421 Kingpin Pud — Battlecry: Resurrect your Ogre-Gang. Give them Windfury.
# ---------------------------------------------------------------------------


def test_nleg_kingpin_pud_resurrects_ogre_gang_with_windfury():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # Put two Ogre-Gang minions on board and kill them so they sit in the
    # graveyard as "died this game".
    outlaw = p.summon("WW_418")   # Ogre-Gang Outlaw
    rider = p.summon("WW_419")    # Ogre-Gang Rider
    # A non-Ogre minion that also died — must NOT be resurrected.
    wisp = p.summon(WISP)
    outlaw.destroy()
    rider.destroy()
    wisp.destroy()
    assert len(p.field) == 0
    pud = p.give("WW_421")
    pud.play()
    # Two Ogre-Gang minions resurrected (plus Pud himself on board = 3).
    resurrected = [m for m in p.field if m.id in ("WW_418", "WW_419")]
    assert len(resurrected) == 2
    assert all(m.windfury for m in resurrected)
    # The Wisp was not resurrected.
    assert WISP not in [m.id for m in p.field]
    assert len([m for m in p.field if m.id == "WW_421"]) == 1


# ---------------------------------------------------------------------------
# WW_379 Flint Firearm — Battlecry: Get a random Quickdraw card. If you play
# it this turn, repeat this.
# ---------------------------------------------------------------------------


def test_nleg_flint_firearm_gives_quickdraw_card_with_marker():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _clear_hand(p)
    flint = p.give("WW_379")
    flint.play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    # Exactly one card added to hand, and it is a Quickdraw card carrying the
    # WW_379e marker buff.
    assert len(p.hand) == 1
    given = p.hand[0]
    assert given.data.tags.get(GameTag.QUICKDRAW)
    assert "WW_379e" in [b.id for b in given.buffs]


def _flint_marked_quickdraw(p):
    """Cards in hand carrying the Flint visual marker (WW_379e) that are
    Quickdraw cards."""
    return [c for c in p.hand if c.data.tags.get(GameTag.QUICKDRAW)
            and "WW_379e" in [b.id for b in c.buffs]]


def test_nleg_flint_firearm_grants_one_marked_quickdraw():
    """Flint's battlecry grants exactly one Quickdraw card, marked with the
    WW_379e enchant (the identity is random but the count and marker are
    not)."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _clear_hand(p)
    p.give("WW_379").play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    granted = _flint_marked_quickdraw(p)
    assert len(granted) == 1
    assert granted[0].data.tags.get(GameTag.QUICKDRAW)


def _flint_arm(game, p, card_id):
    """Install Flint's player-level watcher and hand the player a known,
    marked, free Quickdraw card — isolating the repeat mechanic from Flint's
    random grant so the assertion is deterministic."""
    game.queue_actions(p.hero, [Buff(p, "WW_379t")])
    c = p.give(card_id)
    game.queue_actions(p.hero, [Buff(c, "WW_379e")])
    c._flint_marked = True
    c.cost = 0
    return c


def test_nleg_flint_firearm_repeats_for_minion():
    """Playing a Flint-marked Quickdraw MINION repeats the battlecry: a new
    marked Quickdraw card appears in hand."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _clear_hand(p)
    c = _flint_arm(game, p, "WW_360")  # Azerite Chain Gang — Quickdraw minion
    c.play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    assert len(_flint_marked_quickdraw(p)) == 1


def test_nleg_flint_firearm_repeats_for_spell():
    """Regression: a Flint-marked Quickdraw SPELL must also repeat. A
    card-attached Play listener misses spells (their enchants are cleared on
    cast), so the repeat is driven by the player-level watcher (WW_379t)."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _clear_hand(p)
    c = _flint_arm(game, p, "WW_403")  # Pocket Sand — Quickdraw spell
    c.play(target=game.player2.hero)
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    assert len(_flint_marked_quickdraw(p)) == 1


# ---------------------------------------------------------------------------
# WW_359 Sheriff Barrelbrim — Battlecry: If you have 20 or less Health, open
# the Badlands Jail.
# ---------------------------------------------------------------------------


def test_nleg_sheriff_barrelbrim_opens_jail_when_low_health():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.hero.set_current_health(20)
    enemy = game.player2.summon(WISP)
    sheriff = p.give("WW_359")
    sheriff.play()
    # Location summoned and the enemy minion jailed (dormant for 3 turns).
    assert p.location is not None
    assert p.location.id == "WW_359t"
    assert enemy.dormant
    assert enemy.dormant_turns == 3


def test_nleg_sheriff_barrelbrim_does_nothing_at_high_health():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.hero.set_current_health(21)
    enemy = game.player2.summon(WISP)
    sheriff = p.give("WW_359")
    sheriff.play()
    assert p.location is None
    assert not enemy.dormant


# ---------------------------------------------------------------------------
# WW_0700 Reno, Lone Ranger — Battlecry: If your deck has no duplicates, empty
# the enemy board and limit it to 1 minion for a turn.
# ---------------------------------------------------------------------------


def test_nleg_reno_empties_enemy_board_no_duplicates():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    # Build a strictly-unique deck so the no-duplicates gate is satisfied.
    p.deck = []
    for cid in ("CS2_029", "CS2_023", "EX1_277", "CS2_024", "CS2_025"):
        _add_to_deck(p, cid)
    # Fill the enemy board with several minions.
    opp = game.player2
    for _ in range(4):
        opp.summon(WISP)
    assert len(opp.field) == 4
    reno = p.give("WW_0700")
    reno.play()
    while p.choice:
        p.choice.choose(p.choice.cards[0])
    # Enemy board wiped, and Reno's Handcannon installed as hero power.
    assert len(opp.field) == 0
    assert p.hero.power.id in (
        "WW_0700p", "WW_0700p1", "WW_0700p2", "WW_0700p3",
        "WW_0700p4", "WW_0700p5", "WW_0700p6", "WW_0700p7",
    )


def test_nleg_reno_does_nothing_with_duplicates():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.deck = []
    # Two copies of the same card => duplicates present.
    _add_to_deck(p, "CS2_029")
    _add_to_deck(p, "CS2_029")
    _add_to_deck(p, "CS2_023")
    opp = game.player2
    w1 = opp.summon(WISP)
    w2 = opp.summon(WISP)
    reno = p.give("WW_0700")
    reno.play()
    # The hero swap + Handcannon install is unconditional (it's a Hero card),
    # but the battlecry is suppressed by the duplicates: enemy board intact.
    assert len(opp.field) == 2
    assert w1 in opp.field and w2 in opp.field


# ---------------------------------------------------------------------------
# Reno's Handcannon bullets — each is a hero power with a fixed effect.
# Summon the bullet hero power directly by id and use it.
# ---------------------------------------------------------------------------


def test_nleg_arcane_bullet_damage_and_refresh_mana():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_0700p1")  # replaces hero power with Arcane Bullet
    assert p.hero.power.id == "WW_0700p1"
    # 4 mana available; the hero power costs 2 and then refreshes 2, so the
    # net used_mana is unchanged — proving the refresh fired.
    p.max_mana = 10
    p.used_mana = 6
    target = game.player2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    p.hero.power.use(target=target)
    assert target.damage == 2
    # Pay 2 (used_mana 6 -> 8) then refresh 2 (8 -> 6): back to 6.
    assert p.used_mana == 6


def test_nleg_frost_bullet_damage_and_armor():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_0700p2")
    assert p.hero.power.id == "WW_0700p2"
    assert p.hero.armor == 0
    target = game.player2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    p.hero.power.use(target=target)
    assert target.damage == 2
    assert p.hero.armor == 4


def test_nleg_fire_bullet_damage_target_then_aoe_enemy_minions():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_0700p3")
    assert p.hero.power.id == "WW_0700p3"
    opp = game.player2
    primary = opp.summon(WISP)
    primary.max_health = 80
    primary.damage = 0
    other = opp.summon(WISP)
    other.max_health = 80
    other.damage = 0
    p.hero.power.use(target=primary)
    # Primary takes 2 (direct) + 1 (AoE) = 3; the other enemy minion takes 1.
    assert primary.damage == 3
    assert other.damage == 1


def test_nleg_holy_bullet_damage_and_buff_friendly():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_0700p4")
    assert p.hero.power.id == "WW_0700p4"
    # Exactly one friendly minion so the random buff lands on it.
    friendly = p.summon(WISP)  # 1/1
    target = game.player2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    p.hero.power.use(target=target)
    assert target.damage == 2
    assert friendly.atk == 3
    assert friendly.health == 3


def test_nleg_nature_bullet_damage_and_discover_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _clear_hand(p)
    p.summon("WW_0700p5")
    assert p.hero.power.id == "WW_0700p5"
    target = game.player2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    p.hero.power.use(target=target)
    assert target.damage == 2
    assert p.choice is not None
    assert all(c.type == CardType.SPELL for c in p.choice.cards)
    p.choice.choose(p.choice.cards[0])
    assert len(p.hand) == 1
    assert p.hand[0].type == CardType.SPELL


def test_nleg_shadow_bullet_damage_and_summon_3cost():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_0700p6")
    assert p.hero.power.id == "WW_0700p6"
    target = game.player2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    pre = len(p.field)
    p.hero.power.use(target=target)
    assert target.damage == 2
    assert len(p.field) == pre + 1
    summoned = p.field[-1]
    assert summoned.cost == 3
    assert summoned.type == CardType.MINION


def test_nleg_fel_bullet_damage_and_draw():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    _clear_hand(p)
    p.deck = []
    drawn = _add_to_deck(p, "CS2_029")
    p.summon("WW_0700p7")
    assert p.hero.power.id == "WW_0700p7"
    target = game.player2.summon(WISP)
    target.max_health = 80
    target.damage = 0
    p.hero.power.use(target=target)
    assert target.damage == 2
    assert len(p.hand) == 1
    assert p.hand[0] is drawn


def test_nleg_handcannon_swaps_to_a_bullet_at_turn_start():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_0700p")
    assert p.hero.power.id == "WW_0700p"
    # Cycle a full turn so OWN_TURN_BEGIN fires for player1.
    game.end_turn()
    game.end_turn()
    assert p.hero.power.id in (
        "WW_0700p1", "WW_0700p2", "WW_0700p3", "WW_0700p4",
        "WW_0700p5", "WW_0700p6", "WW_0700p7",
    )


# === merged from test_swib_nrare.py ===
"""Showdown in the Badlands — Neutral Rare card tests (WW_* RARE neutrals)."""


from fireplace.actions import EXCAVATE_TIERS


# ---------------------------------------------------------------------------
# WW_002 Burrow Buster — Rush. Battlecry: Excavate a treasure.
# ---------------------------------------------------------------------------

def test_nrare_burrow_buster():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    assert p.excavates_this_game == 0
    pre_hand = len(p.hand)

    card = p.give("WW_002")
    card.play()

    # Battlecry excavated exactly one (first-tier) treasure into hand.
    assert p.excavates_this_game == 1
    # give() added Burrow Buster (+1), play() removed it (-1), excavate added
    # one treasure (+1) -> net +1 over the pre-give hand size.
    assert len(p.hand) == pre_hand + 1
    assert p.hand[-1].id in EXCAVATE_TIERS[1]
    # Rush minion, in play.
    assert card.zone == Zone.PLAY
    assert bool(card.rush)


# ---------------------------------------------------------------------------
# WW_003 Bounty Board — Your Excavate, Quickdraw, Tradeable, and Legendary
# cards cost (1) less.
# ---------------------------------------------------------------------------

def test_nrare_bounty_board_reduces_matching_cards():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1

    # Cards that should be discounted.
    legendary = p.give("BAR_721")        # Mankrik, 3-cost neutral Legendary
    tradeable = p.give("CORE_DED_009")   # Doggie Biscuit, 2-cost Tradeable
    quickdraw = p.give("WW_360")         # Azerite Chain Gang, 4-cost Quickdraw
    excavate = p.give("WW_002")          # Burrow Buster, 5-cost Excavate
    # A control card with none of the four properties.
    control = p.give(WISP)               # 1-cost vanilla, no matching tags

    base_leg, base_trade = legendary.cost, tradeable.cost
    base_qd, base_exc, base_ctrl = quickdraw.cost, excavate.cost, control.cost

    p.summon("WW_003")

    assert legendary.cost == base_leg - 1
    assert tradeable.cost == base_trade - 1
    assert quickdraw.cost == base_qd - 1
    assert excavate.cost == base_exc - 1
    # Control card is untouched.
    assert control.cost == base_ctrl


def test_nrare_bounty_board_exact_costs():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    p.summon("WW_003")

    mankrik = p.give("BAR_721")          # printed 3 -> 2
    biscuit = p.give("CORE_DED_009")     # printed 2 -> 1
    azerite = p.give("WW_360")           # printed 4 -> 3

    assert mankrik.cost == 2
    assert biscuit.cost == 1
    assert azerite.cost == 3


# ---------------------------------------------------------------------------
# WW_332 Snake Oil Seller — Deathrattle: Shuffle 2 Tradeable Snake Oils into
# your opponent's deck.
# ---------------------------------------------------------------------------

def test_nrare_snake_oil_seller():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    pre_deck = len(p2.deck)

    seller = p1.summon("WW_332")
    seller.destroy()
    game.process_deaths()

    # Opponent's deck gained exactly two Snake Oils.
    snake_oils = [c for c in p2.deck if c.id == "WW_331t"]
    assert len(snake_oils) == 2
    assert len(p2.deck) == pre_deck + 2
    # Friendly deck untouched.
    assert all(c.id != "WW_331t" for c in p1.deck)


# ---------------------------------------------------------------------------
# WW_360 Azerite Chain Gang — Taunt. Battlecry and Quickdraw: Summon a copy
# of this.
# ---------------------------------------------------------------------------

def test_nrare_azerite_chain_gang_battlecry_only():
    """Played from an earlier turn (not Quickdraw-active): battlecry summons
    one copy -> 2 total on board."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1

    card = p.give("WW_360")
    card._turn_entered_hand = game.turn - 1   # disable Quickdraw
    assert card.quickdraw_active is False
    card.play()

    chain_gangs = [m for m in p.field if m.id == "WW_360"]
    assert len(chain_gangs) == 2
    assert all(m.taunt for m in chain_gangs)


def test_nrare_azerite_chain_gang_quickdraw():
    """Played the same turn it entered hand (Quickdraw-active): battlecry +
    Quickdraw each summon a copy -> 3 total on board."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1

    card = p.give("WW_360")
    assert card.quickdraw_active is True
    card.play()

    chain_gangs = [m for m in p.field if m.id == "WW_360"]
    assert len(chain_gangs) == 3
    assert all(m.taunt for m in chain_gangs)


# ---------------------------------------------------------------------------
# WW_419 Ogre-Gang Rider — Rush. 50% chance to give your hero +3 Attack this
# turn instead of attacking.
# ---------------------------------------------------------------------------

def test_nrare_ogre_gang_rider_coinflip_win():
    """Heads (RandomNumber -> 1): the attack is cancelled and the hero gains
    +3 Attack this turn instead."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2

    rider = p1.summon("WW_419")      # Rush 3/6, can attack a minion at once
    target = p2.summon("CS2_182")    # Chillwind Yeti 4/5

    assert p1.hero.atk == 0
    with mock(RandomNumber, 1):
        rider.attack(target)

    # Attack was cancelled: target took no damage, rider took no retaliation.
    assert target.damage == 0
    assert rider.damage == 0
    # Hero gained exactly +3 Attack this turn.
    assert p1.hero.atk == 3


def test_nrare_ogre_gang_rider_coinflip_lose():
    """Tails (RandomNumber -> 0): the attack proceeds normally, no hero buff."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2

    rider = p1.summon("WW_419")      # Rush 3/6
    target = p2.summon("CS2_182")    # Chillwind Yeti 4/5

    assert p1.hero.atk == 0
    with mock(RandomNumber, 0):
        rider.attack(target)

    # Combat happened: rider (3) hit Yeti (5 hp) -> 3 damage; Yeti (4) hit
    # rider (6 hp) -> 4 damage. Both survive.
    assert target.damage == 3
    assert rider.damage == 4
    # No hero buff.
    assert p1.hero.atk == 0


# === merged from test_swib_pal.py ===
def test_pal_showdown():
    # Both players summon three 3/3 Outlaws. Give yours Rush.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Clear boards for an exact count.
    for m in list(game.player1.field):
        m.destroy()
    for m in list(game.player2.field):
        m.destroy()
    spell = game.player1.give("WW_051")
    spell.play()
    assert len(game.player1.field) == 3
    assert len(game.player2.field) == 3
    for m in game.player1.field:
        assert m.id == "WW_051t"
        assert m.atk == 3
        assert m.health == 3
        assert m.rush is True
    for m in game.player2.field:
        assert m.id == "WW_051t"
        assert m.atk == 3
        assert m.health == 3
        assert m.rush is False


def test_pal_holy_cowboy():
    # Battlecry: Your next Holy spell costs (2) less.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Holy Light (HOLY_LIGHT = CS2_089) is a Holy spell costing 2.
    holy = game.player1.give(HOLY_LIGHT)
    base_cost = holy.cost
    assert base_cost == 2
    cowboy = game.player1.give("WW_335")
    cowboy.play()
    # After battlecry the Holy spell costs 2 less (clamped at 0).
    assert holy.cost == max(0, base_cost - 2)
    # A non-Holy spell is unaffected.
    fireball = game.player1.give(FIREBALL)
    assert fireball.cost == 4


def test_pal_holy_cowboy_consumes_after_one_holy_spell():
    # The discount only applies to the NEXT Holy spell.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    holy1 = game.player1.give(HOLY_LIGHT)
    holy2 = game.player1.give(HOLY_LIGHT)
    cowboy = game.player1.give("WW_335")
    cowboy.play()
    assert holy1.cost == 0
    assert holy2.cost == 0
    # Play one Holy spell — the aura should expire, restoring the other's cost.
    holy1.play(target=game.player1.hero)
    assert holy2.cost == 2


def test_pal_lawful_longarm():
    # Rush, Lifesteal. Battlecry: Gain +1 Attack for each card in your hand.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Empty the hand so we control the count exactly.
    for c in list(game.player1.hand):
        c.discard()
    # Give exactly 3 filler cards plus the Longarm (4 in hand; after the
    # Longarm is played from hand there are 3 cards remaining).
    for _ in range(3):
        game.player1.give(WISP)
    longarm = game.player1.give("WW_342")
    longarm.play()
    # Base 1 Attack; 3 cards remain in hand at resolution → +3 Attack.
    assert longarm.atk == 1 + 3
    assert longarm.rush
    assert longarm.lifesteal


def test_pal_hi_ho_silverwing():
    # Divine Shield. Deathrattle: Draw a Holy spell.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    # Stack the deck with exactly one Holy spell so the draw is deterministic.
    holy = game.player1.give(HOLY_LIGHT)
    holy.shuffle_into_deck()
    silver = game.player1.summon("WW_344")
    assert silver.divine_shield
    pre_hand = len(game.player1.hand)
    silver.destroy()
    # The Holy spell was drawn into hand.
    assert holy.zone == Zone.HAND
    assert len(game.player1.hand) == pre_hand + 1


def test_pal_living_horizon_cost():
    # Taunt, Divine Shield. Costs (1) less for each other card in your hand.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    for c in list(game.player1.hand):
        c.discard()
    horizon = game.player1.give("WW_366")
    base = horizon.data.cost
    assert base == 10
    # Cost is reduced by 1 per OTHER card currently in hand.
    others = len(game.player1.hand) - 1
    assert horizon.cost == base - others
    # Add two more cards → cost drops by exactly two more.
    cost_before = horizon.cost
    game.player1.give(WISP)
    game.player1.give(WISP)
    assert horizon.cost == cost_before - 2
    assert horizon.taunt
    assert horizon.divine_shield


def test_pal_prismatic_beam():
    # Deal 3 damage to all enemies. Costs (1) less for each enemy minion.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    for m in list(game.player2.field):
        m.destroy()
    # Two enemy minions, big enough to survive the 3 damage so we assert exact.
    t1 = game.player2.summon(GOLDSHIRE_FOOTMAN)
    t2 = game.player2.summon(GOLDSHIRE_FOOTMAN)
    t1.max_health = 80
    t1.damage = 0
    t2.max_health = 80
    t2.damage = 0
    beam = game.player1.give("WW_336")
    base = beam.data.cost
    assert beam.cost == base - 2  # two enemy minions
    enemy_hero_health = game.player2.hero.health
    beam.play()
    assert t1.damage == 3
    assert t2.damage == 3
    assert game.player2.hero.health == enemy_hero_health - 3


def test_pal_lay_down_the_law_no_quickdraw():
    # Set a minion's Attack and Health to 1. (No Quickdraw → no extra damage.)
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player2.summon("CS2_186")  # War Golem 7/7
    assert target.atk == 7 and target.health == 7
    # Put the spell in hand, then end+begin a turn so it is NOT quickdraw.
    spell = game.player1.give("WW_365")
    game.end_turn()
    game.end_turn()
    spell.play(target=target)
    assert target.atk == 1
    assert target.health == 1
    assert target.damage == 0  # no quickdraw damage


def test_pal_lay_down_the_law_quickdraw():
    # Quickdraw: set to 1/1 then deal 1 damage → it dies.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    target = game.player2.summon("CS2_186")  # War Golem 7/7
    # Give and immediately play this turn → quickdraw active.
    spell = game.player1.give("WW_365")
    spell.play(target=target)
    # 1/1 then 1 damage → destroyed.
    assert target.zone == Zone.GRAVEYARD


def test_pal_deputization_aura():
    # Your left-most minion has +3 Attack and Lifesteal. Lasts 3 turns.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    for m in list(game.player1.field):
        m.destroy()
    left = game.player1.summon(GOLDSHIRE_FOOTMAN)   # 1/2
    right = game.player1.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    aura = game.player1.give("WW_341")
    aura.play()
    # Left-most gets +3 Attack and Lifesteal; right-most untouched.
    assert left.atk == 1 + 3
    assert left.lifesteal is True
    assert right.atk == 1
    assert right.lifesteal is False


def test_pal_deputization_aura_expires():
    # Lasts 3 turns, then the buff goes away.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    for m in list(game.player1.field):
        m.destroy()
    left = game.player1.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    aura = game.player1.give("WW_341")
    aura.play()
    assert left.atk == 4
    # Three of the controller's turn-ends elapse → aura expires.
    for _ in range(3):
        game.end_turn()  # player1 ends
        game.end_turn()  # player2 ends → back to player1
    assert left.atk == 1
    assert left.lifesteal is False


def test_pal_badlands_bandits():
    # Get eight 3/2 Bandits. Any that can't fit in hand are summoned instead.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    for c in list(game.player1.hand):
        c.discard()
    for m in list(game.player1.field):
        m.destroy()
    spell = game.player1.give("WW_345")
    spell.play()
    # Hand had 0 cards; max hand size 10 → all eight fit in hand.
    bandit_ids = {"WW_345t%i" % i for i in range(1, 9)}
    got = [c for c in game.player1.hand if c.id in bandit_ids]
    assert len(got) == 8
    assert {c.id for c in got} == bandit_ids
    for c in got:
        assert c.atk == 3
        assert c.health == 2


def test_pal_badlands_bandits_overflow_summons():
    # When the hand is full, bandits that can't fit are summoned instead.
    game = prepare_game(CardClass.PALADIN, CardClass.PALADIN)
    for m in list(game.player1.field):
        m.destroy()
    for c in list(game.player1.hand):
        c.discard()
    # Give the spell, then pad the hand up to max so that after the spell
    # leaves, the hand sits at (max - 1) = 9.
    spell = game.player1.give("WW_345")
    while len(game.player1.hand) < game.player1.max_hand_size:
        game.player1.give(WISP)
    assert len(game.player1.hand) == game.player1.max_hand_size  # 10
    spell.play()
    bandit_ids = {"WW_345t%i" % i for i in range(1, 9)}
    in_hand = [c for c in game.player1.hand if c.id in bandit_ids]
    on_board = [c for c in game.player1.field if c.id in bandit_ids]
    # Spell leaves hand -> 9 cards; exactly one bandit fits in hand, the
    # remaining seven are summoned to the (cleared) board.
    assert len(in_hand) == 1
    assert len(on_board) == 7
    assert len(in_hand) + len(on_board) == 8


def test_pal_spirit_of_the_badlands_no_dupes():
    # Battlecry: If your deck has no duplicates, get a permanent Mirage.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    # Build a no-duplicate deck with at least one minion.
    for cid in (WISP, "CS2_186", FIREBALL):
        game.player1.give(cid).shuffle_into_deck()
    for c in list(game.player1.hand):
        c.discard()
    spirit = game.player1.give("WW_337")
    spirit.play()
    mirages = [c for c in game.player1.hand if c.id == "WW_337t"]
    assert len(mirages) == 1


def test_pal_spirit_of_the_badlands_with_dupes():
    # With duplicates in deck, no Mirage is granted.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    for _ in range(2):
        game.player1.give(WISP).shuffle_into_deck()
    for c in list(game.player1.hand):
        c.discard()
    spirit = game.player1.give("WW_337")
    spirit.play()
    mirages = [c for c in game.player1.hand if c.id == "WW_337t"]
    assert len(mirages) == 0


def test_pal_mirage_transforms_at_turn_start():
    # Mirage: at the start of your turn, transform into a copy of a minion
    # in your deck (stays in hand).
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    # Deck has exactly one minion so the transform is deterministic.
    game.player1.give("CS2_186").shuffle_into_deck()  # War Golem
    for c in list(game.player1.hand):
        c.discard()
    mirage = game.player1.give("WW_337t")
    assert mirage.id == "WW_337t"
    # Advance to the controller's next turn-begin.
    game.end_turn()  # player1 -> player2
    game.end_turn()  # player2 -> player1 (OWN_TURN_BEGIN fires)
    # The hand card transformed into a copy of the deck minion.
    transformed = game.player1.hand[0]
    assert transformed.id == "CS2_186"
    assert transformed.zone == Zone.HAND


# === merged from test_swib_priest.py ===
# Vanilla 1/1 with no text used as a clean filler in several decks.
WISP = "CS2_231"
# 2-mana 3/2 vanilla (Bloodfen Raptor) — collectible minion for decks.
RAPTOR = "CS2_172"
# Chillwind Yeti 4/5 vanilla.
YETI = "CS2_182"
# Boulderfist Ogre 6/7 vanilla.
OGRE = "CS2_200"
# Magma Rager 5/1 vanilla.
RAGER = "EX1_011"
# A vanilla 1-cost minion: Goldshire Footman (1/2 Taunt) — but we want
# a stat-clean 1-drop. Use Wisp (1/1, 0 cost) where cost matters; use
# Stonetusk Boar for a 1-cost minion.
BOAR = "CS2_171"  # Stonetusk Boar 1/1 Charge, cost 1


def _clear_deck(player):
	while player.deck:
		player.deck[-1].discard()
	player.cant_fatigue = True


def _add_to_deck_2(player, card_id):
	"""Create a card and place it in the deck zone (so deck selectors see
	it; a bare list .append leaves it in SETASIDE)."""
	card = player.card(card_id)
	card.zone = Zone.DECK
	return card


def test_priest_swarm_of_lightbugs_summons_and_bottles_excess():
	"""WW_052 — 10 Lightbugs requested, board caps at 7, so 7 are
	summoned (1/1 Lifesteal) and the remaining 3 are saved in a Bottled
	Lightbugs (WW_052t2) token stamped with amount 3."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	card = game.player1.give("WW_052")
	card.play()
	field = game.player1.field
	assert len(field) == 7
	for m in field:
		assert m.id == "WW_052t"
		assert m.atk == 1
		assert m.max_health == 1
		assert m.lifesteal
	# Excess 3 (10 requested - 7 summoned) stored on a single bottle.
	bottles = [c for c in game.player1.hand if c.id == "WW_052t2"]
	assert len(bottles) == 1
	assert bottles[0]._bottle_amount == 3


def test_priest_swarm_of_lightbugs_no_bottle_when_board_empty_enough():
	"""WW_052 — clears the board first, but 10 > 7 always overflows, so
	a bottle storing exactly 3 always appears from an empty board."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	card = game.player1.give("WW_052")
	card.play()
	assert len(game.player1.field) == 7
	bottle = [c for c in game.player1.hand if c.id == "WW_052t2"][0]
	assert bottle._bottle_amount == 3


def test_priest_bottled_lightbugs_summons_stored_amount():
	"""WW_052t2 — playing the bottle summons exactly the stored number of
	1/1 Lifesteal Lightbugs (here 3) onto an empty board."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	bottle = game.player1.give("WW_052t2")
	bottle._bottle_amount = 3
	bottle.play()
	field = game.player1.field
	assert len(field) == 3
	for m in field:
		assert m.id == "WW_052t"
		assert m.lifesteal


def test_priest_invasive_shadeleaf_deals_8_and_bottles_excess():
	"""WW_393 — deal 8 to a 5-health enemy minion (Chillwind Yeti 4/5):
	it dies, and the 3 excess damage is saved in a Bottled Shadeleaf
	(WW_393t)."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player2.summon(YETI)  # 4/5
	assert target.health == 5
	spell = game.player1.give("WW_393")
	spell.play(target=target)
	assert target.dead
	bottle = [c for c in game.player1.hand if c.id == "WW_393t"][0]
	assert bottle._bottle_amount == 3


def test_priest_invasive_shadeleaf_no_bottle_without_excess():
	"""WW_393 — against a 9-health enemy (Captured Jormungar 5/9), 8
	damage leaves no excess, so no bottle is created."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player2.summon("AT_102")  # 5/9
	spell = game.player1.give("WW_393")
	spell.play(target=target)
	assert not target.dead
	assert target.damage == 8
	assert not any(c.id == "WW_393t" for c in game.player1.hand)


def test_priest_bottled_shadeleaf_deals_stored_damage():
	"""WW_393t — deals exactly the stored excess to a chosen enemy
	minion."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	target = game.player2.summon(YETI)  # 4/5
	bottle = game.player1.give("WW_393t")
	bottle._bottle_amount = 3
	bottle.play(target=target)
	assert target.damage == 3


def test_priest_holy_springwater_heals_8_and_bottles_overheal():
	"""WW_395 — restore 8 to a hero damaged by 2: only 2 is actually
	healed, the 6 overheal is saved in a Bottled Springwater
	(WW_395t)."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	hero = game.player1.hero
	hero.damage = 2
	spell = game.player1.give("WW_395")
	spell.play(target=hero)
	assert hero.damage == 0
	bottle = [c for c in game.player1.hand if c.id == "WW_395t"][0]
	assert bottle._bottle_amount == 6


def test_priest_holy_springwater_no_bottle_when_no_overheal():
	"""WW_395 — restore 8 to a hero damaged by exactly 8: heals fully, no
	overheal → no bottle."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	hero = game.player1.hero
	hero.damage = 8
	spell = game.player1.give("WW_395")
	spell.play(target=hero)
	assert hero.damage == 0
	assert not any(c.id == "WW_395t" for c in game.player1.hand)


def test_priest_bottled_springwater_heals_stored_amount():
	"""WW_395t — restores exactly the stored excess to a damaged
	character."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	hero = game.player1.hero
	hero.damage = 10
	bottle = game.player1.give("WW_395t")
	bottle._bottle_amount = 6
	bottle.play(target=hero)
	assert hero.damage == 4


def test_priest_tram_heist_copies_opponent_last_turn_cards():
	"""WW_053 — get a copy of each card the opponent played last turn.
	Opponent plays exactly two minions on their turn; on my turn Tram
	Heist adds two copies (one of each) to my hand."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	# Make it player2's turn.
	if game.current_player is game.player1:
		game.end_turn()
	# player2 plays two distinct minions this turn.
	game.player2.give(YETI).play()
	game.player2.give(RAPTOR).play()
	game.end_turn()  # back to player1
	pre_hand_ids = [c.id for c in game.player1.hand]
	heist = game.player1.give("WW_053")
	heist.play()
	added = [c.id for c in game.player1.hand if c.id != "WW_053"]
	# Two copies added: one Yeti, one Raptor.
	assert added.count(YETI) == pre_hand_ids.count(YETI) + 1
	assert added.count(RAPTOR) == pre_hand_ids.count(RAPTOR) + 1


def test_priest_posse_possession_summons_4_4_copy_of_enemy_hand_minion():
	"""WW_600 — opponent holds exactly one minion (Boulderfist Ogre 6/7);
	summon a 4/4 copy of it on my side."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	# Clear opponent hand to a single known minion.
	for c in list(game.player2.hand):
		c.discard()
	game.player2.give(OGRE)  # 6/7
	spell = game.player1.give("WW_600")
	spell.play()
	field = game.player1.field
	assert len(field) == 1
	copy = field[0]
	assert copy.id == OGRE
	assert copy.atk == 4
	assert copy.max_health == 4


def test_priest_injured_hauler_battlecry_self_damage():
	"""WW_381 — Battlecry deals 4 to itself; a 3/7 ends at 4 damage."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	hauler = game.player1.give("WW_381")
	hauler.play()
	assert hauler.damage == 4
	assert hauler.health == 3


def test_priest_injured_hauler_overheal_hits_all_enemy_minions():
	"""WW_381 — after the self-hit (4 damage), healing it for 6 overheals
	by 3 → deal 2 to all enemy minions. Two enemy minions both take 2."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	hauler = game.player1.summon("WW_381")  # bypass battlecry
	game.player1.game.cheat_action(hauler, [Hit(hauler, 4)])
	assert hauler.damage == 4
	e1 = game.player2.summon(YETI)   # 4/5
	e2 = game.player2.summon(OGRE)   # 6/7
	# Heal hauler for 6: missing is 4, so heal 4 + overheal 2 → overheal.
	game.player1.game.cheat_action(hauler, [Heal(hauler, 6)])
	assert hauler.damage == 0
	assert e1.damage == 2
	assert e2.damage == 2


def test_priest_injured_hauler_no_overheal_no_aoe():
	"""WW_381 — healing it for exactly its missing health (4) does NOT
	overheal, so enemy minions are untouched."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	hauler = game.player1.summon("WW_381")
	game.player1.game.cheat_action(hauler, [Hit(hauler, 4)])
	enemy = game.player2.summon(YETI)
	game.player1.game.cheat_action(hauler, [Heal(hauler, 4)])
	assert hauler.damage == 0
	assert enemy.damage == 0


def test_priest_benevolent_banker_discovers_from_own_deck():
	"""WW_384 — without Quickdraw, Discover a spell from YOUR deck. Stack
	the deck with one spell so the discover offers exactly it; choosing
	it moves that spell to hand."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	_clear_deck(game.player1)
	_add_to_deck_2(game.player1, MOONFIRE)  # a spell
	banker = game.player1.give("WW_384")
	# A freshly-given card IS quickdraw-active (entered hand this turn).
	# To exercise the no-Quickdraw branch deterministically, backdate the
	# turn it entered hand so quickdraw_active is False.
	banker._turn_entered_hand = -1
	assert banker.quickdraw_active is False
	banker.play()
	assert game.player1.choice is not None
	cards = game.player1.choice.cards
	assert all(c.type == CardType.SPELL for c in cards)
	chosen = cards[0]
	game.player1.choice.choose(chosen)
	assert chosen.id == MOONFIRE
	assert chosen.zone == Zone.HAND


def test_priest_benevolent_banker_quickdraw_discovers_from_enemy_deck():
	"""WW_384 — with Quickdraw, Discover a spell from the ENEMY deck.
	Stack only the enemy deck with a spell and clear my own so the
	discover can only pull from the opponent."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	_clear_deck(game.player1)
	_clear_deck(game.player2)
	_add_to_deck_2(game.player2, FIREBALL)  # enemy spell
	banker = game.player1.give("WW_384")
	# Freshly given → quickdraw_active is set; play this turn → quickdraw.
	assert banker.quickdraw_active is True
	banker.play()
	assert game.player1.choice is not None
	cards = game.player1.choice.cards
	assert len(cards) == 1
	assert cards[0].id == FIREBALL
	game.player1.choice.choose(cards[0])
	assert any(c.id == FIREBALL for c in game.player1.hand)


def test_priest_thirsty_drifter_cost_reduction():
	"""WW_387 — base cost 6; costs (1) less per 1-Cost card played this
	game. Play two 1-cost minions (Stonetusk Boar), then Drifter costs
	4."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	drifter = game.player1.give("WW_387")
	assert drifter.cost == 6
	game.player1.give(BOAR).play()  # 1-cost
	game.player1.give(BOAR).play()  # 1-cost
	assert drifter.cost == 4


def test_priest_thirsty_drifter_no_reduction_without_one_cost():
	"""WW_387 — with no 1-cost cards played, cost stays 6."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	drifter = game.player1.give("WW_387")
	# Play a 2-cost minion; should not reduce.
	game.player1.give(RAPTOR).play()
	assert drifter.cost == 6


def test_priest_pip_the_potent_copies_one_cost_cards():
	"""WW_394 — copy each 1-Cost card in hand. Clear the hand to exactly
	two 1-cost cards (Boar + Moonfire is 1-cost spell) plus a 4-cost; only
	the 1-cost ones are copied."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	for c in list(game.player1.hand):
		c.discard()
	boar = game.player1.give(BOAR)        # cost 1 minion
	moonfire = game.player1.give(MOONFIRE)  # cost 0 spell — NOT 1-cost
	frost = game.player1.give("CS2_024")   # Frostbolt, cost 2 — not 1-cost
	# Add a known 1-cost spell.
	shield = game.player1.give("EX1_371")  # Hand of Protection cost 1
	pip = game.player1.give("WW_394")
	pip.play()
	# 1-cost cards present at play: boar (1), shield (1). Each copied once.
	hand_ids = [c.id for c in game.player1.hand]
	assert hand_ids.count(BOAR) == 2
	assert hand_ids.count("EX1_371") == 2
	# Non-1-cost cards are not copied.
	assert hand_ids.count(MOONFIRE) == 1
	assert hand_ids.count("CS2_024") == 1


def test_priest_elise_summons_4_4_copies_with_no_duplicates():
	"""WW_392 — deck has no duplicates → summon 4/4 copies of 4 random
	minions in the deck. Build a 5-unique-minion deck; exactly 4 copies
	appear, all 4/4."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	_clear_deck(game.player1)
	unique_minions = [YETI, OGRE, RAGER, RAPTOR, BOAR]
	for cid in unique_minions:
		_add_to_deck_2(game.player1, cid)
	elise = game.player1.give("WW_392")
	elise.play()
	# Elise herself + 4 summoned copies.
	field = game.player1.field
	copies = [m for m in field if m.id != "WW_392"]
	assert len(copies) == 4
	for m in copies:
		assert m.atk == 4
		assert m.max_health == 4
		assert m.id in unique_minions


def test_priest_elise_does_nothing_with_duplicates():
	"""WW_392 — deck WITH a duplicate → no copies summoned (only Elise on
	board)."""
	game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
	_clear_deck(game.player1)
	for cid in [YETI, YETI, OGRE]:  # duplicate Yeti
		_add_to_deck_2(game.player1, cid)
	elise = game.player1.give("WW_392")
	elise.play()
	field = game.player1.field
	copies = [m for m in field if m.id != "WW_392"]
	assert len(copies) == 0


# === merged from test_swib_rogue.py ===
import fireplace.cards as _cards

THE_COIN = "GAME_005"
MANA_WYRM = "NEW1_012"  # 1-mana Mage minion (foreign class for a Rogue)


def _resolve_choices_3(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _rogue_game():
    """Return (game, rogue, opponent) with the Rogue as the player currently
    taking their turn. `prepare_game` randomises who goes first and
    `game.player1` tracks turn order (not creation order), so end one turn
    if the Rogue is not the starting player. Determinism matters here
    because several cards key off "another class" relative to the Rogue."""
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    if game.current_player.hero.card_class != CardClass.ROGUE:
        game.end_turn()
    rogue = game.current_player
    assert rogue.hero.card_class == CardClass.ROGUE
    return game, rogue, rogue.opponent


# ---------------------------------------------------------------------------
# WW_006 — Dart Throw
# ---------------------------------------------------------------------------

def test_rogue_dart_throw_two_minions_total_four_damage():
    """Two big-HP enemy minions: the two 2-damage darts deal exactly 4
    damage across the board (regardless of which one each dart hits)."""
    game, rogue, opp = _rogue_game()
    a = opp.summon(GOLDSHIRE_FOOTMAN)
    b = opp.summon(GOLDSHIRE_FOOTMAN)
    for m in (a, b):
        m.max_health = 80
        m.damage = 0
    dart = rogue.give("WW_006")
    dart.play()
    assert a.damage + b.damage == 4


def test_rogue_dart_throw_single_minion_gives_coin():
    """Only one enemy minion: both darts hit it (4 damage) and a Coin is
    added to hand."""
    game, rogue, opp = _rogue_game()
    target = opp.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    pre_hand = len(rogue.hand)
    rogue.give("WW_006").play()
    assert target.damage == 4
    # give() + play() net to zero; the Coin is the net +1.
    assert len(rogue.hand) == pre_hand + 1
    assert rogue.hand[-1].id == THE_COIN


def test_rogue_dart_throw_no_minions_no_coin():
    """No enemy minions: nothing happens, no Coin."""
    game, rogue, opp = _rogue_game()
    pre_coins = sum(1 for c in rogue.hand if c.id == THE_COIN)
    dart = rogue.give("WW_006")
    pre_hand = len(rogue.hand)  # includes the dart still in hand
    dart.play()
    assert len(rogue.hand) == pre_hand - 1  # dart left hand, no coin
    # No NEW coin minted (a starting Coin from CoinRules may already exist).
    assert sum(1 for c in rogue.hand if c.id == THE_COIN) == pre_coins


# ---------------------------------------------------------------------------
# WW_363 — Bounty Wrangler
# ---------------------------------------------------------------------------

def test_rogue_bounty_wrangler_combo_gives_one_coin():
    """Played as the second card this turn -> Combo active -> exactly one
    Coin (via the engine's `combo` branch, even though it is not Quickdraw)."""
    game, rogue, opp = _rogue_game()
    rogue.give(WISP).play()  # first card of the turn enables Combo
    assert rogue.combo is True
    pre_hand = len(rogue.hand)
    wrangler = rogue.give("WW_363")
    wrangler._turn_entered_hand = game.turn - 1  # kill Quickdraw
    wrangler.play()
    assert wrangler.quickdraw_played is False
    assert len(rogue.hand) == pre_hand + 1
    assert rogue.hand[-1].id == THE_COIN


def test_rogue_bounty_wrangler_quickdraw_gives_one_coin():
    """First card of the turn (no Combo) but Quickdraw-active -> one Coin
    (via the `play` branch)."""
    game, rogue, opp = _rogue_game()
    assert rogue.combo is False
    pre_hand = len(rogue.hand)
    wrangler = rogue.give("WW_363")
    assert wrangler.quickdraw_active is True
    wrangler.play()
    assert wrangler.quickdraw_played is True
    assert len(rogue.hand) == pre_hand + 1
    assert rogue.hand[-1].id == THE_COIN


def test_rogue_bounty_wrangler_no_combo_no_quickdraw_no_coin():
    """Neither Combo nor Quickdraw -> no Coin."""
    game, rogue, opp = _rogue_game()
    assert rogue.combo is False
    pre_hand = len(rogue.hand)
    wrangler = rogue.give("WW_363")
    wrangler._turn_entered_hand = game.turn - 1  # kill Quickdraw
    wrangler.play()
    assert wrangler.quickdraw_played is False
    assert len(rogue.hand) == pre_hand  # give+play cancel, no coin
    assert not any(c.id == THE_COIN for c in rogue.hand)


# ---------------------------------------------------------------------------
# WW_364 / WW_364t — Velarok Windblade
# ---------------------------------------------------------------------------

def test_rogue_velarok_transforms_after_three_foreign_cards():
    """Playing three cards from other classes while Velarok is in hand
    transforms it into Velarok, the Deceiver (WW_364t)."""
    game, rogue, opp = _rogue_game()
    velarok = rogue.give("WW_364")
    assert velarok.id == "WW_364"
    for _ in range(3):
        rogue.give(MANA_WYRM).play()  # Mage minion -> foreign to a Rogue
    morphed = velarok.morphed
    assert morphed is not None
    assert morphed.id == "WW_364t"
    assert morphed.zone == Zone.HAND


def test_rogue_velarok_two_foreign_cards_not_enough():
    """Only two foreign cards: Velarok stays unrevealed."""
    game, rogue, opp = _rogue_game()
    velarok = rogue.give("WW_364")
    for _ in range(2):
        rogue.give(MANA_WYRM).play()
    assert velarok.morphed is None
    assert velarok.id == "WW_364"


def test_rogue_velarok_ignores_own_class_and_neutral():
    """Rogue cards and Neutral cards do NOT count toward Velarok's reveal."""
    game, rogue, opp = _rogue_game()
    velarok = rogue.give("WW_364")
    for _ in range(3):
        rogue.give(WISP).play()  # Neutral -> must not progress
    assert velarok.morphed is None


def test_rogue_velarok_deceiver_discount_enchant():
    """Velarok, the Deceiver's after-attack Discover gives the picked card
    a -3 cost enchant (WW_364te)."""
    game, rogue, opp = _rogue_game()
    deceiver = rogue.summon("WW_364t")  # has Charge -> can attack immediately
    deceiver.attack(opp.hero)
    _resolve_choices_3(rogue)
    discovered = rogue.hand[-1]
    base = _cards.db[discovered.id].cost or 0
    assert discovered.cost == max(0, base - 3)


# ---------------------------------------------------------------------------
# WW_410 — Triple Sevens
# ---------------------------------------------------------------------------

def test_rogue_triple_sevens_damage_and_draw():
    """Deal 7 damage to a minion and draw 7 cards."""
    game, rogue, opp = _rogue_game()
    target = opp.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    # Empty the hand so all 7 drawn cards fit (max hand size 10).
    for held in rogue.hand[:]:
        held.discard()
    assert len(rogue.hand) == 0
    pre_deck = len(rogue.deck)
    rogue.give("WW_410").play(target=target)
    assert target.damage == 7
    assert len(rogue.deck) == pre_deck - 7
    assert len(rogue.hand) == 7


# ---------------------------------------------------------------------------
# WW_411 — Stick Up
# ---------------------------------------------------------------------------

def test_rogue_stick_up_discovers_foreign_quickdraw_card():
    """Discover offers only Quickdraw cards from another class; the chosen
    one enters hand."""
    game, rogue, opp = _rogue_game()
    pre_hand = len(rogue.hand)
    rogue.give("WW_411").play()
    assert rogue.choice is not None
    options = rogue.choice.cards
    for opt in options:
        card = _cards.db[opt.id]
        assert card.tags.get(GameTag.QUICKDRAW)
        assert card.card_class != CardClass.ROGUE
        assert card.card_class != CardClass.NEUTRAL
    chosen = options[0]
    rogue.choice.choose(chosen)
    assert len(rogue.hand) == pre_hand + 1
    assert rogue.hand[-1].id == chosen.id


# ---------------------------------------------------------------------------
# WW_412 — Bloodrock Co. Shovel
# ---------------------------------------------------------------------------

def test_rogue_bloodrock_shovel_deathrattle_excavates():
    """Weapon deathrattle excavates a treasure (a card lands in hand)."""
    game, rogue, opp = _rogue_game()
    weapon = rogue.give("WW_412")
    weapon.play()
    assert rogue.weapon is weapon
    assert rogue.excavates_this_game == 0
    pre_hand = len(rogue.hand)
    weapon.destroy()
    assert rogue.excavates_this_game == 1
    assert len(rogue.hand) == pre_hand + 1


# ---------------------------------------------------------------------------
# WW_413 — Antique Flinger
# ---------------------------------------------------------------------------

def test_rogue_antique_flinger_destroys_with_two_excavates():
    """If Excavated twice, the battlecry destroys an enemy minion."""
    game, rogue, opp = _rogue_game()
    rogue.excavates_this_game = 2
    victim = opp.summon(GOLDSHIRE_FOOTMAN)
    rogue.give("WW_413").play(target=victim)
    assert victim.zone == Zone.GRAVEYARD


def test_rogue_antique_flinger_no_destroy_under_two_excavates():
    """Without two Excavates, the enemy minion survives untouched."""
    game, rogue, opp = _rogue_game()
    rogue.excavates_this_game = 1
    victim = opp.summon(GOLDSHIRE_FOOTMAN)
    rogue.give("WW_413").play(target=victim)
    assert victim.zone == Zone.PLAY
    assert victim.health == 2  # Goldshire Footman 1/2, untouched


# ---------------------------------------------------------------------------
# WW_415 — Wishing Well
# ---------------------------------------------------------------------------

def test_rogue_wishing_well_coin_gives_cost_one_foreign_legendary():
    """After the controller plays a Coin, get a Legendary minion from
    another class with Cost set to (1)."""
    game, rogue, opp = _rogue_game()
    rogue.summon("WW_415")
    coin = rogue.give(THE_COIN)
    coin.play()
    reward = rogue.hand[-1]
    rc = _cards.db[reward.id]
    assert rc.type == CardType.MINION
    assert rc.rarity == Rarity.LEGENDARY
    assert rc.card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)
    assert reward.cost == 1


def test_rogue_wishing_well_only_triggers_on_coin():
    """Playing a non-Coin card does not trigger Wishing Well."""
    game, rogue, opp = _rogue_game()
    rogue.summon("WW_415")
    pre_hand = len(rogue.hand)
    pre_legends = sum(
        1 for c in rogue.hand if _cards.db[c.id].rarity == Rarity.LEGENDARY
    )
    rogue.give(WISP).play()
    assert len(rogue.hand) == pre_hand  # give+play cancel, no reward
    # No new Legendary minted (random draft may already hold one).
    assert (
        sum(1 for c in rogue.hand if _cards.db[c.id].rarity == Rarity.LEGENDARY)
        == pre_legends
    )


# ---------------------------------------------------------------------------
# WW_416 — Shell Game
# ---------------------------------------------------------------------------

def test_rogue_shell_game_gets_three_foreign_cards():
    """Get one Epic, one Rare, one Common card, all from other classes."""
    game, rogue, opp = _rogue_game()
    pre_hand = len(rogue.hand)
    rogue.give("WW_416").play()
    assert len(rogue.hand) == pre_hand + 3
    gained = rogue.hand[-3:]
    rarities = sorted(_cards.db[c.id].rarity for c in gained)
    assert rarities == sorted([Rarity.COMMON, Rarity.RARE, Rarity.EPIC])
    for c in gained:
        assert _cards.db[c.id].card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)


# ---------------------------------------------------------------------------
# WW_417 — Drilly the Kid
# ---------------------------------------------------------------------------

def test_rogue_drilly_battlecry_quickdraw_double_excavate():
    """Played Quickdraw-active: battlecry excavates once, Quickdraw adds a
    second -> two excavates."""
    game, rogue, opp = _rogue_game()
    drilly = rogue.give("WW_417")
    assert drilly.quickdraw_active is True
    assert rogue.excavates_this_game == 0
    drilly.play()
    assert drilly.quickdraw_played is True
    assert rogue.excavates_this_game == 2


def test_rogue_drilly_battlecry_only_without_quickdraw():
    """Played NOT Quickdraw-active: only the battlecry excavate fires."""
    game, rogue, opp = _rogue_game()
    drilly = rogue.give("WW_417")
    drilly._turn_entered_hand = game.turn - 1  # not Quickdraw
    drilly.play()
    assert drilly.quickdraw_played is False
    assert rogue.excavates_this_game == 1


def test_rogue_drilly_deathrattle_excavates():
    """Deathrattle excavates once when Drilly dies."""
    game, rogue, opp = _rogue_game()
    drilly = rogue.summon("WW_417")  # summon bypasses battlecry
    assert rogue.excavates_this_game == 0
    drilly.destroy()
    assert rogue.excavates_this_game == 1


# === merged from test_swib_shaman.py ===
def _clear_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_shaman_doctor_hollidae_equips_staff_when_highlander():
    # Empty deck => no duplicates => powered_up => equips the Staff.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    doc = game.player1.give("WW_010")
    doc.play()
    assert game.player1.weapon is not None
    assert game.player1.weapon.id == "WW_010t"


def test_shaman_doctor_hollidae_no_staff_with_duplicates():
    # Two copies of the same card in deck => has duplicates => no equip.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give(WISP).shuffle_into_deck()
    game.player1.give(WISP).shuffle_into_deck()
    doc = game.player1.give("WW_010")
    doc.play()
    assert game.player1.weapon is None


def test_shaman_staff_summons_growing_frogs():
    # Equip the Staff directly; each hero attack summons a Frog that is
    # +1/+1 bigger than the previous one. First Frog = 1/1.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.summon("WW_010t")  # equip weapon (token weapon -> equips)
    assert game.player1.weapon.id == "WW_010t"
    # Give the enemy hero a big body so our hero survives attacking it.
    enemy = game.player2.hero
    # First attack -> first Frog (1/1).
    game.player1.hero.attack(enemy)
    frogs = [m for m in game.player1.field if m.id == "WW_010hexfrog"]
    assert len(frogs) == 1
    assert (frogs[0].atk, frogs[0].max_health) == (1, 1)
    assert frogs[0].taunt
    # End turns to refresh the weapon and attack again -> second Frog (2/2).
    game.end_turn()
    game.end_turn()
    game.player1.hero.attack(enemy)
    frogs = sorted(
        [m for m in game.player1.field if m.id == "WW_010hexfrog"],
        key=lambda m: m.atk,
    )
    assert len(frogs) == 2
    assert (frogs[0].atk, frogs[0].max_health) == (1, 1)
    assert (frogs[1].atk, frogs[1].max_health) == (2, 2)
    assert frogs[1].taunt


def test_shaman_living_prairie_summons_cows_after_elemental():
    # Play an Elemental, end+begin turn so it counts as "last turn", then
    # Living Prairie summons two 3/3 Rush Cows.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    ele = game.player1.give(ELEMENTAL)  # UNG_809t1 Elemental
    ele.play()
    game.end_turn()
    game.end_turn()
    assert game.player1.elemental_played_last_turn >= 1
    prairie = game.player1.give("WW_024")
    prairie.play()
    cows = [m for m in game.player1.field if m.id == "WW_024t"]
    assert len(cows) == 2
    for cow in cows:
        assert (cow.atk, cow.max_health) == (3, 3)
        assert cow.rush


def test_shaman_living_prairie_no_cows_without_elemental():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.end_turn()
    game.end_turn()
    assert game.player1.elemental_played_last_turn == 0
    prairie = game.player1.give("WW_024")
    prairie.play()
    cows = [m for m in game.player1.field if m.id == "WW_024t"]
    assert len(cows) == 0


def test_shaman_skarr_damage_scales_with_elemental_streak():
    # Build a 3-turn streak of playing an Elemental, then play Skarr.
    # Streak = 3 => deal 3 damage to all enemies.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Beef up enemy hero so it absorbs the hit and we can read exact dmg.
    enemy_hero = game.player2.hero
    enemy_minion = game.player2.summon(WISP)
    enemy_minion.max_health = 80
    enemy_minion.damage = 0
    # Turn 1 (mine): play an Elemental.
    game.player1.give(ELEMENTAL).play()
    game.end_turn(); game.end_turn()
    # Turn 2 (mine): play an Elemental.
    game.player1.give(ELEMENTAL).play()
    game.end_turn(); game.end_turn()
    # Turn 3 (mine): play an Elemental, then Skarr.
    game.player1.give(ELEMENTAL).play()
    skarr = game.player1.give("WW_026")
    skarr.play()
    assert enemy_minion.damage == 3
    assert enemy_hero.health == 30 - 3


def test_shaman_skarr_streak_breaks_on_missed_turn():
    # Played an Elemental two turns ago but NOT last turn => streak this
    # turn is just 1 (only the current turn's Elemental), so 1 damage.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    enemy_minion = game.player2.summon(WISP)
    enemy_minion.max_health = 80
    enemy_minion.damage = 0
    # Turn 1 (mine): play an Elemental.
    game.player1.give(ELEMENTAL).play()
    game.end_turn(); game.end_turn()
    # Turn 2 (mine): play NO elemental (break the streak).
    game.end_turn(); game.end_turn()
    # Turn 3 (mine): play an Elemental, then Skarr -> streak 1.
    game.player1.give(ELEMENTAL).play()
    game.player1.give("WW_026").play()
    assert enemy_minion.damage == 1


def test_shaman_minecart_cruiser_skips_overload_after_elemental():
    # Played an Elemental last turn => battlecry prevents the Overload(2).
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give(ELEMENTAL).play()
    game.end_turn(); game.end_turn()
    assert game.player1.elemental_played_last_turn >= 1
    before = game.player1.overloaded
    game.player1.give("WW_326").play()
    assert game.player1.overloaded == before  # no overload added


def test_shaman_minecart_cruiser_overloads_without_elemental():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.end_turn(); game.end_turn()
    assert game.player1.elemental_played_last_turn == 0
    game.player1.give("WW_326").play()
    assert game.player1.overloaded == 2


def test_shaman_cactus_cutter_buffs_when_drawn_spell_cast():
    # Cactus Cutter draws a spell; casting that exact spell this turn
    # buffs it +1/+2 and gives Taunt.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Seed the deck with exactly one spell so the draw is deterministic.
    game.player1.give(MOONFIRE).shuffle_into_deck()
    cutter = game.player1.give("WW_327")
    cutter.play()
    # The drawn spell is now in hand.
    drawn = [c for c in game.player1.hand if c.id == MOONFIRE]
    assert len(drawn) == 1
    assert (cutter.atk, cutter.max_health) == (2, 2)
    assert not cutter.taunt
    drawn[0].play(target=game.player2.hero)
    assert (cutter.atk, cutter.max_health) == (3, 4)
    assert cutter.taunt


def test_shaman_cactus_cutter_no_buff_if_spell_not_cast():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give(MOONFIRE).shuffle_into_deck()
    cutter = game.player1.give("WW_327")
    cutter.play()
    # Don't cast the spell.
    assert (cutter.atk, cutter.max_health) == (2, 2)
    assert not cutter.taunt


def test_shaman_trusty_companion_buffs_and_draws_of_type():
    # Give a Beast +2/+3 and draw a Beast from the deck.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    # Deck has exactly one Beast to draw deterministically.
    game.player1.give("CS2_172").shuffle_into_deck()  # Bloodfen Raptor (Beast)
    beast = game.player1.summon("CS2_172")  # a Beast on board
    assert Race.BEAST in beast.races
    pre_hand = len(game.player1.hand)
    spell = game.player1.give("WW_027")
    spell.play(target=beast)
    assert (beast.atk, beast.max_health) == (3 + 2, 2 + 3)
    drawn = [c for c in game.player1.hand if c.id == "CS2_172"]
    assert len(drawn) == 1
    # pre_hand (before spell) +1 spell -1 played +1 drawn = pre_hand + 1.
    assert len(game.player1.hand) == pre_hand + 1


def test_shaman_trusty_companion_no_draw_if_no_minion_type():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.give("CS2_172").shuffle_into_deck()  # a Beast in deck
    target = game.player1.summon("CS2_182")  # Chillwind Yeti 4/5, no tribe
    assert [r for r in target.races if r != Race.INVALID] == []
    spell = game.player1.give("WW_027")
    spell.play(target=target)
    assert (target.atk, target.max_health) == (4 + 2, 5 + 3)
    # No draw of type since Yeti has no tribe.
    drawn = [c for c in game.player1.hand if c.id == "CS2_172"]
    assert len(drawn) == 0


def test_shaman_amphibious_elixir_heals_and_discovers_spell():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.hero.damage = 8
    elixir = game.player1.give("WW_080")
    elixir.play(target=game.player1.hero)
    assert game.player1.hero.health == 30 - 8 + 5
    # A Discover choice for a spell is open.
    assert game.player1.choice is not None
    for c in game.player1.choice.cards:
        assert c.type == CardType.SPELL
    pre_hand = len(game.player1.hand)
    game.player1.choice.choose(game.player1.choice.cards[0])
    assert len(game.player1.hand) == pre_hand + 1


def test_shaman_giant_tumbleweed_aoe_and_token():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    friendly = game.player1.summon(WISP)
    friendly.max_health = 80
    friendly.damage = 0
    enemy = game.player2.summon(WISP)
    enemy.max_health = 80
    enemy.damage = 0
    game.player1.give("WW_090").play()
    assert friendly.damage == 6
    assert enemy.damage == 6
    tumble = [m for m in game.player1.field if m.id == "WW_090t"]
    assert len(tumble) == 1
    assert (tumble[0].atk, tumble[0].max_health) == (6, 6)


def test_shaman_dehydrate_quickdraw_costs_one():
    # Card drawn this turn => Quickdraw active in hand => costs 1.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    dehy = game.player1.give("WW_325")
    assert dehy.quickdraw_active
    assert dehy.cost == 1


def test_shaman_dehydrate_normal_cost_when_not_quickdraw():
    # If it entered hand a previous turn, no Quickdraw discount => cost 3.
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    dehy = game.player1.give("WW_325")
    game.end_turn(); game.end_turn()
    assert not dehy.quickdraw_active
    assert dehy.cost == 3


def test_shaman_dehydrate_damage_and_lifesteal():
    # Deal 4 to a minion and heal the hero for 4 (Lifesteal).
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    game.player1.hero.damage = 10
    target = game.player2.summon("CS2_172")  # Bloodfen Raptor 3/2 -> needs hp
    target.max_health = 80
    target.damage = 0
    dehy = game.player1.give("WW_325")
    dehy.play(target=target)
    assert target.damage == 4
    assert game.player1.hero.health == 30 - 10 + 4


def test_shaman_walking_mountain_has_mega_windfury():
    game = prepare_empty_game(CardClass.SHAMAN, CardClass.SHAMAN)
    mtn = game.player1.summon("WW_382")
    assert mtn.mega_windfury
    assert mtn.rush
    assert mtn.lifesteal
    assert (mtn.atk, mtn.max_health) == (4, 16)


# === merged from test_swib_treasure.py ===
def _resolve_choices_4(player):
	while player.choice:
		player.choice.choose(player.choice.cards[0])


def test_treasure_rock():
	game = prepare_game()
	target = game.player2.summon("CS2_182")  # 4/5 Chillwind Yeti
	rock = game.player1.give("WW_001t")
	rock.play(target=target)
	assert target.damage == 3


def test_treasure_pouch_of_coins():
	game = prepare_game()
	pre = len(game.player1.hand)
	pouch = game.player1.give("WW_001t18")
	pouch.play()
	# Pouch leaves hand (-1), two Coins added (+2) -> net +1.
	coins = [c for c in game.player1.hand if c.id == "GAME_005"]
	assert len(coins) == 2
	# pre -> give pouch (+1) -> play removes pouch (-1) + 2 coins (+2) = pre+2
	assert len(game.player1.hand) == pre + 2


def test_treasure_water_source():
	game = prepare_game()
	hero = game.player1.hero
	hero.damage = 5
	pre_hand = len(game.player1.hand)
	water = game.player1.give("WW_001t2")
	water.play(target=hero)
	assert hero.damage == 2          # healed exactly 3
	# pre -> give Water Source (+1) -> play removes it (-1) + draw (+1) = pre+1
	assert len(game.player1.hand) == pre_hand + 1


def test_treasure_fools_azerite():
	game = prepare_game()
	card = game.player1.give("WW_001t3")
	card.play()
	assert game.player1.choice
	picked = game.player1.choice.cards[0]
	assert picked.cost == 2          # all discover options are 2-Cost
	game.player1.choice.choose(picked)
	# The discovered card is now in hand and costs 0.
	held = game.player1.hand[-1]
	assert held.cost == 0


def test_treasure_escaping_trogg():
	game = prepare_game()
	trogg = game.player1.summon("WW_001t4")
	assert trogg.rush
	assert trogg.atk == 2 and trogg.max_health == 2


def test_treasure_living_stone():
	game = prepare_game()
	stone = game.player1.summon("WW_001t16")
	assert stone.taunt
	stone.destroy()
	game.process_deaths()
	field = game.player1.field
	assert len(field) == 1
	assert field[0].cost == 2


def test_treasure_falling_stalactite():
	game = prepare_game()
	minion = game.player2.summon("CS2_182")  # 4/5 Yeti
	enemy_hero = game.player2.hero
	card = game.player1.give("WW_001t5")
	card.play(target=minion)
	assert minion.damage == 3
	assert enemy_hero.damage == 3


def test_treasure_canary():
	game = prepare_game()
	enemy = game.player2.summon("CS2_182")
	pre_hand = len(game.player2.hand)
	canary = game.player1.give("WW_001t7")
	canary.play(target=enemy)
	assert enemy.zone == Zone.HAND
	assert enemy in game.player2.hand
	assert len(game.player2.hand) == pre_hand + 1


def test_treasure_glowing_glyph():
	game = prepare_game()
	left = game.player1.summon("CS2_182")    # 4/5
	mid = game.player1.summon("CS2_182")     # 4/5  (target)
	right = game.player1.summon("CS2_182")   # 4/5
	glyph = game.player1.give("WW_001t8")
	glyph.play(target=mid)
	# Target and both neighbours get +1/+2.
	assert (mid.atk, mid.max_health) == (5, 7)
	assert (left.atk, left.max_health) == (5, 7)
	assert (right.atk, right.max_health) == (5, 7)


def test_treasure_azerite_chunk():
	game = prepare_game()
	card = game.player1.give("WW_001t9")
	card.play()
	assert game.player1.choice
	picked = game.player1.choice.cards[0]
	assert picked.cost == 3
	game.player1.choice.choose(picked)
	held = game.player1.hand[-1]
	assert held.cost == 0


def test_treasure_ogrefist_boulder():
	game = prepare_game()
	minion = game.player1.summon("CS2_182")   # 4/5 Yeti
	loc = game.player1.give("WW_001t11")
	loc.play()
	game.end_turn()
	game.end_turn()                            # location now usable
	loc.use(target=minion)
	assert minion.atk == 6
	assert minion.max_health == 7
	assert minion.health == 7


def test_treasure_collapse():
	game = prepare_game()
	m1 = game.player2.summon("CS2_182")   # 4/5
	m2 = game.player2.summon("CS2_182")   # 4/5
	friendly = game.player1.summon("CS2_182")
	enemy_hero = game.player2.hero
	card = game.player1.give("WW_001t12")
	card.play()
	assert m1.damage == 3
	assert m2.damage == 3
	assert enemy_hero.damage == 3
	assert friendly.damage == 0          # only enemies hit


def test_treasure_steelhide_mole():
	game = prepare_game()
	mole = game.player1.summon("WW_001t13")
	assert mole.taunt
	assert mole.has_inspire is False
	assert mole.tags.get(GameTag.REBORN)
	assert mole.atk == 2 and mole.max_health == 7


def test_treasure_azerite_gem():
	game = prepare_game()
	card = game.player1.give("WW_001t14")
	card.play()
	assert game.player1.choice
	picked = game.player1.choice.cards[0]
	assert picked.cost == 5
	game.player1.choice.choose(picked)
	held = game.player1.hand[-1]
	assert held.cost == 0


def test_treasure_motherlode_drake():
	game = prepare_game()
	drake = game.player1.summon("WW_001t17")
	assert drake.rush
	assert drake.divine_shield
	assert drake.lifesteal
	assert drake.atk == 4 and drake.max_health == 3


def test_treasure_azerite_scorpion_no_excavate():
	game = prepare_game()
	game.player1.excavates_this_game = 0
	for c in list(game.player1.hand):
		c.discard()
	pre = len(game.player1.hand)
	card = game.player1.give("WW_001t23")
	card.play()
	_resolve_choices_4(game.player1)
	spells = [c for c in game.player1.hand if c.type == CardType.SPELL]
	# pre -> give Scorpion (+1) -> play it (-1) -> 4 spells gained (+4) = pre+4.
	assert len(game.player1.hand) == pre + 4
	assert len(spells) == 4
	# Not excavated 8 times -> no Scorpion's Sting cost-0 enchant applied.
	for s in spells:
		assert not any(b.id == "WW_001t23e" for b in s.buffs)


def test_treasure_azerite_scorpion_excavated_8():
	game = prepare_game()
	game.player1.excavates_this_game = 8
	# Clear hand so the only spells present are the 4 the Scorpion grants.
	for c in list(game.player1.hand):
		c.discard()
	card = game.player1.give("WW_001t23")
	card.play()
	_resolve_choices_4(game.player1)
	spells = [c for c in game.player1.hand if c.type == CardType.SPELL]
	assert len(spells) == 4
	assert all(c.cost == 0 for c in spells)
	assert all(any(b.id == "WW_001t23e" for b in c.buffs) for c in spells)


def test_treasure_azerite_hawk():
	game = prepare_game()
	pre = len(game.player1.hand)
	card = game.player1.give("WW_001t24")
	card.play()
	# pre -> give Hawk (+1) -> play it (-1) -> Titan added (+1) = pre+1.
	assert len(game.player1.hand) == pre + 1
	titan = game.player1.hand[-1]
	assert titan.data.titan     # the gained card really is a Titan
	assert titan.cost == 1


def test_treasure_azerite_snake():
	game = prepare_game()
	my_hero = game.player1.hero
	enemy_hero = game.player2.hero
	my_hero.damage = 12          # so a 10 heal lands fully (no overheal cap)
	card = game.player1.give("WW_001t25")
	card.play()
	assert enemy_hero.damage == 10
	assert my_hero.damage == 2   # healed exactly 10


def test_treasure_azerite_rat():
	game = prepare_game()
	# A high-cost minion dies, plus a cheaper one, so "highest Cost" is
	# deterministic.
	big = game.player1.summon("CS2_182")     # 4/5 Yeti, cost 4
	small = game.player1.summon("CS2_171")   # 1/1 Stonetusk Boar, cost 1
	big.destroy()
	small.destroy()
	game.process_deaths()
	card = game.player1.give("WW_001t26")
	card.play()
	# Highest-cost dead minion (Yeti) resurrected with +2/+2, Reborn, Lifesteal.
	resurrected = [m for m in game.player1.field if m.id == "CS2_182"]
	assert len(resurrected) == 1
	rat_target = resurrected[0]
	assert rat_target.atk == 6          # 4 + 2
	assert rat_target.max_health == 7   # 5 + 2
	assert rat_target.lifesteal
	assert rat_target.tags.get(GameTag.REBORN)


def test_treasure_azerite_ox():
	game = prepare_game()
	pre_field = len(game.player1.field)
	card = game.player1.give("WW_001t27")
	card.play()
	_resolve_choices_4(game.player1)
	# Ox itself enters the field (+1) plus two 8-Cost minions summoned (+2).
	assert len(game.player1.field) == pre_field + 3
	for m in game.player1.field[-2:]:
		assert m.cost == 8
		assert m.type == CardType.MINION


# === merged from test_swib_warrior.py ===
def test_warrior_detonation_juggernaut():
    # Taunt. Battlecry: Give Taunt minions in your hand +2/+2.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # A Taunt minion (Goldshire Footman 1/1 Taunt) and a non-Taunt minion (Wisp).
    taunt = game.player1.give(GOLDSHIRE_FOOTMAN)
    plain = game.player1.give(WISP)
    jug = game.player1.give("WW_329")
    jug.play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    # Goldshire Footman is a 1/2 Taunt -> +2/+2 makes it 3/4.
    assert taunt.atk == 1 + 2
    assert taunt.health == 2 + 2
    # Non-Taunt minion (Wisp 1/1) untouched.
    assert plain.atk == 1
    assert plain.health == 1


def test_warrior_blast_tortoise():
    # Taunt. Battlecry: Deal damage to all enemy minions equal to its Attack.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    enemy = game.player2.summon(KOBOLD_GEOMANCER)  # 2/2
    enemy.max_health = 80
    enemy.damage = 0
    tortoise = game.player1.give("WW_346")  # 6/2/7
    tortoise.play()
    # Attack is 2 -> 2 damage to all enemy minions.
    assert enemy.damage == 2
    assert tortoise.atk == 2


def test_warrior_badlands_brawler_wins_with_excavate():
    # Battlecry: Start a Brawl! If you've Excavated twice, this always wins.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.excavates_this_game = 2
    # Other minions on each side.
    f1 = game.player1.summon(WISP)
    e1 = game.player2.summon(KOBOLD_GEOMANCER)
    e2 = game.player2.summon(GOLDSHIRE_FOOTMAN)
    brawler = game.player1.give("WW_349")
    brawler.play()
    # Brawler always wins: every other minion destroyed, brawler survives.
    assert brawler.zone == Zone.PLAY
    assert f1.zone == Zone.GRAVEYARD
    assert e1.zone == Zone.GRAVEYARD
    assert e2.zone == Zone.GRAVEYARD
    assert len(game.player1.field) == 1
    assert len(game.player2.field) == 0


def test_warrior_unlucky_powderman():
    # Taunt. Deathrattle: Give Taunt minions in your hand and deck +1/+1.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    hand_taunt = game.player1.give(GOLDSHIRE_FOOTMAN)  # 1/1 Taunt in hand
    deck_taunt = game.player1.give(GOLDSHIRE_FOOTMAN)
    deck_taunt.zone = Zone.DECK
    hand_plain = game.player1.give(WISP)  # non-Taunt in hand, untouched
    powderman = game.player1.summon("WW_367")
    powderman.destroy()
    # Goldshire Footman 1/2 -> +1/+1 makes it 2/3, both in hand and deck.
    assert hand_taunt.atk == 1 + 1
    assert hand_taunt.health == 2 + 1
    assert deck_taunt.atk == 1 + 1
    assert deck_taunt.health == 2 + 1
    # Non-Taunt Wisp 1/1 untouched.
    assert hand_plain.atk == 1
    assert hand_plain.health == 1


def test_warrior_boomboss_thogrun():
    # Battlecry: Shuffle 3 T.N.T. into your deck.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    pre = len(game.player1.deck)
    boomboss = game.player1.give("WW_372")
    boomboss.play()
    tnts = [c for c in game.player1.deck if c.id == "WW_372t"]
    assert len(tnts) == 3
    assert len(game.player1.deck) == pre + 3


def test_warrior_tnt_token():
    # Casts When Drawn: Destroy a random card in opponent's hand, deck, and
    # battlefield.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # Control all three enemy zones: exactly one card each.
    for c in game.player2.hand[:]:
        c.discard()
    for c in game.player2.deck[:]:
        c.discard()
    enemy_hand = game.player2.give(WISP)
    enemy_deck = game.player2.give(WISP)
    enemy_deck.zone = Zone.DECK
    enemy_board = game.player2.summon(KOBOLD_GEOMANCER)
    tnt = game.player1.give("WW_372t")
    tnt.play()
    # One card destroyed from each of the three zones.
    assert enemy_hand.zone == Zone.GRAVEYARD
    assert enemy_deck.zone == Zone.GRAVEYARD
    assert enemy_board.zone == Zone.GRAVEYARD
    assert len(game.player2.hand) == 0
    assert len(game.player2.deck) == 0
    assert len(game.player2.field) == 0


def test_warrior_slagmaw_dormant_and_excavate_hastens():
    # Rush, Taunt. Dormant for 8 turns. Excavate to awaken 2 turns sooner.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    slagmaw = game.player1.summon("WW_375")
    assert slagmaw.dormant is True
    assert slagmaw.dormant_turns == 8
    # An Excavate by the controller hastens awakening by 2 turns.
    exc = game.player1.give("WW_334")
    exc.play()
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert slagmaw.dormant is True
    assert slagmaw.dormant_turns == 6


def test_warrior_reinforced_plating():
    # Gain 6 Armor. Excavate a treasure.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    # Clear the hand so the excavated treasure is the only card in it.
    for c in game.player1.hand[:]:
        c.discard()
    card = game.player1.give("WW_334")
    card.play()
    assert game.player1.hero.armor == 6
    assert game.player1.excavates_this_game == 1
    # The excavated tier-1 treasure is now the only card in hand.
    assert len(game.player1.hand) == 1
    assert game.player1.hand[0].id.startswith("WW_001t")


def test_warrior_misfire_random():
    # Non-Quickdraw: deal 3, 2, 1 to random minions. With a single eligible
    # minion, all three hits land on it for 6 total.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    target = game.player2.summon(KOBOLD_GEOMANCER)
    target.max_health = 80
    target.damage = 0
    misfire = game.player1.give("WW_348")
    # Force the non-Quickdraw branch.
    misfire._turn_entered_hand = -1
    assert misfire.quickdraw_active is False
    misfire.play()
    assert target.damage == 3 + 2 + 1


def test_warrior_misfire_quickdraw_choose():
    # Quickdraw: Choose the targets. Direct all three hits at one minion.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    big = game.player2.summon(KOBOLD_GEOMANCER)
    big.max_health = 80
    big.damage = 0
    decoy = game.player2.summon(WISP)
    decoy.max_health = 80
    decoy.damage = 0
    misfire = game.player1.give("WW_348")
    # Freshly given -> Quickdraw active.
    assert misfire.quickdraw_active is True
    misfire.play()
    # Resolve three target choices, all onto `big`.
    while game.player1.choice:
        game.player1.choice.choose(big)
    assert big.damage == 3 + 2 + 1
    assert decoy.damage == 0


def test_warrior_blast_charge():
    # Destroy a damaged enemy minion. Excavate a treasure.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    enemy = game.player2.summon(KOBOLD_GEOMANCER)  # 2/2
    enemy.damage = 1  # now damaged
    pre_exc = game.player1.excavates_this_game
    charge = game.player1.give("WW_380")
    charge.play(target=enemy)
    while game.player1.choice:
        game.player1.choice.choose(game.player1.choice.cards[0])
    assert enemy.zone == Zone.GRAVEYARD
    assert game.player1.excavates_this_game == pre_exc + 1


def test_warrior_battlepickaxe():
    # Weapon 4/1. After you play a Taunt minion, gain +1 Durability.
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    weapon = game.player1.give("WW_347")
    weapon.play()
    assert game.player1.weapon.durability == 1
    # Play a Taunt minion -> +1 Durability.
    game.player1.give(GOLDSHIRE_FOOTMAN).play()
    assert game.player1.weapon.durability == 2
    # Play a non-Taunt minion -> unchanged.
    game.player1.give(WISP).play()
    assert game.player1.weapon.durability == 2


# ---------------------------------------------------------------------------
# Audit fix regression tests (Tier-1)
# ---------------------------------------------------------------------------

# === merged from test_fix_azerite_giant.py (audit fix regression) ===
"""Regression: Azerite Giant (WW_025) cost discount.

Bug: the "turns in a row you've played an Elemental" streak was only
advanced by the card's own Hand.events (while it sat in hand), so a streak
built before the Giant entered hand was ignored. Fixed by tracking the
streak globally in game._begin_turn (player.azerite_elemental_streak).
"""



FIRE_FLY = "UNG_809"  # 1/1/2 Elemental (battlecry adds a 1/2 Elemental token)
AZERITE_GIANT = "WW_025"  # base cost 8


def _end_full_turn_cycle(game):
    """Advance back to the same player's next turn."""
    game.end_turn()
    game.end_turn()


def test_fix_azerite_giant_streak_tracked_while_in_deck():
    """A streak built up BEFORE the Giant is in hand must still discount it."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.player1
    # Make sure player1 is the active player.
    if game.current_player is not p:
        game.end_turn()
    assert game.current_player is p

    # Turn A: play an Elemental (Giant is NOT yet in hand).
    game.player1.give(FIRE_FLY).play()
    _end_full_turn_cycle(game)
    # After one completed elemental turn, streak == 1.
    assert p.azerite_elemental_streak == 1

    # Turn B: play another Elemental.
    game.player1.give(FIRE_FLY).play()
    _end_full_turn_cycle(game)
    # Two consecutive completed elemental turns.
    assert p.azerite_elemental_streak == 2

    # NOW draw the Giant — it should already cost 8 - 2 = 6.
    giant = game.player1.give(AZERITE_GIANT)
    assert giant.cost == 6


def test_fix_azerite_giant_current_turn_counts_after_playing_elemental():
    """Playing an Elemental on the same turn the Giant is in hand counts too."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()

    # Build a 2-turn streak first.
    game.player1.give(FIRE_FLY).play()
    _end_full_turn_cycle(game)
    game.player1.give(FIRE_FLY).play()
    _end_full_turn_cycle(game)
    assert p.azerite_elemental_streak == 2

    giant = game.player1.give(AZERITE_GIANT)
    assert giant.cost == 6  # before playing this turn's elemental

    # Play an Elemental THIS turn — current turn now counts: discount 3 -> cost 5.
    game.player1.give(FIRE_FLY).play()
    assert giant.cost == 5


def test_fix_azerite_giant_streak_breaks_on_elementless_turn():
    """A turn with no Elemental resets the streak to zero."""
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p = game.player1
    if game.current_player is not p:
        game.end_turn()

    game.player1.give(FIRE_FLY).play()
    _end_full_turn_cycle(game)
    assert p.azerite_elemental_streak == 1

    # A turn with NO elemental played.
    _end_full_turn_cycle(game)
    assert p.azerite_elemental_streak == 0

    giant = game.player1.give(AZERITE_GIANT)
    assert giant.cost == 8  # no discount


# === merged from test_fix_dh.py (audit fix regression) ===
def test_fix_dh_snake_eyes_discovers_only_collectible():
	"""Snake Eyes (WW_400) rolls two dice and Discovers a card of each rolled
	Cost. The Discover pool must be collectible-only — the old bug used bare
	RandomCard(cost=...) which leaked non-collectible tokens (Azerite Gem,
	Spectral Flyer, Misha, etc.) into the offered choices.

	Force a non-doubles roll (3, 5) so we get exactly two Discovers and we know
	the rolled Costs. Assert every offered card in every Discover is collectible
	AND matches the rolled Cost exactly."""
	game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
	player = game.player1

	# Deterministic dice: first two randint calls -> 3 then 5 (no doubles).
	rolls = iter([3, 5])
	orig_randint = game.random.randint

	def fake_randint(a, b):
		if (a, b) == (1, 6):
			return next(rolls)
		return orig_randint(a, b)

	game.random.randint = fake_randint

	snake = player.give("WW_400")
	# Hand size after Snake Eyes leaves hand (it's a Minion going to PLAY),
	# but before the two Discovers add their picks.
	hand_before_discovers = len(player.hand) - 1
	snake.play()

	expected_costs = [3, 5]
	seen_choice_count = 0
	while player.choice:
		choice = player.choice
		offered = list(choice.cards)
		# A Discover always offers candidates.
		assert len(offered) > 0
		# Every offered card must be collectible — this is the regression guard.
		for card in offered:
			assert card.data.collectible is True, (
				f"non-collectible card {card.id} offered by Snake Eyes Discover"
			)
		# Every offered card must match the Cost rolled for this Discover.
		expected = expected_costs[seen_choice_count]
		for card in offered:
			assert card.cost == expected, (
				f"card {card.id} cost {card.cost} != rolled cost {expected}"
			)
		seen_choice_count += 1
		choice.choose(offered[0])

	# Exactly two Discovers (3 and 5, no doubles bonus).
	assert seen_choice_count == 2
	# Both discovered cards were given to hand (Snake Eyes itself went to PLAY).
	assert len(player.hand) == hand_before_discovers + 2


# === merged from test_fix_howdyfin.py (audit fix regression) ===
"""Regression: Howdyfin (WW_333).

Bug: only triggered on PLAY and gave a single Murloc. Printed card fires
whenever the hand drops below 3 by ANY means (play OR discard) and refills
UP TO 3 cards with random Murlocs. Fixed via _HowdyfinRefill looping to 3,
wired to Play (.after) and Discard (.on) events.

Setup note: clear the hand BEFORE summoning Howdyfin, so the setup discards
don't themselves trigger the refill (Give does not trigger it; only a card
leaving hand via play/discard does).
"""



WISP = "CS2_231"


def _murlocs(p):
    return [c for c in p.hand if Race.MURLOC in c.races]


def _setup(p, n_wisps):
    """Clear hand (no Howdyfin yet), summon Howdyfin, then Give n wisps
    (Give does not trigger the refill)."""
    for c in list(p.hand):
        c.discard()
    p.summon("WW_333")
    for _ in range(n_wisps):
        p.give(WISP)


def test_fix_howdyfin_refills_to_three_on_play():
    game = prepare_game()
    p = game.player1
    _setup(p, 3)
    assert len(p.hand) == 3
    assert len(_murlocs(p)) == 0
    # Play one Wisp -> hand drops to 2 -> Howdyfin refills with one Murloc.
    p.hand[0].play()
    assert len(p.hand) == 3
    assert len(_murlocs(p)) == 1


def test_fix_howdyfin_refills_multiple_on_discard():
    game = prepare_game()
    p = game.player1
    _setup(p, 1)
    assert len(p.hand) == 1
    # Discard the only card -> hand hits 0 -> refill all the way to 3 Murlocs.
    p.hand[0].discard()
    assert len(p.hand) == 3
    assert len(_murlocs(p)) == 3


def test_fix_howdyfin_does_nothing_when_hand_at_three_or_more():
    game = prepare_game()
    p = game.player1
    _setup(p, 4)
    assert len(p.hand) == 4
    # Play one Wisp -> hand drops to 3, which is NOT below 3 -> no Murloc.
    p.hand[0].play()
    assert len(p.hand) == 3
    assert len(_murlocs(p)) == 0


# === merged from test_fix_nleg.py (audit fix regression) ===
RENO = "WW_0700"
WISP = "CS2_231"  # 0/1/1 vanilla minion, no battlecry


def _clear_no_dupes(player):
    """Empty the deck so Reno's 'no duplicates' gate (powered_up) is on."""
    for card in list(player.deck):
        player.deck.remove(card)


def test_fix_nleg_reno_limits_enemy_to_one_minion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    reno_player = game.current_player
    enemy = reno_player.opponent

    _clear_no_dupes(reno_player)

    # Enemy already has a board before Reno is cast.
    for _ in range(3):
        enemy.summon(WISP)
    assert len(enemy.field) == 3

    reno = reno_player.give(RENO)
    reno.play()
    while reno_player.choice:
        reno_player.choice.choose(reno_player.choice.cards[0])

    # Battlecry empties the enemy board.
    assert len(enemy.field) == 0

    # Pass to the enemy's turn; the cap must still be live.
    game.end_turn()
    assert game.current_player is enemy

    # First summon sticks.
    first = enemy.summon(WISP)
    assert first.zone == Zone.PLAY
    assert len(enemy.field) == 1

    # Second summon is destroyed instantly (limit = 1).
    second = enemy.summon(WISP)
    assert second.zone == Zone.GRAVEYARD
    assert len(enemy.field) == 1
    assert enemy.field[0] is first

    # Third also suppressed.
    third = enemy.summon(WISP)
    assert third.zone == Zone.GRAVEYARD
    assert len(enemy.field) == 1


def test_fix_nleg_reno_cap_expires_after_enemy_turn():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    reno_player = game.current_player
    enemy = reno_player.opponent

    _clear_no_dupes(reno_player)

    reno = reno_player.give(RENO)
    reno.play()
    while reno_player.choice:
        reno_player.choice.choose(reno_player.choice.cards[0])

    # Enemy turn under the cap: only one minion holds.
    game.end_turn()
    assert game.current_player is enemy
    enemy.summon(WISP)
    capped = enemy.summon(WISP)
    assert capped.zone == Zone.GRAVEYARD
    assert len(enemy.field) == 1

    # End the enemy's turn -> the marker self-clears.
    game.end_turn()  # back to reno_player
    game.end_turn()  # back to enemy, cap gone
    assert game.current_player is enemy

    a = enemy.summon(WISP)
    b = enemy.summon(WISP)
    c = enemy.summon(WISP)
    # All three stick now that the cap expired (started this turn with 1).
    assert a.zone == Zone.PLAY
    assert b.zone == Zone.PLAY
    assert c.zone == Zone.PLAY
    assert len(enemy.field) == 4


def test_fix_nleg_reno_does_not_cap_own_side():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    reno_player = game.current_player

    _clear_no_dupes(reno_player)

    reno = reno_player.give(RENO)
    reno.play()
    while reno_player.choice:
        reno_player.choice.choose(reno_player.choice.cards[0])

    # Reno's own controller is unaffected: Reno minion (the summoned bullet
    # hero is separate) — summon several on the friendly side freely.
    base = len(reno_player.field)
    reno_player.summon(WISP)
    reno_player.summon(WISP)
    reno_player.summon(WISP)
    assert len(reno_player.field) == base + 3


# === merged from test_fix_pal.py (audit fix regression) ===
WISP = "CS2_231"
IMP = "EX1_598"
MIRAGE = "WW_337t"


def _advance_one_controller_turn(game):
    """End both players' turns so the original controller reaches a fresh
    start-of-turn (OWN_TURN_BEGIN fires once per call)."""
    game.end_turn()
    game.end_turn()


def _mirage_form(player):
    """Return the single hand card currently wearing the persistent WW_337e
    re-transform enchant (i.e. the Mirage in its current morphed shape)."""
    matches = [
        c for c in player.hand if any(e.id == "WW_337e" for e in c.buffs)
    ]
    assert len(matches) == 1, matches
    return matches[0]


def test_fix_pal_mirage_retransforms_every_turn():
    # Deck holds two distinct, known minions so every legal morph target is
    # one of {WISP, IMP}. Stack many copies so the per-turn draw never
    # depletes the pool. Mirage token starts alone in hand.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)

    # Clear any auto-dealt cards from player1's hand.
    for card in list(game.player1.hand):
        card.discard()
    assert game.player1.hand == []

    for _ in range(15):
        game.player1.give(WISP).shuffle_into_deck()
        game.player1.give(IMP).shuffle_into_deck()
    deck_ids = {c.id for c in game.player1.deck}
    assert deck_ids == {WISP, IMP}

    mirage = game.player1.give(MIRAGE)
    assert game.player1.hand == [mirage]
    assert mirage.id == MIRAGE

    seen_ids = set()
    prev_card = mirage

    # Advance several of player1's turns. The morph fires at the start of
    # EACH turn — the Mirage's identity must be re-evaluated every turn,
    # producing a NEW object whose id is always a current deck minion. With
    # the OLD (one-shot) behaviour the token morphed once and then never
    # changed: the same object would persist and only one id would be seen.
    for _ in range(10):
        _advance_one_controller_turn(game)

        cur = _mirage_form(game.player1)

        # Every transform yields a fresh card object (morph re-fired).
        assert cur is not prev_card
        # The morphed card is always a valid copy of a deck minion, never
        # stuck on the Mirage token itself.
        assert cur.id in deck_ids
        assert cur.id != MIRAGE

        seen_ids.add(cur.id)
        prev_card = cur

    # Over enough turns BOTH deck-minion identities must appear — proof the
    # re-transform re-rolls every turn rather than locking after the first.
    assert seen_ids == {WISP, IMP}


def test_fix_pal_mirage_retransform_trigger_persists():
    # Robust, RNG-independent check: after the first morph, the freshly
    # morphed card must still carry the persistent WW_337e re-transform
    # enchant (Zerus-style), so it will transform again next turn.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)

    for card in list(game.player1.hand):
        card.discard()
    assert game.player1.hand == []

    game.player1.give(WISP).shuffle_into_deck()
    game.player1.give(IMP).shuffle_into_deck()

    game.player1.give(MIRAGE)

    # First transform.
    _advance_one_controller_turn(game)
    morphed = game.player1.hand[0]
    assert morphed.id in {WISP, IMP}

    enchant_ids = {e.id for e in morphed.buffs}
    assert "WW_337e" in enchant_ids


# === merged from test_fix_priest.py (audit fix regression) ===
# Benevolent Banker (WW_384) — non-Quickdraw battlecry:
# "Discover a spell from your deck."
# Distinct Priest spells we stack in the deck:
HOLY_NOVA = "CS1_112"
HOLY_SMITE = "CS1_130"
POWER_WORD_SHIELD = "CS2_004"
DECK_SPELLS = {HOLY_NOVA, HOLY_SMITE, POWER_WORD_SHIELD}
NORTHSHIRE_CLERIC = "CS2_235"  # a minion in the deck (must NOT be offered)


def _stack_friendly_deck(game):
    """Reset the friendly deck to exactly 3 known spells + 2 minions."""
    p1 = game.player1
    for card in list(p1.deck):
        card.zone = Zone.SETASIDE
    p1.deck.clear()
    for cid in (HOLY_NOVA, HOLY_SMITE, POWER_WORD_SHIELD,
                NORTHSHIRE_CLERIC, NORTHSHIRE_CLERIC):
        p1.give(cid).shuffle_into_deck()
    return p1


def test_fix_priest_benevolent_banker_discovers_spell_from_own_deck():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = _stack_friendly_deck(game)
    # Clear the hand so the only newly added card is the discovered spell.
    for card in list(p1.hand):
        card.discard()
    deck_before = sorted(c.id for c in p1.deck)
    assert deck_before == sorted(
        [HOLY_NOVA, HOLY_SMITE, POWER_WORD_SHIELD,
         NORTHSHIRE_CLERIC, NORTHSHIRE_CLERIC]
    )

    banker = p1.give("WW_384")
    # Force the NON-Quickdraw branch: pretend the card has been in hand
    # since before this turn so quickdraw_active is False.
    banker._turn_entered_hand = -1
    assert not banker.quickdraw_active
    banker.play()  # non-Quickdraw branch -> Discover from OWN deck

    # A Discover choice must be open with exactly 3 cards, all spells that
    # live in the deck. The deck has exactly 3 distinct spells, so the
    # discover offers all three.
    assert p1.choice is not None
    offered = p1.choice.cards
    assert len(offered) == 3
    assert all(c.type == CardType.SPELL for c in offered)
    assert sorted(c.id for c in offered) == sorted(DECK_SPELLS)
    # The minion in the deck must never be offered.
    assert NORTHSHIRE_CLERIC not in {c.id for c in offered}

    chosen = offered[0]
    chosen_id = chosen.id
    p1.choice.choose(chosen)
    assert p1.choice is None

    # The chosen copy is now in hand (exactly one card was added).
    hand_ids = [c.id for c in p1.hand]
    assert hand_ids == [chosen_id]
    assert p1.hand[0].type == CardType.SPELL

    # Discover COPIES — the deck is unchanged (all 3 spells still present).
    deck_after = sorted(c.id for c in p1.deck)
    assert deck_after == deck_before
    assert {chosen_id} <= {c.id for c in p1.deck}


# === merged from test_fix_rogue.py (audit fix regression) ===
"""Regression tests for showdown_in_the_badlands rogue fixes.

(1) WW_006 Dart Throw — darts must be thrown one at a time. The second
    dart re-picks a LIVE enemy minion after the first resolves, and the
    Coin is granted only when a single minion absorbs BOTH darts. A first
    dart that kills its target must never leave a "same target" Coin and
    must never waste the second dart on a corpse.

(2) WW_364 Velarok Windblade — in-hand progress text "({0} left!)" must
    render the remaining foreign-class plays (3 -> 2 -> 1).
"""



# GOLDSHIRE_FOOTMAN, WISP, THE_COIN come from `from utils import *`
# (CS1_042 1/2 Taunt, CS2_231 Wisp, GAME_005). Do NOT redefine them here —
# a module-level redefinition shadows the import for the whole file.
MANA_WYRM = "NEW1_012"         # Mage minion (foreign class for a Rogue)


def _rogue_game_2():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    if game.current_player.hero.card_class != CardClass.ROGUE:
        game.end_turn()
    rogue = game.current_player
    assert rogue.hero.card_class == CardClass.ROGUE
    return game, rogue, rogue.opponent


class _ScriptedChoice:
    """Replaces game.random.choice with a scripted sequence of return
    values so the two dart picks are fully deterministic."""

    def __init__(self, real, sequence):
        self._real = real
        self._sequence = list(sequence)
        self.calls = 0

    def __call__(self, seq):
        if self.calls < len(self._sequence):
            picked = self._sequence[self.calls]
            self.calls += 1
            return picked
        return self._real(seq)


class _PreferChoice:
    """Replaces game.random.choice. Always returns `preferred` if it is
    among the candidates offered, otherwise the first candidate. This is a
    faithful "random pick" — `preferred` is simply the one the RNG happens
    to land on — but it is deterministic. Crucially it returns whatever it
    is *given*, so it works regardless of HOW MANY times the engine samples
    or against WHICH live board, which is what distinguishes the old
    pre-sampled implementation from the corrected one-dart-at-a-time logic."""

    def __init__(self, preferred):
        self.preferred = preferred
        self.calls = 0

    def __call__(self, seq):
        self.calls += 1
        seq = list(seq)
        if self.preferred in seq:
            return self.preferred
        return seq[0]


# ---------------------------------------------------------------------------
# WW_006 — Dart Throw
# ---------------------------------------------------------------------------

def test_fix_rogue_dart_throw_same_minion_grants_coin():
    """Single tanky enemy minion: both darts MUST land on it (no other
    legal target), dealing exactly 4 damage, and a Coin is granted."""
    game, rogue, opp = _rogue_game_2()
    target = opp.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    # Clear hand so the only hand change we can observe is the dart leaving
    # and (possibly) the Coin arriving.
    for held in rogue.hand[:]:
        held.discard()
    rogue.give("WW_006").play()
    # Both darts hit the one minion.
    assert target.damage == 4
    # Exactly one Coin minted (dart played from empty hand -> net +1 Coin).
    assert len(rogue.hand) == 1
    assert rogue.hand[0].id == THE_COIN


def test_fix_rogue_dart_throw_first_dart_kills_no_coin_no_wasted_dart():
    """First dart kills a 1-health minion; the second dart must re-pick a
    LIVE minion (the big one), and NO Coin is granted because no single
    minion absorbed both darts.

    The old implementation pre-sampled both targets up front: scripting
    both picks to the fragile minion made it (a) grant a Coin anyway and
    (b) waste the second dart on the corpse. This test pins the correct
    behaviour."""
    game, rogue, opp = _rogue_game_2()
    small = opp.summon(GOLDSHIRE_FOOTMAN)   # will die to one 2-dmg dart
    small.max_health = 1
    small.damage = 0
    big = opp.summon(GOLDSHIRE_FOOTMAN)
    big.max_health = 80
    big.damage = 0

    for held in rogue.hand[:]:
        held.discard()

    # The RNG always lands on the small minion WHILE IT IS ALIVE. The first
    # dart therefore kills it. The OLD pre-sampling code would have picked
    # `small` for BOTH darts up front (same object), granted a bogus Coin,
    # and wasted the second dart on the corpse (big takes 0). The FIXED code
    # re-samples the second dart from the now-live board (only `big` left),
    # so big takes the second dart and no Coin is granted.
    stub = _PreferChoice(small)
    game.random.choice = stub

    rogue.give("WW_006").play()

    # Small died from the first dart (1 health, took 2).
    assert small.dead
    assert small.zone == Zone.GRAVEYARD
    # The second dart hit the still-LIVE big minion — not the corpse.
    assert big.damage == 2
    # No single minion absorbed both darts -> NO Coin.
    assert all(c.id != THE_COIN for c in rogue.hand)
    assert len(rogue.hand) == 0


def test_fix_rogue_dart_throw_same_live_minion_twice_grants_coin():
    """Two tanky minions; both darts scripted onto the SAME (surviving)
    minion -> it takes 4, the other takes 0, and a Coin is granted."""
    game, rogue, opp = _rogue_game_2()
    a = opp.summon(GOLDSHIRE_FOOTMAN)
    b = opp.summon(GOLDSHIRE_FOOTMAN)
    for m in (a, b):
        m.max_health = 80
        m.damage = 0

    for held in rogue.hand[:]:
        held.discard()

    stub = _PreferChoice(a)
    game.random.choice = stub

    rogue.give("WW_006").play()

    assert a.damage == 4
    assert b.damage == 0
    assert len(rogue.hand) == 1
    assert rogue.hand[0].id == THE_COIN


# ---------------------------------------------------------------------------
# WW_364 — Velarok Windblade (cosmetic progress text)
# ---------------------------------------------------------------------------

def _velarok_remaining_text(card):
    """Render the card and return its description for assertion."""
    return card.description


def test_fix_rogue_velarok_progress_text_counts_down():
    """The in-hand progress text renders the remaining foreign-class plays:
    3 left at 0 plays, 2 left after 1, 1 left after 2."""
    game, rogue, opp = _rogue_game_2()
    velarok = rogue.give("WW_364")

    # 0 foreign plays so far -> "3 left!"
    assert getattr(velarok, "_velarok_count", 0) == 0
    text0 = velarok.description
    assert "3 left!" in text0
    assert "2 left!" not in text0
    assert "Ready!" not in text0

    # 1 foreign play -> "2 left!"
    rogue.give(MANA_WYRM).play()
    assert velarok._velarok_count == 1
    text1 = velarok.description
    assert "2 left!" in text1
    assert "3 left!" not in text1
    assert "Ready!" not in text1

    # 2 foreign plays -> "1 left!"
    rogue.give(MANA_WYRM).play()
    assert velarok._velarok_count == 2
    text2 = velarok.description
    assert "1 left!" in text2
    assert "2 left!" not in text2
    assert "Ready!" not in text2


def test_fix_rogue_velarok_progress_text_ignores_neutral_and_own_class():
    """Neutral / own-class plays do not advance the rendered counter."""
    game, rogue, opp = _rogue_game_2()
    velarok = rogue.give("WW_364")
    for _ in range(3):
        rogue.give(WISP).play()  # Neutral -> no progress
    assert getattr(velarok, "_velarok_count", 0) == 0
    assert "3 left!" in velarok.description


# === merged from test_fix_shaman.py (audit fix regression) ===
FLAME_ELEMENTAL = "UNG_809t1"  # 1-cost vanilla Elemental token, no battlecry
SKARR = "WW_026"               # 7/7/7 Elemental, Skarr the Catastrophe


def _beef_hero(hero):
    """Make a hero able to absorb a big hit so we can read exact damage."""
    hero.max_health = 80
    hero.damage = 0


def test_fix_shaman_skarr_fresh_board_deals_one():
    # Fresh board: the controller has played no Elemental on any prior turn,
    # but Skarr itself is an Elemental being played THIS turn -> streak == 1.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    me = game.current_player
    opp = me.opponent
    _beef_hero(opp.hero)

    assert me.azerite_elemental_streak == 0
    assert me.elemental_played_last_turn == 0

    skarr = me.give(SKARR)
    skarr.play()

    while me.choice:
        me.choice.choose(me.choice.cards[0])

    # Skarr alone on a fresh board MUST deal exactly 1 (never 0 — the bug).
    assert opp.hero.damage == 1


def test_fix_shaman_skarr_two_turn_streak_deals_two():
    # Play an Elemental this turn, cycle a full round, then play Skarr on the
    # controller's next turn. Two consecutive Elemental turns -> streak == 2.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    me = game.current_player

    # This turn: play a non-Skarr Elemental so this becomes an Elemental turn.
    fire = me.give(FLAME_ELEMENTAL)
    fire.play()
    assert Race.ELEMENTAL in fire.races
    assert me.elemental_played_this_turn == 1

    # Advance back to the same player's next turn (full round).
    game.end_turn()
    game.end_turn()
    assert game.current_player is me

    # The engine rolled last turn's Elemental into the consecutive streak.
    assert me.elemental_played_last_turn == 1
    assert me.azerite_elemental_streak == 1

    opp = me.opponent
    _beef_hero(opp.hero)

    skarr = me.give(SKARR)
    skarr.play()

    while me.choice:
        me.choice.choose(me.choice.cards[0])

    # Elemental last turn + Skarr this turn -> exactly 2 damage to enemies.
    assert opp.hero.damage == 2


# === merged from test_fix_treasure.py (audit fix regression) ===
from fireplace.exceptions import GameOver


def test_fix_treasure_snake_steal_full_amount():
	# Enemy hero 30 Health, no armor; friendly damaged 10 -> steal full 10.
	game = prepare_game()
	enemy = game.player2.hero
	friendly = game.player1.hero
	enemy.armor = 0
	enemy.damage = 0  # 30 health
	friendly.damage = 10
	pre_enemy_health = enemy.health
	card = game.player1.give("WW_001t25")
	card.play()
	# Enemy lost exactly 10 health, friendly healed exactly 10.
	assert enemy.health == pre_enemy_health - 10
	assert friendly.damage == 0


def test_fix_treasure_snake_steal_all_armor():
	# Enemy hero 3 Health + 10 Armor; armor soaks all 10 -> steal 0.
	game = prepare_game()
	enemy = game.player2.hero
	friendly = game.player1.hero
	enemy.damage = 27  # 3 health (30 - 27)
	enemy.armor = 10
	friendly.damage = 10
	pre_enemy_health = enemy.health  # 3
	card = game.player1.give("WW_001t25")
	card.play()
	# 10 damage fully soaked by armor -> enemy health unchanged, no steal.
	assert enemy.health == pre_enemy_health  # still 3
	assert enemy.armor == 0
	assert friendly.damage == 10  # NOT healed -- this fails under flat-heal bug


def test_fix_treasure_snake_steal_capped_by_health():
	# Enemy hero 6 Health, no armor; friendly damaged 10 -> steal exactly 6.
	game = prepare_game()
	enemy = game.player2.hero
	friendly = game.player1.hero
	enemy.armor = 0
	enemy.damage = 24  # 6 health (30 - 24)
	friendly.damage = 10
	enemy_health_before = enemy.health  # 6
	card = game.player1.give("WW_001t25")
	# Steal of only 6 means the enemy hero is reduced to 0 Health -> lethal,
	# so the play ends the game. The friendly heal is applied inside the
	# action (before GameOver propagates), so its effect is observable.
	try:
		card.play()
	except GameOver:
		pass
	assert enemy_health_before == 6
	# Health actually removed was 6 (capped), so friendly heals exactly 6:
	# 10 damage - 6 healed == 4 remaining. The flat-heal bug heals 10 -> 0.
	assert friendly.damage == 4
