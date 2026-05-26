from ..utils import *


##
# Concoction token ids (the 5 base Concoctions Concoctor / Potion Belt /
# Vile Apothecary / Potionmaster Putricide draw from).  The "Mixed" tokens
# (e.g. RLK_570t1t1) are only reachable via two-Concoction interactions,
# not from a "random Concoction" pool.
_CONCOCTIONS = (
	"RLK_570t1",  # Slimy Concoction
	"RLK_570t2",  # Dreadful Concoction
	"RLK_570t3",  # Bubbling Concoction
	"RLK_570t4",  # Hazy Concoction
	"RLK_570t5",  # Gleaming Concoction
)

RandomConcoction = RandomID(*_CONCOCTIONS)


##
# Custom actions


class _ScourgeIllusionistCopy(TargetedAction):
	"""Scourge Illusionist deathrattle — pick a random other Deathrattle
	minion in the controller's deck, give a copy of it to hand, and stamp
	the 4/4 + cost-reduction enchant (RLK_217e) on that copy.  Wrapped as
	a custom action so we can scope the buff to the freshly-given card
	(Give.CARD is consumed inside the .then chain)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		pool = [
			c for c in ctrl.deck
			if c.type == CardType.MINION and getattr(c, "has_deathrattle", False)
		]
		if not pool:
			return
		picked = source.game.random.choice(pool)
		source.game.cheat_action(
			source,
			[Give(ctrl, picked.id).then(Buff(Give.CARD, "RLK_217e"))],
		)


class _NoxiousInfiltratorCheck(TargetedAction):
	"""Noxious Infiltrator — "If a friendly Undead died after your last
	turn, deal 1 damage to a minion." Reads the engine-managed
	`_undead_deaths_in_window` tracker."""

	TARGET = ActionArg()

	def do(self, source, target):
		if source.controller._undead_deaths_in_window:
			source.game.cheat_action(source, [Hit(target, 1)])


class _GhoulishAlchemistArm(TargetedAction):
	"""Ghoulish Alchemist — flip a per-turn controller flag so the next
	Concoction the controller plays costs 0.  The actual cost-set lives
	on each Concoction token via a Hand.update aura gated on this flag,
	plus the flag clears as soon as a Concoction leaves the hand (handled
	by _ConcoctionPlayClearsFlag in each Concoction class)."""

	TARGET = ActionArg()

	def do(self, source, target):
		target.next_concoction_costs_zero = True
		source.game.cheat_action(source, [Buff(target, "RLK_570e4")])


##
# Minions


class RLK_216:
	"""Rotten Rodent"""

	# Battlecry: Reduce the Cost of all Deathrattle cards in your deck by (1).
	play = Buff(FRIENDLY_DECK + DEATHRATTLE, "RLK_216e")


class RLK_217:
	"""Scourge Illusionist"""

	# Deathrattle: Add a 4/4 copy of another Deathrattle minion in your
	# deck to your hand. It costs (4) less.
	deathrattle = _ScourgeIllusionistCopy(SELF)


class RLK_529:
	"""Noxious Infiltrator"""

	# Poisonous (in data). Battlecry: If a friendly Undead died after
	# your last turn, deal 1 damage to a minion.
	requirements = {
		PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = _NoxiousInfiltratorCheck(TARGET)


class RLK_568:
	"""Concoctor"""

	# Battlecry: Add a random Concoction to your hand.
	play = Give(CONTROLLER, RandomConcoction)


class RLK_570:
	"""Ghoulish Alchemist"""

	# Battlecry: Your next Concoction costs (0).
	play = _GhoulishAlchemistArm(CONTROLLER)


class RLK_571:
	"""Vile Apothecary"""

	# At the end of your turn, add a random Concoction to your hand.
	events = OWN_TURN_END.on(Give(CONTROLLER, RandomConcoction))


class RLK_572:
	"""Potionmaster Putricide"""

	# After a minion dies, add a Concoction to your hand.
	events = Death(MINION).after(Give(CONTROLLER, RandomConcoction))


##
# Spells


class RLK_567:
	"""Shadow of Demise"""

	# Each time you cast a spell, transform this into a copy of it.
	# 0-cost spell that lives in hand and morphs into whatever spell the
	# controller casts next (mirrors Ring of Tides / TSC_641ta).  The
	# "Each time" wording means it keeps mutating into successive spells
	# while it remains in hand.
	class Hand:
		events = Play(CONTROLLER, SPELL - SELF).after(Morph(SELF, Play.CARD))


class RLK_569:
	"""Potion Belt"""

	# Discover 2 Concoctions.  Two consecutive Discovers over the 5
	# Concoction tokens — each pick goes to hand via the standard
	# DISCOVER(...) wrapper.
	play = DISCOVER(RandomConcoction), DISCOVER(RandomConcoction)


class RLK_573:
	"""Ghostly Strike"""

	# Deal $1 damage. Combo: Draw a card.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
	}
	play = Hit(TARGET, 1)
	combo = Hit(TARGET, 1), Draw(CONTROLLER)


##
# Enchantments


class RLK_216e:
	# In-data buff "Rotten" — -1 cost on a Deathrattle deck card.  The
	# COST tag isn't pre-populated in parsed data, so declare it here.
	tags = {GameTag.COST: -1}


class RLK_217e:
	# In-data buff "Illusion" — set stats to 4/4 and reduce cost by 4.
	# Stats are SET (not deltas); we use SET() for atk/health and
	# COST: -4 for the delta.  The COST: -100 trick (Sunken City Ring of
	# Tides) is for "set cost to 0"; here we want a -4 delta.
	tags = {
		GameTag.ATK: SET(4),
		GameTag.HEALTH: SET(4),
		GameTag.COST: -4,
	}


class RLK_570e:
	# In-data buff "Yellow Potion" — placeholder for the Mixed
	# Concoction recipe-tracking enchant.  Unused by the base 5 tokens
	# (which are scripted to just resolve their effect).  Declared so any
	# Buff(..., "RLK_570e") call from data resolves.
	tags = {}


class RLK_570e4:
	# In-data buff "Doctored" — set on the controller while
	# `next_concoction_costs_zero` is armed (cosmetic stamp; cost-set is
	# applied via the Hand.update aura on each Concoction token).
	tags = {}


##
# Concoction tokens (RLK_570t1..t5).  Each carries its own scripted
# effect when cast.  The "Mix together with another Concoction" rider on
# every base Concoction's printed text is NOT modeled — these scripts
# only implement the standalone effect (the printed "Add another
# Concoction to your hand to mix together!" combo is TODO; the Mixed
# tokens RLK_570t1t1, RLK_570t3t, etc. are never produced).
#
# The "Your next Concoction costs (0)" aura from Ghoulish Alchemist sets
# a controller flag `next_concoction_costs_zero` that any future Play.do
# wire-up can consume.  The actual cost substitution is TODO — analogous
# to Anub'Rekhan / Blood Crusader's per-turn cost flags.


class RLK_570t1:
	"""Slimy Concoction"""

	# Summon a random 3-Cost minion.
	play = Summon(CONTROLLER, RandomMinion(cost=3))


class RLK_570t2:
	"""Dreadful Concoction"""

	# Destroy a random enemy minion.
	play = Destroy(RANDOM(ENEMY_MINIONS))


class RLK_570t3:
	"""Bubbling Concoction"""

	# Deal $3 damage.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
	}
	play = Hit(TARGET, 3)


class RLK_570t4:
	"""Hazy Concoction"""

	# Add a card to your hand from another class. It costs (3) less.
	# Approximation: random collectible from any class other than the
	# controller's, stamped with a -3 cost enchant.
	play = Give(CONTROLLER, RandomOtherClassCollectible()).then(
		Buff(Give.CARD, "RLK_570t4e")
	)


@custom_card
class RLK_570t4e:
	tags = {
		GameTag.CARDNAME: "Hazy Concoction",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: -3,
	}


class RLK_570t5:
	"""Gleaming Concoction"""

	# Draw 2 cards.
	play = Draw(CONTROLLER) * 2


##
# Mixed Concoction tokens — produced by the Give-time Mix hook in
# actions.py (CONCOCTION_MIXES table). Each combines the standalone
# effects of its two ingredient Concoctions. Targeting requirements
# only apply to mixes that include the Bubbling (3 damage) effect.


class RLK_570t1t1:
	"""Mixed Concoction"""

	# Slimy + Hazy: summon a random 3-cost minion + add a card from
	# another class (-3 cost).
	play = (
		Summon(CONTROLLER, RandomMinion(cost=3)),
		Give(CONTROLLER, RandomOtherClassCollectible()).then(
			Buff(Give.CARD, "RLK_570t4e")
		),
	)


class RLK_570t1t2:
	"""Mixed Concoction"""

	# Slimy + Dreadful: summon a random 3-cost minion + destroy random enemy.
	play = (
		Summon(CONTROLLER, RandomMinion(cost=3)),
		Destroy(RANDOM(ENEMY_MINIONS)),
	)


class RLK_570t1t3:
	"""Mixed Concoction"""

	# Slimy + Bubbling: 3 damage to a target + summon a random 3-cost minion.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 3),
		Summon(CONTROLLER, RandomMinion(cost=3)),
	)


class RLK_570t1t4:
	"""Mixed Concoction"""

	# Double Slimy: summon two random 3-cost minions.
	play = Summon(CONTROLLER, RandomMinion(cost=3)) * 2


class RLK_570t2t1:
	"""Mixed Concoction"""

	# Dreadful + Bubbling: 3 damage + destroy random enemy minion.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 3),
		Destroy(RANDOM(ENEMY_MINIONS)),
	)


class RLK_570t2t2:
	"""Mixed Concoction"""

	# Double Dreadful: destroy two random enemy minions.
	play = Destroy(RANDOM(ENEMY_MINIONS)) * 2


class RLK_570t3t:
	"""Mixed Concoction"""

	# Double Bubbling: deal 3 damage, twice.
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = Hit(TARGET, 3) * 2


class RLK_570t4t1:
	"""Mixed Concoction"""

	# Hazy + Dreadful: add other-class card (-3 cost) + destroy random enemy.
	play = (
		Give(CONTROLLER, RandomOtherClassCollectible()).then(
			Buff(Give.CARD, "RLK_570t4e")
		),
		Destroy(RANDOM(ENEMY_MINIONS)),
	)


class RLK_570t4t2:
	"""Mixed Concoction"""

	# Hazy + Bubbling: 3 damage + add other-class card (-3 cost).
	requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
	play = (
		Hit(TARGET, 3),
		Give(CONTROLLER, RandomOtherClassCollectible()).then(
			Buff(Give.CARD, "RLK_570t4e")
		),
	)


class RLK_570t4t3:
	"""Mixed Concoction"""

	# Double Hazy: add two other-class cards (-3 cost each).
	play = (
		Give(CONTROLLER, RandomOtherClassCollectible()).then(
			Buff(Give.CARD, "RLK_570t4e")
		),
	) * 2


class RLK_570tt1:
	"""Mixed Concoction"""

	# Gleaming + Slimy: draw 2 + summon a random 3-cost minion.
	play = (
		Draw(CONTROLLER) * 2,
		Summon(CONTROLLER, RandomMinion(cost=3)),
	)
