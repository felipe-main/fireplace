from ..utils import *


##
# Custom actions / helpers


class _ZokSummonQuilboars(TargetedAction):
	"""Zok Fogsnout — Battlecry: Summon two Quilboars with stats equal to
	{hero attack + armor gained this turn}/{same}. We capture the values
	from the controller at battlecry resolution and stamp each Quilboar
	with a +N/+N buff so the printed 1/1 token ends up at the printed
	stats (delta = max(0, stats - 1))."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		hero_atk = ctrl.hero.atk or 0
		armor_now = ctrl.hero.armor or 0
		armor_start = getattr(ctrl, "_zok_armor_at_turn_start", armor_now)
		armor_gained = max(0, armor_now - armor_start)
		stats = hero_atk + armor_gained
		# Token is the 1/1 Fogsnout Fan (ETC_386t, Taunt in data). Summon
		# two, then buff each to the captured stats via the runtime-stat
		# enchant.
		for _ in range(2):
			source.game.cheat_action(source, [Summon(target, "ETC_386t")])
		if not ctrl.field:
			return
		latest = list(ctrl.field)[-2:]
		delta = max(0, stats - 1)
		if delta <= 0:
			return
		for m in latest:
			source.game.cheat_action(
				source, [Buff(m, "ETC_386e", atk=delta, max_health=delta)]
			)


class _FreeSpiritBumpArmor(TargetedAction):
	"""Free Spirit — bump the controller's `heropower_extra_armor`
	counter (Druid hero power reads it and adds extra armor on top of
	its base 1). Battlecry + Deathrattle both fire this."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.heropower_extra_armor = (
			getattr(target, "heropower_extra_armor", 0) + 1
		)


class _GroovyCatBumpAttack(TargetedAction):
	"""Groovy Cat — bump the controller's `heropower_extra_attack`
	counter (Druid hero power reads it and adds extra attack on top
	of its base +1)."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.heropower_extra_attack = (
			getattr(target, "heropower_extra_attack", 0) + 1
		)


class _TimberTambourineBumpCounter(TargetedAction):
	"""Timber Tambourine — bump the per-weapon counter
	`_cards_cost_5_plus_played_while_equipped` whenever the controller
	plays a card costing 5 or more while the weapon is in play."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardType
		if target is None:
			return
		if getattr(target, "type", None) == CardType.PLAYER:
			return
		cost = getattr(target, "cost", 0) or 0
		if cost < 5:
			return
		source._cards_cost_5_plus_played_while_equipped = (
			getattr(source, "_cards_cost_5_plus_played_while_equipped", 0) + 1
		)


class _TimberTambourineDeathrattle(TargetedAction):
	"""Timber Tambourine — Deathrattle: Summon @ 5/5 Ancients, where @
	is the per-weapon counter accumulated while equipped."""

	TARGET = ActionArg()

	def do(self, source, target):
		n = getattr(source, "_cards_cost_5_plus_played_while_equipped", 0)
		if n <= 0:
			return
		for _ in range(n):
			source.game.cheat_action(source, [Summon(target, "ETC_387bt")])


##
# Spells


class ETC_373:
	"""Drum Circle"""

	# Choose One: Summon five 2/2 Treants; or Give your minions +2/+4
	# and Taunt. Sub-cards ETC_373a and ETC_373b carry the two effects.
	choose = ("ETC_373a", "ETC_373b")


class ETC_373a:
	"""Flower Power"""

	# Summon five 2/2 Treants. ETC_373t is the 2/2 Treant token in data.
	play = Summon(CONTROLLER, "ETC_373t") * 5


class ETC_373b:
	"""Good Vibrations"""

	# Give your minions +2/+4 and Taunt. ETC_373be is the in-data buff
	# (no parsed stats — declared in this file).
	play = Buff(FRIENDLY_MINIONS, "ETC_373be"), Taunt(FRIENDLY_MINIONS)


class ETC_373t:
	"""Treant"""

	# Vanilla 2/2 token, no script.


@custom_card
class ETC_373be:
	# Not in data — register manually. +2/+4 stamp; the Taunt is set
	# separately via the SetTag helper.
	tags = {
		GameTag.CARDNAME: "Drum Circle",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 2,
		GameTag.HEALTH: 4,
	}


class ETC_375:
	"""Peaceful Piper"""

	# Choose One: Draw a Beast; or Discover one.
	choose = ("ETC_375a", "ETC_375b")


class ETC_375a:
	"""Friendly Face"""

	# Draw a Beast.
	play = ForceDraw(RANDOM(FRIENDLY_DECK + BEAST))


class ETC_375b:
	"""Happy Hippie"""

	# Discover a Beast.
	play = DISCOVER(RandomBeast())


class ETC_376:
	"""Summer Flowerchild"""

	# Battlecry: Draw two cards that cost (6) or more. Finale: They
	# cost (1) less. ForceDraw against the deck's COST>=6 pool; if
	# Finale fired, stamp ETC_376e (-1 cost) on the freshly-drawn card
	# via the .then() callback (Draw.CARD = the drawn entity).
	play = (
		ForceDraw(RANDOM(FRIENDLY_DECK + (COST >= 6))).then(
			FINALE & Buff(ForceDraw.TARGET, "ETC_376e"),
		),
		ForceDraw(RANDOM(FRIENDLY_DECK + (COST >= 6))).then(
			FINALE & Buff(ForceDraw.TARGET, "ETC_376e"),
		),
	)


class ETC_376e:
	# In-data buff "Sunny" — Costs (1) less. COST not parsed; declare.
	tags = {GameTag.COST: -1}


class ETC_379:
	"""Harmonic Mood"""

	# Give your hero +2 Attack this turn. Gain 4 Armor. (Swaps each
	# turn — approximation: only the printed base effect ships; the
	# turn-swap is TODO.)
	play = Buff(FRIENDLY_HERO, "ETC_379e"), GainArmor(FRIENDLY_HERO, 4)


@custom_card
class ETC_379e:
	# Not in data — register manually. +2 Attack this turn (temporary
	# flag clears at end of turn via the standard pipeline).
	tags = {
		GameTag.CARDNAME: "Harmonic Mood",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 2,
		enums.TEMPORARY: True,
	}


class ETC_384:
	"""Spread the Word"""

	# Draw 2 cards. Costs (1) less for each Attack your hero has.
	cost_mod = -Attr(FRIENDLY_HERO, GameTag.ATK)
	play = Draw(CONTROLLER) * 2


class ETC_387:
	"""Rhythm and Roots"""

	# Choose One (Secretly): Summon three 5/5 Ancients in 2 turns; or
	# 8/8 Giants in 4 turns. Approximation: just summon the minions
	# immediately (no dormant delay, no "secret" hidden-choice path).
	# TODO: dormant-on-summon + hidden choose-one variant.
	choose = ("ETC_387b", "ETC_387c")


class ETC_387b:
	"""Ancient's Melody"""

	# Summon three 5/5 Ancients (printed: Dormant 2 turns; approximation
	# summons them straight away).
	play = Summon(CONTROLLER, "ETC_387bt") * 3


class ETC_387c:
	"""Giant's Dance"""

	# Summon an 8/8 Giant (printed: Dormant 4 turns; approximation
	# summons immediately).
	play = Summon(CONTROLLER, "ETC_387ct")


class ETC_387bt:
	"""Ancient"""


class ETC_387ct:
	"""Giant"""


##
# Minions


class ETC_382:
	"""Free Spirit"""

	# Battlecry and Deathrattle: Your Hero Power gains 1 more Armor this
	# game. Bumps the controller's `heropower_extra_armor` counter; the
	# druid hero power reads it at activate time.
	play = _FreeSpiritBumpArmor(CONTROLLER)
	deathrattle = _FreeSpiritBumpArmor(CONTROLLER)


class ETC_385:
	"""Groovy Cat"""

	# Battlecry and Deathrattle: Your Hero Power gives your hero 1 more
	# Attack this game. Bumps the controller's `heropower_extra_attack`
	# counter; druid hero power reads it at activate time.
	play = _GroovyCatBumpAttack(CONTROLLER)
	deathrattle = _GroovyCatBumpAttack(CONTROLLER)


class ETC_386:
	"""Zok Fogsnout"""

	# Battlecry: Summon two {hero_atk + armor_gained_this_turn}/{same}
	# Quilboars with Taunt. We summon the 1/1 Fogsnout Fan (ETC_386t,
	# Taunt in data) and stamp a stat buff to lift to the captured stats.
	play = _ZokSummonQuilboars(CONTROLLER)


class ETC_386t:
	"""Fogsnout Fan"""

	# Vanilla 1/1 Taunt token (Taunt is in data).


@custom_card
class ETC_386e:
	# Not in data — variable atk/health stamped at runtime via Buff
	# kwargs. No static stats here.
	tags = {
		GameTag.CARDNAME: "Zok Fogsnout",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


##
# Weapons


class ETC_388:
	"""Timber Tambourine"""

	# Deathrattle: Summon @ 5/5 Ancients. (Play cards that cost (5)+
	# while equipped to improve!) Per-weapon counter is bumped by an
	# in-play Play listener gated on the played card's cost.
	events = Play(CONTROLLER).after(
		_TimberTambourineBumpCounter(Play.CARD),
	)
	deathrattle = _TimberTambourineDeathrattle(CONTROLLER)
