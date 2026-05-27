from ..utils import *
from .utils import _RemixRotate, _RemixFireVariant
from .hunter import _HollowHoundAdjacent


##
# Minions

class JAM_014:
	"""Backstage Bouncer"""

	# Taunt (data). Battlecry: Transform a friendly minion into a copy
	# of this. Use Morph to swap the target into JAM_014 (creates a new
	# JAM_014 instance in place).
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Morph(TARGET, "JAM_014")


##
# Spells

class JAM_013:
	"""Jam Session"""

	# Give a friendly minion +3/+3. Deal 1 damage to all other minions.
	# Overload: (1) is in data — Play.do handles the overload bump.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		Buff(TARGET, "JAM_013e"),
		Hit(ALL_MINIONS - TARGET, 1),
	)


JAM_013e = buff(atk=3, health=3)


##
# Weapons

class JAM_015:
	"""Remixed Tuning Fork"""

	# Gains an extra effect in your hand that changes each turn.
	# Base weapon has no equip effect; the rotated variant supplies it.
	class Hand:
		events = OWN_TURN_BEGIN.on(_RemixRotate(SELF))
	play = _RemixFireVariant(SELF)


class JAM_015t:
	"""Sharpened Tuning Fork"""
	# Battlecry: Gain +2 Attack. Stamp the equipped weapon (SELF would
	# be the base Remixed Tuning Fork) with +2 atk.
	play = Buff(SELF, "JAM_015te")


@custom_card
class JAM_015te:
	# Sharpened Tuning Fork's +2 attack enchant. Not in data; register
	# explicitly so Buff(SELF, "JAM_015te") doesn't KeyError.
	tags = {
		GameTag.CARDNAME: "Sharpened",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 2,
	}


class JAM_015t2:
	"""Reinforced Tuning Fork"""
	# Battlecry: Gain 5 Armor.
	play = GainArmor(FRIENDLY_HERO, 5)


class JAM_015t3:
	"""Curved Tuning Fork"""
	# Also damages minions adjacent to whomever your hero attacks.
	# Apply the adjacent-damage listener as an enchant on the weapon
	# (SELF) so it persists for the weapon's lifetime.
	play = Buff(SELF, "JAM_015t3e")


class JAM_015t4:
	"""Backup Tuning Fork"""
	# Battlecry: Discover a Taunt minion.
	play = DISCOVER(RandomMinion(custom_filter=lambda c: bool(c.tags.get(GameTag.TAUNT))))


@custom_card
class JAM_015t3e:
	# Curved Tuning Fork — while the weapon is equipped, hero attacks
	# also damage minions adjacent to the defender. Reuses the
	# adjacency helper from hunter.py (Hollow Hound).
	tags = {
		GameTag.CARDNAME: "Curved",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = Attack(FRIENDLY_HERO).after(
		_HollowHoundAdjacent(FRIENDLY_HERO, Attack.DEFENDER)
	)
