from ..utils import *


##
# Custom LazyNum


class _SpellSchoolCount(LazyNum):
	"""Lazily evaluate to the number of distinct spell schools the source's
	controller has cast this game (len of spells_cast_by_school dict)."""

	def evaluate(self, source):
		return self.num(len(source.controller.spells_cast_by_school))


##
# Custom actions


class _DiscoveryOfMagic(TargetedAction):
	"""Discovery of Magic — Discover a spell from a school you haven't cast
	this game. Builds a pool of collectible spells whose spell_school is NOT
	already in controller.spells_cast_by_school, then opens a Discover."""

	TARGET = ActionArg()

	def do(self, source, target):
		from fireplace import cards as _cards

		ctrl = source.controller
		cast_schools = set(ctrl.spells_cast_by_school.keys())
		pool = [
			cid
			for cid, c in _cards.db.items()
			if c.collectible
			and c.type == CardType.SPELL
			and c.spell_school is not None
			and int(c.spell_school) != 0
			and int(c.spell_school) not in cast_schools
		]
		if not pool:
			# Fall back to any collectible spell when all schools have been cast.
			pool = [
				cid
				for cid, c in _cards.db.items()
				if c.collectible and c.type == CardType.SPELL
			]
		if not pool:
			return
		source.game.cheat_action(
			source,
			[Discover(ctrl, RandomID(*pool)).then(Give(ctrl, Discover.CARD))],
		)


class _InquisitiveCreationHit(TargetedAction):
	"""Inquisitive Creation battlecry — deal N damage to ALL enemy minions,
	where N = number of distinct spell schools cast this game."""

	TARGET = ActionArg()

	def do(self, source, target):
		n = len(source.controller.spells_cast_by_school)
		if n <= 0:
			return
		source.game.cheat_action(source, [Hit(ENEMY_MINIONS, n)])


_VORTEX_VARIANTS = [
	"TTN_480t",   # Divine Shield
	"TTN_480t1",  # Taunt
	"TTN_480t2",  # Rush
	"TTN_480t3",  # Windfury
	"TTN_480t4",  # Stealth
	"TTN_480t5",  # Poisonous
	"TTN_480t6",  # Lifesteal
	"TTN_480t7",  # Reborn
]


class _ElementalInspirationSummon(TargetedAction):
	"""Elemental Inspiration — summon a 4/5 Primordial Vortex with a random
	bonus effect for each distinct spell school the controller has cast this
	game. Each Vortex independently picks from 8 keyword variants in data."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		n = len(ctrl.spells_cast_by_school)
		for _ in range(n):
			variant = source.game.random.choice(_VORTEX_VARIANTS)
			source.game.cheat_action(source, [Summon(ctrl, variant)])


class _UnchainedGladiatorDraw(TargetedAction):
	"""Unchained Gladiator battlecry — draw 1 card, then draw 1 more for each
	Elemental played last turn (player.elemental_played_last_turn counter)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		draws = 1 + getattr(ctrl, "elemental_played_last_turn", 0)
		for _ in range(draws):
			source.game.cheat_action(source, [Draw(ctrl)])


class _AquaArchivistDiscount(TargetedAction):
	"""Aqua Archivist — mark controller with _next_elemental_discount = 2 so
	the next Elemental played will cost 2 less. The engine does not yet have
	a built-in hook for per-elemental cost discounts, so this sets a custom
	attribute for future expansion.
	# TODO: wire into Play.do or use a cost_mod enchantment on the next
	# Elemental played."""

	TARGET = ActionArg()

	def do(self, source, target):
		target._next_elemental_discount += 2


##
# Spells


class TTN_085:
	"""Wisdom of Norgannon"""

	# Draw 2 cards. Costs (1) less for each different spell school you've
	# cast this game.
	play = Draw(CONTROLLER) * 2
	cost_mod = -_SpellSchoolCount()


class TTN_476:
	"""Discovery of Magic"""

	# Discover a spell from a spell school you haven't cast this game
	# (from any class).
	play = _DiscoveryOfMagic(CONTROLLER)


class TTN_477:
	"""Molten Rune"""

	# Deal 3 damage. Get a random spell. Forge: This casts twice.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = Hit(TARGET, 3), Give(CONTROLLER, RandomSpell())
	forge_card = "TTN_477t1"


class TTN_477t1:
	"""Molten Rune"""

	# Forged: Deal 3 damage twice. Get a random spell twice.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 3),
		Give(CONTROLLER, RandomSpell()),
		Hit(TARGET, 3),
		Give(CONTROLLER, RandomSpell()),
	)


class TTN_480:
	"""Elemental Inspiration"""

	# Summon a 4/5 Vortex with a random bonus effect for each spell school
	# you have cast this game. TTN_480t is "Primordial Vortex" (4/5 Divine
	# Shield) in data. The "random bonus effect" is not implemented.
	# TODO: give each summoned Vortex a distinct random bonus effect.
	play = _ElementalInspirationSummon(CONTROLLER)


##
# Minions


class TTN_071(SpellSchoolCountCardtextMixin):
	"""Sif"""

	# Spell Damage +@ (Improved by each spell school you've cast this game!)
	# Dynamic aura: Spell Damage = number of distinct schools in spells_cast_by_school.
	update = Refresh(
		SELF,
		{
			GameTag.SPELLPOWER: lambda self, i: len(
				self.controller.spells_cast_by_school
			)
		},
	)


class _NorgannonProgenitorsPower(TargetedAction):
	"""Progenitor's Power — deal (3 * 2^idx) damage to all enemies, where idx
	is Norgannon's _titan_ability_index at fire time (0 / 1 / 2)."""

	TARGET = ActionArg()

	def do(self, source, target):
		mult = 2 ** getattr(source, "_titan_ability_index", 0)
		source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 3 * mult)])


class _NorgannonAncientKnowledge(TargetedAction):
	"""Ancient Knowledge — stamp +N cost on each card in the opponent's hand
	(N = 2^idx). The cost-up persists indefinitely (cleanup at end of opp's
	next turn would need per-player event wiring; accepted approximation)."""

	TARGET = ActionArg()

	def do(self, source, target):
		mult = 2 ** getattr(source, "_titan_ability_index", 0)
		opp = source.controller.opponent
		for card in list(opp.hand):
			for _ in range(mult):
				source.game.cheat_action(source, [Buff(card, "TTN_075t2e2")])


class _NorgannonUnlimitedPotential(TargetedAction):
	"""Unlimited Potential — cast (1 * 2^idx) random Mage Secrets."""

	TARGET = ActionArg()

	def do(self, source, target):
		mult = 2 ** getattr(source, "_titan_ability_index", 0)
		for _ in range(mult):
			source.game.cheat_action(
				source,
				[CastSpell(RandomSpell(card_class=CardClass.MAGE, secret=True))],
			)


class TTN_075:
	"""Norgannon"""

	# Titan. After this uses an ability, double the power of the other abilities.
	# Each sub-card reads source._titan_ability_index and multiplies by 2^idx.
	titan_ability_order = ["TTN_075t", "TTN_075t2", "TTN_075t3"]


class TTN_075t:
	"""Progenitor's Power"""

	# Deal @ damage to all enemies. (Base 3, multiplied by 2^ability_index.)
	play = _NorgannonProgenitorsPower(SELF)


class TTN_075t2:
	"""Ancient Knowledge"""

	# Enemy cards cost (@) more next turn. (Base 1, multiplied by 2^idx.)
	play = _NorgannonAncientKnowledge(SELF)


class TTN_075t2e:
	"""Ancient Knowledge"""

	# In-data aura enchantment on the opponent. While alive, raise the cost
	# of every card in the controller's (= opponent's) hand by 1.
	# Destroyed at the end of the owner's next turn.
	update = Refresh(FRIENDLY_HAND, {GameTag.COST: 1})
	events = OWN_TURN_END.on(Destroy(SELF))


class TTN_075t2e2:
	"""Ancient Knowledge Cost Increase"""

	# Per-card cost increase stamped by Ancient Knowledge. The enchant's
	# owner is the opponent (whose hand-card it sits on), so OWN_TURN_END
	# fires at the end of the opponent's NEXT turn — exactly the "next turn"
	# scope on the printed card.
	tags = {GameTag.COST: 1}
	events = OWN_TURN_END.on(Destroy(SELF))


class TTN_075t3:
	"""Unlimited Potential"""

	# Cast @ random Mage Secrets. (Base 1, multiplied by 2^ability_index.)
	play = _NorgannonUnlimitedPotential(SELF)


class TTN_077:
	"""Chill-o-matic"""

	# Magnetic. Freeze any character damaged by this minion.
	# TTN_077e is in data (no @custom_card needed).
	magnetic = MAGNETIC("TTN_077e")
	events = Damage(CHARACTER, None, SELF).on(Freeze(Damage.TARGET))


class TTN_077e:
	"""Chill-o-matic"""

	# Magnetic enchantment — Freeze tag applied via MAGNETIC("TTN_077e").
	tags = {GameTag.FREEZE: True}


class TTN_095:
	"""Aqua Archivist"""

	# Battlecry: The next Elemental you play costs (2) less.
	play = _AquaArchivistDiscount(CONTROLLER)


class TTN_475:
	"""Unchained Gladiator"""

	# Battlecry: Draw a card. Repeat for each Elemental you played last turn.
	play = _UnchainedGladiatorDraw(CONTROLLER)


class TTN_478(SpellSchoolCountCardtextMixin):
	"""Inquisitive Creation"""

	# Battlecry: Deal @ damage to all enemy minions. (Improved by each spell
	# school you've cast this game!)
	play = _InquisitiveCreationHit(SELF)


##
# Tokens


class TTN_480t:
	"""Primordial Vortex"""

	# 4/5 Divine Shield — all data-driven; no extra script needed.
	pass
