from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..gvg.priest import GVG_009, GVG_011
from ..karazhan.collectible import KAR_204
from ..league.collectible import LOE_006
from ..tgt.priest import AT_012, AT_014, AT_015, AT_018
from ..wog.priest import OG_234, OG_334

class WON_056(LOE_006):
	"""Museum Curator"""

class WON_057(KAR_204):
	"""Onyx Bishop"""

class WON_058(AT_012):
	"""Spawn of Shadows"""

class WON_061(AT_014):
	"""Shadowfiend"""

class WON_062(GVG_009):
	"""Shadowbomber"""

class WON_063(AT_018):
	"""Confessor Paletress"""

class WON_313(OG_334):
	"""Hooded Acolyte"""

class WON_314(GVG_011):
	"""Shrinkmeister"""

class WON_315(OG_234):
	"""Darkshire Alchemist"""

class WON_342(AT_015):
	"""Convert"""


##
# Novel cards

class WON_064:
	"""Shadow Word: Forbid"""

	# Tradeable. Destroy a 4-Attack minion. Corrupt: Destroy ALL 4-Attack
	# minions.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Destroy(TARGET)
	corrupt_card = "WON_064ts"


class WON_064ts:
	"""Shadow Word: Forbid"""

	# Corrupted: Destroy ALL 4-Attack minions.
	play = Destroy(ALL_MINIONS + (ATK == 4))


class WON_065:
	"""Ship's Chirurgeon"""

	# After you summon a minion, give it +1 Health.
	events = Summon(CONTROLLER, MINION).after(Buff(Summon.CARD, "WON_065e"))


WON_065e = buff(health=1)


class _MurozondAOE(TargetedAction):
	# After Discover resolves, deal damage equal to the picked Dragon's
	# cost to all other minions. We approximate by reading the most
	# recently added hand card's cost.
	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not ctrl.hand:
			return
		picked = ctrl.hand[-1]
		dmg = picked.cost or 0
		if dmg > 0:
			source.game.cheat_action(
				source, [Hit(ALL_MINIONS - SELF, dmg)]
			)


class WON_066:
	"""Murozond, Thief of Time"""

	# Battlecry: If your deck has no duplicates, Discover a Dragon. Deal
	# damage equal to its Cost to all other minions.
	powered_up = -FindDuplicates(FRIENDLY_DECK)
	play = powered_up & (
		Discover(CONTROLLER, RandomMinion(race=Race.DRAGON)).then(
			_MurozondAOE(CONTROLLER)
		)
	)
