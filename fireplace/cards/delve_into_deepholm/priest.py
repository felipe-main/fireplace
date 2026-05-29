from ..utils import *

from hearthstone.enums import CardType, Zone


class _PendantDiscover(TargetedAction):
	"""Pendant of Earth — a faithful "Discover from your deck": offer up to 3
	DISTINCT deck minions (as preview copies), then move the chosen card's
	real deck copy to hand while the unchosen candidates stay in the deck (a
	real Discover removes nothing it did not pick). The prior GenericChoice
	approach discarded the unchosen deck cards and could offer < 3 distinct
	minions."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		seen = set()
		distinct = []
		for c in ctrl.deck:
			if c.type == CardType.MINION and c.id not in seen:
				seen.add(c.id)
				distinct.append(c)
		if not distinct:
			return
		n = min(3, len(distinct))
		picks = source.game.random.sample(distinct, n)
		offered = [ctrl.card(c.id, source=source) for c in picks]
		choice = Choice(ctrl, offered).then(
			_PendantPick(Choice.PLAYER, Choice.CARDS, Choice.CARD)
		)
		source.game.queue_actions(source, [choice])


class _PendantPick(TargetedAction):
	"""Choose-callback: move a real deck card matching the picked id to hand
	(others stay in the deck), then gain Armor equal to its Cost."""

	PLAYER = ActionArg()
	CARDS = ActionArg()
	CARD = ActionArg()

	def do(self, source, player, cards, picked):
		if isinstance(picked, list):
			picked = picked[0] if picked else None
		if picked is None:
			return
		real = next((c for c in player.deck if c.id == picked.id), None)
		if real is not None:
			real.zone = Zone.HAND
		source.game.cheat_action(source, [GainArmor(player.hero, picked.cost)])


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
	# Offers up to 3 distinct deck minions; the chosen card moves to hand and
	# the unchosen candidates remain in the deck. Armor = the chosen Cost.
	play = _PendantDiscover(CONTROLLER)


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
