"""The Great Dark Beyond — engine-primitive smoke tests.

Exercises the new engine mechanics in isolation (not any specific card's full
script): the Draenei tribe selector, the "next Draenei you play" hooks/discount,
and the Starship bank-on-death / launch flow.
"""

from utils import *

from hearthstone.enums import Race, Zone

from fireplace.actions import Hit, Destroy, Deaths, LaunchStarship
from fireplace.cards.utils import DRAENEI


def test_draenei_selector_matches_draenei_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    velen = p1.summon("GDB_131")  # Velen, Leader of the Exiled (Draenei)
    wisp = p1.summon(WISP)        # not a Draenei
    matched = DRAENEI.eval(p1.field, p1)
    assert velen in matched
    assert wisp not in matched
    assert Race.DRAENEI in velen.races


def test_next_draenei_hook_fires_on_play_only():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.max_mana = 10
    p1.used_mana = 0
    fired = []
    p1.next_draenei_hooks.append(lambda m: fired.append(m.id))
    # Summoning a Draenei must NOT consume the hook (only *playing* does).
    p1.summon(WISP)
    assert fired == []
    # Playing a Draenei fires and clears every pending hook.
    velen = p1.give("GDB_131")
    velen.play()
    while p1.choice:
        p1.choice.choose(p1.choice.cards[0])
    assert fired == ["GDB_131"]
    assert p1.next_draenei_hooks == []


def test_next_draenei_discount_reduces_next_draenei_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    velen = p1.give("GDB_131")
    base = p1.card("GDB_131").cost
    p1.next_draenei_discount = 2
    assert velen.cost == base - 2
    # A non-Draenei is unaffected.
    fireball = p1.give("CS2_029")
    assert fireball.cost == p1.card("CS2_029").cost


def test_starship_banks_pieces_on_death_then_launches():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # Mage has no class ship -> the neutral "The Exile's Hope" (GDB_100t2).
    piece1 = p1.summon("GDB_100")  # 3/4 Taunt, Deathrattle, Starship Piece
    piece2 = p1.summon("GDB_101")  # 2/2 Divine Shield, Starship Piece
    a1, h1 = p1.card("GDB_100").atk, p1.card("GDB_100").health
    a2, h2 = p1.card("GDB_101").atk, p1.card("GDB_101").health

    assert p1.starship is None
    piece1.destroy()
    game.process_deaths()
    ship = p1.starship
    assert p1.is_building_starship
    assert ship.id == "GDB_100t2"
    # Building ship is an untouchable Permanent carrying the running stats.
    assert ship.dormant
    assert ship.cant_be_damaged
    assert (ship.atk, ship.max_health) == (a1, h1)

    piece2.destroy()
    game.process_deaths()
    assert (ship.atk, ship.max_health) == (a1 + a2, h1 + h2)
    assert len(ship._starship_pieces) == 2


def test_starship_permanent_is_immune_and_indestructible_while_building():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    piece = p1.summon("GDB_100")
    piece.destroy()
    game.process_deaths()
    ship = p1.starship
    # AoE damage is fully absorbed.
    game.queue_actions(p1.hero, [Hit(p1.field, 10)])
    game.process_deaths()
    assert ship.zone == Zone.PLAY
    assert ship.damage == 0
    # Destroy effects skip the dormant Permanent.
    game.queue_actions(p1.hero, [Destroy(ship), Deaths()])
    assert ship.zone == Zone.PLAY
    assert p1.is_building_starship


def test_starship_launch_combines_stats_and_keywords():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.summon("GDB_100").destroy()  # Taunt piece
    game.process_deaths()
    p1.summon("GDB_101").destroy()  # Divine Shield piece
    game.process_deaths()
    ship = p1.starship
    a = p1.card("GDB_100").atk + p1.card("GDB_101").atk
    h = p1.card("GDB_100").health + p1.card("GDB_101").health

    game.queue_actions(p1.hero, [LaunchStarship(p1)])
    # Launched: a real, attackable minion with combined stats + keywords.
    assert not p1.is_building_starship
    assert not ship.dormant
    assert not ship.cant_be_damaged
    assert (ship.atk, ship.max_health) == (a, h)
    assert ship.taunt          # from GDB_100
    assert ship.divine_shield  # from GDB_101


def test_starship_class_token_resolves_by_hero_class():
    # Rogue has a unique ship: The Scavenger's Will (GDB_100t8).
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.summon("GDB_100").destroy()
    game.process_deaths()
    assert p1.starship.id == "GDB_100t8"


# Heroes of StarCraft — faction (Protoss/Terran/Zerg GameTag) primitives.

def test_faction_selectors_match_faction_tagged_cards():
    from fireplace.cards.utils import PROTOSS, ZERG
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    colossus = p1.summon("SC_758")  # Protoss
    zergling = p1.summon("SC_010")  # Zerg
    assert colossus in PROTOSS.eval(p1.field, p1)
    assert zergling not in PROTOSS.eval(p1.field, p1)
    assert zergling in ZERG.eval(p1.field, p1)
    assert colossus not in ZERG.eval(p1.field, p1)


def test_protoss_cost_reduction_is_per_game_and_minion_scoped():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    colossus = p1.give("SC_758")          # Protoss minion, base 12
    spell = p1.give("SC_759")             # Protoss spell, base 2
    fireball = p1.give("CS2_029")         # non-Protoss
    p1.protoss_cost_reduction = 3
    assert colossus.cost == 12 - 3        # minion gets the per-game discount
    assert spell.cost == 2                # spell does NOT (minion-scoped)
    assert fireball.cost == p1.card("CS2_029").cost


def test_next_protoss_minion_discount_only_minions():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    colossus = p1.give("SC_758")
    spell = p1.give("SC_759")
    p1.next_protoss_minion_discount = 3
    assert colossus.cost == 12 - 3
    assert spell.cost == 2                # spell unaffected


def test_next_protoss_spell_discount_only_spells():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    colossus = p1.give("SC_758")
    spell = p1.give("SC_759")
    p1.next_protoss_spell_discount = 2
    assert spell.cost == 2 - 2
    assert colossus.cost == 12           # minion unaffected


def test_next_protoss_card_discount_any_type():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    colossus = p1.give("SC_758")
    spell = p1.give("SC_759")
    fireball = p1.give("CS2_029")        # non-Protoss
    p1.next_protoss_card_discount = 2
    assert colossus.cost == 12 - 2
    assert spell.cost == 2 - 2
    assert fireball.cost == p1.card("CS2_029").cost


def test_starship_launch_discount_reduces_launch_button():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    launch = p1.give("GDB_905")          # Launch Starship, base 5
    p1.starship_launch_discount = 2
    assert launch.cost == 5 - 2
