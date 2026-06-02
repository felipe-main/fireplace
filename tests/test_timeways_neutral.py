"""Across the Timeways — Neutral.

One tight test per collectible (and per effect-bearing token). Random effects
are pinned by controlling deck contents / beefing up HP so assertions land
exactly. Rewind cards are tested for both the base effect and the engine's
Rewind re-run (choose the TIME_000tb token).
"""
from utils import *
from hearthstone.enums import GameTag, Race, Rarity


def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


def _clear_deck(player):
    for card in list(player.deck):
        card.discard()


def _deck_card(player, cid):
    return player.card(cid, zone=Zone.DECK)


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _rewind(player):
    """Pick the Rewind-Timeline token (TIME_000tb) from the engine's offer."""
    rewind = next(c for c in player.choice.cards if c.id == "TIME_000tb")
    player.choice.choose(rewind)


def _keep(player):
    keep = next(c for c in player.choice.cards if c.id == "TIME_000ta")
    player.choice.choose(keep)


# ---------------------------------------------------------------------------
# TIME_002 Aeon Wizard — Rewind Battlecry: Get 2 random spells from your class.
# ---------------------------------------------------------------------------


def test_aeon_wizard_gets_two_class_spells():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("TIME_002").play()
    # Rewind offer is pending; keep the timeline to lock the base result.
    _keep(p1)
    assert p1.choice is None
    assert len(p1.hand) == 2
    for c in p1.hand:
        assert c.type == CardType.SPELL
        assert CardClass.MAGE in c.classes


def test_aeon_wizard_rewind_gets_two_more():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)
    p1.give("TIME_002").play()
    # The minion is now in play; hand holds 2 spells. Rewind adds 2 more.
    _rewind(p1)
    assert p1.choice is None
    assert len(p1.hand) == 4


# ---------------------------------------------------------------------------
# TIME_003 Portal Vanguard — Rewind Battlecry: Draw a random minion. Give +2/+2.
# ---------------------------------------------------------------------------


def test_portal_vanguard_draws_and_buffs_minion():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    _clear_deck(p1)
    wisp = _deck_card(p1, WISP)  # 1/1 vanilla minion
    p1.give("TIME_003").play()
    _keep(p1)  # resolve the Rewind offer
    assert wisp.zone == Zone.HAND
    assert wisp.atk == 3 and wisp.health == 3


# ---------------------------------------------------------------------------
# TIME_004 Conflux Crasher — Rewind Battlecry: Deal 7 to a random enemy.
# ---------------------------------------------------------------------------


def test_conflux_crasher_base_and_rewind():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    p1.give("TIME_004").play()
    assert p2.hero.health == 23
    _rewind(p1)
    assert p2.hero.health == 16


# ---------------------------------------------------------------------------
# TIME_024 Murozond, Unbounded — start of next turn, Attack -> INFINITY.
# ---------------------------------------------------------------------------


def test_murozond_attack_set_to_infinity_next_turn():
    game = prepare_game()
    p1 = game.player1
    muro = p1.give("TIME_024").play()
    assert muro.atk == 8
    game.end_turn()
    game.end_turn()  # back to p1: start of next turn fires
    assert muro.atk == 2147483647


# ---------------------------------------------------------------------------
# TIME_035 Time Machine — Deathrattle: Get a random Rewind card.
# ---------------------------------------------------------------------------


def test_time_machine_deathrattle_gets_rewind_card():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    tm = p1.summon("TIME_035")
    tm.destroy()
    assert len(p1.hand) == 1
    assert p1.hand[0].data.tags.get(GameTag.REWIND, 0)


# ---------------------------------------------------------------------------
# TIME_038 Mister Clocksworth — Battlecry: Summon 2 random Legendary minions.
# ---------------------------------------------------------------------------


def test_clocksworth_summons_two_legendaries():
    game = prepare_game()
    p1 = game.player1
    clock = p1.give("TIME_038").play()
    _keep(p1)
    summoned = [m for m in p1.field if m is not clock]
    assert len(summoned) == 2
    for m in summoned:
        assert m.rarity == Rarity.LEGENDARY


def test_clocksworth_token_t3_no_rewind():
    game = prepare_game()
    p1 = game.player1
    clock = p1.give("TIME_038t3").play()
    # t3 has no Rewind tag, so no choice is offered.
    assert p1.choice is None
    legos = [m for m in p1.field if m is not clock and m.rarity == Rarity.LEGENDARY]
    assert len(legos) == 2


# ---------------------------------------------------------------------------
# TIME_040 Fading Memory — Deathrattle: Get a random 5-Cost minion.
# ---------------------------------------------------------------------------


def test_fading_memory_gets_5cost_minion():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    fm = p1.summon("TIME_040")
    fm.destroy()
    assert len(p1.hand) == 1
    got = p1.hand[0]
    assert got.type == CardType.MINION and got.data.cost == 5


# ---------------------------------------------------------------------------
# TIME_041 Futuristic Forefather — guess the opponent's hand card for +4 Health.
# ---------------------------------------------------------------------------


def test_forefather_correct_guess_buffs_health():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p2)
    # Opponent holds exactly one card, so the "correct" choice is unique.
    p2.give(WISP)
    ff = p1.give("TIME_041").play()
    # Pick the card matching the opponent's only hand card.
    correct = next((c for c in p1.choice.cards if c.id == WISP), None)
    assert correct is not None
    p1.choice.choose(correct)
    assert ff.health == 8  # 4 base + 4


def test_forefather_wrong_guess_no_buff():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p2)
    p2.give(WISP)
    ff = p1.give("TIME_041").play()
    wrong = next((c for c in p1.choice.cards if c.id != WISP), None)
    assert wrong is not None
    p1.choice.choose(wrong)
    assert ff.health == 4


# ---------------------------------------------------------------------------
# TIME_045 Whelp of the Infinite — Poisonous Reborn (vanilla keywords).
# ---------------------------------------------------------------------------


def test_whelp_of_the_infinite_keywords():
    game = prepare_game()
    whelp = game.player1.summon("TIME_045")
    assert whelp.poisonous and whelp.reborn


# ---------------------------------------------------------------------------
# TIME_046 Cyborg Patriarch — Dormant for 3 turns, Taunt.
# ---------------------------------------------------------------------------


def test_cyborg_patriarch_dormant_three_turns():
    game = prepare_game()
    p1 = game.player1
    cyborg = p1.give("TIME_046").play()
    assert cyborg.dormant
    for _ in range(2):
        game.end_turn(); game.end_turn()
        assert cyborg.dormant
    game.end_turn(); game.end_turn()
    assert not cyborg.dormant
    assert cyborg.taunt


# ---------------------------------------------------------------------------
# TIME_047 Devious Coyote — costs (1) less per enemy-hero damage this turn.
# ---------------------------------------------------------------------------


def test_devious_coyote_cost_reduction():
    # Coyote reduces cost by 1 per *distinct* enemy-hero damage EVENT this
    # turn — not per damage point. Two separate hits of differing size (1 then
    # 5) are two events => cost - 2 (NOT - 6).
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    coyote = p1.give("TIME_047")  # base cost 5
    base = coyote.data.cost
    assert coyote.cost == base
    assert coyote.stealthed
    # p2 is Coyote's controller's opponent => p2.hero is the "enemy hero".
    game.queue_actions(p1.hero, [Hit(p2.hero, 1)])
    game.queue_actions(p1.hero, [Hit(p2.hero, 5)])
    assert p2.times_hero_damaged_this_turn == 2
    # Exactly base - 2 (two events), NOT base - 6 (the summed damage points).
    assert coyote.cost == base - 2


def test_devious_coyote_single_big_hit_is_one_event():
    # A single large hit is ONE event => cost reduced by exactly 1.
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    coyote = p1.give("TIME_047")
    base = coyote.data.cost
    game.queue_actions(p1.hero, [Hit(p2.hero, 5)])
    assert p2.times_hero_damaged_this_turn == 1
    assert coyote.cost == base - 1


def test_devious_coyote_event_count_resets_across_turns():
    # The damage-event count is a per-turn counter, reset at each turn start,
    # so Coyote's discount does not persist into a later turn.
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    coyote = p1.give("TIME_047")
    base = coyote.data.cost
    game.queue_actions(p1.hero, [Hit(p2.hero, 2)])
    assert coyote.cost == base - 1
    game.end_turn(); game.end_turn()  # back to p1; counters reset both sides
    assert p2.times_hero_damaged_this_turn == 0
    assert coyote.cost == base


# ---------------------------------------------------------------------------
# TIME_048 Clockwork Rager — +1 Health per turn taken this game.
# ---------------------------------------------------------------------------


def test_clockwork_rager_health_per_turn():
    game = prepare_game()
    p1 = game.player1
    turns = len(p1.turns)
    assert turns >= 1
    rager = p1.give("TIME_048").play()
    assert rager.health == 1 + turns


# ---------------------------------------------------------------------------
# TIME_049 Dangerous Variant — start of turn, transform into a 5-Cost minion.
# ---------------------------------------------------------------------------


def test_dangerous_variant_transforms_start_of_turn():
    game = prepare_game()
    p1 = game.player1
    variant = p1.summon("TIME_049")
    game.end_turn(); game.end_turn()
    minion = p1.field[0]
    assert minion.id != "TIME_049"
    assert minion.data.cost == 5


# ---------------------------------------------------------------------------
# TIME_050 Sentient Hourglass — Rush; after surviving damage, swap stats.
# ---------------------------------------------------------------------------


def test_sentient_hourglass_swaps_stats_on_survive():
    game = prepare_game()
    p1 = game.player1
    glass = p1.summon("TIME_050")  # 4/9
    assert glass.atk == 4 and glass.health == 9
    game.queue_actions(p1.hero, [Hit(glass, 2)])
    # Survived at 4/7; swap sets atk=current health (7), health=atk (4),
    # clearing damage. Result: 7/4.
    assert glass.atk == 7 and glass.health == 4
    assert glass.rush


# ---------------------------------------------------------------------------
# TIME_051 Soldier of the Infinite — Rush Battlecry: Double Attack.
# ---------------------------------------------------------------------------


def test_soldier_of_the_infinite_doubles_attack():
    game = prepare_game()
    soldier = game.player1.give("TIME_051").play()  # 3/5 -> double atk = 6/5
    assert soldier.atk == 6 and soldier.health == 5
    assert soldier.rush


# ---------------------------------------------------------------------------
# TIME_052 Amber Warden — Taunt Deathrattle: Summon a random minion.
# ---------------------------------------------------------------------------


def test_amber_warden_deathrattle_summons():
    game = prepare_game()
    p1 = game.player1
    warden = p1.summon("TIME_052")
    assert warden.taunt
    warden.destroy()
    field = [m for m in p1.field]
    assert len(field) == 1
    assert field[0].type == CardType.MINION


# ---------------------------------------------------------------------------
# TIME_053 Sandmaw — vanilla.
# ---------------------------------------------------------------------------


def test_sandmaw_vanilla_stats():
    game = prepare_game()
    sandmaw = game.player1.summon("TIME_053")
    assert sandmaw.atk == 7 and sandmaw.health == 2
    assert Race.ELEMENTAL in sandmaw.races and Race.BEAST in sandmaw.races


# ---------------------------------------------------------------------------
# TIME_054 Time Skipper — end of each player's turn, give that player a Coin.
# ---------------------------------------------------------------------------


def test_time_skipper_gives_coin_each_turn_end():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    p1.summon("TIME_054")
    game.end_turn()  # end of p1's turn -> p1 gets a Coin
    coins = [c for c in p1.hand if c.id == THE_COIN]
    assert len(coins) == 1


# ---------------------------------------------------------------------------
# TIME_055 Unknown Voyager — after surviving damage, transform into a 7-Cost.
# ---------------------------------------------------------------------------


def test_unknown_voyager_transforms_on_survive():
    game = prepare_game()
    p1 = game.player1
    voyager = p1.summon("TIME_055")  # 4/5
    game.queue_actions(p1.hero, [Hit(voyager, 2)])
    minion = p1.field[0]
    assert minion.id != "TIME_055"
    assert minion.data.cost == 7


# ---------------------------------------------------------------------------
# TIME_056 Whelp of the Bronze — Lifesteal Divine Shield (vanilla keywords).
# ---------------------------------------------------------------------------


def test_whelp_of_the_bronze_keywords():
    game = prepare_game()
    whelp = game.player1.summon("TIME_056")
    assert whelp.lifesteal and whelp.divine_shield


# ---------------------------------------------------------------------------
# TIME_057 Wizened Truthseeker — reset every card in both hands to printed Cost.
# ---------------------------------------------------------------------------


def test_wizened_truthseeker_resets_costs():
    # Common case: ordinary additive cost buffs/debuffs on cards in BOTH hands
    # are all reverted to the printed (data) Cost, exactly.
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _clear_hand(p2)
    cheap = p1.give(FIREBALL)  # printed cost 4
    game.queue_actions(p1.hero, [Buff(cheap, "TIME_057e", cost=-3)])
    assert cheap.cost == 1
    # A debuff (cost increase) on an opponent's card, too.
    pricey = p2.give(WISP)  # printed cost 0
    game.queue_actions(p2.hero, [Buff(pricey, "TIME_057e", cost=4)])
    assert pricey.cost == 4
    p1.give("TIME_057").play()
    assert cheap.cost == cheap.data.cost == 4
    assert pricey.cost == pricey.data.cost == 0


def test_wizened_truthseeker_reverses_set_to_zero():
    # Edge case: a persistent set-to-(0) enchantment (GameTag.COST: -100) cannot
    # be undone by an additive delta (engine clamps at 0). The card-only reset
    # strips the pure cost-only enchant so the printed Cost is restored exactly.
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    fireball = p1.give(FIREBALL)  # printed cost 4
    # Pure cost-only enchant setting cost to 0 (delta -100, clamped at 0).
    game.queue_actions(p1.hero, [Buff(fireball, "TIME_057e", cost=-100)])
    assert fireball.cost == 0  # clamped set-to-0
    p1.give("TIME_057").play()
    assert fireball.cost == fireball.data.cost == 4


def test_wizened_truthseeker_preserves_stat_buffs():
    # The reset touches only Cost. A pure stat buff (no cost delta) is left
    # untouched, and a MIXED buff carrying both +stats and a cost delta keeps
    # its stats while the cost lands back on the printed base via the additive
    # correction stage (the mixed buff is NOT stripped).
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    yeti = p1.give("CS2_182")  # 4-cost 4/5 Chillwind Yeti
    base = yeti.data.cost
    # Pure stat buff (survives).
    game.queue_actions(p1.hero, [Buff(yeti, "TIME_003e")])  # +2/+2
    # Mixed buff: +1 atk AND -2 cost (must survive its stats, lose its cost).
    game.queue_actions(p1.hero, [Buff(yeti, "TIME_054e", cost=-2)])  # +1/+1 -2cost
    assert yeti.cost == base - 2
    pre_atk, pre_health = yeti.atk, yeti.health  # 4+2+1=7 / 5+2+1=8
    assert pre_atk == 7 and pre_health == 8
    p1.give("TIME_057").play()
    assert yeti.cost == yeti.data.cost == base
    # Stats from both buffs preserved.
    assert yeti.atk == pre_atk and yeti.health == pre_health


# ---------------------------------------------------------------------------
# TIME_058 Paltry Flutterwing — Deathrattle: random 2-Cost minion, Dormant 2.
# ---------------------------------------------------------------------------


def test_paltry_flutterwing_summons_dormant_2cost():
    game = prepare_game()
    p1 = game.player1
    flutter = p1.summon("TIME_058")
    flutter.destroy()
    summoned = [m for m in p1.field]
    assert len(summoned) == 1
    assert summoned[0].data.cost == 2
    assert summoned[0].dormant


# ---------------------------------------------------------------------------
# TIME_059 Living Paradox — Battlecry: Summon two 2/1 Living Paradoxes.
# ---------------------------------------------------------------------------


def test_living_paradox_summons_two_copies():
    game = prepare_game()
    p1 = game.player1
    paradox = p1.give("TIME_059").play()
    paradoxes = [m for m in p1.field if m.id == "TIME_059"]
    # Original + two summoned tokens (which do not re-trigger battlecry).
    assert len(paradoxes) == 3
    for m in paradoxes:
        assert m.atk == 2 and m.health == 1


# ---------------------------------------------------------------------------
# TIME_060 Quantum Destabilizer — takes double damage.
# ---------------------------------------------------------------------------


def test_quantum_destabilizer_double_damage():
    game = prepare_game()
    p1 = game.player1
    quantum = p1.summon("TIME_060")  # 4/9
    game.queue_actions(p1.hero, [Hit(quantum, 3)])
    assert quantum.damage == 6  # 3 doubled


# ---------------------------------------------------------------------------
# TIME_061 Timeless Causality — Battlecry: Reverse the order of your deck.
# ---------------------------------------------------------------------------


def test_timeless_causality_reverses_deck():
    game = prepare_game()
    p1 = game.player1
    _clear_deck(p1)
    top = _deck_card(p1, WISP)       # placed first
    bottom = _deck_card(p1, MOONFIRE)  # placed last (true top, deck[-1])
    before = list(p1.deck)
    p1.give("TIME_061").play()
    assert list(p1.deck) == before[::-1]


# ---------------------------------------------------------------------------
# TIME_062 Chronicle Keeper — Battlecry: holding a Dragon -> Taunt + Div Shield.
# ---------------------------------------------------------------------------


def test_chronicle_keeper_with_dragon():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    p1.give("TIME_045")  # Whelp of the Infinite is a Dragon
    keeper = p1.give("TIME_062").play()
    assert keeper.taunt and keeper.divine_shield


def test_chronicle_keeper_without_dragon():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    keeper = p1.give("TIME_062").play()
    assert not keeper.taunt and not keeper.divine_shield


# ---------------------------------------------------------------------------
# TIME_063 Timelord Nozdormu — Dormant 5; playing a TIME_ card awakens 1 sooner.
# ---------------------------------------------------------------------------


def test_nozdormu_hastens_on_newest_expansion_play():
    game = prepare_game()
    p1 = game.player1
    noz = p1.give("TIME_063").play()
    assert noz.dormant and noz.dormant_turns == 5
    # Playing a TIME_ card shaves a turn off the dormant timer.
    p1.give("TIME_053").play()  # Sandmaw, a TIME_ minion
    assert noz.dormant_turns == 4


# ---------------------------------------------------------------------------
# TIME_064 Chrono-Lord Deios — Battlecries/Deathrattles trigger twice.
# ---------------------------------------------------------------------------


def test_chrono_lord_doubles_battlecry():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    p1.summon("TIME_064")
    # Conflux Crasher's battlecry (7 to a random enemy) now fires twice.
    p1.give("TIME_004").play()
    _keep(p1)  # resolve the Rewind offer (keep the timeline)
    # Two battlecries: 7 + 7 = 14 to the hero (only enemy character).
    assert p2.hero.health == 16


def test_chrono_lord_doubles_deathrattle():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    p1.summon("TIME_064")
    fm = p1.summon("TIME_040")  # Deathrattle: get a 5-Cost minion
    fm.destroy()
    assert len(p1.hand) == 2  # doubled


# ---------------------------------------------------------------------------
# TIME_100 Hourglass Attendant — end of turn, give hand minions +1/+1.
# ---------------------------------------------------------------------------


def test_hourglass_attendant_buffs_hand_minions():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    wisp = p1.give(WISP)
    p1.summon("TIME_100")
    game.end_turn()  # end of p1's turn
    assert wisp.atk == 2 and wisp.health == 2


# ---------------------------------------------------------------------------
# TIME_101 Misplaced Pyromancer — vanilla body (Shatter has no engine event).
# ---------------------------------------------------------------------------


def test_misplaced_pyromancer_stats():
    game = prepare_game()
    pyro = game.player1.summon("TIME_101")
    assert pyro.atk == 4 and pyro.health == 3


# ---------------------------------------------------------------------------
# TIME_102 Circadiamancer — add an 8-Cost minion; cost drops 1 each turn.
# ---------------------------------------------------------------------------


def test_circadiamancer_adds_discounting_minion():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    p1.give("TIME_102").play()
    added = p1.hand[0]
    assert added.type == CardType.MINION and added.data.cost == 8
    assert added.cost == 8
    game.end_turn(); game.end_turn()  # start of p1's next turn
    assert added.cost == 7
    game.end_turn(); game.end_turn()
    assert added.cost == 6


# ---------------------------------------------------------------------------
# TIME_103 Chromie — Deathrattle: draw copies of cards played this game.
# ---------------------------------------------------------------------------


def test_chromie_draws_copies_of_played_cards():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    _clear_deck(p1)
    # Play two cheap cards so cards_played_this_game has exactly 2 entries.
    p1.give(WISP).play()
    p1.give(MOONFIRE).play(p1.hero)
    played_ids = sorted(c.id for c in p1.cards_played_this_game)
    chromie = p1.summon("TIME_103")
    _clear_hand(p1)
    chromie.destroy()
    drawn = sorted(c.id for c in p1.hand)
    assert drawn == played_ids


# ---------------------------------------------------------------------------
# TIME_428 Yesterloc — end of turn, give your OTHER minions +1 Health.
# ---------------------------------------------------------------------------


def test_yesterloc_buffs_other_minions_health():
    game = prepare_game()
    p1 = game.player1
    yester = p1.summon("TIME_428")  # 3/1
    other = p1.summon(WISP)  # 1/1
    game.end_turn()
    assert other.health == 2
    assert yester.health == 1  # unchanged (only OTHER minions get +1 Health)


# ---------------------------------------------------------------------------
# TIME_434 Temporal Traveler — Deathrattle: 4/1 Shadow attacks a random enemy.
# ---------------------------------------------------------------------------


def test_temporal_traveler_summons_attacking_shadow():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    # 0-Attack taunt (Target Dummy) so the 4/1 Shadow survives the exchange.
    enemy = p2.summon(TARGET_DUMMY)  # 0/2
    enemy.max_health = 80
    enemy.damage = 0
    traveler = p1.summon("TIME_434")
    traveler.destroy()
    shadow = [m for m in p1.field if m.id == "TIME_434t"]
    assert len(shadow) == 1
    # The 4/1 Shadow attacked the only enemy minion for 4.
    assert enemy.damage == 4


# ---------------------------------------------------------------------------
# TIME_720 Soldier of the Bronze — Taunt Battlecry: Double Health.
# ---------------------------------------------------------------------------


def test_soldier_of_the_bronze_doubles_health():
    game = prepare_game()
    soldier = game.player1.give("TIME_720").play()
    assert soldier.health == 6 and soldier.atk == 5
    assert soldier.taunt


# ===========================================================================
# END_ — Across the Timeways End Time mini-set (neutral / dual-class)
# ===========================================================================


def test_jagged_edge_of_time_imbues_hero_power():
    # Rogue gets a real Imbued Hero Power token (END_000p); the counter bumps.
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    before = p1.imbues_this_game
    game.end_turn(); game.end_turn()
    p1.give("END_001").play()
    assert p1.imbues_this_game == before + 1
    assert p1.hero.power.id == "END_000p"


def test_wicked_blightspawn_equips_dagger_when_unarmed():
    game = prepare_game()
    p1 = game.player1
    assert p1.weapon is None
    bs = p1.summon("END_002")
    bs.destroy()
    # Reborn re-summons a copy; the original's deathrattle equips a 1/2 Dagger.
    assert p1.weapon is not None
    assert p1.weapon.id == "CS2_082"
    assert p1.weapon.atk == 1


def test_wicked_blightspawn_buffs_existing_weapon():
    game = prepare_game()
    p1 = game.player1
    p1.give("CS2_082").play()  # equip a 1/2 Wicked Knife first
    base_atk = p1.weapon.atk
    bs = p1.summon("END_002")
    bs.destroy()
    # Weapon already equipped -> +2 Attack instead of a new dagger.
    assert p1.weapon.atk == base_atk + 2


def test_remnant_of_rage_cost_drops_per_death_and_draws():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    remnant = p1.give("END_004")
    assert remnant.cost == 7
    # Kill two of our own minions this turn.
    for _ in range(2):
        m = p1.summon("CS2_182")  # 4/5 Boulderfist
        m.destroy()
    assert p1.minions_killed_this_turn == 2
    assert remnant.cost == 5
    pre_hand = len(p1.hand)
    remnant.play()
    # Battlecry drew 2; the Remnant itself left hand (net +1).
    assert len(p1.hand) == pre_hand - 1 + 2


def _middle_bygone(p1):
    """Give Bygone Echoes flanked by other cards so Outcast does NOT trigger."""
    _clear_hand(p1)
    p1.give("CS2_171")
    card = p1.give("END_005")
    p1.give("CS2_171")
    return card


def test_bygone_echoes_summons_one_without_corpses():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 0
    card = _middle_bygone(p1)
    pre = len(p1.field)
    card.play()
    _resolve_choices(p1)
    assert len(p1.field) == pre + 1


def test_bygone_echoes_spends_corpses_for_second():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 4
    card = _middle_bygone(p1)
    pre = len(p1.field)
    card.play()
    _resolve_choices(p1)
    # Base summon + a second from spending 4 Corpses.
    assert len(p1.field) == pre + 2
    assert p1.corpses == 0


def test_bygone_echoes_outcast_adds_another():
    game = prepare_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.corpses = 0
    _clear_hand(p1)
    card = p1.give("END_005")  # leftmost+rightmost -> Outcast active
    pre = len(p1.field)
    card.play()
    _resolve_choices(p1)
    # Base + Outcast's extra (no corpses spent).
    assert len(p1.field) == pre + 2


def test_press_the_advantage():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # 4/5
    target.max_health = 80
    target.damage = 0
    _clear_hand(p1)
    p1.give("END_007").play(target=target)
    assert target.damage == 1
    assert p1.hero.atk == 1
    assert p1.hero.armor == 1
    # Drew exactly 1 card.
    assert len(p1.hand) == 1


def test_enduring_roach_refreshes_mana_on_hero_power():
    game = prepare_game()
    p1 = game.player1
    p1.summon("END_008")
    p1.used_mana = 5
    p1.hero.power.use()
    # Hero power cost 2 + then refresh 2 crystals.
    assert p1.used_mana == 5


def test_twilight_timereaver_sets_attack_to_one():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    big = p2.summon("CS2_182")  # 4/5
    mine = p1.summon("CS2_182")  # 4/5
    reaver = p1.give("END_010")
    reaver.play(choose="END_010a")
    assert big.atk == 1 and mine.atk == 1
    assert big.health == 5  # health untouched
    assert reaver.atk == 5  # "all OTHER minions"


def test_twilight_timereaver_sets_health_to_one():
    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1, p2 = game.player1, game.player2
    big = p2.summon("CS2_182")  # 4/5
    reaver = p1.give("END_010")
    reaver.play(choose="END_010b")
    assert big.health == 1
    assert big.atk == 4  # attack untouched
    assert reaver.health == 5


def test_acceleration_aura_gives_temp_mana_at_turn_start():
    game = prepare_game()
    p1 = game.player1
    p1.give("END_011").play()
    game.end_turn(); game.end_turn()
    # Start of our turn: +1 temporary mana crystal.
    assert p1.temp_mana == 1


def test_brutish_endmaw_discovers_one_cost_minion():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    p1.give("END_013").play()
    assert p1.choice is not None
    for c in p1.choice.cards:
        assert c.cost == 1 and c.type == CardType.MINION
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 1


def test_synchronized_spark_buffs_on_kill():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    victim = p2.summon("EX1_011")  # 1/3 Voodoo Doctor — dies to 3 damage
    friendly = p1.summon("CS2_182")  # 4/5, the only friendly minion
    pre_atk, pre_health = friendly.atk, friendly.health
    spark = p1.give("END_014")
    spark.play(target=victim)
    assert victim.dead
    assert friendly.atk == pre_atk + 3
    assert friendly.health == pre_health + 3


def test_synchronized_spark_no_buff_on_survive():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_182")  # 4/5 survives 3 damage
    friendly = p1.summon("CS2_182")
    pre_atk = friendly.atk
    p1.give("END_014").play(target=victim)
    assert not victim.dead
    assert friendly.atk == pre_atk


def test_chronoclaws_discards_highest_cost_on_attack():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    cheap = p1.give("CS2_171")   # 1-cost Stonetusk
    pricey = p1.give("CS2_182")  # 6-cost Boulderfist
    p1.give("END_016").play()    # equip 4/3 weapon
    p1.hero.attack(p2.hero)
    # Highest-cost card (Boulderfist) discarded; cheap one remains.
    assert pricey not in p1.hand
    assert cheap in p1.hand


def test_battle_at_end_time_quest_completes():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    quest = p1.give("END_017").play()
    # Fill the hand to max.
    while len(p1.hand) < p1.max_hand_size:
        p1.give("CS2_171")
    game.end_turn(); game.end_turn()  # turn end #1: progress to "filled"
    assert quest.progress == 1
    _clear_hand(p1)
    game.end_turn(); game.end_turn()  # turn end #2: emptied -> reward
    # Reward gives Tick and Tock.
    assert any(c.id == "END_017t" for c in p1.hand)


def test_tick_and_tock_fills_hand_and_empties_enemy():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    # Stock the deck so the battlecry has cards to draw to full.
    for _ in range(12):
        _deck_card(p1, "CS2_171")
    tnt = p1.give("END_017t")
    tnt.play()
    assert len(p1.hand) == p1.max_hand_size
    # Deathrattle empties opponent's hand.
    _clear_hand(p2)
    p2.give("CS2_171"); p2.give("CS2_171")
    assert len(p2.hand) == 2
    tnt.destroy()
    game.process_deaths()
    assert len(p2.hand) == 0


def test_endtime_survivor_buffs_when_hero_damaged():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    p1.hero.damaged_this_turn = 3  # hero took damage this turn
    p1.hero.damage = 3
    surv = p1.give("END_019").play()
    assert surv.atk == 8 and surv.health == 9  # 5/6 + 3/3
    assert surv.taunt


def test_endtime_survivor_no_buff_when_undamaged():
    game = prepare_game()
    p1 = game.player1
    surv = p1.give("END_019").play()
    assert surv.atk == 5 and surv.health == 6


def test_eternal_toil_draw_on_survive():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    survivor = p2.summon("CS2_182")  # 4/5 survives 1 damage
    p1.give("END_020").play(target=survivor)
    assert survivor.damage == 1
    assert not survivor.dead
    assert len(p1.hand) == 1


def test_eternal_toil_summon_on_kill():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    victim = p2.summon("CS2_171")  # 3/1, dies to 1 dmg
    pre = len(p1.field)
    p1.give("END_020").play(target=victim)
    assert victim.dead
    summoned = [m for m in p1.field]
    assert len(p1.field) == pre + 1
    assert summoned[-1].cost == 1


def test_time_twisted_seer_spell_damage_while_damaged():
    game = prepare_game()
    p1 = game.player1
    seer = p1.summon("END_022")  # 1/3
    assert seer.spellpower == 0
    seer.damage = 1
    game.refresh_auras()
    assert seer.spellpower == 2
    seer.damage = 0
    game.refresh_auras()
    assert seer.spellpower == 0


def test_bitter_end_freezes_and_destroys_damaged():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    left = p2.summon("CS2_182")    # 4/5
    center = p2.summon("CS2_182")  # 4/5
    right = p2.summon("CS2_182")   # 4/5
    center.damage = 1  # damaged -> destroyed
    p1.give("END_023").play(target=center)
    assert center.dead
    # Neighbors undamaged -> frozen but alive.
    assert not left.dead and not right.dead
    assert left.frozen and right.frozen


def test_eternal_firebolt_lifesteal_and_return_on_kill():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    p1.hero.damage = 5
    victim = p2.summon("CS2_171")  # 3/1, dies
    _clear_hand(p1)
    bolt = p1.give("END_025")
    bolt.play(target=victim)
    assert victim.dead
    # Lifesteal healed the hero by 3.
    assert p1.hero.damage == 2
    game.end_turn()
    # Returned to hand at end of turn.
    assert any(c.id == "END_025" for c in p1.hand)


def test_eternal_firebolt_no_return_on_survive():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    survivor = p2.summon("CS2_182")  # 4/5 survives
    _clear_hand(p1)
    p1.give("END_025").play(target=survivor)
    assert not survivor.dead
    game.end_turn()
    assert not any(c.id == "END_025" for c in p1.hand)


def test_fragment_of_nothing_draws_on_spell_to_minion():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("END_026")
    _clear_hand(p1)
    target = p2.summon("CS2_182")  # 4/5
    target.max_health = 80
    target.damage = 0
    p1.give("CS2_024").play(target=target)  # Frostbolt -> minion
    assert len(p1.hand) == 1


def test_for_all_time_destroys_low_attack():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    weak = p2.summon("CS2_171")    # 1/1
    strong = p2.summon("CS2_200")  # 6/7 (Boulderfist Ogre) — survives
    mine = p1.summon("CS2_171")    # 1/1, also affected
    p1.give("END_028").play()
    assert weak.dead and mine.dead
    assert not strong.dead


def test_voodoo_totem_gets_shadow_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.player1
    p1.summon("END_029")
    _clear_hand(p1)
    game.end_turn()
    got = [c for c in p1.hand]
    assert len(got) == 1
    assert got[0].type == CardType.SPELL
    assert got[0].data.spell_school == SpellSchool.SHADOW


def test_winged_aberration_combo_grants_immune_and_overload():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.give("CS2_171").play()  # set up combo
    aber = p1.give("END_032").play()
    assert aber.immune
    assert aber.windfury
    assert p1.overloaded == 2


def test_winged_aberration_no_combo_no_effect():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    aber = p1.give("END_032").play()  # first card this turn -> no combo
    assert not aber.immune
    assert p1.overloaded == 0


def test_prescient_slitherdrake_cost_reduction():
    game = prepare_game()
    p1 = game.player1
    drake = p1.give("END_033")
    assert drake.cost == 7
    p1.give("CS2_182")  # not a dragon
    assert drake.cost == 7
    p1.give("END_033")  # another Dragon in hand
    assert drake.cost == 4


def test_crumblecrusher_destroys_minion_and_weapon():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    enemy = p2.summon("CS2_182")  # 4/5
    p2.summon("CS2_082")          # enemy weapon equipped
    assert p2.weapon is not None
    p1.give("END_034").play()
    assert enemy.dead
    assert p2.weapon is None


def test_omen_of_the_end_mills_when_deck_empty():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_deck(p1)
    for _ in range(8):
        _deck_card(p2, "CS2_171")
    pre = len(p2.deck)
    p1.give("END_035").play()
    assert len(p2.deck) == pre - 5


def test_omen_of_the_end_no_mill_when_deck_nonempty():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _deck_card(p1, "CS2_171")  # deck not empty
    for _ in range(8):
        _deck_card(p2, "CS2_171")
    pre = len(p2.deck)
    p1.give("END_035").play()
    assert len(p2.deck) == pre


def test_morchie_discovers_rewind_card():
    game = prepare_game()
    p1 = game.player1
    _clear_hand(p1)
    p1.give("END_036").play()
    assert p1.choice is not None
    for c in p1.choice.cards:
        assert c.data.tags.get(GameTag.REWIND, 0)
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == 1
    # Marker enchant applied to hero.
    assert any(b.id == "END_036e" for b in p1.hero.buffs)


def test_endtime_murozond_fills_board_and_heals():
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    p1.hero.damage = 10
    muro = p1.give("END_037").play()
    # Board filled with dragons (plus Murozond himself).
    assert len(p1.field) == game.MAX_MINIONS_ON_FIELD
    dragons = [m for m in p1.field if Race.DRAGON in m.races and m is not muro]
    assert len(dragons) >= 1
    # Hero fully healed.
    assert p1.hero.damage == 0
