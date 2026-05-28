from ..utils import *


##
# Custom actions


class _KhazgorothAbilityPassive(TargetedAction):
	"""Khaz'goroth — after using a Titan ability, gain Immune this turn
	and attack a random enemy minion.  Called from each of the three
	ability sub-cards' play scripts.  `target` here is Khaz'goroth itself
	(passed as SELF from each ability's play script)."""

	TARGET = ActionArg()

	def do(self, source, target):
		# In the Titan ability context, `source` is Khaz'goroth.
		# `target` is the resolved SELF selector (also Khaz'goroth).
		khaz = source
		ctrl = khaz.controller
		# Grant Immune (CANT_BE_DAMAGED) until end of turn via a temp buff.
		source.game.cheat_action(source, [Buff(khaz, "TTN_415e")])
		# Attack a random enemy minion if one exists.
		if ctrl.opponent.field:
			source.game.cheat_action(
				source,
				[Attack(khaz, RANDOM_ENEMY_MINION)],
			)


class _TrialByFireDeathrattle(TargetedAction):
	"""Trial by Fire Val'kyr deathrattle — when any Val'kyr dies, give
	all other Val'kyrs on the board +1/+1."""

	TARGET = ActionArg()

	def do(self, source, target):
		valkyr_id = "TTN_470t"
		living = [m for m in source.controller.field if m.id == valkyr_id]
		for m in living:
			source.game.cheat_action(source, [Buff(m, "TTN_470te")])


class _SmeltBuff(TargetedAction):
	"""Smelt — give a random minion in your hand +3/+3.  If the
	controller has at least 3 Armor, spend 3 Armor and repeat the buff
	on another random minion in hand."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		for _ in range(10):  # safety cap
			hand_minions = [c for c in ctrl.hand if c.type == CardType.MINION]
			if not hand_minions:
				break
			pick = source.game.random.choice(hand_minions)
			source.game.cheat_action(source, [Buff(pick, "TTN_803e")])
			# "Lose 3 Armor to do it again."
			if (ctrl.hero.armor or 0) >= 3:
				ctrl.hero.armor -= 3
			else:
				break


class _OdynArmorAttackListener(TargetedAction):
	"""Odyn — whenever the hero gains Armor, gain that much Attack for
	that turn.  Fires from the controller enchant's GainArmor listener."""

	TARGET = ActionArg()
	AMOUNT = IntArg()

	def do(self, source, target, amount):
		if amount <= 0:
			return
		# Give the friendly hero temporary Attack equal to the armor amount.
		ctrl = source.controller
		source.game.cheat_action(
			source,
			[Buff(ctrl.hero, "TTN_811e", atk=amount)],
		)


class _SteamGuardianReduceFire(TargetedAction):
	"""Steam Guardian — draw a spell, then reduce the Cost of a Fire
	spell in hand by (1)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		source.game.cheat_action(source, [Draw(ctrl)])
		fire_spells = [
			c for c in ctrl.hand
			if c.type == CardType.SPELL
			   and getattr(c, "spell_school", None) == SpellSchool.FIRE
		]
		if fire_spells:
			pick = source.game.random.choice(fire_spells)
			source.game.cheat_action(source, [Buff(pick, "TTN_468e")])


##
# Minions


class TTN_466:
	"""Minotauren"""

	# Rush (data). Whenever this minion deals damage, gain that much Armor.
	events = Damage(ALL_CHARACTERS, source=SELF).on(
		GainArmor(FRIENDLY_HERO, Damage.AMOUNT)
	)


class TTN_468:
	"""Steam Guardian"""

	# Battlecry: Draw a spell. Reduce the Cost of a Fire spell in your
	# hand by (1).
	play = _SteamGuardianReduceFire(SELF)


class TTN_469:
	"""Stoneskin Armorer"""

	# Battlecry: If your Armor changed this turn, draw 2 cards.
	# Reads player.armor_gained_this_turn (bumped in GainArmor.do, reset at
	# OWN_TURN_BEGIN in game.py).
	play = (Attr(CONTROLLER, "armor_gained_this_turn") >= 1) & (
		Draw(CONTROLLER) * 2
	)


class TTN_471:
	"""Furious Furnace"""

	# Magnetic (data). Also damages minions next to whomever this attacks.
	# Magnetic is set in data. The cleave effect fires as an on-attack
	# trigger: damage adjacent minions by this minion's Attack.
	events = Attack(SELF).on(CLEAVE)


##
# Spells


class TTN_470:
	"""Trial by Fire"""

	# Summon five 1/1 Val'kyr with Rush. When one dies, give the others +1/+1.
	play = Summon(CONTROLLER, "TTN_470t") * 5


class TTN_753:
	"""Bellowing Flames"""

	# Deal 5 damage to a minion.
	# Forge: Then deal 5 damage split among all enemy minions.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	forge_card = "TTN_753t"
	play = Hit(TARGET, 5)


class TTN_753t:
	"""Bellowing Flames"""

	# Forged version — Deal 5 damage to a minion, then 5 random hits to
	# enemy minions.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Hit(TARGET, 5), Hit(RANDOM_ENEMY_MINION, 1) * 5


class TTN_803:
	"""Smelt"""

	# Give a random minion in your hand +3/+3. Lose 3 Armor to do it again.
	play = _SmeltBuff(CONTROLLER)


##
# Weapons


class TTN_467:
	"""Craftsman's Hammer"""

	# After your hero attacks and kills a minion, gain 4 Armor.
	events = Attack(FRIENDLY_HERO, MINION).after(
		Dead(Attack.DEFENDER) & GainArmor(FRIENDLY_HERO, 4)
	)


##
# Titans


class TTN_415:
	"""Khaz'goroth"""

	# Titan. After this uses an ability, gain Immune this turn and attack
	# a random enemy minion.
	titan_ability_order = ["TTN_415t", "TTN_415t2", "TTN_415t3"]


# Titan ability sub-cards


class TTN_415t:
	"""Titanforge"""

	# Gain +2/+2. Draw a weapon.
	play = (
		Buff(SELF, "TTN_415te"),
		ForceDraw(RANDOM(FRIENDLY_DECK + WEAPON)),
		_KhazgorothAbilityPassive(SELF),
	)


class TTN_415t2:
	"""Tempering"""

	# Gain +5 Attack. Give your hero +5 Attack this turn.
	play = (
		Buff(SELF, "TTN_415t2e"),
		Buff(FRIENDLY_HERO, "TTN_415t2he"),
		_KhazgorothAbilityPassive(SELF),
	)


class TTN_415t3:
	"""Heart of Flame"""

	# Gain +5 Health. Give your hero 5 Armor.
	play = (
		Buff(SELF, "TTN_415t3e"),
		GainArmor(FRIENDLY_HERO, 5),
		_KhazgorothAbilityPassive(SELF),
	)


##
# Odyn — persistent rest-of-game armor-to-attack effect


class TTN_811:
	"""Odyn, Prime Designate"""

	# Battlecry: For the rest of the game, after your hero gains Armor,
	# they gain that much Attack for that turn.
	play = Buff(CONTROLLER, "TTN_811enc")


@custom_card
class TTN_811enc:
	# Odyn persistent enchant — lives on the controller.
	# Not in data — register as custom_card.
	tags = {
		GameTag.CARDNAME: "Odyn's Blessing",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = GainArmor(FRIENDLY_HERO).on(
		_OdynArmorAttackListener(SELF, GainArmor.AMOUNT)
	)


##
# Enchantments


class TTN_415e:
	# Khaz'goroth — Immune this turn (TEMPORARY tag in data clears it).
	tags = {GameTag.CANT_BE_DAMAGED: True, enums.TEMPORARY: 1}


class TTN_415te:
	# Titanforge +2/+2.
	tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TTN_415t2e:
	# Tempering +5 Attack on Khaz'goroth itself.
	tags = {GameTag.ATK: 5}


@custom_card
class TTN_415t2he:
	# Tempering +5 Attack on the hero (TEMPORARY, this turn only).
	# Not in data — register as custom_card.
	tags = {
		GameTag.CARDNAME: "Tempering",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 5,
		enums.TEMPORARY: 1,
	}


@custom_card
class TTN_415t3e:
	# Heart of Flame +5 Health on Khaz'goroth itself.
	# Not in data — register as custom_card.
	tags = {
		GameTag.CARDNAME: "Heart of Flame",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.HEALTH: 5,
	}


class TTN_468e:
	# Steam Guardian — -1 cost to a Fire spell in hand.
	tags = {GameTag.COST: -1}


@custom_card
class TTN_470te:
	# Trial by Fire Val'kyr deathrattle buff — +1/+1 to surviving Val'kyrs.
	# Not in data — register as custom_card.
	tags = {
		GameTag.CARDNAME: "Champion's Bond",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 1,
		GameTag.HEALTH: 1,
	}


class TTN_803e:
	# Smelt buff — +3/+3 to a minion in hand.
	tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


@custom_card
class TTN_811e:
	# Odyn attack buff — temporary Attack equal to armor gained.
	# atk is supplied at Buff() time (atk=amount kwarg).
	# TAG_ONE_TURN_EFFECT: True causes end_turn_cleanup to remove this buff.
	tags = {
		GameTag.CARDNAME: "Odyn's Blessing",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.TAG_ONE_TURN_EFFECT: True,
	}


##
# Tokens


class TTN_470t:
	"""Val'kyr Champion"""

	# 1/1 Val'kyr with Rush summoned by Trial by Fire. When this dies,
	# give the other Val'kyrs +1/+1.
	# Rush set in data.
	deathrattle = _TrialByFireDeathrattle(SELF)
