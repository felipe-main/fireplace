from ..utils import *


##
# Custom actions


class _AuraCountdown(TargetedAction):
	"""Generic N-turn aura countdown helper. Call with the enchantment entity
	as TARGET. Decrements `_aura_turns_left` on the enchant and destroys it
	once the counter hits zero.

	Usage in an enchantment class:
	    events = OWN_TURN_END.on(_AuraCountdown(SELF))

	The enchantment must initialise `_aura_turns_left` in its apply()."""

	TARGET = ActionArg()

	def do(self, source, target):
		# `target` is SELF evaluated to the enchantment entity.
		enchant = target
		if enchant is None:
			return
		left = getattr(enchant, "_aura_turns_left", 0) - 1
		enchant._aura_turns_left = max(0, left)
		if left <= 0:
			enchant.game.cheat_action(enchant, [Destroy(enchant)])


class _NobleMiniBotBuff(TargetedAction):
	"""Noble Minibot on-attack buff: give a random minion in the
	controller's hand +1/+1."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		minions = [c for c in list(ctrl.hand) if c.type == CardType.MINION]
		if not minions:
			return
		picked = source.game.random.choice(minions)
		source.game.cheat_action(source, [Buff(picked, "TTN_852e2")])


class _TyrResurrect(TargetedAction):
	"""Tyr battlecry: resurrect a friendly Paladin minion with exactly 2, 3,
	and 4 Attack from the controller's graveyard. Picks a random qualifying
	minion for each attack value."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardClass as CC

		ctrl = source.controller
		dead = [
			c for c in list(ctrl.graveyard)
			if c.type == CardType.MINION
			and c.data.card_class in (CC.PALADIN, None)
		]
		for required_atk in (2, 3, 4):
			candidates = [c for c in dead if c.atk == required_atk]
			if not candidates:
				continue
			picked = source.game.random.choice(candidates)
			source.game.cheat_action(source, [Summon(ctrl, picked.id)])


class _TyrTearsResurrect(TargetedAction):
	"""Tyr's Tears: resurrect up to N different Paladin/Neutral minions from
	the controller's graveyard and set their stats to 2/2 via TTN_855e1.
	N is stored as a plain instance attribute (not an ActionArg)."""

	TARGET = ActionArg()

	def __init__(self, target, n):
		super().__init__(target)
		self._n = n

	def do(self, source, target):
		from hearthstone.enums import CardClass as CC

		ctrl = source.controller
		seen_ids = set()
		candidates = []
		for c in list(ctrl.graveyard):
			if c.type != CardType.MINION:
				continue
			if c.data.card_class not in (CC.PALADIN, CC.NEUTRAL, None):
				continue
			if c.id not in seen_ids:
				seen_ids.add(c.id)
				candidates.append(c)
		source.game.random.shuffle(candidates)
		for c in candidates[: self._n]:
			source.game.cheat_action(
				source,
				[
					Summon(ctrl, c.id).then(
						Buff(Summon.CARD, "TTN_855e1")
					)
				],
			)


class _EarthenGolemBuff(TargetedAction):
	"""Earthen Golem (TTN_900t) on-summon scaling: gain +2/+2 for each other
	TTN_900t summoned this game. Reads player.earthens_summoned_this_game
	(bumped in Summon.do); subtract 1 because counter includes this summon."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target is None:
			return
		ctrl = source.controller
		count = max(0, ctrl.earthens_summoned_this_game - 1)
		if count <= 0:
			return
		buff_amount = count * 2
		source.game.cheat_action(
			source,
			[Buff(target, "TTN_900e2", atk=buff_amount, max_health=buff_amount)],
		)


class _X21RepairbotReturn(TargetedAction):
	"""X-21 Repairbot deathrattle: attempt to return any Magnetized Mechs to
	the controller's hand by scanning the dead minion's buff list for buffs
	sourced from a Magnetic Mech entity.
	# TODO: implement precise Magnetic stack unbinding."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		seen = set()
		for enchant in list(getattr(source, "buffs", [])):
			enc_src = getattr(enchant, "source", None)
			if enc_src is None:
				continue
			if not hasattr(enc_src, "type") or enc_src.type != CardType.MINION:
				continue
			if not getattr(enc_src, "has_magnetic", False):
				continue
			if enc_src.id in seen:
				continue
			seen.add(enc_src.id)
			source.game.cheat_action(source, [Give(ctrl, enc_src.id)])


##
# Spells


class TTN_851:
	"""Resistance Aura"""

	# Your opponent's spells cost (1) more. Lasts 3 turns.
	# Stamps TTN_851e (an aura enchantment) onto the controller.
	play = Buff(CONTROLLER, "TTN_851e")


class TTN_851e:
	"""Resistance"""

	# Aura enchantment on controller: opponent's hand spells cost (1) more.
	# Counts down 3 turns via _AuraCountdown, then destroys itself.
	update = Refresh(ENEMY_HAND + SPELL, {GameTag.COST: 1})
	events = OWN_TURN_END.on(_AuraCountdown(SELF))

	def apply(self, target):
		self._aura_turns_left = 3


class TTN_851e2:
	"""Resisting"""

	# Per-card cost increase (stamped by the aura engine on opponent's cards).
	tags = {GameTag.COST: 1}


class TTN_853:
	"""Judge Unworthy"""

	# Set an enemy minion's Health to 1, then deal 1 damage to all enemies.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Buff(TARGET, "TTN_853e"),
		Hit(ENEMY_CHARACTERS, 1),
	)


class TTN_853e:
	"""Unworthy!"""

	# Sets the target's max_health to 1 (engine clamps current health down).
	max_health = SET(1)


class TTN_854:
	"""Inventor's Aura"""

	# Your Mechs cost (1) less. Lasts 2 turns.
	play = Buff(CONTROLLER, "TTN_854e")


class TTN_854e:
	"""Empowered Workshop"""

	# Aura: friendly Mechs in hand cost (1) less. Expires after 2 turn-ends.
	update = Refresh(FRIENDLY_HAND + MECH, {GameTag.COST: -1})
	events = OWN_TURN_END.on(_AuraCountdown(SELF))

	def apply(self, target):
		self._aura_turns_left = 2


class TTN_855t:
	"""Tyr's Tears"""

	# Resurrect 3 different Paladin minions. Set their stats to 2/2.
	# Forge: TTN_855 (resurrects 4).
	forge_card = "TTN_855"
	play = _TyrTearsResurrect(CONTROLLER, 3)


class TTN_855:
	"""Tyr's Tears"""

	# Forged: Resurrect 4 different Paladin minions. Set their stats to 2/2.
	play = _TyrTearsResurrect(CONTROLLER, 4)


class TTN_855e1:
	"""Tyrful"""

	# Set ATK and Health to 2 (applied after each resurrection).
	atk = SET(2)
	max_health = SET(2)


class TTN_908:
	"""Crusader Aura"""

	# Whenever a friendly minion attacks, give it +2/+1. Lasts 3 turns.
	play = Buff(CONTROLLER, "TTN_908e")


class TTN_908e:
	"""Crusader Aura"""

	# Aura enchantment: on any friendly minion attack, give it +2/+1.
	# Expires after 3 controller turn-ends.
	events = [
		Attack(FRIENDLY_MINIONS).on(Buff(Attack.ATTACKER, "TTN_908e2")),
		OWN_TURN_END.on(_AuraCountdown(SELF)),
	]

	def apply(self, target):
		self._aura_turns_left = 3


class TTN_908e2:
	"""To Battle!"""

	tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


##
# Minions


class TTN_852:
	"""Noble Minibot"""

	# Magnetic. After this attacks, give a random minion in your hand +1/+1.
	magnetic = MAGNETIC("TTN_852e")
	events = Attack(SELF).after(_NobleMiniBotBuff(SELF))


class TTN_852e:
	"""Noble Minibot"""

	# Magnetic enchantment — the attack-trigger buff fires from TTN_852's
	# events, not from this enchantment.
	tags = {}


class TTN_852e2:
	"""Mechanical Nobility"""

	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TTN_856:
	"""Disciple of Amitus"""

	# At the end of your turn, summon a 2/2 Earthen that gains +2/+2
	# for each other Earthen you've summoned this game.
	events = OWN_TURN_END.on(
		Summon(CONTROLLER, "TTN_900t").then(_EarthenGolemBuff(Summon.CARD))
	)


class TTN_857:
	"""Tyr"""

	# Battlecry: Resurrect a 2, 3, and 4-Attack Paladin minion.
	play = _TyrResurrect(CONTROLLER)


class TTN_858:
	"""Amitus, the Peacekeeper"""

	# Titan. Taunt. Your minions can't take more than 2 damage at a time.
	# Uses incoming_damage_max engine cap (Predamage.do reads it).
	titan_ability_order = ["TTN_858t1", "TTN_858t2", "TTN_858t3"]
	update = Refresh(FRIENDLY_MINIONS, {enums.INCOMING_DAMAGE_MAX: 2})


class TTN_858t1:
	"""Reinforced"""

	# Draw 2 minions. Set their Attack, Health, and Cost to 2.
	play = (
		ForceDraw(RANDOM(FRIENDLY_DECK + MINION)).then(
			MultiBuff(ForceDraw.TARGET, ["TTN_858t1e", "TTN_858t1e1"])
		)
	) * 2


class TTN_858t1e:
	"""Reinforcing"""

	# Set ATK and max_health to 2.
	atk = SET(2)
	max_health = SET(2)


class TTN_858t1e1:
	"""Reshaped"""

	# Set cost to 2; removed when the card enters play.
	cost = SET(2)
	events = REMOVED_IN_PLAY


class TTN_858t2:
	"""Empowered"""

	# Give your other minions +2/+2.
	play = Buff(FRIENDLY_MINIONS - SELF, "TTN_858t2e1")


class TTN_858t2e1:
	"""Washed Over"""

	tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TTN_858t3:
	"""Pacified"""

	# Set the Attack and Health of all enemy minions to 2.
	play = Buff(ENEMY_MINIONS, "TTN_858t3e")


class TTN_858t3e:
	"""Pacified"""

	atk = SET(2)
	max_health = SET(2)


class TTN_900:
	"""Stoneheart King"""

	# Deathrattle: Summon a 2/2 Earthen that gains +2/+2 for each other
	# Earthen you've summoned this game.
	deathrattle = Summon(CONTROLLER, "TTN_900t").then(
		_EarthenGolemBuff(Summon.CARD)
	)


class TTN_900t:
	"""Earthen Golem"""

	# After this is summoned, gain +2/+2 for each other Earthen summoned
	# this game. Triggered by TTN_856 / TTN_900 via _EarthenGolemBuff.
	# Also register a self-trigger here in case the token is summoned by
	# other means (e.g. recruit effects).
	events = Summon(CONTROLLER, SELF).on(_EarthenGolemBuff(Summon.CARD))


class TTN_900e1:
	"""Will of the Earthen"""

	# +1/+1 minor buff variant.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TTN_900e2:
	"""Will of the Earthen"""

	# Runtime +N/+N buff (atk and max_health passed at Buff call time).
	tags = {}


class TTN_906:
	"""X-21 Repairbot"""

	# Deathrattle: Return any Mechs Magnetized to this to your hand.
	# TODO: precise Magnetic stack unbinding not yet implemented.
	deathrattle = _X21RepairbotReturn(SELF)


class TTN_907:
	"""Astral Serpent"""

	# At the end of your turn, if this didn't attack, draw 2 cards.
	events = OWN_TURN_END.on(
		(Attr(SELF, "num_attacks") == 0) & Draw(CONTROLLER) * 2
	)
