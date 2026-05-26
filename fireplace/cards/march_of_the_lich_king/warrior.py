from ..utils import *


##
# Custom actions


class _DrawTauntMinion(TargetedAction):
	"""Walk the controller's deck for the first Taunt minion (top-down)
	and draw it. If none exists, no-op (matches Hearthstone: "Draw a
	Taunt minion" with no Taunt in deck simply does nothing)."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardType
		pick = None
		# Iterate top-of-deck-first. Deck order in fireplace is index 0 = bottom,
		# last = top; mirror existing patterns (RANDOM(FRIENDLY_DECK + …)).
		for card in reversed(target.deck):
			if card.type == CardType.MINION and card.taunt:
				pick = card
				break
		if pick is None:
			return
		source.game.cheat_action(source, [ForceDraw(pick)])
		# Stash the drawn card so the parent script can buff it.
		target._last_stand_drawn = pick


class _LastStandDoubleStats(TargetedAction):
	"""Double the stats of the card just drawn by _DrawTauntMinion via
	the RLK_601e enchant (which reads the source card's atk/health at
	apply-time and adds them as a stat buff)."""

	TARGET = ActionArg()

	def do(self, source, target):
		card = getattr(target, "_last_stand_drawn", None)
		if card is None:
			return
		target._last_stand_drawn = None
		source.game.cheat_action(source, [Buff(card, "RLK_601e")])


class _AsvedonCopyLastSpell(TargetedAction):
	"""Asvedon — cast a copy of the last spell the opponent played this
	game. Reads opponent.cards_played_this_game and walks back for the
	most recent SPELL entry."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardType
		opp = target.opponent
		last_spell = None
		for c in reversed(opp.cards_played_this_game):
			if c.type == CardType.SPELL:
				last_spell = c
				break
		if last_spell is None:
			return
		source.game.cheat_action(source, [CastSpell(last_spell.id)])


class _ThoribeloreRevive(TargetedAction):
	"""Awaken Thori'belore (its Phoenix Egg form) when the controller
	casts a Fire spell, decrementing the per-card revives counter. The
	counter starts at 2; once it hits 0 the egg can't revive anymore
	(future fire spells are no-ops on this listener since the gate fails).
	"""

	TARGET = ActionArg()

	def do(self, source, target):
		left = getattr(target, "_thoribelore_revives_left", 2)
		if left <= 0:
			return
		target._thoribelore_revives_left = left - 1
		source.game.cheat_action(source, [Awaken(target)])


##
# Spells


class RLK_600:
	"""Sunfire Smithing"""

	# Equip a 4/2 Sword. Give a random minion in your hand +4/+2.
	play = (
		Summon(CONTROLLER, "RLK_600t"),
		Buff(RANDOM(FRIENDLY_HAND + MINION), "RLK_600e"),
	)


class RLK_600t:
	"""Flamberge"""

	# 4/2 weapon — stats come from data.


class RLK_600e:
	# In-data buff Overheated; +4/+2 not parsed from data.
	tags = {GameTag.ATK: 4, GameTag.HEALTH: 2}


class RLK_601:
	"""Last Stand"""

	# Draw a Taunt minion. Double its stats.
	play = _DrawTauntMinion(CONTROLLER), _LastStandDoubleStats(CONTROLLER)


@custom_card
class RLK_601e:
	# In-data Stalwart Stand says "Stats Doubled" but the actual atk/health
	# values aren't parsed; capture the target's atk/health at apply-time
	# and add them as a flat buff (doubling).
	tags = {
		GameTag.CARDNAME: "Stalwart Stand",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	atk = lambda self, i: i + self._xatk
	max_health = lambda self, i: i + self._xhealth

	def apply(self, target):
		self._xatk = target.atk
		# Use max_health rather than current health so the doubling is on
		# the printed/total HP, matching "Double its stats".
		self._xhealth = target.max_health


class RLK_603:
	"""Light of the Phoenix"""

	# Draw 2 cards. Costs (1) less for each damaged friendly character.
	cost_mod = -Count(FRIENDLY_CHARACTERS + DAMAGED)
	play = Draw(CONTROLLER) * 2


class RLK_605:
	"""Blazing Power"""

	# Give a minion +1/+1. Repeat for each damaged friendly character.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "RLK_605e") * (Count(FRIENDLY_CHARACTERS + DAMAGED) + 1)


class RLK_605e:
	# In-data buff "On Fire!" — +1/+1 not parsed from data.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class RLK_960:
	"""Embers of Strength"""

	# Summon two 1/2 Guards with Taunt. Manathirst (6): Give them +1/+2.
	play = (
		Summon(CONTROLLER, "RLK_960t") * 2,
		MANATHIRST(6) & Buff(FRIENDLY_MINIONS + ID("RLK_960t"), "RLK_960e"),
	)


class RLK_960t:
	"""Emberbound Guard"""

	# 1/2 Taunt — taunt is tagged in data.


class RLK_960e:
	# In-data buff "Empowered Embers" — +1/+2 not parsed from data.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


##
# Minions


class RLK_602:
	"""Silverfury Stalwart"""

	# Taunt, Rush. Can't be targeted by spells or Hero Powers.
	# Taunt/Rush are in data; the two CANT_BE_TARGETED tags aren't, so set
	# them as base tags on the script.
	tags = {
		GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
		GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
	}


class RLK_604:
	"""Thori'belore"""

	# Rush. Deathrattle: Go Dormant. Cast a Fire spell to revive
	# Thori'belore! (Revives 2 times.)
	# Modelled by summoning the Phoenix Egg (RLK_604t) in dormant form
	# carrying a 2-charge revive counter that listens for friendly Fire
	# spells while dormant.
	deathrattle = Summon(CONTROLLER, "RLK_604t").then(
		SetTag(Summon.CARD, GameTag.DORMANT)
	)


class RLK_604t:
	"""Phoenix Egg"""

	# Dormant carrier for Thori'belore. While dormant, casting a Fire spell
	# revives (awakens into) Thori'belore — up to 2 times. The counter
	# lives on the dormant entity itself (_thoribelore_revives_left).
	dormant_events = Play(CONTROLLER, FIRE_SPELL).on(
		_ThoribeloreRevive(SELF)
	)


class RLK_607:
	"""Disruptive Spellbreaker"""

	# At the end of your turn, your opponent discards a spell.
	events = OWN_TURN_END.on(Discard(RANDOM(ENEMY_HAND + SPELL)))


class RLK_608:
	"""Asvedon, the Grandshield"""

	# Battlecry: Cast a copy of the last spell your opponent played.
	play = _AsvedonCopyLastSpell(CONTROLLER)


class RLK_609:
	"""Sunfury Champion"""

	# After you cast a Fire spell, deal 1 damage to all minions.
	events = Play(CONTROLLER, FIRE_SPELL).after(Hit(ALL_MINIONS, 1))
