"""Delve into Deepholm — Warlock cards (WILD_WEST / DEEP_)."""

from ..utils import *


# ---------------------------------------------------------------------------
# Support
# ---------------------------------------------------------------------------


class _ChaosCreationDestroyBottom(TargetedAction):
    """Destroy the bottom 6 cards of the target player's deck.

    ``deck[0]`` is the bottom of the deck, so the bottom 6 cards are
    ``deck[:6]``.  Each card is sent to the graveyard (destroyed).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        for card in list(target.deck[:6]):
            card.zone = Zone.GRAVEYARD
        return []


##
# Minions


class DEEP_030:
    """Elementium Geode"""

    # Battlecry and Deathrattle: Draw a card. Deal 2 damage to your hero.
    play = Draw(CONTROLLER), Hit(FRIENDLY_HERO, 2)
    deathrattle = Draw(CONTROLLER), Hit(FRIENDLY_HERO, 2)


##
# Spells


class DEEP_031:
    """Chaos Creation"""

    # Deal $6 damage. Summon a random 6-Cost minion. Destroy the bottom 6
    # cards of your deck.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Hit(TARGET, 6),
        Summon(CONTROLLER, RandomMinion(cost=6)),
        _ChaosCreationDestroyBottom(CONTROLLER),
    )


class DEEP_032:
    """Soulfreeze"""

    # Freeze a minion and its neighbors. Deal damage to your hero equal to
    # the number Frozen.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Freeze(TARGET | TARGET_ADJACENT),
        Hit(FRIENDLY_HERO, Count(TARGET | TARGET_ADJACENT)),
    )
