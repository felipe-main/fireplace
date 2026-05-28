from ..utils import *

# Reprints inherit from their canonical scripts via Python class
# inheritance — the merge code in cards/__init__.py uses dir(cls), which
# walks the MRO, so inherited play/events/deathrattle/tags flow through.
from ..blackrock.collectible import BRM_028, BRM_034
from ..classic.neutral_common import EX1_007
from ..gangs.neutral_common import CFM_715
from ..gangs.neutral_legendary import CFM_685, CFM_902
from ..gangs.neutral_rare import CFM_321, CFM_325, CFM_649, CFM_852
from ..naxxramas.collectible import FP1_012
from ..tgt.neutral_common import AT_090
from ..wog.neutral_common import OG_283, OG_284, OG_295
from ..wog.neutral_epic import OG_321
from ..wog.neutral_legendary import OG_131, OG_280
from ..wog.neutral_rare import OG_162

class WON_118(CFM_715):
	"""Jade Spirit"""

class WON_124(OG_284):
	"""Twilight Geomancer"""

class WON_125(OG_283):
	"""C'Thun's Chosen"""

class WON_127(OG_162):
	"""Disciple of C'Thun"""

class WON_128(FP1_012):
	"""Sludge Belcher"""

class WON_130(CFM_649):
	"""Kabal Courier"""

class WON_131(OG_321):
	"""Crazed Worshipper"""

class WON_133(BRM_028):
	"""Emperor Thaurissan"""

class WON_134(OG_131):
	"""Twin Emperor Vek'lor"""

class WON_135(OG_280):
	"""C'Thun"""

class WON_136(CFM_902):
	"""Aya Blackpaw"""

class WON_137(CFM_685):
	"""Don Han'Cho"""

class WON_328(AT_090):
	"""Mukla's Champion"""

class WON_329(BRM_034):
	"""Blackwing Corruptor"""

class WON_330(OG_295):
	"""Cult Apothecary"""

class WON_331(CFM_321):
	"""Grimestreet Informant"""

class WON_332(CFM_852):
	"""Lotus Agents"""

class WON_351(CFM_325):
	"""Small-Time Buccaneer"""

class WON_357(EX1_007):
	"""Acolyte of Pain"""


##
# Novel cards

class WON_138:
	"""Shark Puncher"""

	# Deathrattle: Give a random friendly Pirate +2/+2.
	deathrattle = Buff(RANDOM(FRIENDLY_MINIONS + PIRATE), "WON_138e")


WON_138e = buff(atk=2, health=2)


class _TimelineAccelerate(TargetedAction):
	# Draw a Mech. It costs (2) less. Use ForceDraw to keep the draw event
	# pipeline, then apply a cost-mod enchant.
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		import random
		mechs = [c for c in ctrl.deck if c.type == CardType.MINION
		         and Race.MECHANICAL in c.data.races]
		if mechs:
			pick = random.choice(mechs)
			source.game.cheat_action(source, [ForceDraw(pick)])
			source.game.cheat_action(source, [Buff(pick, "WON_139e")])


class WON_139:
	"""Timeline Accelerator"""

	# Battlecry: Draw a Mech. It costs (2) less.
	play = _TimelineAccelerate(CONTROLLER)


@custom_card
class WON_139e:
	tags = {
		GameTag.CARDNAME: "Timeline Acceleration",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -2,
	}


class WON_140:
	"""Future Emissary"""

	# Battlecry: Reduce the Cost of all Dragons in your hand by (1). Give
	# them +1/+1. Approximation: -1 cost via additive enchant; +1/+1 buff.
	play = (
		Buff(FRIENDLY_HAND + DRAGON, "WON_140cost"),
		Buff(FRIENDLY_HAND + DRAGON, "WON_140e", atk=1, max_health=1),
	)


@custom_card
class WON_140cost:
	tags = {
		GameTag.CARDNAME: "Future Cost",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -1,
	}


class _MenagerieBuff(TargetedAction):
	# Pick 3 random friendly minions of DIFFERENT minion types and buff.
	TARGET = ActionArg()
	def do(self, source, target):
		ctrl = source.controller
		buff_id = getattr(source, "_menagerie_buff", "WON_141e")
		import random
		minions = [m for m in ctrl.field if m is not source]
		random.shuffle(minions)
		picked = []
		races_seen = set()
		for m in minions:
			race = next(iter(m.races), None) if m.races else None
			key = race if race else "no-race"
			if key not in races_seen:
				races_seen.add(key)
				picked.append(m)
				if len(picked) == 3:
					break
		atk = getattr(source, "_menagerie_atk", 1)
		hp = getattr(source, "_menagerie_hp", 1)
		for m in picked:
			source.game.cheat_action(
				source, [Buff(m, buff_id, atk=atk, max_health=hp)]
			)


class WON_141:
	"""Menagerie Mug"""

	# Battlecry: Give 3 random friendly minions of different minion types
	# +1/+1.
	_menagerie_buff = "WON_141e"
	_menagerie_atk = 1
	_menagerie_hp = 1
	play = _MenagerieBuff(CONTROLLER)


class WON_142:
	"""Menagerie Jug"""

	# Battlecry: Give 3 random friendly minions of different minion types
	# +2/+2.
	_menagerie_buff = "WON_142e"
	_menagerie_atk = 2
	_menagerie_hp = 2
	play = _MenagerieBuff(CONTROLLER)


class _AmalgamSummon(TargetedAction):
	TARGET = ActionArg()
	def do(self, source, target):
		picker = RandomMinion(cost=1)
		pick = picker.evaluate(source)
		cid = pick[0] if isinstance(pick, list) else pick
		if cid:
			source.game.cheat_action(
				source, [Summon(source.controller, cid)]
			)


class WON_143:
	"""Infinite Amalgam"""

	# Inspire, Frenzy, Spellburst, Honorable Kill, and Overkill: Summon a
	# random 1-Cost minion. Five hooks all calling the same effect.
	inspire = _AmalgamSummon(CONTROLLER)
	frenzy = _AmalgamSummon(CONTROLLER)
	spellburst = _AmalgamSummon(CONTROLLER)
	honorable_kill = _AmalgamSummon(CONTROLLER)
	overkill = _AmalgamSummon(CONTROLLER)


class _EyestalkMirror(TargetedAction):
	# Whenever your C'Thun gains Attack or Health, this does too. Find
	# C'Thun (in deck/hand/play) and mirror its buffs. Approximation: on
	# any friendly Buff event we check if the target was C'Thun and apply
	# the same buff to us if so.
	TARGET = ActionArg()
	BUFF = ActionArg()
	def do(self, source, target, buff):
		# Mirror only if the buffed entity is a C'Thun (canonical OG_280)
		if getattr(target, "id", None) not in ("OG_280", "WON_135"):
			return
		# Build a same-stat buff onto self via a transient enchant.
		atk = getattr(buff, "atk", 0) or 0
		hp = getattr(buff, "max_health", 0) or 0
		if atk or hp:
			source.game.cheat_action(
				source,
				[Buff(source, "WON_144e", atk=atk, max_health=hp)],
			)


@custom_card
class WON_144e:
	tags = {
		GameTag.CARDNAME: "C'Thun Echo",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


class WON_144:
	"""Eyestalk of C'Thun"""

	# Taunt, Lifesteal (data). Whenever your C'Thun gains Attack or
	# Health, this does too (wherever it is).
	events = Buff(FRIENDLY).after(_EyestalkMirror(SELF, Buff.BUFF))


class WON_146:
	"""Soridormi"""

	# Dormant for 2 turns. When this awakens, reduce the Cost of all
	# Dragons in your hand by (3) and give them +3/+3 (per wiki text).
	play = Dormant(SELF, 2)
	dormant_events = []
	awaken = (
		Buff(FRIENDLY_HAND + DRAGON, "WON_146cost"),
		Buff(FRIENDLY_HAND + DRAGON, "WON_146e", atk=3, max_health=3),
	)


@custom_card
class WON_146cost:
	tags = {
		GameTag.CARDNAME: "Time Compression",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -3,
	}


class WON_345:
	"""Valstann Staghelm"""

	# Deathrattle: Summon a Taunt minion from your deck.
	deathrattle = Summon(
		CONTROLLER,
		RANDOM(FRIENDLY_DECK + MINION + TAUNT),
	)

