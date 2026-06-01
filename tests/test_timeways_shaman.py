"""Tests for Across the Timeways — SHAMAN (TIME_) cards.

ISOLATION NOTE: the across_the_timeways package star-imports every per-class
sibling file. While the multi-agent set build is in flight, some siblings are
incomplete and raise at import time. To test the shaman cards in isolation we
inject a stub `fireplace.cards.across_the_timeways` package that exposes ONLY
the shaman module's classes before fireplace.cards initializes. Once all
sibling files are complete this shim is a no-op (the real package would import
fine) and the official gate (tests/test_carddb.py) exercises the full package.
"""

import sys
import types
import importlib.util


def _install_shaman_only_package():
    if "fireplace.cards.across_the_timeways" in sys.modules:
        return
    # Ensure parent packages exist first.
    import fireplace.cards.utils  # noqa: F401

    pkg_name = "fireplace.cards.across_the_timeways"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = ["fireplace/cards/across_the_timeways"]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

    # Exec shaman.py inside the package namespace so `from ..utils import *`
    # resolves, and copy its public classes onto the package.
    spec = importlib.util.spec_from_file_location(
        pkg_name + ".shaman", "fireplace/cards/across_the_timeways/shaman.py"
    )
    shaman = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name + ".shaman"] = shaman
    spec.loader.exec_module(shaman)
    for name in dir(shaman):
        if name.startswith("TIME_") or name.startswith("END_"):
            setattr(pkg, name, getattr(shaman, name))


_install_shaman_only_package()

from hearthstone.enums import CardClass, GameTag, Zone, SpellSchool  # noqa: E402
from utils import prepare_game  # noqa: E402
from fireplace.cards import db  # noqa: E402


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


# ---------------------------------------------------------------------------
# Minions
# ---------------------------------------------------------------------------


def test_farseer_wo_discovers_nature_spell_after_spell_cast():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    game.player2.discard_hand()
    p1.summon("TIME_013")
    # Cast any spell — Static Shock (a Nature spell). The trigger discovers a
    # Nature spell from the past.
    shock = p1.give("TIME_218")
    target = game.player2.summon("CS2_182")  # 4/5 Boulderfist Ogre
    shock.play(target=target)
    assert p1.choice is not None
    # Every discover option must be a Nature spell.
    for card in p1.choice.cards:
        assert card.type == 5  # SPELL
        assert card.spell_school == SpellSchool.NATURE
    pre = len(p1.hand)
    p1.choice.choose(p1.choice.cards[0])
    assert len(p1.hand) == pre + 1


def test_muradin_equips_hammer_and_returns_it_on_death():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    muradin = p1.give("TIME_209")
    muradin.play()
    # Battlecry equips the High King's Hammer.
    assert p1.weapon is not None
    assert p1.weapon.id == "TIME_209t"
    assert p1.weapon.atk == 3
    # Deathrattle adds the hammer (weapon card) to hand.
    pre_hand = len(p1.hand)
    muradin.destroy()
    assert len(p1.hand) == pre_hand + 1
    assert any(c.id == "TIME_209t" for c in p1.hand)


def test_high_king_hammer_shuffles_back_with_plus2_attack():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    hammer = p1.summon("TIME_209t")
    assert p1.weapon is hammer
    assert hammer.atk == 3
    pre_deck = len(p1.deck)
    # Use up the weapon entirely so it dies and its deathrattle fires.
    hammer.destroy()
    assert p1.weapon is None
    # A copy was shuffled into the deck with +2 Attack (now 5).
    assert len(p1.deck) == pre_deck + 1
    shuffled = [c for c in p1.deck if c.id == "TIME_209t"]
    assert len(shuffled) == 1
    assert shuffled[0].atk == 5


def test_avatar_form_buffs_attack_and_adds_cleave_on_attack():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    # A friendly minion to receive Avatar Form.
    wisp = p1.summon("CS2_231")  # 1/1 Wisp
    wisp.turns_in_play = 1  # clear summoning sickness so it can attack
    spell = p1.give("TIME_209t2")
    spell.play(target=wisp)
    assert wisp.atk == 3  # 1 + 2
    # Give the enemy hero and a minion lots of HP so the cleave is measurable.
    enemy = game.player2
    enemy_minion = enemy.summon("CS2_182")  # 4/5 Ogre
    enemy_minion.max_health = 20
    enemy_minion.damage = 0
    enemy.hero.max_health = 30
    enemy.hero.damage = 0
    # Attack the enemy minion; after the attack, deal 2 to all enemies.
    wisp.attack(enemy_minion)
    # enemy_minion took 3 (combat) + 2 (cleave) = 5; hero took 2 (cleave).
    assert enemy_minion.damage == 5
    assert enemy.hero.damage == 2


def test_primordial_overseer_no_nature_spell_held():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    overseer = p1.give("TIME_213")
    pre_hand = len(p1.hand)
    overseer.play()
    # No Nature spell cast while holding -> base 2/3, no draw.
    assert overseer.atk == 2
    assert overseer.health == 3
    # Hand: had overseer (now in play), no extra draw beyond normal play.
    assert len(p1.hand) == pre_hand - 1


def test_primordial_overseer_with_nature_spell_held():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    overseer = p1.give("TIME_213")
    # Cast a Nature spell (Static Shock) while holding the overseer.
    shock = p1.give("TIME_218")
    enemy_minion = game.player2.summon("CS2_182")
    shock.play(target=enemy_minion)
    _resolve_choices(p1)
    assert any(
        e[0] == "TIME_218" for e in getattr(overseer, "spells_history_while_holding", [])
    )
    pre_hand = len(p1.hand)
    overseer.play()
    assert overseer.atk == 3  # 2 + 1
    assert overseer.health == 4  # 3 + 1
    # Drew a card (and the overseer left hand): net hand size unchanged.
    assert len(p1.hand) == pre_hand


def test_flux_revenant_gains_buff_instead_of_nature_spell_damage():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    revenant = p1.summon("TIME_214")  # 1/4 Taunt
    assert revenant.atk == 1 and revenant.health == 4
    # Static Shock (Nature spell) targeting the revenant: it gains +2/+1
    # instead of taking 1 damage.
    shock = p1.give("TIME_218")
    shock.play(target=revenant)
    assert revenant.damage == 0
    assert revenant.atk == 3  # 1 + 2
    assert revenant.health == 5  # 4 + 1


def test_flux_revenant_takes_normal_damage_from_non_nature():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    revenant = p1.summon("TIME_214")  # 1/4
    # Frostbolt (Frost spell, 3 dmg) deals normal damage, no buff. The 1/4
    # survives (3 < 4) so we can read the exact damage.
    frostbolt = p1.give("CS2_024")
    frostbolt.play(target=revenant)
    assert revenant.atk == 1  # unbuffed (not a Nature spell)
    assert revenant.max_health == 4  # base max health unchanged (no +2/+1)
    assert revenant.damage == 3  # took the full Frostbolt hit


def test_stormrook_summons_5cost_instead_of_nature_damage():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    rook = p1.summon("TIME_217")  # 5/5
    pre_field = len(p1.field)
    shock = p1.give("TIME_218")
    shock.play(target=rook)
    # No damage; a random 5-Cost minion was summoned for the controller.
    assert rook.damage == 0
    assert len(p1.field) == pre_field + 1
    summoned = p1.field[-1]
    assert summoned is not rook
    assert summoned.cost == 5


# ---------------------------------------------------------------------------
# Spells
# ---------------------------------------------------------------------------


def test_instant_multiverse_summons_12_mana_of_minions():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    pre_field = len(p1.field)
    spell = p1.give("TIME_014")
    spell.play()
    _resolve_choices(p1)  # rewind choice; pick Keep (first card)
    summoned = p1.field[pre_field:]
    # Summoned at least one minion, and total cost summoned does not exceed
    # the 12-mana budget unless the board cap (7) was hit first.
    assert len(summoned) >= 1
    total = sum(db[c.id].cost or 0 for c in summoned)
    if len(p1.field) < game.MAX_MINIONS_ON_FIELD:
        # Board not full -> budget fully spent, total exactly 12.
        assert total == 12
    else:
        assert total <= 12


def test_lightning_rod_deals_2_to_friendly_and_4_to_enemy():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    friendly = p1.summon("CS2_182")  # 4/5 Ogre (survives 2)
    enemy = game.player2.summon("CS2_182")  # 4/5 Ogre (survives 4, only target)
    spell = p1.give("TIME_212")
    spell.play(target=friendly)
    assert friendly.damage == 2
    assert enemy.damage == 4


def test_thunderquake_hits_all_minions_and_grants_static_shock():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    m1 = p1.summon("CS2_182")
    m2 = game.player2.summon("CS2_182")
    spell = p1.give("TIME_215")
    spell.play()
    assert m1.damage == 1
    assert m2.damage == 1
    # Got a Static Shock (TIME_218) added to hand.
    assert any(c.id == "TIME_218" for c in p1.hand)


def test_nascent_bolt_draws_when_target_survives():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    # Give p1 a stocked deck to draw from.
    for _ in range(5):
        p1.give("CS2_231").shuffle_into_deck()
    target = game.player2.summon("CS2_182")  # 4/5, survives 5? no -> dies
    # Use a tanky target so 5 damage does NOT kill it.
    target.max_health = 10
    target.damage = 0
    spell = p1.give("TIME_216")
    pre_hand = len(p1.hand)
    spell.play(target=target)
    assert target.damage == 5
    assert len(p1.hand) == pre_hand - 1 + 2  # spell left, drew 2


def test_nascent_bolt_no_draw_when_target_dies():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    for _ in range(5):
        p1.give("CS2_231").shuffle_into_deck()
    target = game.player2.summon("CS2_182")
    target.max_health = 4
    target.damage = 0  # 4 health, 5 damage kills it
    spell = p1.give("TIME_216")
    pre_hand = len(p1.hand)
    spell.play(target=target)
    assert target.dead
    assert len(p1.hand) == pre_hand - 1  # spell left, no draw


def test_static_shock_damages_minion_and_buffs_hero():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    target = game.player2.summon("CS2_182")  # 4/5
    spell = p1.give("TIME_218")
    spell.play(target=target)
    assert target.damage == 1
    assert p1.hero.atk == 1  # +1 Attack this turn


# ---------------------------------------------------------------------------
# Across the Timeways mini-set (END_)
# ---------------------------------------------------------------------------


def test_haywire_hornswog_base_cost_no_overload():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    assert p1.overloaded_this_game == 0
    hornswog = p1.give("END_030")
    # Printed base cost is 6; no Overload this game -> no discount.
    assert hornswog.cost == 6
    # Elusive + Taunt come from data tags. Elusive is the ELUSIVE keyword tag
    # (honored in targeting.py), not the legacy cant_be_targeted_by_abilities.
    assert hornswog.taunt is True
    assert hornswog.data.tags.get(GameTag.ELUSIVE)


def test_haywire_hornswog_cost_drops_per_mana_crystal_overloaded():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    hornswog = p1.give("END_030")
    # 4 Mana Crystals Overloaded this game -> costs (4) less: 6 - 4 = 2.
    p1.overloaded_this_game = 4
    assert hornswog.cost == 2
    # Cost never goes below 0: overload 10 -> clamped to 0.
    p1.overloaded_this_game = 10
    assert hornswog.cost == 0
