from ..utils import *
from .utils import _RemixRotate, _RemixFireVariant


##
# Minions

class JAM_016:
	"""Abyssal Bassist"""

	# Taunt, Lifesteal (both in data).
	# Costs (2) less for each weapon you've equipped this game.
	# Reads Player.weapons_equipped_this_game (set in Player.__init__,
	# bumped by Weapon._set_zone on each equip).
	cost_mod = Attr(CONTROLLER, "weapons_equipped_this_game") * -2


##
# Spells (Remixed Rhapsody is here — DH spell)

class JAM_018:
	"""Remixed Rhapsody"""

	# Gains an extra effect in your hand that changes each turn.
	# The base spell has no printed effect of its own; the rotating
	# variant supplies the full play action.
	class Hand:
		events = OWN_TURN_BEGIN.on(_RemixRotate(SELF))
	play = _RemixFireVariant(SELF)


##
# Remixed Rhapsody variants — each shipped as its own data card with
# the full Battlecry-equivalent script.

class JAM_018t:
	"""Angsty Rhapsody"""
	# Deal 3 damage to all minions. Draw 3 cards.
	play = Hit(ALL_MINIONS, 3), Draw(CONTROLLER) * 3


class JAM_018t2:
	"""Resounding Rhapsody"""
	# Deal 3 damage to all minions, twice.
	play = Hit(ALL_MINIONS, 3), Hit(ALL_MINIONS, 3)


class JAM_018t3:
	"""Emotional Rhapsody"""
	# Deal 3 damage to all minions. Give your hero +5 Attack this turn.
	play = Hit(ALL_MINIONS, 3), Buff(FRIENDLY_HERO, "JAM_018t3e")


class JAM_018t3e:
	# +5 Attack this turn — exists in data with TAG_ONE_TURN_EFFECT but
	# no ATK tag, so we declare ATK and the end-of-turn self-destroy
	# here (TAG_ONE_TURN_EFFECT is a no-op in our engine).
	tags = {GameTag.ATK: 5}
	events = OWN_TURN_END.on(Destroy(SELF))


class JAM_018t4:
	"""Wailing Rhapsody"""
	# Deal 3 damage to all minions. Summon a 5/5 Demon.
	# JAM_018t5 (Wailing Fanatic) is the 5/5 Demon token in data.
	play = Hit(ALL_MINIONS, 3), Summon(CONTROLLER, "JAM_018t5")


class JAM_018t5:
	"""Wailing Fanatic"""
	# 5/5 Demon token. Stats in data; no script.


##
# Through Fel and Flames — multi-class (Warrior + DH); placed here on
# the DH side so the related Outcast/Finale-heavy DH file stays the
# home for fel spells. Listed under Warrior pkg-import too — same
# class, harmless.

class JAM_017:
	"""Through Fel and Flames"""

	# Give a minion Rush. Finale: And +1/+1.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		GiveRush(TARGET),
		FINALE & Buff(TARGET, "JAM_017e"),
	)


JAM_017e = buff(atk=1, health=1)
