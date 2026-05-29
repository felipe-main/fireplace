import itertools

from hearthstone.enums import CardType, Race

from ..utils import *


##
# Zilliax Deluxe 3000 (TOY_330) — modular build-a-minion.
#
# Printed rule (hearthstone.wiki.gg/wiki/Zilliax_Deluxe_3000): while building
# your deck you pick EXACTLY TWO of the eight Functional Modules (plus one
# purely-cosmetic art module, which we ignore). "The two Modules have their
# attack, health, cost, and all card text combined into one card." The result
# is a single Mech.
#
# This engine has no deckbuilder, so — mirroring the Death Knight rune pattern
# in fireplace/utils.py (the rune setup is chosen once per draft, then fixed) —
# the two modules are chosen once per draft in random_draft() and Zilliax is
# substituted with a fixed pre-assembled card. In-game it is then deterministic
# and known from turn 1, matching real Hearthstone.
#
# Each of the 28 unordered module pairs is registered as its own assembled
# card (summed stats + the UNION of both modules' text). The eight Functional
# Module tokens are also scripted as real cards (they exist in the data and
# carry battlecry/deathrattle tags, so they need scripts). A default pair is
# baked onto the base TOY_330 for any Zilliax created outside drafting
# (Discover, generation, or test give/summon).


# --- Module enchantments (both ids exist in data) ---
class TOY_330t94e:
    # Power Module — "double this minion's Attack".
    atk = lambda self, i: i * 2


TOY_330t95e1 = buff(+1, +1)  # Pylon's Unity — your other minions have +1/+1.


# --- The eight Functional Modules ---------------------------------------------
# Each spec carries the module's stats (read from data), the keyword tags it
# grants (needed when building the data-less assembled cards), and its behavior
# attributes. Behavior action templates are class-level and safely shared
# across the standalone token and every assembled card that includes them.

MODULE_SPECS = {
    # Recursive Module — Deathrattle: Shuffle this into your deck.
    "TOY_330t92": dict(
        name="Recursive Module", cost=1, atk=1, health=1, tags={},
        deathrattle=(Shuffle(CONTROLLER, SELF),),
    ),
    # Haywire Module — At the end of your turn, deal 3 damage to your hero.
    "TOY_330t93": dict(
        name="Haywire Module", cost=2, atk=4, health=4, tags={},
        events=[OWN_TURN_END.on(Hit(FRIENDLY_HERO, 3))],
    ),
    # Power Module — At the start of your turn, double this minion's Attack.
    "TOY_330t94": dict(
        name="Power Module", cost=2, atk=1, health=3, tags={},
        events=[OWN_TURN_BEGIN.on(Buff(SELF, "TOY_330t94e"))],
    ),
    # Pylon Module — Your other minions have +1/+1.
    "TOY_330t95": dict(
        name="Pylon Module", cost=3, atk=2, health=2, tags={},
        update=(Refresh(FRIENDLY_MINIONS - SELF, buff="TOY_330t95e1"),),
    ),
    # Virus Module — Stealth, Elusive, Poisonous, Reborn.
    "TOY_330t96": dict(
        name="Virus Module", cost=3, atk=1, health=3,
        tags={
            GameTag.STEALTH: True,
            GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
            GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
            GameTag.POISONOUS: True,
            GameTag.REBORN: True,
        },
    ),
    # Twin Module — Battlecry: Summon a copy of this.
    "TOY_330t97": dict(
        name="Twin Module", cost=4, atk=3, health=3, tags={},
        play=(Summon(CONTROLLER, ExactCopy(SELF)),),
    ),
    # Ticking Module — Costs (1) less for each minion in play.
    "TOY_330t98": dict(
        name="Ticking Module", cost=4, atk=1, health=3, tags={},
        cost_mod=-Count(ALL_MINIONS),
    ),
    # Perfect Module — Divine Shield, Taunt, Lifesteal, Rush.
    "TOY_330t99": dict(
        name="Perfect Module", cost=5, atk=3, health=2,
        tags={
            GameTag.DIVINE_SHIELD: True,
            GameTag.TAUNT: True,
            GameTag.LIFESTEAL: True,
            GameTag.RUSH: True,
        },
    ),
}

MODULE_IDS = list(MODULE_SPECS.keys())

# Default assembled pair for any Zilliax created outside drafting.
DEFAULT_PAIR = ("TOY_330t95", "TOY_330t99")  # Pylon + Perfect

_BEHAVIOR_ATTRS = ("play", "deathrattle", "update")


def _behavior_namespace(spec):
    """Standalone module token: behavior only (stats/keywords come from data)."""
    ns = {"__doc__": spec["name"]}
    for attr in _BEHAVIOR_ATTRS:
        if attr in spec:
            ns[attr] = spec[attr]
    if "events" in spec:
        ns["events"] = list(spec["events"])
    if "cost_mod" in spec:
        ns["cost_mod"] = spec["cost_mod"]
    return ns


def _merge_behaviors(a, b):
    """Union of two module specs' behavior attributes."""
    ns = {}
    play = tuple(a.get("play", ())) + tuple(b.get("play", ()))
    if play:
        ns["play"] = play
    dr = tuple(a.get("deathrattle", ())) + tuple(b.get("deathrattle", ()))
    if dr:
        ns["deathrattle"] = dr
    update = tuple(a.get("update", ())) + tuple(b.get("update", ()))
    if update:
        ns["update"] = update
    events = list(a.get("events", [])) + list(b.get("events", []))
    if events:
        ns["events"] = events
    cm_a, cm_b = a.get("cost_mod"), b.get("cost_mod")
    if cm_a is not None and cm_b is not None:
        ns["cost_mod"] = cm_a + cm_b
    elif cm_a is not None:
        ns["cost_mod"] = cm_a
    elif cm_b is not None:
        ns["cost_mod"] = cm_b
    return ns


def zilliax_combo_id(id_a, id_b):
    """Canonical, order-independent id for an assembled module pair."""
    a, b = sorted([id_a, id_b])
    return "TOY_330z_%s_%s" % (a.rsplit("t", 1)[-1], b.rsplit("t", 1)[-1])


def pick_zilliax_combo(rng):
    """Pick two distinct functional modules and return the assembled id.
    Called once per draft (mirrors the DK rune setup)."""
    a, b = rng.sample(MODULE_IDS, 2)
    return zilliax_combo_id(a, b)


# --- Register the eight standalone module token cards -------------------------
for _mid, _spec in MODULE_SPECS.items():
    globals()[_mid] = type(_mid, (), _behavior_namespace(_spec))


# --- Generate the 28 assembled (combined) cards -------------------------------
for _id_a, _id_b in itertools.combinations(MODULE_IDS, 2):
    _a, _b = MODULE_SPECS[_id_a], MODULE_SPECS[_id_b]
    _cid = zilliax_combo_id(_id_a, _id_b)
    _tags = {
        GameTag.CARDNAME: "Zilliax Deluxe 3000",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.CARDRACE: Race.MECHANICAL,
        GameTag.COST: _a["cost"] + _b["cost"],
        GameTag.ATK: _a["atk"] + _b["atk"],
        GameTag.HEALTH: _a["health"] + _b["health"],
        GameTag.ELITE: True,
        GameTag.COLLECTIBLE: False,
    }
    _tags.update(_a["tags"])
    _tags.update(_b["tags"])
    _behaviors = _merge_behaviors(_a, _b)
    # Custom cards have no data tags, so the keyword gates that make the engine
    # process battlecries/deathrattles must be set explicitly.
    if "play" in _behaviors:
        _tags[GameTag.BATTLECRY] = True
    if "deathrattle" in _behaviors:
        _tags[GameTag.DEATHRATTLE] = True
    _ns = {"tags": _tags}
    _ns.update(_behaviors)
    custom_card(type(_cid, (), _ns))


# --- Base Zilliax (TOY_330): bake the default pair onto the data card ---------
# Override only stats + keyword tags + behavior; keep the data card's identity
# (name, collectible, Mech) so it still drafts and Discovers normally.
def _base_namespace():
    a, b = MODULE_SPECS[DEFAULT_PAIR[0]], MODULE_SPECS[DEFAULT_PAIR[1]]
    tags = {
        GameTag.COST: a["cost"] + b["cost"],
        GameTag.ATK: a["atk"] + b["atk"],
        GameTag.HEALTH: a["health"] + b["health"],
    }
    tags.update(a["tags"])
    tags.update(b["tags"])
    behaviors = _merge_behaviors(a, b)
    if "play" in behaviors:
        tags[GameTag.BATTLECRY] = True
    if "deathrattle" in behaviors:
        tags[GameTag.DEATHRATTLE] = True
    ns = {"__doc__": "Zilliax Deluxe 3000", "tags": tags}
    ns.update(behaviors)
    return ns


TOY_330 = type("TOY_330", (), _base_namespace())
