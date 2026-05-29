from ..utils import *


##
# Custom actions / helpers


class _SensoryDeprivationDestroyOriginal(TargetedAction):
	"""Sensory Deprivation — after summoning a copy of an enemy minion,
	if the controller's hero is at 20 or less Health, destroy the
	original (TARGET)."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target is None:
			return
		if source.controller.hero.health <= 20:
			source.game.cheat_action(source, [Destroy(target)])


class _RestInPeaceSummonHighestDead(TargetedAction):
	"""Rest in Peace — each player summons their own highest-Cost minion
	that died this game. Iterates each player's graveyard, picks the
	max-cost MINION entity, and summons a fresh copy on that player's
	side."""

	TARGET = ActionArg()

	def do(self, source, target):
		for player in source.game.players:
			dead_minions = [
				c for c in player.graveyard if c.type == CardType.MINION
			]
			if not dead_minions:
				continue
			best = max(dead_minions, key=lambda c: c.cost or 0)
			if len(player.field) >= 7:
				continue
			source.game.cheat_action(source, [Summon(player, best.id)])


class _NarainGiveFortunes(TargetedAction):
	"""Narain Soothfancy — Battlecry: get two Fortunes (VAC_420t) that
	are copies of the top card of your deck. We hand two Fortune tokens;
	each one resolves its own copy of whatever the top card is at the
	moment it's played (see _FortunePlayTopCard)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		source.game.cheat_action(
			source, [Give(ctrl, "VAC_420t"), Give(ctrl, "VAC_420t")]
		)


class _FortunePlayTopCard(TargetedAction):
	"""Fortune — when played, it is a copy of the top card of your deck:
	make an exact copy of the current top card and play/cast it for free.
	If the deck is empty, nothing happens."""

	TARGET = ActionArg()

	def do(self, source, target):
		from ...dsl.copy import ExactCopy
		ctrl = source.controller
		if not ctrl.deck:
			return
		top = ctrl.deck[-1]
		copy = ExactCopy(top).copy(source, top)
		copy.controller = ctrl
		# Replay the copy for free: spells are cast (engine picks a legal
		# target), minions / weapons / heroes are summoned.
		source.game.cheat_action(source, [Replay(copy)])


def _voljin_swap_resolve(source, a, b):
	"""Chillin' Vol'jin — swap the stats of minions A and B using the
	Spirit Swap (VAC_957e) buff (atk/health read from the other's stats)."""
	from hearthstone.enums import Zone as _Zone
	if a is None or b is None or a is b:
		return
	if a.zone != _Zone.PLAY or b.zone != _Zone.PLAY:
		return
	source.game.cheat_action(source, [SwapStateBuff(a, b, "VAC_957e")])


class _VoljinPickB:
	"""Pick-an-entity choice over the remaining minions so the controller
	chooses the second minion whose stats to swap with the first. Mirrors
	the GenericChoice `.cards` / `.choose(card)` interface so the soak's
	resolver loop can drive it."""

	type = "ENTITY_CHOICE"
	source = None
	player = None
	min_count = 1
	max_count = 1
	cards = ()

	def __init__(self, source, player, cards):
		self.source = source
		self.player = player
		self.cards = list(cards)

	def choose(self, card):
		if card not in self.cards:
			raise ValueError("not a valid pick")
		self.player.choice = None
		a = getattr(self.source, "_voljinA", None)
		_voljin_swap_resolve(self.source, a, card)


class _VoljinSwapAction(TargetedAction):
	"""Chillin' Vol'jin — TARGET is the first chosen minion. Open a pick
	over every OTHER minion (friend or foe) so the controller picks the
	second minion, then swap their stats. A test may pre-stamp
	`source._voljinB` to skip the choice UI."""

	TARGET = ActionArg()

	def do(self, source, target):
		others = [
			m for m in source.game.board
			if m.type == CardType.MINION and m is not target
		]
		if not others:
			return
		source._voljinA = target
		pre_existing_B = getattr(source, "_voljinB", None)
		if pre_existing_B is not None and pre_existing_B in others:
			source._voljinB = None
			_voljin_swap_resolve(source, target, pre_existing_B)
			return
		source.controller.choice = _VoljinPickB(
			source, source.controller, others
		)


class _TwilightMediumSetTopCost(TargetedAction):
	"""Twilight Medium — Battlecry: set the Cost of the top card of your
	deck to (1) by applying the Candle Lit (VAC_423e4) enchant to it."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not ctrl.deck:
			return
		top = ctrl.deck[-1]
		source.game.cheat_action(source, [Buff(top, "VAC_423e4")])


##
# Spells


class VAC_404:
	"""Nightshade Tea"""

	# Deal $3 damage to a minion. Deal $2 damage to your hero.
	# (3 Drinks left!) — chains into VAC_404t1.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Hit(TARGET, 3),
		Hit(FRIENDLY_HERO, 2),
		Give(CONTROLLER, "VAC_404t1"),
	)


class VAC_404t1:
	"""Nightshade Tea"""

	# (2 Drinks left!) — chains into VAC_404t2.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Hit(TARGET, 3),
		Hit(FRIENDLY_HERO, 2),
		Give(CONTROLLER, "VAC_404t2"),
	)


class VAC_404t2:
	"""Nightshade Tea"""

	# (Last Drink!) — chain ends here.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Hit(TARGET, 3),
		Hit(FRIENDLY_HERO, 2),
	)


class VAC_414:
	"""Hot Coals"""

	# Deal $2 damage to all enemies. If your hero took damage this turn,
	# deal $1 more. `damaged_this_turn` is bumped on the hero entity in
	# Damage.do; gate the extra tick on it.
	play = (
		Hit(ENEMY_CHARACTERS, 2),
		(Attr(FRIENDLY_HERO, "damaged_this_turn") > 0) & Hit(ENEMY_CHARACTERS, 1),
	)


class VAC_417:
	"""Sensory Deprivation"""

	# Summon a copy of an enemy minion. If you have 20 or less Health,
	# destroy the original.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
	}
	play = Summon(CONTROLLER, ExactCopy(TARGET)).then(
		_SensoryDeprivationDestroyOriginal(TARGET)
	)


class VAC_419:
	"""Acupuncture"""

	# Deal $4 damage to both heroes.
	play = Hit(ALL_HEROES, 4)


class VAC_457:
	"""Rest in Peace"""

	# Each player summons their highest Cost minion that died this game.
	play = _RestInPeaceSummonHighestDead(CONTROLLER)


##
# Minions


class VAC_418:
	"""Sauna Regular"""

	# Taunt. Costs (1) less for each time your hero has taken damage on
	# your turn. The engine tracks total hero damage taken on own turns
	# (`damage_taken_on_own_turns_this_game`); we discount by that total.
	cost_mod = -Attr(CONTROLLER, "damage_taken_on_own_turns_this_game")


class VAC_420:
	"""Narain Soothfancy"""

	# Battlecry: Get two Fortunes that are copies of the top card of your
	# deck.
	play = _NarainGiveFortunes(CONTROLLER)


class VAC_423:
	"""Twilight Medium"""

	# Taunt. Battlecry: Set the Cost of the top card of your deck to (1).
	play = _TwilightMediumSetTopCost(CONTROLLER)


class VAC_512:
	"""Brain Masseuse"""

	# Whenever this minion takes damage, also deal that amount to your
	# hero.
	events = SELF_DAMAGE.on(Hit(FRIENDLY_HERO, Damage.AMOUNT))


class VAC_957:
	"""Chillin' Vol'jin"""

	# Hunter Tourist (deckbuilding only — no in-game trigger).
	# Battlecry: Choose 2 minions. Swap their stats.
	# The first chosen minion is the play TARGET; a second pick chooses
	# the other minion, then their stats are swapped via Spirit Swap.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _VoljinSwapAction(TARGET)


##
# Tokens


class VAC_420t:
	"""Fortune"""

	# This is a copy of the top card of your deck. When played, copy and
	# play the current top card for free.
	play = _FortunePlayTopCard(CONTROLLER)


##
# Enchantments


class VAC_418e:
	"""Steamy"""

	# Costs (1) less. (Sauna Regular renders its discount via cost_mod;
	# this in-data enchant carries no behaviour we apply, declared so the
	# id resolves.)
	tags = {GameTag.COST: -1}


class VAC_420e1:
	"""Fortune"""

	# Transforming into the top card of your deck. Cosmetic marker — no
	# stat tags.
	tags = {}


class VAC_423e4:
	"""Candle Lit"""

	# Costs (1). Set-cost enchant applied to the top card of the deck.
	cost = lambda self, i: 1


class VAC_957e:
	"""Spirit Swap"""

	# Swapped stats. Applied by SwapStateBuff — reads runtime _xatk /
	# _xhealth stamped onto the enchant from the other minion's stats.
	atk = lambda self, i: self._xatk
	max_health = lambda self, i: self._xhealth
