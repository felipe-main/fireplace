from ..utils import *


class _PlagiarizarrrCopyTop(TargetedAction):
	"""Plagiarizarrr — get a copy of the top card of your opponent's
	deck. Reads the LAST element of opp.deck as the "top" (engine
	convention: deck is a list; top of deck is end of list — same as
	the standard draw site)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		opp = ctrl.opponent
		if not opp.deck:
			return
		top = opp.deck[-1]
		source.game.cheat_action(source, [Give(ctrl, top.id)])


class _AmbientLightspawnBuff(TargetedAction):
	"""Ambient Lightspawn — Finale and Overheal: give another random
	friendly minion +2/+2. Both gates must be true; the Overheal flag
	is `_last_heal_overheal` stamped on the heal target by Heal.do."""

	TARGET = ActionArg()

	def do(self, source, target):
		if not source.play_finale:
			return
		# Overheal gate: this Finale Overheal happens when the play's
		# heal action overhealed. Ambient Lightspawn has a separate
		# heal (printed text: "Battlecry: Restore X Health to a friendly
		# minion") that we don't model here; check the most recently
		# overhealed target.
		# Approximation: rely on _last_heal_overheal stamped on any
		# friendly character within this same action_block.
		ctrl = source.controller
		overheal_seen = False
		for ent in list(ctrl.field) + [ctrl.hero]:
			if getattr(ent, "_last_heal_overheal", 0) > 0:
				overheal_seen = True
				break
		if not overheal_seen:
			return
		others = [m for m in ctrl.field if m is not source]
		if not others:
			return
		pick = source.game.random.choice(others)
		source.game.cheat_action(source, [Buff(pick, "JAM_024e")])


class _FunnelCakeOverheal(TargetedAction):
	"""Funnel Cake — restore 3 to a minion and its neighbours. For
	each one Overhealed, refresh a Mana Crystal. Per-target overheal
	count comes from `_last_heal_overheal` stamped by Heal.do."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target is None or target.type != CardType.MINION:
			return
		field = target.controller.field
		if target not in field:
			# Target died before resolution; skip.
			return
		idx = field.index(target)
		group = [target]
		if idx > 0:
			group.insert(0, field[idx - 1])
		if idx + 1 < len(field):
			group.append(field[idx + 1])
		overheals = 0
		for ent in group:
			source.game.cheat_action(source, [Heal(ent, 3)])
			if getattr(ent, "_last_heal_overheal", 0) > 0:
				overheals += 1
		if overheals <= 0:
			return
		# Refresh one Mana Crystal per overheal (cap at current
		# used_mana).
		ctrl = source.controller
		refresh = min(overheals, ctrl.used_mana)
		if refresh > 0:
			ctrl.used_mana -= refresh


##
# Minions

class JAM_023:
	"""Plagiarizarrr"""

	# Battlecry: Get a copy of the top card of your opponent's deck.
	play = _PlagiarizarrrCopyTop(CONTROLLER)


class JAM_024:
	"""Ambient Lightspawn"""

	# Finale and Overheal: Give another random friendly minion +2/+2.
	# Base card prints no other effect; the Finale+Overheal buff is
	# the entire battlecry.
	play = _AmbientLightspawnBuff(SELF)


class JAM_027:
	"""Fanboy"""

	# Choose One - Give a friendly minion +2 Attack and Rush; or
	# +2 Health and Lifesteal.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	choose = ("JAM_027a", "JAM_027b")


class JAM_027a:
	"""Zok Rocks!"""
	# +2 Attack and Rush
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "JAM_027ae"), GiveRush(TARGET)


JAM_027ae = buff(atk=2)


class JAM_027b:
	"""Poison Bloom!"""
	# +2 Health and Lifesteal
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Buff(TARGET, "JAM_027be"), GiveLifesteal(TARGET)


JAM_027be = buff(health=2)


##
# Spells

class JAM_022:
	"""Deafen"""

	# Silence a minion. Combo: Also deal 2 damage to it.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Silence(TARGET)
	combo = Silence(TARGET), Hit(TARGET, 2)


class JAM_025:
	"""Funnel Cake"""

	# Restore 3 Health to a minion and its neighbors. For each one
	# Overhealed, refresh a Mana Crystal.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _FunnelCakeOverheal(TARGET)


##
# Enchantments

JAM_024e = buff(atk=2, health=2)
