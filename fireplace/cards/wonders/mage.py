from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..classic.mage import NEW1_012
from ..gangs.mage import CFM_760
from ..gvg.mage import GVG_004, GVG_007, GVG_123
from ..tgt.mage import AT_001, AT_006, AT_007
from ..wog.mage import OG_087, OG_090

class WON_029(AT_006):
	"""Dalaran Aspirant"""

class WON_031(NEW1_012):
	"""Mana Wyrm"""

class WON_035(GVG_004):
	"""Goblin Blastmage"""

class WON_036(OG_087):
	"""Servant of Yogg-Saron"""

class WON_037(OG_090):
	"""Cabalist's Tome"""

class WON_038(GVG_007):
	"""Flame Leviathan"""

class WON_308(CFM_760):
	"""Kabal Crystal Runner"""

class WON_341(AT_001):
	"""Flame Lance"""

class WON_344(AT_007):
	"""Spellslinger"""

class WON_033(GVG_123):
	"""Soot Spewer"""


##
# Novel cards

from .hunter import _ImposterRotate


class WON_039:
	"""Black Morass Imposter"""

	# Each turn this is in your hand, transform it into a random 2-Cost
	# minion that gains Spell Damage +1.
	_imposter_cost = 2
	_imposter_keyword = "SPELLPOWER"

	class Hand:
		events = OWN_TURN_BEGIN.on(_ImposterRotate(SELF))


class _DiscoCastSecret(TargetedAction):
	# Disco at the End of Time helper: pick + cast 5 random Secrets, marking
	# each cast secret with a flag so we can destroy them on the controller's
	# next turn-begin via _DiscoCleanup.
	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		for _ in range(5):
			picker = RandomSpell(secret=True)
			pick = picker.evaluate(source)
			cid = pick[0] if isinstance(pick, list) else pick
			if not cid:
				continue
			card = ctrl.card(cid)
			card.zone = Zone.HAND
			card._disco_temp = True
			source.game.cheat_action(source, [CastSpell(card)])
		# Arm the cleanup: game._begin_turn destroys every _disco_temp
		# secret still in play at the start of the caster's next turn.
		ctrl._disco_active = True


class WON_040:
	"""Disco at the End of Time"""

	# Cast 5 random Secrets from the past. At the start of your turn,
	# destroy them. The cleanup is wired in game._begin_turn (keyed off
	# player._disco_active / secret._disco_temp).
	play = _DiscoCastSecret(CONTROLLER)


# Chromie's Historical Epoch tokens are WON_041t .. WON_041t4 — visit
# (choose) 1 of 4, shuffle the other 3 into the deck.
class _ChromieChoice(Choice):
	# Like a Discover over the 4 Epochs, but the UNCHOSEN ones are
	# shuffled into the deck rather than discarded.
	def choose(self, card):
		super().choose(card)
		for _card in self.cards:
			if _card == card:
				if len(self.player.hand) < self.player.max_hand_size:
					_card.zone = Zone.HAND
				else:
					_card.discard()
			else:
				_card.shuffle_into_deck()


class _ChromieVisit(TargetedAction):
	TARGET = ActionArg()

	def do(self, source, target):
		epochs = ["WON_041t", "WON_041t2", "WON_041t3", "WON_041t4"]
		offered = [target.card(cid, source=source) for cid in epochs]
		source.game.queue_actions(source, [_ChromieChoice(target, offered)])


class WON_041:
	"""Chromie, Timehopper"""

	# Battlecry: Visit a Historical Epoch. Shuffle the others into your deck.
	play = _ChromieVisit(CONTROLLER)
