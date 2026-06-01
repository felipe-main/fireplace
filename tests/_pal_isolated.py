"""Throwaway harness: stub in-progress sibling Cataclysm modules so the card DB
can initialize, then run the Paladin tests in isolation. Not committed."""
import sys, types

pkg = "fireplace.cards.cataclysm"
siblings = ["demonhunter", "druid", "hunter", "mage", "priest", "rogue",
            "shaman", "warlock", "warrior", "neutral"]
for s in siblings:
    name = pkg + "." + s
    if name not in sys.modules:
        m = types.ModuleType(name)
        m.__all__ = []
        sys.modules[name] = m

import fireplace.cards.cataclysm.paladin  # noqa: ensure real module loads

import pytest

sys.exit(pytest.main([
    "tests/test_cataclysm_paladin.py", "-q", "--tb=short", "-p", "no:cacheprovider",
]))
