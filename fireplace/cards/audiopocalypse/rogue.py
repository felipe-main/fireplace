from ..utils import *


##
# Minions

class JAM_019:
	"""Rhythmdancer Risa"""

	# Rush (data). After your hero attacks, return this to your hand
	# and set its Cost to (1). Listener on FRIENDLY_HERO Attack
	# (.after) → Bounce SELF + apply set-cost-to-1 enchant.
	events = Attack(FRIENDLY_HERO).after(
		Bounce(SELF).then(Buff(SELF, "JAM_019e")),
	)


class JAM_020:
	"""Tough Crowd"""

	# Outcast: Return a minion to its owner's hand. Outcast trigger
	# is auto-gated by Play.do via card.play_outcast — only fires when
	# the card is played from the leftmost or rightmost hand slot.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	outcast = Bounce(TARGET)


class JAM_021:
	"""One Hit Wonder"""

	# Rush (data). Combo: Gain Poisonous.
	combo = GivePoisonous(SELF)


##
# Enchantments

@custom_card
class JAM_019e:
	# Rhythmdancer Risa — cost-set enchant. Risa prints 4 mana; apply
	# COST: -3 to land at 1. Engine clamps the additive cost-mod path
	# at 0, so we hard-code the offset rather than using SET().
	tags = {
		GameTag.CARDNAME: "Rhythm",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -3,
	}
