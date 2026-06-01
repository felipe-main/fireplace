"""The Lost City of Un'Goro mini-set (Dinosaurs, DINO_) — Mage card tests."""

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone

CHILLWIND_YETI = "CS2_182"  # 4/5 vanilla


def _resolve_choices(player, index=0):
    """Auto-resolve any pending Discover / choice by taking option `index`."""
    while player.choice:
        player.choice.choose(player.choice.cards[index])


# ---------------------------------------------------------------------------
# DINO_409 Techysaurus — Taunt. Costs (1) less for each card you played this
# game that didn't start in your deck.
# ---------------------------------------------------------------------------

def test_techysaurus_cost_reduction():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    techy = p1.give("DINO_409")
    # Base cost is 7, no out-of-deck cards played yet.
    assert techy.cost == 7
    assert techy.taunt is True

    # Play a card that actually STARTED in the deck — must NOT reduce cost.
    # Pull a real starting-deck minion into hand and play it.
    deck_minion = [
        c for c in list(p1.starting_deck)
        if c.type == CardType.MINION and (c.cost or 0) <= 10
    ][0]
    assert deck_minion._from_starting_deck is True
    deck_minion.zone = Zone.HAND
    deck_minion.play()
    assert techy.cost == 7

    # Play two cards that did NOT start in the deck (given straight to hand).
    p1.give(MOONFIRE).play(target=p1.hero)
    assert techy.cost == 6
    p1.give(THE_COIN).play()
    assert techy.cost == 5


# ---------------------------------------------------------------------------
# DINO_414 Tribute Dance — Choose a minion. Choose a different minion to
# transform it into.
# ---------------------------------------------------------------------------

def test_tribute_dance_transforms_into_other():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # First minion (to be transformed): a Wisp (1/1).
    victim = p1.summon(WISP)
    # Second minion (the form): a Kobold Geomancer (2/2).
    form = p2.summon(KOBOLD_GEOMANCER)

    dance = p1.give("DINO_414")
    dance.play(target=victim)
    # Auto-resolve the second-target ChoiceTarget by picking the Geomancer.
    while p1.choice:
        kobolds = [c for c in p1.choice.cards if c.id == KOBOLD_GEOMANCER]
        p1.choice.choose(kobolds[0])

    # The wisp is gone; a Kobold Geomancer now stands in its place under p1.
    new_minion = p1.field[0]
    assert new_minion.id == KOBOLD_GEOMANCER
    assert new_minion.atk == 2
    assert new_minion.health == 2
    assert victim.zone == Zone.SETASIDE
    # The form minion (p2's Geomancer) is untouched.
    assert form.zone == Zone.PLAY
    assert form.controller is p2


# ---------------------------------------------------------------------------
# DINO_429 Sheep Mask — Set a minion's stats to 1/1 and give it
# "Deathrattle: Deal 2 damage to all minions."
# ---------------------------------------------------------------------------

def test_sheep_mask_sets_stats_and_deathrattle():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # A beefy target so we can confirm the stats are SET (not buffed).
    target = p1.summon(CHILLWIND_YETI)  # 4/5
    assert target.atk == 4 and target.health == 5

    # Two bystander minions that must take 2 when the masked minion dies.
    by1 = p1.summon(TARGET_DUMMY)  # 0/2
    by2 = p2.summon(CHILLWIND_YETI)  # 4/5

    mask = p1.give("DINO_429")
    mask.play(target=target)
    # Stats SET to exactly 1/1.
    assert target.atk == 1
    assert target.health == 1

    # Kill the masked minion through the deathrattle pipeline.
    target.destroy()
    game.process_deaths()

    # Deathrattle: 2 damage to ALL minions.
    # by1 (0/2) takes 2 -> dies.
    assert by1.zone == Zone.GRAVEYARD
    # by2 (4/5) takes 2 -> 3 health.
    assert by2.health == 3
    assert by2.damage == 2
