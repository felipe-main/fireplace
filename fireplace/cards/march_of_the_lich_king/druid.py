from ..utils import *


##
# Custom actions


class _WitherSteal(TargetedAction):
	"""Wither — each friendly Undead on the board steals 1 Attack and 1
	Health from the target. Implemented as a per-Undead loop: each one
	gets a +1/+1 Withered buff (RLK_655e), and the target absorbs 1
	damage per Undead. If multiple Undead are present, the target may
	die mid-effect — that's fine, the remaining buffs still resolve
	(matches the printed "Each friendly Undead steals 1/1" wording)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		undead = UNDEAD.eval(ctrl.field, source)
		if not undead:
			return
		for u in undead:
			source.game.cheat_action(source, [Buff(u, "RLK_655e")])
			source.game.cheat_action(source, [Hit(target, 1)])


class _ElderNadoxAbsorb(TargetedAction):
	"""Elder Nadox — destroy a chosen friendly Undead and snapshot its
	Attack, then buff every other friendly minion by that Attack via
	RLK_658e. The target selector handles "a friendly Undead"; we read
	its atk before queuing the Destroy so the buff value is captured
	even after the minion leaves play."""

	TARGET = ActionArg()

	def do(self, source, target):
		atk = target.atk
		source.game.cheat_action(source, [Destroy(target)])
		if atk <= 0:
			return
		ctrl = source.controller
		for m in list(ctrl.field):
			source.game.cheat_action(
				source, [Buff(m, "RLK_658e", atk=atk, max_health=0)]
			)


class _AnubRekhanArmCostMode(TargetedAction):
	"""Anub'Rekhan — flip a per-turn controller flag so the next minions
	this turn are paid in Armor instead of Mana. The cost-substitution
	itself requires a hook in Play.do (analogous to Blood Crusader's
	next_paladin_minion_costs_health_this_turn); we set the flag so the
	engine wire-up lands without a script change. Also stamp the
	RLK_659e enchant on the controller for parity with the printed
	enchant."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.minions_cost_armor_this_turn = True


class _NerubianFlyerCheck(TargetedAction):
	"""Nerubian Flyer — "If a friendly Undead died after your last turn,
	summon a 2/2 Nerubian." Reads the controller's precise
	`_undead_deaths_in_window` tracker (engine-managed in actions.py
	Death.do + game.py end_turn_cleanup)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		if ctrl._undead_deaths_in_window:
			source.game.cheat_action(source, [Summon(ctrl, "RLK_956t")])


##
# Minions


class RLK_650:
	"""Lingering Zombie"""

	# Deathrattle: Summon a 1/1 Disarmed Zombie with
	# "Deathrattle: Summon a 1/1 Zombie."
	deathrattle = Summon(CONTROLLER, "RLK_650t")


class RLK_650t:
	"""Disarmed Zombie"""

	# Deathrattle: Summon a 1/1 Zombie.
	deathrattle = Summon(CONTROLLER, "RLK_650t2")


class RLK_650t2:
	"""Unarmed Zombie"""


class RLK_651:
	"""Crypt Keeper"""

	# Taunt. Costs (1) less for each Armor you have.
	cost_mod = -Attr(FRIENDLY_HERO, GameTag.ARMOR)


class RLK_657:
	"""Underking"""

	# Rush. Battlecry and Deathrattle: Gain 6 Armor.
	play = GainArmor(FRIENDLY_HERO, 6)
	deathrattle = GainArmor(FRIENDLY_HERO, 6)


class RLK_658:
	"""Elder Nadox"""

	# Battlecry: Destroy a friendly Undead. Your minions gain its Attack.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_TARGET_WITH_RACE: Race.UNDEAD,
	}
	play = _ElderNadoxAbsorb(TARGET)


class RLK_659:
	"""Anub'Rekhan"""

	# Battlecry: Gain 8 Armor. This turn, your minions cost Armor
	# instead of Mana.
	# Approximation: gain 8 Armor + set per-turn controller flag
	# `minions_cost_armor_this_turn`. The cost-substitution itself is
	# TODO — needs a hook in Play.do that consumes Armor instead of
	# Mana when the flag is set.
	play = (
		GainArmor(FRIENDLY_HERO, 8),
		_AnubRekhanArmCostMode(CONTROLLER),
		Buff(CONTROLLER, "RLK_659e"),
	)


class RLK_956:
	"""Nerubian Flyer"""

	# Battlecry: If a friendly Undead died after your last turn, summon
	# a 2/2 Nerubian.
	play = _NerubianFlyerCheck(SELF)


class RLK_956t:
	"""Nerubian Skitterer"""


##
# Spells


class RLK_652:
	"""Unending Swarm"""

	# Resurrect all friendly minions that cost (2) or less.
	# Copy() preserves printed/base stats (standard resurrect idiom).
	play = Summon(
		CONTROLLER,
		Copy(FRIENDLY + KILLED + MINION + (COST <= 2)),
	)


class RLK_654:
	"""Beetlemancy"""

	# Choose One - Gain 12 Armor; or Summon two 3/3 Beetles with Taunt.
	choose = ("RLK_654a", "RLK_654b")


class RLK_654a:
	"""Beetle Juice"""

	# Gain 12 Armor.
	play = GainArmor(FRIENDLY_HERO, 12)


class RLK_654b:
	"""Bug Snacks"""

	# Summon two 3/3 Beetles with Taunt.
	play = Summon(CONTROLLER, "RLK_654t") * 2


class RLK_654t:
	"""Beetle"""


class RLK_655:
	"""Wither"""

	# Choose a minion. Each friendly Undead steals 1 Attack and Health
	# from it.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _WitherSteal(TARGET)


class RLK_656:
	"""Chitinous Plating"""

	# Gain 4 Armor. At the start of your next turn, gain 4 more.
	# Stamp the controller with the in-data Molting enchant (RLK_656e)
	# so the delayed armor fires at OWN_TURN_BEGIN. The enchant carries
	# the trigger via its own `events`.
	play = GainArmor(FRIENDLY_HERO, 4), Buff(CONTROLLER, "RLK_656e")


##
# Enchantments


class RLK_655e:
	# In-data buff "Withered" — Reduced stats. Wither uses it as a
	# +1/+1 stat buff on the friendly Undead doing the stealing.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class RLK_656e:
	# In-data buff "Molting" — at the start of your next turn, gain 4
	# Armor, then expire. One-turn delayed armor; destroy after firing
	# so it doesn't trigger again next turn.
	events = OWN_TURN_BEGIN.on(GainArmor(FRIENDLY_HERO, 4), Destroy(SELF))


class RLK_658e:
	# In-data buff "Might of Nadox" — ATK is supplied at runtime via
	# Buff(..., atk=) kwargs (mirrors REV_248k pattern). No static
	# stats here.
	tags = {}


class RLK_659e:
	# In-data buff "Hardened Carapace" — TAG_ONE_TURN_EFFECT in data so
	# the engine auto-clears it at end of turn. The cost-in-armor
	# substitution itself is TODO (handled via
	# `minions_cost_armor_this_turn` controller flag).
	tags = {}
