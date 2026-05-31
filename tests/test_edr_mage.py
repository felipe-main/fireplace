"""Into the Emerald Dream — MAGE collectible card tests.

Covers all 10 collectible mage cards (EDR_430, EDR_517, EDR_519, EDR_520,
EDR_804, EDR_871, EDR_872, EDR_874, EDR_940, EDR_941). Assertions pin the
PRINTED card behaviour.
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone

import fireplace.cards as _cards


WISP = "EDR_851t"            # 0/1/1 Wisp token (Mage Imbue archetype)
YETI = "CS2_182"            # 4/4/5 vanilla Chillwind Yeti (deterministic body)
MOONFIRE = "CS2_008"        # 0-cost Moonfire (deal 1)
STARFIRE = "EX1_173"        # 6-cost Starfire (deal 5, draw)


# EDR_430 — Aessina — Battlecry: If 20 friendly minions have died this game,
# deal 20 damage split among all enemies.
def test_aessina_below_threshold_does_nothing():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.friendly_minions_died_this_game = 19
    p2.hero.set_current_health(30)
    p1.give("EDR_430").play()
    assert p2.hero.health == 30


def test_aessina_at_threshold_deals_20_to_face():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.friendly_minions_died_this_game = 20
    # No enemy minions: the only enemy character is the hero, so all 20
    # damage lands on its face.
    for m in list(p2.field):
        m.destroy()
    game.process_deaths()
    p2.hero.set_current_health(30)
    p1.give("EDR_430").play()
    assert p2.hero.health == 10
    assert len(p2.field) == 0


# EDR_517 — Q'onzu — Battlecry: Discover a spell. Choose to keep it or put it
# on top of your opponent's deck.
def test_qonzu_keep_puts_spell_in_hand():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.give("EDR_517").play()
    # First choice — Discover a spell.
    assert p1.choice
    discovered = p1.choice.cards[0]
    disc_id = discovered.id
    p1.choice.choose(discovered)
    # Second choice — keep vs send-to-opponent marker.
    assert p1.choice
    options = {c.id for c in p1.choice.cards}
    assert "EDR_517t" in options
    keep = [c for c in p1.choice.cards if c.id != "EDR_517t"][0]
    p1.choice.choose(keep)
    assert disc_id in [c.id for c in p1.hand]
    assert len(p2.deck) == 0


def test_qonzu_send_puts_spell_on_opponent_deck_top():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.give("EDR_517").play()
    discovered = p1.choice.cards[0]
    disc_id = discovered.id
    p1.choice.choose(discovered)
    marker = [c for c in p1.choice.cards if c.id == "EDR_517t"][0]
    p1.choice.choose(marker)
    assert len(p2.deck) == 1
    assert p2.deck[-1].id == disc_id
    assert disc_id not in [c.id for c in p1.hand]


# EDR_519 — Wisprider — Battlecry: Imbue your Hero Power, then trigger it.
def test_wisprider_imbues_and_triggers_wisp_power():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p2.hero.set_current_health(30)
    p1.give("EDR_519").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # Imbue installs Blessing of the Wisp (level 1): summon 2 Wisps, deal 2
    # damage split among all enemies. Triggering it once does exactly that.
    assert p1.imbues_this_game == 1
    assert p1.hero_power.id == "EDR_851p"
    wisps = [m for m in p1.field if m.id == WISP]
    assert len(wisps) == 2
    # 2 damage split; no enemy minions, so all 2 to face.
    assert p2.hero.health == 28


# EDR_520 — Forbidden Shrine — Spend all your Mana. Cast a random spell that
# costs that much.
def test_forbidden_shrine_spends_all_mana_and_casts():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    loc = p1.summon("EDR_520")
    assert loc.type == CardType.LOCATION
    p1.used_mana = 0
    p1.max_mana = 4
    assert p1.mana == 4
    loc.use()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    # All mana spent; the random spell cast costs exactly the spent amount.
    assert p1.mana == 0


# EDR_804 — Divination — Destroy a friendly Wisp to draw 3 cards.
def test_divination_destroys_wisp_and_draws_three():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    wisp = p1.summon(WISP)
    yeti = p1.summon("CS2_182")  # Chillwind Yeti — a friendly non-Wisp minion
    # Stock the deck so the three draws are real.
    for _ in range(5):
        c = p1.card("CS2_029")
        c.zone = Zone.DECK
    spell = p1.give("EDR_804")
    # Targeting is restricted to a friendly Wisp by NAME: the Wisp is valid,
    # the Yeti is not (REQ_TARGET_WITH_CARD_NAME).
    assert wisp in spell.play_targets
    assert yeti not in spell.play_targets
    pre_hand = len(p1.hand)
    spell.play(target=wisp)
    assert wisp.dead
    assert wisp.zone == Zone.GRAVEYARD
    assert not yeti.dead
    # Hand: -1 (Divination leaves hand) +3 (drawn) relative to pre-play count.
    assert len(p1.hand) == pre_hand - 1 + 3


# EDR_871 — Spirit Gatherer — Battlecry: Get a Wisp. Imbue your Hero Power.
def test_spirit_gatherer_gives_wisp_and_imbues():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("EDR_871").play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert p1.imbues_this_game == 1
    assert p1.hero_power.id == "EDR_851p"
    wisps_in_hand = [c for c in p1.hand if c.id == WISP]
    assert len(wisps_in_hand) == 1


# EDR_872 — Spark of Life — Choose One: Discover a Mage spell; or Discover a
# Druid spell.
def test_spark_of_life_mage_option_discovers_mage_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    spark = p1.give("EDR_872")
    assert [c.id for c in spark.choose_cards] == ["EDR_872A", "EDR_872B"]
    spark.play(choose="EDR_872A")
    assert p1.choice
    for c in p1.choice.cards:
        assert int(_cards.db[c.id].card_class) == int(CardClass.MAGE)
    pre_hand = len(p1.hand)
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == pre_hand + 1


def test_spark_of_life_druid_option_discovers_druid_spell():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    spark = p1.give("EDR_872")
    spark.play(choose="EDR_872B")
    assert p1.choice
    for c in p1.choice.cards:
        assert int(_cards.db[c.id].card_class) == int(CardClass.DRUID)
    pre_hand = len(p1.hand)
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == pre_hand + 1


# EDR_874 — Stellar Balance — Get a Moonfire and a Starfire. Give them Spell
# Damage +1.
def test_stellar_balance_gives_both_spells_with_buff():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.give("EDR_874").play()
    moonfires = [c for c in p1.hand if c.id == MOONFIRE]
    starfires = [c for c in p1.hand if c.id == STARFIRE]
    assert len(moonfires) == 1
    assert len(starfires) == 1
    # Spell Damage +1 rider applied as the EDR_874e enchant on each spell.
    assert [b.id for b in moonfires[0].buffs] == ["EDR_874e"]
    assert [b.id for b in starfires[0].buffs] == ["EDR_874e"]


# EDR_940 — Merry Moonkin — At the end of your turn, gain Armor (1 + Wisps you
# control).
def test_merry_moonkin_gains_armor_scaling_with_wisps():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("EDR_940")
    p1.summon(WISP)
    p1.summon(WISP)
    pre_armor = p1.hero.armor
    game.end_turn()
    # Base 1 Armor + 1 per Wisp you control (2 Wisps) = 3.
    assert p1.hero.armor - pre_armor == 3


def test_merry_moonkin_gains_one_armor_with_no_wisps():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("EDR_940")
    pre_armor = p1.hero.armor
    game.end_turn()
    assert p1.hero.armor - pre_armor == 1


# EDR_941 — Starsurge — Deal damage to a minion (1 + friendly minions that died
# this game).
def test_starsurge_scales_with_friendly_deaths():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.friendly_minions_died_this_game = 4
    tank = p2.summon(YETI)
    tank.max_health = 80
    tank.damage = 0
    p1.give("EDR_941").play(target=tank)
    # Base 1 + 4 deaths = 5 damage.
    assert tank.damage == 5


def test_starsurge_base_one_with_no_deaths():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    tank = p2.summon(YETI)
    tank.max_health = 80
    tank.damage = 0
    p1.give("EDR_941").play(target=tank)
    assert tank.damage == 1
