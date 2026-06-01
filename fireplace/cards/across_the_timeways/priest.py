from ..utils import *

# Shared set-wide Dark Gift granter (random Nightmare keyword Bonus Effect).
# Reused from the Emerald Dream package — Wings of Eternity (END_027) grants a
# Dark Gift to its Discovered Dragon exactly like the EDR Dark-Gift cards.
from ..emerald_dream.neutral import _GiveDarkGift


##
# Minions


class TIME_037:
    """Disciple of the Dove"""

    # Battlecry: Draw a minion. Give minions in your hand +2 Health.
    play = (
        ForceDraw(RANDOM(FRIENDLY_DECK + MINION)),
        Buff(FRIENDLY_HAND + MINION, "TIME_037e"),
    )


TIME_037e = buff(health=2)


class TIME_427:
    """Cleansing Lightspawn"""

    # Lifesteal. Battlecry: Deal damage to an enemy minion equal to this
    # minion's Health. (No PlayRequirement in data -> auto-targets a random
    # enemy minion; Lifesteal on this minion heals from the battlecry damage.)
    play = Hit(RANDOM(ENEMY_MINIONS), CURRENT_HEALTH(SELF))


@custom_card
class TIME_429e:
    # Override enchant: pins Attack and Health to the higher of the target's
    # two stats at apply-time. Mirrors REV_250e (Pelagos) — the lambdas
    # override (not add) the underlying stats.
    tags = {
        GameTag.CARDNAME: "Divine Augur Buff",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: self._higher
    max_health = lambda self, i: self._higher

    def apply(self, target):
        self._higher = max(target.atk, target.max_health)
        # If health is being raised, clear damage so new max == new current.
        if self._higher > target.max_health:
            target.damage = 0


class TIME_429:
    """Divine Augur"""

    # Battlecry: Set the Attack and Health of every minion in your hand to
    # the higher of the two stats.
    play = Buff(FRIENDLY_HAND + MINION, "TIME_429e")


class TIME_431:
    """Amber Priestess"""

    # Taunt. Battlecry: Restore Health to a character equal to this minion's
    # Health. (No PlayRequirement in data -> heals the friendly hero.)
    play = Heal(FRIENDLY_HERO, CURRENT_HEALTH(SELF))


class TIME_435:
    """Eternus"""

    # Battlecry: Take control of an enemy minion with this minion's Health or
    # less. (Auto — picks a random eligible enemy minion.)
    play = Steal(RANDOM(ENEMY_MINIONS + (CURRENT_HEALTH <= CURRENT_HEALTH(SELF))))


class TIME_890:
    """Medivh the Hallowed"""

    # Fabled. Costs (0) if you control Karazhan. Battlecry: Silence and
    # destroy all other minions.
    cost_mod = Find(IN_PLAY + FRIENDLY + ID("TIME_890t2")) & -100
    play = (Silence(ALL_MINIONS - SELF), Destroy(ALL_MINIONS - SELF))


class TIME_890t:
    """Atiesh the Greatstaff"""

    # Costs (0) if you control Medivh. Double the damage and healing of your
    # spells.
    cost_mod = Find(IN_PLAY + FRIENDLY + ID("TIME_890")) & -100
    update = Refresh(
        CONTROLLER,
        {
            GameTag.HEALING_DOUBLE: 1,
            GameTag.SPELLPOWER_DOUBLE: 1,
        },
    )


class TIME_890t2:
    """Karazhan the Sanctum"""

    # Costs (0) if you're wielding Atiesh. Summon two random 8-Cost minions.
    cost_mod = Find(IN_PLAY + FRIENDLY + ID("TIME_890t")) & -100
    activate = Summon(CONTROLLER, RandomMinion(cost=8)) * 2


##
# Spells


class TIME_432:
    """Intertwined Fate"""

    # Discover a copy of a card from your deck and one from your opponent's.
    play = GenericChoice(
        CONTROLLER, Copy(RANDOM(DeDuplicate(FRIENDLY_DECK)) * 3)
    ).then(GenericChoice(CONTROLLER, Copy(RANDOM(DeDuplicate(ENEMY_DECK)) * 3)))


class _CeaseToExist(TargetedAction):
    """Pick ONE random enemy minion, then Silence AND Destroy that same minion
    (the Silence strips its deathrattle before it is destroyed). Capturing the
    victim once avoids the two-independent-rolls bug where a tuple of
    Silence(RANDOM(...)) / Destroy(RANDOM(...)) hits two different minions."""

    TARGET = ActionArg()

    def do(self, source, target):
        victims = (ENEMY_MINIONS - DEAD).eval(source.game, source)
        if not victims:
            return
        victim = source.game.random.choice(victims)
        source.game.cheat_action(source, [Silence(victim), Destroy(victim)])


class TIME_433:
    """Cease to Exist"""

    # Rewind. Silence and destroy a random enemy minion. (Rewind is
    # engine-handled via GameTag.REWIND — only the base effect lives here.)
    play = _CeaseToExist(CONTROLLER)


class TIME_447:
    """Power Word: Barrier"""

    # Give a character Divine Shield. Give minions in your hand +2 Health.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        GiveDivineShield(TARGET),
        Buff(FRIENDLY_HAND + MINION, "TIME_447e2"),
    )


TIME_447e2 = buff(health=2)


##
# Location — Conflux chain (Past -> Present -> Future)


# Random picker over collectible Dragons that cost (5) or more.
BIG_DRAGON = lambda: RandomDragon(custom_filter=lambda c: (c.cost or 0) >= 5)


class TIME_436:
    """Past Conflux"""

    # Summon a random Dragon that costs (5) or more. Advance to the present!
    activate = Summon(CONTROLLER, BIG_DRAGON()).then(Morph(SELF, "TIME_436t1"))


class TIME_436t1:
    """Present Conflux"""

    # Discover a Dragon that costs (5) or more and summon it. Advance to the
    # future!
    activate = Discover(CONTROLLER, BIG_DRAGON()).then(
        Summon(CONTROLLER, Discover.CARD), Morph(SELF, "TIME_436t2")
    )


class TIME_436t2:
    """Future Conflux"""

    # Discover a Dragon that costs (5) or more and summon it. Also get a copy
    # of it.
    activate = Discover(CONTROLLER, BIG_DRAGON()).then(
        Summon(CONTROLLER, Discover.CARD),
        Give(CONTROLLER, Copy(Discover.CARD)),
    )


##
# Across the Timeways (END_) — End Time mini-set


class END_027:
    """Wings of Eternity"""

    # Discover a Dragon from the past with a Dark Gift.
    # "From the past" is flavour — the data pool is collectible Dragons. The
    # Discovered Dragon receives a random Dark Gift via the shared set-wide
    # `_GiveDarkGift` helper (same modelling as every EDR Dark-Gift card).
    play = Discover(
        CONTROLLER,
        RandomDragon(),
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))
