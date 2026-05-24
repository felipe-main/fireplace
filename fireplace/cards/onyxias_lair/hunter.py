from ..utils import *


##
# Spells


class ONY_008:
    """Furious Howl"""

    # Draw a card. Repeat until you have at least 3 cards.
    def play(self):
        controller = self.controller
        # The play action runs while the spell card itself has already left
        # hand. We draw until the player has at least 3 cards in hand.
        guard = 30
        while len(controller.hand) < 3 and guard > 0:
            guard -= 1
            yield Draw(CONTROLLER)


class ONY_010:
    """Dragonbane Shot"""

    # Deal $2 damage. <b>Honorable Kill:</b> Add a Dragonbane Shot to your hand.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 2)
    honorable_kill = Give(CONTROLLER, "ONY_010")


##
# Minions


class ONY_009:
    """Pet Collector"""

    # <b>Battlecry:</b> Summon a Beast from your deck that costs (5) or less.
    play = Find(FRIENDLY_DECK + BEAST + (COST <= 5)) & Summon(
        CONTROLLER, RANDOM(FRIENDLY_DECK + BEAST + (COST <= 5))
    )
