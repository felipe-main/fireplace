"""Across the Timeways — Tier-1 fix regressions (audit real bugs).

Covers four real bugs surfaced by the adversarial audit:
  * TIME_441 Aeon Rend       — two DISTINCT random enemies (selector*2).
  * TIME_433 Cease to Exist  — Silence+Destroy the SAME random minion.
  * TIME_620 Untimely Death  — fires only the turn immediately after play.
  * TIME_211 Well of Eternity — empowered spells cast twice (engine flag).
"""
from utils import *

from hearthstone.enums import Zone


def _resolve_rewind_keep(player):
    """A Rewind card queues a Keep/Rewind choice after its effect; take Keep."""
    if player.choice is not None:
        keep = next(c for c in player.choice.cards if c.id == "TIME_000ta")
        player.choice.choose(keep)


# ---------------------------------------------------------------------------
# TIME_441 Aeon Rend — Deal 4 damage to two DISTINCT random enemies.
# Opponent has exactly two enemy characters (hero + one minion), so both must
# be hit for exactly 4 each. The old action*2 form could roll the hero twice
# (8 to hero, 0 to the minion).
# ---------------------------------------------------------------------------
def test_aeon_rend_hits_two_distinct_enemies():
    game = prepare_game(CardClass.DEMONHUNTER, CardClass.DEMONHUNTER)
    p1, p2 = game.player1, game.player2
    minion = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    rend = p1.give("TIME_441")
    rend.play()
    _resolve_rewind_keep(p1)
    # Both distinct enemies took exactly 4.
    assert p2.hero.health == 26
    assert minion.damage == 4


# ---------------------------------------------------------------------------
# TIME_433 Cease to Exist — Silence AND Destroy the SAME random enemy minion.
# Two Leper Gnomes (Deathrattle: 2 damage to enemy hero). Whichever is chosen
# is Silenced first, so its deathrattle never fires: our hero takes 0 damage.
# The old two-rolls form could destroy an un-silenced gnome (2 to our hero).
# ---------------------------------------------------------------------------
def test_cease_to_exist_silences_the_destroyed_minion():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1, p2 = game.player1, game.player2
    p2.summon("EX1_029")  # Leper Gnome
    p2.summon("EX1_029")  # Leper Gnome
    start_health = p1.hero.health

    spell = p1.give("TIME_433")
    spell.play()
    _resolve_rewind_keep(p1)

    # Exactly one gnome destroyed; the destroyed one was silenced, so no
    # deathrattle damage reached our hero.
    assert len([m for m in p2.field if m.id == "EX1_029"]) == 1
    assert p1.hero.health == start_health


# ---------------------------------------------------------------------------
# TIME_620 Untimely Death — Secret: a friendly minion that dies the turn
# IMMEDIATELY after being played is resummoned. A death two+ turns later must
# NOT trigger.
# ---------------------------------------------------------------------------
def test_untimely_death_fires_the_turn_after():
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.give("TIME_620").play()            # secret armed
    yeti = p1.give("CS2_182")
    yeti.play()                           # played this turn (sets turn_played)
    game.end_turn()                       # -> opponent's immediately-next turn
    yeti.destroy()
    game.process_deaths()
    # Secret revealed + a fresh copy resummoned.
    assert p1.secrets == []
    assert len([m for m in p1.field if m.id == "CS2_182"]) == 1


def test_untimely_death_ignores_later_turn_death():
    game = prepare_game(CardClass.HUNTER, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.give("TIME_620").play()            # secret armed
    yeti = p1.give("CS2_182")
    yeti.play()                           # played this turn (sets turn_played)
    # Let several turns pass before the minion dies (opponent's turn, 2 rounds
    # later) — well past "the turn after".
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    yeti.destroy()
    game.process_deaths()
    # Secret still armed; nothing resummoned.
    assert len(p1.secrets) == 1
    assert len([m for m in p1.field if m.id == "CS2_182"]) == 0


# ---------------------------------------------------------------------------
# TIME_211 Well of Eternity (empowered) — its spells cast twice. Tested via the
# engine flag _casts_twice_self on a known spell (Fireball: 6 -> 12 damage).
# ---------------------------------------------------------------------------
def test_casts_twice_self_flag_doubles_a_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon("CS2_182")  # Chillwind Yeti 4/5
    target.max_health = 80
    target.set_current_health(80)

    fireball = p1.give("CS2_029")  # Fireball — 6 damage
    fireball._casts_twice_self = True
    fireball.play(target=target)
    # Cast twice: 6 + 6 = 12.
    assert target.damage == 12


def test_empowered_well_flags_its_spells():
    from fireplace.cards.across_the_timeways.druid import _FillTemporarySpells

    game = prepare_game(CardClass.DRUID, CardClass.DRUID)
    p1 = game.player1
    for c in list(p1.hand):
        c.discard()
    game.queue_actions(p1.hero, [_FillTemporarySpells(p1, True)])
    spells = [c for c in p1.hand if c.type == CardType.SPELL]
    assert spells, "empowered Well should fill the hand with spells"
    assert all(getattr(s, "_casts_twice_self", False) for s in spells)
