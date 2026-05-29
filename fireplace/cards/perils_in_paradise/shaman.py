from ..utils import *


##
# Custom actions / helpers


class _RazzleDazzlerSummon(TargetedAction):
	"""Razzle-Dazzler — Battlecry: Summon a random 5-Cost minion, then
	repeat once for each distinct spell school you've cast this game.
	So total summons = 1 + (number of distinct schools in
	``controller.spells_cast_by_school``)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		schools = len(getattr(ctrl, "spells_cast_by_school", {}))
		total = 1 + schools
		for _ in range(total):
			pick = RandomMinion(cost=5).evaluate(source)
			if not pick:
				continue
			source.game.cheat_action(source, [Summon(ctrl, pick)])


class _SirenSongUnknownSchools(TargetedAction):
	"""Siren Song — Get two random spells from spell schools you haven't
	cast this game. We pick schools the controller has NOT cast yet
	(from ARCANE..FEL), then hand a random spell of each of two such
	schools. If fewer than two unused schools remain, fall back to any
	random spell so the card never fizzles."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import SpellSchool

		ctrl = source.controller
		cast = set(getattr(ctrl, "spells_cast_by_school", {}).keys())
		all_schools = [int(s) for s in (
			SpellSchool.ARCANE, SpellSchool.FIRE, SpellSchool.FROST,
			SpellSchool.NATURE, SpellSchool.HOLY, SpellSchool.SHADOW,
			SpellSchool.FEL,
		)]
		unused = [s for s in all_schools if s not in cast]
		source.game.random.shuffle(unused)
		picks = []
		for school in unused:
			if len(picks) >= 2:
				break
			pick = RandomSpell(spell_school=SpellSchool(school)).evaluate(source)
			if isinstance(pick, list):
				pick = pick[0] if pick else None
			if pick:
				picks.append(pick)
		# Fill remaining slots with any random spell if not enough
		# distinct unused schools had a collectible spell.
		while len(picks) < 2:
			pick = RandomSpell().evaluate(source)
			if isinstance(pick, list):
				pick = pick[0] if pick else None
			if not pick:
				break
			picks.append(pick)
		for pick in picks:
			source.game.cheat_action(source, [Give(ctrl, pick.id)])


class _NaturalTalentGet(TargetedAction):
	"""Natural Talent — Get a random Naga and a random spell. They cost
	(1) less. Hand a random Naga minion and a random spell, then stamp a
	-1 cost enchant on each freshly-given card."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		naga = RandomMinion(race=Race.NAGA).evaluate(source)
		spell = RandomSpell().evaluate(source)
		for pick in (naga, spell):
			if isinstance(pick, list):
				pick = pick[0] if pick else None
			if not pick:
				continue
			given = ctrl.card(pick.id, source=source)
			source.game.cheat_action(source, [Give(ctrl, given)])
			source.game.cheat_action(source, [Buff(given, "VAC_329e")])


class _CabaretHeadlinerReduce(TargetedAction):
	"""Cabaret Headliner — Reduce the Cost of a spell of each school in
	your hand by (2). For every spell school, pick at most one held spell
	of that school and stamp the -2 cost enchant. NONE-school spells are
	skipped (they belong to no school)."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import SpellSchool

		ctrl = source.controller
		used_schools = set()
		for card in list(ctrl.hand):
			if card.type != CardType.SPELL:
				continue
			school = getattr(card, "spell_school", None)
			if not school or int(school) == int(SpellSchool.NONE):
				continue
			if int(school) in used_schools:
				continue
			used_schools.add(int(school))
			source.game.cheat_action(source, [Buff(card, "VAC_954e1")])


class _CarefreeCookieSummon(TargetedAction):
	"""Carefree Cookie — After a friendly minion dies, summon a random
	minion that costs (1) more than the dead minion."""

	TARGET = ActionArg()
	OTHER = CardArg()

	def do(self, source, target, other):
		if isinstance(other, list):
			other = other[0] if other else None
		if other is None:
			return
		cost = (other.cost or 0) + 1
		pick = RandomMinion(cost=cost).evaluate(source)
		if not pick:
			return
		source.game.cheat_action(source, [Summon(source.controller, pick)])


# Maps a sorted pair of spell-school ints to the Carress transform variant.
# Effects per school: 1 Arcane=Draw 2, 2 Fire=Deal 6 to hero,
# 3 Frost=Freeze 3, 4 Nature=+2/+2 & Taunt, 5 Holy=Restore 6,
# 6 Shadow=Destroy 2, 7 Fel=Deal 2 to all enemy minions.
_CARRESS_VARIANTS = {
	(1, 2): "VAC_449t",     # Draw2 + Deal6hero
	(1, 3): "VAC_449t1",    # Draw2 + Freeze3
	(1, 4): "VAC_449t2",    # Draw2 + +2/+2 Taunt
	(1, 5): "VAC_449t3",    # Draw2 + Restore6
	(1, 6): "VAC_449t4",    # Draw2 + Destroy2
	(1, 7): "VAC_449t5",    # Draw2 + Deal2all
	(2, 3): "VAC_449t6",    # Deal6hero + Freeze3
	(2, 4): "VAC_449t7",    # Deal6hero + +2/+2 Taunt
	(2, 5): "VAC_449t8",    # Deal6hero + Restore6
	(2, 6): "VAC_449t9",    # Deal6hero + Destroy2
	(2, 7): "VAC_449t10",   # Deal6hero + Deal2all
	(3, 4): "VAC_449t11",   # +2/+2 Taunt + Freeze3
	(3, 5): "VAC_449t12",   # Restore6 + Freeze3
	(3, 6): "VAC_449t13",   # Destroy2 + Freeze3
	(3, 7): "VAC_449t14",   # Deal2all + Freeze3
	(4, 5): "VAC_449t15",   # +2/+2 Taunt + Restore6
	(4, 6): "VAC_449t16",   # +2/+2 Taunt + Destroy2
	(4, 7): "VAC_449t17",   # +2/+2 Taunt + Deal2all
	(5, 6): "VAC_449t18",   # Restore6 + Destroy2
	(5, 7): "VAC_449t19",   # Restore6 + Deal2all
	(6, 7): "VAC_449t20",   # Deal2all + Destroy2
}


class _MatchingOutfits(TargetedAction):
	"""Matching Outfits — Transform the targeted minion into a random
	minion that costs (1) more than it, then summon a copy of the
	transformed minion."""

	TARGET = ActionArg()

	def do(self, source, target):
		if isinstance(target, list):
			target = target[0] if target else None
		if target is None:
			return
		cost = (target.cost or 0) + 1
		pick = RandomMinion(cost=cost).evaluate(source)
		if isinstance(pick, list):
			pick = pick[0] if pick else None
		if not pick:
			return
		# `pick` is a freshly-created Card entity from the pool; morph the
		# target straight into it, then summon a copy of the result.
		new_card = source.controller.card(pick.id, source=source)
		ctrl = target.controller
		source.game.cheat_action(source, [Morph(target, new_card)])
		# Summon a copy of the transformed minion (freshly morphed, so a
		# clean instance of the same card id is an exact copy).
		source.game.cheat_action(source, [Summon(ctrl, new_card.id)])


class _CarressTransform(TargetedAction):
	"""Carress, Cabaret Star — while in hand, once two *different* spell
	schools have been cast while holding it, transform into the variant
	whose Battlecry combines the two matching effects (see
	``_CARRESS_VARIANTS``)."""

	TARGET = ActionArg()

	def do(self, source, target):
		schools = sorted(getattr(target, "spell_schools_cast_while_holding", set()))
		if len(schools) < 2:
			return
		key = (schools[0], schools[1])
		variant = _CARRESS_VARIANTS.get(key)
		if not variant:
			return
		new_card = source.controller.card(variant, source=source)
		source.game.cheat_action(source, [Morph(target, new_card)])


##
# Minions


class VAC_301:
	"""Razzle-Dazzler"""

	# [x]<b>Battlecry:</b> Summon a random 5-Cost minion. Repeat for each
	# spell school you've cast this game.
	play = _RazzleDazzlerSummon(CONTROLLER)


class VAC_328:
	"""Meltemental"""

	# [x]<b>Taunt</b> This is permanently <b>Frozen</b>.
	# (Taunt is a data tag. The engine clears FROZEN at the owner's
	# turn-begin; re-apply it on every turn-begin so it never thaws.)
	events = TURN_BEGIN.on(SetTag(SELF, GameTag.FROZEN))


class VAC_328e:
	"""Stay Frosty"""

	# Permanently Frozen
	tags = {GameTag.FROZEN: True}


class VAC_449:
	"""Carress, Cabaret Star"""

	# While in your hand, play two different spell schools to transform.
	# (Vanilla 5/5 until it transforms; the transform fires from hand on
	# each spell cast once two distinct schools have been played.)
	class Hand:
		events = OWN_SPELL_PLAY.after(_CarressTransform(SELF))

	def custom_cardtext(self):
		segments = self.data.description.split("@")
		if len(segments) < 3:
			return self.data.description
		count = len(getattr(self, "spell_schools_cast_while_holding", set()))
		if count >= 2:
			return segments[0] + segments[2]
		return segments[0] + segments[1]

	def cardtext_entity_0(self):
		count = len(getattr(self, "spell_schools_cast_while_holding", set()))
		return max(0, 2 - count)

	tags = {
		enums.CUSTOM_CARDTEXT: custom_cardtext,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


class VAC_449e1:
	"""Siren Songs"""

	# +2/+2.
	tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


# Carress transform variants. Each is a 5/5 Naga with a two-part Battlecry.
# Effect building blocks (reused below):
#   Draw2          = Draw(CONTROLLER) * 2
#   Deal6hero      = Hit(ENEMY_HERO, 6)
#   Freeze3        = Freeze(RANDOM_ENEMY_MINION * 3)
#   Plus22Taunt    = Buff(SELF, "VAC_449e1"), Taunt(SELF)
#   Restore6       = Heal(FRIENDLY_HERO, 6)
#   Destroy2       = Destroy(RANDOM_ENEMY_MINION * 2)
#   Deal2all       = Hit(ENEMY_MINIONS, 2)

class VAC_449t:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Draw 2 cards. Deal 6 damage to the enemy hero.
	play = Draw(CONTROLLER) * 2, Hit(ENEMY_HERO, 6)


class VAC_449t1:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Draw 2 cards. Freeze three random enemy minions.
	play = Draw(CONTROLLER) * 2, Freeze(RANDOM_ENEMY_MINION * 3)


class VAC_449t2:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Draw 2 cards. Gain +2/+2 and Taunt.
	play = Draw(CONTROLLER) * 2, Buff(SELF, "VAC_449e1"), Taunt(SELF)


class VAC_449t3:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Draw 2 cards. Restore 6 Health to your hero.
	play = Draw(CONTROLLER) * 2, Heal(FRIENDLY_HERO, 6)


class VAC_449t4:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Draw 2 cards. Destroy 2 random enemy minions.
	play = Draw(CONTROLLER) * 2, Destroy(RANDOM_ENEMY_MINION * 2)


class VAC_449t5:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Draw 2 cards. Deal 2 damage to all enemy minions.
	play = Draw(CONTROLLER) * 2, Hit(ENEMY_MINIONS, 2)


class VAC_449t6:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Deal 6 damage to the enemy hero. Freeze three
	# random enemy minions.
	play = Hit(ENEMY_HERO, 6), Freeze(RANDOM_ENEMY_MINION * 3)


class VAC_449t7:
	"""Carress, Cabaret Star"""

	# [x]<b>Battlecry:</b> Deal 6 damage to the enemy hero. Gain +2/+2 and
	# Taunt.
	play = Hit(ENEMY_HERO, 6), Buff(SELF, "VAC_449e1"), Taunt(SELF)


class VAC_449t8:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Deal 6 damage to the enemy hero. Restore 6 Health
	# to your hero.
	play = Hit(ENEMY_HERO, 6), Heal(FRIENDLY_HERO, 6)


class VAC_449t9:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Deal 6 damage to the enemy hero. Destroy 2 random
	# enemy minions.
	play = Hit(ENEMY_HERO, 6), Destroy(RANDOM_ENEMY_MINION * 2)


class VAC_449t10:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Deal 6 damage to the enemy hero. Deal 2 damage to
	# all enemy minions.
	play = Hit(ENEMY_HERO, 6), Hit(ENEMY_MINIONS, 2)


class VAC_449t11:
	"""Carress, Cabaret Star"""

	# [x]<b>Battlecry:</b> Gain +2/+2 and Taunt. Freeze three random enemy
	# minions.
	play = (
		Buff(SELF, "VAC_449e1"), Taunt(SELF),
		Freeze(RANDOM_ENEMY_MINION * 3),
	)


class VAC_449t12:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Restore 6 Health to your hero. Freeze three random
	# enemy minions.
	play = Heal(FRIENDLY_HERO, 6), Freeze(RANDOM_ENEMY_MINION * 3)


class VAC_449t13:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Destroy two random enemy minions. Freeze three
	# random enemy minions.
	play = Destroy(RANDOM_ENEMY_MINION * 2), Freeze(RANDOM_ENEMY_MINION * 3)


class VAC_449t14:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Deal 2 damage to all enemy minions. Freeze three
	# random enemy minions.
	play = Hit(ENEMY_MINIONS, 2), Freeze(RANDOM_ENEMY_MINION * 3)


class VAC_449t15:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Gain +2/+2 and Taunt. Restore 6 Health to your hero.
	play = Buff(SELF, "VAC_449e1"), Taunt(SELF), Heal(FRIENDLY_HERO, 6)


class VAC_449t16:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Gain +2/+2 and Taunt. Destroy 2 random enemy minions.
	play = (
		Buff(SELF, "VAC_449e1"), Taunt(SELF),
		Destroy(RANDOM_ENEMY_MINION * 2),
	)


class VAC_449t17:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Gain +2/+2 and Taunt. Deal 2 damage to all enemy
	# minions.
	play = Buff(SELF, "VAC_449e1"), Taunt(SELF), Hit(ENEMY_MINIONS, 2)


class VAC_449t18:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Restore 6 Health to your hero. Destroy 2 random
	# enemy minions.
	play = Heal(FRIENDLY_HERO, 6), Destroy(RANDOM_ENEMY_MINION * 2)


class VAC_449t19:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Restore 6 Health to your hero. Deal 2 damage to all
	# enemy minions.
	play = Heal(FRIENDLY_HERO, 6), Hit(ENEMY_MINIONS, 2)


class VAC_449t20:
	"""Carress, Cabaret Star"""

	# <b>Battlecry:</b> Deal 2 damage to all enemy minions. Destroy 2
	# random enemy minions.
	play = Hit(ENEMY_MINIONS, 2), Destroy(RANDOM_ENEMY_MINION * 2)


class VAC_450:
	"""Carefree Cookie"""

	# [x]<b>Demon Hunter Tourist</b> After a friendly minion dies, summon a
	# random minion that costs (1) more.
	# (Tourist is deckbuilding-only — only the death trigger is scripted.)
	events = Death(FRIENDLY + MINION).after(
		_CarefreeCookieSummon(SELF, Death.ENTITY)
	)


class VAC_954:
	"""Cabaret Headliner"""

	# <b>Battlecry:</b> Reduce the Cost of a spell of each school in your
	# hand by (2).
	play = _CabaretHeadlinerReduce(CONTROLLER)


class VAC_954e1:
	"""Siren Serenade"""

	# Costs (2) less.
	tags = {GameTag.COST: -2}


##
# Spells


class VAC_305:
	"""Frosty Décor"""

	# Summon two 2/4 Elementals with <b>Taunt</b> and "<b>Deathrattle</b>:
	# Gain 4 Armor".
	play = Summon(CONTROLLER, "VAC_305t") * 2


class VAC_305t:
	"""Ice Sculpture"""

	# <b>Taunt</b> <b>Deathrattle:</b> Gain 4 Armor.
	# (Taunt is a data tag.)
	deathrattle = GainArmor(FRIENDLY_HERO, 4)


class VAC_308:
	"""Siren Song"""

	# Get two random spells from spell schools you haven't cast this game.
	play = _SirenSongUnknownSchools(CONTROLLER)


class VAC_323:
	"""Malted Magma"""

	# Deal $1 damage to all enemies. (3 Drinks left!)
	play = Hit(ENEMY_CHARACTERS, 1), Give(CONTROLLER, "VAC_323t")


class VAC_323t:
	"""Malted Magma"""

	# Deal $1 damage to all enemies. (2 Drinks left!)
	play = Hit(ENEMY_CHARACTERS, 1), Give(CONTROLLER, "VAC_323t2")


class VAC_323t2:
	"""Malted Magma"""

	# Deal $1 damage to all enemies. (Last Drink!)
	play = Hit(ENEMY_CHARACTERS, 1)


class VAC_324:
	"""Matching Outfits"""

	# Transform a minion into a random one that costs (1) more, then summon
	# a copy of it.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _MatchingOutfits(TARGET)


class VAC_329:
	"""Natural Talent"""

	# Get a random Naga and a random spell. They cost (1) less.
	play = _NaturalTalentGet(CONTROLLER)


@custom_card
class VAC_329e:
	"""Natural Talent"""

	# Costs (1) less. (Not in card data — registered as an engine-internal
	# cost-reduction enchant for the cards Natural Talent hands you.)
	tags = {
		GameTag.CARDNAME: "Natural Talent",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -1,
	}
