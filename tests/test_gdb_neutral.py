"""The Great Dark Beyond — NEUTRAL collectible cards.

Tight unit tests asserting the PRINTED behaviour of every collectible
NEUTRAL card (GDB_ prefix) in the Space set. One test (or a small cluster)
per card; assertions are exact wherever the setup can be constrained.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards


# ---------------------------------------------------------------------------
# GDB_100 — Arkonite Defense Crystal: Taunt. Deathrattle: Gain 6 Armor.
# Starship Piece.
# ---------------------------------------------------------------------------
def test_arkonite_defense_crystal():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    crystal = p1.summon("GDB_100")
    assert crystal.taunt
    assert _cards.db["GDB_100"].tags.get(GameTag.STARSHIP_PIECE, 0)
    p1.hero.armor = 0
    crystal.destroy()
    game.process_deaths()
    assert p1.hero.armor == 6


# ---------------------------------------------------------------------------
# GDB_101 — Dimensional Core: Divine Shield. Starship Piece. (vanilla, data)
# ---------------------------------------------------------------------------
def test_dimensional_core():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    core = p1.summon("GDB_101")
    assert core.divine_shield
    assert _cards.db["GDB_101"].tags.get(GameTag.STARSHIP_PIECE, 0)
    assert (core.atk, core.max_health) == (2, 2)


# ---------------------------------------------------------------------------
# GDB_120 — The Exodar: Battlecry: If you're building a Starship, launch it and
# choose a Protocol! (Emergency Repairs / Offensive Formation / Crew Transport.)
# ---------------------------------------------------------------------------
def _exodar_with_ship(game, p1):
    # Bank one piece (GDB_100, 2/4 Taunt) so a Starship is building.
    p1.summon("GDB_100").destroy()
    game.process_deaths()
    assert p1.is_building_starship
    ship = p1.starship
    exodar = p1.give("GDB_120")
    exodar.play()
    assert not p1.is_building_starship
    assert not ship.dormant
    # All three Protocols are offered.
    assert p1.choice is not None
    assert [c.id for c in p1.choice.cards] == ["GDB_100a", "GDB_100b", "GDB_100c"]
    return ship


def test_the_exodar_emergency_repairs_protocol():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    ship = _exodar_with_ship(game, p1)
    hp = ship.health
    # Zero armor after the banking (Arkonite's Deathrattle gives +6) so we
    # measure only the Protocol's contribution.
    p1.hero.armor = 0
    p1.choice.choose(p1.choice.cards[0])  # Emergency Repairs
    # Gain Armor equal to the ship's Health, twice.
    assert p1.hero.armor == hp * 2


def test_the_exodar_offensive_formation_protocol():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    foe = p2.summon("CS2_201")
    foe.max_health = 40
    foe.damage = 0
    ship = _exodar_with_ship(game, p1)
    atk = ship.atk
    p1.choice.choose(p1.choice.cards[1])  # Offensive Formation
    # Deal damage equal to the ship's Attack, split among all enemies.
    assert (30 - p2.hero.health) + foe.damage == atk


def test_the_exodar_crew_transport_protocol():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Bank two distinct pieces so we can see both copied.
    p1.summon("GDB_100").destroy()
    game.process_deaths()
    p1.summon("GDB_112").destroy()
    game.process_deaths()
    assert p1.is_building_starship
    p1.give("GDB_120").play()
    p1.choice.choose(p1.choice.cards[2])  # Crew Transport
    copies = [c for c in p1.hand if c.id in ("GDB_100", "GDB_112")]
    assert len(copies) == 2
    assert all(c.cost == 1 for c in copies)


def test_the_exodar_does_nothing_without_starship():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert not p1.is_building_starship
    p1.hero.armor = 0
    exodar = p1.give("GDB_120")
    exodar.play()
    # No starship being built -> no launch, no protocol armor.
    assert p1.hero.armor == 0
    assert p1.starship is None


# ---------------------------------------------------------------------------
# GDB_129 — Doommaiden: Battlecry: Draw a card from your opponent's deck.
# (Approx: put-back rider not modelled.)
# The printed card draws the opponent's card into YOUR hand. The script does
# Draw(controller, opponent_card); the drawn card's controller flips to you and
# it leaves the opponent's deck, but it is NOT added to your hand list (it stays
# registered in the opponent's hand). Likely a shared-engine cross-player Draw
# bug — reported in notes; asserted at the printed behaviour and xfailed.
# ---------------------------------------------------------------------------
def test_doommaiden_draws_from_opponent_deck():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Single, known card in the opponent's deck -> deterministic draw.
    seed = p2.give(WISP)
    seed.zone = Zone.DECK
    assert len(p2.deck) == 1
    maiden = p1.give("GDB_129")
    maiden.play()
    # The opponent's Wisp moved into p1's hand; p2's deck is now empty.
    assert len(p2.deck) == 0
    assert seed in p1.hand


def test_doommaiden_returns_unplayed_card_at_end_of_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    seed = p2.give(WISP)
    seed.zone = Zone.DECK
    p1.give("GDB_129").play()
    assert seed in p1.hand
    # You don't play it -> at end of your turn it goes back to the opponent.
    # (end_turn also starts p2's turn, and with an otherwise-empty deck p2
    # immediately draws the returned card — so assert it left your hand and is
    # the opponent's again, not the exact zone.)
    game.end_turn()
    assert seed not in p1.hand
    assert seed.controller is p2


def test_doommaiden_keeps_card_if_played_this_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    if game.current_player is not p1:
        game.end_turn()
    seed = p2.give(WISP)
    seed.zone = Zone.DECK
    p1.give("GDB_129").play()
    assert seed in p1.hand
    # Play it this turn -> it stays in play, not returned.
    p1.used_mana = 0
    seed.play()
    assert seed.zone == Zone.PLAY
    game.end_turn()
    assert seed.zone == Zone.PLAY
    assert seed.controller is p1


# ---------------------------------------------------------------------------
# GDB_130 — Crystal Welder: Taunt. Battlecry: If you're building a Starship,
# gain +2/+2.
# ---------------------------------------------------------------------------
def test_crystal_welder_buffs_when_building_starship():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("GDB_100").destroy()  # start building a starship
    game.process_deaths()
    assert p1.is_building_starship
    welder = p1.give("GDB_130")
    welder.play()
    assert welder.taunt
    assert (welder.atk, welder.max_health) == (2 + 2, 3 + 2)


def test_crystal_welder_no_buff_without_starship():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert not p1.is_building_starship
    welder = p1.give("GDB_130")
    welder.play()
    assert (welder.atk, welder.max_health) == (2, 3)


# ---------------------------------------------------------------------------
# GDB_131 — Velen, Leader of the Exiled: Taunt. Deathrattle: Trigger the
# Battlecries and Deathrattles of all other Draenei you played this game.
# (Approx: re-fires deathrattle scripts.)
# ---------------------------------------------------------------------------
def test_velen_retriggers_draenei_deathrattles():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    from hearthstone.enums import SpellSchool

    assert Race.DRAENEI in _cards.db["GDB_131"].races
    # Play a Draenei with a clean, observable deathrattle: Galactic Crusader
    # (GDB_862, Draenei, Deathrattle: get two Holy spells costing 3 less).
    assert Race.DRAENEI in _cards.db["GDB_862"].races
    crusader = p1.give("GDB_862")
    crusader.play()
    crusader.destroy()  # fire its own deathrattle once already
    game.process_deaths()
    for c in list(p1.hand):
        c.discard()
    p1.used_mana = 0  # refill so the 7-cost Velen is playable
    velen = p1.give("GDB_131")
    velen.play()
    assert velen.taunt
    # Velen dies -> retriggers GDB_862's deathrattle (two Holy spells).
    velen.destroy()
    game.process_deaths()
    spells = [c for c in p1.hand if c.type == CardType.SPELL]
    assert len(spells) == 2
    for s in spells:
        assert s.data.spell_school == SpellSchool.HOLY


# ---------------------------------------------------------------------------
# GDB_132 — Relentless Wrathguard: Battlecry: Deal 2 damage to an enemy minion.
# If it dies, Discover a Demon.
# ---------------------------------------------------------------------------
def test_relentless_wrathguard_kills_and_discovers_demon():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    victim = p2.summon(WISP)  # 1/1 -> dies to 2 damage
    guard = p1.give("GDB_132")
    guard.play(target=victim)
    game.process_deaths()
    assert victim.dead
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert Race.DEMON in _cards.db[cid].races
    p1.choice.choose(p1.choice.cards[0])


def test_relentless_wrathguard_survivor_no_discover():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # Chillwind Yeti 4/5 -> survives 2 damage
    guard = p1.give("GDB_132")
    guard.play(target=target)
    game.process_deaths()
    assert not target.dead
    assert target.damage == 2
    assert p1.choice is None


# ---------------------------------------------------------------------------
# GDB_142 — The Ceaseless Expanse: Costs (1) less for each card drawn/played/
# destroyed. Battlecry: Destroy all other minions. (Cost approx: counts cards
# played this game.)
# ---------------------------------------------------------------------------
def test_ceaseless_expanse_destroys_all_other_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    ally = p1.summon("CS2_182")
    enemy = p2.summon("CS2_182")
    # Base cost is 100; summon it onto the board, then fire its play script
    # directly (the battlecry: Destroy all other minions).
    expanse = p1.summon("GDB_142")
    game.queue_actions(expanse, list(expanse.data.scripts.play))
    game.process_deaths()
    assert ally.dead
    assert enemy.dead
    assert not expanse.dead
    assert expanse in p1.field


def test_ceaseless_expanse_cost_reduction():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    expanse = p1.give("GDB_142")
    assert expanse.cost == 100
    # cost_mod = -Count(CARDS_PLAYED_THIS_GAME): play 2 cards.
    p1.give(WISP).play()
    p1.give(WISP).play()
    assert len(p1.cards_played_this_game) == 2
    assert expanse.cost == 100 - 2


def test_ceaseless_expanse_counts_draw_play_destroy():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    expanse = p1.give("GDB_142")
    assert expanse.cost == 100  # baseline: ledger at 0
    # Draw a card (+1).
    seed = p1.give(WISP)
    seed.zone = Zone.DECK
    p1.draw()
    # Play a minion (+1) then destroy it (+1).
    m = p1.give(WISP)
    m.play()
    m.destroy()
    game.process_deaths()
    # Drawn + played + destroyed = 3 ledger events -> 3 cheaper.
    assert expanse.cost == 100 - 3


# ---------------------------------------------------------------------------
# GDB_143 — Nexus-Prince Shaffar: Spellburst: Give a minion in your hand +3/+3
# and this Spellburst.  (UNIMPLEMENTED in script -> CARD BUG.)
# ---------------------------------------------------------------------------
def test_nexus_prince_shaffar_spellburst_buffs_hand_minion():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    shaffar = p1.summon("GDB_143")
    assert shaffar.has_spellburst
    # A single minion in hand -> unique buff target.
    hand_minion = p1.give(WISP)  # 1/1
    base_atk, base_health = hand_minion.atk, hand_minion.max_health
    # Cast a spell to trigger the Spellburst.
    p1.give(MOONFIRE).play(target=p1.hero)
    assert hand_minion.atk == base_atk + 3
    assert hand_minion.max_health == base_health + 3
    # ...and the buffed minion gained the Spellburst too.
    assert hand_minion.has_spellburst


def test_nexus_prince_shaffar_spellburst_propagates():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("GDB_143")
    first = p1.give(WISP)  # 1/1, the only hand minion
    # First spell: Shaffar buffs the Wisp +3/+3 and grants it the Spellburst.
    p1.give(MOONFIRE).play(target=p1.hero)
    assert (first.atk, first.max_health) == (1 + 3, 1 + 3)
    assert first.has_spellburst
    # Play the buffed Wisp, add a second hand minion, cast again -> the Wisp's
    # propagated Spellburst buffs the second minion +3/+3.
    first.play()
    second = p1.give(WISP)  # the only hand minion now
    p1.give(MOONFIRE).play(target=p1.hero)
    assert (second.atk, second.max_health) == (1 + 3, 1 + 3)
    assert second.has_spellburst


# ---------------------------------------------------------------------------
# GDB_145 — Kil'jaeden: Battlecry: Replace your deck with an endless portal of
# Demons. Each turn, they gain an additional +2/+2.
# ---------------------------------------------------------------------------
def test_kiljaeden_fills_deck_with_demons():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Seed the deck with a non-Demon to prove it's replaced.
    old = p1.give(WISP)
    old.zone = Zone.DECK
    kj = p1.give("GDB_145")
    kj.play()
    assert old.zone == Zone.SETASIDE
    assert len(p1.deck) == p1.max_deck_size
    for c in p1.deck:
        assert Race.DEMON in _cards.db[c.id].races
    assert p1._kiljaeden_active


def test_kiljaeden_portal_never_fatigues():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("GDB_145").play()
    # Empty the deck, then draw: the portal conjures a Demon instead of fatigue.
    for c in list(p1.deck):
        c.zone = Zone.SETASIDE
    hp = p1.hero.health
    game.queue_actions(p1.hero, [Draw(p1)])
    assert p1.hero.health == hp  # no fatigue damage
    drawn = p1.hand[-1]
    assert Race.DEMON in _cards.db[drawn.id].races


def test_kiljaeden_demons_escalate_two_two_each_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("GDB_145").play()
    # Track one specific portal Demon's stats across turns.
    demon = p1.deck[0]
    base = (demon.atk, demon.max_health)
    assert p1._kiljaeden_bonus == 0
    game.end_turn()
    game.end_turn()  # one own-turn cycle -> +2/+2
    assert p1._kiljaeden_bonus == 2
    assert (demon.atk, demon.max_health) == (base[0] + 2, base[1] + 2)
    game.end_turn()
    game.end_turn()  # another -> +4/+4 total
    assert p1._kiljaeden_bonus == 4
    assert (demon.atk, demon.max_health) == (base[0] + 4, base[1] + 4)


# ---------------------------------------------------------------------------
# GDB_310 — Ethereal Oracle: Spell Damage +1. Spellburst: Draw 2 spells.
# ---------------------------------------------------------------------------
def test_ethereal_oracle_spellburst_draws_two_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert _cards.db["GDB_310"].spell_damage == 1
    oracle = p1.summon("GDB_310")
    assert oracle.has_spellburst
    # Stock deck: 2 spells (drawable) plus a minion that must NOT be drawn.
    for _ in range(2):
        s = p1.give(FIREBALL)
        s.zone = Zone.DECK
    m = p1.give(WISP)
    m.zone = Zone.DECK
    # Clear hand so the drawn spells are easy to count.
    for c in list(p1.hand):
        c.discard()
    p1.give(MOONFIRE).play(target=p1.hero)  # trigger spellburst
    drawn_spells = [c for c in p1.hand if c.id == FIREBALL]
    assert len(drawn_spells) == 2
    assert m.zone == Zone.DECK  # the minion was not drawn


# ---------------------------------------------------------------------------
# GDB_311 — Deep Space Curator: Spellburst: Get a random minion of the spell's
# Cost. Set its Cost to (0).
# ---------------------------------------------------------------------------
def test_deep_space_curator_gets_zero_cost_minion_of_spell_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    curator = p1.summon("GDB_311")
    assert curator.has_spellburst
    for c in list(p1.hand):
        c.discard()
    fb = p1.give(FIREBALL)  # 4-cost spell
    fb.play(target=p1.hero)
    got = [c for c in p1.hand if c.type == CardType.MINION]
    assert len(got) == 1
    minion = got[0]
    # Random minion of the spell's Cost (4) and its Cost set to 0.
    assert minion.data.cost == 4
    assert minion.cost == 0


# ---------------------------------------------------------------------------
# GDB_320 — Eredar Brute: Taunt, Lifesteal. Costs (1) less for each enemy
# minion.
# ---------------------------------------------------------------------------
def test_eredar_brute_cost_reduction_per_enemy_minion():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    brute = p1.give("GDB_320")
    assert brute.cost == 7
    p2.summon(WISP)
    p2.summon(WISP)
    assert brute.cost == 7 - 2  # two enemy minions -> -2


def test_eredar_brute_keywords():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    brute = p1.summon("GDB_320")
    assert brute.taunt
    assert brute.lifesteal


# ---------------------------------------------------------------------------
# GDB_321 — Mutating Lifeform: After this survives damage, gain a random Bonus
# Effect.
# ---------------------------------------------------------------------------
def test_mutating_lifeform_gains_bonus_effect_on_survival():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    from fireplace.actions import Hit

    lifeform = p1.summon("GDB_321")  # 3/8
    pre_tags = {t: lifeform.tags.get(t, 0) for t in (
        GameTag.TAUNT, GameTag.DIVINE_SHIELD, GameTag.RUSH, GameTag.WINDFURY,
        GameTag.LIFESTEAL, GameTag.POISONOUS, GameTag.REBORN,
    )}
    pre_atk, pre_health = lifeform.atk, lifeform.max_health
    # Survive damage: 3 to an 8-health minion.
    game.queue_actions(p1.hero, [Hit(lifeform, 3)])
    game.process_deaths()
    assert not lifeform.dead
    # A random Bonus Effect was gained: at least one keyword/stat changed.
    post_tags = {t: lifeform.tags.get(t, 0) for t in pre_tags}
    stat_changed = (lifeform.atk != pre_atk) or (lifeform.max_health != pre_health)
    keyword_changed = any(post_tags[t] != pre_tags[t] for t in pre_tags)
    assert stat_changed or keyword_changed


# ---------------------------------------------------------------------------
# GDB_322 — Lightfused Manasaber: Rush. Spellburst: Gain Divine Shield.
# ---------------------------------------------------------------------------
def test_lightfused_manasaber_spellburst_divine_shield():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    saber = p1.summon("GDB_322")
    assert saber.rush
    assert not saber.divine_shield
    p1.give(MOONFIRE).play(target=p1.hero)
    assert saber.divine_shield


# ---------------------------------------------------------------------------
# GDB_330 — Ur'zul Rager: Lifesteal. Spellburst: Attack a random enemy minion.
# ---------------------------------------------------------------------------
def test_urzul_rager_spellburst_attacks_enemy_minion():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    rager = p1.summon("GDB_330")  # 5/1 Lifesteal
    assert rager.lifesteal
    # Single enemy minion, beefed up so it survives the 5-attack and is the
    # only legal target.
    enemy = p2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    p1.hero.damage = 5  # so lifesteal healing is observable
    p1.give(MOONFIRE).play(target=p1.hero)  # MOONFIRE hits hero for 1 first
    # The Moonfire took the hero to damage 6; the rager attacked enemy for 5,
    # lifesteal heals the hero by 5 -> hero damage 6 - 5 = 1.
    assert enemy.damage == 5
    assert p1.hero.damage == 1


# ---------------------------------------------------------------------------
# GDB_331 — Splitting Spacerock: Deathrattle: Summon two 4/4 Splitting Boulders.
# (and the token chain.)
# ---------------------------------------------------------------------------
def test_splitting_spacerock_deathrattle_chain():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    rock = p1.summon("GDB_331")  # 8/8
    rock.destroy()
    game.process_deaths()
    boulders = [m for m in p1.field if m.id == "GDB_331t1"]
    assert len(boulders) == 2
    assert all((b.atk, b.max_health) == (4, 4) for b in boulders)


def test_splitting_boulder_into_stones():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    boulder = p1.summon("GDB_331t1")
    boulder.destroy()
    game.process_deaths()
    stones = [m for m in p1.field if m.id == "GDB_331t2"]
    assert len(stones) == 2
    assert all((s.atk, s.max_health) == (2, 2) for s in stones)


def test_splitting_stone_into_pebbles():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    stone = p1.summon("GDB_331t2")
    stone.destroy()
    game.process_deaths()
    pebbles = [m for m in p1.field if m.id == "GDB_331t3"]
    assert len(pebbles) == 2
    assert all((p.atk, p.max_health) == (1, 1) for p in pebbles)


# ---------------------------------------------------------------------------
# GDB_333 — Space Pirate: Deathrattle: Your next weapon costs (1) less.
# Enchant GDB_333e ({COST: -1}) is applied to the PLAYER entity, where a flat
# COST tag does nothing to weapons in hand -> the next weapon is not discounted.
# CARD BUG (needs a real next-weapon cost_mod).
# ---------------------------------------------------------------------------
def test_space_pirate_discounts_next_weapon():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    pirate = p1.summon("GDB_333")
    pirate.destroy()
    game.process_deaths()
    weapon = p1.give(LIGHTS_JUSTICE)  # base 1-cost
    assert weapon.cost == 1 - 1


# ---------------------------------------------------------------------------
# GDB_340 — Star Vulpera: Tradeable. Battlecry: Destroy an enemy Starship or
# Starship Piece.
# ---------------------------------------------------------------------------
def test_star_vulpera_destroys_enemy_starship_piece():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Enemy has a single Starship Piece in play.
    piece = p2.summon("GDB_101")  # Dimensional Core, Starship Piece
    assert _cards.db["GDB_101"].tags.get(GameTag.STARSHIP_PIECE, 0)
    vulpera = p1.give("GDB_340")
    vulpera.play()
    game.process_deaths()
    assert piece.dead
    assert piece not in p2.field


def test_star_vulpera_destroys_enemy_building_starship():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.summon("GDB_100").destroy()  # opponent builds a starship
    game.process_deaths()
    assert p2.is_building_starship
    vulpera = p1.give("GDB_340")
    vulpera.play()
    game.process_deaths()
    assert p2.starship is None


# ---------------------------------------------------------------------------
# GDB_341 — Red Giant: Costs (1) less for each adjacent card played while in
# hand.
# ---------------------------------------------------------------------------
def test_red_giant_cost_reduction_per_adjacent_play():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    giant = p1.give("GDB_341")
    assert giant.cost == 8
    # The cost_mod reads the per-card "adjacent_plays_while_in_hand" counter.
    giant.adjacent_plays_while_in_hand = 3
    assert giant.cost == 8 - 3


# ---------------------------------------------------------------------------
# GDB_343 — Perplexing Anomaly: Rush, Taunt, ...Stealth? (vanilla keywords)
# ---------------------------------------------------------------------------
def test_perplexing_anomaly_keywords():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    anomaly = p1.summon("GDB_343")
    assert anomaly.rush
    assert anomaly.taunt
    assert anomaly.stealthed
    assert (anomaly.atk, anomaly.max_health) == (2, 5)


# ---------------------------------------------------------------------------
# GDB_435 — Moonstone Mauler: Battlecry: Shuffle 3 Asteroids into your deck that
# deal damage to a random enemy when drawn.
# ---------------------------------------------------------------------------
def test_moonstone_mauler_shuffles_three_asteroids():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    mauler = p1.give("GDB_435")
    mauler.play()
    asteroids = [c for c in p1.deck if c.id == "GDB_430"]
    assert len(asteroids) == 3


# ---------------------------------------------------------------------------
# GDB_450 — Ace Wayfinder: Battlecry: Gain two random Bonus Effects. The next
# Draenei you play gains them as well.
# ---------------------------------------------------------------------------
def test_ace_wayfinder_gains_bonus_effects_and_passes_to_next_draenei():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1

    def keyset(m):
        return {t: m.tags.get(t, 0) for t in (
            GameTag.TAUNT, GameTag.DIVINE_SHIELD, GameTag.RUSH, GameTag.WINDFURY,
            GameTag.LIFESTEAL, GameTag.POISONOUS, GameTag.REBORN,
            GameTag.ATK, GameTag.HEALTH,
        )}

    ace = p1.give("GDB_450")  # 4/4 Draenei
    pre = keyset(ace)
    ace.play()
    post = keyset(ace)
    # Ace gained two bonus effects: its own tag state changed.
    assert any(post[t] != pre[t] for t in pre)
    # The next Draenei played also gains the bonus effects (hook registered).
    assert len(p1.next_draenei_hooks) == 1
    p1.used_mana = 0  # refill so the 7-cost Velen is playable
    velen = p1.give("GDB_131")  # next Draenei
    velen_pre = keyset(velen)
    velen.play()
    velen_post = keyset(velen)
    assert any(velen_post[t] != velen_pre[t] for t in velen_pre)
    assert p1.next_draenei_hooks == []  # hook consumed


# ---------------------------------------------------------------------------
# GDB_461 — Astral Vigilant: Battlecry: Get a copy of the last Draenei you
# played.
# ---------------------------------------------------------------------------
def test_astral_vigilant_copies_last_draenei():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Play a Draenei first so last_draenei_played is set.
    velen = p1.give("GDB_131")
    velen.play()
    assert p1.last_draenei_played == "GDB_131"
    vigilant = p1.give("GDB_461")
    vigilant.play()
    copies = [c for c in p1.hand if c.id == "GDB_131"]
    assert len(copies) == 1


def test_astral_vigilant_no_draenei_played_gives_nothing():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    assert p1.last_draenei_played is None
    for c in list(p1.hand):
        c.discard()
    vigilant = p1.give("GDB_461")
    vigilant.play()
    assert len(p1.hand) == 0  # nothing added


# ---------------------------------------------------------------------------
# GDB_463 — Troubled Mechanic: Divine Shield. Spellburst: Draw a Draenei.
# ---------------------------------------------------------------------------
def test_troubled_mechanic_spellburst_draws_draenei():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    mech = p1.summon("GDB_463")
    assert mech.divine_shield
    for c in list(p1.hand):
        c.discard()
    # Deck: one Draenei (drawable) + one non-Draenei that must stay.
    draenei = p1.give("GDB_131")
    draenei.zone = Zone.DECK
    other = p1.give(WISP)
    other.zone = Zone.DECK
    p1.give(MOONFIRE).play(target=p1.hero)  # trigger spellburst
    assert any(c.id == "GDB_131" for c in p1.hand)
    assert other.zone == Zone.DECK


# ---------------------------------------------------------------------------
# GDB_720 — Starlight Wanderer: Battlecry: The next Draenei you play gains
# +2/+1.
# The script buffs the next Draenei with GDB_720e1 but passes no atk/health and
# the enchant has no ATK/HEALTH tags in data -> the +2/+1 is never granted.
# CARD BUG.
# ---------------------------------------------------------------------------
def test_starlight_wanderer_buffs_next_draenei():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    wanderer = p1.give("GDB_720")
    wanderer.play()
    assert len(p1.next_draenei_hooks) == 1
    p1.used_mana = 0
    velen = p1.give("GDB_131")  # 7/7 Draenei
    velen.play()
    assert (velen.atk, velen.max_health) == (7 + 2, 7 + 1)
    assert p1.next_draenei_hooks == []


# ---------------------------------------------------------------------------
# GDB_722 — Crimson Commander: Battlecry and Deathrattle: Give all Draenei in
# your hand +1/+1.
# ---------------------------------------------------------------------------
def test_crimson_commander_buffs_draenei_in_hand():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    draenei = p1.give("GDB_131")  # 7/7 Draenei in hand
    nonD = p1.give(WISP)          # not a Draenei
    cmd = p1.give("GDB_722")
    cmd.play()
    assert (draenei.atk, draenei.max_health) == (7 + 1, 7 + 1)
    assert (nonD.atk, nonD.max_health) == (1, 1)  # unaffected
    # Deathrattle buffs hand Draenei again.
    cmd.destroy()
    game.process_deaths()
    assert (draenei.atk, draenei.max_health) == (7 + 2, 7 + 2)


# ---------------------------------------------------------------------------
# GDB_723 — Hologram Operator: Battlecry: Get 3 random Temporary Draenei.
# ---------------------------------------------------------------------------
def test_hologram_operator_gives_three_temporary_draenei():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    op = p1.give("GDB_723")
    op.play()
    got = list(p1.hand)
    assert len(got) == 3
    for c in got:
        assert Race.DRAENEI in c.races
        # Temporary: marked to vanish at end of turn (TEMPORARY tag).
        assert c.temporary


# ---------------------------------------------------------------------------
# GDB_860 — Starscale Constellar: Spellburst: Double this minion's Attack.
# ---------------------------------------------------------------------------
def test_starscale_constellar_spellburst_doubles_attack():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    constellar = p1.summon("GDB_860")  # 4/7
    assert constellar.atk == 4
    p1.give(MOONFIRE).play(target=p1.hero)
    assert constellar.atk == 8  # doubled


# ---------------------------------------------------------------------------
# GDB_861 — Stranded Spaceman: Battlecry: The next Draenei you play gains +2
# Health and Rush.
# ---------------------------------------------------------------------------
def test_stranded_spaceman_buffs_next_draenei_health_and_rush():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    spaceman = p1.give("GDB_861")
    spaceman.play()
    assert len(p1.next_draenei_hooks) == 1
    velen = p1.give("GDB_131")  # 7/7 Draenei
    velen.play()
    assert velen.atk == 7  # attack unchanged
    assert velen.max_health == 7 + 2
    assert velen.rush
    assert p1.next_draenei_hooks == []


# ---------------------------------------------------------------------------
# GDB_862 — Galactic Crusader: Taunt. Deathrattle: Get two random Holy spells.
# They cost (3) less.
# ---------------------------------------------------------------------------
def test_galactic_crusader_deathrattle_two_discounted_holy_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    from hearthstone.enums import SpellSchool

    crusader = p1.summon("GDB_862")
    assert crusader.taunt
    for c in list(p1.hand):
        c.discard()
    crusader.destroy()
    game.process_deaths()
    spells = [c for c in p1.hand if c.type == CardType.SPELL]
    assert len(spells) == 2
    for s in spells:
        assert s.data.spell_school == SpellSchool.HOLY
        assert s.cost == max(0, s.data.cost - 3)


# ---------------------------------------------------------------------------
# GDB_863 — Lunar Trailblazer: Battlecry: Set the Cost of a random spell in
# your hand to this minion's Cost.
# The script applies Buff(spell, "GDB_863e", cost=self.cost), which ADDS the
# minion's cost (+5) instead of SETTING the spell's cost. Pyroblast 10 -> 15
# rather than 5. CARD BUG ("set the Cost" implemented as "+Cost").
# ---------------------------------------------------------------------------
def test_lunar_trailblazer_sets_spell_cost_to_own_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    # Single spell in hand -> deterministic target. Pyroblast base cost 10.
    spell = p1.give(PYROBLAST)
    assert spell.cost == 10
    trailblazer = p1.give("GDB_863")  # 5-cost
    assert trailblazer.cost == 5
    trailblazer.play()
    # The spell's cost is set to Trailblazer's cost (5).
    assert spell.cost == 5


# ---------------------------------------------------------------------------
# GDB_874 — Astrobiologist: Battlecry: At the start of your next turn, Discover
# a spell.  (Enchant GDB_874e has no events -> effect not wired. CARD BUG.)
# ---------------------------------------------------------------------------
def test_astrobiologist_discovers_spell_next_turn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    if game.current_player is not p1:
        game.end_turn()
    assert game.current_player is p1
    bio = p1.give("GDB_874")
    bio.play()
    assert p1.choice is None  # nothing yet
    game.end_turn()  # p2's turn
    game.end_turn()  # back to p1: start-of-turn Discover should pop
    assert p1.choice is not None
    for cid in p1.choice.cards:
        assert _cards.db[cid].type == CardType.SPELL
    p1.choice.choose(p1.choice.cards[0])


# ---------------------------------------------------------------------------
# GDB_877 — Escape Pod: Rush. Deathrattle: Give adjacent minions +1/+1 and Rush.
# ---------------------------------------------------------------------------
def test_escape_pod_deathrattle_buffs_adjacent():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    left = p1.summon(WISP)        # 1/1
    pod = p1.summon("GDB_877")    # in the middle
    right = p1.summon(WISP)       # 1/1
    assert pod.rush
    pod.destroy()
    game.process_deaths()
    # Both neighbours gain +1/+1 and Rush.
    assert (left.atk, left.max_health) == (2, 2)
    assert left.rush
    assert (right.atk, right.max_health) == (2, 2)
    assert right.rush


# ---------------------------------------------------------------------------
# GDB_878 — Braingill: Battlecry: Give all friendly Murlocs "Deathrattle: Draw
# a card."
# ---------------------------------------------------------------------------
def test_braingill_gives_murlocs_draw_deathrattle():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    murloc = p1.summon(MURLOC)   # a friendly Murloc
    assert Race.MURLOC in murloc.races
    nonmurloc = p1.summon(WISP)
    braingill = p1.give("GDB_878")  # also a Murloc -> Braingill is a Murloc too
    braingill.play()
    # Deck has a card to draw on the deathrattle.
    seed = p1.give(WISP)
    seed.zone = Zone.DECK
    for c in list(p1.hand):
        c.discard()
    murloc.destroy()
    game.process_deaths()
    # The buffed Murloc's deathrattle drew a card.
    assert any(c.id == WISP for c in p1.hand)
    # Non-Murloc did NOT receive the deathrattle buff.
    assert not any(b.id == "GDB_878e" for b in nonmurloc.buffs)
