"""
Base game rules (events, etc)
"""

from .cards.utils import *


class WeaponRules:
    base_events = [Attack(FRIENDLY_HERO).after(Hit(SELF, 1))]


class LocationRules:
    base_events = []
