"""Firelands mini-set — WARLOCK collectible card tests.

Covers the three Firelands Warlock cards:
  FIR_924 Shadowflame Stalker, FIR_954 Conflagrate, FIR_955 Emberroot Destroyer.
"""

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone


WISP = "CS2_231"
CHILLWIND = "CS2_182"  # Chillwind Yeti 4/5 (no deathrattle)


# The eight-keyword Dark Gift (Bonus Effect) pool — a Dark-Gift card grants
# exactly one of these.
_GIFT_TAGS = (
    GameTag.TAUNT,
    GameTag.WINDFURY,
    GameTag.DIVINE_SHIELD,
    GameTag.POISONOUS,
    GameTag.CANT_BE_TARGETED_BY_SPELLS,
    GameTag.RUSH,
    GameTag.LIFESTEAL,
    GameTag.REBORN,
)


# ---------------------------------------------------------------------------
# FIR_924 — Shadowflame Stalker: Battlecry: Discover a Demon with a Dark Gift.
# Get a copy of it. (4/4/3)
# ---------------------------------------------------------------------------
def test_shadowflame_stalker_discovers_demon_with_dark_gift():
    from random import Random

    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    game.random = Random(0)
    p1 = game.player1
    pre_hand = len(p1.hand)

    stalker = p1.give("FIR_924")
    stalker.play()

    assert p1.choice is not None
    # Every offered card is a Demon minion.
    for card in p1.choice.cards:
        assert card.type == CardType.MINION
        assert card.races and Race.DEMON in card.races

    chosen = p1.choice.cards[0]
    base_tags = {t for t in _GIFT_TAGS if chosen.data.tags.get(t)}
    p1.choice.choose(chosen)

    # The chosen Demon copy lands in hand...
    assert chosen.zone == Zone.HAND
    assert len(p1.hand) == pre_hand + 1
    assert Race.DEMON in chosen.races

    # ...carrying exactly one new Dark-Gift keyword (recorded on the minion).
    live_tags = {t for t in _GIFT_TAGS if chosen.tags.get(t)}
    granted = live_tags - base_tags
    assert len(granted) == 1
    assert len(getattr(chosen, "_dark_gifts", [])) == 1


# ---------------------------------------------------------------------------
# FIR_954 — Conflagrate: Deal $5 damage to a minion. Its owner draws a card.
# (1-mana spell)
# ---------------------------------------------------------------------------
def test_conflagrate_damages_minion_and_owner_draws():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2

    # Enemy target with enough health to survive 5 damage so we can assert the
    # exact post-damage value.
    target = p2.summon(CHILLWIND)  # 4/5
    target.max_health = 20
    target.damage = 0

    # Stack p2's deck so the draw is deterministic and observable.
    p2.deck = []
    drawn_card = p2.give(WISP)
    drawn_card.shuffle_into_deck()
    pre_p2_hand = len(p2.hand)

    spell = p1.give("FIR_954")
    spell.play(target=target)

    # Exactly 5 damage to the targeted minion.
    assert target.damage == 5
    assert target.zone == Zone.PLAY

    # The TARGET's owner (p2) drew exactly one card; p1 did not draw.
    assert drawn_card.zone == Zone.HAND
    assert len(p2.hand) == pre_p2_hand + 1


# ---------------------------------------------------------------------------
# FIR_955 — Emberroot Destroyer: Whenever your hero takes damage on your turn,
# deal 3 damage to a random enemy minion. (3/3/3)
# ---------------------------------------------------------------------------
def test_emberroot_destroyer_fires_on_own_turn_hero_damage():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2

    destroyer = p1.summon("FIR_955")
    assert destroyer.atk == 3 and destroyer.max_health == 3

    # Single enemy minion that survives one 3-damage tick exactly.
    enemy = p2.summon(CHILLWIND)  # 4/5
    enemy.max_health = 30
    enemy.damage = 0

    # On p1's own turn, damaging p1's hero triggers the effect.
    game.queue_actions(p1.hero, [Hit(p1.hero, 1)])
    assert enemy.damage == 3


def test_emberroot_destroyer_silent_on_opponent_turn():
    game = prepare_game(CardClass.WARLOCK, CardClass.WARLOCK)
    p1, p2 = game.player1, game.player2

    destroyer = p1.summon("FIR_955")
    enemy = p2.summon(CHILLWIND)
    enemy.max_health = 30
    enemy.damage = 0

    # Pass to the opponent's turn; now it is NOT p1's turn.
    game.end_turn()
    assert game.current_player is p2

    # p1's hero takes damage on the OPPONENT's turn -> effect must not fire.
    game.queue_actions(p2.hero, [Hit(p1.hero, 1)])
    assert enemy.damage == 0
