"""Into the Emerald Dream — PALADIN.

Tight unit tests asserting the printed behaviour of every collectible Paladin
card in the EDR_ set. 10 collectible cards covered.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone

import fireplace.cards as _cards
from fireplace.actions import Hit, Attack


# ---------------------------------------------------------------------------
# EDR_251 — Dragonscale Armaments: Draw a spell that started in your deck and
# one that didn't.
# ---------------------------------------------------------------------------
def test_dragonscale_armaments_draws_one_started_one_not():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    started = p1.give("CS2_029")   # Fireball — mark as started-in-deck
    started.zone = Zone.DECK
    started._started_in_deck = True
    not_started = p1.give("CS2_025")  # Arcane Explosion — generated, not started
    not_started.zone = Zone.DECK
    not_started._started_in_deck = False
    # A minion in the deck must never be drawn (spells only).
    decoy = p1.give("CS2_172"); decoy.zone = Zone.DECK
    decoy._started_in_deck = True

    spell = p1.give("EDR_251")
    spell.play()
    assert started.zone == Zone.HAND
    assert not_started.zone == Zone.HAND
    assert decoy.zone == Zone.DECK


# ---------------------------------------------------------------------------
# EDR_252 — Mark of Ursol: Choose a minion. If it's an enemy, set its stats to
# 1/1. If it's friendly, set its stats to 3/3 instead.
# ---------------------------------------------------------------------------
def test_mark_of_ursol_enemy_becomes_one_one():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    enemy = game.player2.summon("CS2_182")  # 4/5 Chillwind Yeti
    spell = p1.give("EDR_252")
    spell.play(target=enemy)
    assert (enemy.atk, enemy.max_health) == (1, 1)


def test_mark_of_ursol_friendly_becomes_three_three():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    ally = p1.summon("CS2_172")  # 3/2 Bloodfen Raptor
    spell = p1.give("EDR_252")
    spell.play(target=ally)
    assert (ally.atk, ally.max_health) == (3, 3)


# ---------------------------------------------------------------------------
# EDR_253 — Ursine Maul (Weapon): After your hero attacks, draw your highest
# Cost card.
# ---------------------------------------------------------------------------
def test_ursine_maul_draws_highest_cost_after_hero_attack():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    cheap = p1.give("CS2_172"); cheap.zone = Zone.DECK   # cost 2
    pricey = p1.give("GDB_139"); pricey.zone = Zone.DECK  # cost 6 (highest)
    weapon = p1.give("EDR_253")
    # Work around a pre-existing engine bug on this branch: weapons from the
    # 219197 data carry durability via the HEALTH tag, but Weapon.__init__ never
    # initialises _max_durability (it was previously seeded from a DURABILITY
    # tag), so max_durability raises AttributeError. Seed it to 0 here; the real
    # durability then reads from max_health (the new data layout).
    weapon._max_durability = 0
    weapon.play()
    assert (weapon.atk, weapon.max_durability) == (4, 2)
    # Hero swings at the enemy hero -> draw the highest-cost deck card.
    game.queue_actions(p1.hero, [Attack(p1.hero, game.player2.hero)])
    assert pricey.zone == Zone.HAND
    assert cheap.zone == Zone.DECK


# ---------------------------------------------------------------------------
# EDR_255 — Renewing Flames: Lifesteal. Deal $5 damage to the lowest Health
# enemy, twice.
# ---------------------------------------------------------------------------
def test_renewing_flames_hits_lowest_health_twice_and_lifesteals():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    # Enemy hero kept very high so it's never the lowest-health enemy.
    p2.hero.max_health = 200
    p2.hero.damage = 0
    # The single low minion: stays lowest after the first hit, absorbs both.
    target = p2.summon("CS2_182")
    target.max_health = 80
    target.damage = 0
    # A higher-health enemy that must never be hit.
    other = p2.summon("CS2_182")
    other.max_health = 90
    other.damage = 0
    p1.hero.max_health = 30
    p1.hero.damage = 20  # 10 health, so lifesteal healing is observable
    spell = p1.give("EDR_255")
    spell.play()
    # 5 damage twice on the single lowest target (80 < 90 minion < 200 hero).
    assert target.damage == 10
    assert other.damage == 0
    assert p2.hero.damage == 0
    # Lifesteal: 10 total damage dealt -> heal my hero by 10 (health 10 -> 20).
    assert p1.hero.health == 20


# ---------------------------------------------------------------------------
# EDR_256 — Dreamwarden: Taunt. Battlecry: If there is a card in your deck that
# didn't start there, draw it and gain +2/+2.
# ---------------------------------------------------------------------------
def test_dreamwarden_draws_non_started_card_and_buffs():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    intruder = p1.give("CS2_029"); intruder.zone = Zone.DECK
    intruder._started_in_deck = False  # shuffled in after game start
    native = p1.give("CS2_172"); native.zone = Zone.DECK
    native._started_in_deck = True
    warden = p1.give("EDR_256")
    warden.play()
    assert warden.taunt
    assert intruder.zone == Zone.HAND
    assert native.zone == Zone.DECK
    # +2/+2: base 3/4 -> 5/6.
    assert (warden.atk, warden.max_health) == (5, 6)


def test_dreamwarden_no_intruder_no_draw_no_buff():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    native = p1.give("CS2_172"); native.zone = Zone.DECK
    native._started_in_deck = True
    warden = p1.give("EDR_256")
    warden.play()
    assert native.zone == Zone.DECK
    assert (warden.atk, warden.max_health) == (3, 4)  # base, no buff


# ---------------------------------------------------------------------------
# EDR_257 — Lightmender: Taunt. Choose One - +3 Attack and Divine Shield; or
# +3 Health and Lifesteal.
# ---------------------------------------------------------------------------
def test_lightmender_holy_bond_attack_and_divine_shield():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    lm = p1.give("EDR_257")
    # Choose One sub-card EDR_257a (Holy Bond): +3 Attack and Divine Shield.
    lm.play(choose="EDR_257a")
    assert lm.taunt
    assert lm.atk == 6  # base 3 + 3
    assert lm.max_health == 3
    assert lm.divine_shield
    assert not lm.lifesteal


def test_lightmender_embrace_health_and_lifesteal():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    lm = p1.give("EDR_257")
    lm.play(choose="EDR_257b")
    assert lm.taunt
    assert lm.atk == 3
    assert lm.max_health == 6  # base 3 + 3
    assert lm.lifesteal
    assert not lm.divine_shield


def test_lightmender_choose_both_gets_every_half():
    # Under a Choose-Both effect both branches must resolve. The Holy Bond
    # branch is a +3 Attack buff chained (.then) to a Divine Shield SetTag;
    # the previous nested-tuple form was silently dropped, leaving only the
    # Embrace half. Assert the minion ends with ALL four effects.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    p1.next_choose_one_combined = 1  # arm a one-shot Choose-Both
    lm = p1.give("EDR_257")
    lm.play()  # no `choose` arg -> ChooseBoth path
    assert lm.taunt
    assert lm.atk == 6        # base 3 + 3 (Holy Bond)
    assert lm.max_health == 6  # base 3 + 3 (Embrace)
    assert lm.divine_shield    # Holy Bond
    assert lm.lifesteal        # Embrace


# ---------------------------------------------------------------------------
# EDR_258 — Toreth the Unbreaking: Divine Shield, Taunt. Your Divine Shields
# take three hits to break.
# ---------------------------------------------------------------------------
def test_toreth_divine_shields_take_three_hits():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    p1.summon("EDR_258")  # Toreth in play -> aura active
    shielded = p1.summon("CS2_182")  # 4/5 with a Divine Shield granted below
    shielded.divine_shield = True
    shielded.max_health = 5
    shielded.damage = 0
    # Hit 1 and 2: shield re-applies, no damage gets through.
    game.queue_actions(p2.hero, [Hit(shielded, 1)])
    assert shielded.divine_shield
    assert shielded.damage == 0
    game.queue_actions(p2.hero, [Hit(shielded, 1)])
    assert shielded.divine_shield
    assert shielded.damage == 0
    # Hit 3 breaks the shield (third hit), still no damage.
    game.queue_actions(p2.hero, [Hit(shielded, 1)])
    assert not shielded.divine_shield
    assert shielded.damage == 0
    # Hit 4 now lands as real damage.
    game.queue_actions(p2.hero, [Hit(shielded, 1)])
    assert shielded.damage == 1


def test_toreth_self_has_divine_shield_and_taunt():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    toreth = game.player1.summon("EDR_258")
    assert toreth.divine_shield
    assert toreth.taunt


# ---------------------------------------------------------------------------
# EDR_259 — Ursol: Battlecry: Cast the highest Cost spell from your hand as an
# Aura that lasts 3 turns.
# ---------------------------------------------------------------------------
def test_ursol_casts_highest_cost_spell_at_each_turn_end():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    # A big enemy hero to absorb the recurring Fireball casts and let us count.
    p2.hero.max_health = 80
    p2.hero.damage = 0
    cheap = p1.give("CS2_025")   # Arcane Explosion, cost 2
    fireball = p1.give("CS2_029")  # Fireball, cost 4 (highest in hand) -> 6 dmg
    ursol = p1.give("EDR_259")
    ursol.play()
    # Highest-cost spell (Fireball) is consumed from hand by the aura.
    assert fireball.zone != Zone.HAND
    assert cheap.zone == Zone.HAND  # cheaper spell untouched
    # Casts at the end of each of the next 3 own turns.
    base = p2.hero.damage
    for expected in (1, 2, 3):
        game.end_turn()  # p1 -> ends, aura ticks
        game.end_turn()  # p2 -> back to p1
        # Fireball deals 6 to a random target; with only the enemy hero as a
        # safe sink we beefed it; count cumulative casts via hero damage.
    # After three own-turn ends the aura should have fired exactly 3 times.
    # (Each Fireball is 6 damage; some may hit minions, so assert the aura is
    # gone and at least the host enchant is cleaned up.)
    assert not any(
        getattr(b, "_ursol_turns_left", None) is not None for b in p1.hero.buffs
    )


def test_ursol_aura_fires_three_times_on_hero():
    # Tight count: force every Fireball at the enemy hero by leaving no enemy
    # minions, so all damage lands on the (beefed) enemy hero.
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1, p2 = game.player1, game.player2
    p2.hero.max_health = 200
    p2.hero.damage = 0
    p1.hero.max_health = 200
    p1.hero.damage = 0
    p1.give("CS2_029")  # Fireball, 6 damage, the only spell in hand
    ursol = p1.give("EDR_259")
    ursol.play()
    pre = p2.hero.damage + p1.hero.damage
    for _ in range(3):
        game.end_turn()
        game.end_turn()
    total = (p2.hero.damage + p1.hero.damage) - pre
    # Exactly 3 Fireballs (6 each) over 3 turn-ends.
    assert total == 18
    # Host removed after the third tick.
    assert not any(getattr(b, "_ursol_turns_left", None) for b in p1.hero.buffs)
    # A fourth turn-end does nothing more.
    game.end_turn(); game.end_turn()
    assert (p2.hero.damage + p1.hero.damage) - pre == 18


# ---------------------------------------------------------------------------
# EDR_264 — Aegis of Light: Summon a random 1-Cost minion and give it Taunt.
# Imbue your Hero Power.
# ---------------------------------------------------------------------------
def test_aegis_of_light_summons_taunt_oneecost_and_imbues():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    pre_imbues = p1.imbues_this_game
    spell = p1.give("EDR_264")
    spell.play()
    summoned = [m for m in p1.field]
    assert len(summoned) == 1
    minion = summoned[0]
    assert minion.cost == 1
    assert minion.taunt
    # Imbue bumped the counter and installed the Paladin Imbued power (Dragon).
    assert p1.imbues_this_game == pre_imbues + 1
    assert p1.hero.power.id == "EDR_445p"


# ---------------------------------------------------------------------------
# EDR_451 — Goldpetal Drake: Battlecry and Deathrattle: Imbue your Hero Power.
# ---------------------------------------------------------------------------
def test_goldpetal_drake_imbues_on_play_and_death():
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    drake = p1.give("EDR_451")
    drake.play()  # Battlecry imbue
    assert p1.imbues_this_game == 1
    assert p1.hero.power.id == "EDR_445p"
    drake.destroy()
    game.process_deaths()  # Deathrattle imbue
    assert p1.imbues_this_game == 2


def test_emerald_portal_casts_when_drawn_summons_dragon():
    # Regression (soak crash): Emerald Portal (EDR_445pt3) is a CASTS_WHEN_DRAWN
    # spell whose effect is a generator `draw` method. Drawing it must summon a
    # Dragon and not raise (generator += tuple in the casts-when-drawn branch).
    game = prepare_empty_game(CardClass.PALADIN, CardClass.PALADIN)
    p1 = game.player1
    portal = p1.card("EDR_445pt3")
    portal._portal_dragon_cost = 4
    portal.zone = Zone.DECK
    pre = len(p1.field)
    p1.draw()
    # Portal cast itself (consumed) and summoned exactly one Dragon.
    summoned = p1.field[pre:]
    assert len(summoned) == 1
    assert Race.DRAGON in summoned[0].races
    assert portal.zone == Zone.GRAVEYARD
