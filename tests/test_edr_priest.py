"""Into the Emerald Dream — PRIEST collectible cards.

One test (or cluster) per collectible, asserting the PRINTED behaviour:
  EDR_449 (Lunarwing Messenger), EDR_460 (Wish of the New Moon),
  EDR_461 (Ritual of the New Moon), EDR_462 (Selenic Drake),
  EDR_463 (Twilight Influence), EDR_464 (Tyrande),
  EDR_472 (Weaver of the Cycle), EDR_476 (Moonwell),
  EDR_895 (Aviana, Elune's Chosen), EDR_970 (Kaldorei Priestess).
"""

import pytest

from utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone, Race

import fireplace.cards as _cards


# ---------------------------------------------------------------------------
# EDR_449 — Lunarwing Messenger: Lifesteal. Battlecry: Imbue your Hero Power.
# ---------------------------------------------------------------------------
def test_lunarwing_messenger():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    assert p1.hero.power.id != "EDR_449p"
    c = p1.give("EDR_449")
    c.play()
    # Lifesteal (from data) and the Imbue installed the Priest Imbued power.
    assert c.lifesteal
    assert p1.imbues_this_game == 1
    assert p1.hero.power.id == "EDR_449p"


# ---------------------------------------------------------------------------
# EDR_460 — Wish of the New Moon: Deal 6 to a minion. (Cast 4 spells to gain
# Lifesteal.)
# ---------------------------------------------------------------------------
def test_wish_of_the_new_moon_base():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    t = p2.summon("CS2_182")  # Chillwind Yeti
    t.max_health = 80
    t.damage = 0
    p1.hero.damage = 10
    w = p1.give("EDR_460")
    w.play(target=t)
    # Exactly 6 damage, no Lifesteal (fewer than 4 spells cast).
    assert t.damage == 6
    assert not w.lifesteal
    assert p1.hero.damage == 10


def test_wish_of_the_new_moon_fourth_spell_lifesteals():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    t = p2.summon("CS2_182")
    t.max_health = 80
    t.damage = 0
    p1.hero.damage = 10
    # This is the player's 4th spell this game (3 already cast, counter not yet
    # including the current spell).
    p1.spells_played_this_game = 3
    w = p1.give("EDR_460")
    w.play(target=t)
    assert w.lifesteal
    assert t.damage == 6
    # Lifesteal heals the hero for the 6 dealt: 10 -> 4.
    assert p1.hero.damage == 4


# ---------------------------------------------------------------------------
# EDR_461 — Ritual of the New Moon: Summon two random 3-Cost minions. (Cast 4
# spells to summon 6-Cost minions instead.)
# ---------------------------------------------------------------------------
def test_ritual_of_the_new_moon_base():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    before = len(p1.field)
    r = p1.give("EDR_461")
    r.play()
    summoned = p1.field[before:]
    assert len(summoned) == 2
    assert all(m.cost == 3 for m in summoned)


def test_ritual_of_the_new_moon_fourth_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.spells_played_this_game = 3
    before = len(p1.field)
    r = p1.give("EDR_461")
    r.play()
    summoned = p1.field[before:]
    assert len(summoned) == 2
    assert all(m.cost == 6 for m in summoned)


# ---------------------------------------------------------------------------
# EDR_462 — Selenic Drake: Elusive. At the end of your turn, get a random
# Dragon.
# ---------------------------------------------------------------------------
def test_selenic_drake():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p1.discard_hand()
    d = p1.summon("EDR_462")
    # Elusive — can't be targeted by spells / Hero Powers.
    assert d.cant_be_targeted_by_abilities
    assert d.cant_be_targeted_by_hero_powers
    assert len(p1.hand) == 0
    game.end_turn()
    # End of your turn: exactly one card added, and it's a Dragon.
    assert len(p1.hand) == 1
    assert Race.DRAGON in p1.hand[0].races


# ---------------------------------------------------------------------------
# EDR_463 — Twilight Influence: Choose One - Destroy a minion with 3 or less
# Attack; or Summon a random 2-Cost minion.
# ---------------------------------------------------------------------------
def test_twilight_influence_destroy():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    victim = p2.summon("CS2_171")  # Stonetusk Boar 1/1 (Attack 1 <= 3)
    ti = p1.give("EDR_463")
    ti.play(choose="EDR_463a", target=victim)
    assert victim.zone == Zone.GRAVEYARD


def test_twilight_influence_summon():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    before = len(p1.field)
    ti = p1.give("EDR_463")
    ti.play(choose="EDR_463b")
    summoned = p1.field[before:]
    assert len(summoned) == 1
    assert summoned[0].cost == 2


# ---------------------------------------------------------------------------
# EDR_464 — Tyrande: Battlecry: The next 3 spells you play cast twice.
# ---------------------------------------------------------------------------
def test_tyrande_next_three_spells_cast_twice():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    ty = p1.give("EDR_464")
    ty.play()
    assert p1.spells_cast_twice
    t = p2.summon("CS2_182")
    t.max_health = 80
    t.damage = 0
    # Holy Smite deals 3 (this build); cast twice => 6 per play.
    for expected in (6, 12, 18):
        sm = p1.give("CS1_130")
        sm.play(target=t)
        assert t.damage == expected
    # The third spell consumed the charge; the aura is gone now.
    assert not p1.spells_cast_twice
    # A 4th spell casts only once (+3). Refill mana first (Tyrande + 3 Smites
    # already spent the turn's 10 crystals).
    p1.used_mana = 0
    sm = p1.give("CS1_130")
    sm.play(target=t)
    assert t.damage == 21


# ---------------------------------------------------------------------------
# EDR_472 — Weaver of the Cycle: Battlecry: If you're holding a spell that
# costs (5) or more, deal 3 damage.
# ---------------------------------------------------------------------------
def test_weaver_of_the_cycle_with_big_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    p1.discard_hand()
    p1.give("EDR_476")  # Moonwell, costs 7 (>= 5)
    t = p2.summon("CS2_182")
    t.max_health = 80
    t.damage = 0
    w = p1.give("EDR_472")
    w.play(target=t)
    assert t.damage == 3


def test_weaver_of_the_cycle_without_big_spell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    p1.discard_hand()
    t = p2.summon("CS2_182")
    t.max_health = 80
    t.damage = 0
    w = p1.give("EDR_472")
    w.play(target=t)
    # No 5+ spell in hand -> battlecry deals nothing.
    assert t.damage == 0


# ---------------------------------------------------------------------------
# EDR_476 — Moonwell: Deal 4 damage to all enemy characters. Restore 4 Health
# to all friendly characters.
# ---------------------------------------------------------------------------
def test_moonwell():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    enemy = p2.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    friendly = p1.summon("CS2_182")
    friendly.max_health = 80
    friendly.damage = 20
    p1.hero.damage = 10
    p2.hero.damage = 0
    mw = p1.give("EDR_476")
    mw.play()
    # 4 damage to every enemy character.
    assert enemy.damage == 4
    assert p2.hero.damage == 4
    # 4 healing to every friendly character.
    assert friendly.damage == 16
    assert p1.hero.damage == 6


# ---------------------------------------------------------------------------
# EDR_895 — Aviana, Elune's Chosen: Battlecry: Start a three turn lunar cycle.
# When the Full Moon rises, your cards cost (1) this game.
# ---------------------------------------------------------------------------
def test_aviana_lunar_cycle():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    a = p1.give("EDR_895")
    a.play()
    yeti = p1.give("CS2_182")
    assert yeti.cost == 4  # cycle not yet complete
    # Two own-turn-begins: still full cost.
    game.end_turn(); game.end_turn()
    assert yeti.cost == 4
    game.end_turn(); game.end_turn()
    assert yeti.cost == 4
    # Third own-turn-begin: Full Moon rises.
    game.end_turn(); game.end_turn()
    assert yeti.cost == 1
    # Persists this game: a freshly given card also costs (1).
    fresh = p1.give("EDR_476")  # base cost 7
    assert fresh.cost == 1


def test_aviana_full_moon_persists_after_death():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    a = p1.give("EDR_895")
    a.play()
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    game.end_turn(); game.end_turn()
    # Full Moon up. Kill Aviana — the cost effect is attached to the player,
    # so it survives.
    a.destroy()
    assert a.zone == Zone.GRAVEYARD
    yeti = p1.give("CS2_182")
    assert yeti.cost == 1


# ---------------------------------------------------------------------------
# EDR_449p — Blessing of the Moon (Priest Imbued Hero Power): Choose a Priest
# minion or Priest spell to add to your hand. It costs (@) less.
#
# Regression: the discover pool must be COLLECTIBLE Priest minions and spells
# only. A bare RandomCard(card_class=PRIEST) leaked hero cards, weapons and
# non-collectible tokens/enchants. Assert every offered card is a collectible
# Priest MINION or SPELL.
# ---------------------------------------------------------------------------
def test_blessing_of_the_moon_pool_is_collectible_minions_and_spells():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    # Imbue installs EDR_449p as the Hero Power.
    p1.give("EDR_449").play()
    assert p1.hero.power.id == "EDR_449p"
    # Fire the imbued power 30 times, inspecting every Discover offer.
    seen = 0
    for _ in range(30):
        p1.used_mana = 0
        p1.hero.power.activations_this_turn = 0
        p1.hero.power.use()
        choice = p1.choice
        assert choice is not None
        assert len(choice.cards) == 3
        for card in choice.cards:
            data = _cards.db[card.id]
            assert data.collectible, f"{card.id} is not collectible"
            assert data.type in (CardType.MINION, CardType.SPELL), (
                f"{card.id} is type {data.type} (not minion/spell)"
            )
            # Priest by primary class OR multiclass membership (e.g. Rally!).
            classes = getattr(data, "classes", None) or [data.card_class]
            assert CardClass.PRIEST in classes, (
                f"{card.id} classes {classes} (not Priest)"
            )
            seen += 1
        # Resolve the choice and refresh the power for the next iteration.
        choice.choose(choice.cards[0])
        p1.hero.power.activations_this_turn = 0
    assert seen == 90


# ---------------------------------------------------------------------------
# EDR_970 — Kaldorei Priestess: Battlecry: Give all enemy minions -2 Attack
# until your next turn. Imbue your Hero Power.
# ---------------------------------------------------------------------------
def test_kaldorei_priestess():
    game = prepare_game(CardClass.PRIEST, CardClass.PRIEST)
    p1 = game.current_player
    p2 = p1.opponent
    yeti = p2.summon("CS2_182")  # 4/5
    boar = p2.summon("CS2_171")  # 1/1
    assert p1.hero.power.id != "EDR_449p"
    k = p1.give("EDR_970")
    k.play()
    # -2 Attack to all enemy minions (clamped at 0).
    assert yeti.atk == 2
    assert boar.atk == 0
    # Imbue installed the Priest Imbued power.
    assert p1.imbues_this_game == 1
    assert p1.hero.power.id == "EDR_449p"
    # Wears off on your next turn.
    game.end_turn(); game.end_turn()
    assert yeti.atk == 4
    assert boar.atk == 1
