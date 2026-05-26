from ..utils import *


##
# Custom actions


class _EnergyShaperMorphHand(TargetedAction):
	"""Energy Shaper — for every spell in the controller's hand, morph it
	into a random spell whose cost equals the original spell's cost + 2.
	Approximation: each picked replacement is sampled from the full
	collectible spell pool (no class restriction) and stamped with
	RLK_545e to record the +2 cost bump. The replacement's intrinsic cost
	already differs from the original, so we don't extra-modify cost — the
	enchant is purely a marker / engine attachment.
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		from ... import cards as _cards
		ctrl = target
		spells = [c for c in list(ctrl.hand) if c.type == CardType.SPELL]
		for sp in spells:
			new_cost = (sp.cost or 0) + 2
			pool = _cards.db.filter(
				collectible=True, type=CardType.SPELL, cost=new_cost
			)
			if not pool:
				continue
			new_id = source.game.random.choice(pool)
			source.game.cheat_action(source, [Morph(sp, new_id)])


class _VastWisdomSwapCosts(TargetedAction):
	"""Vast Wisdom — printed text: "Discover two spells that cost (3) or
	less. Swap their Costs." Approximation: pick two random ≤3 cost
	collectible spells, give both to the controller, then swap their
	costs via the RLK_546e enchant (cost mod recorded on each card so it
	persists while in hand).
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		from ... import cards as _cards
		pool = _cards.db.filter(
			collectible=True, type=CardType.SPELL, cost=[0, 1, 2, 3]
		)
		if len(pool) < 2:
			return
		picks = source.game.random.sample(pool, 2)
		a_id, b_id = picks
		a_card = source.controller.card(a_id)
		b_card = source.controller.card(b_id)
		a_cost = a_card.cost or 0
		b_cost = b_card.cost or 0
		# Give both to hand.
		source.game.cheat_action(
			source,
			[Give(source.controller, a_id), Give(source.controller, b_id)],
		)
		# Last two given cards live at the tail of the hand.
		hand = list(source.controller.hand)
		if len(hand) >= 2:
			given_a, given_b = hand[-2], hand[-1]
			# Set each card's cost to the other's.
			source.game.cheat_action(
				source,
				[
					Buff(given_a, "RLK_546e2", cost=b_cost - a_cost),
					Buff(given_b, "RLK_546e2", cost=a_cost - b_cost),
				],
			)


class _RommathRecastNonStarting(TargetedAction):
	"""Grand Magister Rommath — recast each spell the controller has cast
	this game that didn't start in their deck. Reads
	`controller.cards_played_this_game` and filters by SPELL type and the
	per-card `_from_starting_deck` flag.
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		spells = [
			c for c in list(ctrl.cards_played_this_game)
			if c.type == CardType.SPELL
			and not getattr(c, "_from_starting_deck", False)
		]
		for sp in spells:
			source.game.cheat_action(source, [CastSpell(sp.id)])


##
# Spells


class RLK_544:
	"""Arcane Defenders"""

	# Summon two 5/6 Golems with Taunt and "Can't be targeted by spells
	# or Hero Powers."
	play = Summon(CONTROLLER, "RLK_544t") * 2


class RLK_544t:
	"""Golem Guardian"""


class RLK_546:
	"""Vast Wisdom"""

	# Discover two spells that cost (3) or less. Swap their Costs.
	# Approximation: random pick of two ≤3-cost spells (not a true
	# Discover UI), then swap their costs via RLK_546e2 cost-delta buff.
	play = _VastWisdomSwapCosts(CONTROLLER)


class RLK_843:
	"""Arcane Bolt"""

	# Deal $2 damage. Manathirst (8): Deal $3 damage instead.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
	}
	play = (MANATHIRST(8) & Hit(TARGET, 3)) | Hit(TARGET, 2)


##
# Minions


class _VexallusEchoOnce(TargetedAction):
	"""Vexallus echo — cast a copy of the just-played Arcane spell, but
	only if we are not already inside a Vexallus-driven recast (guards
	against infinite recursion when a recast itself triggers OWN_SPELL_PLAY
	listeners that match the original spell)."""

	TARGET = ActionArg()
	SPELL = ActionArg()
	SPELL_TARGET = ActionArg()

	def do(self, source, target, spell, spell_target):
		if isinstance(spell, list):
			spell = spell[0] if spell else None
		if isinstance(spell_target, list):
			spell_target = spell_target[0] if spell_target else None
		if spell is None:
			return
		if target._recast_depth > 0:
			return
		target._recast_depth += 1
		try:
			source.game.cheat_action(source, [CastSpell(spell.id, spell_target)])
		finally:
			target._recast_depth -= 1


class RLK_541:
	"""Vexallus"""

	# Your Arcane spells cast twice.
	# Recursion guard via Player._recast_depth so a recast triggering
	# another OWN_SPELL_PLAY hook doesn't infinitely re-fire Vexallus.
	events = Play(CONTROLLER, SPELL + ARCANE_SPELL).after(
		_VexallusEchoOnce(CONTROLLER, Play.CARD, Play.TARGET)
	)


class RLK_542:
	"""Arcsplitter"""

	# Deathrattle: Add 2 Arcane Bolts to your hand.
	deathrattle = Give(CONTROLLER, "RLK_843") * 2


class RLK_543:
	"""Magister's Apprentice"""

	# Your Arcane spells cost (1) less.
	update = Refresh(
		FRIENDLY_HAND + SPELL + ARCANE_SPELL, {GameTag.COST: -1}
	)


class RLK_545:
	"""Energy Shaper"""

	# Battlecry: Transform all spells in your hand into ones that cost
	# (2) more.
	play = _EnergyShaperMorphHand(CONTROLLER)


class RLK_547:
	"""Prismatic Elemental"""

	# Battlecry: Discover a spell from any class. It costs (1) less.
	play = DISCOVER(RandomSpell()).then(Buff(Give.CARD, "RLK_547e"))


class RLK_548:
	"""Arcane Wyrm"""

	# Battlecry: Add an Arcane Bolt to your hand.
	play = Give(CONTROLLER, "RLK_843")


class RLK_803:
	"""Grand Magister Rommath"""

	# Battlecry: Recast each spell you've cast this game that didn't
	# start in your deck.
	play = _RommathRecastNonStarting(CONTROLLER)


##
# Enchantments


@custom_card
class RLK_545e:
	# Not in data — marker enchant for Energy Shaper's morph effect.
	# The actual cost change comes from the morph itself (new card has
	# cost+2); the enchant exists so the engine has an attachment point
	# if downstream logic wants to inspect the source.
	tags = {
		GameTag.CARDNAME: "Energy Shaper",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_546e2:
	# Not in data — Vast Wisdom cost-swap delta. Cost is supplied via
	# Buff(..., cost_delta=N) kwarg at runtime; no static COST tag so the
	# kwarg can vary per pair of picked spells.
	tags = {
		GameTag.CARDNAME: "Infinite Wisdom",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
