"""Throwaway harness: stub in-progress sibling Cataclysm modules so the card DB
can initialize, then run the Demon Hunter tests in isolation. Not committed.

The shared cataclysm/__init__.py is still scaffold (only imports druid/warlock),
so we also splice demonhunter's symbols onto the package namespace the way the
final __init__ will, so get_script_definition can find CATA_ Demon Hunter ids."""
import sys, types

# OWN_SUMMON is a Cataclysm engine primitive the orchestrator adds to the
# engine: a self-observing Summon event that (unlike the base Summon action,
# whose _broadcast self-blocks at actions.py:3031) DOES fire for the summoned
# minion's own summon. Shim a faithful non-self-blocking variant for isolated
# testing so the "When summoned" tokens (tentacles / soldiers / wings) trigger.
import fireplace.events as _ev
import fireplace.actions as _act
from fireplace.actions import Summon as _Summon
from fireplace.dsl.selector import CONTROLLER as _CTRL, MINION as _MIN


# Faithfully simulate the engine change: drop Summon's own-summon self-block so
# "When summoned" listeners on the summoned minion fire. (The orchestrator's
# real OWN_SUMMON does this in the engine; here we patch it for isolated tests.)
_act.Summon._broadcast = _act.TargetedAction._broadcast

if not hasattr(_ev, "OWN_SUMMON"):
    _ev.OWN_SUMMON = _Summon(_CTRL, _MIN)
import fireplace.cards.utils as _u
if not hasattr(_u, "OWN_SUMMON"):
    _u.OWN_SUMMON = _ev.OWN_SUMMON

pkg = "fireplace.cards.cataclysm"
siblings = ["druid", "hunter", "mage", "priest", "rogue",
            "shaman", "warlock", "warrior", "neutral"]
for s in siblings:
    name = pkg + "." + s
    if name not in sys.modules:
        m = types.ModuleType(name)
        m.__all__ = []
        sys.modules[name] = m

import fireplace.cards.cataclysm as catapkg
import fireplace.cards.cataclysm.demonhunter as dh

# Splice every demonhunter symbol onto the package so the DB lookup finds them.
for k in dir(dh):
    if not k.startswith("__"):
        setattr(catapkg, k, getattr(dh, k))

import pytest

sys.exit(pytest.main([
    "tests/test_cataclysm_demonhunter.py", "-q", "--tb=short", "-p", "no:cacheprovider",
]))
