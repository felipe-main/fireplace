"""Showdown in the Badlands — Neutral Epic cards (WILD_WEST)."""

from ..utils import *


class _AzeriteStreak(LazyNum):
	"""Lazily read the controller's "turns in a row you've played an
	Elemental" streak. The base streak (azerite_elemental_streak) counts
	completed consecutive turns and is maintained globally in
	game._begin_turn; if the controller has already played an Elemental on
	the current turn, that turn counts too — so the discount grows the
	moment you play this turn's Elemental."""

	def __init__(self, selector):
		super().__init__()
		self.selector = selector

	def evaluate(self, source):
		player = self.selector.eval(source.game, source)[0]
		streak = player.azerite_elemental_streak
		if player.elemental_played_this_turn > 0:
			streak += 1
		return self.num(streak)


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


def _howdyfin_fill(source, ctrl, exclude=None):
	"""Refill ctrl's hand up to 3 cards with random Murlocs. The printed
	card "keeps filling the player's hand until they have 3 cards every
	time the hand size gets lower than 3", so this loops (giving more than
	one Murloc when the hand dropped by more than one) and stops the instant
	the hand reaches 3 (or fills). `exclude` holds card(s) in hand right now
	but about to leave (the in-flight Discard target), so they are not
	counted toward the 3. The DSL passes selector results as a list, so
	normalise to a set of entities."""
	if exclude is None:
		excluded = set()
	elif hasattr(exclude, "__iter__"):
		excluded = set(exclude)
	else:
		excluded = {exclude}
	for _ in range(ctrl.max_hand_size):
		held = [c for c in ctrl.hand if c not in excluded]
		if len(held) >= 3:
			break
		source.game.cheat_action(source, [Give(ctrl, RandomMurloc())])


class _HowdyfinRefillOnPlay(TargetedAction):
	"""Howdyfin refill triggered by a card the controller PLAYED (which has
	already left hand by the AFTER broadcast, so nothing to exclude)."""

	TARGET = ActionArg()

	def do(self, source, target):
		_howdyfin_fill(source, target)


class _HowdyfinRefillOnDiscard(TargetedAction):
	"""Howdyfin refill triggered by a DISCARD. Discard broadcasts ON before
	the card's zone changes, so the discarded card (CARD) is still in hand
	and must be excluded from the count."""

	TARGET = ActionArg()
	CARD = ActionArg()

	def do(self, source, target, card):
		_howdyfin_fill(source, target, exclude=card)


##
# Minions


class WW_025:
	"""Azerite Giant"""

	# [x]Costs (1) less for each turn in a row you've played an Elemental.
	cost_mod = -_AzeriteStreak(CONTROLLER)


class WW_333:
	"""Howdyfin"""

	# [x]Whenever your hand has less than 3 cards in it, get a random Murloc.
	# Triggers on any action that drops the controller's hand below 3 — both
	# playing and discarding a card — and refills back up to 3 Murlocs.
	# Play filters on the acting player and fires AFTER the card has left
	# hand. Discard broadcasts the discarded card (ON, before zone change),
	# so it filters on a FRIENDLY card and excludes that in-flight card.
	events = (
		Play(CONTROLLER).after(_HowdyfinRefillOnPlay(CONTROLLER)),
		Discard(FRIENDLY).on(_HowdyfinRefillOnDiscard(CONTROLLER, Discard.TARGET)),
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
