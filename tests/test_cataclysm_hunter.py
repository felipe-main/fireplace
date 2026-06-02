"""Tests for Cataclysm — HUNTER (CATA_) cards.

ISOLATION NOTE: the cataclysm package star-imports every per-class sibling
file. While the multi-agent set build is in flight, some siblings are
incomplete and raise at import time. To test the hunter cards in isolation we
inject a stub `fireplace.cards.cataclysm` package that exposes ONLY the hunter
module's classes before fireplace.cards initializes. Once all sibling files are
complete this shim is a no-op (the real package imports fine) and the official
gate (tests/test_carddb.py) exercises the full package.
"""

import sys
import types
import importlib.util


def _install_hunter_only_package():
    if "fireplace.cards.cataclysm" in sys.modules:
        return
    import fireplace.cards.utils  # noqa: F401

    pkg_name = "fireplace.cards.cataclysm"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = ["fireplace/cards/cataclysm"]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

    spec = importlib.util.spec_from_file_location(
        pkg_name + ".hunter", "fireplace/cards/cataclysm/hunter.py"
    )
    hunter = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name + ".hunter"] = hunter
    spec.loader.exec_module(hunter)
    for name in dir(hunter):
        if name.startswith("CATA_"):
            setattr(pkg, name, getattr(hunter, name))


_install_hunter_only_package()

from hearthstone.enums import CardClass, GameTag, Zone, CardType  # noqa: E402
from utils import prepare_game  # noqa: E402
from fireplace.cards import db  # noqa: E402


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# Dragon-in-hand transforms
# ---------------------------------------------------------------------------


def test_stonetalon_striker_has_taunt_and_transforms_on_dragon_play():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    striker = p1.give("CATA_551")
    assert striker.taunt
    assert striker.id == "CATA_551"
    # Give a real Dragon (Ebyssian token is a Dragon) and play it.
    dragon = p1.give("CATA_553t")
    dragon.play()
    # The in-hand striker has morphed into its 6/6 Dragon form.
    new = [c for c in p1.hand if c.id == "CATA_551t"]
    assert len(new) == 1
    assert new[0].atk == 6 and new[0].health == 6
    assert new[0].race == 24  # DRAGON
    assert new[0].taunt


def test_stonetalon_striker_no_transform_without_dragon():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    p1.give("CATA_551")
    # Play a non-Dragon minion (Reinforcement Rallier).
    p1.give("CATA_558").play()
    assert any(c.id == "CATA_551" for c in p1.hand)
    assert not any(c.id == "CATA_551t" for c in p1.hand)


def test_ebonscale_scout_battlecry_deals_attack_damage():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    scout = p1.give("CATA_552")  # 4/4
    enemy = game.player2.summon("CS2_182")  # 4/5 Ogre
    enemy.max_health = 20
    enemy.damage = 0
    scout.play(target=enemy)
    assert enemy.damage == 4  # equal to Scout's Attack


def test_ebonscale_scout_transforms_to_8_8_dragon_form():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    p1.give("CATA_552")
    dragon = p1.give("CATA_553t")
    dragon.play()
    new = [c for c in p1.hand if c.id == "CATA_552t"]
    assert len(new) == 1
    assert new[0].atk == 8 and new[0].health == 8
    assert new[0].race == 24


def test_ebonscale_scout_dragon_form_battlecry_deals_8():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    # The 8/8 Dragon form's battlecry deals damage equal to its (8) Attack.
    scout = p1.give("CATA_552t")
    enemy = game.player2.summon("CS2_182")
    enemy.max_health = 30
    enemy.damage = 0
    scout.play(target=enemy)
    assert enemy.damage == 8


def test_ebyssian_gives_dragons_rush_and_transforms():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    ebyssian = p1.give("CATA_553")  # 6/6, in hand
    # A dragon already on board should not have rush yet.
    drag_on_board = p1.summon("CATA_551t")  # 6/6 Dragon token
    assert not drag_on_board.rush
    ebyssian.play()
    # Aura now grants Rush to friendly Dragons.
    assert drag_on_board.rush
    # A newly summoned Dragon also gets Rush.
    drag2 = p1.summon("CATA_552t")
    assert drag2.rush
    # Non-dragon does not.
    nondrag = p1.summon("CATA_558")
    assert not nondrag.rush


def test_ebyssian_transforms_to_12_12_on_dragon_play():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    p1.give("CATA_553")
    dragon = p1.give("CATA_551t")  # 6/6 Dragon
    dragon.play()
    new = [c for c in p1.hand if c.id == "CATA_553t"]
    assert len(new) == 1
    assert new[0].atk == 12 and new[0].health == 12
    assert new[0].race == 24


# ---------------------------------------------------------------------------
# Reinforcement Rallier
# ---------------------------------------------------------------------------


def test_reinforcement_rallier_is_elusive():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    rallier = game.player2.summon("CATA_558")
    assert rallier.atk == 2 and rallier.health == 2
    # Elusive: a friendly enemy-targeting spell may NOT target it.
    fireball = p1.give("CS2_029")  # Fireball, single-target damage spell
    assert rallier not in fireball.targets
    # A non-elusive vanilla minion IS targetable, proving the gate is real.
    plain = game.player2.summon("CS2_182")  # Chillwind/Boulderfist Ogre
    assert plain in fireball.targets


# ---------------------------------------------------------------------------
# Tol'vir Carver
# ---------------------------------------------------------------------------


def test_tolvir_carver_reduces_a_hand_card_cost_each_turn():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    # Exactly one other card in hand so the random pick is deterministic.
    fireball = p1.give("CS2_029")  # 4-cost Fireball
    base_cost = fireball.cost
    carver = p1.give("CATA_566")
    carver.play()
    # The enchant is attached but cost only drops at the START of each turn.
    assert fireball.cost == base_cost
    # End p1 turn, end p2 turn -> start of p1's next turn ticks once.
    game.end_turn()
    game.end_turn()
    assert fireball.cost == base_cost - 1
    game.end_turn()
    game.end_turn()
    assert fireball.cost == base_cost - 2


# ---------------------------------------------------------------------------
# Earthen Roar
# ---------------------------------------------------------------------------


def test_earthen_roar_sets_health_to_1():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    enemy = game.player2.summon("CS2_182")  # 4/5 Ogre
    roar = p1.give("CATA_554")
    roar.play(target=enemy)
    assert enemy.health == 1
    assert enemy.max_health == 1


def test_earthen_roar_picks_second_when_holding_dragon():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    e1 = game.player2.summon("CS2_182")  # 4/5
    e2 = game.player2.summon("CS2_182")  # 4/5
    p1.give("CATA_553t")  # hold a Dragon
    roar = p1.give("CATA_554")
    roar.play(target=e1)
    _resolve_choices(p1)
    # Both enemy minions now have 1 health.
    assert e1.health == 1
    assert e2.health == 1


def test_earthen_roar_second_pick_is_player_chosen():
    # With >1 other enemy minion the second pick is a real ENTITY_CHOICE: the
    # player picks WHICH minion, the others are untouched.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    e1 = game.player2.summon("CS2_182")  # 4/5 — first (targeted) pick
    e2 = game.player2.summon("CS2_182")  # 4/5
    e3 = game.player2.summon("CS2_182")  # 4/5
    p1.give("CATA_553t")  # hold a Dragon
    roar = p1.give("CATA_554")
    roar.play(target=e1)
    # A choice over the two remaining enemy minions must be offered.
    assert p1.choice is not None
    assert set(p1.choice.cards) == {e2, e3}
    p1.choice.choose(e2)
    assert e1.health == 1
    assert e2.health == 1
    assert e3.health == 5  # not chosen → untouched


def test_earthen_roar_with_spell_in_hand_no_crash():
    # Regression: the holding-a-Dragon check iterated c.race over the whole
    # hand, crashing on Spells (no .race attr). A non-Dragon hand (incl. a
    # spell) must not crash and must NOT trigger the second pick.
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    e1 = game.player2.summon("CS2_182")  # 4/5
    e2 = game.player2.summon("CS2_182")  # 4/5
    p1.give("CS2_029")  # Fireball — a spell in hand (no .race)
    roar = p1.give("CATA_554")
    roar.play(target=e1)
    _resolve_choices(p1)
    assert e1.health == 1
    assert e2.health == 5  # second pick NOT triggered (no Dragon held)


# ---------------------------------------------------------------------------
# Sylvanas's Triumph
# ---------------------------------------------------------------------------


def test_sylvanas_triumph_single_hit_first_copy():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    target = game.player2.summon("CS2_182")  # 4/5
    target.max_health = 20
    target.damage = 0
    other = game.player2.summon("CS2_182")
    other.max_health = 20
    other.damage = 0
    spell = p1.give("CATA_557")
    spell.play(target=target)
    assert target.damage == 3
    assert other.damage == 0  # only the chosen target hit


def test_sylvanas_triumph_second_copy_hits_all_enemies():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    # Play first copy at a minion.
    t0 = game.player2.summon("CS2_182")
    t0.max_health = 20
    t0.damage = 0
    p1.give("CATA_557").play(target=t0)
    # Set up a fresh board for the second copy.
    m1 = game.player2.summon("CS2_182")
    m1.max_health = 20
    m1.damage = 0
    m2 = game.player2.summon("CS2_182")
    m2.max_health = 20
    m2.damage = 0
    game.player2.hero.max_health = 30
    game.player2.hero.damage = 0
    p1.give("CATA_557").play(target=m1)
    # Second copy hits ALL enemies for 3 (target arg ignored).
    assert m1.damage == 3
    assert m2.damage == 3
    assert game.player2.hero.damage == 3


# ---------------------------------------------------------------------------
# Confront the Tol'vir
# ---------------------------------------------------------------------------


def test_confront_replays_each_1cost_card_played():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    # Play a 1-cost minion (Reinforcement Rallier) and a 1-cost spell
    # (Earthen Roar) earlier this game.
    p1.give("CATA_558").play()  # 1-cost minion now on board
    enemy = game.player2.summon("CS2_182")  # target for the roar
    enemy.max_health = 20
    enemy.damage = 0
    p1.give("CATA_554").play(target=enemy)  # 1-cost spell, sets enemy hp to 1
    pre_field = len(p1.field)
    # Now Confront: replays Rallier (a fresh one summoned) and Earthen Roar
    # (recast at an enemy minion).
    confront = p1.give("CATA_560")
    confront.play()
    _resolve_choices(p1)
    # A second Reinforcement Rallier was summoned.
    ralliers = [c for c in p1.field if c.id == "CATA_558"]
    assert len(ralliers) == 2
    assert len(p1.field) == pre_field + 1


# ---------------------------------------------------------------------------
# Supply Run (Shatter halves)
# ---------------------------------------------------------------------------


def test_supply_run_draw_half_draws_three_minions():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    # Stock the deck with minions so the draw is deterministic.
    for _ in range(5):
        p1.give("CATA_558").shuffle_into_deck()
    pre_hand = len(p1.hand)
    p1.give("CATA_820t").play()
    drawn = len(p1.hand) - pre_hand
    # +1 (the spell left hand on play, so net = 3 drawn - 0; count minions).
    minions_drawn = [c for c in p1.hand if c.type == CardType.MINION]
    assert len(minions_drawn) == 3


def test_supply_run_buff_half_gives_hand_minions_plus2():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    m = p1.give("CATA_558")  # 2/2 in hand
    base_atk, base_health = m.atk, m.health
    p1.give("CATA_820t2").play()
    assert m.atk == base_atk + 2
    assert m.health == base_health + 2


# ---------------------------------------------------------------------------
# Magmaw (Colossal)
# ---------------------------------------------------------------------------


def test_magmaw_summons_colossal_bodies():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.summon("CATA_550")
    # Magmaw + its appendages fill the board (engine caps at 7).
    assert any(c.id == "CATA_550" for c in p1.field)
    bodies = [c for c in p1.field if c.id.startswith("CATA_550t")]
    assert len(bodies) >= 1
    # Each body is a 2/1 Beast/Mech.
    for b in bodies:
        assert b.atk == 2 and b.health == 1


def test_magmaw_body_deathrattle_buffs_random_friendly():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.player1
    p1.discard_hand()
    # A single friendly minion to receive the +2 Attack deterministically.
    wisp = p1.summon("CS2_231")  # 1/1
    body = p1.summon("CATA_550t")
    base = wisp.atk
    body.destroy()
    assert wisp.atk == base + 2
