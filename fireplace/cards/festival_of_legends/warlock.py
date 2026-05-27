from ..utils import *


##
# Custom actions


class _BaritoneImpFatigue(TargetedAction):
	"""Baritone Imp — take Fatigue damage, then buff SELF by that amount
	in atk/health. The fatigue *amount* is the post-bump counter (the
	hit that just landed), NOT the per-call delta — Fatigue.do bumps
	the counter by 1 then hits the hero for the new total."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		pre = ctrl.fatigue_counter
		source.game.cheat_action(source, [Fatigue(ctrl)])
		# If fatigue is blocked (cant_fatigue), counter didn't change.
		if ctrl.fatigue_counter == pre:
			return
		amount = ctrl.fatigue_counter  # post-bump = damage that landed
		source.game.cheat_action(
			source,
			[Buff(source, "ETC_068e", atk=amount, max_health=amount)],
		)


class _CrescendoFatigue(TargetedAction):
	"""Crescendo — take Fatigue damage, then deal that much damage to
	all enemies. "That much" = the fatigue hit just landed (post-bump
	counter value, mirroring Fatigue.do)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		pre = ctrl.fatigue_counter
		source.game.cheat_action(source, [Fatigue(ctrl)])
		if ctrl.fatigue_counter == pre:
			return
		amount = ctrl.fatigue_counter
		source.game.cheat_action(
			source, [Hit(ENEMY_CHARACTERS, amount)]
		)


class _CrazedConductorFatigue(TargetedAction):
	"""Crazed Conductor — take Fatigue damage, then summon that many
	3/3 Orchestral Imps (ETC_070t). Board space clamps each Summon."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		pre = ctrl.fatigue_counter
		source.game.cheat_action(source, [Fatigue(ctrl)])
		if ctrl.fatigue_counter == pre:
			return
		amount = ctrl.fatigue_counter
		for _ in range(max(0, amount)):
			source.game.cheat_action(source, [Summon(ctrl, "ETC_070t")])


class _RinDeathrattle(TargetedAction):
	"""Rin, Orchestrator of Doom — deathrattle: both players draw 2,
	discard 2, and destroy the top 2 cards of their deck. Resolves
	for each player in turn order (controller first)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		players = [ctrl, ctrl.opponent]
		for p in players:
			# Draw 2
			source.game.cheat_action(source, [Draw(p) * 2])
			# Discard 2 random from hand — pick directly rather than
			# via RANDOM() because RANDOM expects a Selector and we
			# have a CardList in hand.
			for _ in range(2):
				if not p.hand:
					break
				pick = source.game.random.choice(list(p.hand))
				source.game.cheat_action(source, [Discard(pick)])
			# Mill top 2 cards of deck.
			for _ in range(2):
				if not p.deck:
					break
				top = p.deck[-1]
				source.game.cheat_action(source, [Destroy(top)])


class _DirgeOfDespairSummonDemon(TargetedAction):
	"""Dirge of Despair — if the targeted character is dead after the
	$3 hit, summon a random Demon from the controller's deck. Reads
	target post-hit; falls back to no-op if the target survived."""

	TARGET = ActionArg()

	def do(self, source, target):
		# Target may be hero or minion; treat death uniformly.
		if not getattr(target, "dead", False) and target.zone != Zone.GRAVEYARD:
			return
		ctrl = source.controller
		demons = [
			c for c in ctrl.deck
			if c.type == CardType.MINION and Race.DEMON in c.races
		]
		if not demons:
			return
		pick = source.game.random.choice(demons)
		source.game.cheat_action(source, [Summon(ctrl, pick.id)])


class _DemonicDynamicsPlay(TargetedAction):
	"""Demonic Dynamics — Discover 2 Demons sequentially, then (Finale)
	stamp +1/+2 on the freshly-discovered copies. The Discovers go to
	the controller; picks are stashed on the source spell so the
	Finale callback can buff them."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		# Queue two sequential Discovers of Demons. Each goes through
		# the standard DISCOVER(...) wrapper which sets player.choice
		# and on-pick gives the card to the controller's hand.
		source.game.cheat_action(
			source, [DISCOVER(RandomMinion(race=Race.DEMON))]
		)
		source.game.cheat_action(
			source, [DISCOVER(RandomMinion(race=Race.DEMON))]
		)
		# Finale: walk the hand from the right and buff the two most
		# recently added Demons +1/+2 (best-effort proxy for "the
		# freshly-picked cards").
		if not source.play_finale:
			return
		demons_buffed = 0
		for c in reversed(list(ctrl.hand)):
			if demons_buffed >= 2:
				break
			if c.type == CardType.MINION and Race.DEMON in c.races:
				source.game.cheat_action(source, [Buff(c, "ETC_083e")])
				demons_buffed += 1


_MOVEMENTS = (
	"ETC_085t",   # Envy
	"ETC_085t2",  # Pride
	"ETC_085t3",  # Wrath
	"ETC_085t4",  # Gluttony
	"ETC_085t6",  # Desire
	"ETC_085t7",  # Greed
	"ETC_085t8",  # Sloth
)


class _SymphonyOfSinsShuffleRest(TargetedAction):
	"""Symphony of Sins — after the picked Movement is cast, shuffle
	every other Movement into the controller's deck. Fires from the
	Discover.then chain so we know which id was picked (Discover.CARD)."""

	TARGET = ActionArg()
	PICKED = CardArg()

	def do(self, source, target, picked):
		ctrl = target
		picked_id = picked.id if hasattr(picked, "id") else picked
		for cid in _MOVEMENTS:
			if cid == picked_id:
				continue
			source.game.cheat_action(source, [Give(ctrl, cid)])
			if ctrl.hand:
				new_card = ctrl.hand[-1]
				if new_card.id == cid:
					source.game.cheat_action(
						source, [Shuffle(ctrl, new_card)]
					)


class _SymphonyOfSinsPlay(TargetedAction):
	"""Symphony of Sins — Discover one of the 7 Movements and cast it,
	then shuffle the other 6 into the controller's deck. Skips
	ETC_085t5 (Movement of Lust, missing from data this patch)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		discover = Discover(ctrl, RandomID(*_MOVEMENTS)).then(
			CastSpell(Discover.CARD),
			_SymphonyOfSinsShuffleRest(ctrl, Discover.CARD),
		)
		source.game.cheat_action(source, [discover])


class _FelstringHarpDamageGuard(TargetedAction):
	"""Felstring Harp — listens for damage about to land on the
	controller's hero during the controller's own turn. Substitutes a
	2-heal for the damage and chews 1 durability off the weapon. Uses
	a Damage.on listener (pre-Damage) so we can intercept by cancelling
	the queued hit and queueing a Heal instead. Since we can't truly
	cancel a damage post-broadcast, this is an approximation: we let
	the damage land, then heal 2 immediately after, and consume 1
	durability."""

	TARGET = ActionArg()
	AMOUNT = IntArg()

	def do(self, source, target, amount):
		# `source` is the weapon. Only fire when the controller is the
		# current player and the weapon has durability left.
		ctrl = source.controller
		if ctrl is not source.game.current_player:
			return
		if source.zone != Zone.PLAY:
			return
		if (source.durability or 0) <= 0:
			return
		# Heal the hero by 2; chew 1 durability off the weapon. The
		# damage was already broadcast (engine ordering), so this is a
		# best-effort approximation rather than a true pre-damage swap.
		source.game.cheat_action(source, [Heal(ctrl.hero, 2)])
		source.damage = (source.damage or 0) + 1
		if source.durability <= 0:
			source.game.cheat_action(source, [Destroy(source)])


##
# Minions


class ETC_034:
	"""Opera Soloist"""

	# Battlecry: If you control no other minions, deal 3 damage to all
	# enemy minions. EMPTY_BOARD alone is False at battlecry time
	# (Opera already entered PLAY) — use the explicit -SELF filter to
	# enforce "no OTHER minions".
	play = (Count(FRIENDLY_MINIONS - SELF) == 0) & Hit(ENEMY_MINIONS, 3)


class ETC_068:
	"""Baritone Imp"""

	# Battlecry: Take Fatigue damage. Gain that much Attack and Health.
	play = _BaritoneImpFatigue(SELF)


class ETC_070:
	"""Crazed Conductor"""

	# Battlecry: Take Fatigue damage. Summon that many 3/3 Imps.
	play = _CrazedConductorFatigue(SELF)


class ETC_071:
	"""Rin, Orchestrator of Doom"""

	# Taunt. Deathrattle: Both players draw 2 cards, discard 2 cards,
	# and destroy the top 2 cards of their deck. Taunt is in data; only
	# the deathrattle is scripted.
	deathrattle = _RinDeathrattle(SELF)


class ETC_081:
	"""Void Virtuoso"""

	# During your turn, your hero is Immune.
	# Aura refreshes the friendly hero with CANT_BE_DAMAGED; the
	# CURRENT_PLAYER gate keeps it active only on the controller's turn.
	update = (
		Find(CURRENT_PLAYER + FRIENDLY)
		& Refresh(FRIENDLY_HERO, {GameTag.CANT_BE_DAMAGED: True}),
	)


##
# Spells


class ETC_069:
	"""Crescendo"""

	# Take Fatigue damage. Deal that much damage to all enemies.
	play = _CrescendoFatigue(SELF)


class ETC_082:
	"""Dirge of Despair"""

	# Deal $3 damage to a character. If that kills it, summon a Demon
	# from your deck.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
	}
	play = Hit(TARGET, 3), _DirgeOfDespairSummonDemon(TARGET)


class ETC_083:
	"""Demonic Dynamics"""

	# Discover 2 Demons. Finale: Give them +1/+2.
	play = _DemonicDynamicsPlay(SELF)


class ETC_085:
	"""Symphony of Sins"""

	# Discover and play a Movement. Shuffle the other 6 into your deck.
	play = _SymphonyOfSinsPlay(SELF)


##
# Weapons


class ETC_084:
	"""Felstring Harp"""

	# Whenever your hero would take damage on your turn, restore 2 Health
	# instead. Lose 1 Durability. Approximation: post-damage trigger
	# (heal 2 + chew 1 durability) rather than a true pre-damage swap.
	events = Damage(FRIENDLY_HERO).on(
		_FelstringHarpDamageGuard(SELF, Damage.AMOUNT)
	)


##
# Enchantments


class ETC_068e:
	# In-data buff "Sing!" — Baritone Imp's fatigue self-buff. Stats
	# supplied at runtime via Buff(..., atk=, max_health=).
	tags = {}


##
# Tokens — Movement of Sloth's 6/6 Demon summon


class ETC_070t:
	"""Orchestral Imp"""

	# 3/3 vanilla token summoned by Crazed Conductor's battlecry. No
	# script needed.


class ETC_085t:
	"""Movement of Envy"""

	# Remove the top 6 cards from your opponent's deck.
	play = _MovementOfEnvyMill(CONTROLLER) if False else None


# --- Movement spell scripts ---


class _MovementOfEnvyMill(TargetedAction):
	"""Movement of Envy — destroy the top 6 cards of the opponent's
	deck. "Remove" reads as "mill"."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = target.opponent
		for _ in range(6):
			if not opp.deck:
				break
			top = opp.deck[-1]
			source.game.cheat_action(source, [Destroy(top)])


# Re-bind ETC_085t.play now that the action exists.
ETC_085t.play = _MovementOfEnvyMill(CONTROLLER)


class ETC_085t2:
	"""Movement of Pride"""

	# Draw your highest Cost minion. Reduce its Cost by (6).
	play = None  # bound below after action defined


class _MovementOfPrideDraw(TargetedAction):
	"""Movement of Pride — find the highest-cost minion in the
	controller's deck, force-draw it, then stamp a -6 cost enchant on
	the drawn copy."""

	TARGET = ActionArg()

	def do(self, source, target):
		minions = [c for c in target.deck if c.type == CardType.MINION]
		if not minions:
			return
		highest = max(minions, key=lambda c: c.cost or 0)
		source.game.cheat_action(source, [ForceDraw(highest)])
		source.game.cheat_action(source, [Buff(highest, "ETC_085t2e")])


ETC_085t2.play = _MovementOfPrideDraw(CONTROLLER)


@custom_card
class ETC_085t2e:
	tags = {
		GameTag.CARDNAME: "Pride",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -6,
	}


class ETC_085t3:
	"""Movement of Wrath"""

	# Deal $6 damage to all characters.
	play = Hit(ALL_CHARACTERS, 6)


class ETC_085t4:
	"""Movement of Gluttony"""

	# Give a random minion in your hand, deck, and battlefield +6/+6.
	play = None  # bound after action defined


class _MovementOfGluttonyBuff(TargetedAction):
	"""Movement of Gluttony — pick one random minion from controller's
	hand, deck, and battlefield (each pool independent) and stamp +6/+6
	on each pick."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = target
		zones = (
			[c for c in ctrl.hand if c.type == CardType.MINION],
			[c for c in ctrl.deck if c.type == CardType.MINION],
			[c for c in ctrl.field if c.type == CardType.MINION],
		)
		for zone in zones:
			if not zone:
				continue
			pick = source.game.random.choice(zone)
			source.game.cheat_action(
				source, [Buff(pick, "ETC_085t4e")]
			)


ETC_085t4.play = _MovementOfGluttonyBuff(CONTROLLER)


@custom_card
class ETC_085t4e:
	tags = {
		GameTag.CARDNAME: "Gluttony",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.ATK: 6,
		GameTag.HEALTH: 6,
	}


class ETC_085t6:
	"""Movement of Desire"""

	# Lifesteal. Deal $6 damage to the enemy hero. Lifesteal is in data.
	play = Hit(ENEMY_HERO, 6)


class ETC_085t7:
	"""Movement of Greed"""

	# Draw 6 cards.
	play = Draw(CONTROLLER) * 6


class ETC_085t8:
	"""Movement of Sloth"""

	# Summon a 6/6 Demon with Taunt and Reborn. No specific token id
	# in data this patch — summon a custom 6/6 Demon via a known
	# placeholder. Pick the Felguard token if present; otherwise summon
	# a 6/6 generic.
	play = None  # bound below


class _MovementOfSlothSummon(TargetedAction):
	"""Movement of Sloth — summon a 6/6 Taunt Reborn Demon. No printed
	demon token id is available in current data; spawn a generic Imp
	(EX1_598) and stat-stamp it to 6/6 with Taunt + Reborn."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		source.game.cheat_action(
			source,
			[SummonCustomMinion(ctrl, "EX1_598", 6, 6, 6)],
		)
		if ctrl.field:
			demon = ctrl.field[-1]
			source.game.cheat_action(
				source,
				[Buff(demon, "ETC_085t8e")],
			)


ETC_085t8.play = _MovementOfSlothSummon(CONTROLLER)


@custom_card
class ETC_085t8e:
	tags = {
		GameTag.CARDNAME: "Sloth",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.TAUNT: True,
		GameTag.REBORN: True,
	}
