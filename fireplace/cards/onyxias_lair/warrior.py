from ..utils import *


##
# Spells


class ONY_023:
    """Hit It Very Hard"""

    # Gain +10 Attack and "Can't attack heroes" this turn.
    play = Buff(FRIENDLY_HERO, "ONY_023e")


class ONY_023e:
    tags = {
        GameTag.ATK: 10,
        GameTag.CANNOT_ATTACK_HEROES: True,
        enums.TEMPORARY: 1,
    }


class ONY_025:
    """Shoulder Check"""

    # <b>Tradeable</b>. Give a minion +2/+1 and <b>Rush</b>.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "ONY_025e"), GiveRush(TARGET)


ONY_025e = buff(atk=2, health=1)


##
# Minions


class ONY_024:
    """Onyxian Drake"""

    # <b>Taunt</b>. <b>Battlecry:</b> Deal damage equal to your Armor to an
    # enemy minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Hit(TARGET, Attr(FRIENDLY_HERO, GameTag.ARMOR))
