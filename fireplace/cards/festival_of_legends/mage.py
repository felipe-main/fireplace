from ..utils import *


##
# Custom actions


class _VolumeUpDrawAndRecord(TargetedAction):
	"""Volume Up — draw 3 spells from the controller's deck, remembering
	which exact cards landed in hand. The Finale Discover branch (see
	_VolumeUpFinaleDiscover) reuses that snapshot so the player picks
	one of *the three drawn*, not just any three random spells.

	We snapshot the deck-tail spells before pulling them (Draw works on
	the picked card), then dispatch a Draw for each so all on-draw
	triggers fire normally.
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		drawn = []
		for _ in range(3):
			candidates = [c for c in list(ctrl.deck) if c.type == CardType.SPELL]
			if not candidates:
				break
			pick = source.game.random.choice(candidates)
			drawn.append(pick)
			source.game.cheat_action(source, [Draw(ctrl, pick)])
		source._volume_up_drawn = drawn


class _VolumeUpFinaleDiscover(TargetedAction):
	"""Volume Up — Finale half: open a Discover over the (up to 3) spells
	just drawn by _VolumeUpDrawAndRecord. The chosen card's id is given
	back to the controller's hand as a fresh copy."""

	TARGET = ActionArg()

	def do(self, source, target):
		if not getattr(source, "play_finale", False):
			return
		drawn = getattr(source, "_volume_up_drawn", [])
		ids = [c.id for c in drawn if c is not None]
		if not ids:
			return
		source.game.cheat_action(
			source,
			[Discover(target, RandomID(*ids)).then(Give(target, Discover.CARD))],
		)


class _InfinitizeReturnAtEndOfTurn(TargetedAction):
	"""Infinitize the Maxitude — Finale clause: at end of turn, add a
	fresh copy of Infinitize the Maxitude back to the controller's hand.
	Schedules a one-shot OWN_TURN_END listener via the controller flag."""

	TARGET = ActionArg()

	def do(self, source, target):
		if not getattr(source, "play_finale", False):
			return
		target._infinitize_pending = getattr(
			target, "_infinitize_pending", 0
		) + 1


class _CosmicKeyboardSpawn(TargetedAction):
	"""Cosmic Keyboard — after the controller casts a spell, summon
	a generic Elemental forced to literal N/N stats where N = the
	spell's printed cost. Uses SummonCustomMinion to overwrite the
	chassis card's stats so the printed "stats equal to its Cost"
	text reads exactly N/N regardless of the source minion's data."""

	TARGET = ActionArg()
	SPELL = ActionArg()

	def do(self, source, target, spell):
		if isinstance(spell, list):
			spell = spell[0] if spell else None
		if spell is None:
			return
		cost = spell.cost or 0
		if cost <= 0:
			return
		from ... import cards as _cards
		# Pick any collectible Elemental chassis at any cost (its printed
		# stats are about to be overwritten). Iterate the db directly so
		# the race comparison is exact (db.filter loosely matches multi-
		# race minions and would let a Mech like Steel Rager slip in).
		pool = [
			cid for cid, c in _cards.db.items()
			if c.collectible
			and c.type == CardType.MINION
			and int(getattr(c, "race", 0) or 0) == int(Race.ELEMENTAL)
		]
		if not pool:
			return
		picked_id = source.game.random.choice(pool)
		# SummonCustomMinion expects a card entity (it sets per-instance
		# atk/max_health/cost on the entity). Materialise the picked id.
		card_entity = target.card(picked_id)
		source.game.cheat_action(
			source,
			[SummonCustomMinion(target, card_entity, cost, cost, cost)],
		)


class _LightshowHits(TargetedAction):
	"""Lightshow — fire (2 + lightshows_cast_this_game-prior) bolts of 2
	damage at random enemy characters. Counter is read *before* this cast
	bumps it so the first cast fires exactly 2 bolts."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		prior = getattr(ctrl, "lightshows_cast_this_game", 0)
		bolts = 2 + prior
		ctrl.lightshows_cast_this_game = prior + 1
		for _ in range(bolts):
			source.game.cheat_action(
				source, [Hit(RANDOM(ENEMY_CHARACTERS), 2)]
			)


class _RewindDiscoverCast(TargetedAction):
	"""Rewind — open a Discover over up to 3 random spells the controller
	has cast this game (excluding Rewind itself). If <3 candidates, just
	open the full list."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		pool = [
			c.id
			for c in list(ctrl.cards_played_this_game)
			if c.type == CardType.SPELL and c.id != source.id
		]
		if not pool:
			return
		# De-dup so the same spell doesn't appear thrice.
		uniq = list(dict.fromkeys(pool))
		source.game.cheat_action(
			source,
			[Discover(target, RandomID(*uniq)).then(Give(target, Discover.CARD))],
		)


class _SynthesizeAddElementals(TargetedAction):
	"""Synthesize — add a random 1, 2, and 3-cost Elemental to hand."""

	TARGET = ActionArg()

	def do(self, source, target):
		from ... import cards as _cards
		for cost in (1, 2, 3):
			pool = _cards.db.filter(
				collectible=True,
				type=CardType.MINION,
				race=Race.ELEMENTAL,
				cost=cost,
			)
			if not pool:
				continue
			picked = source.game.random.choice(pool)
			source.game.cheat_action(source, [Give(target, picked)])


class _AudioSplitterCopyMaxCost(TargetedAction):
	"""Audio Splitter deathrattle — copy the highest-cost spell in the
	controller's hand. Ties: pick the first such spell (left to right) so
	the result is deterministic."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		spells = [c for c in list(ctrl.hand) if c.type == CardType.SPELL]
		if not spells:
			return
		max_cost = max((s.cost or 0) for s in spells)
		picked = next(s for s in spells if (s.cost or 0) == max_cost)
		source.game.cheat_action(source, [Give(ctrl, picked.id)])


##
# Spells


class ETC_205:
	"""Volume Up"""

	# Draw 3 spells. Finale: Discover a copy of one.
	play = (
		_VolumeUpDrawAndRecord(CONTROLLER),
		_VolumeUpFinaleDiscover(CONTROLLER),
	)


class ETC_206:
	"""Infinitize the Maxitude"""

	# Discover a spell. Finale: Return this to your hand at end of turn.
	# Approximation: a finale marker enchant on the controller re-adds
	# ETC_206 to hand at the next OWN_TURN_END and self-destructs.
	play = (
		FINALE & Buff(CONTROLLER, "ETC_206e_marker"),
		DISCOVER(RandomSpell()),
	)


@custom_card
class ETC_206e_marker:
	"""Infinitize the Maxitude"""

	# Finale return marker. Stamped on the controller when a Finale
	# Infinitize resolves. At end of turn the marker re-adds Infinitize
	# to hand and self-destructs.
	tags = {
		GameTag.CARDNAME: "Infinitize the Maxitude",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = OWN_TURN_END.on(Give(CONTROLLER, "ETC_206"), Destroy(SELF))


class ETC_528:
	"""Lightshow"""

	# Shoot two beams at enemies that deal $2 damage. Shoot one more for
	# each Lightshow cast this game.
	play = _LightshowHits(CONTROLLER)


class ETC_532:
	"""Rewind"""

	# Discover a copy of another spell you've cast this game.
	play = _RewindDiscoverCast(CONTROLLER)


class ETC_535:
	"""Synthesize"""

	# Add a random 1, 2, and 3-Cost Elemental to your hand.
	play = _SynthesizeAddElementals(CONTROLLER)


##
# Minions


class ETC_029:
	"""Keyboard Soloist"""

	# Battlecry: If you control no other minions, summon two 1/2 Amps
	# with Spell Damage +1.
	# Count check is against "other friendly minions" — Soloist is
	# already in play when the battlecry resolves, so we test == 1.
	play = (Count(FRIENDLY_MINIONS) == 1) & (
		Summon(CONTROLLER, "ETC_029t") * 2
	)


class ETC_029t:
	"""Keyboard Amplifier"""


class ETC_395:
	"""DJ Manastorm"""

	# Battlecry: Set the Cost of spells in your hand to (0). After you
	# cast one, the others cost (1) more.
	# We stamp a -100 cost buff on every spell currently in hand (engine
	# clamps the effective cost to 0). After each spell cast this turn,
	# bump the others' cost by +1 via a per-card enchant.
	play = Buff(FRIENDLY_HAND + SPELL, "ETC_395e")
	events = Play(CONTROLLER, SPELL).after(
		Buff(FRIENDLY_HAND + SPELL, "ETC_395e2")
	)


@custom_card
class ETC_395e:
	# Sets cost to (effectively) 0. -100 is clamped at 0 by pay_cost.
	tags = {
		GameTag.CARDNAME: "DJ Manastorm",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -100,
	}


@custom_card
class ETC_395e2:
	# After-cast +1 cost stack. Each cast adds one of these to every
	# remaining spell in hand, so the next spell costs (prior_stack + 1).
	tags = {
		GameTag.CARDNAME: "DJ Manastorm",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: 1,
	}


class ETC_534:
	"""Holotechnician"""

	# After ANY minion takes exactly 1 damage, destroy it.
	# Gate on Damage.AMOUNT == 1; works on any minion (friend or foe,
	# including SELF).
	events = Damage(MINION).after(
		(Damage.AMOUNT == 1) & Destroy(Damage.TARGET)
	)


class ETC_536:
	"""Audio Splitter"""

	# Deathrattle: Copy the highest Cost spell in your hand.
	deathrattle = _AudioSplitterCopyMaxCost(SELF)


##
# Weapons


class ETC_521:
	"""Cosmic Keyboard"""

	# After you cast a spell, summon an Elemental with stats equal to its
	# Cost. Lose 1 Durability.
	# Note: a literal "N/N Elemental" doesn't exist for every cost, so we
	# approximate by summoning a random collectible Elemental of matching
	# cost (its printed stats stand in for "N/N"). Lose-1-durability is
	# the standard weapon-trigger pattern: Hit(SELF, 1).
	events = Play(CONTROLLER, SPELL).after(
		_CosmicKeyboardSpawn(CONTROLLER, Play.CARD),
		Hit(SELF, 1),
	)
