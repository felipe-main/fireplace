from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..blackrock.collectible import BRM_008
from ..gangs.rogue import CFM_690, CFM_691
from ..league.collectible import LOE_012
from ..tgt.rogue import AT_028, AT_033, AT_034, AT_036
from ..wog.rogue import OG_282, OG_330

class WON_067(CFM_691):
	"""Jade Swarmer"""

class WON_070(CFM_690):
	"""Jade Shuriken"""

class WON_071(AT_033):
	"""Burgle"""

class WON_073(BRM_008):
	"""Dark Iron Skulker"""

class WON_075(OG_282):
	"""Blade of C'Thun"""

class WON_076(AT_036):
	"""Anub'arak"""

class WON_316(AT_028):
	"""Shado-Pan Rider"""

class WON_317(OG_330):
	"""Undercity Huckster"""

class WON_318(AT_034):
	"""Poisoned Blade"""

class WON_340(LOE_012):
	"""Tomb Pillager"""


##
# Novel cards

from .hunter import _ImposterRotate


class WON_077:
	"""Mount Hyjal Imposter"""

	# Each turn this is in your hand, transform it into a random 4-Cost
	# minion that gains Stealth.
	_imposter_cost = 4
	_imposter_keyword = "STEALTH"

	class Hand:
		events = OWN_TURN_BEGIN.on(_ImposterRotate(SELF))


class _JadeTelegramChoice(Choice):
	# The caster looks at 3 of the opponent's real hand cards and picks
	# one to shuffle into the opponent's deck. The other two are the
	# opponent's actual cards — leave them in hand.
	def choose(self, card):
		super().choose(card)
		card.shuffle_into_deck()   # card.controller is the opponent


class _JadeTelegram(TargetedAction):
	# Look at 3 cards in opp hand, shuffle the chosen one into their deck,
	# then summon a Jade Golem.
	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		opp = ctrl.opponent
		# Summon the Jade Golem first: queuing the choice below sets
		# ctrl.choice, which would otherwise defer the summon until the
		# choice resolves.
		source.game.cheat_action(source, [SummonJadeGolem(ctrl)])
		if opp.hand:
			n = min(3, len(opp.hand))
			offered = source.game.random.sample(list(opp.hand), n)
			# player = the caster (the choice is theirs); cards = opp's.
			source.game.queue_actions(source, [_JadeTelegramChoice(ctrl, offered)])


class WON_078:
	"""Jade Telegram"""

	# Look at 3 cards in your opponent's hand and shuffle one back. Summon
	# a Jade Golem.
	play = _JadeTelegram(CONTROLLER)


class WON_079:
	"""The Scarab Lord"""

	# Battlecry: Summon a 0/2 Gong for your opponent. Combo: Gain Rush.
	play = Summon(OPPONENT, "WON_079t")
	combo = (Summon(OPPONENT, "WON_079t"), GiveRush(SELF))


class _ScarabGongDamage(TargetedAction):
	# Scarab Gong (WON_079t) deathrattle/on-damage: fill opponent's board
	# with 1/1 Scarabs. The Gong is on OPPONENT's side, so "opponent's
	# board" relative to the Gong is actually the player who summoned it
	# (the original caster).
	TARGET = ActionArg()

	def do(self, source, target):
		# The Scarab Gong (WON_079t) was summoned on the original Scarab
		# Lord's *opponent's* side — when it takes damage we fill the
		# Scarab Gong's opponent's board (= the original caster's
		# opponent again). For our purposes, fill the caster's side:
		filler = source.controller.opponent
		slots = max(0, 7 - len(filler.field))
		for _ in range(slots):
			source.game.cheat_action(
				source, [Summon(filler, "WON_079t2")]
			)


class WON_079t:
	"""Scarab Gong"""

	# After this takes damage, fill your opponent's board with 1/1 Scarabs.
	events = Damage(SELF).after(_ScarabGongDamage(SELF))
