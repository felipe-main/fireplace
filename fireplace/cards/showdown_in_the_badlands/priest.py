"""Showdown in the Badlands — Priest cards (WILD_WEST)."""

from ..utils import *


##
# Custom LazyNums


class _OneCostCardsPlayed(LazyNum):
	"""Counts how many 1-Cost cards the controller has played this game.
	Reads the printed (base) cost from each played card's data so the
	count never re-enters the cost-evaluation pipeline (which would
	recurse through Thirsty Drifter's own cost_mod)."""

	def evaluate(self, source):
		ctrl = source.controller
		count = sum(
			1 for c in ctrl.cards_played_this_game if c.data.cost == 1
		)
		return self.num(count)


##
# Custom actions


class _BottleStore(TargetedAction):
	"""Create a "1-Cost Bottle" token, stamp the saved excess amount on
	it, and add it to the controller's hand. The bottle's own play reads
	the stamped `_bottle_amount`. Shared by every "Save any excess in a
	1-Cost Bottle" card. TARGET is the controller; the excess amount is
	passed via the constructor."""

	TARGET = ActionArg()

	def get_target_args(self, source, target):
		bottle_id = self._args[1]
		amount = self._args[2]
		if isinstance(amount, LazyValue):
			amount = amount.evaluate(source)
		if hasattr(amount, "__iter__"):
			amount = amount[0] if amount else 0
		return [bottle_id, int(amount)]

	def do(self, source, target, bottle_id, amount):
		if amount <= 0:
			return
		bottle = target.card(bottle_id, source=source)
		bottle._bottle_amount = amount
		source.game.cheat_action(source, [Give(target, bottle)])


class _SwarmOfLightbugs(TargetedAction):
	"""Swarm of Lightbugs (WW_052) — summon up to 10 Lightbugs (WW_052t,
	1/1 Lifesteal). The board caps at 7, so summon as many as fit and
	save the remainder in a Bottled Lightbugs token (WW_052t2)."""

	TARGET = ActionArg()

	def do(self, source, target):
		free = 7 - len(target.field)
		to_summon = min(10, max(0, free))
		excess = 10 - to_summon
		for _ in range(to_summon):
			source.game.cheat_action(source, [Summon(target, "WW_052t")])
		if excess > 0:
			source.game.cheat_action(
				source, [_BottleStore(target, "WW_052t2", excess)]
			)


class _BottledLightbugs(TargetedAction):
	"""Bottled Lightbugs (WW_052t2) — summon the saved number of 1/1
	Lifesteal Lightbugs, again clamped to the board cap."""

	TARGET = ActionArg()

	def do(self, source, target):
		amount = getattr(source, "_bottle_amount", 0)
		free = 7 - len(target.field)
		for _ in range(min(amount, max(0, free))):
			source.game.cheat_action(source, [Summon(target, "WW_052t")])


class _ShadeleafHit(TargetedAction):
	"""Invasive Shadeleaf (WW_393) — deal 8 to an enemy minion; the
	overkill (damage beyond the minion's current Health) is saved in a
	Bottled Shadeleaf (WW_393t). The spell is immune to Spell Damage, so
	the amount is a flat 8."""

	TARGET = ActionArg()

	def do(self, source, target):
		excess = max(0, 8 - target.health)
		source.game.cheat_action(source, [Hit(target, 8)])
		if excess > 0:
			source.game.cheat_action(
				source, [_BottleStore(source.controller, "WW_393t", excess)]
			)


class _BottledShadeleaf(TargetedAction):
	"""Bottled Shadeleaf (WW_393t) — deal the saved excess damage to an
	enemy minion."""

	TARGET = ActionArg()

	def do(self, source, target):
		amount = getattr(source, "_bottle_amount", 0)
		if amount > 0:
			source.game.cheat_action(source, [Hit(target, amount)])


class _SpringwaterHeal(TargetedAction):
	"""Holy Springwater (WW_395) — restore 8 Health to a damaged
	character; the overheal is saved in a Bottled Springwater
	(WW_395t)."""

	TARGET = ActionArg()

	def do(self, source, target):
		source.game.cheat_action(source, [Heal(target, 8)])
		excess = getattr(target, "_last_heal_overheal", 0)
		if excess > 0:
			source.game.cheat_action(
				source, [_BottleStore(source.controller, "WW_395t", excess)]
			)


class _BottledSpringwater(TargetedAction):
	"""Bottled Springwater (WW_395t) — restore the saved excess Health to
	a damaged character."""

	TARGET = ActionArg()

	def do(self, source, target):
		amount = getattr(source, "_bottle_amount", 0)
		if amount > 0:
			source.game.cheat_action(source, [Heal(target, amount)])


class _EliseSummonCopies(TargetedAction):
	"""Elise, Badlands Savior (WW_392) — if the controller's deck has no
	duplicate cards, summon 4/4 copies of 4 random minions in the deck."""

	TARGET = ActionArg()

	def do(self, source, target):
		deck = list(target.deck)
		ids = [c.id for c in deck]
		if len(ids) != len(set(ids)):
			return
		minions = [c for c in deck if c.type == CardType.MINION]
		if not minions:
			return
		source.game.random.shuffle(minions)
		for minion in minions[:4]:
			copy = target.card(minion.id, source=source)
			source.game.cheat_action(
				source,
				[Summon(target, copy).then(Buff(copy, "WW_392e"))],
			)


class _PipCopyOneCost(TargetedAction):
	"""Pip the Potent (WW_394) — copy each 1-Cost card in the
	controller's hand. Snapshot the hand first so the freshly-added
	copies aren't themselves re-copied."""

	TARGET = ActionArg()

	def do(self, source, target):
		originals = [c for c in list(target.hand) if c.cost == 1]
		for card in originals:
			copy = target.card(card.id, source=source)
			source.game.cheat_action(source, [Give(target, copy)])


class _BankerFriendlyDiscover(TargetedAction):
	"""Benevolent Banker (WW_384) non-Quickdraw branch — Discover a spell
	from your OWN deck. Scope a RandomID picker to the spell-ids currently
	in the controller's deck and feed it through the standard deck-Discover
	mechanism (DISCOVER copies the chosen card to hand; the deck keeps its
	originals). Mirrors Flowrider (ETC_359)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		ids = [c.id for c in ctrl.deck if c.type == CardType.SPELL]
		if not ids:
			return
		source.game.cheat_action(source, [DISCOVER(RandomID(*ids))])


class _BankerEnemyDiscover(TargetedAction):
	"""Benevolent Banker (WW_384) Quickdraw branch — Discover a spell from
	the OPPONENT's deck. Discovering from an enemy deck yields a copy you
	own (the opponent keeps their card), so offer up-to-3 distinct copies
	of random enemy-deck spells via a GenericChoice."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		spells = [c for c in opp.deck if c.type == CardType.SPELL]
		# De-duplicate by id, then pick up to three at random.
		seen = {}
		for c in spells:
			seen.setdefault(c.id, c)
		pool = list(seen.values())
		source.game.random.shuffle(pool)
		pool = pool[:3]
		if not pool:
			return
		copies = [source.controller.card(c.id, source=source) for c in pool]
		source.game.cheat_action(
			source, [GenericChoice(source.controller, copies)]
		)


class _InjuredHaulerOverheal(TargetedAction):
	"""Injured Hauler (WW_381) — Overheal: deal 2 damage to all enemy
	minions. Fires only when a heal of SELF actually overhealed (reads
	`_last_heal_overheal` stamped on SELF by Heal.do)."""

	TARGET = ActionArg()

	def do(self, source, target):
		if getattr(target, "_last_heal_overheal", 0) > 0:
			source.game.cheat_action(source, [Hit(ENEMY_MINIONS, 2)])


class _PossePossession(TargetedAction):
	"""Posse Possession (WW_600) — summon a 4/4 copy of a random minion
	in the opponent's hand."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		minions = [c for c in opp.hand if c.type == CardType.MINION]
		if not minions:
			return
		picked = source.game.random.choice(minions)
		copy = source.controller.card(picked.id, source=source)
		source.game.cheat_action(
			source,
			[Summon(source.controller, copy).then(Buff(copy, "WW_600e"))],
		)


##
# Spells


class WW_052:
	"""Swarm of Lightbugs"""

	# Summon 10 1/1 Lightbugs with Lifesteal. Save any excess in a
	# 1-Cost Bottle.
	play = _SwarmOfLightbugs(CONTROLLER)


class WW_053:
	"""Tram Heist"""

	# Get a copy of each card your opponent played last turn.
	play = Give(CONTROLLER, Copy(CARDS_OPPONENT_PLAYED_LAST_TURN))


class WW_393:
	"""Invasive Shadeleaf"""

	# Deal $8 damage to an enemy minion. Save any excess in a 1-Cost
	# Bottle.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
	}
	play = _ShadeleafHit(TARGET)


class WW_395:
	"""Holy Springwater"""

	# Restore #8 Health to a damaged character. Save any excess in a
	# 1-Cost Bottle.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_DAMAGED_TARGET: 0,
	}
	play = _SpringwaterHeal(TARGET)


class WW_600:
	"""Posse Possession"""

	# Summon a 4/4 copy of a random minion in your opponent's hand.
	play = _PossePossession(CONTROLLER)


##
# Minions


class WW_381:
	"""Injured Hauler"""

	# Battlecry: Deal 4 damage to this minion. Overheal: Deal 2 damage to
	# all enemy minions.
	# The battlecry self-hit leaves it damaged; the Overheal half lives
	# on a permanent self-listener that watches Heals of SELF (same shape
	# as Festival's Heartbreaker Hedanis).
	play = Hit(SELF, 4)
	events = Heal(SELF).on(_InjuredHaulerOverheal(SELF))


class WW_384:
	"""Benevolent Banker"""

	# Battlecry: Discover a spell from your deck. Quickdraw: Enemy deck
	# instead.
	play = (
		QUICKDRAW
		& _BankerEnemyDiscover(CONTROLLER)
		| _BankerFriendlyDiscover(CONTROLLER)
	)


class WW_387:
	"""Thirsty Drifter"""

	# Taunt. Costs (1) less for each 1-Cost card you've played this game.
	cost_mod = -_OneCostCardsPlayed()


class WW_392:
	"""Elise, Badlands Savior"""

	# Battlecry: If your deck has no duplicates, summon 4/4 copies of 4
	# random minions in your deck.
	play = _EliseSummonCopies(CONTROLLER)


class WW_394:
	"""Pip the Potent"""

	# Battlecry: Copy each 1-Cost card in your hand.
	play = _PipCopyOneCost(CONTROLLER)


##
# Tokens & enchantments


class WW_052t2:
	"""Bottled Lightbugs"""

	# Summon the excess 1/1 Lightbugs with Lifesteal.
	play = _BottledLightbugs(CONTROLLER)

	def custom_cardtext(self):
		segments = self.data.description.split("@")
		if len(segments) < 2:
			return self.data.description
		return segments[1].replace("{0}", str(getattr(self, "_bottle_amount", 0)))

	def cardtext_entity_0(self):
		return getattr(self, "_bottle_amount", 0)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class WW_393t:
	"""Bottled Shadeleaf"""

	# Deal the excess damage to an enemy minion.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
	}
	play = _BottledShadeleaf(TARGET)

	def custom_cardtext(self):
		segments = self.data.description.split("@")
		if len(segments) < 2:
			return self.data.description
		return segments[1].replace("{0}", str(getattr(self, "_bottle_amount", 0)))

	def cardtext_entity_0(self):
		return getattr(self, "_bottle_amount", 0)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class WW_395t:
	"""Bottled Springwater"""

	# Restore the excess Health to a damaged character.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_DAMAGED_TARGET: 0,
	}
	play = _BottledSpringwater(TARGET)

	def custom_cardtext(self):
		segments = self.data.description.split("@")
		if len(segments) < 2:
			return self.data.description
		return segments[1].replace("{0}", str(getattr(self, "_bottle_amount", 0)))

	def cardtext_entity_0(self):
		return getattr(self, "_bottle_amount", 0)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class WW_392e:
	# 4/4.
	atk = SET(4)
	max_health = SET(4)


class WW_600e:
	# 4/4.
	atk = SET(4)
	max_health = SET(4)
