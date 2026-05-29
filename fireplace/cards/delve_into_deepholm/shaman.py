from ..utils import *


# Needlerock Totem
# At the end of your turn, gain 2 Armor and draw a card.
class DEEP_008:
    """Needlerock Totem"""
    events = OWN_TURN_END.on(GainArmor(FRIENDLY_HERO, 2), Draw(CONTROLLER))


# Digging Straight Down
# Deal $8 damage to a minion. Excavate a treasure.
class DEEP_009:
    """Digging Straight Down"""
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 8), Excavate(CONTROLLER)
