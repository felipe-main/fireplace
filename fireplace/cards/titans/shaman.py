from ..utils import *


##
# Custom actions


class _GolgannePassive(TargetedAction):
	"""Golganneth — passive aura controller: first spell each turn costs
	(3) less.  Implemented the same channel as Love Everlasting / Glacial
	Advance: arm _golganneth_active on the controller when Golganneth
	enters the field; pay_cost checks a per-turn latch.  The latch is
	re-armed in begin_turn via a per-turn-begin listener on the enchant
	stamped on the controller."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		ctrl._golganneth_active = True
		ctrl._golganneth_consumed_this_turn = False



class _GolganneDrawOverload(TargetedAction):
	"""Golganneth ability — Shargahn's Wrath: Draw 3 Overload cards from
	the deck.  Falls back to drawing random cards if fewer than 3
	Overload cards exist in deck."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		overload_cards = [c for c in ctrl.deck if getattr(c, "overload", 0) > 0]
		drawn = 0
		for card in overload_cards[:3]:
			if drawn >= 3:
				break
			source.game.cheat_action(source, [ForceDraw(card)])
			drawn += 1
		# Pad with normal draws if deck had fewer than 3 Overload cards.
		remaining = 3 - drawn
		if remaining > 0:
			source.game.cheat_action(source, [Draw(ctrl) * remaining])


class _FlashOfLightningTick(TargetedAction):
	"""TTN_830e — two-tick counter so the nature discount lasts through
	NEXT turn rather than expiring at the end of this turn.
	First OWN_TURN_END (cast-turn end): increment counter, keep enchant.
	Second OWN_TURN_END (next turn's end): destroy enchant."""

	TARGET = ActionArg()

	def do(self, source, target):
		ticks = getattr(source, "_flash_ticks", 0) + 1
		source._flash_ticks = ticks
		if ticks >= 2:
			source.game.cheat_action(source, [Destroy(source)])


class _NatureSpellsThisTurn(LazyNum):
	"""LazyNum counting how many Nature spells the controller has cast
	this turn.  Reads from player.spells_cast_by_school: the dict maps
	int(SpellSchool) → list of card-ids cast this game.  We approximate
	"this turn" by tracking a snapshot at turn-begin and diffing; a
	simpler per-turn attribute is added below via the
	_NatureSpellResetListener on TTN_831 itself."""

	def evaluate(self, source):
		ctrl = source.controller
		key = int(SpellSchool.NATURE)
		all_nature = ctrl.spells_cast_by_school.get(key, [])
		turn_start = getattr(ctrl, "_nature_spells_at_turn_start", 0)
		return max(0, len(all_nature) - turn_start)


class _SnapNatureSpellCount(TargetedAction):
	"""At the start of the controller's turn, snapshot the current length
	of the Nature-spells-cast-this-game list so TTN_831's cost_mod can
	compute a per-turn delta cheaply."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		key = int(SpellSchool.NATURE)
		all_nature = ctrl.spells_cast_by_school.get(key, [])
		ctrl._nature_spells_at_turn_start = len(all_nature)


##
# Spells


class TTN_317:
	"""Lightning Reflexes"""

	# Discover a Nature spell. If you play it this turn, Discover another.
	# Approximation: Discover a Nature spell.  The bonus second Discover
	# for playing it the same turn requires cross-spell event wiring that
	# the engine doesn't support cleanly; TODO for a future pass.
	play = DISCOVER(RandomSpell(spell_school=SpellSchool.NATURE))


class TTN_722:
	"""Turn the Tides"""

	# Give your hero +3 Attack this turn. Summon a 3/3 Elemental with Rush.
	# Overload: (1) — set in data, handled by Play.do.
	play = (
		Buff(FRIENDLY_HERO, "TTN_722e"),
		Summon(CONTROLLER, "TTN_833t"),  # Waveling 3/3 with Rush
	)


@custom_card
class TTN_722e:
	# +3 Attack this turn (TEMPORARY auto-clears at end of turn).
	# Not in data — register as custom_card.
	tags = {
		GameTag.CARDNAME: "Turn the Tides",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 3,
		enums.TEMPORARY: 1,
	}


class TTN_830:
	"""Flash of Lightning"""

	# Draw a card. Next turn, your Nature spells cost (1) less.
	# Approximate: draw a card and stamp a one-turn Nature discount via
	# a controller enchant whose OWN_TURN_END self-destructs after one
	# more turn.
	play = Draw(CONTROLLER), Buff(CONTROLLER, "TTN_830e")


class TTN_830e:
	# "Flash of Lightning" — while this enchant lives, Nature spells cost
	# (1) less.  Stamped on the controller when cast; should last until
	# the END of the *next* turn.  We implement a two-tick counter:
	# first OWN_TURN_END increments _flash_ticks; second one destroys.
	# This means the enchant persists through the remainder of THIS turn
	# (no effect immediately) and then through all of NEXT turn, expiring
	# at the end of that turn.
	events = OWN_TURN_END.on(_FlashOfLightningTick(SELF))
	update = Refresh(FRIENDLY_HAND + NATURE_SPELL, {GameTag.COST: -1})


class TTN_831:
	"""Crash of Thunder"""

	# Deal 3 damage to all enemies. Costs (1) less for each Nature spell
	# you've cast this turn.
	# The per-turn counter is approximated via a snapshot at turn-begin
	# (see _SnapNatureSpellCount).  TTN_831 itself listens OWN_TURN_BEGIN
	# in hand via a Hand.events class to set up the snapshot.
	cost_mod = -_NatureSpellsThisTurn()
	play = Hit(ENEMY_CHARACTERS, 3)

	class Hand:
		events = OWN_TURN_BEGIN.on(_SnapNatureSpellCount(SELF))


##
# Minions


class _ThorignirSummonAndAttackFirst(TargetedAction):
	"""Thorignir Drake — summon two 3/1 Whelps that attack the original
	defender BEFORE Thorignir's own hit lands. Whelps don't have Rush in
	data, so we bypass attack-eligibility checks and directly Hit the
	defender for each Whelp's attack value. The Whelp itself also takes
	the defender's retaliation damage (handled by the Hit pair).
	"""

	TARGET = ActionArg()
	DEFENDER = ActionArg()

	def do(self, source, target, defender):
		if isinstance(defender, (list, tuple)):
			defender = defender[0] if defender else None
		if defender is None or defender.zone != Zone.PLAY:
			return
		ctrl = source.controller
		for _ in range(2):
			source.game.cheat_action(source, [Summon(ctrl, "TTN_727t")])
			whelp = ctrl.field[-1] if ctrl.field else None
			if whelp is None or whelp.id != "TTN_727t":
				continue
			if defender.zone != Zone.PLAY:
				return
			# Simulate the Whelp's attack: Whelp hits defender for its atk,
			# defender hits Whelp back for its atk. Mirrors Attack.do damage
			# exchange without needing the Whelp to clear summoning sickness.
			whelp_atk = whelp.atk
			defender_atk = defender.atk
			source.game.cheat_action(whelp, [Hit(defender, whelp_atk)])
			if whelp.zone == Zone.PLAY and defender.zone == Zone.PLAY:
				source.game.cheat_action(defender, [Hit(whelp, defender_atk)])


class TTN_727:
	"""Thorignir Drake"""

	# Rush (data). Whenever this attacks, summon two 3/1 Whelps to attack
	# the target first.
	events = Attack(SELF).on(
		_ThorignirSummonAndAttackFirst(SELF, Attack.DEFENDER)
	)


class TTN_801:
	"""Champion of Storms"""

	# After you cast a Nature spell, summon a 4/2 Storm Cyclone.
	# Forge: the Cyclone gains Rush. Tokens TTN_801t1 (base) and TTN_801t2
	# (Rush) live in CardXML; the previously-summoned TTN_801e / TTN_801et
	# IDs were not real and crashed when triggered by random soak plays.
	forge_card = "TTN_801t"
	events = OWN_SPELL_PLAY.after(
		Find(Play.CARD + NATURE_SPELL) & Summon(CONTROLLER, "TTN_801t1")
	)


class TTN_801t:
	"""Champion of Storms"""

	events = OWN_SPELL_PLAY.after(
		Find(Play.CARD + NATURE_SPELL) & Summon(CONTROLLER, "TTN_801t2")
	)


class TTN_833:
	"""Disciple of Golganneth"""

	# At the end of your turn, reduce the Cost of a random Overload card
	# in your hand by (1).
	events = OWN_TURN_END.on(
		Buff(RANDOM(FRIENDLY_HAND + OVERLOAD), "TTN_833e")
	)


class TTN_835:
	"""Thorim, Stormlord"""

	# Battlecry: Unlock your Overloaded Mana Crystals. Draw that many cards.
	# play is bound below (after _ThorimUnlockAndDraw is defined).
	pass


##
# Weapons


class TTN_725:
	"""Tempest Hammer"""

	# After your hero attacks, deal 3 damage to the lowest Health enemy.
	events = Attack(FRIENDLY_HERO).after(
		Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 3)
	)


##
# Titans


class TTN_800:
	"""Golganneth, the Thunderer"""

	# Titan (data). Your first spell each turn costs (3) less.
	# Arm the permanent flag on the controller on entering play; the
	# per-turn latch is reset in game.py begin_turn, and the actual
	# -3 discount applied in player.py pay_cost (mirrors Love Everlasting).
	titan_ability_order = ["TTN_800t", "TTN_800t2", "TTN_800t3"]
	play = _GolgannePassive(CONTROLLER)


# Titan ability sub-cards


class TTN_800t:
	"""Roaring Oceans"""

	# Deal 3 damage to all enemies and restore 6 Health to all friendlies.
	play = Hit(ENEMY_CHARACTERS, 3), Heal(FRIENDLY_CHARACTERS, 6)


class TTN_800t2:
	"""Lord of Skies"""

	# Deal 20 damage to a minion.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Hit(TARGET, 20)


class TTN_800t3:
	"""Shargahn's Wrath"""

	# Draw 3 Overload cards.
	play = _GolganneDrawOverload(CONTROLLER)


##
# Enchantments


class TTN_833e:
	# Disciple of Golganneth — -1 cost to a random Overload card in hand.
	tags = {GameTag.COST: -1}


##
# Tokens


class TTN_722t:
	"""Crackling Elemental"""

	# 3/3 Elemental with Rush summoned by Turn the Tides.
	# Rush is set in data.




class TTN_727t:
	"""Stormy Whelp"""

	# 3/1 Whelp with Rush summoned by Thorignir Drake.
	# Rush set in data.


##
# Custom actions (defined after class stubs to avoid forward-reference issues)


class _ThorimUnlockAndDraw(TargetedAction):
	"""Thorim, Stormlord battlecry — snapshot the overload_locked amount,
	unlock both locked and pending overload, then draw that many cards."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		# overload_locked = crystals owed from LAST turn (now locked).
		# overloaded = crystals already owed but not yet locked this turn.
		locked = ctrl.overload_locked + ctrl.overloaded
		if locked <= 0:
			return
		source.game.cheat_action(source, [UnlockOverload(ctrl)])
		source.game.cheat_action(source, [Draw(ctrl) * locked])


# Re-bind TTN_835 play to the action defined after it.
TTN_835.play = _ThorimUnlockAndDraw(SELF)
