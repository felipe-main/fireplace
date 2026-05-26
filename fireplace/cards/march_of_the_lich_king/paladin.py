from ..utils import *


##
# Custom actions


class _TimewardenTick(TargetedAction):
	"""Decrement the Timewarden counter on the controller. The aura
	auto-stops firing once it reaches zero (the event listener gate
	reads the counter)."""

	TARGET = ActionArg()

	def do(self, source, target):
		left = getattr(target, "_timewarden_turns_left", 0) - 1
		target._timewarden_turns_left = max(0, left)


class _TimewardenStartAura(TargetedAction):
	"""Timewarden — flip a controller flag that lasts until the end of
	the controller's NEXT turn. Tracked as `_timewarden_turns_left = 2`
	(decremented at each OWN_TURN_END), so it covers the rest of this
	turn + all of next turn. The aura logic itself lives on the
	Timewarden minion's `events` (see RLK_527 below)."""

	TARGET = ActionArg()

	def do(self, source, target):
		target._timewarden_turns_left = (
			getattr(target, "_timewarden_turns_left", 0) + 2
		)


class _AnachronosTimeJump(TargetedAction):
	"""Anachronos — printed text "Send all other minions 2 turns into
	the future." Snapshot every other minion's id/atk/health, send them
	to SETASIDE, and register a delayed-return entry on each owner's
	_anachronos_returns. The game's begin_turn ticks down and re-summons
	at the owner's 2nd upcoming turn (Tier-0.5 scheduler)."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import Zone
		for m in list(source.game.board):
			if m is source:
				continue
			owner = m.controller
			entry = {
				"turns_left": 2,
				"id": m.id,
				"atk": m.atk,
				"max_health": m.max_health,
			}
			if not hasattr(owner, "_anachronos_returns"):
				owner._anachronos_returns = []
			owner._anachronos_returns.append(entry)
			# Remove the minion from play (treat as setaside, not destroyed
			# — death triggers/Reborn shouldn't fire).
			m.zone = Zone.SETASIDE


class _BloodCrusaderArm(TargetedAction):
	"""Blood Crusader — set a per-turn controller flag so the next
	Paladin minion the controller plays this turn costs Health instead
	of Mana. The cost-substitution itself is a TODO requiring a hook in
	Play.do (analogous to Anub'Rekhan's minions_cost_armor_this_turn);
	we set the flag so the engine wire-up lands without a script change."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.next_paladin_minion_costs_health_this_turn = True


##
# Spells


class RLK_917:
	"""Flight of the Bronze"""

	# Discover a Dragon. Manathirst (7): Summon a 5/5 Drake with Taunt.
	play = (
		DISCOVER(RandomMinion(race=Race.DRAGON)),
		MANATHIRST(7) & Summon(CONTROLLER, "RLK_917t"),
	)


class RLK_917t:
	"""Bronze Defender"""


class RLK_918:
	"""For Quel'Thalas!"""

	# Give a friendly minion +3 Attack. Give your hero +2 Attack this turn.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "RLK_918e"), Buff(FRIENDLY_HERO, "RLK_918e2")


class RLK_918e:
	# In-data card, but ATK tag is not in the parsed data — declare it.
	tags = {GameTag.ATK: 3}


class RLK_918e2:
	# In-data card; carries TAG_ONE_TURN_EFFECT in data so the engine
	# auto-clears it at end of turn. We add the ATK tag (not present in
	# parsed data).
	tags = {GameTag.ATK: 2}


class RLK_922:
	"""Seal of Blood"""

	# Give a minion +3/+3 and Divine Shield. Deal $3 damage to your hero.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Buff(TARGET, "RLK_922e"),
		GiveDivineShield(TARGET),
		Hit(FRIENDLY_HERO, 3),
	)


class RLK_922e:
	# In-data buff Blood Seal; ATK/HEALTH not parsed from data.
	tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class RLK_923:
	"""Feast and Famine"""

	# Give your hero +3 Attack this turn. Manathirst (4): And Lifesteal.
	# Lifesteal is attached via the alternate one-turn buff RLK_923e2
	# (LIFESTEAL on the enchant carries over to hero attacks). The base
	# branch uses RLK_923e (+3 Attack only).
	play = (
		(MANATHIRST(4) & Buff(FRIENDLY_HERO, "RLK_923e2"))
		| Buff(FRIENDLY_HERO, "RLK_923e"),
	)


@custom_card
class RLK_923e:
	# Not present in data — register manually. +3 Attack, one-turn.
	tags = {
		GameTag.CARDNAME: "Feast and Famine",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 3,
		GameTag.TAG_ONE_TURN_EFFECT: True,
	}


@custom_card
class RLK_923e2:
	# Manathirst (4) variant: +3 Attack and Lifesteal for the turn.
	tags = {
		GameTag.CARDNAME: "Feast and Famine",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 3,
		GameTag.LIFESTEAL: True,
		GameTag.TAG_ONE_TURN_EFFECT: True,
	}


##
# Minions


class RLK_527:
	"""Timewarden"""

	# Battlecry: Until the end of your next turn, Dragons you summon
	# gain Taunt and Divine Shield. The aura runs from Timewarden's own
	# `events` while it remains in play (printed text doesn't require
	# Timewarden to survive, but this is the standard fireplace pattern
	# for "until end of next turn" battlecry auras and the engine has
	# no separate aura-entity primitive). Ticks down at each
	# OWN_TURN_END.
	play = _TimewardenStartAura(CONTROLLER)
	events = [
		Summon(CONTROLLER, DRAGON - SELF).after(
			(Attr(CONTROLLER, "_timewarden_turns_left") > 0)
			& (
				Taunt(Summon.CARD),
				GiveDivineShield(Summon.CARD),
			)
		),
		OWN_TURN_END.on(_TimewardenTick(CONTROLLER)),
	]


class RLK_916:
	"""Daring Drake"""

	# Rush. Battlecry: If you're holding a Dragon, gain +1/+1.
	play = HOLDING_DRAGON & Buff(SELF, "RLK_916e")


class RLK_916e:
	# In-data buff Bravery; ATK/HEALTH not parsed from data.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class RLK_919:
	"""Anachronos"""

	# Battlecry: Send all other minions 2 turns into the future.
	# Implementation: every other minion is moved to SETASIDE and a
	# delayed-return entry is appended to its owner. The engine's
	# begin_turn (game.py) ticks down each entry and summons a fresh
	# copy with snapshotted atk/health when the count hits 0.
	play = _AnachronosTimeJump(SELF)


class RLK_921:
	"""Sanguine Soldier"""

	# Divine Shield. Battlecry: Deal 2 damage to your hero.
	play = Hit(FRIENDLY_HERO, 2)


class RLK_924:
	"""Blood Matriarch Liadrin"""

	# After you summon a minion with less Attack than this, give it
	# Divine Shield and Rush.
	events = Summon(CONTROLLER, MINION - SELF).after(
		(Attr(Summon.CARD, GameTag.ATK) < Attr(SELF, GameTag.ATK))
		& (GiveDivineShield(Summon.CARD), GiveRush(Summon.CARD))
	)


class RLK_927:
	"""Blood Crusader"""

	# Battlecry: Your next Paladin minion this turn costs Health
	# instead of Mana.
	# Approximation: set per-turn controller flag
	# `next_paladin_minion_costs_health_this_turn`. The cost
	# substitution itself is TODO — needs a hook in Play.do mirroring
	# Anub'Rekhan's minions_cost_armor_this_turn.
	play = _BloodCrusaderArm(CONTROLLER)


class RLK_927e:
	# In-data buff "Crusade" — CANT_BE_SILENCED + TAG_ONE_TURN_EFFECT
	# already set in data; this declaration just wires it for the engine.
	tags = {}
