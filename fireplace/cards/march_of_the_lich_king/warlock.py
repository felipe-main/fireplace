from ..utils import *


##
# Custom actions


class _ScourgeSuppliesDiscardChoice(TargetedAction):
	"""Scourge Supplies — draw 3 cards, then open a Choice over those 3
	cards. The picked card is discarded. Implemented as a custom action
	because the printed effect needs to scope the choice to *exactly*
	the freshly-drawn cards (not the whole hand)."""

	TARGET = ActionArg()

	def do(self, source, target):
		drawn = []
		for _ in range(3):
			pre = list(target.hand)
			source.game.cheat_action(source, [Draw(target)])
			new = [c for c in target.hand if c not in pre]
			if new:
				drawn.extend(new)
		drawn = [c for c in drawn if c in target.hand]
		if not drawn:
			return
		choice = Choice(target, drawn).then(
			_ScourgeSuppliesDoDiscard(Choice.PLAYER, Choice.CARDS, Choice.CARD)
		)
		source.game.queue_actions(source, [choice])


class _ScourgeSuppliesDoDiscard(TargetedAction):
	"""Choose-callback: discard the picked card."""

	PLAYER = ActionArg()
	CARDS = ActionArg()
	CARD = ActionArg()

	def do(self, source, player, cards, picked):
		if isinstance(picked, list):
			if not picked:
				return
			picked = picked[0]
		source.game.cheat_action(source, [Discard(picked)])


class _TwistedTetherTransfer(TargetedAction):
	"""Twisted Tether — snapshot the chosen minion's atk/health, pick a
	random Undead in the controller's hand, buff it with those stats,
	then destroy the original. If no Undead is in hand the destroy still
	resolves (matches printed behaviour: stats simply have no recipient)."""

	TARGET = ActionArg()

	def do(self, source, target):
		atk = target.atk
		hp = target.health
		ctrl = source.controller
		pool = UNDEAD.eval(ctrl.hand, source)
		if pool:
			recipient = source.game.random.choice(pool)
			source.game.cheat_action(
				source,
				[Buff(recipient, "RLK_537e", atk=atk, max_health=hp)],
			)
		source.game.cheat_action(source, [Destroy(target)])


class _DevourerGainDeathrattle(TargetedAction):
	"""Devourer of Souls — when a friendly minion (not SELF) dies, copy
	its deathrattle scripts onto SELF via additional_deathrattles so they
	fire when SELF dies."""

	TARGET = ActionArg()
	ENTITY = ActionArg()

	def do(self, source, target, entity):
		if isinstance(entity, list):
			if not entity:
				return
			entity = entity[0]
		if entity is source:
			return
		drs = list(entity.data.scripts.deathrattle or ())
		if not drs:
			return
		# additional_deathrattles is a list of action-iterables; each entry
		# must itself be a tuple/list so Deathrattle can queue_actions on it.
		source.additional_deathrattles.append(tuple(drs))
		source.has_deathrattle = True


class _AmorphousSlimeDiscardSnapshot(TargetedAction):
	"""Amorphous Slime — discard a random Undead from the controller's
	hand and stash its id on SELF so the deathrattle can summon a copy.
	If no Undead is in hand, no discard happens and the deathrattle has
	nothing to summon (matches printed behaviour)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		pool = UNDEAD.eval(ctrl.hand, source)
		if not pool:
			return
		picked = source.game.random.choice(pool)
		source._amorphous_discarded_id = picked.id
		source.game.cheat_action(source, [Discard(picked)])


class _AmorphousSlimeDeathrattle(TargetedAction):
	"""Amorphous Slime deathrattle — summon a copy of the Undead that
	was discarded by the battlecry (id stashed on SELF)."""

	TARGET = ActionArg()

	def do(self, source, target):
		cid = getattr(source, "_amorphous_discarded_id", None)
		if not cid:
			return
		source.game.cheat_action(source, [Summon(source.controller, cid)])


##
# Minions


class RLK_531:
	"""Infantry Reanimator"""

	# Battlecry: Resurrect a friendly Undead. Give it Reborn.
	play = Summon(
		CONTROLLER,
		Copy(RANDOM(FRIENDLY + KILLED + MINION + UNDEAD)),
	).then(GiveReborn(Summon.CARD))


class RLK_532:
	"""Walking Dead"""

	# Taunt. If you discard this minion, summon it.
	# Engine pipes the dying-in-hand discard through
	# `card.get_actions("discard")`, so a bare `discard = ...` script on
	# the card is sufficient.
	discard = Summon(CONTROLLER, "RLK_532")


class RLK_535:
	"""Savage Ymirjar"""

	# Rush. Battlecry: Discard 2 cards.
	play = Discard(RANDOM(FRIENDLY_HAND)) * 2


class RLK_538:
	"""Devourer of Souls"""

	# After a friendly minion dies, gain its Deathrattle.
	# FRIENDLY + MINION (without IN_PLAY) lets the selector still match
	# the dying minion which has already moved to GRAVEYARD by AFTER-time.
	events = Death(FRIENDLY + MINION - SELF).on(
		_DevourerGainDeathrattle(SELF, Death.ENTITY)
	)


class RLK_539:
	"""Dar'Khan Drathir"""

	# Lifesteal. At the end of your turn, deal 6 damage to the enemy hero.
	# LIFESTEAL is set in data; we only need the end-of-turn trigger.
	events = OWN_TURN_END.on(Hit(ENEMY_HERO, 6))


class RLK_540:
	"""Amorphous Slime"""

	# Battlecry: Discard a random Undead. Deathrattle: Summon a copy of it.
	play = _AmorphousSlimeDiscardSnapshot(SELF)
	deathrattle = _AmorphousSlimeDeathrattle(SELF)


##
# Spells


class RLK_533:
	"""Scourge Supplies"""

	# Draw 3 cards. Choose one to discard.
	play = _ScourgeSuppliesDiscardChoice(CONTROLLER)


class RLK_534:
	"""Soul Barrage"""

	# When you play or discard this, deal $6 damage randomly split among
	# all enemies.  The discard branch fires while Soul Barrage is in
	# hand, so the listener lives on Hand.events; the play branch is the
	# usual cast effect.
	play = Hit(RANDOM_ENEMY_CHARACTER, 1) * SPELL_DAMAGE(6)

	class Hand:
		events = Discard(SELF).on(Hit(RANDOM_ENEMY_CHARACTER, 1) * 6)


class RLK_536:
	"""Shallow Grave"""

	# Trigger a friendly minion's Deathrattle, then destroy it.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_TARGET_WITH_DEATHRATTLE: 0,
	}
	play = Deathrattle(TARGET), Destroy(TARGET)


class RLK_537:
	"""Twisted Tether"""

	# Destroy a minion. Give its stats to a random Undead in your hand.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _TwistedTetherTransfer(TARGET)


##
# Enchantments


class RLK_537e:
	# In-data buff "Twisted Tether — Increased stats". The ATK / HEALTH
	# values are supplied via Buff(..., atk=, max_health=) kwargs at
	# runtime (mirrors REV_248k / Castle Nathria's Priest pattern), so
	# no static stat tags here.
	tags = {}
