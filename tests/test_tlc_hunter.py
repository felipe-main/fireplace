"""The Lost City of Un'Goro — HUNTER unit tests.

Concurrency note: this set's sibling card modules (rogue/neutral/...) may be
edited by other agents while this file runs. To keep these tests hermetic
against an in-flux sibling that fails to import, we stub the other
the_lost_city class modules with empty modules BEFORE the cards package is
imported. Only hunter.py (the module under test) and the already-stable base
sets load. This shim is a no-op once the siblings are complete.
"""

import sys
import types

for _sib in (
    "demonhunter", "rogue", "shaman", "warlock", "paladin",
    "neutral", "priest", "warrior", "druid", "mage", "deathknight",
):
    _name = "fireplace.cards.the_lost_city." + _sib
    sys.modules.setdefault(_name, types.ModuleType(_name))

from utils import prepare_game

from hearthstone.enums import CardClass, CardType, Race, Zone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Vanilla beasts keyed by Attack (used to drive Kindred / quest / etc.)
BEAST_1ATK = "BAR_031"   # Sunscale Raptor 1/1/3
BEAST_3ATK = "BAR_325"   # Razorboar 2/3/2
BEAST_5ATK = "AT_039"    # Savage Combatant 4/5/4
BEAST_7ATK = "TSC_935"   # Selfish Shellfish 4/7/7
PLAIN_BEAST = "CS2_172"  # Bloodfen Raptor 3/2 (Beast)
ARCANE_SHOT = "DS1_185"  # 1-Cost "Deal $2 damage" (Hunter)


def _resolve_choices(player):
    while player.choice:
        player.choice.choose(player.choice.cards[0])


def _play_beast_last_turn(game, player, beast_id=PLAIN_BEAST):
    """Play a Beast, then advance two turns so its race counts as 'played last
    turn' for Kindred."""
    player.give(beast_id).play()
    game.end_turn()
    game.end_turn()


# ---------------------------------------------------------------------------
# TLC_366 — Pterrorwing Ravager (Rush; Kindred: Costs (2) less.)
# ---------------------------------------------------------------------------

def test_pterrorwing_ravager_kindred_discount():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    base = p1.give("TLC_366").cost          # full cost (no Kindred yet)
    _play_beast_last_turn(game, p1)
    assert Race.BEAST in p1.races_played_last_turn
    rav = p1.give("TLC_366")
    assert rav.cost == base - 2


def test_pterrorwing_ravager_no_kindred_full_cost():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    rav = p1.give("TLC_366")
    base = rav.cost
    # No matching type last turn -> full cost.
    assert Race.BEAST not in p1.races_played_last_turn
    assert rav.cost == base


# ---------------------------------------------------------------------------
# TLC_822 — Dinositter (end of turn: -1 Cost to a random Beast in hand)
# ---------------------------------------------------------------------------

def test_dinositter_reduces_beast_cost_at_turn_end():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    for c in list(p1.hand):
        c.discard()
    beast = p1.give(PLAIN_BEAST)
    cost0 = beast.cost
    p1.summon("TLC_822")
    game.end_turn()                          # own turn end fires the trigger
    assert beast.cost == cost0 - 1


# ---------------------------------------------------------------------------
# TLC_823 — Cower in Fear (Deal 3 to a minion; next Beast costs (2) less)
# ---------------------------------------------------------------------------

def test_cower_in_fear_damage_and_discount():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    target = p1.opponent.summon("CS2_182")   # Chillwind Yeti 4/5
    p1.give("TLC_823").play(target=target)
    assert target.damage == 3                # exactly 3, survives

    beast = p1.give(PLAIN_BEAST)
    cost = beast.cost
    p1.max_mana = 10
    p1.used_mana = 0
    beast.play()
    # Paid (cost) then refunded min(cost, 2) -> net used_mana = cost - 2.
    assert p1.used_mana == max(0, cost - 2)


def test_cower_in_fear_discount_only_first_beast():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    target = p1.opponent.summon("CS2_182")
    p1.give("TLC_823").play(target=target)
    p1.max_mana = 10
    p1.used_mana = 0
    first = p1.give(PLAIN_BEAST)
    c1 = first.cost
    first.play()
    after_first = p1.used_mana                # = c1 - 2
    second = p1.give(PLAIN_BEAST)
    c2 = second.cost
    second.play()
    # Second Beast pays full price (no remaining discount).
    assert p1.used_mana == after_first + c2


# ---------------------------------------------------------------------------
# TLC_824 — Odd Map (Discover odd-Attack Beast; if played, pick one of others)
# ---------------------------------------------------------------------------

def test_odd_map_discovers_odd_attack_beasts():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    for c in list(p1.hand):
        c.discard()
    p1.give("TLC_824").play()
    assert p1.choice is not None
    cards = p1.choice.cards
    assert len(cards) == 3
    assert all(c.atk % 2 == 1 for c in cards)
    assert all(Race.BEAST in c.races for c in cards)


def test_odd_map_second_pick_when_played():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    for c in list(p1.hand):
        c.discard()
    p1.give("TLC_824").play()
    chosen = p1.choice.cards[0]
    runners = sorted(c.id for c in p1.choice.cards if c is not chosen)
    p1.choice.choose(chosen)

    given = next(c for c in p1.hand if c.id == chosen.id)
    p1.max_mana = 10
    p1.used_mana = 0
    hand_before = len(p1.hand)
    given.play()
    # Playing the Discovered Beast offers a second Discover of the two runners.
    assert p1.choice is not None
    assert sorted(c.id for c in p1.choice.cards) == runners
    p1.choice.choose(p1.choice.cards[0])
    # Net hand: played 'given' (-1) then gained the second pick (+1).
    assert len(p1.hand) == hand_before


def test_odd_map_no_second_pick_for_unrelated_minion():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    for c in list(p1.hand):
        c.discard()
    p1.give("TLC_824").play()
    p1.choice.choose(p1.choice.cards[0])     # resolve first Discover
    assert p1.choice is None
    # Playing a different minion must NOT fire the second pick.
    p1.max_mana = 10
    p1.used_mana = 0
    p1.give(PLAIN_BEAST).play()
    assert p1.choice is None


# ---------------------------------------------------------------------------
# TLC_825 — Ravasaur Matriarch (Kindred: deal dmg = its Attack to enemy minion)
# ---------------------------------------------------------------------------

def test_ravasaur_matriarch_kindred_hits_enemy_minion():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    _play_beast_last_turn(game, p1)
    enemy = p1.opponent.summon("CS2_182")    # 4/5
    enemy.max_health = 80
    enemy.damage = 0
    rm = p1.give("TLC_825")                  # 5 Attack
    rm.play()
    assert enemy.damage == 5                 # exactly its Attack


def test_ravasaur_matriarch_no_kindred_no_damage():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    enemy = p1.opponent.summon("CS2_182")
    enemy.max_health = 80
    enemy.damage = 0
    assert Race.BEAST not in p1.races_played_last_turn
    p1.give("TLC_825").play()
    assert enemy.damage == 0


# ---------------------------------------------------------------------------
# TLC_826 — Story of Carnassa (Shuffle ten 1-Cost 3/2 Raptors)
# ---------------------------------------------------------------------------

def test_story_of_carnassa_shuffles_ten_raptors():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    deck0 = len(p1.deck)
    p1.give("TLC_826").play()
    assert len(p1.deck) == deck0 + 10
    raptors = [c for c in p1.deck if c.id == "UNG_920t2"]
    assert len(raptors) == 10
    assert all(r.cost == 1 and r.atk == 3 and r.health == 2 for r in raptors)


# ---------------------------------------------------------------------------
# TLC_827 — Grazing Stegodon (+1 Attack at end of turn, even in hand/deck)
# ---------------------------------------------------------------------------

def test_grazing_stegodon_gains_attack_in_hand():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    steg = p1.give("TLC_827")
    atk0 = steg.atk
    game.end_turn()                          # one own turn-end
    game.end_turn()
    game.end_turn()                          # second own turn-end
    game.end_turn()
    assert steg.atk == atk0 + 2


def test_grazing_stegodon_gains_attack_in_play():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    steg = p1.summon("TLC_827")
    atk0 = steg.atk
    game.end_turn()                          # own turn-end while in play
    assert steg.atk == atk0 + 1


# ---------------------------------------------------------------------------
# TLC_828 — Supreme Dinomancy (+2/+2 to all Beasts in hand, deck, board)
# ---------------------------------------------------------------------------

def test_supreme_dinomancy_buffs_all_zones():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    hand_beast = p1.give(PLAIN_BEAST)        # 3/2 in hand
    board_beast = p1.summon(PLAIN_BEAST)     # 3/2 on board
    deck_beast = p1.card(PLAIN_BEAST, zone=Zone.DECK)  # 3/2 in deck
    ha, hh = hand_beast.atk, hand_beast.health
    ba, bh = board_beast.atk, board_beast.health
    da, dh = deck_beast.atk, deck_beast.health
    p1.give("TLC_828").play()
    assert hand_beast.atk == ha + 2 and hand_beast.health == hh + 2
    assert board_beast.atk == ba + 2 and board_beast.health == bh + 2
    assert deck_beast.atk == da + 2 and deck_beast.health == dh + 2


def test_supreme_dinomancy_ignores_non_beasts():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    nonbeast = p1.summon("CS2_182")          # Chillwind Yeti (not a Beast)
    a0, h0 = nonbeast.atk, nonbeast.health
    p1.give("TLC_828").play()
    assert nonbeast.atk == a0 and nonbeast.health == h0


# ---------------------------------------------------------------------------
# TLC_830 — The Food Chain (Quest: play 1/3/5/7-Attack Beast -> Shokk)
# ---------------------------------------------------------------------------

def test_food_chain_completes_and_rewards_shokk():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    quest = p1.give("TLC_830")
    quest.play()
    p1.max_mana = 10
    for beast_id, expect_progress in (
        (BEAST_1ATK, 1), (BEAST_3ATK, 2), (BEAST_5ATK, 3),
    ):
        p1.used_mana = 0
        beast = p1.give(beast_id)
        _resolve_choices(p1)
        beast.play()
        _resolve_choices(p1)
        assert quest.progress == expect_progress
    # Fourth distinct Attack completes the quest.
    p1.used_mana = 0
    beast = p1.give(BEAST_7ATK)
    _resolve_choices(p1)
    beast.play()
    _resolve_choices(p1)
    shokk = [c for c in p1.hand if c.id == "TLC_830t"]
    assert len(shokk) == 1
    assert shokk[0].data.name == "Shokk, Jungle Tyrant"


def test_food_chain_duplicate_attack_does_not_advance():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    quest = p1.give("TLC_830")
    quest.play()
    p1.max_mana = 10
    for _ in range(3):
        p1.used_mana = 0
        beast = p1.give(BEAST_1ATK)          # all 1-Attack
        _resolve_choices(p1)
        beast.play()
        _resolve_choices(p1)
    assert quest.progress == 1               # only one distinct Attack value


# ---------------------------------------------------------------------------
# TLC_830t — Shokk, Jungle Tyrant (Get 8/6/4-Attack Beasts, set Cost to 2)
# ---------------------------------------------------------------------------

def test_shokk_battlecry_gets_three_beasts_cost_two(monkeypatch):
    # Determinism: a few 8/6/4-Attack Beasts use an ALTERNATE cost (e.g.
    # Reanimated Pterrordax TLC_436 costs Corpses, mana cost forced to 0), so a
    # mana-cost "set to 2" cannot apply to them. Strip those from the random
    # pool so the assertion has exactly one valid outcome (mirrors the Nebula
    # Colossal-pool fix). All remaining 8/6/4-atk Beasts honour the set-cost.
    import fireplace.cards as _c
    from hearthstone.enums import GameTag
    _orig = _c.filter
    alt_cost = {cid for cid, cd in _c.db.items()
                if cd.tags.get(GameTag.CARD_ALTERNATE_COST, 0)}
    assert alt_cost  # guard: revisit if the pool ever stops carrying these
    def _patched(*args, **kwargs):
        ids = _orig(*args, **kwargs)
        return [i for i in ids if i not in alt_cost]
    monkeypatch.setattr(_c, "filter", _patched)

    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    for c in list(p1.hand):
        c.discard()
    p1.give("TLC_830t").play()
    beasts = [c for c in p1.hand if c.type == CardType.MINION]
    assert len(beasts) == 3
    assert all(Race.BEAST in c.races for c in beasts)
    assert sorted(c.atk for c in beasts) == [4, 6, 8]
    assert all(c.cost == 2 for c in beasts)


# ---------------------------------------------------------------------------
# TLC_836 — Niri of the Crater (double 1-Cost minion stats; recast 1-Cost spell)
# ---------------------------------------------------------------------------

def test_niri_doubles_one_cost_minion_stats():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    p1.summon("TLC_836")
    boar = p1.give("CS2_171")                # Stonetusk Boar 1-Cost 1/1
    boar.play()
    assert boar.atk == 2 and boar.health == 2


def test_niri_does_not_double_expensive_minion():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    p1.summon("TLC_836")
    yeti = p1.give("CS2_182")                # 4-Cost 4/5
    yeti.play()
    assert yeti.atk == 4 and yeti.health == 5


def test_niri_casts_one_cost_spell_twice():
    game = prepare_game(CardClass.HUNTER, CardClass.HUNTER)
    p1 = game.current_player
    p1.summon("TLC_836")
    enemy = p1.opponent.hero
    enemy.max_health = 80
    enemy.damage = 0
    shot = p1.give(ARCANE_SHOT)              # 1-Cost "Deal 2 damage"
    assert shot.cost == 1                     # guard against data rebalance
    shot.play(target=enemy)
    assert enemy.damage == 4                 # cast twice -> 2 + 2


def test_niri_does_not_recast_two_cost_spell():
    game = prepare_game(CardClass.MAGE, CardClass.MAGE)
    p1 = game.current_player
    p1.summon("TLC_836")
    frostbolt = p1.give("CS2_024")           # 2-Cost "Deal 3 damage..."
    assert frostbolt.cost == 2               # guard against data rebalance
    enemy = p1.opponent.hero
    enemy.max_health = 80
    enemy.damage = 0
    frostbolt.play(target=enemy)
    assert enemy.damage == 3                 # cast once only (not doubled to 6)
