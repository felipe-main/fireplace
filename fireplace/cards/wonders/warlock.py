from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..classic.warlock import EX1_320
from ..gangs.warlock import CFM_750
from ..gvg.warlock import GVG_015
from ..karazhan.collectible import KAR_205
from ..league.collectible import LOE_023
from ..tgt.warlock import AT_021, AT_024, AT_025
from ..wog.warlock import OG_116, OG_121, OG_302

class WON_093(AT_024):
	"""Demonfuse"""

class WON_095(GVG_015):
	"""Darkbomb"""

class WON_096(LOE_023):
	"""Dark Peddler"""

class WON_097(OG_116):
	"""Spreading Madness"""

class WON_098(KAR_205):
	"""Silverware Golem"""

class WON_099(AT_021):
	"""Tiny Knight of Evil"""

class WON_100(AT_025):
	"""Dark Bargain"""

class WON_105(OG_121):
	"""Cho'gall"""

class WON_322(OG_302):
	"""Usher of Souls"""

class WON_323(EX1_320):
	"""Bane of Doom"""

class WON_324(CFM_750):
	"""Krul the Unshackled"""


##
# Novel cards

class _ChamberDiscardDraw(TargetedAction):
	# Look at 3 cards in your hand and choose one to discard. Draw two
	# cards. Approximation: discard a random card from hand, then draw 2.
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		import random
		if ctrl.hand:
			pick = random.choice(list(ctrl.hand))
			source.game.cheat_action(source, [Discard(pick)])
		source.game.cheat_action(source, [Draw(ctrl) * 2])


class WON_103:
	"""Chamber of Viscidus"""

	# Location: Look at 3 cards in your hand and choose one to discard.
	# Draw two cards.
	activate = _ChamberDiscardDraw(CONTROLLER)


class _WitchArchThief(TargetedAction):
	# Battlecry: Summon a 1/3 Voidwalker. If opp has more minions,
	# repeat. Always summons at least one, then loops while opp.field
	# > ctrl.field, capped by the engine's 7-minion board cap.
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		opp = ctrl.opponent
		while True:
			if len(ctrl.field) >= 7:
				break
			source.game.cheat_action(source, [Summon(ctrl, "CS2_065")])
			if len(opp.field) <= len(ctrl.field):
				break


class WON_104:
	"""Witch of the Arch-Thief"""

	# Battlecry: Summon a 1/3 Voidwalker with Taunt. If your opponent has
	# more minions, repeat.
	play = _WitchArchThief(CONTROLLER)
