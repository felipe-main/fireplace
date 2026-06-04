"""Emerald Dream mini-set (Firelands, FIR_) — ROGUE collectible card tests.

Covers the three mini-set Rogue cards:
  FIR_919 Everburning Phoenix, FIR_920 Smoke Bomb, FIR_922 Cindersword.
"""

from utils import *

from hearthstone.enums import CardType, GameTag, Zone


# FIR_919 — Everburning Phoenix | MINION 4/2/2:
# Costs (1) less for each card you've played this turn.
# Deathrattle: Return this to your hand.
def test_everburning_phoenix_cost_drops_per_card_played():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    phoenix = p1.give("FIR_919")
    # Nothing played yet this turn -> full cost.
    assert p1.cards_played_this_turn == 0
    assert phoenix.cost == 4
    # Play two 0-cost Wisps; each bumps cards_played_this_turn by one.
    p1.give("CS2_231").play()
    p1.give("CS2_231").play()
    assert p1.cards_played_this_turn == 2
    # Cost drops (1) per card played this turn: 4 - 2 == 2.
    assert phoenix.cost == 2


def test_everburning_phoenix_cost_never_below_zero():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    phoenix = p1.give("FIR_919")
    for _ in range(6):  # play more cards than the base cost
        p1.give("CS2_231").play()
    assert p1.cards_played_this_turn == 6
    # 4 - 6 would be negative; engine clamps cost at 0.
    assert phoenix.cost == 0


def test_everburning_phoenix_deathrattle_returns_to_hand():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    phoenix = p1.summon("FIR_919")
    assert phoenix.zone == Zone.PLAY
    assert len(p1.hand) == 0
    phoenix.destroy()
    game.process_deaths()
    # Deathrattle bounced it back to hand; board is empty.
    assert phoenix.zone == Zone.HAND
    assert len(p1.field) == 0
    assert [c.id for c in p1.hand] == ["FIR_919"]


# FIR_920 — Smoke Bomb | SPELL 2:
# Discover a Combo, Battlecry, or Stealth minion with a Dark Gift.
def test_smoke_bomb_discovers_keyword_minion_with_dark_gift():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    spell = p1.give("FIR_920")
    spell.play()
    # A Discover choice is presented.
    assert p1.choice is not None
    assert len(p1.choice.cards) == 3
    # Every option is a Combo, Battlecry, or Stealth minion.
    for c in p1.choice.cards:
        assert c.type == CardType.MINION
        assert (
            c.tags.get(GameTag.COMBO)
            or c.tags.get(GameTag.BATTLECRY)
            or c.tags.get(GameTag.STEALTH)
        )
    chosen = p1.choice.cards[0]
    p1.choice.choose(chosen)
    # The discovered minion carries exactly one Dark Gift. It usually lands in
    # hand, but the "Sweet Dreams" gift relocates it to the top of the deck.
    held = next(c for c in (list(p1.hand) + list(p1.deck))
                if c.id == chosen.id and getattr(c, "_dark_gifts", None))
    assert len(held._dark_gifts) == 1


# FIR_922 — Cindersword | WEAPON 1/1/2:
# Battlecry: If you're holding a minion with a Dark Gift, gain +3 Attack.
def test_cindersword_gains_attack_when_holding_gifted_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    # Hold a minion that carries a Dark Gift (the set-wide _dark_gifts marker).
    gifted = p1.give("CS2_182")  # Chillwind Yeti
    gifted._dark_gifts = ["EDR_100t3"]  # gift id marker
    sword = p1.give("FIR_922")
    sword.play()
    w = p1.weapon
    assert w.id == "FIR_922"
    # Base 1 Attack + 3 from the battlecry == 4.
    assert w.atk == 4
    assert any(b.id == "FIR_922e" for b in w.buffs)


def test_cindersword_no_buff_without_gifted_minion():
    game = prepare_empty_game(CardClass.ROGUE, CardClass.ROGUE)
    p1 = game.player1
    p1.discard_hand()
    # Hold a plain minion (no Dark Gift).
    p1.give("CS2_182")  # Chillwind Yeti, no _dark_gifts
    sword = p1.give("FIR_922")
    sword.play()
    w = p1.weapon
    assert w.id == "FIR_922"
    # No gifted minion held -> base Attack, no enchant.
    assert w.atk == 1
    assert not any(b.id == "FIR_922e" for b in w.buffs)
