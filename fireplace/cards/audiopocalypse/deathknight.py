from ..utils import *

from hearthstone.enums import Race as _Race


class _YellingYodelerDouble(TargetedAction):
	"""Yelling Yodeler — fire the target minion's Deathrattle twice
	without killing the minion. Uses the engine's Deathrattle action
	directly so reborn / on-deathrattle hooks all fire."""

	TARGET = ActionArg()

	def do(self, source, target):
		if not target.has_deathrattle:
			return
		source.game.cheat_action(source, [Deathrattle(target) * 2])


class _DeadAirResurrect(TargetedAction):
	"""Dead Air — destroy every friendly Undead minion, then resummon
	each by its original card id. Order: destroy all first (so each
	deathrattle fires from the same dying snapshot), then summon all
	from the captured id list."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		victims = [
			m for m in list(ctrl.field)
			if _Race.UNDEAD in m.races
		]
		if not victims:
			return
		ids = [m.id for m in victims]
		for v in victims:
			source.game.cheat_action(source, [Destroy(v)])
		for cid in ids:
			source.game.cheat_action(source, [Summon(ctrl, cid)])


##
# Minions

class JAM_005:
	"""Yelling Yodeler"""

	# Battlecry: Trigger a friendly minion's Deathrattle twice.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_TARGET_WITH_DEATHRATTLE: 0,
	}
	play = _YellingYodelerDouble(TARGET)


class JAM_007:
	"""Cool Ghoul"""

	# Divine Shield, Reborn. Both keywords sit in data — no script needed.


##
# Spells

class JAM_006:
	"""Cold Feet"""

	# Enemy minions cost (5) more next turn. Implementation: stamp a
	# per-card +5 cost enchant on every card in the opponent's hand
	# that is a minion, plus a listener that auto-removes the enchant
	# at the opponent's next OWN_TURN_END (i.e. after their turn).
	play = Buff(ENEMY_HAND + MINION, "JAM_006e")


class JAM_008:
	"""Dead Air"""

	# Destroy your Undead. Resummon them.
	play = _DeadAirResurrect(CONTROLLER)


##
# Enchantments

@custom_card
class JAM_006e:
	# Cold Feet — +5 cost while on an enemy hand minion. Self-destroys
	# at the end of the controller's (the enemy's) next turn.
	tags = {
		GameTag.CARDNAME: "Cold Feet",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: 5,
	}
	events = OWN_TURN_END.on(Destroy(SELF))
