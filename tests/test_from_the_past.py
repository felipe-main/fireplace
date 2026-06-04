"""'From the past' pools must be Wild-inclusive.

Cards whose printed text says "...from the past" (e.g. Time-Lost Glaive) draw
from the full historic Wild pool — every collectible card of the matching type
ever printed, INCLUDING today's Standard cards. The engine models this with a
`from_past=True` flag on the random picker that suppresses the auto-Standard
narrowing inside a Standard game (fireplace/dsl/random_picker.py).

These tests force a Standard game (both players all-Standard) — the only mode in
which the narrowing would otherwise bite — and assert the pool stays Wild-wide.
"""

import os

from hearthstone.enums import CardClass, CardType, Race, Rarity, SpellSchool

import fireplace.cards as _cards
from fireplace.dsl.random_picker import (
    RandomBeast,
    RandomDemon,
    RandomDragon,
    RandomElemental,
    RandomLegendaryMinion,
    RandomMinion,
    RandomSpell,
    RandomWeapon,
    _bare_card_id,
)


def _card_keys(ids):
    """Collapse reprint aliases (CORE_/VAN_) to one key per printable card, so
    reachability is compared at the card level — the random pool now offers each
    printable card under a single id (see _dedupe_reprints)."""
    return {_bare_card_id(i) for i in ids}

from utils import prepare_empty_game


def _standard_game():
    """A game forced Standard on both sides (so game.is_standard is True)."""
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.is_standard = True
    game.player2.is_standard = True
    assert game.is_standard
    return game


def _wild_game():
    """A game where at least one side is non-Standard (game.is_standard False)."""
    game = prepare_empty_game(CardClass.MAGE, CardClass.MAGE)
    game.player1.is_standard = False
    game.player2.is_standard = False
    assert not game.is_standard
    return game


# ---------------------------------------------------------------------------
# Engine flag — the single mechanism every "from the past" card routes through.
# ---------------------------------------------------------------------------


def test_from_past_flag_demon_pool():
    src = _standard_game().player1.hero

    # Compare at printable-card level: the Standard pool keeps a reprinted card
    # under its Standard-legal id, while the from_past (Wild) pool dedupes
    # reprint aliases — so raw ids differ but the card sets nest correctly.
    narrowed = _card_keys(RandomDemon().find_cards(src))           # auto Standard
    full = _card_keys(RandomDemon(from_past=True).find_cards(src))  # from_past

    # The flag genuinely widens the pool inside a Standard game.
    assert narrowed < full

    # Mal'Ganis (GVG_021) is a Wild-only Demon: present only with from_past.
    # (narrowed is exactly the Standard card set, so full - narrowed is the
    # Wild-only widening.)
    assert "GVG_021" in full
    assert "GVG_021" not in narrowed

    # Sargeras (TTN_960, a Titan tagged DONT_PICK_FROM_SUBSETS) stays excluded
    # even with from_past — "from the past" widens by format, not past the bans.
    assert "TTN_960" not in full


def test_from_past_pool_dedupes_reprint_aliases():
    # A Wild pool must offer each printable card ONCE — not 2-3x for cards that
    # also have a CORE_/VAN_ reprint (which would inflate their pick weight).
    src = _standard_game().player1.hero
    pool = RandomDemon(from_past=True).find_cards(src)
    # No two ids in the pool collapse to the same printable card.
    keys = [_bare_card_id(i) for i in pool]
    assert len(keys) == len(set(keys)), "pool still contains reprint duplicates"
    # And no entry sits under more than one of {bare, CORE_x, VAN_x}.
    assert len(pool) == len(set(keys))
    # Concretely: Voidwalker (CS2_065) appears once, not three times (it has both
    # a VAN_ and a CORE_ reprint).
    assert sum(1 for i in pool if _bare_card_id(i) == "CS2_065") == 1


def test_from_past_equals_wild_baseline():
    """from_past in a Standard game == the same picker in a non-Standard game.

    Proves the flag produces exactly the Wild pool, for every picker family the
    19 cards use — independent of any one card's wiring.
    """
    families = {
        "minion": lambda **kw: RandomMinion(**kw),
        "minion_cost5": lambda **kw: RandomMinion(cost=5, **kw),
        "demon": lambda **kw: RandomDemon(**kw),
        "dragon": lambda **kw: RandomDragon(**kw),
        "elemental": lambda **kw: RandomElemental(**kw),
        "beast_legendary": lambda **kw: RandomBeast(rarity=Rarity.LEGENDARY, **kw),
        "legendary_minion": lambda **kw: RandomLegendaryMinion(**kw),
        "weapon_pal": lambda **kw: RandomWeapon(card_class=CardClass.PALADIN, **kw),
        "spell": lambda **kw: RandomSpell(**kw),
        "spell_arcane": lambda **kw: RandomSpell(spell_school=SpellSchool.ARCANE, **kw),
        "spell_nature": lambda **kw: RandomSpell(spell_school=SpellSchool.NATURE, **kw),
        "secret": lambda **kw: RandomSpell(secret=True, **kw),
    }
    std_src = _standard_game().player1.hero
    wild_src = _wild_game().player1.hero

    for name, factory in families.items():
        past_in_standard = set(factory(from_past=True).find_cards(std_src))
        wild_baseline = set(factory().find_cards(wild_src))
        narrowed = set(factory().find_cards(std_src))

        # from_past reproduces the full Wild pool. Dedup is scoped to from_past
        # pools, so the from_past pool collapses reprint aliases while the plain
        # Wild-game baseline does not — compare at printable-card level.
        assert _card_keys(past_in_standard) == _card_keys(wild_baseline), (
            f"{name}: from_past != wild pool"
        )
        # …and that pool is strictly wider than the Standard-narrowed one.
        assert _card_keys(narrowed) < _card_keys(past_in_standard), (
            f"{name}: from_past did not widen"
        )


# ---------------------------------------------------------------------------
# The three cards that previously did "from the past" WRONG (Wild-ONLY, i.e.
# they excluded Standard cards). The fix must let Standard cards back in.
# Pickers here mirror the card scripts exactly.
# ---------------------------------------------------------------------------


def _standard_members(predicate):
    """Printable cards (reprint aliases collapsed) that are Standard-legal and
    match predicate."""
    return {
        _bare_card_id(cid)
        for cid, c in _cards.db.items()
        if c.collectible
        and getattr(c, "is_standard", False)
        and predicate(c)
    }


def test_eroded_sediment_pool_includes_standard_elementals():
    # WW_428: was RandomElemental(is_standard=False) -> Wild-only (bug).
    src = _standard_game().player1.hero
    pool = set(RandomElemental(from_past=True).find_cards(src))
    standard_elementals = _standard_members(
        lambda c: c.type == CardType.MINION and Race.ELEMENTAL in c.races
    )
    assert standard_elementals  # sanity: Standard Elementals exist
    # Previously every one of these was wrongly excluded; now they're eligible.
    assert standard_elementals <= _card_keys(pool)


def test_unpopular_has_been_pool_includes_standard_5cost():
    # ETC_349: was a custom pool filtered to `not is_standard` -> Wild-only.
    src = _standard_game().player1.hero
    pool = set(RandomMinion(cost=5, from_past=True).find_cards(src))
    standard_5cost = _standard_members(
        lambda c: c.type == CardType.MINION and (c.cost or 0) == 5
    )
    assert standard_5cost
    assert standard_5cost <= _card_keys(pool)


def test_hemet_pool_includes_standard_legendary_beasts():
    # TOY_355: was a custom pool filtered to `not is_standard` -> Wild-only.
    src = _standard_game().player1.hero
    pool = set(RandomBeast(rarity=Rarity.LEGENDARY, from_past=True).find_cards(src))
    standard_leg_beasts = _standard_members(
        lambda c: c.type == CardType.MINION
        and Race.BEAST in c.races
        and c.rarity == Rarity.LEGENDARY
    )
    assert standard_leg_beasts
    assert standard_leg_beasts <= _card_keys(pool)


# ---------------------------------------------------------------------------
# Regression net for all 19 implemented "from the past" cards: every script
# must carry the from_past flag and none may use the old (wrong) idioms.
# ---------------------------------------------------------------------------


# (id -> relative source file) for every implemented "from the past" card.
FROM_PAST_CARDS = {
    "TIME_444": "across_the_timeways/demonhunter.py",
    "TIME_040": "across_the_timeways/neutral.py",
    "TIME_052": "across_the_timeways/neutral.py",
    "TIME_016": "across_the_timeways/paladin.py",
    "TIME_711": "across_the_timeways/rogue.py",
    "TIME_013": "across_the_timeways/shaman.py",
    "TIME_857": "across_the_timeways/mage.py",
    "TIME_861": "across_the_timeways/mage.py",
    "TIME_704": "across_the_timeways/druid.py",
    "TIME_707": "across_the_timeways/druid.py",
    "END_027": "across_the_timeways/priest.py",
    "TTN_484": "titans/priest.py",
    "VAC_336": "perils_in_paradise/rogue.py",
    "WON_040": "wonders/mage.py",
    "GDB_857": "the_great_dark_beyond/druid.py",
    "MIS_700": "whizbangs_workshop/paladin.py",
    "MIS_701": "whizbangs_workshop/shaman.py",
    "WW_428": "showdown_in_the_badlands/neutral_common.py",
    "ETC_349": "festival_of_legends/neutral.py",
    "TOY_355": "whizbangs_workshop/hunter.py",
}

_CARDS_DIR = os.path.join(os.path.dirname(_cards.__file__))


def test_every_from_past_card_is_scripted_and_uses_the_flag():
    # All 19 are implemented and route through from_past — guards against a
    # future card or refactor silently dropping the flag.
    for cid, relpath in FROM_PAST_CARDS.items():
        assert cid in _cards.db, f"{cid} missing from data"
        src = open(os.path.join(_CARDS_DIR, *relpath.split("/")), encoding="utf-8").read()
        assert "from_past=True" in src, f"{relpath} no longer wires from_past"


def test_no_legacy_from_past_idioms_in_these_cards():
    # The superseded hacks must be gone from the 19 "from the past" scripts:
    #   is_standard=None / is_standard=False  (manual filter fiddling)
    #   not getattr(c, "is_standard"          (hand-rolled Wild-only pools)
    # (Scoped to these files only — other cards use is_standard for unrelated,
    # legitimate set-specific pools, e.g. "first-edition" / Wild-flashback cards.)
    bad = ('is_standard=None', 'is_standard=False', 'not getattr(c, "is_standard"')
    for relpath in set(FROM_PAST_CARDS.values()):
        text = open(os.path.join(_CARDS_DIR, *relpath.split("/")), encoding="utf-8").read()
        for token in bad:
            assert token not in text, f"{relpath} still uses `{token}`"
