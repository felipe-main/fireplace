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


class _ElementalInspirationSummon(TargetedAction):
	"""Elemental Inspiration — summon a 4/5 Primordial Vortex (TTN_480t) for
	each distinct spell school the controller has cast this game. TTN_480t has
	Divine Shield per the data card."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		n = len(ctrl.spells_cast_by_school)
		for _ in range(n):
			source.game.cheat_action(source, [Summon(ctrl, "TTN_480t")])


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


class TTN_071:
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


class TTN_075:
	"""Norgannon"""

	# Titan. After this uses an ability, double the power of the other abilities.
	# TODO: Ability-power doubling on each use is not implemented; abilities
	# fire at their base values.
	titan_ability_order = ["TTN_075t", "TTN_075t2", "TTN_075t3"]


class TTN_075t:
	"""Progenitor's Power"""

	# Deal @ damage to all enemies. (Base 3, doubles each subsequent use — TODO.)
	# Approximation: always deals 3 to all enemies.
	play = Hit(ENEMY_CHARACTERS, 3)


class TTN_075t2:
	"""Ancient Knowledge"""

	# Enemy cards cost (1) more next turn. (Base 1, doubles per use — TODO.)
	# Approximation: stamp the in-data TTN_075t2e aura enchantment onto the
	# opponent controller. TTN_075t2e is an aura; TTN_075t2e2 is the per-card
	# cost enchantment. We implement the aura via Refresh and expire it at the
	# opponent's next turn-end.
	play = Buff(OPPONENT, "TTN_075t2e")


class TTN_075t2e:
	"""Ancient Knowledge"""

	# In-data aura enchantment on the opponent. While alive, raise the cost
	# of every card in the controller's (= opponent's) hand by 1.
	# Destroyed at the end of the owner's next turn.
	update = Refresh(FRIENDLY_HAND, {GameTag.COST: 1})
	events = OWN_TURN_END.on(Destroy(SELF))


class TTN_075t2e2:
	"""Ancient Knowledge Cost Increase"""

	# Per-card cost increase stamped when the aura fires.
	tags = {GameTag.COST: 1}


class TTN_075t3:
	"""Unlimited Potential"""

	# Cast 1 random Mage Secret. (Base 1, doubles per use — TODO.)
	# Approximation: cast 1 random Mage Secret.
	play = CastSpell(RandomSpell(card_class=CardClass.MAGE, secret=True))


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


class TTN_478:
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
