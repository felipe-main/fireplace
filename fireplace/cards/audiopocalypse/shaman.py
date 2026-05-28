from ..utils import *
from .utils import _RemixRotate, _RemixFireVariant


class _HornOfWindlordSetTarget(TargetedAction):
	"""Horn of the Windlord — when your hero attacks a minion, set
	its stats to 3/3. Approximate via Buff with explicit atk/health
	delta computed against the target's current stats."""

	TARGET = ActionArg()
	DEFENDER = ActionArg()

	def do(self, source, target, defender):
		if isinstance(defender, (list, tuple)):
			defender = defender[0] if defender else None
		if defender is None or defender.zone != Zone.PLAY:
			return
		if defender.type != CardType.MINION:
			return
		# True SET-to-3/3: clear existing buffs first so no atk/health
		# enchant survives, then apply a fresh enchant computed from the
		# base stats. Mirrors Hearthstone "set stats" semantics where
		# pre-existing buffs are wiped before the set takes effect.
		defender.clear_buffs()
		atk_delta = 3 - defender.atk
		hp_delta = 3 - defender.max_health
		source.game.cheat_action(
			source,
			[Buff(defender, "JAM_011e", atk=atk_delta, max_health=hp_delta)],
		)


##
# Minions

class JAM_012:
	"""Remixed Totemcarver"""

	# Gains an extra effect in your hand that changes each turn.
	class Hand:
		events = OWN_TURN_BEGIN.on(_RemixRotate(SELF))
	play = _RemixFireVariant(SELF)


class JAM_012t:
	"""Loud Totemcarver"""
	# Battlecry: Summon a 0/3 Stereo Totem (ETC_105 from Festival).
	play = Summon(CONTROLLER, "ETC_105")


class JAM_012t2:
	"""Bluesy Totemcarver"""
	# Battlecry: Summon a 0/3 Mana Tide Totem (reusing the canonical
	# Mana Tide Totem token from data — fall back to the printed
	# name if id unknown).
	play = Summon(CONTROLLER, "EX1_575")


class JAM_012t3:
	"""Blazing Totemcarver"""
	# Battlecry: Summon a 0/2 Flametongue Totem (canonical id).
	play = Summon(CONTROLLER, "EX1_565")


class JAM_012t4:
	"""Karaoke Totemcarver"""
	# Battlecry: Summon a 0/4 Jukebox Totem (the Audiopocalypse
	# Paladin Jukebox Totem token JAM_010).
	play = Summon(CONTROLLER, "JAM_010")


##
# Weapons

class JAM_011:
	"""Horn of the Windlord"""

	# Windfury (data). Whenever your hero attacks a minion, set its
	# stats to 3/3.
	events = Attack(FRIENDLY_HERO).on(
		_HornOfWindlordSetTarget(SELF, Attack.DEFENDER),
	)


##
# Enchantments

JAM_011e = buff()
