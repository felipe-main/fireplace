"""Across the Timeways — Demon Hunter.

One tight test per collectible (and per effect-bearing Broxigar token). Random
effects are pinned by clearing the deck of minions / beefing up target HP so
assertions are exact.
"""
from utils import *
from hearthstone.enums import Race


def _clear_hand(player):
    for card in list(player.hand):
        card.discard()


def _clear_deck_minions(player):
    for card in list(player.deck):
        if card.type == CardType.MINION:
            card.discard()


def _deck_card(player, cid):
    return player.card(cid, zone=Zone.DECK)


def _brox_game():
    """A game whose player1 deck contains Broxigar (so its Start of Game
    fires), plus filler minions for player2."""
    from fireplace.player import Player

    deck1 = ["TIME_020"] + ["CS2_182"] * 29
    deck2 = ["CS2_182"] * 30
    p1 = Player("Player1", deck1, CardClass.DEMONHUNTER.default_hero)
    p2 = Player("Player2", deck2, CardClass.DEMONHUNTER.default_hero)
    game = BaseTestGame(players=(p1, p2))
    game.start()
    for pl in game.players:
        if pl.choice:
            pl.choice.choose()
    # Return the game plus the Broxigar owner (turn order is coin-flipped, so
    # game.player1 is not necessarily the deck that held Broxigar).
    return game, p1


# ---------------------------------------------------------------------------
# Broxigar (TIME_020) + Argus tokens
# ---------------------------------------------------------------------------


def test_broxigar_start_of_game_equips_and_shuffles():
    game, p1 = _brox_game()
    # Broxigar disappeared, equipped the Axe of Cenarius, shuffled in Portal 1.
    assert not any(c.id == "TIME_020" for c in p1.deck)
    assert not any(c.id == "TIME_020" for c in p1.hand)
    assert p1.weapon is not None and p1.weapon.id == "TIME_020t1"
    assert any(c.id == "TIME_020t2" for c in p1.deck)


def test_axe_of_cenarius_draws_portal_on_kill():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _deck_card(p1, "TIME_020t2")
    p1.summon("TIME_020t1")  # equip the Axe (3/2)
    victim = p2.summon("CS2_182")
    victim.max_health = 1
    victim.damage = 0
    p1.hero.attack(victim)
    assert victim.dead
    assert any(c.id == "TIME_020t2" for c in p1.hand)
    assert not any(c.id == "TIME_020t2" for c in p1.deck)


def test_axe_of_cenarius_no_draw_without_kill():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    _deck_card(p1, "TIME_020t2")
    p1.summon("TIME_020t1")  # 3-attack Axe
    tanky = p2.summon("CS2_182")  # 4/5 — survives a 3-damage swing
    tanky.max_health = 20
    tanky.damage = 0
    p1.hero.attack(tanky)
    assert not tanky.dead
    assert not any(c.id == "TIME_020t2" for c in p1.hand)


def test_first_portal_summons_demon_and_chains():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    portal = p1.give("TIME_020t2")
    portal.play()
    demon = [m for m in p2.field if m.id == "TIME_020t2t"]
    assert len(demon) == 1
    assert demon[0].atk == 1 and demon[0].health == 1
    pre = len(p1.hand)
    demon[0].destroy()
    # Owner (p1) draws a card and the Second Portal is shuffled into p1's deck.
    assert len(p1.hand) - pre == 1
    assert any(c.id == "TIME_020t3" for c in p1.deck)


def test_second_portal_demon_chains_to_third():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    portal = p1.give("TIME_020t3")
    portal.play()
    demon = [m for m in p2.field if m.id == "TIME_020t3t"][0]
    assert demon.atk == 2 and demon.health == 1
    demon.destroy()
    assert any(c.id == "TIME_020t4" for c in p1.deck)


def test_third_portal_demon_chains_to_final():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    portal = p1.give("TIME_020t4")
    portal.play()
    demon = [m for m in p2.field if m.id == "TIME_020t4t"][0]
    assert demon.atk == 3 and demon.health == 1
    demon.destroy()
    assert any(c.id == "TIME_020t5" for c in p1.deck)


def test_final_portal_demon_returns_broxigar():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    _clear_hand(p1)
    portal = p1.give("TIME_020t5")
    portal.play()
    demon = [m for m in p2.field if m.id == "TIME_020t5t"][0]
    assert demon.atk == 4 and demon.health == 1
    demon.destroy()
    assert any(c.id == "TIME_020" for c in p1.hand)


# ---------------------------------------------------------------------------
# Doomsday Prepper (TIME_021)
# ---------------------------------------------------------------------------


def test_doomsday_prepper_outcast_immune():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    dp = p1.give("TIME_021")  # only card -> outcast position
    dp.play()
    assert p1.hero.immune


def test_doomsday_prepper_no_outcast_no_immune():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    # Surround it so it is neither leftmost nor rightmost -> not an Outcast.
    p1.give("CS2_182")
    dp = p1.give("TIME_021")
    p1.give("CS2_182")
    dp.play()
    assert not p1.hero.immune


# ---------------------------------------------------------------------------
# Perennial Serpent (TIME_022)
# ---------------------------------------------------------------------------


def test_perennial_serpent_cost_reduction_with_dormant():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    serpent = p1.give("TIME_022")
    assert serpent.cost == 8  # no Dormant minion yet
    # Imprison an enemy minion (makes it Dormant) via Timeway Warden.
    enemy = p2.summon("CS2_182")
    warden = p1.give("TIME_442")
    warden.play(target=enemy)
    assert enemy.dormant
    assert serpent.cost == 4  # 8 - 4


# ---------------------------------------------------------------------------
# Aeon Rend (TIME_441) — Rewind
# ---------------------------------------------------------------------------


def test_aeon_rend_base_two_hits():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # Single enemy (hero) with big HP absorbs both random hits.
    p2.hero.max_health = 80
    rend = p1.give("TIME_441")
    rend.play()
    keep = next(c for c in p1.choice.cards if c.id == "TIME_000ta")
    p1.choice.choose(keep)
    assert p2.hero.damage == 8  # exactly 4 + 4


def test_aeon_rend_rewind_reruns():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    rend = p1.give("TIME_441")
    rend.play()
    rewind = next(c for c in p1.choice.cards if c.id == "TIME_000tb")
    p1.choice.choose(rewind)
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert p2.hero.damage == 16  # 8 from base + 8 from rewind re-run


# ---------------------------------------------------------------------------
# Timeway Warden (TIME_442)
# ---------------------------------------------------------------------------


def test_timeway_warden_imprison_and_awaken():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon("CS2_182")
    warden = p1.give("TIME_442")
    warden.play(target=enemy)
    assert enemy.dormant
    assert enemy.dormant_turns == 10000
    # Deathrattle awakens the imprisoned minion.
    warden.destroy()
    assert not enemy.dormant
    assert enemy.zone == Zone.PLAY


# ---------------------------------------------------------------------------
# Hounds of Fury (TIME_443)
# ---------------------------------------------------------------------------


def test_hounds_of_fury_summons_two():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    hounds = p1.give("TIME_443")
    hounds.play()
    pups = [m for m in p1.field if m.id in ("TIME_443t", "TIME_443t2")]
    assert len(pups) == 2
    for h in pups:
        assert h.atk == 3 and h.health == 3


def test_hounds_of_fury_attack_when_no_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    _clear_deck_minions(p1)
    # Make the hero NOT the lowest, force both hounds onto the Yeti.
    p2.hero.max_health = 80
    target = p2.summon("CS2_182")
    target.max_health = 40
    target.damage = 0
    hounds = p1.give("TIME_443")
    hounds.play()
    assert target.damage == 6  # both 3/3 hounds hit it
    assert p2.hero.damage == 0


def test_hounds_of_fury_no_attack_with_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    # Deck still has minions -> hounds do NOT auto-attack.
    assert any(c.type == CardType.MINION for c in p1.deck)
    target = p2.summon("CS2_182")
    target.damage = 0
    hounds = p1.give("TIME_443")
    hounds.play()
    assert target.damage == 0


# ---------------------------------------------------------------------------
# Time-Lost Glaive (TIME_444)
# ---------------------------------------------------------------------------


def test_time_lost_glaive_deathrattle_gives_demon():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    glaive = p1.give("TIME_444")
    glaive.play()
    assert p1.weapon is not None and p1.weapon.id == "TIME_444"
    p1.weapon.destroy()
    assert len(p1.hand) == 1
    got = p1.hand[0]
    assert got.type == CardType.MINION and Race.DEMON in got.races


# ---------------------------------------------------------------------------
# The Eternal Hold (TIME_446) — Location
# ---------------------------------------------------------------------------


def test_eternal_hold_gives_expensive_demon_and_zeroes_cost():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_deck_minions(p1)
    loc = p1.give("TIME_446")
    loc.play()
    game.end_turn()
    game.end_turn()  # location off cooldown
    _clear_hand(p1)  # so the only new hand card is the gotten Demon
    loc.use()
    assert len(p1.hand) == 1
    demon = p1.hand[0]
    assert demon.type == CardType.MINION and Race.DEMON in demon.races
    assert demon.data.cost >= 5  # printed cost 5+
    assert demon.cost == 0  # Jailbreak zeroed it (no minions in deck)


def test_eternal_hold_no_discount_with_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    assert any(c.type == CardType.MINION for c in p1.deck)
    loc = p1.give("TIME_446")
    loc.play()
    game.end_turn()
    game.end_turn()
    _clear_hand(p1)
    loc.use()
    assert len(p1.hand) == 1
    demon = p1.hand[0]
    # Deck still has minions -> Jailbreak (cost-0) did NOT apply.
    assert not any(b.id == "TIME_446e" for b in demon.buffs)
    assert demon.data.cost >= 5


# ---------------------------------------------------------------------------
# Solitude (TIME_448)
# ---------------------------------------------------------------------------


def test_solitude_discovers_and_reduces_when_no_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    _clear_deck_minions(p1)
    yeti = p1.give("CS2_182")  # 4-cost minion in hand
    sol = p1.give("TIME_448")
    sol.play()
    while p1.choice:  # resolve the Discover
        p1.choice.choose(p1.choice.cards[0])
    assert yeti.cost == 2  # 4 - 2


def test_solitude_no_reduction_with_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_hand(p1)
    assert any(c.type == CardType.MINION for c in p1.deck)
    yeti = p1.give("CS2_182")
    sol = p1.give("TIME_448")
    sol.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert yeti.cost == 4  # unchanged


# ---------------------------------------------------------------------------
# Lasting Legacy (TIME_449)
# ---------------------------------------------------------------------------


def test_lasting_legacy_buffs_hero_only_with_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    assert any(c.type == CardType.MINION for c in p1.deck)
    yeti = p1.give("CS2_182")  # 4/5 in hand
    legacy = p1.give("TIME_449")
    legacy.play()
    assert p1.hero.atk == 4  # +4 this turn
    assert yeti.atk == 4  # hand minion NOT buffed (deck has minions)


def test_lasting_legacy_buffs_hand_minions_when_no_deck_minions():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    _clear_deck_minions(p1)
    yeti = p1.give("CS2_182")  # 4/5 in hand
    legacy = p1.give("TIME_449")
    legacy.play()
    assert p1.hero.atk == 4
    assert yeti.atk == 8  # 4 + 4


def test_lasting_legacy_hero_buff_expires_end_of_turn():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1 = game.player1
    legacy = p1.give("TIME_449")
    legacy.play()
    assert p1.hero.atk == 4
    game.end_turn()
    assert p1.hero.atk == 0  # "this turn" effect wore off
