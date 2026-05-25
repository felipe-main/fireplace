from ..utils import *


##
# Spells


class TID_931:
    """Jackpot!"""

    # Add two random spells from other classes that cost (5) or more to
    # your hand.
    play = Give(
        CONTROLLER,
        RandomSpell(card_class=ANOTHER_CLASS, cost=range(5, 100)),
    ) * 2


##
# Minions


class TID_078:
    """Shattershambler"""

    # Battlecry: Your next Deathrattle minion costs (1) less, but
    # immediately dies when played.
    def play(self):
        self.controller.next_deathrattle_discount = 1
        self.controller.next_deathrattle_dies_on_play = 1
        # Yield nothing — engine-side counters do the work.
        return
        yield
