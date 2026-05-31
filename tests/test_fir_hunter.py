"""Firelands mini-set (FIR_) — HUNTER collectible cards.

Tight unit tests asserting the PRINTED card behaviour. One test per card:
  FIR_909 Bursting Shot, FIR_953 Magma Hound, FIR_960 Tending Dragonkin.
"""

import pytest

from utils import *

from hearthstone.enums import CardType, GameTag, Race, Zone


# FIR_909 — Bursting Shot: Deal $2 damage to three random enemies.
def test_bursting_shot_hits_three_enemies():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    # The only enemy character is one beefy minion (no hero overkill, no
    # other minions) so all three 2-damage darts must land on it: 6 total.
    game.end_turn()
    target = p2.summon("CS2_182")  # Chillwind Yeti
    target.max_health = 80
    target._max_health = 80
    target.damage = 0
    # Make the hero immune-ish by beefing it too; assert exact split below.
    p2.hero.max_health = 80
    p2.hero._max_health = 80
    p2.hero.damage = 0
    game.end_turn()
    shot = p1.give("FIR_909")
    shot.play()
    # Three darts of 2 each across the only two living enemy characters
    # (one minion + hero) -> grand total is exactly 6.
    assert target.damage + p2.hero.damage == 6
    # Each dart deals exactly 2, so the total is a multiple of 2.
    assert target.damage % 2 == 0
    assert p2.hero.damage % 2 == 0


# FIR_953 — Magma Hound: Rush. After this attacks a minion and survives, deal
# this minion's Attack damage split among all enemies.
def test_magma_hound_splits_attack_when_surviving():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    hound = p1.summon("FIR_953")  # 5/8 Rush
    assert hound.rush
    assert (hound.atk, hound.max_health) == (5, 8)
    game.end_turn()
    # A small minion to be attacked; the hound (8 health) survives its 1 atk.
    chump = p2.summon("CS2_171")  # 1/1 Stonetusk Boar
    chump.max_health = 1
    # A single beefy second enemy to absorb every split dart deterministically.
    sink = p2.summon("CS2_182")
    sink.max_health = 80
    sink._max_health = 80
    sink.damage = 0
    game.end_turn()
    hound.attack(chump)
    game.process_deaths()
    # Hound survived (8 hp, took 1). It dealt 5 to chump (killed) and then
    # split its 5 Attack among all enemies. chump is dead, so the only living
    # enemy minion left is sink, plus the enemy hero. Assert the *total* extra
    # damage dealt by the split equals exactly the hound's Attack (5).
    assert hound.zone == Zone.PLAY
    assert chump.zone == Zone.GRAVEYARD
    split_total = sink.damage + p2.hero.damage
    assert split_total == 5


def test_magma_hound_no_split_when_dies():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1, p2 = game.player1, game.player2
    hound = p1.summon("FIR_953")
    hound.max_health = 8
    hound.damage = 0
    game.end_turn()
    # A big defender that kills the hound on the counterattack.
    killer = p2.summon("CS2_182")
    killer.atk = 20
    sink = p2.summon("CS2_182")
    sink.max_health = 80
    sink._max_health = 80
    sink.damage = 0
    game.end_turn()
    hound.attack(killer)
    game.process_deaths()
    assert hound.zone == Zone.GRAVEYARD
    # Hound died -> no split. sink takes nothing; killer only took the hound's
    # 5 Attack from the attack itself; hero untouched.
    assert sink.damage == 0
    assert p2.hero.damage == 0


# FIR_960 — Tending Dragonkin: Battlecry: Copy the lowest Cost Beast in your
# hand.
def test_tending_dragonkin_copies_lowest_cost_beast():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # Clear hand so only the beasts we add are candidates.
    for c in list(p1.hand):
        c.discard()
    cheap_beast = p1.give("CS2_171")  # Stonetusk Boar, 1-cost Beast
    pricey_beast = p1.give("CS2_125")  # Ironfur Grizzly, 3-cost Beast
    assert cheap_beast.cost == 1
    assert pricey_beast.cost == 3
    dragonkin = p1.give("FIR_960")
    pre_count = len([c for c in p1.hand if c.id == "CS2_171"])
    assert pre_count == 1
    dragonkin.play()
    # The lowest-cost Beast (Stonetusk Boar) is copied into hand.
    copies = [c for c in p1.hand if c.id == "CS2_171"]
    assert len(copies) == 2
    # The pricier beast was not copied.
    assert len([c for c in p1.hand if c.id == "CS2_125"]) == 1


def test_tending_dragonkin_no_beast_no_copy():
    game = prepare_empty_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    non_beast = p1.give("CS2_182")  # Chillwind Yeti — not a Beast
    dragonkin = p1.give("FIR_960")
    dragonkin.play()
    # No Beast in hand -> nothing copied; only the original Yeti remains.
    assert len([c for c in p1.hand if c.id == "CS2_182"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
