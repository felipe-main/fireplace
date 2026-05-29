"""Delve into Deepholm — Druid cards (WILD_WEST / Patch 28.4)."""

from ..utils import *


##
# Custom actions / helpers


class _CrystalClusterGain(TargetedAction):
	"""Crystal Cluster — Gain three empty Mana Crystals. Any of the three
	that can't fit (the controller is already at the 10-crystal cap)
	summon a 3/7 Elemental with Taunt (DEEP_028t) instead.

	We resolve each of the three crystals one at a time: if there is room
	(`max_mana < max_resources`) gain an empty crystal, otherwise summon
	one Crystal Crusher in its place."""

	TARGET = ActionArg()

	def do(self, source, target):
		for _ in range(3):
			if target.max_mana < target.max_resources:
				source.game.cheat_action(
					source, [GainMana(target, 1).then(SpendMana(target, 1))]
				)
			else:
				source.game.cheat_action(source, [Summon(target, "DEEP_028t")])


##
# Minions


class DEEP_027:
	"""Gloomstone Guardian"""

	# Taunt. Choose One - Discard 2 cards; or Destroy one of your Mana
	# Crystals. Forge: Do NEITHER.
	# Taunt is in data. Choose One picks one of the two sub-spells; Forge
	# morphs the card into DEEP_027t (vanilla Taunt) before any battlecry,
	# so a forged Guardian does neither effect.
	forge_card = "DEEP_027t"
	choose = ("DEEP_027a", "DEEP_027b")


class DEEP_027a:
	"""Splintered Form"""

	# Discard 2 cards.
	play = Discard(RANDOM(FRIENDLY_HAND) * 2)


class DEEP_027b:
	"""Mana Disintegration"""

	# Destroy one of your Mana Crystals.
	play = GainEmptyMana(CONTROLLER, -1)


class DEEP_027t:
	"""Gloomstone Guardian"""

	# Forged Taunt. Vanilla 4/6/8 Taunt (Taunt in data, no battlecry).


class DEEP_028t:
	"""Crystal Crusher"""

	# Taunt. Vanilla 3/7 Taunt Elemental (Taunt in data).


class DEEP_029:
	"""Trogg Gemtosser"""

	# Finale: Deal 1 damage to a random enemy for each of your Mana
	# Crystals.
	play = FINALE & Hit(RANDOM_ENEMY_CHARACTER, 1) * Attr(CONTROLLER, "max_mana")


##
# Spells


class DEEP_028:
	"""Crystal Cluster"""

	# Gain three empty Mana Crystals. Any that can't fit summon a 3/7
	# Elemental with Taunt.
	play = _CrystalClusterGain(CONTROLLER)
