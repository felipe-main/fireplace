"""Into the Emerald Dream — the real ten-gift "Dark Gift" Nightmare pool.

Each Dark Gift is applied deterministically via `apply_dark_gift` (bypassing
the random roll in `_GiveDarkGift`) so every gift's exact effect is asserted.
See fireplace/cards/emerald_dream/_dark_gift.py.
"""

from utils import *

from hearthstone.enums import GameTag, Zone

from fireplace.cards.emerald_dream._dark_gift import (
    apply_dark_gift, eligible_gifts,
    WAKING_TERROR, WELL_RESTED, SHORT_CLAWS, BUNDLED_UP, LIVING_NIGHTMARE,
    SLEEPWALKER, RUDE_AWAKENING, SWEET_DREAMS, PERSISTING_HORROR, HARPYS_TALONS,
)

WISP = "CS2_231"        # 1/1 vanilla
YETI = "CS2_182"        # Chillwind Yeti 4/5 vanilla
TIDEHUNTER = "EX1_506"  # Murloc Tidehunter — Battlecry: Summon a 1/1 Murloc Scout
SCOUT = "EX1_506a"      # Murloc Scout 1/1


def _gift(p, minion_id, gift):
    """Summon a minion and apply a specific Dark Gift to it; return the minion."""
    m = p.summon(minion_id)
    apply_dark_gift(p.hero, m, gift)
    return m


def test_waking_terror_plus3_attack_and_lifesteal():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, WISP, WAKING_TERROR)  # 1/1 base
    assert m.atk == 1 + 3
    assert m.max_health == 1
    assert m.lifesteal


def test_well_rested_plus2_2_and_elusive():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, WISP, WELL_RESTED)
    assert (m.atk, m.max_health) == (1 + 2, 1 + 2)
    # Elusive == can't be targeted by spells (abilities) or hero powers.
    assert m.cant_be_targeted_by_abilities
    assert m.cant_be_targeted_by_hero_powers


def test_short_claws_minus2_attack_and_minus2_cost():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, YETI, SHORT_CLAWS)  # 4/5, cost 4
    assert m.atk == 4 - 2
    assert m.max_health == 5
    assert m.cost == 4 - 2


def test_bundled_up_plus4_health_and_taunt():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, WISP, BUNDLED_UP)
    assert m.atk == 1
    assert m.max_health == 1 + 4
    assert m.taunt


def test_sleepwalker_grants_charge():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, YETI, SLEEPWALKER)
    assert m.charge
    assert (m.atk, m.max_health) == (4, 5)  # no stat change


def test_harpys_talons_divine_shield_and_windfury():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, WISP, HARPYS_TALONS)
    assert m.divine_shield
    assert m.windfury


def test_persisting_horror_grants_reborn():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    m = _gift(game.player1, WISP, PERSISTING_HORROR)
    assert m.reborn


def test_living_nightmare_summons_2_2_copy_on_play():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    yeti = p1.give(YETI)
    apply_dark_gift(p1.hero, yeti, LIVING_NIGHTMARE)
    assert yeti._living_nightmare
    yeti.play()
    yetis = [m for m in p1.field if m.id == YETI]
    # The original 4/5 plus a 2/2 copy.
    assert len(yetis) == 2
    copies = sorted((m.atk, m.max_health) for m in yetis)
    assert copies == [(2, 2), (4, 5)]


def test_sweet_dreams_buffs_and_moves_to_top_of_deck():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    p1.discard_hand()
    p1.deck[:] = []
    wisp = p1.give(WISP)  # in hand, 1/1
    apply_dark_gift(p1.hero, wisp, SWEET_DREAMS)
    # +4/+5 applied and the card relocated to the TOP of the deck (deck[-1]).
    assert (wisp.atk, wisp.max_health) == (1 + 4, 1 + 5)
    assert wisp.zone == Zone.DECK
    assert wisp not in p1.hand
    assert p1.deck[-1] is wisp


def test_rude_awakening_battlecry_triggers_twice():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    tide = p1.give(TIDEHUNTER)  # Battlecry: summon a 1/1 Murloc Scout
    assert tide.has_battlecry
    apply_dark_gift(p1.hero, tide, RUDE_AWAKENING)
    assert tide._battlecries_twice
    tide.play()
    scouts = [m for m in p1.field if m.id == SCOUT]
    # Battlecry fired twice -> two Murloc Scouts instead of one.
    assert len(scouts) == 2


def test_eligibility_skips_no_op_gifts():
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.player1
    # A vanilla 1/1 (atk 1, <3, no keywords, no battlecry): Short Claws (needs
    # 3+ Attack) and Rude Awakening (needs a Battlecry) are NOT offered.
    wisp = p1.summon(WISP)
    elig = eligible_gifts(wisp)
    assert SHORT_CLAWS not in elig
    assert RUDE_AWAKENING not in elig
    # ...but Sleepwalker (atk >= 1) and the always-on gifts are.
    assert SLEEPWALKER in elig
    assert LIVING_NIGHTMARE in elig and SWEET_DREAMS in elig

    # Already-Taunt minion is never offered Bundled Up; already-Lifesteal is
    # never offered Waking Terror.
    from fireplace.actions import SetTags
    game.queue_actions(p1.hero, [SetTags(wisp, {GameTag.TAUNT: True})])
    assert BUNDLED_UP not in eligible_gifts(wisp)