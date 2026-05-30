from ..utils import *

from ...actions import LaunchStarship, _StarshipSpellburst  # noqa: F401


##
# Starship tokens
#
# The building / launched Starship is the per-class token below. The engine
# (actions._bank_starship_piece / LaunchStarship) drives all stat, keyword,
# deathrattle and event combination directly on the token instance; the only
# script the token itself needs is a `spellburst` that replays the banked
# pieces' spellbursts (Spellburst.get_actions reads the host's own data
# script). The shared mixin supplies it; each token keeps its printed name.


class _StarshipToken:
    spellburst = _StarshipSpellburst(SELF)


class GDB_100t2(_StarshipToken):
    """The Exile's Hope"""


class GDB_100t4(_StarshipToken):
    """The Spirits' Passage"""


class GDB_100t5(_StarshipToken):
    """The Legion's Bane"""


class GDB_100t6(_StarshipToken):
    """The Celestial Archive"""


class GDB_100t7(_StarshipToken):
    """The Astral Compass"""


class GDB_100t8(_StarshipToken):
    """The Scavenger's Will"""


class GDB_100t9(_StarshipToken):
    """The Nether's Eye"""


class GDB_905:
    """Launch Starship"""

    # Launch your Starship.
    play = LaunchStarship(CONTROLLER)


class GDB_906:
    """Abort Launch"""

    # Abort Launch. (No effect — purely a UI cancel.)
