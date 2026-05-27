from ..utils import *
from .utils import _HarmonicSwap


##
# Custom actions


class _BreakdanceClone(TargetedAction):
	"""Breakdance — return the targeted friendly minion to hand, then
	summon a Breakdancer (ETC_076t) whose ATK/HEALTH match the returned
	minion's *current* stats. Rush is baked into the data card; the
	clone is otherwise a fresh minion (no enchants carry over)."""

	TARGET = ActionArg()

	def do(self, source, target):
		atk = target.atk
		hp = target.health
		ctrl = source.controller
		source.game.cheat_action(source, [Bounce(target)])
		source.game.cheat_action(
			source,
			[SummonCustomMinion(ctrl, "ETC_076t", 1, atk, hp)],
		)


class _MixtapeDiscoverOpponentPlayed(TargetedAction):
	"""Mixtape — Discover a copy of a card the opponent has played this
	game. If the opponent has played nothing yet, no discover opens
	(printed text reads "a card your opponent played")."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		played_ids = [c.id for c in opp.cards_played_this_game]
		if not played_ids:
			return
		source.game.cheat_action(source, [DISCOVER(RandomID(*played_ids))])


class _RecordScratcherBump(TargetedAction):
	"""Bumps the equipped Record Scratcher's per-weapon Combo counter
	whenever the controller plays a Combo card while the weapon is
	equipped. `source` is the weapon (Play.on listener owner)."""

	TARGET = ActionArg()

	def do(self, source, target):
		source.combo_played_while_equipped = (
			getattr(source, "combo_played_while_equipped", 0) + 1
		)


class _RecordScratcherDeathrattle(TargetedAction):
	"""Record Scratcher deathrattle — refresh as many mana crystals as
	the controller played Combo cards while the weapon was equipped.
	Counter lives on the weapon entity itself."""

	TARGET = ActionArg()

	def do(self, source, target):
		n = getattr(target, "combo_played_while_equipped", 0)
		if n <= 0:
			return
		source.game.cheat_action(source, [FillMana(source.controller, n)])


##
# Minions


class ETC_072:
	"""Beatboxer"""

	# Combo: Deal 4 damage randomly split among all enemies.
	combo = Hit(RANDOM(ENEMY_CHARACTERS - DEAD), 1) * 4


class ETC_073:
	"""Rhyme Spinner"""

	# Rush. Combo: Gain +1/+1 for each other Combo card you've played
	# this game. Rush is in data; only the combo buff is scripted.
	# `-SELF` filters this card out of the count — by the time the
	# combo block resolves, Rhyme Spinner has already been logged into
	# cards_played_this_game (Play.do appends BEFORE the combo block
	# runs, per actions.py).
	combo = Buff(SELF, "ETC_073e")


@custom_card
class ETC_073e:
	tags = {
		GameTag.CARDNAME: "Rhyme Spinner",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	atk = lambda self, i: i + self._n
	max_health = lambda self, i: i + self._n

	def apply(self, target):
		# Snapshot at combo-resolution time. Exclude `target` (the
		# Rhyme Spinner we're buffing) — by the time the combo block
		# runs, the spinner has already been appended to
		# cards_played_this_game by Play.do, so the printed "each
		# OTHER Combo card" filter requires excluding it.
		ctrl = target.controller
		self._n = len([
			c for c in ctrl.cards_played_this_game
			if c.has_combo and c is not target
		])


class ETC_077:
	"""Disc Jockey"""

	# Combo: Add a random Combo card to your hand.
	combo = Give(CONTROLLER, RandomCollectible(combo=True))


class ETC_078:
	"""MC Blingtron"""

	# Battlecry: Both players equip 1/2 Microphones. Your opponent's
	# increases all damage they take by 1!
	# Friendly: ETC_078t2 Golden Microphone (vanilla 1/2 weapon).
	# Enemy:    ETC_078t  Broken Microphone (1/2; +1 incoming damage
	#           adjustment on the equipping hero).
	play = (
		Summon(CONTROLLER, "ETC_078t2"),
		Summon(OPPONENT, "ETC_078t"),
	)


##
# Spells


class ETC_074:
	"""Mixtape"""

	# Discover a copy of a card your opponent played this game.
	play = _MixtapeDiscoverOpponentPlayed(CONTROLLER)


class ETC_075:
	"""Mic Drop"""

	# Draw 2 cards. Finale: Give your weapon +2 Attack.
	play = (
		Draw(CONTROLLER) * 2,
		FINALE & Buff(FRIENDLY_WEAPON, "ETC_075e"),
	)


class ETC_076:
	"""Breakdance"""

	# Return a friendly minion to your hand. Summon a Dancer with its
	# stats and Rush.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
	}
	play = _BreakdanceClone(TARGET)


class ETC_079:
	"""Bounce Around (ft. Garona)"""

	# Return all friendly minions to your hand. They cost (1) this turn.
	play = Bounce(FRIENDLY_MINIONS).then(
		Buff(Bounce.TARGET, "ETC_079e")
	)


class ETC_717:
	"""Harmonic Hip Hop"""

	# Printed base: Deal $1 damage. Give your weapon +3 Attack.
	# Alt branch (Swaps each turn): deal $2 damage to the target instead
	# (no weapon buff). Drives off the controller's
	# `_harmonic_phase_swapped` flag.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
	}
	_HARMONIC_BASE = (
		Hit(TARGET, 1),
		Buff(FRIENDLY_WEAPON, "ETC_717e"),
	)
	_HARMONIC_ALT = (Hit(TARGET, 2),)
	play = _HarmonicSwap(TARGET)


##
# Weapons


class ETC_518:
	"""Record Scratcher"""

	# Deathrattle: Refresh @ Mana Crystals. (Play Combo cards while
	# equipped to improve!) Per-weapon counter bumped on each Combo
	# card the controller plays while equipped; counter is consumed by
	# the deathrattle which restores that many mana crystals.
	combo_played_while_equipped = 0
	events = Play(CONTROLLER, COMBO - SELF).on(_RecordScratcherBump(SELF))
	deathrattle = _RecordScratcherDeathrattle(SELF)


##
# Enchantments (in-data — declare stat tags where missing)


class ETC_075e:
	# In-data "OHHHHH!!!!" — +2 Attack to the equipped weapon.
	tags = {GameTag.ATK: 2}


class ETC_079e:
	# In-data "Bouncing Around" — Costs (1) this turn. Cost-set buff
	# that expires when the card is played (REMOVED_IN_PLAY hook).
	# Use the `cost = SET(1)` class-attr idiom (DMF_071e pattern) —
	# SET() in a tags dict crashes per CLAUDE.md.
	cost = SET(1)
	events = REMOVED_IN_PLAY


class ETC_717e:
	# In-data weapon buff — +3 Attack (stat tag not in parsed data).
	tags = {GameTag.ATK: 3}


##
# Tokens


class ETC_076t:
	"""Breakdancer"""

	# 1/1 Rush by default — stat-stamped via SummonCustomMinion when
	# spawned by Breakdance. Rush is in data; no script needed.


class ETC_078t:
	"""Broken Microphone"""

	# Your hero takes 1 additional damage from all sources. While this
	# weapon is equipped, the equipping player's hero gains +1 incoming
	# damage adjustment (mirrors Voidtouched Attendant SW_446e pattern).
	update = Refresh(FRIENDLY_HERO, {GameTag.INCOMING_DAMAGE_ADJUSTMENT: 1})


class ETC_078t2:
	"""Golden Microphone"""

	# Vanilla 1/2 weapon. No script.
