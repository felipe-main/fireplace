from ..utils import *
from .utils import _HarmonicSwap


##
# Custom actions


class _DiscoMaulBuff(TargetedAction):
	"""Disco Maul deathrattle — give a random friendly minion +N/+N where
	N is the per-weapon `_disco_minions_played` counter (bumped each time
	the controller plays a minion while Disco Maul is equipped)."""

	TARGET = ActionArg()

	def do(self, source, target):
		n = getattr(source, "_disco_minions_played", 0)
		if n <= 0:
			return
		ctrl = source.controller
		friendly = [m for m in ctrl.field if m.type == CardType.MINION]
		if not friendly:
			return
		picked = source.game.random.choice(friendly)
		source.game.cheat_action(
			source, [Buff(picked, "ETC_317e", atk=n, max_health=n)]
		)


class _KangorSwapWithHand(TargetedAction):
	"""Kangor deathrattle — Swap this minion with a minion from your
	hand and give it Lifesteal. Implementation: pull the SAME card
	entity (not a fresh copy) from hand into PLAY via Summon-route,
	preserving any in-hand buffs / cost mods. Then stamp Lifesteal.

	"Swap" in printed HS lingo here means the hand minion comes out
	while Kangor's body dies; Kangor isn't returned to hand (his
	deathrattle has already triggered)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		minions = [c for c in list(ctrl.hand) if c.type == CardType.MINION]
		if not minions:
			return
		picked = source.game.random.choice(minions)
		# Route the picked hand entity through Summon so on-summon
		# triggers fire and the entity (not a fresh copy) lands on
		# the board with its in-hand buffs intact.
		source.game.cheat_action(source, [Summon(ctrl, picked)])
		from hearthstone.enums import Zone
		if picked.zone == Zone.PLAY:
			source.game.cheat_action(
				source, [Buff(picked, "ETC_329e_lifesteal")]
			)


class _HarmonicDiscoBuff(TargetedAction):
	"""Harmonic Disco — discover a 5-cost minion, then summon it with
	+1/+1. We delegate the discover via a chained then() and inspect the
	freshly given card to summon a fresh copy with the buff."""

	TARGET = ActionArg()

	def do(self, source, target):
		picker = RandomMinion(cost=5)
		source.game.cheat_action(
			source,
			[Discover(target, picker).then(_HarmonicDiscoFinish(target, Discover.CARD))],
		)


class _HarmonicDiscoAlt(TargetedAction):
	"""Harmonic Disco — alt branch (Swaps each turn): summon a random
	5-cost minion directly with no Discover and no +1/+1 buff."""

	TARGET = ActionArg()

	def do(self, source, target):
		pick = RandomMinion(cost=5).evaluate(source)
		if not pick:
			return
		cid = pick[0] if isinstance(pick, list) else pick
		source.game.cheat_action(source, [Summon(target, cid)])


class _HarmonicDiscoFinish(TargetedAction):
	"""Harmonic Disco — once a 5-cost minion has been picked from the
	discover UI, summon it (instead of giving) and apply +1/+1."""

	TARGET = ActionArg()
	CARD = ActionArg()

	def do(self, source, target, card):
		if isinstance(card, list):
			card = card[0] if card else None
		if card is None:
			return
		card_id = card.id if hasattr(card, "id") else card
		source.game.cheat_action(
			source,
			[Summon(target, card_id).then(Buff(Summon.CARD, "ETC_506e"))],
		)


##
# Spells


class ETC_318:
	"""Boogie Down"""

	# Summon two 1-Cost minions from your deck. Finale: Give them Taunt.
	# Pick two distinct 1-cost minions; Finale gates the taunt buff on
	# both summoned minions (Summon.CARD references the most-recently
	# summoned minion).
	play = (
		Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST == 1))).then(
			FINALE & Taunt(Summon.CARD)
		),
		Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST == 1))).then(
			FINALE & Taunt(Summon.CARD)
		),
	)


class ETC_320:
	"""Spotlight"""

	# Tradeable. Convert a friendly Divine Shield minion into a 5/5
	# Elemental. (Living Spotlight token.)
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Morph(TARGET, "ETC_320t")


class ETC_330:
	"""Starlight Groove"""

	# Give your hero Divine Shield. For the rest of the game, playing a
	# Holy spell refreshes it.
	# We arm `controller.starlight_groove_active` and wire the refresh
	# via a buff on the controller carrying a Play(HOLY_SPELL) listener.
	play = (
		GiveDivineShield(FRIENDLY_HERO),
		Buff(CONTROLLER, "ETC_330e_aura"),
	)


@custom_card
class ETC_330e_aura:
	"""Starlight Groove"""

	tags = {
		GameTag.CARDNAME: "Starlight Groove",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = Play(CONTROLLER, SPELL + HOLY_SPELL).after(
		GiveDivineShield(FRIENDLY_HERO)
	)


class ETC_506:
	"""Harmonic Disco"""

	# Printed base: Discover a 5-Cost minion. Summon it with +1/+1.
	# Alt branch (Swaps each turn): summon a random 5-cost minion outright
	# (no discover UI, no +1/+1 buff).
	_HARMONIC_BASE = (_HarmonicDiscoBuff(CONTROLLER),)
	_HARMONIC_ALT = (_HarmonicDiscoAlt(CONTROLLER),)
	play = _HarmonicSwap(CONTROLLER)


##
# Minions


class ETC_321:
	"""Annoy-o-Troupe"""

	# Taunt, Divine Shield. Deathrattle: Summon three 1/2 Mechs with
	# Taunt and Divine Shield.
	deathrattle = Summon(CONTROLLER, "ETC_321t") * 3


@custom_card
class ETC_321t:
	"""Annoy-o-Tron Jr."""

	tags = {
		GameTag.CARDNAME: "Annoy-o-Tron Jr.",
		GameTag.CARDTYPE: CardType.MINION,
		GameTag.ATK: 1,
		GameTag.HEALTH: 2,
		GameTag.TAUNT: True,
		GameTag.DIVINE_SHIELD: True,
		GameTag.CARDRACE: Race.MECHANICAL,
	}


class ETC_324:
	"""Jitterbug"""

	# Divine Shield. After a friendly character loses Divine Shield,
	# draw a card.
	# The engine's DS-strip path goes through LosesDivineShield (called
	# by Damage.do when a shielded target takes a hit). Listen on that
	# action for any friendly character.
	events = LosesDivineShield(FRIENDLY + CHARACTER).after(Draw(CONTROLLER))


class ETC_328:
	"""Lead Dancer"""

	# Deathrattle: Summon a minion from your deck with less Attack than
	# this minion.
	deathrattle = Summon(
		CONTROLLER,
		RANDOM(FRIENDLY_DECK + MINION + (ATK < Attr(SELF, GameTag.ATK))),
	)


class ETC_329:
	"""Kangor, Dancing King"""

	# Lifesteal. Deathrattle: Swap this with a minion from your hand and
	# give it Lifesteal.
	deathrattle = _KangorSwapWithHand(SELF)


class ETC_337:
	"""Funkfin"""

	# Divine Shield. Your minions with Divine Shield have +2 Attack.
	# Aura: any friendly minion with DS gets +2 atk. Applies to SELF too
	# (printed text says "Your minions" — Funkfin counts).
	update = Refresh(FRIENDLY_MINIONS + DIVINE_SHIELD, buff="ETC_337e")


class ETC_337e:
	"""Funky"""

	# In-data enchant "Funky" — +2 Attack while Divine Shielded
	# (Funkfin's aura). ATK tag not parsed; declare here.
	tags = {GameTag.ATK: 2}


##
# Weapons


class _IncDiscoCounter(TargetedAction):
	"""Disco Maul — bump the per-weapon `_disco_minions_played` counter."""

	TARGET = ActionArg()

	def do(self, source, target):
		target._disco_minions_played = (
			getattr(target, "_disco_minions_played", 0) + 1
		)


class ETC_317:
	"""Disco Maul"""

	# Deathrattle: Give a random friendly minion +@/+@.
	# Counter `_disco_minions_played` is bumped on every minion Play
	# while this weapon is equipped on the controller's hero. On
	# weapon-destroy, the deathrattle reads the counter and buffs.
	events = Play(CONTROLLER, MINION).after(_IncDiscoCounter(SELF))
	deathrattle = _DiscoMaulBuff(SELF)


##
# Enchantments


class ETC_317e:
	# In-data buff "Power of Disco" — +N/+N stamped by Disco Maul's
	# deathrattle (amount supplied at runtime via Buff kwargs).
	tags = {}


@custom_card
class ETC_329e_lifesteal:
	"""Kangor, Dancing King"""

	tags = {
		GameTag.CARDNAME: "Kangor, Dancing King",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.LIFESTEAL: True,
	}


@custom_card
class ETC_506e:
	"""Harmonic Groove"""

	tags = {
		GameTag.CARDNAME: "Harmonic Groove",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 1,
		GameTag.HEALTH: 1,
	}
