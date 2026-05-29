"""Perils in Paradise — DRUID collectible cards.

Tests assert the PRINTED card behaviour. One test (cluster) per collectible
card: Cruise Captain Lora, Dozing Dragon, Hiking Trail, Tortollan Traveler,
Mistah Vistah, Bouldering Buddy (minions); Trail Mix, Sleep Under the Stars,
Hydration Station, New Heights (spells); Hiking Trail (location).
"""

from utils import *

from hearthstone.enums import CardType, GameTag, Zone

import fireplace.cards as _cards


# VAC_506 — Cruise Captain Lora (7/4/5 Pirate): Battlecry: Summon 2 random
# locations.
def test_cruise_captain_lora():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    lora = p1.give("VAC_506")
    lora.play()
    # Lora is on the board.
    assert lora in p1.field
    # Battlecry summons 2 random locations. A player can hold only ONE location
    # at a time (HS rule — the 2nd replaces the 1st), so the final state has a
    # single random collectible location in play.
    assert p1.location is not None
    assert p1.location.type == CardType.LOCATION
    assert p1.location.id != "VAC_506"


# VAC_511 — Dozing Dragon (5/3/5 Dragon): Dormant for 2 turns. While Dormant,
# summon a 3/5 Dragon with Taunt at the end of your turn.
def test_dozing_dragon_dormant_summons_whelp_each_dormant_turn_end():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    dragon = p1.give("VAC_511")
    dragon.play()
    assert dragon.dormant
    assert dragon.dormant_turns == 2
    # End of this (controller's) turn while dormant -> summon one Restless Whelp.
    pre = len([m for m in p1.field if m.id == "VAC_511t"])
    game.end_turn()
    whelps = [m for m in p1.field if m.id == "VAC_511t"]
    assert len(whelps) == pre + 1
    whelp = whelps[0]
    # Restless Whelp (VAC_511t) is a 3/5 Dragon (data line 4/3/5 = cost/atk/hp).
    assert whelp.atk == 3 and whelp.max_health == 5
    assert whelp.taunt
    assert Race.DRAGON in whelp.races


def test_dozing_dragon_awakens_after_two_turns():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    dragon = p1.give("VAC_511")
    dragon.play()
    assert dragon.dormant
    # Two full rounds (begin-turn ticks dormant_turns twice) -> awaken.
    game.end_turn()  # p2's turn
    game.end_turn()  # back to p1 (tick 1)
    assert dragon.dormant_turns == 1
    assert dragon.dormant
    game.end_turn()
    game.end_turn()  # back to p1 (tick 2 -> Awaken)
    assert dragon.dormant_turns == 0
    assert not dragon.dormant


# VAC_518 — Tortollan Traveler (3/1/5): Taunt. Deathrattle: Draw another Taunt
# minion. Reduce its Cost by (2).
def test_tortollan_traveler_deathrattle_draws_taunt_and_discounts():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Seed deck with exactly one Taunt minion of known cost.
    taunt = p1.card(GOLDSHIRE_FOOTMAN)  # 1-cost 1/2 Taunt
    taunt.zone = Zone.DECK
    base_cost = taunt.cost
    traveler = p1.summon("VAC_518")
    assert traveler.taunt
    traveler.destroy()
    game.process_deaths()
    # The Taunt minion was drawn and discounted by 2.
    assert taunt.zone == Zone.HAND
    assert taunt.cost == max(0, base_cost - 2)
    assert any(b.id == "VAC_518e" for b in taunt.buffs)


def test_tortollan_traveler_only_draws_taunt():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    # Deck holds only a NON-taunt minion -> the taunt-restricted draw misses it.
    nontaunt = p1.card(WISP)  # not a Taunt
    nontaunt.zone = Zone.DECK
    traveler = p1.summon("VAC_518")
    traveler.destroy()
    game.process_deaths()
    assert nontaunt.zone == Zone.DECK


# VAC_519 — Mistah Vistah (5/5/5): Mage Tourist. Battlecry: In 3 turns, replay
# every spell you've cast between now and then.
def test_mistah_vistah_replays_spells_after_three_turns():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p2 = [p for p in game.players if p is not p1][0]
    p1.cant_fatigue = True
    p2.cant_fatigue = True
    vistah = p1.give("VAC_519")
    vistah.play()
    # Cast a target-free spell (Claw -> +2 Armor) so the replay's effect is
    # unambiguous and deterministic (no random target). Armor persists.
    claw = p1.give("CS2_005")
    claw.play()
    assert p1.hero.armor == 2
    # Timer started at 3; it decrements on each of the controller's turn-ends.
    # After 3 of the controller's turn-ends the recorded spell replays. Run 6
    # half-turns (3 full rounds) so the 3rd controller turn-end fires.
    for _ in range(6):
        game.end_turn()
    # The replayed Claw grants another +2 Armor -> 4 total.
    assert p1.hero.armor == 4


# VAC_950 — Bouldering Buddy (7/6/7 Elemental): Rush, Taunt. Costs (1) if you
# have at least 10 Mana Crystals.
def test_bouldering_buddy_keywords_and_cost():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    buddy = p1.give("VAC_950")
    # prepare_game sets max_mana = 10 -> costs 1.
    assert p1.max_mana == 10
    assert buddy.cost == 1
    m = p1.summon("VAC_950")
    assert m.rush
    assert m.taunt
    assert Race.ELEMENTAL in m.races


def test_bouldering_buddy_full_cost_below_ten_mana():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    p1.max_mana = 9
    buddy = p1.give("VAC_950")
    # Base cost is 7 when below 10 Mana Crystals.
    assert buddy.cost == 7


# VAC_508 — Trail Mix: Gain 2 Mana Crystals next turn only.
def test_trail_mix_grants_two_mana_next_turn_only():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.max_mana = 5
    spell = p1.give("VAC_508")
    spell.play()
    # No immediate temporary mana this turn (it's "next turn only").
    assert p1.temp_mana == 0
    # Advance to p1's next turn: at turn begin it grants 2 temporary mana.
    game.end_turn()
    game.end_turn()
    assert p1.temp_mana == 2


def test_trail_mix_expires_after_one_turn():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.max_mana = 5
    spell = p1.give("VAC_508")
    spell.play()
    game.end_turn()
    game.end_turn()  # next p1 turn: +2 temp mana, then enchant destroyed
    assert p1.temp_mana == 2
    # The following p1 turn must NOT grant the bonus again.
    game.end_turn()
    game.end_turn()
    assert p1.temp_mana == 0


# VAC_907 — Sleep Under the Stars: Choose Thrice — Draw 2 cards; Gain 5 Armor;
# Refresh 3 Mana Crystals.
def test_sleep_under_the_stars_all_three_effects():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    # Seed deck with 2 cards so Draw 2 is deterministic and observable.
    for _ in range(2):
        c = p1.card(WISP)
        c.zone = Zone.DECK
    p1.max_mana = 10
    p1.used_mana = 0
    p1.hero.armor = 0
    spell = p1.give("VAC_907")  # costs 7
    assert spell.cost == 7
    spell.play()
    # Draw 2 cards.
    assert len([c for c in p1.hand if c.id == WISP]) == 2
    # Gain 5 Armor.
    assert p1.hero.armor == 5
    # Refresh 3 Mana Crystals: paying 7 leaves 3 available (10 - 7), and the
    # refresh restores 3 more, so 6 mana is available this turn.
    assert p1.mana == 6


# VAC_948 — Hydration Station: Resurrect your 3 highest Cost Taunt minions.
def test_hydration_station_resurrects_three_highest_cost_taunts():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    # Kill four Taunt minions of distinct cost plus one non-taunt. Only the
    # THREE highest-cost Taunts (3, 5, 8) should be resurrected; the cheapest
    # Taunt (1) and the non-taunt Wisp must be excluded.
    cheap = p1.summon(GOLDSHIRE_FOOTMAN)  # 1-cost Taunt (excluded — lowest)
    low = p1.summon("EX1_390")  # Tauren Warrior, 3-cost Taunt
    mid = p1.summon("CS2_187")  # Booty Bay Bodyguard, 5-cost Taunt
    big = p1.summon("NEW1_010")  # Al'Akir the Windlord, 8-cost Taunt
    nontaunt = p1.summon(WISP)  # not a Taunt — excluded
    for m in (cheap, low, mid, big, nontaunt):
        m.destroy()
    game.process_deaths()
    assert len(p1.field) == 0
    spell = p1.give("VAC_948")
    spell.play()
    summoned = list(p1.field)
    assert len(summoned) == 3
    res_ids = sorted(m.id for m in summoned)
    assert res_ids == sorted(["EX1_390", "CS2_187", "NEW1_010"])
    assert all(bool(m.tags.get(GameTag.TAUNT)) for m in summoned)


# VAC_949 — New Heights: Increase your maximum Mana by 3 and gain an empty Mana
# Crystal.
def test_new_heights_increases_max_mana_by_three_plus_empty_crystal():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    p1.max_mana = 6
    p1.used_mana = 0
    pre_max = p1.max_mana
    spell = p1.give("VAC_949")  # costs 3
    assert spell.cost == 3
    spell.play()
    # +3 from GainMana and +1 empty crystal = +4 max mana total.
    assert p1.max_mana == pre_max + 4
    # Net available mana: started 6, paid 3 for the spell, GainMana(3) refreshed
    # those 3 crystals (the empty crystal adds max but no available mana). So
    # available = 6 - 3 (spell) + 3 (refresh) = 6.
    assert p1.mana == 6


# VAC_517 — Hiking Trail (Location, 3 dur): Discover a Taunt minion. After you
# gain Armor, reopen this.
def test_hiking_trail_discovers_taunt_minion():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    loc = p1.give("VAC_517")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    pre_hand = len(p1.hand)
    loc.use()
    assert p1.choice is not None
    for cid in p1.choice.cards:
        cdata = _cards.db[cid]
        assert cdata.type == CardType.MINION
        assert bool(cdata.tags.get(GameTag.TAUNT))
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    assert any(c.id == chosen for c in p1.hand)
    # After a use the location goes on cooldown (2).
    assert loc.cooldown == 2


def test_hiking_trail_reopens_after_gaining_armor():
    game = prepare_empty_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.current_player
    loc = p1.give("VAC_517")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert loc.cooldown == 2
    # "After you gain Armor, reopen this." -> gaining Armor sets cooldown back
    # to 0 so the location is usable again immediately.
    armor = p1.give("VAC_907")  # Sleep Under the Stars gains 5 Armor
    armor.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert p1.hero.armor == 5
    assert loc.cooldown == 0
