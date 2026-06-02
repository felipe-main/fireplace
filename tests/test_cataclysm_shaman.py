import importlib.util
import os
import sys

import fireplace.cards as _C

# Bootstrap: while sibling Cataclysm class files are still being authored in
# parallel, the package's `__init__.py` star-import chain can abort before
# reaching shaman.py, leaving our CATA_ shaman scripts unloaded. Patch
# get_script_definition to source the shaman scripts directly from this file's
# sibling module so this test suite is runnable in isolation. The shim is a
# no-op once the package imports cleanly (orig already returns our class).
_SHAMAN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "fireplace", "cards", "cataclysm", "shaman.py",
)
if not getattr(_C, "_cata_shaman_shim", False):
    import fireplace.cards.utils  # noqa: F401  (ensure relative imports resolve)
    _spec = importlib.util.spec_from_file_location(
        "fireplace.cards.cataclysm._cata_shaman_only", _SHAMAN_PATH
    )
    _mod = importlib.util.module_from_spec(_spec)
    _mod.__package__ = "fireplace.cards.cataclysm"
    sys.modules["_cata_shaman_only"] = _mod
    _spec.loader.exec_module(_mod)
    _orig_gsd = _C.get_script_definition

    def _patched_gsd(id, card=None):
        if id.startswith("CATA_") and hasattr(_mod, id):
            cls = getattr(_mod, id)
            if [a for a in dir(cls) if not a.startswith("__")]:
                return cls
        return _orig_gsd(id, card)

    _C.get_script_definition = _patched_gsd
    _C._cata_shaman_shim = True

from hearthstone.enums import CardClass, CardType, Zone, GameTag

from utils import prepare_game


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def test_alakir_battlecry_and_colossal():
    # Al'Akir: Colossal +2 (two Charged Hand limbs) + Battlecry: get 2 minions
    # with Cost == Attack (8), each costing (1).
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    alakir = p1.summon("CATA_153")  # summon -> still runs Colossal limb hook
    # Colossal: two limbs flanking Al'Akir.
    limbs = [m for m in p1.field if m.id in ("CATA_153t", "CATA_153t1")]
    assert len(limbs) == 2
    # Battlecry only fires when played; play a fresh copy from hand.
    p1.discard_hand()
    card = p1.give("CATA_153")
    card.play()
    _resolve_choices(p1)
    gained = [c for c in p1.hand if c.type == CardType.MINION]
    assert len(gained) == 2
    # "Get 2 minions with Cost equal to this minion's Attack." Both are drawn
    # from the same Attack bucket, so they share one printed Cost; "They cost
    # (1)" buffs the effective Cost down to 1.
    assert gained[0].data.cost == gained[1].data.cost
    for c in gained:
        assert c.cost == 1


def test_alakir_charged_hand_aura():
    # Charged Hand of Al'Akir: adjacent minions have +1 Attack.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    left = p1.summon("CS2_125")   # Ironfur Grizzly 3/3
    hand = p1.summon("CATA_153t")
    right = p1.summon("CS2_125")
    # left and right flank the Charged Hand
    assert p1.field.index(hand) == 1
    assert left.atk == 3 + 1
    assert right.atk == 3 + 1


def test_ritual_of_power():
    # Herald {0}. Get two 1/1 Elementals with Rush.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    assert p1.heralds_this_game == 0
    card = p1.give("CATA_561")
    card.play()
    assert p1.heralds_this_game == 1
    breezlings = [c for c in p1.hand if c.id == "CATA_561t"]
    assert len(breezlings) == 2
    assert all(c.data.tags.get(GameTag.RUSH, 0) for c in breezlings)


def test_skywall_sentinel_herald():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    card = p1.give("CATA_565")
    card.play()
    assert p1.heralds_this_game == 1
    assert card.taunt


def test_crackling_cloudstrider_absorb_and_cast():
    # Battlecry absorbs an eligible (<=4 cost) hand spell; deathrattle casts it.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    p1.discard_hand()
    # Only one eligible spell: Lightning Bolt (1 mana, deal 3) targets enemy.
    spell = p1.give("EX1_238")  # Lightning Bolt: 3 damage, Overload (1)
    crackling = p1.give("CATA_563")
    crackling.play()
    # Spell absorbed (removed from hand).
    assert spell.zone == Zone.GRAVEYARD or spell not in p1.hand
    assert getattr(crackling, "_absorbed_spell", None) == "EX1_238"
    enemy_hp = p2.hero.health
    crackling.destroy()
    game.process_deaths()
    # Deathrattle cast the bolt at the enemy hero (no other target).
    assert p2.hero.health == enemy_hp - 3


def test_air_support():
    # Give a friendly minion Mega-Windfury; it can't attack heroes.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    target = p1.summon("CS2_125")  # 3/3
    card = p1.give("CATA_564")
    card.play(target=target)
    assert target.mega_windfury
    assert target.cannot_attack_heroes
    assert target.max_attacks == 4


def test_ascendance_transform_and_deathrattle():
    # Transform all friendly minions into ones that cost (1) more; they summon
    # the originals when they die.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    orig = p1.summon("CS2_171")  # Stonetusk Boar, 1 cost
    card = p1.give("CATA_567")
    card.play()
    _resolve_choices(p1)
    field = list(p1.field)
    assert len(field) == 1
    morphed = field[0]
    assert morphed.id != "CS2_171"
    assert (morphed.cost or 0) == 2  # 1 + 1
    assert morphed.has_deathrattle
    morphed.destroy()
    game.process_deaths()
    # Original summoned back.
    assert any(m.id == "CS2_171" for m in p1.field)


def test_ascendance_transforms_again_on_second_cast():
    # Regression: a persistent per-minion `_ascended` flag used to block a
    # SECOND Ascendance in the same game (the already-morphed minions kept the
    # flag), so the second cast transformed nothing. Each cast must transform
    # all current friendly minions.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.summon("CS2_171")  # 1-cost Boar
    p1.give("CATA_567").play()
    _resolve_choices(p1)
    after_first = [m.id for m in p1.field]
    assert after_first and after_first[0] != "CS2_171"
    first_id = after_first[0]
    # Second Ascendance must transform the (already-morphed) minion again.
    p1.give("CATA_567").play()
    _resolve_choices(p1)
    after_second = [m.id for m in p1.field]
    assert len(after_second) == 1
    assert after_second[0] != first_id  # genuinely re-transformed


def test_muradin_cost_reduction():
    # Costs (1) less per friendly attack this game.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1, p2 = game.player1, game.player2
    muradin = p1.give("CATA_568")
    assert muradin.cost == 9
    # A friendly minion attacks (clear summoning sickness first).
    attacker = p1.summon("CS2_125")  # 3/3
    attacker.turns_in_play = 1
    attacker.attack(p2.hero)
    assert getattr(muradin, "_muradin_attacks", 0) == 1
    assert muradin.cost == 8


def test_muradin_draws_two():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    for _ in range(5):
        p1.give("CS2_171")  # stack deck-independent? no — fill via deck
    pre = len(p1.hand)
    card = p1.give("CATA_568")
    card.play()
    # Drew 2 (net: -1 for playing Muradin, +2 draws).
    assert len(p1.hand) == pre + 2


def test_ceremonial_clash():
    # Summon a random 3, 2, and 1-Cost minion. Overload: (1).
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    pre = len(p1.field)
    card = p1.give("CATA_569")
    card.play()
    _resolve_choices(p1)
    summoned = p1.field[pre:]
    assert len(summoned) == 3
    costs = sorted(m.data.cost for m in summoned)
    assert costs == [1, 2, 3]
    assert p1.overloaded == 1


def test_morchok_cost_reduction():
    # Draw a card, reduce its cost by (10), repeat with excess.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    # Put a single known card on top of deck: a 4-cost minion.
    target = p1.card("CS2_182")  # Chillwind Yeti, 4 cost
    target.zone = Zone.DECK
    card = p1.give("CATA_570")
    card.play()
    _resolve_choices(p1)
    drawn = next((c for c in p1.hand if c.id == "CS2_182"), None)
    assert drawn is not None
    assert drawn.cost == 0  # 4 - 10 clamps to 0


def test_stormbinder_unlock_overload():
    # Deathrattle: unlock overloaded mana.
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.overloaded = 2
    p1.overload_locked = 2
    binder = p1.summon("CATA_724")
    binder.destroy()
    game.process_deaths()
    assert p1.overloaded == 0
    assert p1.overload_locked == 0


def test_rehgar_stats():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    rehgar = game.player1.summon("CORE_CATA_004")
    assert rehgar.atk == 3 and rehgar.health == 5 and rehgar.cost == 5


def test_rehgar_gives_lightning_bolt_when_self_attacks():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    rehgar = p1.summon("CORE_CATA_004")  # 3/5
    # Clear summoning sickness so Rehgar can attack.
    game.end_turn()
    game.end_turn()
    assert rehgar.can_attack()
    p2 = game.player2
    victim = p2.summon("CS2_182")  # 4/5
    victim.max_health = 30
    victim.damage = 0
    pre = len(p1.hand)
    rehgar.attack(victim)
    # After Rehgar attacks: exactly one Lightning Bolt (EX1_238) added to hand.
    assert len(p1.hand) == pre + 1
    bolt = p1.hand[-1]
    assert bolt.id == "EX1_238"


def test_rehgar_gives_bolt_when_adjacent_minion_attacks():
    game = prepare_game(CardClass.SHAMAN, CardClass.SHAMAN)
    p1 = game.player1
    p1.discard_hand()
    rehgar = p1.summon("CORE_CATA_004")
    neighbor = p1.summon("CS2_182")  # adjacent 4/5
    game.end_turn()
    game.end_turn()
    assert neighbor.can_attack()
    p2 = game.player2
    victim = p2.summon("CS2_182")
    victim.max_health = 30
    victim.damage = 0
    pre = len(p1.hand)
    neighbor.attack(victim)
    # Adjacent minion attacked -> Rehgar grants a Lightning Bolt.
    assert len(p1.hand) == pre + 1
    assert p1.hand[-1].id == "EX1_238"
