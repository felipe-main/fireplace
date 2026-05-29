from ..utils import *


##
# Spells


class DEEP_021:
	"""Shadow Word: Steal"""

	# Return an enemy minion to YOUR hand.
	# Take control of the targeted enemy minion (so it becomes ours), then
	# bounce it: Bounce sends a minion to its *current* controller's hand,
	# and after Steal the current controller is us.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
	}
	play = Steal(TARGET), Bounce(TARGET)


class DEEP_025:
	"""Shattered Reflections"""

	# Choose a minion. Add a copy to your hand, deck, and battlefield.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Give(CONTROLLER, Copy(TARGET)),
		Shuffle(CONTROLLER, Copy(TARGET)),
		Summon(CONTROLLER, Copy(TARGET)),
	)


class DEEP_026:
	"""Pendant of Earth"""

	# Discover a minion from your deck. Gain Armor equal to its Cost.
	# Discover-from-deck follows the engine convention (core priest
	# CS3_028): a GenericChoice over up-to-3 distinct deck minions; the
	# chosen one moves to hand. Armor gained reads the chosen card's Cost.
	play = GenericChoice(
		CONTROLLER, DeDuplicate(RANDOM(FRIENDLY_DECK + MINION, 3))
	).then(GainArmor(FRIENDLY_HERO, COST(GenericChoice.CARD)))


##
# Minions


class DEEP_023:
	"""Hidden Gem"""

	# Stealth (data). At the end of your turn, restore #2 Health to all
	# friendly characters.
	events = OWN_TURN_END.on(Heal(FRIENDLY_CHARACTERS, 2))


class DEEP_024:
	"""Glowstone Gyreworm"""

	# Lifesteal (data). Quickdraw: Deal 5 damage.
	# Forge: Change Quickdraw to Battlecry (-> DEEP_024t).
	requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
	forge_card = "DEEP_024t"
	play = QUICKDRAW & Hit(TARGET, 5)


class DEEP_024t:
	"""Glowstone Gyreworm"""

	# Forged, Lifesteal (data). Battlecry: Deal 5 damage.
	requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
	play = Hit(TARGET, 5)
