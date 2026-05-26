from ..utils import *

from .utils import ManathirstCardtextMixin


##
# Shared evaluators


class _UndeadDiedAfterLastTurn(LazyNum):
	"""Returns 1 if any friendly Undead died after the controller's last
	OWN_TURN_END, else 0. Reads the engine-managed
	`_undead_deaths_in_window` tracker."""

	def evaluate(self, source):
		return 1 if source.controller._undead_deaths_in_window else 0


##
# Custom actions


class _BrittleskinZombieDeathrattle(TargetedAction):
	"""Brittleskin Zombie — gate the 3-damage payload on whether the
	controller's opponent is the current player at death-resolution
	time. Expressed imperatively because the OPPONENT selector path
	can return an empty list at deathrattle resolution (the entity is
	mid-zone-transition to GRAVEYARD)."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		if opp.current_player:
			source.game.cheat_action(source, [Hit(opp.hero, 3)])


class _PlaguespreaderMorph(TargetedAction):
	"""Plaguespreader deathrattle — transform a random minion card in the
	opponent's hand into a Plaguespreader (RLK_831). Single-target Morph
	can't easily be expressed via the selector DSL because the picked
	minion is a hand card on the *opponent*; we do it imperatively here."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		pool = [c for c in opp.hand if c.type == CardType.MINION]
		if not pool:
			return
		picked = source.game.random.choice(pool)
		source.game.cheat_action(source, [Morph(picked, "RLK_831")])


class _InfectiousGhoulGiftDeathrattle(TargetedAction):
	"""Infectious Ghoul deathrattle — give a random other friendly minion
	the deathrattle 'Summon an Infectious Ghoul' (RLK_653e applied via
	additional_deathrattles so it stacks with any existing deathrattle)."""

	TARGET = ActionArg()

	def do(self, source, target):
		pool = [m for m in source.controller.field if m is not source]
		if not pool:
			return
		recipient = source.game.random.choice(pool)
		source.game.cheat_action(source, [Buff(recipient, "RLK_653e")])


class _FleshBehemothDrawAndCopy(TargetedAction):
	"""Flesh Behemoth deathrattle — draw another Undead from the deck and
	summon a copy of it on the controller's side. If no Undead remains in
	deck, nothing happens (matches printed text — no fallback to non-Undead)."""

	TARGET = ActionArg()

	def do(self, source, target):
		pool = [c for c in target.deck if Race.UNDEAD in getattr(c, "races", [])]
		if not pool:
			return
		pick = source.game.random.choice(pool)
		# Route the draw through the standard Draw action so OWN_DRAW
		# listeners (Vereesa Windrunner, Voracious Reader, etc.) fire,
		# matching the printed "Draw another Undead" text. Then summon
		# a fresh copy of the same id on the controller's side.
		source.game.cheat_action(source, [Draw(target, pick)])
		source.game.cheat_action(source, [Summon(target, pick.id)])


class _TranslocationInstructorSwap(TargetedAction):
	"""Translocation Instructor — pick a random minion in the opponent's
	deck and swap it with the chosen enemy minion: the chosen minion goes
	to the deck slot, the deck minion is summoned in the chosen one's
	board position on the opponent's side."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = target.controller
		pool = [c for c in opp.deck if c.type == CardType.MINION]
		if not pool:
			return
		pick = source.game.random.choice(pool)
		# Pull pick out of deck, summon on opp side; bounce target to deck.
		from hearthstone.enums import Zone
		opp.deck.remove(pick)
		pick._zone = Zone.SETASIDE
		source.game.cheat_action(source, [Summon(opp, pick.id)])
		# Remove the chosen minion from board and stash it in opp's deck.
		target.zone = Zone.SETASIDE
		target.zone = Zone.DECK


class _BonelordFrostwhisperTick(TargetedAction):
	"""Bonelord Frostwhisper death-counter tick. Decrements the opponent's
	`_frostwhisper_turns_left` at end of their turn; when it reaches 0
	the opponent's hero takes lethal damage (`Hit` for current health).
	Aura entity is the death-counter enchant RLK_591e attached to the
	enemy hero."""

	TARGET = ActionArg()

	def do(self, source, target):
		# `target` is the controller of the doom-counter buff (resolved
		# via CONTROLLER selector).
		left = getattr(target, "_frostwhisper_turns_left", 0) - 1
		target._frostwhisper_turns_left = max(0, left)
		if left <= 0 and target.hero.health > 0:
			source.game.cheat_action(
				source, [Hit(target.hero, target.hero.health + 100)]
			)


class _BonelordFrostwhisperArm(TargetedAction):
	"""Bonelord Frostwhisper deathrattle — stamp the enemy hero with
	`_frostwhisper_turns_left = 3` so the death-counter starts, and flip
	`_frostwhisper_first_card_free = True` so pay_cost zero-prices the
	first card the (opponent) plays each turn for the rest of the game.
	Resets to "first not yet consumed this turn" at OWN_TURN_BEGIN via
	the `_frostwhisper_consumed_this_turn` flag."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		opp._frostwhisper_turns_left = 3
		opp._frostwhisper_first_card_free = True
		opp._frostwhisper_consumed_this_turn = False


class _InvincibleBuffRandomUndead(TargetedAction):
	"""Invincible battlecry & deathrattle — give a random friendly Undead
	+5/+5 and Taunt. Picks from current friendly Undead minions on the
	board (excluding SELF)."""

	TARGET = ActionArg()

	def do(self, source, target):
		pool = [
			m for m in source.controller.field
			if m is not source and Race.UNDEAD in getattr(m, "races", [])
		]
		if not pool:
			return
		pick = source.game.random.choice(pool)
		source.game.cheat_action(source, [Buff(pick, "RLK_592e")])
		source.game.cheat_action(source, [SetTags(pick, (GameTag.TAUNT,))])


class _LorthemarDoubleDeckStats(TargetedAction):
	"""Lor'themar Theron battlecry — double the stats of every minion in
	the controller's deck. Implemented imperatively because the standard
	Buff() path on FRIENDLY_DECK + MINION would need a stat-mirror enchant
	per recipient; here we stamp RLK_593e with atk/max_health snapshotted
	from each deck card."""

	TARGET = ActionArg()

	def do(self, source, target):
		for c in list(target.deck):
			if c.type != CardType.MINION:
				continue
			source.game.cheat_action(
				source,
				[Buff(c, "RLK_593e", atk=c.atk, max_health=c.health)],
			)


class _SilvermoonArcanistArm(TargetedAction):
	"""Silvermoon Arcanist battlecry — set the per-turn flag that filters
	heroes out of spell-target picks. Cleared at OWN_TURN_END."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.spells_cant_target_heroes_this_turn = True


class _AstalorBloodswornDamage(TargetedAction):
	"""Astalor Bloodsworn — Manathirst (5): Deal 2 damage. Done as a
	custom action only to be explicit about target selection (random
	enemy character for the un-targeted printed text)."""

	TARGET = ActionArg()

	def do(self, source, target):
		if source.controller.max_mana < 5:
			return
		pool = [c for c in target.opponent.characters if c.health > 0]
		if not pool:
			return
		pick = source.game.random.choice(pool)
		source.game.cheat_action(source, [Hit(pick, 2)])


##
# Minions


class RLK_029:
	"""Shatterskin Gargoyle"""

	# Taunt. Deathrattle: Deal 4 damage to a random enemy.
	deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 4)


class RLK_070:
	"""Infected Peasant"""

	# Deathrattle: Summon a 2/2 Undead Peasant.
	deathrattle = Summon(CONTROLLER, "RLK_070t")


class RLK_104:
	"""Street Sweeper"""

	# Battlecry: Deal 2 damage to all other minions.
	play = Hit(ALL_MINIONS - SELF, 2)


class RLK_113:
	"""Brittleskin Zombie"""

	# Deathrattle: If it's your opponent's turn, deal 3 damage to them.
	deathrattle = _BrittleskinZombieDeathrattle(SELF)


class RLK_117:
	"""Incorporeal Corporal"""

	# After this minion attacks, destroy it.
	events = Attack(SELF).after(Destroy(SELF))


class RLK_119:
	"""Drakkari Embalmer"""

	# Battlecry: Give a friendly Undead Reborn.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_TARGET_WITH_RACE: int(Race.UNDEAD),
	}
	play = GiveReborn(TARGET)


class RLK_123:
	"""Bone Flinger"""

	# Battlecry: If a friendly Undead died after your last turn, deal 2 damage.
	# Uses the engine-managed `_undead_deaths_in_window` (Death.do appends,
	# OWN_TURN_END resets) — exact match to the printed window semantics.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
	}
	play = (_UndeadDiedAfterLastTurn() >= 1) & Hit(TARGET, 2)


class RLK_218:
	"""Silvermoon Arcanist"""

	# Spell Damage +2. Battlecry: Your spells can't target heroes this turn.
	# SPELLPOWER is set in data; the "can't target heroes" rider arms
	# `controller.spells_cant_target_heroes_this_turn` (consumed by
	# is_valid_target in targeting.py, reset at OWN_TURN_END in game.py).
	# The Buff(CONTROLLER, "RLK_218e") below is purely cosmetic — the
	# enchant has TAG_ONE_TURN_EFFECT so it visibly clears at turn end.
	play = (
		_SilvermoonArcanistArm(CONTROLLER),
		Buff(CONTROLLER, "RLK_218e"),
	)


@custom_card
class RLK_218e:
	# Per-turn marker. Engine TODO: when active, gate spell target picks
	# to exclude heroes. For now this enchant just exists so the play
	# action has something to anchor; auto-clears at OWN_TURN_END.
	tags = {
		GameTag.CARDNAME: "Silvermoon Arcanist",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.TAG_ONE_TURN_EFFECT: True,
	}


class RLK_219:
	"""Sunfury Clergy"""

	# Battlecry: Restore 3 Health to all friendly characters. Manathirst
	# (6): Restore 6 Health instead.
	play = (MANATHIRST(6) & Heal(FRIENDLY_CHARACTERS, 6)) | Heal(
		FRIENDLY_CHARACTERS, 3
	)


class RLK_220:
	"""Tenacious San'layn"""

	# Lifesteal. Whenever this attacks, deal 2 damage to the enemy hero.
	# LIFESTEAL is set in data.
	events = Attack(SELF).on(Hit(ENEMY_HERO, 2))


class RLK_221:
	"""Crystal Broker"""

	# Manathirst (5): Summon a random 3-Cost minion. Manathirst (10):
	# Summon an 8-Cost minion instead.
	play = (
		MANATHIRST(10) & Summon(CONTROLLER, RandomMinion(cost=8))
	) | (MANATHIRST(5) & Summon(CONTROLLER, RandomMinion(cost=3)))


class RLK_222(ManathirstCardtextMixin):
	"""Astalor Bloodsworn"""

	# Battlecry: Add Astalor, the Protector to your hand. Manathirst (5):
	# Deal 2 damage.
	manathirst_threshold = 5
	play = (
		Give(CONTROLLER, "RLK_222t1"),
		_AstalorBloodswornDamage(CONTROLLER),
	)


class RLK_222t1(ManathirstCardtextMixin):
	"""Astalor, the Protector"""

	# Battlecry: Add Astalor, the Flamebringer to your hand. Manathirst
	# (8): Gain 8 Armor.
	manathirst_threshold = 8
	play = (
		Give(CONTROLLER, "RLK_222t2"),
		MANATHIRST(8) & GainArmor(FRIENDLY_HERO, 8),
	)


class RLK_222t2(ManathirstCardtextMixin):
	"""Astalor, the Flamebringer"""

	# Battlecry: Deal 8 damage randomly split between all enemies.
	# Manathirst (10): Deal 16 instead.
	manathirst_threshold = 10
	play = (
		(MANATHIRST(10) & Hit(RANDOM_ENEMY_CHARACTER, 1) * 16)
		| (Hit(RANDOM_ENEMY_CHARACTER, 1) * 8),
	)


class RLK_518(ManathirstCardtextMixin):
	"""Silvermoon Sentinel"""

	# Taunt. Manathirst (5): Gain +2/+2 and Divine Shield.
	manathirst_threshold = 5
	play = MANATHIRST(5) & (
		Buff(SELF, "RLK_518e"),
		GiveDivineShield(SELF),
	)


class RLK_591:
	"""Bonelord Frostwhisper"""

	# Deathrattle: For the rest of the game, your first card each turn
	# costs (0). You die in 3 turns.
	# Approximation: stamp the opponent with a 3-turn doom counter
	# (lethal hit at expiry). The "first card costs 0" aura is TODO
	# (no per-turn cost-mod hook yet).
	deathrattle = (
		_BonelordFrostwhisperArm(SELF),
		Buff(ENEMY_HERO, "RLK_591e"),
	)


class RLK_591e:
	# In-data enchant "Lich Death Counter" — listens for the opponent's
	# (i.e. the Frostwhisper-buffed hero's) own turn-end to tick down.
	events = OWN_TURN_END.on(_BonelordFrostwhisperTick(CONTROLLER))


class RLK_592:
	"""Invincible"""

	# Reborn. Battlecry and Deathrattle: Give a random friendly Undead
	# +5/+5 and Taunt.
	play = _InvincibleBuffRandomUndead(SELF)
	deathrattle = _InvincibleBuffRandomUndead(SELF)


class RLK_592e:
	# In-data enchant "Invincible's Reins" — +5/+5. CardXML doesn't
	# parse the stat tags so we re-declare them.
	tags = {GameTag.ATK: 5, GameTag.HEALTH: 5}


class RLK_593:
	"""Lor'themar Theron"""

	# Battlecry: Double the stats of all minions in your deck.
	play = _LorthemarDoubleDeckStats(CONTROLLER)


class RLK_593e:
	# In-data enchant "Superior Strategy" — stat values come from runtime
	# atk/max_health kwargs (snapshot per recipient), not static tags.
	tags = {}


class RLK_653:
	"""Infectious Ghoul"""

	# Deathrattle: Give a random friendly minion "Deathrattle: Summon an
	# Infectious Ghoul."
	deathrattle = _InfectiousGhoulGiftDeathrattle(SELF)


class RLK_653e:
	# In-data enchant "Infected" — grants the "Summon an Infectious
	# Ghoul" deathrattle. The engine reads DEATHRATTLE=1 + a script
	# `deathrattle` to register a granted deathrattle on the target.
	tags = {GameTag.DEATHRATTLE: True}
	deathrattle = Summon(CONTROLLER, "RLK_653")


class RLK_677:
	"""Sanctum Spellbender"""

	# Whenever your opponent targets another minion with a spell, redirect
	# it to this. Implemented via a redirect hook in PlayableCard.play()
	# (fireplace/card.py): if the spell's controller is the enemy of one
	# of our Spellbenders, the target is a minion other than the
	# Spellbender, and the Spellbender is on the field, the target is
	# rewritten to the Spellbender before play_targets is re-validated.
	pass


class RLK_824:
	"""Arms Dealer"""

	# After you summon an Undead, give it +1 Attack.
	events = Summon(CONTROLLER, UNDEAD - SELF).after(
		Buff(Summon.CARD, "RLK_824e")
	)


class RLK_830:
	"""Flesh Behemoth"""

	# Taunt. Deathrattle: Draw another Undead and summon a copy of it.
	deathrattle = _FleshBehemothDrawAndCopy(CONTROLLER)


class RLK_831:
	"""Plaguespreader"""

	# Deathrattle: Transform a random minion in your opponent's hand
	# into a Plaguespreader.
	deathrattle = _PlaguespreaderMorph(SELF)


class RLK_833:
	"""Foul Egg"""

	# Deathrattle: Summon a 3/3 Undead Chicken.
	deathrattle = Summon(CONTROLLER, "RLK_833t")


class RLK_834:
	"""Nerubian Vizier"""

	# Battlecry: Discover a spell. If a friendly Undead died after your
	# last turn, it costs (2) less. Uses the engine-managed
	# `_undead_deaths_in_window` for the precise window check.
	play = DISCOVER(RandomSpell()).then(
		(_UndeadDiedAfterLastTurn() >= 1) & Buff(Give.CARD, "RLK_834e")
	)


class RLK_867:
	"""Vrykul Necrolyte"""

	# Battlecry: Give a friendly minion "Deathrattle: Summon a 2/2 Zombie
	# with Rush."
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "RLK_867e")


class RLK_867e:
	# In-data enchant "It's Necro-Lit" — grants a deathrattle that
	# summons RLK_018t (Rampaging Zombie, 2/2 Rush — re-used token).
	tags = {GameTag.DEATHRATTLE: True}
	deathrattle = Summon(CONTROLLER, "RLK_018t")


class RLK_900:
	"""Scourge Rager"""

	# Reborn. Battlecry: Die.
	play = Destroy(SELF)


class RLK_914:
	"""Umbral Geist"""

	# Deathrattle: Add a random Shadow spell to your hand.
	deathrattle = Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.SHADOW))


class RLK_915:
	"""Amber Whelp"""

	# Battlecry: If you're holding a Dragon, deal 3 damage.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
	}
	play = HOLDING_DRAGON & Hit(TARGET, 3)


class RLK_926:
	"""Bloodied Knight"""

	# At the end of your turn, deal 2 damage to your hero.
	events = OWN_TURN_END.on(Hit(FRIENDLY_HERO, 2))


class RLK_950:
	"""Translocation Instructor"""

	# Battlecry: Choose an enemy minion. Swap it with a random one in
	# their deck.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _TranslocationInstructorSwap(TARGET)


class RLK_951:
	"""Coroner"""

	# Battlecry: Freeze an enemy minion. Manathirst (6): Silence it first.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = (
		MANATHIRST(6) & Silence(TARGET),
		Freeze(TARGET),
	)


class RLK_952:
	"""Enchanter"""

	# Enemy minions take double damage during your turn.
	# `incoming_damage_multiplier` uses left-shift (<<= multiplier), so
	# `1` doubles. We gate on the controller being the current player.
	update = (
		(Attr(CONTROLLER, GameTag.CURRENT_PLAYER) == True)
		& Refresh(ENEMY_MINIONS, {GameTag.INCOMING_DAMAGE_MULTIPLIER: 1})
	)


class RLK_955(ManathirstCardtextMixin):
	"""Silvermoon Armorer"""

	# Rush. Manathirst (5): Gain +2/+2.
	manathirst_threshold = 5
	play = MANATHIRST(5) & Buff(SELF, "RLK_955e")


class RLK_957:
	"""Banshee"""

	# Deathrattle: Give a random friendly Undead +2/+1.
	deathrattle = Buff(
		RANDOM(FRIENDLY_MINIONS + UNDEAD), "RLK_957e"
	)


class RLK_970:
	"""Hawkstrider Rancher"""

	# After you play a minion, give it +1/+1 and "Deathrattle: Summon a
	# 1/1 Hawkstrider."
	events = Play(CONTROLLER, MINION - SELF).after(
		Buff(Play.CARD, "RLK_970e")
	)


class RLK_970e:
	# In-data enchant "Hawkriding" — +1/+1 plus a granted deathrattle.
	# Parsed CardXML doesn't expose the ATK/HEALTH tags, so we declare
	# them here alongside the granted-deathrattle flag.
	tags = {
		GameTag.ATK: 1,
		GameTag.HEALTH: 1,
		GameTag.DEATHRATTLE: True,
	}
	deathrattle = Summon(CONTROLLER, "RLK_970t")


##
# Stat enchantments (in-data ids whose ATK/HEALTH didn't parse)


class RLK_518e:
	# Silvermoon's Might — +2/+2.
	tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class RLK_824e:
	# Undead Fortitude — +1 Attack.
	tags = {GameTag.ATK: 1}


class RLK_834e:
	# Nerubian Vision — Costs (2) less.
	tags = {GameTag.COST: -2}


class RLK_955e:
	# Supplied — +2/+2.
	tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class RLK_957e:
	# Banshee's Wail — +2/+1.
	tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


##
# Spells


class RLK_590:
	"""The Sunwell"""

	# Fill your hand with random spells. Costs (1) less for each other
	# card in your hand.
	cost_mod = -Count(FRIENDLY_HAND - SELF)
	play = Give(
		CONTROLLER, RandomSpell()
	) * (Attr(CONTROLLER, GameTag.MAXHANDSIZE) - Count(FRIENDLY_HAND))


##
# Enchantments (custom registrations for ids not present in data)


@custom_card
class RLK_104e:
	# Not present in data — Street Sweeper has no in-data battlecry
	# enchant, but a few engine paths look up the cardname for damage
	# attribution. Register a no-op stub so any future lookup resolves.
	tags = {
		GameTag.CARDNAME: "Sweeping",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_677e:
	# Not in data; reserved for any future Sanctum Spellbender redirect
	# marker. No script today.
	tags = {
		GameTag.CARDNAME: "Redirected",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_830e:
	# Not in data; placeholder for Flesh Behemoth — no aura/buff applied.
	tags = {
		GameTag.CARDNAME: "Behemoth",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_900e:
	# Not in data; Scourge Rager's "die" effect needs no enchant.
	tags = {
		GameTag.CARDNAME: "Reborn",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_926e:
	# Not in data; Bloodied Knight self-damage requires no enchant.
	tags = {
		GameTag.CARDNAME: "Bloodied",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_951e:
	# Not in data; Coroner uses Freeze/Silence directly, no enchant.
	tags = {
		GameTag.CARDNAME: "Coronered",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}


@custom_card
class RLK_952e:
	# Not in data; Enchanter aura is applied via update=Refresh, not buff.
	tags = {
		GameTag.CARDNAME: "Enchanted",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
