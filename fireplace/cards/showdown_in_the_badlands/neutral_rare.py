"""Showdown in the Badlands — Neutral Rare cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions


class _OgreGangCancelAttack(TargetedAction):
    """Cancel SELF's currently-proposed attack by nullifying the defender.

    The Attack action's resolution treats a None ``proposed_defender`` as an
    interrupted attack (it bails before any Hit is queued), so SELF never
    swings. The +3-Attack hero buff is applied separately by the play/event.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        if game.proposed_defender is not None:
            game.proposed_defender.defending = False
        game.proposed_defender = None


# Rush. Battlecry: Excavate a treasure.
class WW_002:
    """Burrow Buster"""

    play = Excavate(CONTROLLER)


# Your Excavate, Quickdraw, Tradeable, and Legendary cards cost (1) less.
def _bounty_board_match(entities, source):
    """Excavate / Quickdraw / Tradeable / Legendary cards.

    The Excavate, Quickdraw and Tradeable keywords live on the printed card
    data (``card.data.tags``) and are not copied onto the live entity tag
    map, so we read them from the data definition directly. Legendary is a
    rarity, read off the live entity.
    """
    out = []
    for e in entities:
        data_tags = getattr(getattr(e, "data", None), "tags", {})
        if (
            data_tags.get(GameTag.EXCAVATE)
            or data_tags.get(GameTag.QUICKDRAW)
            or data_tags.get(GameTag.TRADEABLE)
            or getattr(e, "rarity", Rarity.INVALID) == Rarity.LEGENDARY
        ):
            out.append(e)
    return out


class WW_003:
    """Bounty Board"""

    update = Refresh(
        FRIENDLY_HAND + FuncSelector(_bounty_board_match),
        {GameTag.COST: -1},
    )


# Deathrattle: Shuffle 2 Tradeable Snake Oils into your opponent's deck.
class WW_332:
    """Snake Oil Seller"""

    deathrattle = Shuffle(OPPONENT, "WW_331t") * 2


# Taunt. Battlecry and Quickdraw: Summon a copy of this.
class WW_360:
    """Azerite Chain Gang"""

    play = (
        Summon(CONTROLLER, Copy(SELF)),
        QUICKDRAW & Summon(CONTROLLER, Copy(SELF)),
    )


# Rush. 50% chance to give your hero +3 Attack this turn instead of attacking.
class WW_419:
    """Ogre-Gang Rider"""

    events = Attack(SELF).on(
        COINFLIP
        & (_OgreGangCancelAttack(SELF), Buff(FRIENDLY_HERO, "WW_419e"))
    )


WW_419e = buff(atk=3)
