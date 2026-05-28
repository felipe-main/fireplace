from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..classic.paladin import EX1_354
from ..gangs.paladin import CFM_639
from ..karazhan.collectible import KAR_057, KAR_077
from ..league.collectible import LOE_017
from ..tgt.paladin import AT_078, AT_079
from ..wog.paladin import OG_310, OG_311

class WON_045(KAR_057):
	"""Ivory Knight"""

class WON_046(CFM_639):
	"""Grimestreet Enforcer"""

class WON_048(EX1_354):
	"""Lay on Hands"""

class WON_049(AT_078):
	"""Enter the Coliseum"""

class WON_309(KAR_077):
	"""Silvermoon Portal"""

class WON_310(OG_310):
	"""Steward of Darkshire"""

class WON_311(LOE_017):
	"""Keeper of Uldaman"""

class WON_333(OG_311):
	"""A Light in the Darkness"""

class WON_334(AT_079):
	"""Mysterious Challenger"""


##
# Novel cards

class _TimelessBlessing(TargetedAction):
	# Pick 4 distinct random minions in hand and buff with +4/+4, +3/+3,
	# +2/+2, +1/+1 respectively.
	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		import random
		minions = [c for c in ctrl.hand if c.type == CardType.MINION and c is not source]
		random.shuffle(minions)
		for amount, m in zip([4, 3, 2, 1], minions):
			source.game.cheat_action(
				source,
				[Buff(m, "WON_051e", atk=amount, max_health=amount)],
			)


class WON_051:
	"""Timeless Blessing"""

	# Give four random minions in your hand +4/+4, +3/+3, +2/+2, and +1/+1.
	play = _TimelessBlessing(CONTROLLER)


class WON_052:
	"""Bronze Dragonknight"""

	# Battlecry: If this has 5 or more Attack, summon a copy of this.
	play = Find(SELF + (ATK >= 5)) & Summon(CONTROLLER, Copy(SELF))


# Runi's "future Locations" — pick from a fixed entourage of 7 sub-locations.
class _RuniDiscover(TargetedAction):
	TARGET = ActionArg()

	def do(self, source, target):
		# Approximation: random-give one Future location instead of a
		# Discover UI. The audit row marks this for tier-N upgrade.
		import random
		entourage = ["WON_053t", "WON_053t2", "WON_053t3", "WON_053t4",
		             "WON_053t5", "WON_053t6", "WON_053t7"]
		cid = random.choice(entourage)
		source.game.cheat_action(source, [Give(source.controller, cid)])


class WON_053:
	"""Runi, Time Explorer"""

	# Battlecry: Discover a location from the FUTURE!
	play = _RuniDiscover(CONTROLLER)
