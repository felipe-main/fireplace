"""Tests for Across the Timeways — MAGE (TIME_).

NOTE on the sibling-module stubs below: while the Across the Timeways set is
being authored class-by-class (in parallel), some sibling card files in the
``across_the_timeways`` package may be incomplete and fail to import, which
would block ``fireplace.cards.db.initialize()`` for the WHOLE package. To keep
this MAGE test runnable in isolation, we replace any sibling module that fails
to import with an empty stub BEFORE the card DB initializes. Modules that import
cleanly (including ``mage``) are left untouched. Once the whole set is complete
every module imports and the stubbing is a no-op.
"""

import importlib
import sys
import types

# Pre-import the package and stub only the siblings that currently fail.
_PKG = "fireplace.cards.across_the_timeways"
_SIBLINGS = [
    "deathknight",
    "demonhunter",
    "druid",
    "hunter",
    "paladin",
    "priest",
    "rogue",
    "shaman",
    "warlock",
    "warrior",
    "neutral",
]
for _m in _SIBLINGS:
    _name = _PKG + "." + _m
    if _name in sys.modules:
        continue
    try:
        importlib.import_module(_name)
    except Exception:
        sys.modules[_name] = types.ModuleType(_name)

import pytest  # noqa: E402
from hearthstone.enums import CardClass, CardType, Race, Zone  # noqa: E402

import fireplace.cards as cards  # noqa: E402

sys.path.insert(0, "tests")
from utils import prepare_game  # noqa: E402

YETI = "CS2_182"  # Chillwind Yeti 4/5 (fat vanilla target)
TWILIGHT_DRAKE = "EX1_043"  # 4/4 Dragon (no spellpower)


def _auto_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _beef(minion, hp=80):
    minion.max_health = hp
    minion.damage = 0
    return minion


# ---------------------------------------------------------------------------
# TIME_000 — Semi-Stable Portal (Rewind spell)
# "Rewind. Add a random minion to your hand. It costs (3) less."
# ---------------------------------------------------------------------------
def test_semi_stable_portal_base():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    spell = p.give("TIME_000")
    spell.play()
    # Engine offers the Rewind keep/rewind choice: choose KEEP so the effect
    # runs exactly once.
    while p.choice:
        keep = [c for c in p.choice.cards if c.id == "TIME_000ta"]
        p.choice.choose(keep[0] if keep else p.choice.cards[0])
    minions = [c for c in p.hand if c.type == CardType.MINION]
    assert len(minions) == 1
    added = minions[0]
    assert added.cost == max(0, cards.db[added.id].cost - 3)


def test_semi_stable_portal_rewind_reruns():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    spell = p.give("TIME_000")
    spell.play()
    # Choose REWIND: engine re-runs the play effect once more -> 2 minions.
    guard = 0
    while p.choice:
        rewind = [c for c in p.choice.cards if c.id == "TIME_000tb"]
        p.choice.choose(rewind[0] if rewind else p.choice.cards[0])
        guard += 1
        assert guard < 8
    minions = [c for c in p.hand if c.type == CardType.MINION]
    assert len(minions) == 2


# ---------------------------------------------------------------------------
# TIME_006 — Mirror Dimension
# "Summon a 0/4 minion with Taunt. If you are holding a Dragon, summon another."
# ---------------------------------------------------------------------------
def test_mirror_dimension_no_dragon():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    before = len(p.field)
    p.give("TIME_006").play()
    assert len(p.field) - before == 1
    m = p.field[-1]
    assert m.id == "TIME_006t1"
    assert (m.atk, m.health, m.taunt) == (0, 4, True)


def test_mirror_dimension_holding_dragon():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    p.give("TIME_852")  # a Dragon held in hand
    before = len(p.field)
    p.give("TIME_006").play()
    assert len(p.field) - before == 2
    assert all(m.id == "TIME_006t1" for m in p.field[-2:])


# ---------------------------------------------------------------------------
# TIME_855 — Arcane Barrage
# "Deal $3 damage to an enemy and $2 damage to two other random ones."
# ---------------------------------------------------------------------------
def test_arcane_barrage():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    # Exactly two other enemy characters available besides the chosen target,
    # both beefed to absorb their shot, and the enemy hero beefed too. The two
    # 2-damage shots are random among {minion B, minion C, enemy hero}, so we
    # assert the deterministic invariants: chosen target == 3, total == 7, and
    # the two 2-damage hits land on two DISTINCT other characters.
    ms = [_beef(p2.summon(YETI)) for _ in range(3)]
    _beef(p2.hero)
    p1.give("TIME_855").play(target=ms[0])
    assert ms[0].damage == 3
    others = [ms[1], ms[2], p2.hero]
    hit2 = [c for c in others if c.damage == 2]
    assert len(hit2) == 2  # two distinct other characters, each hit once for 2
    assert all(c.damage in (0, 2) for c in others)
    total = ms[0].damage + ms[1].damage + ms[2].damage + p2.hero.damage
    assert total == 7


# ---------------------------------------------------------------------------
# TIME_852 — Azure Queen Sindragosa (Fabled)
# "If you control another Dragon, your Arcane spells cost (2) less."
# ---------------------------------------------------------------------------
def test_sindragosa_arcane_discount():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    barrage = p.give("TIME_855")  # Arcane spell, base cost 3
    assert barrage.cost == 3
    # Sindragosa alone: no OTHER dragon -> no discount.
    p.summon("TIME_852")
    assert barrage.cost == 3
    # Add a second dragon -> aura now active -> -2.
    p.summon(TWILIGHT_DRAKE)
    assert barrage.cost == 1
    # A non-Arcane spell is unaffected.
    fireball = p.give("CS2_029")  # Fire school
    assert fireball.cost == cards.db["CS2_029"].cost


# ---------------------------------------------------------------------------
# TIME_852t1 — Azure King Malygos (token)
# "If you control another Dragon, your Arcane spells cast twice."
# ---------------------------------------------------------------------------
def test_malygos_arcane_casts_twice():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("TIME_852t1")  # Malygos
    p1.summon(TWILIGHT_DRAKE)  # another dragon -> aura active
    t = _beef(p2.summon(YETI))
    p1.give("TIME_855").play(target=t)  # Arcane Barrage, casts twice
    # Chosen target hit by 3 on each cast => exactly 6.
    assert t.damage == 6


def test_malygos_no_echo_without_dragon():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("TIME_852t1")  # Malygos alone, no other dragon
    t = _beef(p2.summon(YETI))
    p1.give("TIME_855").play(target=t)
    assert t.damage == 3


def test_malygos_fire_spell_not_echoed():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    p1.summon("TIME_852t1")
    p1.summon(TWILIGHT_DRAKE)
    t = _beef(p2.summon(YETI))
    fireball = p1.give("CS2_029")  # Fire spell, 6 damage, single cast only
    fireball.play(target=t)
    assert t.damage == 6


# ---------------------------------------------------------------------------
# TIME_852t3 — Azure Oathstone (token)
# "Summon your Dragons that died this game."
# ---------------------------------------------------------------------------
def test_azure_oathstone():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    d1 = p.summon(TWILIGHT_DRAKE)
    d2 = p.summon("TIME_856")  # Algeth'ar Instructor (Dragon)
    nondragon = p.summon(YETI)
    d1.destroy()
    d2.destroy()
    nondragon.destroy()
    game.process_deaths()
    before = len(p.field)
    p.give("TIME_852t3").play()
    summoned = [m.id for m in p.field[before:]]
    assert sorted(summoned) == sorted([TWILIGHT_DRAKE, "TIME_856"])
    assert YETI not in summoned


# ---------------------------------------------------------------------------
# TIME_856 — Algeth'ar Instructor
# "Spell Damage +2"
# ---------------------------------------------------------------------------
def test_algethar_instructor_spellpower():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    inst = p1.summon("TIME_856")
    assert (inst.atk, inst.health) == (4, 7)
    assert inst.spellpower == 2
    assert Race.DRAGON in inst.races
    t = _beef(p2.summon(YETI))
    p1.give("CS2_029").play(target=t)  # Fireball 6 + 2 spellpower = 8
    assert t.damage == 8


# ---------------------------------------------------------------------------
# TIME_857 — Alter Time
# "Discover two Arcane spells from the past. They cost (2) less."
# ---------------------------------------------------------------------------
def test_alter_time():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    p.give("TIME_857").play()
    resolved = 0
    while p.choice:
        # Every offered card must be an Arcane spell.
        for card in p.choice.cards:
            assert card.type == CardType.SPELL
            assert cards.db[card.id].spell_school.name == "ARCANE"
        p.choice.choose(p.choice.cards[0])
        resolved += 1
    assert resolved == 2
    added = list(p.hand)
    assert len(added) == 2
    for c in added:
        assert c.cost == max(0, cards.db[c.id].cost - 2)


# ---------------------------------------------------------------------------
# TIME_858 — Temporal Construct
# "Battlecry: Deal 5 damage to an enemy minion. Draw cards equal to the excess."
# ---------------------------------------------------------------------------
def test_temporal_construct_excess_draw():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(YETI)
    target.max_health = 3
    target.damage = 0  # 3 health -> 5 damage => excess 2
    hand_before = len(p1.hand)
    construct = p1.give("TIME_858")
    construct.play(target=target)
    assert target.zone == Zone.GRAVEYARD
    assert len(p1.hand) - hand_before == 2


def test_temporal_construct_no_excess():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    target = p2.summon(YETI)
    target.max_health = 9
    target.damage = 0  # 9 health -> 5 damage => 0 excess
    hand_before = len(p1.hand)
    p1.give("TIME_858").play(target=target)
    assert target.zone == Zone.PLAY
    assert target.damage == 5
    assert len(p1.hand) - hand_before == 0


# ---------------------------------------------------------------------------
# TIME_859 — Anomalize
# "Summon a random 10 and 1-Cost minion. Scramble their stats."
# ---------------------------------------------------------------------------
def test_anomalize_scrambles_stats():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.random.seed(0)
    p = game.player1
    before = len(p.field)
    p.give("TIME_859").play()
    summoned = p.field[before:]
    assert len(summoned) == 2
    a, b = summoned
    base_a = cards.db[a.id]
    base_b = cards.db[b.id]
    # Stats are swapped (scrambled): each minion now wears the OTHER's stats.
    assert (a.atk, a.health) == (base_b.atk, base_b.health)
    assert (b.atk, b.health) == (base_a.atk, base_a.health)
    # And one was a 10-cost, the other a 1-cost.
    assert sorted([base_a.cost, base_b.cost]) == [1, 10]


# ---------------------------------------------------------------------------
# TIME_860 — Faceless Enigma
# "Battlecry: Look at 2 random Secrets. Pick one to cast for yourself. The
#  other casts for your opponent."
# ---------------------------------------------------------------------------
def test_faceless_enigma_splits_secrets():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1, p2 = game.player1, game.player2
    s1, s2 = len(p1.secrets), len(p2.secrets)
    enigma = p1.give("TIME_860")
    enigma.play()
    assert p1.choice is not None
    assert len(p1.choice.cards) == 2
    _auto_choices(p1)
    # Exactly one secret armed for me, one for my opponent.
    assert len(p1.secrets) - s1 == 1
    assert len(p2.secrets) - s2 == 1


# ---------------------------------------------------------------------------
# TIME_861 — Timelooper Toki
# "Battlecry: Get 4 random spells from the past. When you play ALL 4, get
#  another Timelooper Toki."
# ---------------------------------------------------------------------------
def _force_play(player, spell, game):
    """Best-effort REAL play of an arbitrary marked spell: zero its cost and
    supply a target when one is required (Choose One spells are skipped — they
    need an explicit sub-card pick, so the seed search just moves on). Returns
    True iff the spell actually played through the normal Play pipeline (which
    is what fires the Toki listener)."""
    if getattr(spell, "must_choose_one", False):
        return False
    spell.cost = 0
    try:
        if spell.requires_target():
            targets = spell.targets
            if not targets:
                return False
            spell.play(target=targets[0])
        else:
            spell.play()
    except Exception:
        return False
    _auto_choices(player)
    return True


def test_toki_gives_four_spells():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p = game.player1
    for c in list(p.hand):
        c.discard()
    p.give("TIME_861").play()
    _auto_choices(p)
    marked = [c for c in p.hand if getattr(c, "_toki_group", None) == 0]
    assert len(marked) == 4
    assert all(c.type == CardType.SPELL for c in marked)


def _run_toki_full(seed):
    """Play Toki, then play ALL 4 marked spells. Returns (played, new_tokis,
    groups) for one game seeded with `seed`. Used to find a seed where all four
    random spells happen to be castable so we can assert the exact outcome."""
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.random.seed(seed)
    p1, p2 = game.player1, game.player2
    for c in list(p1.hand):
        c.discard()
    # Fat targets on both sides so any target-requiring marked spell resolves.
    for _ in range(3):
        _beef(p2.summon(YETI), 90)
    for _ in range(2):
        _beef(p1.summon(YETI), 90)
    p1.give("TIME_861").play()
    _auto_choices(p1)
    marked = [c for c in list(p1.hand) if getattr(c, "_toki_group", None) == 0]
    if len(marked) != 4:
        return 0, [], dict(getattr(p1, "_toki_groups", {}))
    played = 0
    for spell in marked:
        if spell in p1.hand and _force_play(p1, spell, game):
            played += 1
    new_tokis = [c for c in p1.hand if c.id == "TIME_861"]
    return played, new_tokis, dict(getattr(p1, "_toki_groups", {}))


def test_toki_playing_all_four_makes_new_toki():
    # Find a seed where all four random spells are fully castable, then assert
    # the exact loop outcome: 4 plays -> group 0 exhausted -> 1 fresh Toki.
    for seed in range(80):
        try:
            played, new_tokis, groups = _run_toki_full(seed)
        except Exception:
            continue
        # Require a clean run: all 4 marked spells played AND their group
        # closed out (some random spells transform/replace themselves on play,
        # so their Play broadcast card no longer carries the Toki marker — skip
        # those seeds rather than weaken the assertion).
        if played == 4 and 0 not in groups:
            assert len(new_tokis) == 1
            return
    pytest.fail("no seed produced 4 cleanly-tracked Toki spells")


def test_toki_partial_play_no_new_toki():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    game.random.seed(7)
    p1, p2 = game.player1, game.player2
    for c in list(p1.hand):
        c.discard()
    for _ in range(3):
        _beef(p2.summon(YETI), 90)
    p1.give("TIME_861").play()
    _auto_choices(p1)
    marked = [c for c in list(p1.hand) if getattr(c, "_toki_group", None) == 0]
    # Play at most three of the four — never enough to complete the group.
    count = 0
    for spell in marked:
        if count >= 3:
            break
        if spell in p1.hand and _force_play(p1, spell, game):
            count += 1
    # Fewer than 4 played -> no new Toki, group still pending.
    assert [c for c in p1.hand if c.id == "TIME_861"] == []
    assert p1._toki_groups.get(0, 0) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
