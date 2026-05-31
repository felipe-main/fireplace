"""Reusable per-set dumper for the autonomous roadmap run.

Usage: python roadmap/dump_set.py <CARDSET_ENUM_NAME>

Prints:
  - every collectible card in the set (id/type/stats/class/name/text)
  - which ones already have a fireplace script (implemented) vs not (new work)
  - a GameTag histogram over the UNIMPLEMENTED cards (novel-mechanic signal)
"""
import sys
from collections import Counter

from hearthstone.cardxml import load
from hearthstone.enums import CardSet, CardType
import hearthstone_data

import fireplace.cards
from fireplace.cards import db as fpdb, get_script_definition

SET_NAME = sys.argv[1] if len(sys.argv) > 1 else "SPACE"

fpdb.initialize()
xmldb, _ = load(path=hearthstone_data.get_carddefs_path(), locale="enUS")

cards = sorted(
    (cid, c) for cid, c in xmldb.items()
    if c.card_set.name == SET_NAME and c.collectible
)

def has_script(cid):
    try:
        sd = get_script_definition(cid)
    except Exception:
        sd = None
    if sd is None:
        return False
    # a real script has at least one recognized class attribute
    for attr in ("play", "deathrattle", "events", "tags", "update",
                 "cost_mod", "choose", "powered_up", "requirements",
                 "entourage", "dormant_events"):
        if getattr(sd, attr, None):
            return True
    return False

impl, new = [], []
for cid, c in cards:
    (impl if has_script(cid) else new).append((cid, c))

print(f"=== CardSet {SET_NAME}: {len(cards)} collectible "
      f"({len(impl)} implemented, {len(new)} NEW) ===\n")

print("--- NEW (unimplemented) cards ---")
for cid, c in new:
    cost = c.cost or 0
    stats = (f"{cost}/{c.atk}/{c.health}" if c.type == CardType.MINION
             else f"{cost}/{c.atk}/{c.durability}" if c.type == CardType.WEAPON
             else str(cost))
    cls = c.card_class.name if c.card_class else "NEUTRAL"
    text = (c.description or "").replace(chr(10), " ")
    print(f"{cid:14s} {c.type.name:7s} {stats:9s} {cls:13s} {c.name:34s} | {text}")

print("\n--- GameTag histogram over NEW cards ---")
tags = Counter()
for cid, c in new:
    for t in c.tags:
        name = t.name if hasattr(t, "name") else str(t)
        tags[name] += 1
for name, n in tags.most_common():
    print(f"  {n:3d}  {name}")

print("\n--- Race histogram over NEW minions ---")
races = Counter()
for cid, c in new:
    for r in getattr(c, "races", []) or []:
        races[r.name if hasattr(r, "name") else str(r)] += 1
for name, n in races.most_common():
    print(f"  {n:3d}  {name}")
