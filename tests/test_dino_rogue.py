"""The Lost City of Un'Goro — MINI-SET (Dinosaurs, DINO_) — Rogue cards.

DINO_407 Mirrex, the Crystalline — in-hand 3/3 copy of opponent's last minion
DINO_408 Crystal Tusk         — weapon: shuffle leftmost / deathrattle draw 2
DINO_427 Costume Merchant     — get a Mask from another class; Combo (2) less
"""

from utils import *

from hearthstone.enums import CardClass, CardType, Zone

import fireplace.cards


COIN = "GAME_005"
YETI = "CS2_182"          # Chillwind Yeti — vanilla 4/5
BOULDERFIST = "CS2_200"   # Boulderfist Ogre — vanilla 6/7
WISP = "CS2_231"          # 0/1, no text

# Costume Merchant's pool: the five class Masks (one per other class).
MASKS = {"DINO_402", "DINO_403", "DINO_428", "DINO_429", "DINO_432"}


def _clear_hand(player):
    for c in list(player.hand):
        c.discard()


# ---------------------------------------------------------------------------
# DINO_407 Mirrex, the Crystalline
# While in your hand, this is a 3/3 copy of the last minion your opponent
# played.
# ---------------------------------------------------------------------------
def test_mirrex_copies_opponent_last_minion_as_3_3():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2

    mirrex = p1.give("DINO_407")
    # Before the opponent has played any minion, Mirrex is its own 3/3 self.
    assert mirrex.id == "DINO_407"
    assert mirrex.atk == 3 and mirrex.max_health == 3

    game.end_turn()
    p2.give(YETI).play()          # Chillwind Yeti — opponent's last minion
    game.refresh_auras()

    copies = [c for c in p1.hand if getattr(c, "_mirrex", False)]
    assert len(copies) == 1
    copy = copies[0]
    # Mirrex now shows the Yeti's identity, but pinned to 3/3.
    assert copy.id == YETI
    assert copy.atk == 3
    assert copy.max_health == 3


def test_mirrex_resyncs_when_opponent_plays_a_new_minion():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2

    p1.give("DINO_407")
    game.end_turn()
    p2.give(YETI).play()
    game.refresh_auras()
    first = [c for c in p1.hand if getattr(c, "_mirrex", False)][0]
    assert first.id == YETI

    # Opponent plays a different minion → Mirrex re-syncs to it (still 3/3).
    p2.give(BOULDERFIST).play()
    game.refresh_auras()
    second = [c for c in p1.hand if getattr(c, "_mirrex", False)][0]
    assert second.id == BOULDERFIST
    assert second.atk == 3 and second.max_health == 3


def test_mirrex_plays_as_3_3_body():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2

    p1.give("DINO_407")
    game.end_turn()
    p2.give(YETI).play()
    game.refresh_auras()
    game.end_turn()               # back to p1, who can now play the copy

    copy = [c for c in p1.hand if getattr(c, "_mirrex", False)][0]
    copy.play()

    body = p1.field[-1]
    assert body.id == YETI
    assert body.atk == 3
    assert body.max_health == 3


# ---------------------------------------------------------------------------
# DINO_408 Crystal Tusk (weapon)
# Battlecry: Shuffle the left-most card in your hand into your deck.
# Deathrattle: Draw 2 cards.
# ---------------------------------------------------------------------------
def test_crystal_tusk_battlecry_shuffles_leftmost():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)

    leftmost = p1.give(WISP)      # hand[0] after clear
    p1.give(YETI)                 # hand[1] — must survive
    deck_before = len(p1.deck)

    tusk = p1.give("DINO_408")    # hand[2] — the weapon being played
    tusk.play()

    # The Wisp (left-most) went to the deck; the Yeti stayed in hand.
    assert leftmost.zone == Zone.DECK
    assert len(p1.deck) == deck_before + 1
    assert any(c.id == YETI for c in p1.hand)
    assert p1.weapon is not None and p1.weapon.id == "DINO_408"


def test_crystal_tusk_battlecry_noop_on_empty_hand():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)

    deck_before = len(p1.deck)
    tusk = p1.give("DINO_408")    # only card in hand → leaves on play → empty
    tusk.play()

    # Nothing left to shuffle: deck size unchanged, weapon equipped.
    assert len(p1.deck) == deck_before
    assert p1.weapon is not None and p1.weapon.id == "DINO_408"


def test_crystal_tusk_deathrattle_draws_two():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1

    tusk = p1.summon("DINO_408")  # bypass cost + battlecry; just the weapon
    assert p1.weapon is tusk
    hand_before = len(p1.hand)

    tusk.destroy()                # fire the deathrattle pipeline

    assert len(p1.hand) == hand_before + 2
    assert p1.weapon is None


# ---------------------------------------------------------------------------
# DINO_427 Costume Merchant
# Battlecry: Get a random Mask from another class. Combo: It costs (2) less.
# ---------------------------------------------------------------------------
def test_costume_merchant_no_combo_gets_mask_full_price():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)

    # No card played first this turn → no combo.
    assert not p1.combo
    cm = p1.give("DINO_427")
    cm.play()

    masks = [c for c in p1.hand if c.id in MASKS]
    assert len(masks) == 1
    mask = masks[0]
    # Mask is from another class (Costume Merchant is Rogue).
    assert CardClass.ROGUE not in (mask.data.classes or [mask.data.card_class])
    # Full price — no combo discount.
    assert mask.cost == mask.data.cost


def test_costume_merchant_combo_discounts_mask_by_two():
    game = prepare_game(CardClass.ROGUE, CardClass.MAGE)
    p1 = game.player1
    _clear_hand(p1)

    p1.give(COIN).play()          # warm-up card → combo active
    assert p1.combo
    cm = p1.give("DINO_427")
    cm.play()

    masks = [c for c in p1.hand if c.id in MASKS]
    assert len(masks) == 1
    mask = masks[0]
    # Combo: it costs exactly (2) less than its printed cost.
    assert mask.cost == mask.data.cost - 2
