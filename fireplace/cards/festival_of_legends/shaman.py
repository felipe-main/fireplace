from ..utils import *
from .utils import _WeaponCounterCardtextMixin


##
# Custom actions


class _FlowriderDiscoverFromDeck(TargetedAction):
	"""Flowrider — if the controller is Overloaded, Discover a spell from
	their own deck. Builds a RandomID picker scoped to the spell-ids
	currently in deck so the discover window matches the printed text
	"a spell from your deck" rather than any random spell."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not (ctrl.overloaded > 0 or ctrl.overload_locked > 0):
			return
		spells = [c for c in ctrl.deck if c.type == CardType.SPELL]
		if not spells:
			return
		# Each card in the deck is its own entity — use ids; collapse
		# duplicates (RandomID handles uniqueness inside the discover).
		ids = [c.id for c in spells]
		source.game.cheat_action(source, [DISCOVER(RandomID(*ids))])


class _PackTheHouseSummon(TargetedAction):
	"""Pack the House — summon a random 6, 5, 4, and 3-cost minion (one
	of each). Implemented as a single custom action so each RandomMinion
	pick is independent and we can hit four distinct costs in one block."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardType
		ctrl = source.controller
		for cost in (6, 5, 4, 3):
			pick = RandomMinion(cost=cost).evaluate(source)
			if not pick:
				continue
			cid = pick[0] if isinstance(pick, list) else pick
			source.game.cheat_action(source, [Summon(ctrl, cid)])


class _MelomaniaArm(TargetedAction):
	"""Melomania — flip a controller flag so the OWN_PLAY listener fires
	this turn. Listener is on the controller's Hero (already alive); the
	flag auto-clears at OWN_TURN_END."""

	TARGET = ActionArg()

	def do(self, source, target):
		target._melomania_active = True
		source.game.cheat_action(source, [Buff(target, "ETC_367e")])


class _MelomaniaGiveSpell(TargetedAction):
	"""Melomania — on each minion played by the controller this turn,
	give the controller a random Shaman spell. Gated on the per-turn
	flag set by _MelomaniaArm."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not getattr(ctrl, "_melomania_active", False):
			return
		source.game.cheat_action(
			source,
			[Give(ctrl, RandomSpell(card_class=CardClass.SHAMAN))],
		)


class _JazzBassDeathrattle(TargetedAction):
	"""Jazz Bass deathrattle — stamp the controller's
	`_next_spell_cost_reduction` to the per-weapon counter of overload
	the controller incurred while this weapon was equipped. Pay_cost on
	the next spell consumes it (MotLK Glacial Advance reuses the same
	channel)."""

	TARGET = ActionArg()

	def do(self, source, target):
		n = getattr(target, "overload_while_equipped", 0)
		if n <= 0:
			return
		source.controller._next_spell_cost_reduction = n


class _JazzBassOverloadBump(TargetedAction):
	"""Bump the equipped Jazz Bass's per-weapon Overload counter each
	time the controller triggers Overload while the weapon is equipped.
	`source` is the weapon (Overload.on listener owner)."""

	TARGET = ActionArg()
	AMOUNT = IntArg()

	def do(self, source, target, amount):
		# `target` is the player Overload fires on; ensure it matches the
		# weapon's controller before bumping.
		if target is not source.controller:
			return
		source.overload_while_equipped = (
			getattr(source, "overload_while_equipped", 0) + (amount or 0)
		)


##
# Minions


class ETC_357:
	"""Brass Elemental"""

	# Rush, Divine Shield, Taunt, Windfury — all in data. Vanilla. No
	# scripted behaviour required.


class ETC_358:
	"""Saxophone Soloist"""

	# Battlecry: If you control no other minions, add a Saxophone
	# Soloist to your hand. EMPTY_BOARD alone is False at battlecry
	# time (Sax already entered PLAY before battlecry resolves) — use
	# the explicit -SELF filter to enforce "no OTHER minions".
	play = (Count(FRIENDLY_MINIONS - SELF) == 0) & Give(CONTROLLER, "ETC_358")


class ETC_359:
	"""Flowrider"""

	# Battlecry: If you're Overloaded, Discover a spell from your deck.
	play = _FlowriderDiscoverFromDeck(SELF)


class ETC_371:
	"""Inzah"""

	# Battlecry: For the rest of the game, your Overload cards cost (1)
	# less. Persistent aura stamped on the controller (lives forever —
	# not dependent on Inzah staying on the board). Mirrors REV_314e
	# (Topior the Shrubbagazzor) which puts a permanent listener on
	# the controller via Buff(CONTROLLER, "...").
	play = Buff(CONTROLLER, "ETC_371e")


@custom_card
class ETC_371e:
	# Custom enchant stamped on the controller. While alive, refreshes
	# every Overload card in the controller's hand with -1 cost.
	tags = {
		GameTag.CARDNAME: "Inzah",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	update = Refresh(FRIENDLY_HAND + OVERLOAD, {GameTag.COST: -1})


##
# Spells


class ETC_356:
	"""Altered Chord"""

	# Lifesteal. Deal $5 damage to a minion. Costs (3) less if you're
	# Overloaded. Lifesteal is set in data.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	# OVERLOADED is a python-level helper (`lambda s: bool`) and can't
	# compose with `& -3` for cost_mod, which needs a LazyNum/Evaluator.
	# Use the explicit OWED/LOCKED comparator: -3 if either is > 0.
	cost_mod = (Attr(CONTROLLER, GameTag.OVERLOAD_OWED) + Attr(CONTROLLER, GameTag.OVERLOAD_LOCKED) >= 1) & -3
	play = Hit(TARGET, 5)


class ETC_362:
	"""JIVE, INSECT!"""

	# Transform a minion into Ragnaros the Firelord.
	# Overload: (2) is in data (handled by Play.do).
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Morph(TARGET, "EX1_298")


class ETC_367:
	"""Melomania"""

	# Each time you play a minion this turn, add a random Shaman spell
	# to your hand. Arms a per-turn flag on the controller; the listener
	# is wired below on the enchantment's Hand-side (cast-on-hero).
	play = _MelomaniaArm(CONTROLLER)


class ETC_367e:
	# In-data "Melomania" enchantment — stamped on controller for the
	# turn. While the flag is set, every minion the controller plays
	# adds a random Shaman spell to hand. Auto-cleared at end of turn
	# (TAG_ONE_TURN_EFFECT in data).
	events = (
		Play(CONTROLLER, MINION).after(_MelomaniaGiveSpell(SELF)),
		OWN_TURN_END.on(
			# Clear the flag at end of turn (the engine-side
			# TAG_ONE_TURN_EFFECT will also tear this enchant down).
			Destroy(SELF),
		),
	)


class ETC_369:
	"""Chill Vibes"""

	# Restore #8 Health. Finale: Summon a 3/3 Elemental with Taunt.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
	}
	play = (
		Heal(TARGET, 8),
		FINALE & Summon(CONTROLLER, "ETC_369t"),
	)


class ETC_370:
	"""Pack the House"""

	# Summon a random 6, 5, 4, and 3-Cost minion.
	# Overload: (2) is in data.
	play = _PackTheHouseSummon(CONTROLLER)


##
# Weapons


class ETC_813(_WeaponCounterCardtextMixin):
	"""Jazz Bass"""

	# Deathrattle: Your next spell costs (@) less. (Overload while
	# equipped to improve!) Per-weapon counter tracks total Overload
	# triggered by the controller while this weapon is equipped; on
	# death the counter is dumped into the controller's
	# _next_spell_cost_reduction (consumed by pay_cost on next spell).
	overload_while_equipped = 0
	counter_attr = "overload_while_equipped"
	events = Overload(CONTROLLER).on(_JazzBassOverloadBump(SELF))
	deathrattle = _JazzBassDeathrattle(SELF)


##
# Tokens


class ETC_369t:
	"""Chill Elemental"""

	# 3/3 Elemental with Taunt summoned by Chill Vibes' Finale.
	# Taunt set in data; no script needed.
