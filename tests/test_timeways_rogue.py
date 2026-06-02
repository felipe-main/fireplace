# --- isolation shim -------------------------------------------------------
# This set is implemented by several parallel agents, one file per class. While
# sibling class files are still being written they may raise at import time,
# which would block the whole `across_the_timeways` package (its __init__ star-
# imports every class module). To let the ROGUE suite run independently, we
# probe each sibling in a subprocess (with every OTHER sibling stubbed) and, if
# it fails to import, pre-stub it with an empty module BEFORE the package
# __init__ runs. Once every sibling is complete this block stubs nothing (real
# modules import fine). The rogue module itself is never stubbed.
import subprocess as _subprocess
import sys as _sys
import types as _types

_PKG = "fireplace.cards.across_the_timeways"
_SIBS = (
    "deathknight", "demonhunter", "druid", "hunter", "mage", "paladin",
    "priest", "shaman", "warlock", "warrior", "neutral",
)


def _sibling_imports_ok(name):
    lines = [
        "import sys, types",
        "PKG = %r" % _PKG,
        "SIBS = %r" % (_SIBS,),
        "NAME = %r" % name,
        "for s in SIBS:",
        "    if s != NAME:",
        "        full = PKG + '.' + s",
        "        sys.modules[full] = types.ModuleType(full)",
        "import importlib",
        "importlib.import_module(PKG + '.' + NAME)",
    ]
    code = "\n".join(lines)
    return _subprocess.run([_sys.executable, "-c", code]).returncode == 0


for _sib in _SIBS:
    if not _sibling_imports_ok(_sib):
        _full = _PKG + "." + _sib
        _sys.modules[_full] = _types.ModuleType(_full)
# --------------------------------------------------------------------------

from hearthstone.enums import CardType, Zone

from utils import prepare_game, CardClass


def _both(game):
    """Return (acting player, opponent), pinned to turn order so tests are
    deterministic regardless of who pick_first_player chose."""
    me = game.current_player
    return me, me.opponent


def _refill(player):
    player.used_mana = 0


# TIME_001 Chrono Daggers — Rewind: Throw 3 knives at random enemies that deal
# 2 damage each.
def test_chrono_daggers():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    for m in list(opp.field):
        m.destroy()
    enemy = opp.hero
    enemy.max_health = 80
    enemy.damage = 0
    me.give("TIME_001").play()
    # Decline Rewind (pick Keep Timeline = first option).
    assert me.choice
    me.choice.choose(me.choice.cards[0])
    assert me.choice is None
    assert enemy.damage == 6  # 3 knives x 2


def test_chrono_daggers_rewind():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    for m in list(opp.field):
        m.destroy()
    enemy = opp.hero
    enemy.max_health = 80
    enemy.damage = 0
    me.give("TIME_001").play()
    # Pick Rewind (TIME_000tb = second token) to re-run the effect once.
    assert me.choice
    rewind = me.choice.cards[1]
    assert rewind.id == "TIME_000tb"
    me.choice.choose(rewind)
    while me.choice:
        me.choice.choose(me.choice.cards[0])
    assert enemy.damage == 12  # 3 x 2, run twice


# TIME_036 Royal Informant — Battlecry: Look at the rightmost card in your
# opponent's hand. Either get a copy of it or increase its Cost by (2).
def test_royal_informant_copy():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    opp.discard_hand()
    opp.give("CS2_029")  # Fireball — rightmost
    pre_hand = len(me.hand)
    me.give("TIME_036").play()
    assert me.choice
    copy_option = me.choice.cards[0]
    assert copy_option.id == "CS2_029"
    me.choice.choose(copy_option)
    assert me.choice is None
    assert len(me.hand) == pre_hand + 1
    assert any(c.id == "CS2_029" for c in me.hand)
    # The mitigate token must not also be retained.
    assert not any(c.id == "TIME_036t" for c in me.hand)


def test_royal_informant_mitigate():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    opp.discard_hand()
    target = opp.give("CS2_029")  # Fireball, base cost 4
    base_cost = target.cost
    me.give("TIME_036").play()
    assert me.choice
    mitigate = me.choice.cards[1]
    assert mitigate.id == "TIME_036t"
    pre_hand_ids = {c.id for c in me.hand}
    me.choice.choose(mitigate)
    assert me.choice is None
    assert target.cost == base_cost + 2
    # The Mitigate-Threat trigger token must NOT be retained in hand.
    assert not any(c.id == "TIME_036t" for c in me.hand)
    assert {c.id for c in me.hand} == pre_hand_ids


# TIME_039 Deja Vu — Discover a copy of a card in your opponent's hand. It
# costs (1) less.
def test_deja_vu():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    opp.discard_hand()
    opp.give("CS2_029")  # Fireball (cost 4)
    pre_hand = len(me.hand)
    me.give("TIME_039").play()
    assert me.choice
    chosen = me.choice.cards[0]
    assert chosen.id == "CS2_029"
    me.choice.choose(chosen)
    assert me.choice is None
    assert len(me.hand) == pre_hand + 1
    copy = next(c for c in me.hand if c.id == "CS2_029")
    assert copy.cost == 3  # 4 - 1


# TIME_710 Troubled Double — Stealth. Combo: Summon a copy of this.
def test_troubled_double_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.give("GAME_005").play()  # the Coin — sets combo
    _refill(me)
    me.give("TIME_710").play()
    doubles = [m for m in me.field if m.id == "TIME_710"]
    assert len(doubles) == 2
    assert all(m.stealthed for m in doubles)


def test_troubled_double_no_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.give("TIME_710").play()
    doubles = [m for m in me.field if m.id == "TIME_710"]
    assert len(doubles) == 1
    assert doubles[0].stealthed


# TIME_711 Flashback — Summon two random 1-Cost minions from the past. Combo:
# With +1 Attack.
def test_flashback_no_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    pre = len(me.field)
    me.give("TIME_711").play()
    summoned = me.field[pre:]
    assert len(summoned) == 2
    assert all(m.cost == 1 for m in summoned)


def test_flashback_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.give("GAME_005").play()  # the Coin — sets combo
    _refill(me)
    pre = len(me.field)
    me.give("TIME_711").play()
    summoned = me.field[pre:]
    assert len(summoned) == 2
    # +1 Attack: each summoned minion's atk == its base atk + 1.
    for m in summoned:
        assert m.atk == m.data.atk + 1


# TIME_712 Dethrone — Destroy a minion. Combo: Summon a random 8-Cost minion.
def test_dethrone_no_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    victim = opp.summon("CS2_182")  # Chillwind Yeti
    pre = len(me.field)
    me.give("TIME_712").play(target=victim)
    assert victim.zone == Zone.GRAVEYARD
    assert len(me.field) == pre  # no combo summon


def test_dethrone_combo():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.give("GAME_005").play()  # the Coin — sets combo
    _refill(me)
    victim = opp.summon("CS2_182")
    pre = len(me.field)
    me.give("TIME_712").play(target=victim)
    assert victim.zone == Zone.GRAVEYARD
    summoned = me.field[pre:]
    assert len(summoned) == 1
    assert summoned[0].cost == 8


# TIME_713 Time Adm'ral Hooktail — Battlecry: Summon a 0/8 Chest for your
# opponent.
def test_hooktail():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.give("TIME_713").play()
    chests = [m for m in opp.field if m.id == "TIME_713t"]
    assert len(chests) == 1
    chest = chests[0]
    assert chest.atk == 0
    assert chest.health == 8


# TIME_713t Timeless Chest — Deathrattle: Fill your opponent's hand with Coins.
def test_timeless_chest_deathrattle():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.give("TIME_713").play()
    chest = next(m for m in opp.field if m.id == "TIME_713t")
    me.discard_hand()
    chest.destroy()
    # Chest is controlled by opp; "your opponent" from its view is `me` — fill
    # my hand with Coins.
    assert len(me.hand) == me.max_hand_size
    assert all(c.id == "GAME_005" for c in me.hand)


# TIME_770 Fast Forward — Draw 2 cards. Pick one to have its Cost reduced by
# (2).
def test_fast_forward():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    # Stack two known cards on top of the deck (deck[-1] is drawn first).
    y1 = me.give("CS2_182")
    y1.zone = Zone.DECK
    y2 = me.give("CS2_182")
    y2.zone = Zone.DECK
    pre_hand = len(me.hand)
    me.give("TIME_770").play()
    assert me.choice
    picked = me.choice.cards[0]
    base_cost = picked.data.cost
    me.choice.choose(picked)
    assert me.choice is None
    assert len(me.hand) == pre_hand + 2
    assert picked.cost == base_cost - 2


# TIME_875 Garona Halforcen — Battlecry: If your opponent is holding King
# Llane, destroy him and cut their Health in half.
def test_garona_with_llane():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    llane = opp.give("TIME_875t")
    opp.hero.max_health = 30
    opp.hero.damage = 0  # 30 health
    me.give("TIME_875").play()
    assert llane.zone == Zone.GRAVEYARD
    assert opp.hero.health == 15  # half of 30


def test_garona_without_llane():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    opp.discard_hand()
    opp.hero.max_health = 30
    opp.hero.damage = 0
    me.give("TIME_875").play()
    assert opp.hero.health == 30  # untouched


# TIME_875t King Llane — Battlecry: Draw a card. Shuffle this back into your
# deck.
def test_king_llane():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    deck_card = me.give("CS2_182")
    deck_card.zone = Zone.DECK
    llane = me.give("TIME_875t")
    llane.play()
    # Drew a card; Llane shuffled itself back into the deck.
    assert llane.zone == Zone.DECK
    assert any(c.id == "CS2_182" for c in me.hand)


# TIME_875t1 The Kingslayers — After your hero attacks, both players draw a
# Legendary card.
def test_kingslayers():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    opp.discard_hand()
    # Empty both decks, then plant exactly one Legendary in each so the draw is
    # deterministic.
    for p in (me, opp):
        for c in list(p.deck):
            c.zone = Zone.REMOVEDFROMGAME
    my_leg = me.give("EX1_116")  # Leeroy Jenkins (Legendary)
    my_leg.zone = Zone.DECK
    opp_leg = opp.give("EX1_116")
    opp_leg.zone = Zone.DECK
    me.give("TIME_875t1").play()
    pre_me = len(me.hand)
    pre_opp = len(opp.hand)
    me.hero.attack(opp.hero)
    assert my_leg.zone == Zone.HAND
    assert opp_leg.zone == Zone.HAND
    assert len(me.hand) == pre_me + 1
    assert len(opp.hand) == pre_opp + 1


# TIME_876 Shapeshifter — Each turn this is in your hand, transform into a
# random minion in your opponent's hand.
def _advance_to_own_turn_begin(game, owner):
    if game.current_player is owner:
        game.end_turn()
    while game.current_player is not owner:
        game.end_turn()


def test_shapeshifter_transforms():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    opp.discard_hand()
    # Freeze the opponent's hand: empty deck + no draws, then give exactly one
    # minion so the transform target is deterministic across the turn cycle.
    for c in list(opp.deck):
        c.zone = Zone.REMOVEDFROMGAME
    opp.cant_draw = True
    opp.cant_fatigue = True
    opp.give("CS2_182")  # Chillwind Yeti — sole minion in the enemy hand
    me.give("TIME_876")
    _advance_to_own_turn_begin(game, me)
    morphed = [c for c in me.hand if c.id == "CS2_182"]
    assert len(morphed) == 1
    assert not any(c.id == "TIME_876" for c in me.hand)


def test_shapeshifter_retransforms_every_turn():
    # Zerus-style recurrence: the card must transform on EACH of the owner's
    # turns, not just the first. We swap the (frozen) enemy hand between the
    # two morphs so the second transform is provably a *fresh* morph — if the
    # card morphed only once it would still read CS2_182 after turn 3, but a
    # re-transform makes it read CS2_222 (the new sole enemy minion).
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    opp.discard_hand()
    # Freeze BOTH hands entirely (no draws, no fatigue churn) so the only cards
    # that move are the Shapeshifter morphs — the in-hand morphed card is then
    # the sole entity in `me.hand` and we can assert its id exactly.
    for p in (me, opp):
        for c in list(p.deck):
            c.zone = Zone.REMOVEDFROMGAME
        p.cant_draw = True
        p.cant_fatigue = True

    # First morph target: Chillwind Yeti is the sole enemy minion.
    yeti = opp.give("CS2_182")
    shifter = me.give("TIME_876")
    assert shifter.id == "TIME_876"
    assert len(me.hand) == 1  # only the Shapeshifter

    # First own-turn-begin (turn 3): TIME_876 -> CS2_182.
    _advance_to_own_turn_begin(game, me)
    assert len(me.hand) == 1
    assert me.hand[0].id == "CS2_182"
    assert not any(c.id == "TIME_876" for c in me.hand)

    # Swap the (still frozen) enemy hand to a different sole minion so the next
    # transform must land on CS2_222, proving the trigger re-fired rather than
    # leaving the card frozen as CS2_182.
    yeti.discard()
    opp.give("CS2_222")  # Stormwind Champion — new sole enemy minion

    # Second own-turn-begin (turn 5): CS2_182 -> CS2_222 (re-transform).
    _advance_to_own_turn_begin(game, me)
    assert len(me.hand) == 1
    assert me.hand[0].id == "CS2_222"
    # Still no original Shapeshifter lingering.
    assert not any(c.id == "TIME_876" for c in me.hand)


def test_shapeshifter_no_enemy_minions():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    opp.discard_hand()
    for c in list(opp.deck):
        c.zone = Zone.REMOVEDFROMGAME
    opp.cant_draw = True
    opp.cant_fatigue = True
    me.give("TIME_876")
    _advance_to_own_turn_begin(game, me)
    # No enemy minion in hand -> Shapeshifter stays itself (Find gate fails).
    assert any(c.id == "TIME_876" for c in me.hand)


# ===========================================================================
# Across the Timeways mini-set (END_)
# ===========================================================================


# END_000 Eventuality — Deal 2 damage. Imbue your Hero Power.
def test_eventuality_damage_and_imbue():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    target = opp.summon("CS2_182")  # 4/5 Chillwind Yeti
    pre_imbues = me.imbues_this_game
    me.give("END_000").play(target=target)
    # 2 damage to the chosen target.
    assert target.damage == 2
    # Hero Power imbued once -> Rogue's Blessing of the Bronze installed.
    assert me.imbues_this_game == pre_imbues + 1
    assert me.hero_power.id == "END_000p"


def test_eventuality_can_hit_face():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    opp.hero.max_health = 30
    opp.hero.damage = 0
    me.give("END_000").play(target=opp.hero)
    assert opp.hero.health == 28
    assert me.hero_power.id == "END_000p"


# END_000p Blessing of the Bronze — Get a random minion from another class.
# It costs (@) less. (@ scales with imbue level.)
def test_blessing_of_the_bronze_level1():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    # Install the Imbued Hero Power at level 1 via Eventuality.
    me.give("END_000").play(target=opp.hero)
    assert me.hero_power.id == "END_000p"
    assert me.imbues_this_game == 1
    me.used_mana = 0
    me.hero.power.use()
    # Exactly one minion added to hand, from a class other than Rogue/Neutral.
    assert len(me.hand) == 1
    got = me.hand[0]
    assert got.type == CardType.MINION
    assert got.card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)
    # Level 1 => costs (1) less than its base cost.
    assert got.cost == max(0, got.data.cost - 1)


def test_blessing_of_the_bronze_scales_with_imbue_level():
    game = prepare_game(CardClass.ROGUE, CardClass.ROGUE)
    me, opp = _both(game)
    me.discard_hand()
    # Imbue twice -> level 2.
    me.give("END_000").play(target=opp.hero)
    me.give("END_000").play(target=opp.hero)
    assert me.imbues_this_game == 2
    assert me.hero_power.id == "END_000p"
    me.used_mana = 0
    me.hero.power.use()
    assert len(me.hand) == 1
    got = me.hand[0]
    assert got.card_class not in (CardClass.ROGUE, CardClass.NEUTRAL)
    # Level 2 => costs (2) less.
    assert got.cost == max(0, got.data.cost - 2)
