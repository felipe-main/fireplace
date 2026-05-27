from ..utils import *
from .utils import _TrailingProgressCardtextMixin, _WeaponCounterCardtextMixin


##
# Custom actions / helpers


class _GoingDownSwingingAttackAll(TargetedAction):
	"""Going Down Swinging — after the +2 ATK/Immune buff lands, the
	controller's hero attacks each enemy minion in board order. We
	iterate manually because Attack(HERO, ENEMY_MINIONS) only resolves
	the first target — mid-cascade deaths are handled by the standard
	pipeline (the attack loop re-reads the field each iteration)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		hero = ctrl.hero
		# Snapshot the enemy minion ids; iterate the live field each
		# time in case the order shifts after a death.
		victims = list(ctrl.opponent.field)
		for v in victims:
			if v.zone != Zone.PLAY:
				continue
			source.game.cheat_action(source, [Attack(hero, v)])


class _SnakebiteCountDeaths(LazyNum):
	"""Snakebite — at battlecry resolution, evaluate to the number of
	minions that have died this turn on either side. Tracked via
	`Player.minions_killed_this_turn` on each controller; the printed
	wording is "for each minion that died this turn" (any side)."""

	def evaluate(self, source):
		ctrl = source.controller
		return int(self.base) * (
			ctrl.minions_killed_this_turn + ctrl.opponent.minions_killed_this_turn
		)


class _InstrumentSmasherEquipRandomDH(TargetedAction):
	"""Instrument Smasher — when your weapon is destroyed, equip a random
	Demon Hunter weapon. Random pick from collectible DH weapons; no-op
	if the pool is empty."""

	TARGET = ActionArg()

	def do(self, source, target):
		from .. import db
		pool = [
			cid for cid, c in db.items()
			if c.collectible
			and c.card_class == CardClass.DEMONHUNTER
			and c.type == CardType.WEAPON
		]
		if not pool:
			return
		cid = source.game.random.choice(pool)
		source.game.cheat_action(source, [Summon(target, cid)])


class _GlaivetarBumpOutcastCounter(TargetedAction):
	"""Glaivetar — bump the per-weapon "Outcasts played while equipped"
	counter. Plain attribute access on the weapon entity; the counter
	is initialised lazily (getattr default 0)."""

	TARGET = ActionArg()

	def do(self, source, target):
		# `source` is the weapon itself (Play.events fires from the
		# listening card as source). Bump on the weapon entity.
		n = getattr(source, "_outcasts_played_while_equipped", 0)
		source._outcasts_played_while_equipped = n + 1


class _GlaivetarDeathrattleDraw(TargetedAction):
	"""Glaivetar — Deathrattle: Draw @ cards, where @ is the per-weapon
	Outcast-played counter accumulated while equipped."""

	TARGET = ActionArg()

	def do(self, source, target):
		n = getattr(source, "_outcasts_played_while_equipped", 0)
		if n <= 0:
			return
		source.game.cheat_action(source, [Draw(target) * n])


##
# Minions


class ETC_026:
	"""Guitar Soloist"""

	# Battlecry: If you control no other minions, draw a spell, a minion,
	# and a weapon. SELF is on the field at battlecry resolution, so
	# "no other minions" gates on Count(FRIENDLY_MINIONS) == 1.
	play = (Count(FRIENDLY_MINIONS) == 1) & (
		ForceDraw(RANDOM(FRIENDLY_DECK + SPELL)),
		ForceDraw(RANDOM(FRIENDLY_DECK + MINION)),
		ForceDraw(RANDOM(FRIENDLY_DECK + WEAPON)),
	)


class ETC_398:
	"""Eye of Shadow"""

	# Your hero has Lifesteal. Aura: stamp LIFESTEAL on the friendly
	# hero while this minion is in play.
	update = Refresh(FRIENDLY_HERO, {GameTag.LIFESTEAL: True})


class ETC_399:
	"""Halveria Darkraven"""

	# Rush. After a friendly Rush minion attacks, give your minions +1
	# Attack. RUSH from data. Listener fires for any friendly minion
	# with RUSH (Halveria herself included).
	events = Attack(FRIENDLY_MINIONS + RUSH).after(
		Buff(FRIENDLY_MINIONS, "ETC_399e"),
	)


class ETC_399e:
	# In-data "Sorrowchord" — +1 Attack. ATK tag isn't parsed, so
	# declare here for the buff stamp.
	tags = {GameTag.ATK: 1}


class ETC_400:
	"""Instrument Smasher"""

	# Whenever your weapon is destroyed, equip a random Demon Hunter
	# weapon. Listen for friendly-weapon Death events (engine routes
	# the "weapon at 0 durability" path through the same pipeline).
	events = Death(FRIENDLY + WEAPON).on(
		_InstrumentSmasherEquipRandomDH(CONTROLLER),
	)


class ETC_410(_TrailingProgressCardtextMixin):
	"""Snakebite"""

	# Rush. Battlecry: Gain +1/+1 for each minion that died this turn.
	# RUSH in data. Stack ETC_410e once per dead minion (this turn,
	# both sides).
	play = Buff(SELF, "ETC_410e") * _SnakebiteCountDeaths()

	def cardtext_entity_0(self):
		ctrl = getattr(self, "controller", None)
		if ctrl is None:
			return "0"
		return str(
			(ctrl.minions_killed_this_turn or 0)
			+ (ctrl.opponent.minions_killed_this_turn or 0)
		)

	tags = {
		**_TrailingProgressCardtextMixin.tags,
		GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
	}


@custom_card
class ETC_410e:
	# Not in data. +1/+1 stack stamp.
	tags = {
		GameTag.CARDNAME: "Snakebite",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 1,
		GameTag.HEALTH: 1,
	}


##
# Spells


class ETC_200:
	"""Rush the Stage"""

	# Draw two Rush minions. They cost (1) less.
	# Two ForceDraws against the deck's Rush minion pool, each stamped
	# with the (1)-cost discount enchant (ETC_200e) via the .then()
	# callback (Draw.CARD references the freshly-drawn card entity).
	play = (
		ForceDraw(RANDOM(FRIENDLY_DECK + MINION + RUSH)).then(
			Buff(ForceDraw.TARGET, "ETC_200e"),
		),
		ForceDraw(RANDOM(FRIENDLY_DECK + MINION + RUSH)).then(
			Buff(ForceDraw.TARGET, "ETC_200e"),
		),
	)


class ETC_200e:
	# In-data buff "Rush the Stage" — Costs (1) less. COST tag isn't
	# parsed; declare here so pay_cost sees -1.
	tags = {GameTag.COST: -1}


class ETC_394:
	"""Taste of Chaos"""

	# Deal $2 damage to a minion. Finale: Discover a Fel spell.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Hit(TARGET, 2),
		FINALE & DISCOVER(RandomSpell(spell_school=SpellSchool.FEL)),
	)


class ETC_411:
	"""SECURITY!!"""

	# Summon two 1/1 Illidari with Rush. Outcast: Summon one more.
	# BT_036t (Illidari Initiate, 1/1 Rush) is the matching in-data token.
	# The engine replaces play with outcast when card.play_outcast is
	# True (Play.do battlecry branch), so the outcast script summons
	# all three at once.
	play = Summon(CONTROLLER, "BT_036t") * 2
	outcast = Summon(CONTROLLER, "BT_036t") * 3


class ETC_413:
	"""Going Down Swinging"""

	# Give your hero +2 Attack and Immune this turn, then attack each
	# enemy minion. +2/Immune stamped via ETC_413e (TAG_ONE_TURN_EFFECT
	# in data — auto-clears at end of turn). The cascading hero attack
	# rides the engine's Attack action against each enemy minion in
	# order; deaths mid-cascade are handled by the standard pipeline.
	play = (
		Buff(FRIENDLY_HERO, "ETC_413e"),
		_GoingDownSwingingAttackAll(CONTROLLER),
	)


class ETC_413e:
	# In-data "Swinging" — +2 Attack this turn + Immune. ATK + immune
	# tags not parsed; declare here. TAG_ONE_TURN_EFFECT in data auto-
	# clears at end of turn.
	tags = {
		GameTag.ATK: 2,
		GameTag.CANT_BE_DAMAGED: True,
		GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
	}


##
# Weapons


class ETC_405(_WeaponCounterCardtextMixin):
	"""Glaivetar"""

	# Deathrattle: Draw @ cards. (Play Outcast cards while equipped to
	# improve!) The per-weapon counter `_outcasts_played_while_equipped`
	# is bumped by the in-play Play(CONTROLLER, OUTCAST) listener (custom
	# action — pure side-effect, lives outside the events lambda twice-
	# evaluation trap).
	counter_attr = "_outcasts_played_while_equipped"
	events = Play(CONTROLLER, OUTCAST).after(
		_GlaivetarBumpOutcastCounter(SELF),
	)
	deathrattle = _GlaivetarDeathrattleDraw(CONTROLLER)
