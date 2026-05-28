from ..utils import *
from .utils import _RemixRotate, _RemixFireVariant


class _StarPowerCascade(TargetedAction):
	"""Star Power — deal 5 damage to a random enemy minion, then 4, 3,
	2, 1 (each pick is independently random, can repeat targets).
	A step with no alive enemy minions is silently skipped."""

	TARGET = ActionArg()

	def do(self, source, target):
		for dmg in (5, 4, 3, 2, 1):
			pool = ENEMY_MINIONS.eval(source.game, source)
			pool = [m for m in pool if m.zone == Zone.PLAY]
			if not pool:
				continue
			victim = source.game.random.choice(pool)
			source.game.cheat_action(source, [Hit(victim, dmg)])


class _CostumedSingerDrawSecret(TargetedAction):
	"""Costumed Singer — at OWN_TURN_END, draw a random Secret from
	the controller's deck. Uses ForceDraw so OWN_CARD_DRAWN listeners
	and the per-turn draw counter fire — the printed text says "draw",
	not "add", so the verb matters."""

	TARGET = ActionArg()

	def do(self, source, target):
		# `secret` is a Spell-only attribute; guard with getattr so a
		# non-spell card in the deck doesn't crash the filter.
		secrets = [c for c in target.deck if getattr(c, "secret", False)]
		if not secrets:
			return
		pick = source.game.random.choice(secrets)
		source.game.cheat_action(source, [ForceDraw(pick)])


##
# Minions

class JAM_000:
	"""Remixed Dispense-o-bot"""

	# Gains an extra effect in your hand that changes each turn.
	# Base card has no play effect; the rotated variant supplies it.
	class Hand:
		events = OWN_TURN_BEGIN.on(_RemixRotate(SELF))
	play = _RemixFireVariant(SELF)


class JAM_000t:
	"""Chilling Dispense-o-bot"""
	# Battlecry: Get two random Frost spells.
	play = Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.FROST)) * 2


class JAM_000t2:
	"""Merch Dispense-o-bot"""
	# Battlecry: Get two random Mechs.
	play = Give(CONTROLLER, RandomMinion(race=Race.MECHANICAL)) * 2


class JAM_000t3:
	"""Money Dispense-o-bot"""
	# Battlecry: Get two Coins.
	play = Give(CONTROLLER, "GAME_005") * 2


class JAM_000t4:
	"""Mystery Dispense-o-bot"""
	# Battlecry: Get two random Mage Secrets.
	play = Give(
		CONTROLLER,
		RandomSpell(card_class=CardClass.MAGE, secret=True),
	) * 2


class JAM_001:
	"""Costumed Singer"""

	# At the end of your turn, draw a Secret.
	events = OWN_TURN_END.on(_CostumedSingerDrawSecret(CONTROLLER))


##
# Spells

class JAM_002:
	"""Star Power"""

	# Deal 5 damage to a random enemy minion. Repeat this with 1 less
	# damage. Five independent random picks.
	play = _StarPowerCascade(CONTROLLER)
