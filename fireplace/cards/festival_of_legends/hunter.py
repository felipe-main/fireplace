from ..utils import *


##
# Custom actions / helpers


class _HarmonicaCastSecretCallback(TargetedAction):
	"""Harmonica Soloist — after DISCOVER gives a Secret to the player's
	hand, cast it immediately (engine handles routing it to the secrets
	zone). The Discover.CARD callback hands us the freshly-given card
	entity; CastSpell on it does the rest."""

	TARGET = ActionArg()
	CARD = ActionArg()

	def do(self, source, player, picked):
		# `picked` may arrive as a single Card or a single-item list,
		# depending on the wrapping action chain. Normalize to one card.
		if isinstance(picked, list):
			if not picked:
				return
			picked = picked[0]
		if picked is None:
			return
		from hearthstone.enums import Zone
		if picked.zone != Zone.HAND:
			return
		source.game.cheat_action(source, [CastSpell(picked)])


class _MisterMuklaFillBananas(TargetedAction):
	"""Mister Mukla — Battlecry: Fill your opponent's hand with Bananas
	(ETC_201). Loops Give(opponent, "ETC_201") until the hand is full."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = target
		while len(opp.hand) < opp.max_hand_size:
			source.game.cheat_action(source, [Give(opp, "ETC_201")])


class _BanjosaurDrawAndAbsorb(TargetedAction):
	"""Banjosaur — whenever this attacks, draw a Beast from the deck and
	gain its (atk, max_health) on top of Banjosaur's own. We compose:
	pick a random Beast from deck → draw it (so it lands in hand and
	the draw triggers fire) → buff Banjosaur by the drawn Beast's
	stats via a runtime-stamped enchant."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		beasts = [c for c in ctrl.deck if Race.BEAST in getattr(c, "races", [])]
		if not beasts:
			return
		pick = source.game.random.choice(beasts)
		atk = pick.atk or 0
		hp = pick.max_health or 0
		source.game.cheat_action(source, [ForceDraw(pick)])
		if atk == 0 and hp == 0:
			return
		source.game.cheat_action(
			source, [Buff(source, "ETC_840e", atk=atk, max_health=hp)]
		)


class _ThornmantleArmNextBeast(TargetedAction):
	"""Thornmantle Musician — Finale: arm a one-shot "next Beast summon
	gets +1/+1" flag on the controller. Consumed by Summon (engine
	hook reads `next_beast_summon_bonus`)."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.next_beast_summon_bonus = (
			getattr(target, "next_beast_summon_bonus", 0) + 1
		)


class _JungleJammerBumpSpellCounter(TargetedAction):
	"""Jungle Jammer — bump the per-weapon `_spells_cast_while_equipped`
	counter on every controller spell cast while the weapon is in play."""

	TARGET = ActionArg()

	def do(self, source, target):
		source._spells_cast_while_equipped = (
			getattr(source, "_spells_cast_while_equipped", 0) + 1
		)


class _JungleJammerDeathrattle(TargetedAction):
	"""Jungle Jammer — Deathrattle: Summon a random @-Cost Beast, where
	@ is the per-weapon spell-cast counter."""

	TARGET = ActionArg()

	def do(self, source, target):
		from .. import db
		n = getattr(source, "_spells_cast_while_equipped", 0)
		if n <= 0:
			return
		pool = [
			cid for cid, c in db.items()
			if c.collectible
			and c.type == CardType.MINION
			and c.race == Race.BEAST
			and (c.cost or 0) == n
		]
		if not pool:
			return
		cid = source.game.random.choice(pool)
		source.game.cheat_action(source, [Summon(target, cid)])


class _BigDreamsSummonDormantBeast(TargetedAction):
	"""Big Dreams — Summon the highest-cost Beast from your hand. It
	goes Dormant for 2 turns. We pick the top-cost Beast in hand,
	route through Summon (so on-summon triggers fire — Knife Juggler,
	Imp Master, etc.), then queue Dormant(2)."""

	TARGET = ActionArg()

	def do(self, source, target):
		beasts = [c for c in target.hand if Race.BEAST in getattr(c, "races", [])]
		if not beasts:
			return
		pick = max(beasts, key=lambda c: c.cost or 0)
		# Route through Summon(target, pick) — pick is the actual hand
		# entity; Summon transitions it to PLAY and fires the on-summon
		# broadcast (which the bare `pick.zone = Zone.PLAY` swap skipped).
		source.game.cheat_action(source, [Summon(target, pick)])
		# Only apply Dormant if the summon actually landed (e.g. board
		# wasn't full).
		from hearthstone.enums import Zone
		if pick.zone == Zone.PLAY:
			source.game.cheat_action(source, [Dormant(pick, 2)])


##
# Spells


class ETC_201e:
	# In-data buff "Banana" — +1/+1. ATK/HEALTH not parsed; declare.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class ETC_201:
	"""Bunch of Bananas"""

	# Give a minion +1/+1. (3 Bananas left!) After casting, add the
	# next variant (ETC_201t — "2 left") to your hand.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "ETC_201e"), Give(CONTROLLER, "ETC_201t")


class ETC_201t:
	"""Bunch of Bananas"""

	# Give a minion +1/+1. (2 Bananas left!) Adds ETC_201t2 (last).
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "ETC_201e"), Give(CONTROLLER, "ETC_201t2")


class ETC_201t2:
	"""Bunch of Bananas"""

	# Give a minion +1/+1. (Last Banana!) Chain ends here — no further
	# variants are added.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "ETC_201e")


class ETC_207:
	"""Barrel of Monkeys"""

	# Summon a 1/4 Monkey with Taunt. (3 Monkeys left!) Chain into
	# ETC_207t. The 1/4 Taunt Monkey isn't in data — we use our own
	# custom token ETC_207mt.
	play = Summon(CONTROLLER, "ETC_207mt"), Give(CONTROLLER, "ETC_207t")


class ETC_207t:
	"""Barrel of Monkeys"""

	# (2 Monkeys left!)
	play = Summon(CONTROLLER, "ETC_207mt"), Give(CONTROLLER, "ETC_207t2")


class ETC_207t2:
	"""Barrel of Monkeys"""

	# (Last Monkey!)
	play = Summon(CONTROLLER, "ETC_207mt")


@custom_card
class ETC_207mt:
	# Not in data — register the 1/4 Taunt Monkey token manually. The
	# spell text says "1/4 Monkey with Taunt" but no in-data minion
	# matches; this token is the implementation.
	tags = {
		GameTag.CARDNAME: "Monkey",
		GameTag.CARDTYPE: CardType.MINION,
		GameTag.ATK: 1,
		GameTag.HEALTH: 4,
		GameTag.TAUNT: True,
	}


class _StranglethornHeartResurrectAll(TargetedAction):
	"""Stranglethorn Heart — resurrect EVERY friendly Beast that died
	this game and cost (5) or more (not a single random pick).
	Iterates the controller's graveyard, deduplicating by entity, and
	summons a fresh copy of each qualifying beast."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		# graveyard preserves all dead entities (minions + spells +
		# weapons). Filter to MINION + BEAST + cost>=5.
		seen = set()
		to_summon = []
		for c in list(ctrl.graveyard):
			if c.type != CardType.MINION:
				continue
			if Race.BEAST not in getattr(c, "races", []):
				continue
			if (c.cost or 0) < 5:
				continue
			if id(c) in seen:
				continue
			seen.add(id(c))
			to_summon.append(c.id)
		for cid in to_summon:
			if len(ctrl.field) >= 7:
				break
			source.game.cheat_action(source, [Summon(ctrl, cid)])


class ETC_208:
	"""Stranglethorn Heart"""

	# Tradeable. Resurrect ALL friendly Beasts that cost (5) or more.
	# Tradeable is a data tag — engine handles.
	play = _StranglethornHeartResurrectAll(CONTROLLER)


class ETC_838:
	"""Big Dreams"""

	# Summon the highest-Cost Beast from your hand. It goes Dormant for
	# 2 turns.
	play = _BigDreamsSummonDormantBeast(CONTROLLER)


##
# Minions


class ETC_028:
	"""Harmonica Soloist"""

	# Battlecry: If you control no other minions, Discover and cast a
	# Secret. SELF is on the field at battlecry time so the field count
	# gate is exactly 1. DISCOVER opens a 3-secret pick and gives the
	# choice to hand; the callback casts it immediately. Inside the
	# Give().then() callback, the picked card is exposed as Give.CARD
	# (the just-given entity), so the cast targets that card.
	play = (Count(FRIENDLY_MINIONS) == 1) & Discover(
		CONTROLLER, RandomSpell(secret=True)
	).then(
		Give(CONTROLLER, Discover.CARD).then(
			_HarmonicaCastSecretCallback(CONTROLLER, Give.CARD),
		),
	)


class ETC_831:
	"""Thornmantle Musician"""

	# Finale: The next Beast you summon gets +1/+1. Arms a one-shot
	# `next_beast_summon_bonus` controller flag consumed by the engine's
	# Summon hook on the next Beast summoned.
	play = FINALE & _ThornmantleArmNextBeast(CONTROLLER)


class ETC_833:
	"""Arrow Smith"""

	# After you cast a spell, deal 1 damage to the lowest Health enemy.
	events = OWN_SPELL_PLAY.after(
		Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 1),
	)


class ETC_836:
	"""Mister Mukla"""

	# Rush. Battlecry: Fill your opponent's hand with Bananas (ETC_201).
	# RUSH in data. Loop Give until opponent's hand is full.
	play = _MisterMuklaFillBananas(OPPONENT)


class ETC_840:
	"""Banjosaur"""

	# Rush. Whenever this attacks, draw a Beast and gain its stats.
	events = Attack(SELF).on(_BanjosaurDrawAndAbsorb(SELF))


##
# Weapons


class ETC_832:
	"""Jungle Jammer"""

	# Deathrattle: Summon a random @-Cost Beast. (Cast spells while
	# equipped to improve!) Per-weapon counter bumped by an in-play
	# OWN_SPELL_PLAY listener.
	events = OWN_SPELL_PLAY.after(
		_JungleJammerBumpSpellCounter(SELF),
	)
	deathrattle = _JungleJammerDeathrattle(CONTROLLER)
