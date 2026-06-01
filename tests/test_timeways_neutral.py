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
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    coyote = p1.give("TIME_047")
    assert coyote.cost == 5
    p2.hero.damage = 3  # enemy hero took 3 damage worth this turn
    p2.hero_damage_taken_this_turn = 3
    assert coyote.cost == 2
    assert coyote.stealthed


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
    game = prepare_game()
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _clear_hand(p2)
    cheap = p1.give(FIREBALL)  # printed cost 4
    cheap.buff_cost = 0
    game.queue_actions(p1.hero, [Buff(cheap, "TIME_057e", cost=-3)])
    assert cheap.cost == 1
    p1.give("TIME_057").play()
    assert cheap.cost == 4


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
