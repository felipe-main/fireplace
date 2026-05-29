from ..utils import *
from hearthstone.enums import Race
from ...dsl.random_picker import RandomOtherClassCollectible


##
# Weapons


class DEEP_014:
	"""Quick Pick"""

	# After your hero attacks, draw a card.
	events = Attack(FRIENDLY_HERO).after(Draw(CONTROLLER))


##
# Spells


class _RandomOtherClassRace(RandomOtherClassCollectible):
	"""Pick a random collectible MINION of a given race whose class is
	neither the controller's class nor Neutral. Used by Fool's Gold for
	its "Pirate from another class" / "Elemental from another class" pulls.

	(The printed card calls these "Golden" cards; golden is a purely
	cosmetic premium-art layer with no gameplay effect, and the engine has
	no premium concept, so the generated card is gameplay-identical to a
	normal copy — see engine_gaps.)"""

	def __init__(self, race, **kw):
		from hearthstone.enums import CardType
		super().__init__(**kw)
		self._race = race

	def clone(self, memo):
		ret = super().clone(memo)
		ret._race = self._race
		return ret

	def evaluate(self, source):
		from hearthstone.enums import CardClass, CardType
		from ... import cards as card_module
		controller_class = getattr(
			source.controller.hero, "card_class", CardClass.INVALID
		)
		filters = dict(collectible=True, type=CardType.MINION, race=self._race)
		if source.game.is_standard:
			filters["is_standard"] = True
		all_ids = card_module.db.filter(**filters)
		filtered = []
		for cid in all_ids:
			c = card_module.db[cid]
			classes = getattr(c, "classes", None) or [c.card_class]
			if controller_class in classes:
				continue
			if classes == [CardClass.NEUTRAL]:
				continue
			filtered.append(cid)
		if not filtered:
			return []
		return [source.game.random.choice(filtered)]


class DEEP_022:
	"""Fool's Gold"""

	# Get a random Golden Pirate and Elemental from other classes.
	play = (
		Give(CONTROLLER, _RandomOtherClassRace(Race.PIRATE)),
		Give(CONTROLLER, _RandomOtherClassRace(Race.ELEMENTAL)),
	)
