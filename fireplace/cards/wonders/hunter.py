from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..classic.hunter import EX1_609
from ..gangs.hunter import CFM_334, CFM_336
from ..gvg.hunter import GVG_046, GVG_073
from ..league.collectible import LOE_105
from ..tgt.hunter import AT_061, AT_062, AT_063, AT_063t

class WON_018(EX1_609):
	"""Snipe"""

class WON_021(AT_062):
	"""Ball of Spiders"""

class WON_022(LOE_105):
	"""Explorer's Hat"""

class WON_023(AT_061):
	"""Lock and Load"""

class WON_024(AT_063):
	"""Acidmaw"""

class WON_025(AT_063t):
	"""Dreadscale"""

class WON_162(GVG_046):
	"""King of Beasts"""

class WON_306(GVG_073):
	"""Cobra Shot"""

class WON_307(CFM_336):
	"""Shaky Zipgunner"""

class WON_347(CFM_334):
	"""Smuggler's Crate"""


##
# Novel cards

class _ImposterRotate(TargetedAction):
	"""Imposter cards (WON_026/039/077): each turn while in hand, morph
	into a random N-cost minion that gains a fixed keyword. Cost N and
	the keyword come from per-card class attributes."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target.zone != Zone.HAND:
			return
		cost = getattr(target, "_imposter_cost", 3)
		keyword = getattr(target, "_imposter_keyword", None)
		picker = RandomMinion(cost=cost)
		pick = picker.evaluate(source)
		cid = pick[0] if isinstance(pick, list) else pick
		if not cid:
			return
		source.game.cheat_action(source, [Morph(target, cid)])
		if keyword == "POISONOUS":
			target.poisonous = True
		elif keyword == "STEALTH":
			target.stealth = True
		elif keyword == "SPELLPOWER":
			target.spellpower += 1


class WON_026:
	"""Durnholde Imposter"""

	# Each turn this is in your hand, transform it into a random 3-Cost
	# minion that gains Poisonous.
	_imposter_cost = 3
	_imposter_keyword = "POISONOUS"

	class Hand:
		events = OWN_TURN_BEGIN.on(_ImposterRotate(SELF))


class WON_027:
	"""Time-Lost Raptor"""

	# Echo. Battlecry: Adapt your Time-Lost Raptors. Echo is a data tag,
	# Adapt is a primitive — only target Raptors (by name match).
	play = Adapt(FRIENDLY_MINIONS + ID("WON_027"))


class WON_028:
	"""Trial of the Jormungars"""

	# Summon copies of two Beasts in your deck that cost (3) or less.
	play = Summon(
		CONTROLLER,
		Copy(RANDOM(FRIENDLY_DECK + MINION + BEAST + (COST <= 3))),
	) * 2
