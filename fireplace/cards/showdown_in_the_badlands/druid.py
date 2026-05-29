"""Showdown in the Badlands — Druid cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions / helpers


class _CactusConstructSummonCopy(TargetedAction):
	"""Cactus Construct — after Discovering a 2-Cost minion, summon a copy
	of it and set the copy's stats to 1/2 (WW_818e "Wittle"). We stamp the
	stat-set enchant as a delta from the freshly-summoned copy's printed
	stats so the result is exactly 1/2 regardless of the source minion."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target is None:
			return
		ctrl = source.controller
		# Discovered card is a freshly-created entity (no enchants); summon a
		# plain copy by id, then set its stats to 1/2.
		source.game.cheat_action(source, [Summon(ctrl, target.id)])
		if not ctrl.field:
			return
		minion = list(ctrl.field)[-1]
		atk_delta = 1 - (minion.atk or 0)
		health_delta = 2 - (minion.max_health or 0)
		source.game.cheat_action(
			source,
			[Buff(minion, "WW_818e", atk=atk_delta, max_health=health_delta)],
		)


class _DragonGolemSummonCopies(TargetedAction):
	"""Dragon Golem — Battlecry: Summon a copy of this for each Dragon in
	your hand. We count Dragons in hand at resolution and summon that many
	plain copies of Dragon Golem (WW_822) alongside the played one."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		from hearthstone.enums import Race
		dragons = [
			c for c in ctrl.hand
			if c.type == CardType.MINION and Race.DRAGON in c.races
		]
		for _ in range(len(dragons)):
			if len(ctrl.field) >= 7:
				break
			source.game.cheat_action(source, [Summon(ctrl, "WW_822")])


class _FyeBumpDragonsSummoned(TargetedAction):
	"""Fye, the Setting Sun — bump the per-card `_dragons_summoned` counter
	each time the controller summons a Dragon. Fye reads this in cost_mod
	to discount itself by (1) per Dragon summoned this game. Fired from
	both Deck.events and Hand.events so the count is correct from game
	start through the moment Fye is played."""

	TARGET = ActionArg()

	def do(self, source, target):
		source._dragons_summoned = getattr(source, "_dragons_summoned", 0) + 1


class _FyeDragonsSummoned(LazyNum):
	"""Count of Dragons the controller has summoned this game, tracked on
	Fye via `_dragons_summoned` (bumped by the Deck/Hand summon listeners).
	Defaults to 0 before any Dragon is summoned."""

	def evaluate(self, source):
		return self.num(getattr(source, "_dragons_summoned", 0))


##
# Spells


class WW_816:
	"""Take to the Skies"""

	# Draw two Dragons. Give them +1/+1. ForceDraw against the deck's Dragon
	# pool; stamp WW_816e (+1/+1) on each freshly-drawn Dragon.
	play = (
		ForceDraw(RANDOM(FRIENDLY_DECK + DRAGON)).then(
			Buff(ForceDraw.TARGET, "WW_816e"),
		),
		ForceDraw(RANDOM(FRIENDLY_DECK + DRAGON)).then(
			Buff(ForceDraw.TARGET, "WW_816e"),
		),
	)


class WW_816e:
	# In-data "Soaaaring, Flyyyying" — +1/+1, but stats aren't parsed.
	tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class WW_816t:
	"""Happy Whelp"""

	# Vanilla 1/2 Taunt token (Taunt is in data).


class WW_818:
	"""Cactus Construct"""

	# Discover a 2-Cost minion. Summon a 1/2 copy of it.
	requirements = {PlayReq.REQ_NUM_MINION_SLOTS: 0}
	play = Discover(CONTROLLER, RandomMinion(cost=2)).then(
		_CactusConstructSummonCopy(Discover.CARD)
	)


class WW_818e:
	# In-data "Wittle" — Stats set to 1/2. Applied as a runtime delta
	# (atk/max_health stamped via Buff kwargs) so no static stats here.
	tags = {}


class WW_821:
	"""Dragon Tales"""

	# Choose One: Get two random Dragons that cost (5) or less; or Get two
	# that cost more than (5). Sub-cards WW_821t1 / WW_821t2 carry the two
	# effects.
	choose = ("WW_821t1", "WW_821t2")


class WW_821t1:
	"""Short Stories"""

	# Get two random Dragons that cost (5) or less.
	play = Give(CONTROLLER, RandomDragon(cost=list(range(0, 6)))) * 2


class WW_821t2:
	"""Tall Tales"""

	# Get two random Dragons that cost more than (5).
	play = Give(CONTROLLER, RandomDragon(cost=list(range(6, 31)))) * 2


class WW_823:
	"""Rehydrate"""

	# Restore #7 Health. Quickdraw: Refresh 2 Mana Crystals. The base heal
	# always resolves; the Quickdraw bonus refills 2 used crystals.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
	}
	play = (
		Heal(TARGET, 7),
		QUICKDRAW & FillMana(CONTROLLER, 2),
	)


##
# Minions


class WW_819:
	"""Splish-Splash Whelp"""

	# Battlecry: If you're holding a Dragon, gain an empty Mana Crystal.
	play = HOLDING_DRAGON & GainEmptyMana(CONTROLLER, 1)


class WW_820:
	"""Spinetail Drake"""

	# Battlecry: If you're holding a Dragon, deal 5 damage to an enemy
	# minion.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_ENEMY_TARGET: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = HOLDING_DRAGON & Hit(TARGET, 5)


class WW_822:
	"""Dragon Golem"""

	# Taunt. Battlecry: Summon a copy of this for each Dragon in your hand.
	# Taunt is in data; the battlecry summons WW_822 copies.
	play = _DragonGolemSummonCopies(CONTROLLER)


class WW_824:
	"""Rheastrasza"""

	# Battlecry: If your deck has no duplicates, summon the Purified Dragon
	# Nest (WW_824t).
	powered_up = -FindDuplicates(FRIENDLY_DECK)
	play = powered_up & Summon(CONTROLLER, "WW_824t")


class WW_824t:
	"""Purified Dragon Nest"""

	# At the start of your turn, Discover a Dragon. It costs (4) less.
	# Discover a Dragon, then stamp WW_824e (-4 cost) on the chosen card.
	events = OWN_TURN_BEGIN.on(
		Discover(CONTROLLER, RandomDragon()).then(
			Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "WW_824e")),
		),
	)


class WW_824e:
	# In-data "Happily Hatched" — Costs (4) less. COST not parsed; declare.
	tags = {GameTag.COST: -4}


class WW_825:
	"""Fye, the Setting Sun"""

	# Rush, Lifesteal, Taunt (all in data). Costs (1) less for each Dragon
	# you've summoned this game. We track the count via a per-card counter
	# bumped whenever the controller summons a Dragon (Deck + Hand events),
	# and discount in cost_mod.
	cost_mod = -_FyeDragonsSummoned()

	class Deck:
		events = Summon(CONTROLLER, DRAGON).after(
			_FyeBumpDragonsSummoned(SELF)
		)

	class Hand:
		events = Summon(CONTROLLER, DRAGON).after(
			_FyeBumpDragonsSummoned(SELF)
		)


class WW_826:
	"""Desert Nestmatron"""

	# Taunt (in data). Battlecry: If you're holding a Dragon, refresh 4 Mana
	# Crystals.
	play = HOLDING_DRAGON & FillMana(CONTROLLER, 4)
