from ..utils import *


class _DoomkinStealMana(TargetedAction):
	"""Doomkin — take one of the opponent's empty Mana Crystals: drop
	the opponent's max_mana by 1, raise ours by 1 (capped at 10).
	Acts only on EMPTY crystals (opp.used_mana < opp.max_mana). If the
	opponent has no empty crystal this turn, nothing happens."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		opp = ctrl.opponent
		# An "empty" crystal is one not currently spent — opp.max_mana
		# greater than opp.used_mana. Their unused crystals are the
		# candidates; we take one.
		if opp.max_mana - opp.used_mana <= 0:
			return
		if opp.max_mana <= 0:
			return
		opp.max_mana -= 1
		if ctrl.max_mana < ctrl.max_resources:
			ctrl.max_mana += 1


class _PixieNextHeroPowerFree(TargetedAction):
	"""Popular Pixie — second Choose option: your next Hero Power this
	turn costs (0). Sets the per-turn flag consumed by HeroPower's
	pay_cost path (see Player.pay_cost / actions.py:803)."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.next_hero_power_costs_zero = 1


##
# Minions

class JAM_026:
	"""Popular Pixie"""

	# Choose One - Refresh your Hero Power; or Your next one costs (0).
	choose = ("JAM_026a", "JAM_026b")


class JAM_026a:
	"""Soothing Melody"""
	# Refresh your Hero Power (reset activations_this_turn so it can be
	# used again this turn).
	play = RefreshHeroPower(FRIENDLY_HERO_POWER)


class JAM_026b:
	"""Inspirational Lyrics"""
	# Your next Hero Power this turn costs (0).
	play = _PixieNextHeroPowerFree(CONTROLLER)


class JAM_028:
	"""Blood Treant"""

	# Costs Health instead of Mana. Engine handles via the
	# `card_costs_health` boolean property; the pay_cost path in
	# player.py routes the cost to hero damage when set.
	card_costs_health = True


class JAM_029:
	"""Doomkin"""

	# Battlecry: Take one of your opponent's empty Mana Crystals.
	play = _DoomkinStealMana(CONTROLLER)
