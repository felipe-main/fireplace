from ..utils import *

from .utils import InfuseCardtextMixin


##
# Spells


class REV_307:
    """Natural Causes"""

    # Deal 2 damage. Summon a 2/2 Treant.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 2), Summon(CONTROLLER, "tt_010a")


class REV_311:
    """Nightshade Bud"""

    # Choose One — Discover a minion from your deck to summon; or a spell
    # to cast.
    choose = ("REV_311t2", "REV_311t")


class REV_311t2:
    """Moonlight Blossom"""

    # Discover a minion from your deck and summon it. Approximation:
    # summon a random minion from your deck (no discover UI).
    play = Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION))


class REV_311t:
    """Sunlight Blossom"""

    # Discover a spell from your deck and cast it. Approximation: cast
    # a random spell from your deck.
    play = CastSpell(RANDOM(FRIENDLY_DECK + SPELL))


class REV_313:
    """Planted Evidence"""

    # Discover a spell. It costs (2) less this turn.
    play = Discover(CONTROLLER, RandomSpell()).then(
        Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "REV_313e"))
    )


class REV_313e:
    tags = {GameTag.COST: -2}
    events = OWN_TURN_END.on(Destroy(SELF))


class REV_336(InfuseCardtextMixin):
    """Plot of Sin"""

    # Summon two 2/2 Treants. (Infused: two 5/5 Ancients instead.)
    play = Summon(CONTROLLER, "tt_010a") * 2


class REV_336t4:
    """Plot of Sin"""

    # Infused — Summon two 5/5 Ancients.
    play = Summon(CONTROLLER, "REV_336t3") * 2


class REV_336t3:
    """Ancient"""


class REV_365:
    """Convoke the Spirits"""

    # Cast 8 random Druid spells (targets chosen randomly).
    play = CastSpell(RandomSpell(card_class=CardClass.DRUID)) * 8


##
# Minions


class REV_310:
    """Death Blossom Whomper"""

    # Battlecry: Draw a Deathrattle minion and gain its Deathrattle.
    # Approximation: just draw a deathrattle minion (no deathrattle copy).
    play = ForceDraw(FRIENDLY_DECK + MINION + DEATHRATTLE)


class REV_314:
    """Topior the Shrubbagazzor"""

    # Battlecry: For the rest of the game, after you cast a Nature spell,
    # summon a 3/3 Whelp with Rush.
    play = Buff(CONTROLLER, "REV_314e")


class REV_314e:
    events = OWN_SPELL_PLAY.after(
        (Find(Play.CARD + NATURE_SPELL)) & Summon(CONTROLLER, "REV_314t")
    )


class REV_314t:
    """Whelpagazzor"""


class REV_318:
    """Widowbloom Seedsman"""

    # Battlecry: Draw a Nature spell. Gain an empty Mana Crystal.
    play = ForceDraw(FRIENDLY_DECK + NATURE_SPELL), GainEmptyMana(CONTROLLER, 1)


class REV_319:
    """Sesselie of the Fae Court"""

    # Deathrattle: Draw a minion. Reduce its Cost by (8).
    deathrattle = ForceDraw(RANDOM(FRIENDLY_DECK + MINION)).then(
        Buff(ForceDraw.TARGET, "REV_319e")
    )


class REV_319e:
    tags = {GameTag.COST: -8}


##
# Locations


class REV_333:
    """Hedge Maze"""

    # Trigger a friendly minion's Deathrattle.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Deathrattle(TARGET)
