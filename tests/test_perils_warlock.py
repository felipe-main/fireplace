"""Perils in Paradise — WARLOCK collectible card tests.

Covers all 10 collectible Warlock cards:
  VAC_503 Summoner Darkmarrow, VAC_939 Eat! The! Imp!, VAC_940 Party Fiend,
  VAC_941 Announce Darkness, VAC_942 Fearless Flamejuggler,
  VAC_943 Sacrificial Imp, VAC_944 Cursed Souvenir, VAC_945 Party Planner Vona,
  VAC_951 "Health" Drink, VAC_952 Felfire Bonfire.
"""

from utils import *

from hearthstone.enums import CardClass, CardType


# ---------------------------------------------------------------------------
# VAC_503 — Summoner Darkmarrow: Death Knight Tourist. Your Deathrattles
# trigger twice. After you play a Deathrattle minion, destroy it.
# ---------------------------------------------------------------------------
def test_summoner_darkmarrow_doubles_deathrattles():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.summon("VAC_503")
    # Loot Hoarder: Deathrattle: Draw a card. With doubled deathrattles it
    # should draw exactly 2.
    hoarder = p1.summon("EX1_096")
    pre_hand = len(p1.hand)
    hoarder.destroy()
    game.process_deaths()
    assert len(p1.hand) == pre_hand + 2


def test_summoner_darkmarrow_destroys_played_deathrattle_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.summon("VAC_503")
    # Play (not summon) a Deathrattle minion from hand -> Darkmarrow destroys it.
    loot = p1.give("EX1_096")  # Loot Hoarder, Deathrattle: draw a card
    pre_hand = len(p1.hand)
    loot.play()
    game.process_deaths()
    # The Loot Hoarder is destroyed by Darkmarrow's effect.
    assert loot.zone == Zone.GRAVEYARD
    assert loot not in p1.field
    # Its (doubled) deathrattle drew 2 cards; playing it removed it from hand.
    # pre_hand included the Loot Hoarder; after play it's gone (-1) +2 draws.
    assert len(p1.hand) == pre_hand - 1 + 2


def test_summoner_darkmarrow_tourist_unlocks_deathknight():
    from fireplace.utils import random_draft
    deck = random_draft(CardClass.WARLOCK, tourist=CardClass.DEATHKNIGHT)
    from fireplace import cards as _cards
    classes_seen = set()
    has_dk_tourist = False
    for cid in deck:
        data = _cards.db[cid]
        cls = data.card_class
        classes_seen.add(cls)
        from fireplace.utils import tourist_class_of
        if data.card_class == CardClass.WARLOCK and tourist_class_of(data) == CardClass.DEATHKNIGHT:
            has_dk_tourist = True
    assert CardClass.DEATHKNIGHT in classes_seen
    assert has_dk_tourist


# ---------------------------------------------------------------------------
# VAC_939 — Eat! The! Imp!: Destroy a friendly minion to draw 3 cards.
# ---------------------------------------------------------------------------
def test_eat_the_imp_destroys_and_draws_three():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Seed deck with exactly 3 known cards to draw.
    for _ in range(3):
        c = p1.give(WISP)
        c.zone = Zone.DECK
    victim = p1.summon(WISP)
    pre_hand = len(p1.hand)
    spell = p1.give("VAC_939")
    pre_with_spell = len(p1.hand)
    spell.play(target=victim)
    assert victim.zone == Zone.GRAVEYARD
    assert victim not in p1.field
    # Spell leaves hand (-1), draws 3 => net +2 vs. the hand-with-spell count.
    assert len(p1.hand) == pre_with_spell - 1 + 3


# ---------------------------------------------------------------------------
# VAC_940 — Party Fiend: Battlecry: Summon two 1/1 Felbeasts. Deal 3 damage
# to your hero.
# ---------------------------------------------------------------------------
def test_party_fiend_summons_two_felbeasts_and_hits_hero():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    fiend = p1.give("VAC_940")
    fiend.play()
    felbeasts = [m for m in p1.field if m.id == "VAC_940t"]
    assert len(felbeasts) == 2
    for fb in felbeasts:
        assert (fb.atk, fb.max_health) == (1, 1)
    assert p1.hero.damage == 3


def test_felbeast_token_stats():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    fb = game.player1.summon("VAC_940t")
    assert (fb.atk, fb.max_health) == (1, 1)
    assert Race.DEMON in fb.races


# ---------------------------------------------------------------------------
# VAC_941 — Announce Darkness: Replace your Hero Power and non-Warlock cards
# with Warlock ones. They cost (1) less.
# ---------------------------------------------------------------------------
def test_announce_darkness_replaces_hero_power_and_cards():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Clear hand to control exactly which cards are present.
    for c in list(p1.hand):
        c.discard()
    # Give two non-Warlock (Mage) cards.
    a = p1.give("CS2_029")  # Fireball (Mage spell)
    b = p1.give("CS2_172")  # Bloodfen Raptor (Neutral minion)
    spell = p1.give("VAC_941")
    spell.play()
    # Hero Power is now Life Tap (Warlock).
    assert p1.hero.power.id == "HERO_07bp"
    # Every remaining non-spell hand card is now a Warlock card costing 1 less.
    from fireplace import cards as _cards
    for c in list(p1.hand):
        data = _cards.db[c.id]
        classes = list(getattr(data, "classes", None) or [data.card_class])
        assert CardClass.WARLOCK in classes
        # Cost reduced by 1 via VAC_941e enchant.
        assert any(buff.id == "VAC_941e" for buff in c.buffs)


# ---------------------------------------------------------------------------
# VAC_942 — Fearless Flamejuggler: Battlecry: Gain stats equal to the damage
# your hero has taken this turn.
# ---------------------------------------------------------------------------
def test_fearless_flamejuggler_gains_hero_damage_taken():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    # Deal 4 damage to own hero this turn.
    game.queue_actions(p1.hero, [Hit(p1.hero, 4)])
    assert p1.hero.damaged_this_turn == 4
    juggler = p1.give("VAC_942")
    juggler.play()
    # Base 1/1 + 4/4 = 5/5.
    assert juggler.atk == 1 + 4
    assert juggler.max_health == 1 + 4


def test_fearless_flamejuggler_no_damage_no_buff():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    juggler = p1.give("VAC_942")
    juggler.play()
    assert juggler.atk == 1
    assert juggler.max_health == 1


# ---------------------------------------------------------------------------
# VAC_943 — Sacrificial Imp: Deathrattle: If it's your turn, summon a 6/6 Imp
# with Taunt.
# ---------------------------------------------------------------------------
def test_sacrificial_imp_summons_on_own_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    imp = p1.summon("VAC_943")
    assert p1.current_player
    imp.destroy()
    game.process_deaths()
    monsters = [m for m in p1.field if m.id == "VAC_943t"]
    assert len(monsters) == 1
    m = monsters[0]
    assert (m.atk, m.max_health) == (6, 6)
    assert m.taunt


def test_sacrificial_imp_no_summon_on_enemy_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    imp = p1.summon("VAC_943")
    game.end_turn()  # now it's player2's turn; p1 is not current player
    assert not p1.current_player
    imp.destroy()
    game.process_deaths()
    monsters = [m for m in p1.field if m.id == "VAC_943t"]
    assert len(monsters) == 0


def test_monstrous_imp_token_stats():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    m = game.player1.summon("VAC_943t")
    assert (m.atk, m.max_health) == (6, 6)
    assert m.taunt


# ---------------------------------------------------------------------------
# VAC_944 — Cursed Souvenir: Give a minion +3/+3 and "At the start of your
# turn, deal 3 damage to your hero."
# ---------------------------------------------------------------------------
def test_cursed_souvenir_buff_and_turn_damage():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    target = p1.summon(WISP)  # 1/1
    base_atk, base_health = target.atk, target.max_health
    spell = p1.give("VAC_944")
    spell.play(target=target)
    assert target.atk == base_atk + 3
    assert target.max_health == base_health + 3
    # Advance to the start of p1's next turn: 3 damage to own hero.
    game.end_turn()  # p2 turn
    game.end_turn()  # back to p1, start-of-turn fires
    assert p1.hero.damage == 3


# ---------------------------------------------------------------------------
# VAC_945 — Party Planner Vona: Battlecry: If you've taken 8 damage on your
# turns, summon Ourobos.
# ---------------------------------------------------------------------------
def test_party_planner_vona_summons_ourobos_at_threshold():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    # Take 8 damage on own turn -> counter reaches 8.
    game.queue_actions(p1.hero, [Hit(p1.hero, 8)])
    assert p1.damage_taken_on_own_turns_this_game == 8
    vona = p1.give("VAC_945")
    vona.play()
    ouro = [m for m in p1.field if m.id == "VAC_945t"]
    assert len(ouro) == 1
    assert (ouro[0].atk, ouro[0].max_health) == (8, 8)
    assert ouro[0].taunt


def test_party_planner_vona_no_summon_below_threshold():
    game = prepare_empty_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    p1.hero.max_health = 30
    p1.hero.damage = 0
    game.queue_actions(p1.hero, [Hit(p1.hero, 7)])
    assert p1.damage_taken_on_own_turns_this_game == 7
    vona = p1.give("VAC_945")
    vona.play()
    assert len([m for m in p1.field if m.id == "VAC_945t"]) == 0


def test_ourobos_deathrattle_gives_hand_minion_resummon():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1 = game.player1
    # Clear hand, give exactly one minion to receive the deathrattle enchant.
    for c in list(p1.hand):
        c.discard()
    hand_minion = p1.give(WISP)
    ouro = p1.summon("VAC_945t")
    ouro.destroy()
    game.process_deaths()
    # The hand minion gains the "Deathrattle: Summon Ourobos" enchant (VAC_945e).
    assert any(b.id == "VAC_945e" for b in hand_minion.buffs)


# ---------------------------------------------------------------------------
# VAC_951 — "Health" Drink: Lifesteal. Deal $3 damage to a minion.
# (Drink chain: 3 -> 2 -> last.)
# ---------------------------------------------------------------------------
def test_health_drink_damage_lifesteal_and_next_copy():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    p1.hero.max_health = 30
    p1.hero.damage = 10  # so lifesteal heal is visible
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    enemy.max_health = 80
    enemy.damage = 0
    drink = p1.give("VAC_951")
    drink.play(target=enemy)
    assert enemy.damage == 3
    # Lifesteal healed the hero for 3.
    assert p1.hero.damage == 7
    # Next copy ("2 Drinks left!") appears in hand.
    nexts = [c for c in p1.hand if c.id == "VAC_951t"]
    assert len(nexts) == 1


def test_health_drink_second_gives_last():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    drink2 = p1.give("VAC_951t")  # the "2 Drinks left" copy
    drink2.play(target=enemy)
    assert enemy.damage == 3
    lasts = [c for c in p1.hand if c.id == "VAC_951t2"]
    assert len(lasts) == 1


def test_health_drink_last_returns_nothing():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    last = p1.give("VAC_951t2")  # "Last Drink!"
    last.play(target=enemy)
    assert enemy.damage == 3
    # No further Drink copies generated.
    assert not any(c.id in ("VAC_951", "VAC_951t", "VAC_951t2") for c in p1.hand)


# ---------------------------------------------------------------------------
# VAC_952 — Felfire Bonfire: Deal $4 damage to a minion. If it dies, your next
# Deathrattle minion costs (3) less.
# ---------------------------------------------------------------------------
def test_felfire_bonfire_kills_and_discounts_deathrattle_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    victim = p2.summon(WISP)  # 1/1 -> dies to 4 damage
    spell = p1.give("VAC_952")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.zone == Zone.GRAVEYARD
    # Next Deathrattle minion in hand costs 3 less. Loot Hoarder base cost 2 -> 0.
    loot = p1.give("EX1_096")  # Loot Hoarder, cost 2, has a Deathrattle
    assert loot.cost == max(0, 2 - 3)


def test_felfire_bonfire_no_kill_no_discount():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    victim = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    victim.max_health = 20
    victim.damage = 0
    spell = p1.give("VAC_952")
    spell.play(target=victim)
    game.process_deaths()
    assert victim.zone == Zone.PLAY
    assert victim.damage == 4
    # No discount applied: Loot Hoarder still full cost.
    loot = p1.give("EX1_096")
    assert loot.cost == 2


def test_felfire_bonfire_discount_only_deathrattle_minion():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2
    victim = p2.summon(WISP)
    spell = p1.give("VAC_952")
    spell.play(target=victim)
    game.process_deaths()
    # A non-Deathrattle minion is NOT discounted (Bloodfen Raptor, cost 2).
    raptor = p1.give("CS2_172")
    assert raptor.cost == 2
