from utils import *

from hearthstone.enums import CardClass, CardSet, CardType, Race, Zone, GameTag

import fireplace.cards as cards_module

# First-edition Demon Hunter pool = Ashes of Outland (BLACK_TEMPLE) +
# Demon Hunter Initiate.
FIRST_EDITION_DH_SETS = {CardSet.BLACK_TEMPLE, CardSet.DEMON_HUNTER_INITIATE}


# ---------------------------------------------------------------------------
# TOY_028 — Spirit of the Team
#   2/0/3 Undead. Stealth for 1 turn. Your hero has +2 Attack on your turn.
# ---------------------------------------------------------------------------
def test_toy_028_spirit_of_the_team():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    minion = game.player1.give("TOY_028")
    minion.play()
    # Stealth present on summon.
    assert minion.stealthed
    # Hero gets +2 Attack while it's our turn.
    assert game.player1.hero.atk == 2
    # Opponent's turn: aura off, stealth dropped at start of our next turn.
    game.end_turn()
    assert game.player2.hero.atk == 0  # sanity: opponent unaffected
    assert game.player1.hero.atk == 0  # aura only on our turn
    game.end_turn()  # back to player1 — OWN_TURN_BEGIN drops stealth
    assert not minion.stealthed
    assert game.player1.hero.atk == 2


# ---------------------------------------------------------------------------
# TOY_640 — Workshop Mishap
#   4-cost Fel spell. Deal 5 damage to a minion. Excess damages both neighbors.
#   Outcast: Gain Lifesteal.
# ---------------------------------------------------------------------------
def test_toy_640_workshop_mishap_excess_to_neighbours():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    # Three enemy minions in a row. Center has 3 health -> 5 dmg = 2 excess.
    left = game.player2.summon("CS2_182")    # Chillwind Yeti 4/5
    center = game.player2.summon("CS2_120")  # River Crocolisk 2/3
    right = game.player2.summon("CS2_182")
    left.max_health = 50
    left.damage = 0
    right.max_health = 50
    right.damage = 0
    assert center.health == 3

    spell = game.player1.give("TOY_640")
    # Push spell to interior so it's NOT left/right-most (no Outcast).
    game.player1.hand[:] = []
    fillerL = game.player1.give("CS2_171")
    game.player1.give("TOY_640")
    spell = game.player1.hand[-1]
    fillerR = game.player1.give("CS2_171")
    assert game.player1.hand[0] is not spell
    assert game.player1.hand[-1] is not spell
    spell.play(target=center)

    # Center took full 5 -> dead.
    assert center.zone == Zone.GRAVEYARD
    # Excess = 5 - 3 = 2 to each neighbour.
    assert left.damage == 2
    assert right.damage == 2


def test_toy_640_no_excess_no_neighbour_damage():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    left = game.player2.summon("CS2_182")
    center = game.player2.summon("CS2_182")  # 4/5, 5 health exactly
    right = game.player2.summon("CS2_182")
    left.max_health = 50
    left.damage = 0
    right.max_health = 50
    right.damage = 0
    assert center.health == 5

    spell = game.player1.give("TOY_640")
    spell.play(target=center)
    # 5 dmg to 5 health -> dead, zero excess -> neighbours untouched.
    assert center.zone == Zone.GRAVEYARD
    assert left.damage == 0
    assert right.damage == 0


def test_toy_640_outcast_grants_lifesteal():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    target = game.player2.summon("CS2_182")  # 4/5
    target.max_health = 50
    target.damage = 0
    game.player1.hero.damage = 10
    pre_hero_hp = game.player1.hero.health

    spell = game.player1.give("TOY_640")
    # Spell is right-most in hand -> Outcast active.
    assert game.player1.hand[-1] is spell
    spell.play(target=target)

    assert target.damage == 5
    # Lifesteal heals the hero for the damage dealt (5).
    assert game.player1.hero.health == pre_hero_hp + 5


# ---------------------------------------------------------------------------
# TOY_641 — Umpire's Grasp
#   3/3/2 Weapon. Deathrattle: Draw a Demon and reduce its Cost by (2).
# ---------------------------------------------------------------------------
def test_toy_641_umpires_grasp_draws_demon_cost_reduced():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    # Empty the deck so only the planted Demon can be drawn.
    game.player1.deck[:] = []
    demon = game.player1.card("EX1_319", zone=Zone.DECK)  # Flame Imp 1/3/2 Demon
    base_cost = demon.cost  # 1
    weapon = game.player1.give("TOY_641")
    weapon.play()
    pre_hand = len(game.player1.hand)
    # Destroy weapon -> deathrattle.
    weapon.destroy()
    assert demon.zone == Zone.HAND
    assert len(game.player1.hand) == pre_hand + 1
    assert demon.cost == max(0, base_cost - 2)


# ---------------------------------------------------------------------------
# TOY_642 — Ball Hog
#   4/3/3 Quilboar. Lifesteal. Battlecry & Deathrattle: Deal 3 to lowest-Health enemy.
# ---------------------------------------------------------------------------
def test_toy_642_ball_hog_battlecry_lowest_health_lifesteal():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    # Raise enemy hero HP so a minion is the lowest-Health enemy character.
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0
    high = game.player2.summon("CS2_182")  # 4/5
    high.max_health = 50
    high.damage = 0
    low = game.player2.summon("CS2_182")   # make it the lowest-Health enemy
    low.max_health = 4
    low.damage = 0                          # 4 health -> survives 3 dmg, stays lowest
    game.player1.hero.damage = 10
    pre_hero_hp = game.player1.hero.health

    ballhog = game.player1.give("TOY_642")
    ballhog.play()
    # Battlecry hits lowest-health enemy (low) for 3; it survives so damage reads 3.
    assert low.zone == Zone.PLAY
    assert low.damage == 3
    assert high.damage == 0
    # Lifesteal heals controller hero for 3.
    assert game.player1.hero.health == pre_hero_hp + 3


def test_toy_642_ball_hog_deathrattle():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    game.player2.hero.max_health = 80
    game.player2.hero.damage = 0
    enemy = game.player2.summon("CS2_182")  # lowest-Health enemy character
    enemy.max_health = 50
    enemy.damage = 0
    ballhog = game.player1.summon("TOY_642")  # summon -> no battlecry
    assert enemy.damage == 0
    game.player1.hero.damage = 10
    pre_hp = game.player1.hero.health
    ballhog.destroy()
    assert enemy.damage == 3
    assert game.player1.hero.health == pre_hp + 3


# ---------------------------------------------------------------------------
# TOY_643 — Blind Box
#   2-cost spell. Get 2 random Demons. Outcast: Discover them instead.
# ---------------------------------------------------------------------------
def test_toy_643_blind_box_base_gets_two_demons():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    game.player1.hand[:] = []
    # Push spell to interior so it's NOT left/right-most (no Outcast).
    game.player1.give("CS2_171")  # Stonetusk Boar (not a demon)
    spell = game.player1.give("TOY_643")
    game.player1.give("CS2_171")
    assert game.player1.hand[0] is not spell
    assert game.player1.hand[-1] is not spell
    pre_hand = len(game.player1.hand)
    spell.play()
    # No choice should appear (base mode).
    assert not game.player1.choice
    # Spell consumed; +2 demons in hand -> net +1.
    assert len(game.player1.hand) == pre_hand - 1 + 2
    demons = [c for c in game.player1.hand if Race.DEMON in c.races]
    assert len(demons) == 2


def test_toy_643_blind_box_outcast_discovers_twice():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    game.player1.hand[:] = []
    spell = game.player1.give("TOY_643")  # only card -> Outcast
    spell.play()
    # Outcast: two Discovers fire in sequence.
    choices_seen = 0
    while game.player1.choice:
        choices_seen += 1
        cards = game.player1.choice.cards
        assert len(cards) == 3
        assert all(Race.DEMON in c.races for c in cards)
        game.player1.choice.choose(cards[0])
    assert choices_seen == 2
    demons = [c for c in game.player1.hand if Race.DEMON in getattr(c, "races", [])]
    assert len(demons) == 2


# ---------------------------------------------------------------------------
# TOY_644 — Red Card
#   1-cost spell. Make a minion go Dormant for 2 turns.
# ---------------------------------------------------------------------------
def test_toy_644_red_card_dormant():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    target = game.player2.summon("CS2_182")
    spell = game.player1.give("TOY_644")
    spell.play(target=target)
    assert target.dormant
    assert target.dormant_turns == 2


# ---------------------------------------------------------------------------
# TOY_645 — Lesser Opal Spellstone (and upgrade chain)
#   Draw 1. Attack with hero 4 times to upgrade -> Opal (draw 2) -> Greater (draw 3).
# ---------------------------------------------------------------------------
def test_toy_645_lesser_opal_draws_one():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    for _ in range(5):
        game.player1.card("CS2_171", zone=Zone.DECK)
    spell = game.player1.give("TOY_645")
    pre = len(game.player1.hand)
    spell.play()
    # Draw 1 -> spell gone (-1) + draw (+1) = net 0.
    assert len(game.player1.hand) == pre


def test_toy_645t_opal_draws_two():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    for _ in range(5):
        game.player1.card("CS2_171", zone=Zone.DECK)
    spell = game.player1.give("TOY_645t")
    pre = len(game.player1.hand)
    spell.play()
    # net +1
    assert len(game.player1.hand) == pre + 1


def test_toy_645t1_greater_opal_draws_three():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    for _ in range(5):
        game.player1.card("CS2_171", zone=Zone.DECK)
    spell = game.player1.give("TOY_645t1")
    pre = len(game.player1.hand)
    spell.play()
    # net +2
    assert len(game.player1.hand) == pre + 2


def test_toy_645_upgrades_after_four_hero_attacks():
    # Printed text: "Attack with your hero 4 times to upgrade." AddProgress ticks
    # +1 per hero attack and progress_total = 4, so the spellstone upgrades on
    # the 4th attack — not before.
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    spell = game.player1.give("TOY_645")
    weapon = game.player1.give("CS2_106")  # Fiery War Axe 3/2
    weapon.play()
    weapon.max_durability = 50
    weapon.damage = 0
    enemy = game.player2.hero
    enemy.max_health = 80
    enemy.damage = 0

    # First 3 attacks: still Lesser, no upgrade.
    for _ in range(3):
        game.player1.hero.num_attacks = 0
        game.player1.hero.attack(enemy)
        assert any(c.id == "TOY_645" for c in game.player1.hand)
        assert not any(c.id == "TOY_645t" for c in game.player1.hand)
    # 4th attack upgrades to TOY_645t (Opal Spellstone).
    game.player1.hero.num_attacks = 0
    game.player1.hero.attack(enemy)
    assert any(c.id == "TOY_645t" for c in game.player1.hand)
    assert not any(c.id == "TOY_645" for c in game.player1.hand)


# ---------------------------------------------------------------------------
# TOY_647 — Magtheridon, Unreleased
#   8/12/12 Mech/Demon. Dormant for 2 turns; while Dormant deal 3 to all enemies
#   at end of your turn.
# ---------------------------------------------------------------------------
def test_toy_647_magtheridon_dormant_and_pings():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    mag = game.player1.summon("TOY_647")
    assert mag.dormant
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    enemy_hero = game.player2.hero
    enemy_hero.max_health = 80
    enemy_hero.damage = 0
    # End of our turn while dormant -> 3 to all enemies.
    game.end_turn()
    assert enemy.damage == 3
    assert enemy_hero.damage == 3


def test_toy_647_magtheridon_awakens_after_two_turns():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    mag = game.player1.summon("TOY_647")
    assert mag.dormant
    game.end_turn()  # p1 end (turn 1 dormant)
    game.end_turn()  # p2 end -> back to p1
    game.end_turn()  # p1 end (turn 2 dormant)
    game.end_turn()  # back to p1 again -> should be awake now
    assert not mag.dormant


# ---------------------------------------------------------------------------
# TOY_652 — Window Shopper
#   5/6/5 Demon. Miniaturize. Battlecry: Discover a Demon. Set its stats & Cost
#   to this minion's.
# ---------------------------------------------------------------------------
def test_toy_652_window_shopper_sets_stats_to_5_6_5():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    shopper = game.player1.give("TOY_652")
    shopper.play()
    assert game.player1.choice
    picked = game.player1.choice.cards[0]
    game.player1.choice.choose(picked)
    # The given card is now in hand with stats set to 6/5 and cost 5.
    given = [c for c in game.player1.hand if c.id == picked.id]
    assert given, "discovered demon should be in hand"
    card = given[0]
    assert card.atk == 6
    assert card.health == 5
    assert card.cost == 5


def test_toy_652t_window_shopper_mini_sets_stats_to_1_1_1():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    mini = game.player1.give("TOY_652t")
    mini.play()
    assert game.player1.choice
    picked = game.player1.choice.cards[0]
    game.player1.choice.choose(picked)
    card = [c for c in game.player1.hand if c.id == picked.id][0]
    assert card.atk == 1
    assert card.health == 1
    assert card.cost == 1


# ---------------------------------------------------------------------------
# TOY_913 — Ci'Cigi
#   4/4/3. Deathrattle: Get 3 random first-edition Demon Hunter cards.
# ---------------------------------------------------------------------------
def test_toy_913_cicigi_deathrattle_three_dh_cards():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    cici = game.player1.summon("TOY_913")
    pre = len(game.player1.hand)
    cici.destroy()
    # Exactly 3 cards added.
    assert len(game.player1.hand) == pre + 3
    new = game.player1.hand[-3:]
    valid_sets = {int(s) for s in FIRST_EDITION_DH_SETS}
    for c in new:
        # Each card is a Demon Hunter card...
        assert CardClass.DEMONHUNTER in c.data.classes
        # ...and comes from the first-edition pool (Ashes of Outland /
        # Demon Hunter Initiate), not any modern DH set.
        assert int(cards_module.db[c.id].card_set) in valid_sets
