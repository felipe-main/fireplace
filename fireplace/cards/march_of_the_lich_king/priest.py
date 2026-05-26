from ..utils import *


##
# Custom actions


class _DiedSinceLastTurn(LazyNum):
	"""Evaluator-style helper: returns 1 if any friendly Undead in the
	controller's graveyard was killed after the controller's last turn
	began, else 0. We expose it as a LazyNum so it composes with the
	`&` / cost_mod operators just like `Attr(...)` / `Count(...)`.

	"After your last turn" semantics: graveyard scan for any minion with
	`turn_killed > player.last_turn`. The graveyard contains card objects
	whose `turn_killed` is populated by card.py's death pipeline; the
	first turn of the game has `last_turn is None`, which we treat as -1
	(so anything that has died at all counts).
	"""

	def evaluate(self, source):
		from hearthstone.enums import Race, CardType

		ctrl = source.controller
		last = ctrl.last_turn if ctrl.last_turn is not None else -1
		for c in ctrl.graveyard:
			if c.type != CardType.MINION:
				continue
			if getattr(c, "turn_killed", -1) <= last:
				continue
			if Race.UNDEAD in (c.race, getattr(c, "secondary_race", None)):
				return 1
		return 0


def _friendly_undead_died_since_last_turn(ctrl):
	"""Shared helper for action-side checks (Bonecaller / SW:Undeath /
	High Cultist Basaleph). Returns the list of card objects in the
	controller's graveyard that are Undead minions killed after the
	controller's previous turn began."""
	from hearthstone.enums import Race, CardType

	last = ctrl.last_turn if ctrl.last_turn is not None else -1
	out = []
	for c in ctrl.graveyard:
		if c.type != CardType.MINION:
			continue
		if getattr(c, "turn_killed", -1) <= last:
			continue
		if Race.UNDEAD in (c.race, getattr(c, "secondary_race", None)):
			out.append(c)
	return out


class _BonecallerResurrect(TargetedAction):
	"""Bonecaller deathrattle — pick a random friendly Undead from the
	controller's graveyard that died this game (any turn) and summon a
	fresh copy. Mirrors the "Resurrect" idiom but restricted to UNDEAD."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import Race, CardType

		ctrl = source.controller
		pool = [
			c for c in ctrl.graveyard
			if c.type == CardType.MINION
			and Race.UNDEAD in (c.race, getattr(c, "secondary_race", None))
		]
		if not pool:
			return
		picked = source.game.random.choice(pool)
		source.game.cheat_action(source, [Summon(ctrl, picked.id)])


class _SWUndeathExtra(TargetedAction):
	"""Shadow Word: Undeath — if a friendly Undead died after the
	controller's last turn, fire an extra 2 damage to all enemies. The
	base 2-to-all is queued separately in the `play` script; this action
	only handles the conditional second hit."""

	TARGET = ActionArg()

	def do(self, source, target):
		if not _friendly_undead_died_since_last_turn(target):
			return
		source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 2)])


class _HighCultistBasalephResurrect(TargetedAction):
	"""High Cultist Basaleph — summon a fresh copy of every friendly
	Undead that died after the controller's last turn. Loops the
	graveyard scan (no de-duplication: a minion that died twice this
	window comes back twice, matching the printed effect)."""

	TARGET = ActionArg()

	def do(self, source, target):
		dead = _friendly_undead_died_since_last_turn(target)
		for c in dead:
			source.game.cheat_action(source, [Summon(target, c.id)])


class _HauntingNightmareStamp(TargetedAction):
	"""Haunting Nightmare deathrattle — stamp the RLK_822e "Cold Sweat"
	enchant onto a random card in the controller's hand. The enchant's
	`Hand.events` listens for that card's Play and summons a 3/3 Soldier
	(RLK_822t). If the controller's hand is empty, nothing happens
	(matches printed behaviour: nothing to haunt)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if not ctrl.hand:
			return
		picked = source.game.random.choice(list(ctrl.hand))
		source.game.cheat_action(source, [Buff(picked, "RLK_822e")])


class _MindEaterCopyDeck(TargetedAction):
	"""Mind Eater deathrattle — add a copy of a random card from the
	opponent's deck to the controller's hand. If the opponent's deck is
	empty, nothing happens."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		if not opp.deck:
			return
		picked = source.game.random.choice(list(opp.deck))
		source.game.cheat_action(
			source, [Give(source.controller, picked.id)]
		)


##
# Spells


class RLK_812:
	"""Animate Dead"""

	# Resurrect a friendly minion that costs (3) or less.
	# Copy() preserves printed/base stats (standard resurrect idiom);
	# pool restricted to dead friendly minions with cost <= 3.
	play = Summon(
		CONTROLLER,
		Copy(RANDOM(FRIENDLY + KILLED + MINION + (COST <= 3))),
	)


class RLK_815:
	"""Shadow Word: Undeath"""

	# Deal $2 damage to all enemies. If a friendly Undead died after your
	# last turn, deal $2 more.
	play = Hit(ENEMY_CHARACTERS, 2), _SWUndeathExtra(CONTROLLER)


class RLK_823:
	"""Undying Allies"""

	# After you play an Undead this turn, give it Reborn.
	# Stamp the in-data "Grave Calling" enchant (RLK_823e) on the
	# controller; the enchant carries the trigger via its own
	# `events` and self-destructs at end of turn.
	play = Buff(CONTROLLER, "RLK_823e")


class RLK_829:
	"""Grave Digging"""

	# Draw 2 cards. Costs (1) if a friendly Undead died after your last
	# turn.
	# cost_mod uses the _DiedSinceLastTurn LazyNum: it returns 1 when the
	# condition holds, 0 otherwise. Printed cost is 4, so subtract 3 when
	# the flag fires to land at 1.
	play = Draw(CONTROLLER) * 2
	cost_mod = -(_DiedSinceLastTurn() * 3)


##
# Minions


class RLK_813:
	"""Bonecaller"""

	# Taunt. Deathrattle: Resurrect a friendly Undead that died this game.
	deathrattle = _BonecallerResurrect(SELF)


class RLK_814:
	"""Crystalsmith Cultist"""

	# Battlecry: If you're holding a Shadow spell, gain +1/+1.
	# Mirrors the HOLDING_DRAGON pattern: find any SHADOW_SPELL in the
	# controller's hand (excluding SELF, which is a minion anyway) and
	# gate the buff on it.
	play = (
		Find(FRIENDLY_HAND + SHADOW_SPELL) & Buff(SELF, "RLK_814e")
	)


class RLK_816:
	"""Sister Svalna"""

	# Battlecry: Permanently add a Vision of Darkness to your hand.
	# "Permanently" is a flavour annotation in the printed text — the
	# data card's effect is just to give one copy of RLK_816t3. The
	# engine doesn't model the "this card stays in hand forever" tag
	# differently from a normal Give.
	play = Give(CONTROLLER, "RLK_816t3")


class RLK_816t3:
	"""Vision of Darkness"""

	# Discover a Shadow spell. (This stays in your hand.)
	# The "stays in your hand" clause is cosmetic for fireplace — the
	# discovered spell is added to hand via DISCOVER, and Vision of
	# Darkness itself is consumed when cast (standard spell behaviour).
	play = DISCOVER(RandomSpell(spell_school=SpellSchool.SHADOW))


class RLK_822:
	"""Haunting Nightmare"""

	# Deathrattle: Haunt a card in your hand. When you play it, summon a
	# 3/3 Soldier.
	deathrattle = _HauntingNightmareStamp(SELF)


class RLK_832:
	"""High Cultist Basaleph"""

	# Battlecry: Resurrect all friendly Undead that died after your last
	# turn.
	play = _HighCultistBasalephResurrect(CONTROLLER)


class RLK_845:
	"""Mind Eater"""

	# Deathrattle: Add a copy of a card in your opponent's deck to your
	# hand.
	deathrattle = _MindEaterCopyDeck(SELF)


##
# Enchantments


class RLK_814e:
	# In-data buff "Shadow Flow" — +1/+1. ATK/HEALTH are not parsed from
	# data on this card, so declare them explicitly (mirrors RLK_916e).
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class RLK_822e:
	# In-data buff "Cold Sweat" — stamped on a random hand card by
	# Haunting Nightmare's deathrattle. When the haunted card is played,
	# summon a 3/3 Haunted Soldier (RLK_822t) for the controller, then
	# self-destruct so the trigger fires exactly once.

	class Hand:
		events = Play(OWNER).on(
			Summon(CONTROLLER, "RLK_822t"), Destroy(SELF)
		)


class RLK_822t:
	"""Haunted Soldier"""


class RLK_823e:
	# In-data buff "Grave Calling" — stamped on the controller by
	# Undying Allies. After the controller plays an Undead this turn,
	# give that Undead Reborn. Self-destructs at end of turn (the in-data
	# card carries TAG_ONE_TURN_EFFECT, but we also wire OWN_TURN_END to
	# be safe in case the parsed flag isn't honoured by the buff path).
	events = [
		Play(CONTROLLER, MINION + UNDEAD).after(GiveReborn(Play.CARD)),
		OWN_TURN_END.on(Destroy(SELF)),
	]
