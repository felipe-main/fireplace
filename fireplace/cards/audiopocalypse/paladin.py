from ..utils import *


##
# Locations

class JAM_009:
	"""Dance Floor"""

	# Location. Activate: Give your minions Rush. Durability comes
	# from data (HEALTH tag); cooldown is the engine-default 2 turns.
	activate = GiveRush(FRIENDLY_MINIONS)


##
# Minions

class JAM_010:
	"""Jukebox Totem"""

	# At the end of your turn, summon a 1/1 Silver Hand Recruit
	# (CS2_101t — the canonical Silver Hand Recruit token).
	events = OWN_TURN_END.on(Summon(CONTROLLER, "CS2_101t"))
