"""Perils in Paradise — DEATHKNIGHT collectible card tests.

One (or a small cluster of) tests per collectible Death Knight card:
  VAC_402 Frostbitten Freebooter, VAC_425 Horizon's Edge, VAC_426 Eliza Goreblade,
  VAC_427 Corpsicle, VAC_429 Snow Shredder, VAC_436 Brittlebone Buccaneer,
  VAC_437 Buttons (Shaman Tourist), VAC_445 Ghouls' Night, VAC_513 Slippery Slope,
  VAC_514 Dreadhound Handler.
Assertions follow the PRINTED card text.
"""

from utils import *


# VAC_402 — Frostbitten Freebooter: Deathrattle: Freeze 3 random enemies. Any
# that were already Frozen take 5 damage instead.
def test_frostbitten_freebooter_freezes_three_enemies():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Exactly 3 enemy minions (plus the enemy hero makes 4 chars) — but only
    # minions chosen here are deterministic if we limit to exactly 3 minions
    # and beef nothing; the 3-of-pool is shuffled. We give exactly 3 enemy
    # characters total by clearing & using minions + hero. Use 3 minions so
    # the pool (3 minions + hero = 4) -> 3 frozen. To pin exactly which 3, we
    # instead place exactly 3 enemy minions and freeze-protect the hero by
    # noting it MIGHT be one of the 3. So assert "3 frozen among 4 chars".
    m1 = p2.summon(WISP)
    m2 = p2.summon(WISP)
    m3 = p2.summon(WISP)
    freeb = p1.summon("VAC_402")
    freeb.destroy()
    game.process_deaths()
    enemy_chars = [p2.hero] + list(p2.field)
    frozen = [c for c in enemy_chars if c.frozen]
    assert len(frozen) == 3


def test_frostbitten_freebooter_damages_already_frozen():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Only ONE enemy character: a big minion that is already Frozen. The
    # deathrattle picks 3 random enemies but only this one exists -> it takes
    # 5 damage instead of being (re-)frozen.
    victim = p2.summon(GOLDSHIRE_FOOTMAN)  # 1/2
    victim.max_health = 80
    victim.damage = 0
    victim.frozen = True
    freeb = p1.summon("VAC_402")
    freeb.destroy()
    game.process_deaths()
    assert victim.damage == 5


# VAC_425 — Horizon's Edge (Location): Deal 3 damage randomly split among all
# enemies. After a friendly minion dies, reopen this.
def test_horizons_edge_deals_3_split():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Enemies: a big minion + the enemy hero. The 3 ticks are split RANDOMLY
    # among all enemies, so pin the EXACT TOTAL (3) across both, with each
    # beefed up so no tick is lost to overkill.
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    pre_hero = p2.hero.health
    loc = p1.give("VAC_425")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    game.process_deaths()
    # 3 damage randomly split among all enemies -> exactly 3 total.
    hero_dmg = pre_hero - p2.hero.health
    assert enemy.damage + hero_dmg == 3
    # Using a location sets a 2-turn cooldown.
    assert loc.cooldown == 2


def test_horizons_edge_reopens_on_friendly_minion_death():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    enemy = p2.summon(GOLDSHIRE_FOOTMAN)
    enemy.max_health = 80
    enemy.damage = 0
    loc = p1.give("VAC_425")
    loc.play()
    loc.turn_played = -5
    loc.cooldown = 0
    loc.use()
    game.process_deaths()
    assert loc.cooldown == 2
    # A friendly minion dies -> reopen (cooldown back to 0, usable again).
    fodder = p1.summon(WISP)
    fodder.destroy()
    game.process_deaths()
    assert loc.cooldown == 0
    assert loc.is_usable()


# VAC_426 — Eliza Goreblade: Deathrattle: For the rest of the game, your minions
# have +1 Attack.
def test_eliza_goreblade_buffs_minions_for_rest_of_game():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    eliza = p1.summon("VAC_426")
    # A friendly minion already on board gets +1 Attack after Eliza dies.
    wisp = p1.summon(WISP)  # 1/1
    assert wisp.atk == 1
    eliza.destroy()
    game.process_deaths()
    assert wisp.atk == 2
    # The aura also applies to minions summoned AFTER she died.
    later = p1.summon(WISP)
    assert later.atk == 2


# VAC_427 — Corpsicle: Deal $3 damage. Spend 3 Corpses to return this to your
# hand at the end of your turn.
def test_corpsicle_deals_3():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    target = p2.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    p1.corpses = 0  # not enough corpses -> no return
    spell = p1.give("VAC_427")
    spell.play(target=target)
    assert target.damage == 3


def test_corpsicle_returns_to_hand_when_3_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    target = p2.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    p1.corpses = 3
    spell = p1.give("VAC_427")
    spell.play(target=target)
    # 3 corpses spent.
    assert p1.corpses == 0
    # At end of turn, a fresh Corpsicle is added to hand.
    assert not any(c.id == "VAC_427" for c in p1.hand)
    game.end_turn()
    assert any(c.id == "VAC_427" for c in p1.hand)


def test_corpsicle_no_return_without_corpses():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    target = p2.summon(GOLDSHIRE_FOOTMAN)
    target.max_health = 80
    target.damage = 0
    p1.corpses = 2  # < 3, no return
    spell = p1.give("VAC_427")
    spell.play(target=target)
    assert p1.corpses == 2
    game.end_turn()
    assert not any(c.id == "VAC_427" for c in p1.hand)


# VAC_429 — Snow Shredder: Costs (1) if a character is Frozen. Base cost 4.
def test_snow_shredder_full_cost_when_nothing_frozen():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    shredder = p1.give("VAC_429")
    assert shredder.cost == 4


def test_snow_shredder_costs_1_when_a_character_frozen():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    shredder = p1.give("VAC_429")
    frozen_minion = p2.summon(WISP)
    frozen_minion.frozen = True
    assert shredder.cost == 1


# VAC_436 — Brittlebone Buccaneer: Whenever you play a Deathrattle minion, give
# it Reborn.
def test_brittlebone_gives_reborn_to_deathrattle_minion():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.summon("VAC_436")
    # Loot Hoarder (EX1_096) is a Deathrattle minion.
    dr = p1.give("EX1_096")
    dr.play()
    assert dr.reborn


def test_brittlebone_no_reborn_for_nondeathrattle():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    p1.summon("VAC_436")
    plain = p1.give(WISP)  # no deathrattle
    plain.play()
    assert not plain.reborn


# VAC_437 — Buttons (Shaman Tourist): Battlecry: Draw a spell of each spell
# school.
def test_buttons_draws_one_spell_of_each_school():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    # Seed the deck with exactly one spell of each of the 7 schools so each
    # per-school Draw has exactly one valid card -> all 7 drawn.
    by_school = {
        SpellSchool.ARCANE: "CS2_023",   # Arcane Intellect
        SpellSchool.FIRE: "CS2_029",     # Fireball
        SpellSchool.FROST: "CS2_024",    # Frostbolt
        SpellSchool.NATURE: "EX1_169",   # Innervate
        SpellSchool.HOLY: "CS2_089",     # Holy Light
        SpellSchool.SHADOW: "EX1_622",   # Shadow Word: Death
        SpellSchool.FEL: "EX1_596",      # Demonfire
    }
    planted = {}
    for school, cid in by_school.items():
        try:
            c = p1.card(cid)
        except Exception:
            continue
        if c.data.spell_school != school:
            continue
        c.zone = Zone.DECK
        planted[school] = c.id
    # All 7 schools should have been planted successfully.
    assert len(planted) == 7
    buttons = p1.give("VAC_437")
    buttons.play()
    hand_ids = [c.id for c in p1.hand]
    # Each planted school's spell should have been drawn.
    for school, cid in planted.items():
        assert cid in hand_ids, f"{school.name} spell {cid} not drawn"


# VAC_445 — Ghouls' Night: Summon five 1/1 Ghouls that attack random enemies.
def test_ghouls_night_summons_five_ghouls_that_attack():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    spell = p1.give("VAC_445")
    spell.play()
    # Five 1/1 Ghoul tokens summoned (some may have died if they attacked a
    # minion, but with only the enemy hero available they all survive a face
    # hit). Only enemy target is the hero -> each deals 1 = 5 total.
    assert p2.hero.health == 80 - 5
    ghouls = [m for m in p1.field if m.id == "VAC_445t"]
    assert len(ghouls) == 5
    for g in ghouls:
        assert (g.atk, g.max_health) == (1, 1)


# VAC_513 — Slippery Slope: Freeze a character. Draw a card for each Frozen
# character.
def test_slippery_slope_freezes_and_draws_for_each_frozen():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1, p2 = game.player1, game.player2
    # Pre-freeze one enemy; the spell freezes a second -> 2 frozen -> draw 2.
    pre_frozen = p2.summon(WISP)
    pre_frozen.frozen = True
    target = p2.summon(WISP)
    # Seed deck so draws are real (cant_fatigue is set, but give real cards).
    for _ in range(2):
        c = p1.give(WISP)
        c.zone = Zone.DECK
    pre_hand = len(p1.hand)
    spell = p1.give("VAC_513")
    pre_hand_after_give = len(p1.hand)
    spell.play(target=target)
    assert target.frozen
    # 2 Frozen characters (pre_frozen + target) -> drew 2 cards.
    # Hand after playing = (hand after give) - 1 (spell played) + 2 (drawn).
    assert len(p1.hand) == pre_hand_after_give - 1 + 2


# VAC_514 — Dreadhound Handler: Rush. Deathrattle: Summon a 1/1 Dreadhound with
# Reborn.
def test_dreadhound_handler_has_rush():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    handler = game.player1.summon("VAC_514")
    assert handler.rush


def test_dreadhound_handler_deathrattle_summons_reborn_hound():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    p1 = game.player1
    handler = p1.summon("VAC_514")
    handler.destroy()
    game.process_deaths()
    hounds = [m for m in p1.field if m.id == "VAC_514t"]
    assert len(hounds) == 1
    hound = hounds[0]
    assert (hound.atk, hound.max_health) == (1, 1)
    assert hound.reborn


def test_dreadhound_token_is_beast():
    game = prepare_empty_game(CardClass.DEATHKNIGHT, CardClass.DEATHKNIGHT)
    hound = game.player1.summon("VAC_514t")
    assert Race.BEAST in hound.races
