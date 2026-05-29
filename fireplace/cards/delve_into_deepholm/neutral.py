from ..utils import *


##
# The eight "random bonus effect" enchants (shared Deepholm/Showdown pool).
# Each grants +3/+3 and one keyword. Reused from the Showdown Chameleon
# pool (WW_810t1e1..WW_810t8e1). Iridescent Gyreworm hands a random one of
# these to each friendly minion on death.
_neutral_BONUS_EFFECTS = (
    "WW_810t1e1",  # +3/+3, Divine Shield
    "WW_810t2e1",  # +3/+3, Taunt
    "WW_810t3e1",  # +3/+3, Rush
    "WW_810t4e1",  # +3/+3, Windfury
    "WW_810t5e1",  # +3/+3, Stealth
    "WW_810t6e1",  # +3/+3, Poisonous
    "WW_810t7e1",  # +3/+3, Lifesteal
    "WW_810t8e1",  # +3/+3, Reborn
)


class _GyrewormBonusEffects(TargetedAction):
    """Iridescent Gyreworm deathrattle helper. Gives EACH friendly minion an
    independently-rolled random bonus effect (one of the eight enchants). A
    single Buff(FRIENDLY_MINIONS, RandomID(...)) would roll one enchant and
    stamp the same one on everybody, so we iterate and roll per minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        for minion in list(target.field):
            enchant = source.game.random.choice(_neutral_BONUS_EFFECTS)
            source.game.cheat_action(source, [Buff(minion, enchant)])


class _TherazaneDoubleElementals(TargetedAction):
    """Therazane deathrattle helper. Doubles the stats of every Elemental in
    the controller's hand AND deck by stamping DEEP_036e (which doubles via
    its apply()) on each, snapshotting nothing — DEEP_036e reads live stats.
    Imperative because Buff(FRIENDLY_HAND/DECK + ELEMENTAL, ...) would still
    work, but iterating keeps the per-card apply() clean across both zones."""

    TARGET = ActionArg()

    def do(self, source, target):
        elementals = [
            c for c in list(target.hand) + list(target.deck)
            if c.type == CardType.MINION and c.race == Race.ELEMENTAL
        ]
        for c in elementals:
            source.game.cheat_action(source, [Buff(c, "DEEP_036e")])


class _MaruutSummonAndGive(TargetedAction):
    """Maruut Stonebinder Discover callback. Summons the chosen Elemental and
    adds the other two offered candidates to hand."""

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, cards, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        source.game.cheat_action(source, [Summon(target, card.id)])
        for other in cards:
            if other is card:
                continue
            source.game.cheat_action(source, [Give(target, other.id)])


##
# Minions


class DEEP_006:
    """Stone Drake"""

    # <b>Divine Shield</b>, <b>Taunt</b>, <b>Lifesteal</b> Can't be targeted
    # by spells or Hero Powers.
    # DIVINE_SHIELD/TAUNT/LIFESTEAL live in data, but the two untargetable
    # tags are NOT parsed from the data card, so declare them here.
    tags = {
        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }


class DEEP_034:
    """Shale Spider"""

    # <b>Battlecry:</b> If you played an Elemental last turn, draw a card.
    play = ELEMENTAL_PLAYED_LAST_TURN & Draw(CONTROLLER)


class DEEP_035:
    """Iridescent Gyreworm"""

    # <b>Deathrattle:</b> Give each of your minions a random <b>bonus
    # effect</b>.
    deathrattle = _GyrewormBonusEffects(CONTROLLER)


class DEEP_036:
    """Therazane"""

    # <b>Taunt</b>  <b>Deathrattle:</b> Double the stats of all Elementals in
    # your hand and deck.
    # Taunt lives in data; the deathrattle doubles hand+deck Elementals.
    deathrattle = _TherazaneDoubleElementals(CONTROLLER)


class DEEP_036e:
    # Earthmother's Boon — Doubled Attack and Health.
    # Enchant exists in data; we override apply() to double live stats.
    def apply(self, target):
        self._xatk = target.atk * 2
        self._xhealth = target.health * 2

    atk = lambda self, _: self._xatk
    max_health = lambda self, _: self._xhealth


class DEEP_037:
    """Maruut Stonebinder"""

    # <b>Battlecry:</b> If your deck has no duplicates, <b>Discover</b> an
    # Elemental to summon. Add the others to your hand.
    powered_up = -FindDuplicates(FRIENDLY_DECK)
    play = powered_up & Discover(CONTROLLER, RandomElemental()).then(
        _MaruutSummonAndGive(Discover.TARGET, Discover.CARDS, Discover.CARD)
    )
