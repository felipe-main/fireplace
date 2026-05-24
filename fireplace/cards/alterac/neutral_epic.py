from ..utils import *


##
# Minions


class AV_102:
    """Popsicooler"""

    # [x]<b>Deathrattle:</b> <b>Freeze</b> two random enemy minions.
    deathrattle = Freeze(RANDOM(ENEMY_MINIONS) * 2)


class AV_222:
    """Spammy Arcanist"""

    # [x]<b>Battlecry:</b> Deal 1 damage to all other minions. If any die,
    # repeat this. Same pattern as Lord Godfrey (GIL_825).
    def play(self):
        yield Hit(ALL_MINIONS - SELF, 1)
        for _ in range(13):
            if Dead(ALL_MINIONS).check(self):
                yield Deaths()
                yield Hit(ALL_MINIONS - SELF, 1)
            else:
                break


class AV_128:
    """Frozen Mammoth"""

    # This is <b>Frozen</b> until you cast a Fire spell.
    play = Freeze(SELF)
    events = Play(CONTROLLER, SPELL + FIRE_SPELL).on(
        UnsetTag(SELF, GameTag.FROZEN)
    )


class AV_138:
    """Grimtotem Bounty Hunter"""

    # <b>Battlecry:</b> Destroy an enemy <b>Legendary</b> minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_LEGENDARY_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Destroy(TARGET)


class AV_139:
    """Abominable Lieutenant"""

    # At the end of your turn, eat a random enemy minion and gain its stats.
    events = OWN_TURN_END.on(
        Destroy(RANDOM(ENEMY_MINIONS)).then(
            Buff(SELF, "AV_139e")  # approximation: small flat buff
        )
    )


AV_139e = buff(atk=1, health=1)
