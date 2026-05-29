from ..utils import *


##
# Custom actions

class _HagathaSlime(TargetedAction):
	"""Hagatha the Fabled — transform a drawn spell into a Fairy Tale
	Slime (TOY_504t) that remembers the underlying spell. The Slime's
	battlecry casts that stored spell. We morph the freshly-drawn spell
	in hand into the Slime token and stamp the original spell id onto
	the new minion entity via ``_fairy_tale_spell``."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target is None:
			return
		if isinstance(target, (list, tuple)):
			target = target[0] if target else None
		if target is None or target.type != CardType.SPELL:
			return
		ctrl = source.controller
		slime = ctrl.card("TOY_504t")
		slime._fairy_tale_spell = target.id
		source.game.cheat_action(source, [Morph(target, slime)])


class _FairyTaleSlimeCast(TargetedAction):
	"""Fairy Tale Slime battlecry — cast the spell it remembers."""

	TARGET = ActionArg()

	def do(self, source, target):
		spell_id = getattr(source, "_fairy_tale_spell", None)
		if not spell_id:
			return
		spell = source.controller.card(spell_id)
		source.game.cheat_action(source, [CastSpell(spell)])


##
# Spells

class TOY_046:
	"""Incredible Value"""

	# <b>Discover</b> a 4-Cost minion. Set its Attack and Health to 7.
	play = Discover(CONTROLLER, RandomMinion(cost=4)).then(
		Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "TOY_046e"))
	)


class TOY_046e:
	# Attack and Health set to 7.
	atk = SET(7)
	max_health = SET(7)


class TOY_500:
	"""Baking Soda Volcano"""

	# <b>Lifesteal</b>. Deal $10 damage randomly split among all minions.
	# <b>Overload:</b> (1)
	# (Lifesteal + Overload live in data; only the random-split damage is scripted.)
	play = Hit(RANDOM(ALL_MINIONS), 1) * SPELL_DAMAGE(10)


class TOY_506:
	"""Once Upon a Time..."""

	# Summon a random 3-Cost Beast, Dragon, Elemental, and Murloc.
	play = (
		Summon(CONTROLLER, RandomBeast(cost=3)),
		Summon(CONTROLLER, RandomDragon(cost=3)),
		Summon(CONTROLLER, RandomElemental(cost=3)),
		Summon(CONTROLLER, RandomMurloc(cost=3)),
	)


class TOY_508:
	"""Pop-Up Book"""

	# Deal $2 damage. Summon two 0/1 Frogs with <b>Taunt</b>.
	play = (
		Hit(RANDOM_ENEMY_CHARACTER, 2),
		Summon(CONTROLLER, "hexfrog") * 2,
	)


class TOY_877:
	"""Wish Upon a Star"""

	# Give +2/+3 to all minions in your hand, deck, and battlefield.
	play = Buff(
		FRIENDLY + (IN_DECK | IN_HAND | IN_PLAY) + MINION - DORMANT,
		"TOY_877e1",
	)


# +2/+3.
TOY_877e1 = buff(+2, +3)


##
# Location

class TOY_507:
	"""Fairy Tale Forest"""

	# [x]Draw a <b>Battlecry</b> minion. It costs (1) less.
	play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + BATTLECRY)).then(
		Buff(Draw.CARD, "TOY_507e")
	)


class TOY_507e:
	# Costs (1) less.
	tags = {GameTag.COST: -1}


##
# Minions

class _ShudderblockPrime(TargetedAction):
	"""Set the controller's next battlecry to trigger 3 times total (2 extra)
	and to be unable to damage the enemy hero. Consumed by the engine in
	Battlecry.do when the next battlecry minion is played."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.next_battlecry_extra = 2


class TOY_501:
	"""Shudderblock"""

	# [x]<b>Miniaturize</b> <b>Battlecry:</b> Your next <b>Battlecry</b>
	# triggers 3 times, but can't damage the enemy hero.
	# (Miniaturize Mini token auto-added by the engine. The 3x next-battlecry
	# boost + enemy-hero damage suppression is engine-backed via
	# Player.next_battlecry_extra, consumed in Battlecry.do.)
	play = _ShudderblockPrime(CONTROLLER)


class TOY_501t:
	"""Shudderblock"""

	# [x]<b>Mini</b> <b>Battlecry:</b> Your next <b>Battlecry</b> triggers
	# 3 times, but can't damage the enemy hero.
	play = _ShudderblockPrime(CONTROLLER)


class TOY_503:
	"""Shining Sentinel"""

	# <b>Taunt</b>, <b>Elusive</b> <b>Battlecry:</b> Summon a copy of this.
	# (Taunt + Elusive are data tags.)
	play = Summon(CONTROLLER, Copy(SELF))


class TOY_504:
	"""Hagatha the Fabled"""

	# [x]<b>Battlecry:</b> Draw 2 spells that cost (5) or more. Transform
	# them into Slimes that cast the spells.
	play = Draw(
		CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST >= 5))
	).then(_HagathaSlime(Draw.CARD)) * 2


class TOY_504t:
	"""Fairy Tale Slime"""

	# <b>Battlecry:</b> Cast {0}.
	play = _FairyTaleSlimeCast(SELF)


class TOY_513:
	"""Sand Art Elemental"""

	# [x]<b>Miniaturize</b> <b>Battlecry:</b> Give your hero +1 Attack and
	# <b>Windfury</b> this turn.
	play = Buff(FRIENDLY_HERO, "TOY_513e")


class TOY_513e:
	# +1 Attack and Windfury.
	tags = {GameTag.ATK: 1, GameTag.WINDFURY: True, enums.TEMPORARY: 1}


class TOY_513t:
	"""Sand Art Elemental"""

	# [x]<b>Mini</b> <b>Battlecry:</b> Give your hero +1 Attack and
	# <b>Windfury</b> this turn.
	play = Buff(FRIENDLY_HERO, "TOY_513e")
