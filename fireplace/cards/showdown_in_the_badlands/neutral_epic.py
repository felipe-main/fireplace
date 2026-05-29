"""Showdown in the Badlands — Neutral Epic cards (WILD_WEST)."""

from ..utils import *


class _AzeriteStreak(LazyNum):
	"""Lazily read the controller's "turns in a row you've played an
	Elemental" streak, defaulting to 0 when it has never been set."""

	def __init__(self, selector):
		super().__init__()
		self.selector = selector

	def evaluate(self, source):
		player = self.selector.eval(source.game, source)[0]
		return self.num(getattr(player, "azerite_elemental_streak", 0))


class _AzeriteGiantStreak(TargetedAction):
	"""Azerite Giant — at the end of each turn (while Azerite Giant is in
	hand) update the controller's "turns in a row you've played an
	Elemental" streak. If an Elemental was played this turn, bump the
	streak by one; otherwise reset it to zero. The streak drives the
	card's cost reduction (one less per turn in a row)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		if ctrl.elemental_played_this_turn > 0:
			ctrl.azerite_elemental_streak = (
				getattr(ctrl, "azerite_elemental_streak", 0) + 1
			)
		else:
			ctrl.azerite_elemental_streak = 0


class _GattlesnakeLoad(TargetedAction):
	"""Gattlesnake — at the end of your turn, load two bullets. Each
	loaded bullet is tracked on the minion via the _loaded_bullets
	counter and shown with the "Loaded Bullet" (WW_431e) marker enchant."""

	TARGET = ActionArg()

	def do(self, source, target):
		target._loaded_bullets = getattr(target, "_loaded_bullets", 0) + 2
		source.game.cheat_action(target, [Buff(target, "WW_431e") * 2])


class _GattlesnakeFire(TargetedAction):
	"""Gattlesnake deathrattle — fire every loaded bullet at a random
	enemy, each dealing 1 damage."""

	TARGET = ActionArg()

	def do(self, source, target):
		bullets = getattr(target, "_loaded_bullets", 0)
		for _ in range(bullets):
			source.game.cheat_action(target, [Hit(RANDOM(ENEMY_CHARACTERS), 1)])


##
# Minions


class WW_025:
	"""Azerite Giant"""

	# [x]Costs (1) less for each turn in a row you've played an Elemental.
	cost_mod = -_AzeriteStreak(CONTROLLER)

	class Hand:
		events = OWN_TURN_END.on(_AzeriteGiantStreak(CONTROLLER))


class WW_333:
	"""Howdyfin"""

	# [x]Whenever your hand has less than 3 cards in it, get a random Murloc.
	events = Play(CONTROLLER).after(
		(Count(FRIENDLY_HAND) < 3) & Give(CONTROLLER, RandomMurloc())
	)


class WW_351:
	"""Cattle Rustler"""

	# <b>Battlecry:</b> Draw a Beast. It costs (3) less.
	play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + BEAST)).then(
		Buff(Draw.CARD, "WW_351e")
	)


class WW_351e:
	"""Rustled"""

	# The data enchant carries no COST tag, so graft the printed
	# "Costs (3) less" reduction here.
	tags = {GameTag.COST: -3}


class WW_420:
	"""Ogre-Gang Ace"""

	# [x]<b>Rush</b> Whenever this attacks, gain <b>Divine Shield</b>.
	# <i>(50% chance to gain <b>Lifesteal</b> instead.)</i>
	events = Attack(SELF).on(
		COINFLIP & GiveLifesteal(SELF) | GiveDivineShield(SELF)
	)


class WW_431:
	"""Gattlesnake"""

	# [x]At the end of your turn, load two bullets that deal 1 damage
	# each. <b>Deathrattle:</b> Fire at random enemies!
	events = OWN_TURN_END.on(_GattlesnakeLoad(SELF))
	deathrattle = _GattlesnakeFire(SELF)
