"""Across the Timeways — Warrior.

One tight test per collectible warrior card (plus the effect-bearing
Blood Fighter tokens). Assertions pin exact post-state; random effects are
made deterministic by controlling the board / deck.
"""
from utils import *
from hearthstone.enums import CardClass, Zone


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# TIME_034 Stadium Announcer
# Rewind Battlecry: Both players equip a random weapon. Give yours +1/+1.
# ---------------------------------------------------------------------------
def test_stadium_announcer_both_equip_and_buff():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    announcer = game.player1.give("TIME_034")
    announcer.play()
    # Engine offers the Rewind choice; keep the timeline (no re-run).
    assert game.player1.choice is not None
    keep = [c for c in game.player1.choice.cards if c.id == "TIME_000ta"][0]
    game.player1.choice.choose(keep)

    w1 = game.player1.weapon
    w2 = game.player2.weapon
    assert w1 is not None
    assert w2 is not None
    # Yours got +1/+1 from TIME_034e; the opponent's did not.
    assert any(b.id == "TIME_034e" for b in w1.buffs)
    assert not any(b.id == "TIME_034e" for b in w2.buffs)
    # The +1/+1 enchant raises both attack and durability by exactly 1 over
    # an unbuffed copy of the same weapon.
    ref = game.player1.card(w1.id)
    assert w1.atk == ref.atk + 1
    assert w1.durability == ref.durability + 1


def test_stadium_announcer_rewind_reequips():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    announcer = game.player1.give("TIME_034")
    announcer.play()
    rewind = [c for c in game.player1.choice.cards if c.id == "TIME_000tb"][0]
    game.player1.choice.choose(rewind)
    _resolve_choices(game.player1)
    # After the re-run both players still have a weapon and yours is buffed.
    assert game.player1.weapon is not None
    assert game.player2.weapon is not None
    assert any(b.id == "TIME_034e" for b in game.player1.weapon.buffs)


# ---------------------------------------------------------------------------
# TIME_714 Chrono-Lord Epoch
# Battlecry: Destroy all minions that your opponent played last turn.
# ---------------------------------------------------------------------------
def test_chrono_lord_epoch_destroys_last_turn_plays():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.end_turn()  # opponent's turn
    played = game.player2.give("CS2_182")  # Chillwind Yeti, played this turn
    played.play()
    game.end_turn()  # back to player1
    # A minion the opponent summoned (not "played") must survive.
    survivor = game.player2.summon("CS2_182")  # turn_played == -1
    epoch = game.player1.give("TIME_714")
    epoch.play()
    assert played.zone == Zone.GRAVEYARD
    assert survivor.zone == Zone.PLAY


# ---------------------------------------------------------------------------
# TIME_850 Lo'Gosh, Blood Fighter
# Deathrattle: Summon a Blood Fighter from your hand. It gains +5/+5 and
# attacks a random enemy.
# ---------------------------------------------------------------------------
def test_logosh_deathrattle_summons_buffs_and_attacks():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.discard_hand()
    logosh = game.player1.summon("TIME_850")  # 7/7 in play
    broll = game.player1.give("TIME_850t")  # Blood Fighter in hand
    # Only enemy character is the hero, so the attack lands deterministically.
    assert not game.player2.field
    pre_hp = game.player2.hero.health
    logosh.destroy()
    assert broll.zone == Zone.PLAY
    # 7/7 base + 5/5 = 12/12 (it attacked the hero, taking no return damage).
    assert broll.atk == 12
    assert broll.health == 12
    assert broll.damage == 0
    # Attacked the enemy hero for 12.
    assert game.player2.hero.health == pre_hp - 12


# ---------------------------------------------------------------------------
# TIME_850t Broll, Blood Fighter (token)
# Taunt. Deathrattle: Summon a Blood Fighter from your hand. Give it +5/+5
# and Taunt.
# ---------------------------------------------------------------------------
def test_broll_deathrattle_summons_buffs_and_taunts():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.discard_hand()
    broll = game.player1.summon("TIME_850t")  # 7/7 Taunt in play
    assert broll.taunt
    valeera = game.player1.give("TIME_850t1")  # another Blood Fighter in hand
    broll.destroy()
    assert valeera.zone == Zone.PLAY
    assert valeera.atk == 12
    assert valeera.health == 12
    assert valeera.taunt


# ---------------------------------------------------------------------------
# TIME_850t1 Valeera, Blood Fighter (token)
# Elusive. Deathrattle: Summon a Blood Fighter from your hand. Give it +5/+5
# and Elusive.
# ---------------------------------------------------------------------------
def test_valeera_deathrattle_summons_buffs_and_elusive():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.discard_hand()
    valeera = game.player1.summon("TIME_850t1")  # Elusive in play
    assert valeera.cant_be_targeted_by_abilities
    logosh = game.player1.give("TIME_850")  # Blood Fighter in hand
    valeera.destroy()
    assert logosh.zone == Zone.PLAY
    assert logosh.atk == 12
    assert logosh.health == 12
    assert logosh.cant_be_targeted_by_abilities


# ---------------------------------------------------------------------------
# TIME_871 Heir of Hereafter
# Taunt. Battlecry: Gain +2/+2 for each damaged minion.
# ---------------------------------------------------------------------------
def test_heir_of_hereafter_gains_per_damaged_minion():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    d1 = game.player1.summon("CS2_182")
    d1.damage = 1
    d2 = game.player2.summon("CS2_182")
    d2.damage = 2
    game.player2.summon("CS2_182")  # undamaged — does not count
    heir = game.player1.give("TIME_871")
    heir.play()
    # Base 2/6, +2/+2 for each of the 2 damaged minions = 6/10. (Heir
    # itself is undamaged at battlecry time so it does not count.)
    assert heir.atk == 6
    assert heir.health == 10
    assert heir.taunt


# ---------------------------------------------------------------------------
# TIME_872 Undefeated Champion
# Rush. Battlecry: Fill your opponent's board with random 1-Cost minions.
# ---------------------------------------------------------------------------
def test_undefeated_champion_fills_enemy_board():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    champ = game.player1.give("TIME_872")
    champ.play()
    assert len(game.player2.field) == 7
    assert all(m.cost == 1 for m in game.player2.field)
    assert champ.rush


# ---------------------------------------------------------------------------
# TIME_715 For Glory!
# Draw 2 cards. Costs (1) less for each minion your opponent controls.
# ---------------------------------------------------------------------------
def test_for_glory_cost_and_draw():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    for _ in range(3):
        game.player2.summon("CS2_182")
    glory = game.player1.give("TIME_715")
    # Base 5 - 3 enemy minions = 2.
    assert glory.cost == 2
    pre = len(game.player1.hand)
    glory.play()
    # Drew 2, played 1 = net +1.
    assert len(game.player1.hand) == pre + 1


# ---------------------------------------------------------------------------
# TIME_716 Slow Motion
# Your opponent's cards cost (1) more next turn.
# ---------------------------------------------------------------------------
def test_slow_motion_raises_opponent_cost_next_turn():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player2.discard_hand()
    opp_card = game.player2.give("CS2_182")  # base cost 4
    assert opp_card.cost == 4
    slow = game.player1.give("TIME_716")
    slow.play()
    # Aura active immediately on the opponent's hand.
    assert opp_card.cost == 5
    game.end_turn()  # opponent's (slowed) turn
    drawn = game.player2.give("CS2_029")  # base cost 4, drawn next turn
    assert opp_card.cost == 5
    assert drawn.cost == 5  # aura covers cards drawn during the slowed turn
    game.end_turn()  # opponent's turn ends -> aura clears at caster's begin
    assert opp_card.cost == 4
    assert drawn.cost == 4


# ---------------------------------------------------------------------------
# TIME_750 Precursory Strike
# Deal 3 damage. If you're holding a minion that costs (5) or more, draw a
# minion.
# ---------------------------------------------------------------------------
def test_precursory_strike_damage_and_conditional_draw():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    deck_minion = game.player1.give("CS2_186")  # War Golem
    deck_minion.zone = Zone.DECK
    game.player1.give("CS2_186")  # 7-cost minion held -> qualifies (>= 5)
    target = game.player2.summon("CS2_182")
    target.max_health = 10
    target.damage = 0
    strike = game.player1.give("TIME_750")
    strike.play(target=target)
    assert target.damage == 3
    # Held a 5+ minion -> drew the only deck minion.
    assert deck_minion.zone == Zone.HAND


def test_precursory_strike_no_draw_without_big_minion():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    game.player1.discard_hand()
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    deck_minion = game.player1.give("CS2_186")
    deck_minion.zone = Zone.DECK
    game.player1.give("CS2_182")  # 4-cost minion only -> does NOT qualify
    target = game.player2.summon("CS2_182")
    target.max_health = 10
    target.damage = 0
    strike = game.player1.give("TIME_750")
    strike.play(target=target)
    assert target.damage == 3
    assert deck_minion.zone == Zone.DECK  # no draw


# ---------------------------------------------------------------------------
# TIME_870 Gladiatorial Combat
# Summon a random minion from your deck. Summon a 5/5 Tiger with Stealth for
# your opponent.
# ---------------------------------------------------------------------------
def test_gladiatorial_combat_recruits_and_gives_tiger():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    for c in list(game.player1.deck):
        c.zone = Zone.SETASIDE
    deck_minion = game.player1.give("CS2_186")  # only minion in deck
    deck_minion.zone = Zone.DECK
    combat = game.player1.give("TIME_870")
    combat.play()
    assert deck_minion.zone == Zone.PLAY  # recruited from deck
    tigers = [m for m in game.player2.field if m.id == "TIME_870t"]
    assert len(tigers) == 1
    assert tigers[0].atk == 5
    assert tigers[0].health == 5
    assert tigers[0].stealthed


# ---------------------------------------------------------------------------
# TIME_873 Unleash the Crocolisks
# Gain 10 Armor. Summon two 2/3 Beasts for your opponent.
# ---------------------------------------------------------------------------
def test_unleash_the_crocolisks_armor_and_enemy_beasts():
    game = prepare_game(CardClass.WARRIOR, CardClass.WARRIOR)
    pre_armor = game.player1.hero.armor
    unleash = game.player1.give("TIME_873")
    unleash.play()
    assert game.player1.hero.armor == pre_armor + 10
    crocs = [m for m in game.player2.field if m.id == "TIME_873t"]
    assert len(crocs) == 2
    assert all(m.atk == 2 and m.health == 3 for m in crocs)
