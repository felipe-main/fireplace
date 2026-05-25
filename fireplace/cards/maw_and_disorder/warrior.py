from ..utils import *


##
# Spells


class _OpponentSummonFromHand(TargetedAction):
    """Make the opponent summon a random minion from their hand. The
    minion enters play (battlecry NOT triggered, matching the printed
    text 'summon')."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType
        pool = [c for c in target.hand if c.type == CardType.MINION]
        if not pool:
            return
        if len(target.field) >= 7:
            return
        pick = source.game.random.choice(pool)
        source.game.cheat_action(source, [Summon(target, pick)])


class MAW_027:
    """Call to the Stand"""

    # Your opponent summons a random minion from their hand.
    play = _OpponentSummonFromHand(OPPONENT)


##
# Minions


class MAW_028:
    """Mawsworn Bailiff"""

    # Taunt (in data). Battlecry: If you have 4 or more Armor, gain
    # +4/+4.
    play = (Attr(FRIENDLY_HERO, GameTag.ARMOR) >= 4) & Buff(SELF, "MAW_028e2")


class MAW_028e2:
    tags = {GameTag.ATK: 4, GameTag.HEALTH: 4}


class MAW_029:
    """Weapons Expert"""

    # Battlecry: If you have a weapon equipped, give it +1/+1.
    # Otherwise, draw a weapon.
    play = (
        (Count(FRIENDLY_WEAPON) >= 1) & Buff(FRIENDLY_WEAPON, "MAW_029e2"),
        (Count(FRIENDLY_WEAPON) < 1) & ForceDraw(FRIENDLY_DECK + WEAPON),
    )


class MAW_029e2:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}
