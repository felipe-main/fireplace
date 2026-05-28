from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..gangs.druid import CFM_343, CFM_816
from ..gvg.druid import GVG_035
from ..karazhan.collectible import KAR_065
from ..tgt.druid import AT_041, AT_045
from ..wog.druid import OG_188, OG_202, OG_293, OG_313

class WON_003(AT_041):
	"""Knight of the Wild"""

class WON_009(OG_313):
	"""Addled Grizzly"""

class WON_010(OG_188):
	"""Klaxxi Amber-Weaver"""

class WON_011(GVG_035):
	"""Malorne"""

class WON_012(AT_045):
	"""Aviana"""

class WON_300(CFM_816):
	"""Virmen Sensei"""

class WON_302(OG_202):
	"""Mire Keeper"""

class WON_303(CFM_343):
	"""Jade Behemoth"""

class WON_304(OG_293):
	"""Dark Arakkoa"""

class WON_305(KAR_065):
	"""Menagerie Warden"""


##
# Novel cards

class WON_013:
	"""Rat Sensei"""

	# Battlecry and Deathrattle: Add two 1/1 Turtles with Taunt to your hand.
	play = Give(CONTROLLER, "WON_013t") * 2
	deathrattle = Give(CONTROLLER, "WON_013t") * 2


class WON_014:
	"""Invigorate"""

	# Choose One — Gain an empty Mana Crystal; or Draw a card.
	# Sub-card ids are listed in data (c.choose_cards = WON_014a/b) but
	# neither id exists as a standalone CardXML — we register both as
	# @custom_card below so the engine can resolve them.
	choose = ("WON_014a", "WON_014b")
	play = ChooseBoth(CONTROLLER) & (GainMana(CONTROLLER, 1), Draw(CONTROLLER))


@custom_card
class WON_014a:
	tags = {
		GameTag.CARDNAME: "Invigorate (Mana)",
		GameTag.CARDTYPE: CardType.SPELL,
		GameTag.CLASS: CardClass.DRUID,
		GameTag.COST: 2,
	}
	play = GainMana(CONTROLLER, 1)


@custom_card
class WON_014b:
	tags = {
		GameTag.CARDNAME: "Invigorate (Draw)",
		GameTag.CARDTYPE: CardType.SPELL,
		GameTag.CLASS: CardClass.DRUID,
		GameTag.COST: 2,
	}
	play = Draw(CONTROLLER)


class WON_015:
	"""Cenarion Hold"""

	# Location: Your next Choose One card this turn has both effects combined.
	# Uses the existing IncreaseAttr action that other Choose-One-combiner
	# cards (TITANS druid Heart of the Wild, Onyxia's Lair) use.
	activate = IncreaseAttr(CONTROLLER, "next_choose_one_combined", 1)
