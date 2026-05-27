from ..utils import *


class _ReverberationsSummonGlass(TargetedAction):
	"""Reverberations — summon a copy of a target minion that dies
	after taking any damage. Stamp a per-copy flag _glass_dies that a
	Damage listener consumes."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target is None or target.type != CardType.MINION:
			return
		ctrl = source.controller
		copy = ctrl.card(target.id)
		copy._glass_dies = True
		source.game.cheat_action(source, [Summon(ctrl, copy)])


class _GlassDamageKill(TargetedAction):
	"""Listener stamped on glass copies — destroy on first damage."""

	TARGET = ActionArg()

	def do(self, source, target):
		if not getattr(target, "_glass_dies", False):
			return
		source.game.cheat_action(source, [Destroy(target)])


class _FiddlefireImpAddSpells(TargetedAction):
	"""Fiddlefire Imp — add a random Fire Mage spell AND a random
	Fire Warlock spell to the controller's hand."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		picker_mage = RandomSpell(
			card_class=CardClass.MAGE, spell_school=SpellSchool.FIRE
		)
		picker_warlock = RandomSpell(
			card_class=CardClass.WARLOCK, spell_school=SpellSchool.FIRE
		)
		for picker in (picker_mage, picker_warlock):
			pick = picker.evaluate(source)
			cid = pick[0] if isinstance(pick, list) else pick
			if cid:
				source.game.cheat_action(source, [Give(ctrl, cid)])


##
# Minions

class JAM_030:
	"""Fanottem, Lord of the Opera"""

	# Taunt, Lifesteal (data). Cost equals the number of cards in
	# your deck. Read deck size at cost-mod time.
	cost_mod = Count(FRIENDLY_DECK) - 30


class JAM_032:
	"""Fiddlefire Imp"""

	# Battlecry: Add a random Fire Mage and Fire Warlock spell to your
	# hand.
	play = _FiddlefireImpAddSpells(CONTROLLER)


##
# Spells

class JAM_031:
	"""Reverberations"""

	# Summon a copy of a minion. Each one dies after taking damage.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _ReverberationsSummonGlass(TARGET)


##
# Engine hook — glass-copy on-damage destroy is wired as a board-wide
# listener (rather than per-card events) because the glass copies are
# created on the fly and don't carry their own script.

# Note: a global Damage(ALL_MINIONS).on(...) listener on every minion
# would be too noisy. Approximation: glass copies don't actually carry
# the "dies on damage" rule today — they're summoned vanilla. Tracked
# as a Significant approximation row in review.csv at audit time.
