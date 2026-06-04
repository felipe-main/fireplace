from copy import copy, deepcopy

from hearthstone.enums import CardType, Race, Rarity

from .lazynum import LazyValue
from .selector import Selector


# Reprint namespaces: a printable card can appear in the data under its original
# id AND a Core-set reprint (CORE_* / Core_*) AND/OR a Legacy reprint (VAN_*).
_REPRINT_PREFIXES = ("CORE_", "Core_", "VAN_")


def _bare_card_id(cid):
    """Strip a reprint namespace so a card's original id and its Core/Legacy
    reprints collapse to one key (mirrors the CORE_ stripping in
    cards.get_script_definition)."""
    for prefix in _REPRINT_PREFIXES:
        if cid.startswith(prefix):
            return cid[len(prefix):]
    return cid


def _dedupe_reprints(ids):
    """Collapse reprint aliases so each printable card appears once in a pool.
    Without this, a card with a Core (CORE_*) and/or Legacy (VAN_*) reprint in
    addition to its original printing would sit in a Wild pool under two or three
    ids and be picked that many times more often.

    When a group has more than one id, pick a single representative by rank:
    a Standard-legal printing first, then the bare (original) id, then the first
    seen. Preferring the Standard-legal id keeps a Wild pool's representative for
    a card identical to the id a Standard pool uses for it. Order is preserved
    (deterministic)."""
    from .. import cards as _c

    def rank(cid):
        card = _c.db[cid] if cid in _c.db else None
        is_standard = bool(getattr(card, "is_standard", False))
        is_bare = cid == _bare_card_id(cid)
        return (is_standard, is_bare)

    chosen = {}
    order = []
    for cid in ids:
        key = _bare_card_id(cid)
        if key not in chosen:
            chosen[key] = cid
            order.append(key)
        elif rank(cid) > rank(chosen[key]):
            chosen[key] = cid
    return [chosen[k] for k in order]


class RandomCardPicker(LazyValue):
    """
    Store filters and generate a random card matching the filters on pick()
    Constructor takes a single global set of filters, default weighting of 1
    Additional weighted filter sets can be added with add(),
    these will be merged with the global filters
    """

    def __init__(self, **filters):
        self.weights = []
        self.weightedfilters = []
        self.filters = filters
        self.count = 1

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.filters)

    def clone(self, memo):
        # deepcopy functionality is here because parent __deepcopy__ is
        # difficult to call from subclasses
        ret = copy(self)
        ret.weights = list(self.weights)
        ret.filters = deepcopy(self.filters, memo)
        ret.weightedfilters = deepcopy(self.weightedfilters, memo)
        ret.count = self.count

        return ret

    def __deepcopy__(self, memo):
        return self.clone(memo)

    # select number of cards to fetch
    def __mul__(self, other):
        ret = deepcopy(self)
        ret.count = other
        return ret

    # add a filter set
    def copy_with_weighting(self, weight, **filters):
        ret = deepcopy(self)
        ret.weights.append(weight)
        ret.weightedfilters.append(filters)
        return ret

    def find_cards(self, source, **filters):
        """
        Generate a card pool with all cards matching specified filters
        """
        if not filters:
            new_filters = self.filters.copy()
        else:
            new_filters = filters.copy()

        # "From the past" pools (cards whose text says e.g. "Get a random Demon
        # from the past") draw from the full historic Wild pool — every
        # collectible card ever printed, INCLUDING today's Standard cards. The
        # from_past flag suppresses the auto-Standard narrowing below so the
        # pool stays Wild-inclusive even inside a Standard game. It is popped
        # here so it is never passed on as a card-attribute filter.
        from_past = new_filters.pop("from_past", False)

        if source.game.is_standard and not from_past and "is_standard" not in new_filters:
            new_filters["is_standard"] = True

        for k, v in new_filters.items():
            if isinstance(v, LazyValue):
                new_filters[k] = v.evaluate(source)
            elif isinstance(v, Selector):
                new_filters[k] = v.eval(source.game, source)

        from .. import cards

        pool = cards.filter(**new_filters)
        # A "from the past" pool draws from the full historic Wild card set, where
        # a printable card can appear under its original id AND its CORE_/VAN_
        # reprint ids — weighting it 2-3x. Collapse reprint aliases so each card
        # is offered exactly once (e.g. Time-Lost Glaive's Demon pool 223 -> 181).
        # Scoped to from_past: it is these pools the effect is defined over, and
        # confining the dedup here keeps every other random pool's outcomes
        # (and RNG stream) untouched.
        if from_past:
            pool = _dedupe_reprints(pool)
        return pool

    def find_card_sets(self, source, cards):
        if cards:
            # Use specific card list if given
            self.weights = [1]
            if "exclude" in self.filters:
                exclude = self.filters["exclude"]
                if isinstance(exclude, LazyValue):
                    exclude = exclude.evaluate(source)
                elif isinstance(exclude, Selector):
                    exclude = exclude.eval(source.game, source)
                exclude = [card.id for card in exclude]
                cards = [card for card in cards if card not in exclude]
            return [list(cards)]
        elif not self.weightedfilters:
            # Use global filters if no weighted filter sets given
            self.weights = [1]
            return [self.find_cards(source)]
        else:
            # Otherwise find cards for each set of filters
            # add the global filters to each set of filters
            wf = [{**x, **self.filters} for x in self.weightedfilters]
            return [self.find_cards(source, **x) for x in wf]

    def evaluate(self, source, cards=None) -> str:
        """
        This picks from a single combined card pool without replacement,
        weighting each filtered set of cards against the total
        """
        card_sets = self.find_card_sets(source, cards)
        from ..utils import weighted_card_choice

        # get weighted sample of card pools
        return weighted_card_choice(source, self.weights, card_sets, self.count)


RandomCard = lambda **kw: RandomCardPicker(**kw)
RandomCollectible = lambda **kw: RandomCardPicker(collectible=True, **kw)
RandomMinion = lambda **kw: RandomCollectible(type=CardType.MINION, **kw)
RandomBeast = lambda **kw: RandomMinion(race=Race.BEAST, **kw)
RandomDemon = lambda **kw: RandomMinion(race=Race.DEMON, **kw)
RandomDragon = lambda **kw: RandomMinion(race=Race.DRAGON, **kw)
RandomMech = lambda **kw: RandomMinion(race=Race.MECHANICAL, **kw)
RandomMurloc = lambda **kw: RandomMinion(race=Race.MURLOC, **kw)
RandomSpell = lambda **kw: RandomCollectible(type=CardType.SPELL, **kw)
RandomTotem = lambda **kw: RandomCardPicker(race=Race.TOTEM, **kw)
RandomElemental = lambda **kw: RandomMinion(race=Race.ELEMENTAL, **kw)
RandomWeapon = lambda **kw: RandomCollectible(type=CardType.WEAPON, **kw)
RandomLegendaryMinion = lambda **kw: RandomMinion(rarity=Rarity.LEGENDARY, **kw)
RandomSparePart = lambda: RandomCardPicker(spare_part=True)


class RandomEntourage(RandomCardPicker):
    def evaluate(self, source):
        return super().evaluate(source, source.entourage)


class RandomID(RandomCardPicker):
    def __init__(self, *args, **kw):
        super().__init__(**kw)
        self._cards = args

    def clone(self, memo):
        ret = super().clone(memo)
        ret._cards = deepcopy(self._cards, memo)
        return ret

    def evaluate(self, source):
        return super().evaluate(source, self._cards)


class RandomOtherClassCollectible(RandomCardPicker):
    """Pick a random collectible card whose primary class is neither the
    source's controller's hero class nor Neutral. Used by Hazy Concoction
    + Mixed Concoction tokens for the "card from another class" effect."""

    def __init__(self, **kw):
        from hearthstone.enums import CardType
        kw.setdefault("collectible", True)
        super().__init__(**kw)

    def evaluate(self, source):
        from hearthstone.enums import CardClass
        from .. import cards as card_module
        controller_class = getattr(source.controller.hero, "card_class", CardClass.INVALID)
        all_ids = card_module.db.filter(collectible=True)
        filtered = []
        for cid in all_ids:
            c = card_module.db[cid]
            classes = getattr(c, "classes", None) or [c.card_class]
            # Exclude any card whose class list contains the controller's
            # class (multiclass cards with the controller's class are also
            # excluded — they're "your class" cards) or only Neutral.
            if controller_class in classes:
                continue
            if classes == [CardClass.NEUTRAL]:
                continue
            filtered.append(cid)
        if not filtered:
            return []
        return [source.game.random.choice(filtered)]
