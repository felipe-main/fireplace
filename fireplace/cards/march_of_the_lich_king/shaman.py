from ..utils import *


##
# Custom actions


class _UnlivingChampionCheck(TargetedAction):
	"""Unliving Champion — Battlecry: If a friendly Undead died after the
	controller's last turn, summon two 3/2 Zombies. Scans the controller's
	graveyard for any minion with the UNDEAD race whose `turn_killed` is
	more recent than `controller.last_turn` (mirrors the Nerubian Flyer
	check in march_of_the_lich_king/druid.py)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		last = ctrl.last_turn if ctrl.last_turn is not None else -1
		from hearthstone.enums import Race, CardType
		found = False
		for c in ctrl.graveyard:
			if c.type != CardType.MINION:
				continue
			if getattr(c, "turn_killed", -1) <= last:
				continue
			if Race.UNDEAD in (c.race, getattr(c, "secondary_race", None)):
				found = True
				break
		if found:
			source.game.cheat_action(source, [Summon(ctrl, "RLK_909t") * 2])


class _PrescienceDraw(TargetedAction):
	"""Prescience — Draw 2 minions. For each that costs (5) or more,
	summon a 2/3 Spirit (Ghastly Apparition, RLK_553t) with Taunt. The
	engine has no native "draw a card matching a filter" primitive, so we
	scan the deck for minions, pick up to 2 at random, force-draw them,
	and count those whose cost >= 5 for the summon. Falls back to plain
	draws if there are no minions left in the deck."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardType
		drawn_minions = []
		for _ in range(2):
			pool = [c for c in target.deck if c.type == CardType.MINION]
			if pool:
				picked = source.game.random.choice(pool)
				source.game.cheat_action(source, [ForceDraw(picked)])
				drawn_minions.append(picked)
			else:
				source.game.cheat_action(source, [Draw(target)])
		summons = sum(1 for c in drawn_minions if (c.cost or 0) >= 5)
		for _ in range(summons):
			source.game.cheat_action(source, [Summon(target, "RLK_553t")])


class _FromDeOtherSide(TargetedAction):
	"""From De Other Side — for each minion in the controller's hand,
	summon a copy on the board, have it attack a random enemy minion (or
	enemy hero if no minions remain), then destroy it. Resolves
	minion-by-minion in hand order; the originals stay in hand. If the
	board is full when a copy would summon, the remaining copies are
	silently skipped (engine clamp)."""

	TARGET = ActionArg()

	def do(self, source, target):
		from hearthstone.enums import CardType, Zone
		ctrl = source.controller
		opp = ctrl.opponent
		minions_in_hand = [c for c in list(ctrl.hand) if c.type == CardType.MINION]
		for original in minions_in_hand:
			# Bail out if board full.
			if len(ctrl.field) >= source.game.MAX_MINIONS_ON_FIELD:
				continue
			source.game.cheat_action(source, [Summon(ctrl, original.id)])
			# Find the just-summoned copy: the last minion in the field
			# matching the id that wasn't there before.
			summoned = None
			for m in reversed(ctrl.field):
				if m.id == original.id:
					summoned = m
					break
			if summoned is None or summoned.zone != Zone.PLAY:
				continue
			# Pick attack target: random enemy minion if any, else hero.
			enemy_minions = [m for m in opp.field if m.zone == Zone.PLAY]
			if enemy_minions:
				victim = source.game.random.choice(enemy_minions)
			else:
				victim = opp.hero
			# Force the attack even on summoning-sick minions.
			summoned.attack_target = victim
			summoned.num_attacks = 0
			try:
				source.game.cheat_action(source, [Attack(summoned, victim)])
			except Exception:
				pass
			# Destroy whatever's left of the summoned copy.
			if summoned.zone == Zone.PLAY:
				source.game.cheat_action(source, [Destroy(summoned)])


class _DrakuruResurrect(TargetedAction):
	"""Overlord Drakuru — after this attacks and kills a minion, summon a
	copy of the killed defender on our side. Reads Attack.DEFENDER from
	the firing Attack event; if the defender is dead and was a minion,
	summon a fresh copy onto the controller's field."""

	TARGET = ActionArg()
	DEFENDER = ActionArg()

	def do(self, source, target, defender):
		if isinstance(defender, list):
			if not defender:
				return
			defender = defender[0]
		if defender is None:
			return
		from hearthstone.enums import CardType, Zone
		if defender.type != CardType.MINION:
			return
		# "Killed" — defender is now dead / in graveyard.
		if defender.zone not in (Zone.GRAVEYARD, Zone.SETASIDE) and not defender.dead:
			return
		ctrl = source.controller
		if len(ctrl.field) >= source.game.MAX_MINIONS_ON_FIELD:
			return
		source.game.cheat_action(source, [Summon(ctrl, defender.id)])


##
# Minions


class RLK_550:
	"""Rotgill"""

	# Battlecry: Give your other minions "Deathrattle: Give your minions +1/+1."
	# RLK_550e is the in-data "Deathwatch" enchant whose deathrattle fires
	# RLK_550e2 (+1/+1) on all friendly minions.
	play = Buff(FRIENDLY_MINIONS - SELF, "RLK_550e")


class RLK_550e:
	# In-data "Deathwatch" — Deathrattle: Give your minions +1/+1.
	deathrattle = Buff(FRIENDLY_MINIONS, "RLK_550e2")


class RLK_550e2:
	# In-data "Deathsight" — +1/+1. Stat tags not in parsed data.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class RLK_551:
	"""Blightblood Berserker"""

	# Taunt, Lifesteal, Reborn. Deathrattle: Deal 3 damage to a random enemy.
	# Taunt / Lifesteal / Reborn are set in data; only the deathrattle is
	# scripted. RANDOM_ENEMY_CHARACTER picks a live enemy character (minion
	# or hero) — matches the printed "random enemy".
	deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 3)


class RLK_552:
	"""Unliving Champion"""

	# Battlecry: If a friendly Undead died after your last turn, summon
	# two 3/2 Zombies. Reuses Drakkari Zombie (RLK_909t) as the 3/2
	# Zombie token.
	play = _UnlivingChampionCheck(SELF)


class RLK_554:
	"""Harkener of Dread"""

	# Taunt. Deathrattle: Summon a 6/6 Undead with Taunt.
	# Taunt set in data; deathrattle summons Drakkari Specter (RLK_554t,
	# a 6/6 Taunt Undead token from this same set).
	deathrattle = Summon(CONTROLLER, "RLK_554t")


class _ScourgeTrollExtraDeathrattle(TargetedAction):
	"""Scourge Troll — re-fire the `additional_deathrattles` once more
	after the normal deathrattle pipeline has resolved. The engine
	already runs each deathrattle once via card.deathrattles; we queue a
	second run only of the *added* ones (the printed text says
	"Deathrattles given to this minion trigger twice")."""

	TARGET = ActionArg()

	def do(self, source, target):
		for dr in list(target.additional_deathrattles):
			source.game.queue_actions(target, dr)


class RLK_912:
	"""Scourge Troll"""

	# Deathrattles given to this minion trigger twice.
	# Approximation: on this minion's death, re-queue its `additional_deathrattles`
	# a second time after the engine's normal pipeline. The printed text
	# scopes to *given* deathrattles only; Scourge Troll has no printed
	# deathrattle of its own, so `additional_deathrattles` is exactly the
	# right list. If the Troll never had any deathrattles attached, the
	# extra fire is a no-op.
	events = Death(SELF).after(
		_ScourgeTrollExtraDeathrattle(SELF),
	)


class RLK_913:
	"""Overlord Drakuru"""

	# Rush, Windfury. After this attacks and kills a minion, resurrect it
	# on your side. Rush / Windfury set in data; the resurrect lives in
	# events. Attack(SELF).after fires once Attack resolves; the custom
	# action checks whether the defender died and summons a copy.
	events = Attack(SELF).after(
		_DrakuruResurrect(SELF, Attack.DEFENDER),
	)


##
# Spells


class RLK_553:
	"""Prescience"""

	# Draw 2 minions. For each that costs (5) or more, summon a 2/3 Spirit
	# with Taunt. Token: Ghastly Apparition (RLK_553t).
	play = _PrescienceDraw(CONTROLLER)


class RLK_909:
	"""Deathweaver Aura"""

	# Give a minion "Deathrattle: Summon two 3/2 Zombies." Overload: (1)
	# In-data buff RLK_909e ("Voodoo Be With You") carries the deathrattle.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "RLK_909e")


class RLK_909e:
	# In-data "Voodoo Be With You" — Deathrattle: Summon two 3/2 Zombies.
	deathrattle = Summon(CONTROLLER, "RLK_909t") * 2


class RLK_909t:
	"""Drakkari Zombie"""


class RLK_910:
	"""Shadow Suffusion"""

	# Give your minions "Deathrattle: Deal 3 damage to a random enemy."
	# In-data buff RLK_910e ("Mojo Missile") carries the deathrattle.
	play = Buff(FRIENDLY_MINIONS, "RLK_910e")


class RLK_910e:
	# In-data "Mojo Missile" — Deathrattle: Deal 3 damage to a random enemy.
	deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 3)


class RLK_911:
	"""From De Other Side"""

	# Summon a copy of each minion in your hand. They attack random enemy
	# minions, then die.
	play = _FromDeOtherSide(CONTROLLER)


##
# Tokens


class RLK_553t:
	"""Ghastly Apparition"""

	# 2/3 Taunt token summoned by Prescience for each 5+ cost minion drawn.
	# Taunt set in data; no script needed beyond the class declaration.


class RLK_554t:
	"""Drakkari Specter"""

	# 6/6 Taunt Undead token summoned by Harkener of Dread's deathrattle.
	# Taunt set in data; no script needed.
