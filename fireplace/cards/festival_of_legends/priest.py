from ..utils import *
from .utils import _HarmonicSwap


##
# Custom actions


class _DreamboatHealAndBuff(TargetedAction):
	"""Dreamboat — restore 3 health to all other friendly minions; for
	each one overhealed, gain +1/+1 on SELF.

	Overheal here matches the engine's Heal-hook definition: requested
	amount exceeds the minion's pre-heal damage. A minion that's exactly
	healed to full (damage == 3, heal 3) does NOT count.
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		others = [m for m in source.controller.field if m is not source]
		overhealed = 0
		for m in others:
			pre_damage = m.damage
			source.game.cheat_action(source, [Heal(m, 3)])
			if 3 > pre_damage:  # requested > pre_damage
				overhealed += 1
		for _ in range(overhealed):
			source.game.cheat_action(source, [Buff(source, "ETC_332e")])


class _HedanisOverhealRetaliate(TargetedAction):
	"""Heartbreaker Hedanis — Overheal: deal 5 to a random enemy.

	Reads `_last_heal_overheal` stamped on SELF by Heal.do (engine hook).
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		if getattr(target, "_last_heal_overheal", 0) > 0:
			source.game.cheat_action(
				source, [Hit(RANDOM(ENEMY_CHARACTERS), 5)]
			)


class _HeartthrobOverhealSummon(TargetedAction):
	"""Heartthrob — Overheal: summon a random minion whose Cost equals
	the overheal amount. Reads `_last_heal_overheal` stamped on SELF by
	Heal.do."""

	TARGET = ActionArg()

	def do(self, source, target):
		overheal = getattr(target, "_last_heal_overheal", 0)
		if overheal <= 0:
			return
		from ... import cards as _cards
		pool = _cards.db.filter(
			collectible=True, type=CardType.MINION, cost=overheal
		)
		if not pool:
			return
		picked = source.game.random.choice(pool)
		source.game.cheat_action(
			source, [Summon(source.controller, picked)]
		)


class _LoveEverlastingArm(TargetedAction):
	"""Love Everlasting — flip the controller's per-turn discount flag
	and stamp the marker enchant. The discount itself is applied by the
	in-data ETC_335e enchant (auras refresh on the controller); we just
	arm the controller-side counter so the cost mod can find it."""

	TARGET = ActionArg()

	def do(self, source, target):
		target._love_everlasting_active = True


class _PowerChordCopyAndMaybeBuff(TargetedAction):
	"""Power Chord: Synchronize — copy TARGET to hand. Finale: also
	+1/+2 both the original and the copy."""

	TARGET = ActionArg()

	def do(self, source, target):
		from ...dsl.copy import ExactCopy
		ctrl = source.controller
		copy = ExactCopy(target).copy(source, target)
		copy.controller = ctrl
		source.game.cheat_action(source, [Give(ctrl, copy)])
		if getattr(source, "play_finale", False):
			source.game.cheat_action(
				source,
				[
					Buff(target, "ETC_338e_buff"),
					Buff(copy, "ETC_338e_buff"),
				],
			)


def _fight_over_me_resolve(source, a, b):
	"""Resolve the Fight Over Me strike between two enemy minions A
	and B. Simultaneous-strike: both deal their atk to each other,
	then a copy of each casualty lands in the controller's hand."""
	from ...dsl.copy import ExactCopy
	from hearthstone.enums import Zone
	if a is None or b is None or a is b:
		return
	t_atk = a.atk
	m_atk = b.atk
	source.game.cheat_action(
		source, [Hit(a, m_atk), Hit(b, t_atk)]
	)
	for c in (a, b):
		if c is None:
			continue
		if c.zone == Zone.GRAVEYARD or getattr(c, "dead", False):
			copy = ExactCopy(c).copy(source, c)
			copy.controller = source.controller
			source.game.cheat_action(
				source, [Give(source.controller, copy)]
			)


class _FightOverMePickB:
	"""Lightweight pick-an-entity choice opened on the controller.
	Exposes the same `.cards` / `.choose(card)` interface as the
	engine's GenericChoice so the soak's choice-resolver loop
	(`player.choice.choose(random.choice(player.choice.cards))`) can
	drive it without modification. `choose(card)` fires the resolver
	against the stashed A and the just-picked B."""

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
		a = getattr(self.source, "_fightovermeA", None)
		_fight_over_me_resolve(self.source, a, card)


class _FightOverMeAction(TargetedAction):
	"""Fight Over Me — TARGET is the first chosen enemy minion.
	Open a pick-an-entity choice over the OTHER enemy minions so the
	controller picks the second combatant. Resolution happens in
	`choose()` on _FightOverMePickB. (The prior approximation picked
	the second combatant at random — printed text says "Choose two".)"""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		others = [m for m in opp.field if m is not target]
		if not others:
			return
		source._fightovermeA = target
		pre_existing_B = getattr(source, "_fightovermeB", None)
		if pre_existing_B is not None and pre_existing_B in others:
			# Test-injected pre-pick: skip the choice UI.
			source._fightovermeB = None
			_fight_over_me_resolve(source, target, pre_existing_B)
			return
		source.controller.choice = _FightOverMePickB(
			source, source.controller, others
		)


##
# Spells


class ETC_305:
	"""Shadow Chord: Distort"""

	# Give a minion -5/-5. If it has 0 Attack, destroy it.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Buff(TARGET, "ETC_305e"),
		(Attr(TARGET, GameTag.ATK) == 0) & Destroy(TARGET),
	)


class ETC_314:
	"""Harmonic Pop"""

	# Printed base: Deal $3 damage to all minions. Summon a 6/6 Popstar.
	# Alt branch (Swaps each turn): deal $6 damage to all enemy minions
	# instead (no Popstar summon, no friendly minion damage).
	_HARMONIC_BASE = (
		Hit(ALL_MINIONS, 3),
		Summon(CONTROLLER, "ETC_314t_popstar"),
	)
	_HARMONIC_ALT = (Hit(ENEMY_MINIONS, 6),)
	play = _HarmonicSwap(CONTROLLER)


@custom_card
class ETC_314t_popstar:
	"""Popstar"""

	tags = {
		GameTag.CARDNAME: "Popstar",
		GameTag.CARDTYPE: CardType.MINION,
		GameTag.ATK: 6,
		GameTag.HEALTH: 6,
	}


class ETC_316:
	"""Fight Over Me"""

	# Choose two enemy minions. They fight! Add copies of any that die
	# to your hand. Approximation: take the targeted enemy + a random
	# other enemy as the second combatant.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _FightOverMeAction(TARGET)


class ETC_335:
	"""Love Everlasting"""

	# Your first spell each turn costs (2) less. Lasts until you don't
	# play a spell on your turn.
	play = _LoveEverlastingArm(CONTROLLER)


class ETC_338:
	"""Power Chord: Synchronize"""

	# Choose a minion. Add a copy of it to your hand. Finale: Give both
	# +1/+2.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _PowerChordCopyAndMaybeBuff(TARGET)


##
# Minions


class ETC_332:
	"""Dreamboat"""

	# Battlecry: Restore #3 Health to all other friendly minions. Gain
	# +1/+1 for each one Overhealed.
	play = _DreamboatHealAndBuff(SELF)


class ETC_334:
	"""Heartbreaker Hedanis"""

	# Battlecry: Deal 4 damage to this minion. Overheal: Deal 5 damage
	# to a random enemy.
	# Battlecry just self-hits; the Overheal half lives on a permanent
	# self-listener that watches Heals of SELF.
	play = Hit(SELF, 4)
	events = Heal(SELF).on(_HedanisOverhealRetaliate(SELF))


class ETC_339:
	"""Heartthrob"""

	# Overheal: Summon a random minion with Cost equal to the amount
	# Overhealed.
	events = Heal(SELF).on(_HeartthrobOverhealSummon(SELF))


##
# Weapons


class ETC_312:
	"""Idol's Adoration"""

	# Your Hero Power costs (0). After you use it, lose 1 Durability.
	update = Refresh(FRIENDLY_HERO_POWER, buff="ETC_312e")
	events = Activate(FRIENDLY_HERO_POWER).after(Hit(SELF, 1))


class ETC_312e:
	# In-data buff "Sing!" — Hero Power costs (0). Data parser misses
	# the COST tag, so declare -100 (engine clamps to 0).
	tags = {GameTag.COST: -100}


##
# Locations


class ETC_449:
	"""Fan Club"""

	# Restore #3 Health to all friendly characters.
	activate = Heal(FRIENDLY_CHARACTERS, 3)


##
# Enchantments


class ETC_305e:
	# In-data buff "Distorted" — -5/-5. ATK/HEALTH not parsed from data.
	tags = {GameTag.ATK: -5, GameTag.HEALTH: -5}


class ETC_332e:
	"""So Dreamy!"""

	# In-data Dreamboat buff — +1/+1 per overhealed friendly minion.
	# ATK/HEALTH not parsed from data; declare here.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


@custom_card
class ETC_338e_buff:
	"""Synchronized"""

	tags = {
		GameTag.CARDNAME: "Synchronized",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 1,
		GameTag.HEALTH: 2,
	}
