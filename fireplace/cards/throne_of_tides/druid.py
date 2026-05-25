from ..utils import *


##
# Spells


class TID_001:
    """Moonbeam"""

    # Deal $1 damage to an enemy, twice.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 1) * 2


##
# Minions


class TID_000:
    """Spirit of the Tides"""

    # If you have any unspent Mana at the end of your turn, gain +1/+2.
    events = OWN_TURN_END.on((CURRENT_MANA(CONTROLLER) > 0) & Buff(SELF, "TID_000e"))


class TID_000e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class TID_002:
    """Herald of Nature"""

    # Battlecry: If you've cast a Nature spell while holding this, give your
    # other minions +1/+2.
    def play(self):
        schools = getattr(self, "spell_schools_cast_while_holding", set())
        if int(SpellSchool.NATURE) in schools:
            yield Buff(FRIENDLY_MINIONS - SELF, "TID_002e")


class TID_002e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}
