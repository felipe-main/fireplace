from ..utils import *


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


class _FightOverMeAction(TargetedAction):
	"""Fight Over Me — TARGET is a chosen enemy minion. Pick a random
	other enemy minion as the second combatant; both deal their attack
	to each other simultaneously. Add a copy of any combatant that dies
	to the controller's hand."""

	TARGET = ActionArg()

	def do(self, source, target):
		from ...dsl.copy import ExactCopy
		from hearthstone.enums import Zone
		opp = source.controller.opponent
		others = [m for m in opp.field if m is not target]
		if not others:
			return
		mate = source.game.random.choice(others)
		combatants = [target, mate]
		t_atk = target.atk
		m_atk = mate.atk
		source.game.cheat_action(
			source, [Hit(target, m_atk), Hit(mate, t_atk)]
		)
		for c in combatants:
			if c.zone == Zone.GRAVEYARD or getattr(c, "dead", False):
				copy = ExactCopy(c).copy(source, c)
				copy.controller = source.controller
				source.game.cheat_action(
					source, [Give(source.controller, copy)]
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

	# Deal $3 damage to all minions. Summon a 6/6 Popstar.
	play = Hit(ALL_MINIONS, 3), Summon(CONTROLLER, "ETC_314t_popstar")


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
