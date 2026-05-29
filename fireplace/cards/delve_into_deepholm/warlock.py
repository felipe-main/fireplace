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


class _Soulfreeze(TargetedAction):
    """Freeze the target minion and its board neighbors, then deal damage to
    the controller's hero equal to the number ACTUALLY Frozen. Immune minions
    cannot be Frozen, so they are neither frozen nor counted (the self-damage
    must equal the number Frozen, not the size of the selection)."""

    TARGET = ActionArg()

    def do(self, source, target):
        field = list(target.controller.field)
        if target not in field:
            return
        idx = field.index(target)
        group = [target]
        if idx > 0:
            group.append(field[idx - 1])
        if idx < len(field) - 1:
            group.append(field[idx + 1])
        frozen = [m for m in group if not getattr(m, "immune", False)]
        for m in frozen:
            source.game.cheat_action(source, [Freeze(m)])
        if frozen:
            source.game.cheat_action(
                source, [Hit(source.controller.hero, len(frozen))]
            )


class DEEP_032:
    """Soulfreeze"""

    # Freeze a minion and its neighbors. Deal damage to your hero equal to
    # the number Frozen.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _Soulfreeze(TARGET)
