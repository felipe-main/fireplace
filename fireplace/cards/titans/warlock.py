from ..utils import *


##
# Custom actions


class _MortalEradicationHit(TargetedAction):
	"""Mortal Eradication — deal 5 damage split randomly among all enemy
	minions (1 per random hit, 5 times). Each minion death restores 2
	Health to the friendly hero."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		for _ in range(5):
			if not opp.field:
				break
			source.game.cheat_action(
				source, [Hit(RANDOM_ENEMY_MINION, 1)]
			)
		kills = opp.minions_killed_this_turn
		if kills > 0:
			source.game.cheat_action(
				source, [Heal(FRIENDLY_HERO, 2 * kills)]
			)


class _WingWeldingDiscard(TargetedAction):
	"""Wing Welding — discard the highest-cost card in hand, then deal
	damage equal to its cost to ALL minions."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not ctrl.hand:
			return
		highest = max(ctrl.hand, key=lambda c: c.cost or 0)
		cost = max(0, highest.cost or 0)
		source.game.cheat_action(source, [Discard(highest)])
		if cost > 0:
			source.game.cheat_action(source, [Hit(ALL_MINIONS, cost)])


class _ForgeOfWillsSummon(TargetedAction):
	"""Forge of Wills — Summon a Giant (10/10 Demon) and set its stats
	to match the targeted friendly minion's current stats."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not target or target.zone != Zone.PLAY:
			return
		target_atk = target.atk or 0
		target_health = target.max_health or 1
		source.game.cheat_action(source, [
			Summon(ctrl, "TTN_465t").then(
				Buff(Summon.CARD, "TTN_465te",
				     atk=target_atk, max_health=target_health),
				GiveRush(Summon.CARD),
			)
		])


class _SargerasPortal(TargetedAction):
	"""Sargeras battlecry — give the controller a persistent enchant that
	summons two 3/2 Imps at the end of every turn for the rest of the
	game."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		source.game.cheat_action(source, [Buff(ctrl, "TTN_960e")])


class _LokenDeckDiscover(TargetedAction):
	"""Loken, Jailer of Yogg-Saron — Discover a minion from your deck,
	then summon a Tentacle with that minion's stats and Taunt."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		minions = [c for c in ctrl.deck if c.type == CardType.MINION]
		if not minions:
			return
		ids = list({c.id for c in minions})
		discover = Discover(ctrl, RandomID(*ids)).then(
			_LokenSummonTentacle(ctrl, Discover.CARD),
		)
		source.game.queue_actions(source, [discover])


class _LokenSummonTentacle(TargetedAction):
	"""Loken — once the player picks a minion from the Discover window,
	summon a Tentacle token (TTN_960t) with the chosen minion's stats
	and Taunt."""

	TARGET = ActionArg()
	CARD = CardArg()

	def do(self, source, target, card):
		if isinstance(card, list):
			card = card[0] if card else None
		if card is None:
			return
		ctrl = source.controller
		atk = getattr(card, "atk", 0) or 0
		hp = getattr(card, "max_health", 1) or 1
		source.game.cheat_action(source, [
			Summon(ctrl, "TTN_960t").then(
				Buff(Summon.CARD, "TTN_487te", atk=atk, max_health=hp),
				Taunt(Summon.CARD),
			)
		])


class _DiscardASpellSummonImps(TargetedAction):
	"""Disciple of Sargeras base — discard a random spell from hand
	(if any), then summon two 3/2 Imps (TTN_960t6)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		spells = [c for c in ctrl.hand if c.type == CardType.SPELL]
		if not spells:
			return
		pick = source.game.random.choice(spells)
		source.game.cheat_action(source, [Discard(pick)])
		source.game.cheat_action(source, [Summon(ctrl, "TTN_960t6") * 2])


class _DiscardASpellSummonImpsForged(TargetedAction):
	"""Disciple of Sargeras forged — discard a random spell, summon two
	3/4 Imps with Taunt (base 3/2 Imp + +2 Health and Taunt)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		spells = [c for c in ctrl.hand if c.type == CardType.SPELL]
		if not spells:
			return
		pick = source.game.random.choice(spells)
		source.game.cheat_action(source, [Discard(pick)])
		for _ in range(2):
			source.game.cheat_action(source, [
				Summon(ctrl, "TTN_960t6").then(
					Buff(Summon.CARD, "TTN_490te"),
					Taunt(Summon.CARD),
				)
			])


class _LegionDemonBuff(TargetedAction):
	"""Sargeras ability TTN_960t4 — Legion Invasion!: future Demons the
	controller summons get +2 Health and Taunt.  Stamps a persistent
	controller enchant that applies the aura."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		source.game.cheat_action(source, [Buff(ctrl, "TTN_960t4e")])


##
# Minions


class TTN_456:
	"""Thornveil Tentacle"""

	# Lifesteal (data). Battlecry: Deal 2 damage to a random enemy minion.
	play = Hit(RANDOM_ENEMY_MINION, 2)


class _ImprisonedHorrorCostMod(LazyNum):
	"""Imprisoned Horror — cost (1) less for each damage taken on your
	turns this game.  The engine tracks damage_taken_on_opponents_turn
	(reset each turn) but not damage taken on OWN turns.  We approximate
	by reading total hero damage (hero.damage = total hp lost) and
	subtracting the opponent-turn contribution (which resets per turn so
	is lost).  A proper "damage taken on own turns" counter would require
	a per-turn reset hook; for now, use total hero damage as a proxy."""

	def evaluate(self, source):
		ctrl = source.controller
		hero = ctrl.hero
		return -(hero.damage or 0)


class TTN_462:
	"""Imprisoned Horror"""

	# Costs (1) less for each damage you've taken on your turns this game.
	# Approximation: costs (1) less for each hero damage taken total.
	# TODO: track "damage taken on own turns" separately for accuracy.
	cost_mod = _ImprisonedHorrorCostMod()


class TTN_465:
	"""Forge of Wills"""

	# Location. Choose a friendly minion. Summon a Giant with its stats
	# and Rush.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	activate = _ForgeOfWillsSummon(TARGET)


class TTN_487:
	"""Loken, Jailer of Yogg-Saron"""

	# Battlecry: Discover a minion from your deck. Summon a Tentacle
	# with its stats and Taunt.
	play = _LokenDeckDiscover(SELF)


class TTN_490:
	"""Disciple of Sargeras"""

	# Battlecry: Discard a spell to summon two 3/2 Imps.
	# Forge: Give them +2 Health and Taunt.
	forge_card = "TTN_490t"
	play = _DiscardASpellSummonImps(SELF)


class TTN_490t:
	"""Disciple of Sargeras"""

	# Forged — Discard a spell to summon two 3/4 Imps with Taunt.
	play = _DiscardASpellSummonImpsForged(SELF)


##
# Spells


class TTN_460:
	"""Mortal Eradication"""

	# Deal 5 damage randomly split among all enemy minions. Restore 2
	# Health to your hero for each killed.
	play = _MortalEradicationHit(SELF)


class TTN_463:
	"""Wing Welding"""

	# Discard your highest Cost card. Deal damage equal to its Cost to
	# all minions.
	play = _WingWeldingDiscard(SELF)


class TTN_486:
	"""Monstrous Form"""

	# Give a friendly minion +3/+3 until your next turn.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "TTN_486e")


class TTN_932:
	"""Chaotic Consumption"""

	# Destroy a friendly minion to destroy an enemy minion.
	# Full two-target selection (pick friendly to sacrifice + enemy to
	# destroy) isn't supported cleanly by the engine in a single targeting
	# requirement.  Approximate: target the enemy; destroy that target and
	# a random friendly minion as the "cost".  REQ_MINIMUM_TOTAL_MINIONS
	# ensures the spell can only be played when there's at least one
	# minion on each side.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_MINIMUM_TOTAL_MINIONS: 2,
	}
	play = (
		Destroy(RANDOM_FRIENDLY_MINION),
		Destroy(TARGET),
	)


##
# Titans


class TTN_960:
	"""Sargeras, the Destroyer"""

	# Titan. Battlecry: Open a portal that summons two 3/2 Imps each turn.
	titan_ability_order = ["TTN_960t2", "TTN_960t3", "TTN_960t4"]
	play = _SargerasPortal(CONTROLLER)


# Titan ability sub-cards


class TTN_960t2:
	"""To the Void!"""

	# Send all other minions into the Twisting Nether (destroy all minions
	# except Sargeras himself).
	play = Destroy(ALL_MINIONS - SELF)


class TTN_960t3:
	"""Inferno!"""

	# Summon two 6/6 Infernals.
	play = Summon(CONTROLLER, "TTN_960t5") * 2


class TTN_960t4:
	"""Legion Invasion!"""

	# Future Demons have +2 Health and Taunt.
	play = _LegionDemonBuff(CONTROLLER)


##
# Enchantments


class TTN_486e:
	# Monstrous Form — +3/+3 until your next turn.  TAG_ONE_TURN_EFFECT
	# set in data auto-clears at turn start.
	tags = {GameTag.ATK: 3, GameTag.HEALTH: 3, enums.TEMPORARY: 1}


@custom_card
class TTN_487te:
	# Loken tentacle stat-override enchant (custom, not in data).
	tags = {
		GameTag.CARDNAME: "Yogg's Jailer",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class TTN_465te:
	# Forge of Wills Giant stat-override enchant (custom, not in data).
	tags = {
		GameTag.CARDNAME: "Forge of Wills",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class TTN_490te:
	# Forged Imp buff — +2 Health and Taunt set via data if present, or
	# via this enchant's tag dict.
	tags = {
		GameTag.CARDNAME: "Touched by Sargeras",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.HEALTH: 2,
	}


@custom_card
class TTN_960e:
	# Sargeras portal enchant — summons two 3/2 Imps at end of each turn.
	tags = {
		GameTag.CARDNAME: "Portal to the Nether",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = OWN_TURN_END.on(
		Summon(CONTROLLER, "TTN_960t6"),
		Summon(CONTROLLER, "TTN_960t6"),
	)


@custom_card
class TTN_960t4e:
	# Legion Invasion aura — while this enchant lives on the controller,
	# future Demons get +2 Health and Taunt.
	tags = {
		GameTag.CARDNAME: "Legion Invasion",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	update = Refresh(FRIENDLY_MINIONS + DEMON, {GameTag.HEALTH: 2, GameTag.TAUNT: True})


##
# Tokens


class TTN_465t:
	"""Nathrezim Giant"""

	# Giant with stats set at summon time. No standalone script needed.


class TTN_960t:
	"""Tentacle of Yogg-Saron"""

	# Tentacle token summoned by Loken. Stats set at summon time.


class TTN_960t5:
	"""Infernal"""

	# 6/6 Infernal summonedby Sargeras' Inferno! ability.


class TTN_960t6:
	"""3/2 Imp"""

	# 3/2 Imp summoned by Sargeras' portal and Disciple of Sargeras.
