from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..gangs.shaman import CFM_310, CFM_312, CFM_707
from ..karazhan.collectible import KAR_021
from ..naxxramas.collectible import FP1_025
from ..tgt.shaman import AT_046, AT_048, AT_049, AT_050
from ..wog.shaman import OG_209

class WON_081(AT_046):
	"""Tuskarr Totemic"""

class WON_082(CFM_707):
	"""Jade Lightning"""

class WON_083(KAR_021):
	"""Wicked Witchdoctor"""

class WON_084(CFM_312):
	"""Jade Chieftain"""

class WON_085(AT_049):
	"""Thunder Bluff Valiant"""

class WON_086(CFM_310):
	"""Call in the Finishers"""

class WON_320(AT_048):
	"""Healing Wave"""

class WON_321(AT_050):
	"""Charged Hammer"""

class WON_335(FP1_025):
	"""Reincarnate"""

class WON_336(OG_209):
	"""Hallazeal the Ascended"""


##
# Novel cards

class _PebblyPageDraw(TargetedAction):
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		import random
		overload_cards = [c for c in ctrl.deck
		                  if (c.data.tags.get(GameTag.OVERLOAD, 0) or 0) > 0]
		if overload_cards:
			pick = random.choice(overload_cards)
			source.game.cheat_action(source, [ForceDraw(pick)])


class WON_090:
	"""Pebbly Page"""

	# Battlecry: Draw an Overload card. You can't be Overloaded this turn.
	# cant_overload is passed as a Buff kwarg so it lands on the enchant
	# instance; Player.cant_overload (slot_buff_property) ORs over buffs.
	play = (
		_PebblyPageDraw(CONTROLLER),
		Buff(CONTROLLER, "WON_090e", cant_overload=True),
	)


class WON_090e:
	"""Pebbled"""
	# cant_overload is supplied as a Buff kwarg (a bare class attr never
	# reaches the buff instance). Self-destruct at turn end.
	events = OWN_TURN_END.on(Destroy(SELF))



class WON_091:
	"""Totally Totems"""

	# Summon all FIVE basic Totems. Overload: (1) is in data.
	play = (
		Summon(CONTROLLER, "NEW1_009"),  # Healing Totem
		Summon(CONTROLLER, "CS2_050"),  # Searing Totem
		Summon(CONTROLLER, "CS2_051"),  # Stoneclaw Totem
		Summon(CONTROLLER, "CS2_052"),  # Wrath of Air Totem
		Summon(CONTROLLER, "CS2_058"),  # Strength Totem
	)


class _AlakirDrawKeyword(TargetedAction):
	# Hero Battlecry: draw a Charge, Divine Shield, Taunt, and Windfury
	# minion from your deck.
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		import random
		for tag in (GameTag.CHARGE, GameTag.DIVINE_SHIELD,
		            GameTag.TAUNT, GameTag.WINDFURY):
			cands = [c for c in ctrl.deck
			         if c.type == CardType.MINION
			         and (c.data.tags.get(tag, 0) or 0) > 0]
			if cands:
				card = random.choice(cands)
				source.game.cheat_action(source, [ForceDraw(card)])


class WON_092h:
	"""Al'Akir, the Winds of Time"""

	# HERO card. Battlecry: Draw a Charge, Divine Shield, Taunt, and
	# Windfury minion. Hero power swap to WON_092p is handled by data.
	play = _AlakirDrawKeyword(CONTROLLER)
