from ..utils import *


##
# Spells


class _ImmolateBurn(TargetedAction):
    """Stamp all cards in the opponent's hand with a 3-turn burn timer.
    Implementation lives in the engine: PlayableCard.burn_turns_left is
    decremented at the owner's begin_turn and Destroy fires when it hits 0.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        for card in list(target.hand):
            card.burn_turns_left = 3


class TID_718:
    """Immolate"""

    # Light every card in the opponent's hand on fire. In 3 turns, any
    # still in hand are destroyed.
    play = _ImmolateBurn(OPPONENT)


##
# Minions


class TID_717:
    """Herald of Shadows"""

    # Battlecry: If you've cast a Shadow spell while holding this, steal 2
    # Health from a minion. (Targeted; the target check is gated by the
    # threshold so we list a soft target requirement.)
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}

    def play(self):
        schools = getattr(self, "spell_schools_cast_while_holding", set())
        if int(SpellSchool.SHADOW) not in schools or self.target is None:
            return
        target = self.target
        # Steal 2 Health: drain 2 from target's max health, give 2 to self.
        if target.type == CardType.MINION:
            yield Buff(target, "TID_717e")
        yield Buff(self, "TID_717e2")


class TID_717e:
    # "Siphoned" — -2 Health on the source.
    tags = {GameTag.HEALTH: -2}


class TID_717e2:
    # "Shadow Siphon" — +2 Health on Herald of Shadows.
    tags = {GameTag.HEALTH: 2}


class TID_719:
    """Commander Ulthok"""

    # Battlecry: Your opponent's cards cost Health instead of Mana next
    # turn. Approximation: their cards become free next turn but playing
    # any costs Health equal to the card's printed cost (Hit on hero).
    def play(self):
        self.controller.opponent.pays_health_for_cards_turns_left = 2
        return
        yield
