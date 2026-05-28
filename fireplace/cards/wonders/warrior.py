from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..blackrock.collectible import BRM_016
from ..gangs.warrior import CFM_631, CFM_643, CFM_752, CFM_754, CFM_756, CFM_940
from ..gvg.warrior import GVG_050, GVG_056
from ..karazhan.collectible import KAR_091
from ..wog.warrior import OG_301

class WON_108(CFM_754):
	"""Grimy Gadgeteer"""

class WON_110(CFM_752):
	"""Stolen Goods"""

class WON_111(OG_301):
	"""Ancient Shieldbearer"""

class WON_114(GVG_056):
	"""Iron Juggernaut"""

class WON_117(CFM_643):
	"""Hobart Grapplehammer"""

class WON_325(GVG_050):
	"""Bouncing Blade"""

class WON_326(CFM_631):
	"""Brass Knuckles"""

class WON_337(KAR_091):
	"""Ironforge Portal"""

class WON_338(BRM_016):
	"""Axe Flinger"""

class WON_339(CFM_756):
	"""Alley Armorsmith"""

class WON_350(CFM_940):
	"""I Know a Guy"""


##
# Novel cards

class _BlastFromThePast(TargetedAction):
	# Get 2 Spare Parts. Summon two 1/1 Boom Bots. Shuffle a Bomb into opp.
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		for _ in range(2):
			picker = RandomSparePart()
			pick = picker.evaluate(source)
			cid = pick[0] if isinstance(pick, list) else pick
			if cid:
				source.game.cheat_action(source, [Give(ctrl, cid)])
		source.game.cheat_action(source, [Summon(ctrl, "GVG_110t") * 2])
		source.game.cheat_action(source, [Shuffle(ctrl.opponent, "BOT_511t")])


class WON_115:
	"""Blast from the Past"""

	# Get 2 Spare Parts. Summon two 1/1 Boom Bots. Shuffle a Bomb into
	# your opponent's deck.
	play = _BlastFromThePast(CONTROLLER)


class _IvoryRookArmor(TargetedAction):
	# Gain armor equal to the Discovered Taunt minion's cost. The chosen
	# card is passed via Discover.CARD — never read hand[-1], which is a
	# different card (and the Discover doesn't add to hand until Give runs).
	TARGET = ActionArg()
	CARD = CardArg()
	def do(self, source, target, card):
		cost = (card.cost or 0) if card else 0
		if cost > 0:
			source.game.cheat_action(
				source, [GainArmor(FRIENDLY_HERO, cost)]
			)


class WON_116:
	"""Ivory Rook"""

	# Battlecry: Discover a Taunt minion. Gain Armor equal to its Cost.
	play = Discover(CONTROLLER, RandomMinion(taunt=True)).then(
		Give(CONTROLLER, Discover.CARD),
		_IvoryRookArmor(CONTROLLER, Discover.CARD),
	)
