"""Showdown in the Badlands — Demonhunter cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions / helpers


class _SnakeEyesDiscover(TargetedAction):
	"""Snake Eyes — roll two dice (1-6 each) then Discover one card of each
	rolled Cost. Doubles grant an extra Discover of that Cost. We resolve
	the discovers one at a time via a re-entrant action: each Discover's
	`.then` re-invokes this action with the remaining cost list so the
	choices never stomp on each other (flat tuples of Discover all set
	player.choice at once and only the last survives — see CLAUDE.md)."""

	TARGET = ActionArg()

	def do(self, source, target):
		# First entry: roll the two dice and stash the work-list of Costs.
		costs = getattr(source, "_snake_eyes_costs", None)
		if costs is None:
			d1 = source.game.random.randint(1, 6)
			d2 = source.game.random.randint(1, 6)
			costs = [d1, d2]
			if d1 == d2:
				# Doubles: an extra Discover of the (shared) rolled Cost.
				costs.append(d1)
			source._snake_eyes_costs = costs

		if not costs:
			# Done — clean up so a re-played copy rolls fresh.
			source._snake_eyes_costs = None
			return

		cost = costs.pop(0)
		# Discover any card of exactly this Cost, then loop back in for the
		# next rolled Cost once this choice resolves.
		source.game.cheat_action(
			source,
			[
				Discover(target, RandomCard(cost=cost)).then(
					Give(target, Discover.CARD),
					_SnakeEyesDiscover(target),
				)
			],
		)


class _KurtrusShootHand(TargetedAction):
	"""Gunslinger Kurtrus — fire 6 random 2-damage shots at minions in the
	enemy's hand. Each shot re-picks a random minion card currently in the
	opponent's hand; a hand minion reduced to 0 health is removed via the
	standard death pipeline. Shots with no valid target fizzle."""

	TARGET = ActionArg()

	def do(self, source, target):
		opponent = source.controller.opponent
		for _ in range(6):
			pool = [
				c for c in opponent.hand
				if c.type == CardType.MINION and not c.dead
			]
			if not pool:
				break
			victim = source.game.random.choice(pool)
			source.game.cheat_action(source, [Hit(victim, 2)])
			source.game.process_deaths()


class _BartendSlideLeft(TargetedAction):
	"""Bartend-O-Bot — move the freshly-drawn Outcast card to the left-most
	slot of the controller's hand. The draw appends it to the end of the
	hand list; we pop it and re-insert at index 0."""

	TARGET = ActionArg()

	def do(self, source, target):
		if isinstance(target, list):
			target = target[0] if target else None
		if target is None:
			return
		hand = source.controller.hand
		if target in hand:
			hand.remove(target)
			hand.insert(0, target)


class _OasisDiscountIfNaga(TargetedAction):
	"""Oasis Outlaws — if a Naga was played while this card was held, reduce
	the discovered Naga's Cost by (1) via WW_404e."""

	TARGET = ActionArg()
	CARD = CardArg()

	def do(self, source, target, card):
		if isinstance(card, list):
			card = card[0] if card else None
		if card is None:
			return
		if getattr(source, "nagas_played_while_holding", 0) > 0:
			source.game.cheat_action(source, [Buff(card, "WW_404e")])


class _FanTheHammerShots(TargetedAction):
	"""Fan the Hammer — deal 6 damage split among the lowest-Health enemies.
	Fire six 1-damage shots; before each shot, re-pick the lowest-Health
	living enemy (processing deaths between shots so overkill spills onto the
	next-lowest target, matching the in-game behaviour). HS tiebreak for
	equal Health is play-order (earliest entity first)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		for _ in range(6):
			source.game.process_deaths()
			pool = [
				e for e in ([ctrl.opponent.hero] + list(ctrl.opponent.field))
				if e is not None and not e.dead
			]
			if not pool:
				break
			low = min(e.health for e in pool)
			candidates = [e for e in pool if e.health == low]
			victim = min(candidates, key=lambda e: getattr(e, "entity_id", 0))
			source.game.cheat_action(source, [Hit(victim, 1)])


class _LoadedConsume(TargetedAction):
	"""Load the Chamber — consume the "Loaded Fel Spell" discount enchant
	(TARGET) when a Fel spell is played, but ignore Load the Chamber's own
	play (the spell that created the enchant is itself a Fel spell, and its
	Play event fires right after the buff lands)."""

	TARGET = ActionArg()
	CARD = CardArg()

	def do(self, source, target, card):
		if isinstance(card, list):
			card = card[0] if card else None
		if card is not None and card.id == "WW_409":
			# The creating Load the Chamber play — don't consume.
			return
		if isinstance(target, list):
			for t in target:
				source.game.cheat_action(source, [Destroy(t)])
		else:
			source.game.cheat_action(source, [Destroy(target)])


def _blindeye_naga_fires(entities, source):
	"""Blindeye Sharpshooter — naga-mode gate. Fires when the minion's
	current mode is 'naga' (its starting mode), then flips to 'spell'."""
	if getattr(source, "_blindeye_mode", "naga") != "naga":
		return []
	source._blindeye_mode = "spell"
	return [source]


def _blindeye_spell_fires(entities, source):
	"""Blindeye Sharpshooter — spell-mode gate (mirror of the naga gate)."""
	if getattr(source, "_blindeye_mode", "naga") != "spell":
		return []
	source._blindeye_mode = "naga"
	return [source]


##
# Minions


class WW_400:
	"""Snake Eyes"""

	# Battlecry: Roll two dice, then Discover two cards of those Costs.
	# (Doubles get an extra Discover!)
	play = _SnakeEyesDiscover(CONTROLLER)


class WW_401:
	"""Gunslinger Kurtrus"""

	# Battlecry: If your deck has no duplicates, fire 6 random 2 damage
	# shots at minions in the enemy's hand.
	play = (-FindDuplicates(FRIENDLY_DECK)) & _KurtrusShootHand(CONTROLLER)


class WW_402:
	"""Blindeye Sharpshooter"""

	# After you play a Naga, deal 2 damage to a random enemy and draw a
	# spell. (Then switch!)
	# After you cast a spell, deal 2 damage to a random enemy and draw a
	# Naga. (Then switch!)
	# Starts in "naga" mode — a Naga play fires the naga half and flips to
	# "spell"; the next spell cast fires the spell half and flips back.
	events = [
		Play(CONTROLLER, MINION + NAGA).after(
			Find(FuncSelector(_blindeye_naga_fires))
			& (
				Hit(RANDOM_ENEMY_CHARACTER, 2),
				Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)),
			)
		),
		OWN_SPELL_PLAY.after(
			Find(FuncSelector(_blindeye_spell_fires))
			& (
				Hit(RANDOM_ENEMY_CHARACTER, 2),
				Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + NAGA)),
			)
		),
	]


class WW_406:
	"""Midnight Wolf"""

	# Rush. Outcast: Summon a copy of this.
	# RUSH lives in data. Outcast replaces play in Play.do when the card is
	# the left- or right-most card in hand.
	outcast = Summon(CONTROLLER, ExactCopy(SELF))


class WW_407:
	"""Parched Desperado"""

	# Battlecry: If you've cast a spell while holding this, give your hero
	# +3 Attack this turn.
	play = (Attr(SELF, "spells_cast_while_holding") > 0) & Buff(
		FRIENDLY_HERO, "WW_407e"
	)


class WW_407e:
	# In-data "*GULP*" — +3 Attack this turn. TAG_ONE_TURN_EFFECT lives in
	# data (auto-clears at end of turn); the ATK value isn't parsed, so
	# declare it here.
	tags = {GameTag.ATK: 3}


class WW_408:
	"""Bartend-O-Bot"""

	# Battlecry: Draw an Outcast card and slide it to the left side of your
	# hand. ForceDraw against the deck's Outcast pool, then reposition the
	# freshly-drawn card to the left-most hand slot.
	play = ForceDraw(RANDOM(FRIENDLY_DECK + OUTCAST)).then(
		_BartendSlideLeft(ForceDraw.TARGET)
	)


##
# Spells


class WW_403:
	"""Pocket Sand"""

	# Deal $3 damage. Quickdraw: Your opponent's next card costs (1) more.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 3),
		QUICKDRAW & Buff(OPPONENT, "WW_403e"),
	)


class WW_403e:
	# In-data "Sand In Your Eyes" — Your opponent's next card costs (1) more.
	# Attached to OPPONENT via Buff, but the enchant's controller is the
	# caster, so ENEMY_HAND resolves to the opponent's hand (the same trick
	# Boompistol Bully / YOD_033e uses). Destroyed once the opponent plays
	# their next card.
	update = Refresh(ENEMY_HAND, {GameTag.COST: 1})
	events = Play(OPPONENT).after(Destroy(SELF))


class WW_404:
	"""Oasis Outlaws"""

	# Discover a Naga. If you've played a Naga while holding this, reduce its
	# Cost by (1). The DISCOVER gives the chosen Naga; the discount stamp is
	# applied (conditionally) to the freshly-given card.
	play = Discover(CONTROLLER, RandomMinion(race=Race.NAGA)).then(
		Give(CONTROLLER, Discover.CARD),
		_OasisDiscountIfNaga(CONTROLLER, Give.CARD),
	)


@custom_card
class WW_404e:
	# Not in data — (1)-cost discount stamp for the discovered Naga.
	tags = {
		GameTag.CARDNAME: "Oasis Outlaws",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -1,
	}


class WW_405:
	"""Fan the Hammer"""

	# Deal $6 damage split among the lowest Health enemies. Six individual
	# 1-damage shots, each re-evaluating the current lowest-Health enemy
	# (deaths processed between shots so overkill spills to the next-lowest).
	play = _FanTheHammerShots(CONTROLLER)


class WW_409:
	"""Load the Chamber"""

	# Deal $2 damage. Your next Naga, Fel spell, and weapon cost (1) less.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 2),
		Buff(CONTROLLER, "WW_409e"),
		Buff(CONTROLLER, "WW_409e2"),
		Buff(CONTROLLER, "WW_409e3"),
	)


class WW_409e:
	# In-data "Loaded Naga" — your next Naga costs (1) less. Reduce in-hand
	# Nagas by 1 while live; destroy the enchant after the next Naga is
	# played.
	update = Refresh(FRIENDLY_HAND + NAGA, {GameTag.COST: -1})
	events = Play(CONTROLLER, MINION + NAGA).after(Destroy(SELF))


class WW_409e2:
	# In-data "Loaded Fel Spell" — your next Fel spell costs (1) less.
	# Load the Chamber is itself a Fel spell, so its own Play event must NOT
	# consume the discount — we destroy the enchant only when a *different*
	# Fel spell is played (PlayWasNotSource gate).
	update = Refresh(FRIENDLY_HAND + SPELL + FEL, {GameTag.COST: -1})
	events = Play(CONTROLLER, SPELL + FEL).after(
		_LoadedConsume(SELF, Play.CARD)
	)


class WW_409e3:
	# In-data "Loaded Weapon" — your next weapon costs (1) less.
	update = Refresh(FRIENDLY_HAND + WEAPON, {GameTag.COST: -1})
	events = Play(CONTROLLER, WEAPON).after(Destroy(SELF))
