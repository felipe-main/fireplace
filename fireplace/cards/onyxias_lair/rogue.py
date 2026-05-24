from ..utils import *


##
# Minions


class ONY_030:
    """SI:7 Smuggler"""

    # <b>Battlecry:</b> Summon a random minion with Cost equal to the amount
    # of SI:7 cards you've played this game.
    play = Summon(
        CONTROLLER,
        RandomMinion(cost=Count(CARDS_PLAYED_THIS_GAME + SI_7)),
    )


##
# Spells


class ONY_031:
    """Smokescreen"""

    # Draw 5 cards. Trigger any <b>Deathrattles</b> drawn.
    def play(self):
        controller = self.controller
        drawn = []
        for _ in range(5):
            before = len(controller.hand)
            yield Draw(CONTROLLER)
            # If a card was actually drawn, the last hand entry is it.
            if len(controller.hand) > before:
                drawn.append(controller.hand[-1])
        # Trigger deathrattles on every drawn card that has one.
        for card in drawn:
            if getattr(card, "has_deathrattle", False) and card.data.scripts.deathrattle:
                for dr_action in card.data.scripts.deathrattle:
                    yield dr_action


class ONY_032:
    """Tooth of Nefarian"""

    # Deal $3 damage. <b>Honorable Kill:</b> <b>Discover</b> a spell from
    # another class.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3)

    def honorable_kill(self):
        # Pick a random class that isn't ours, then discover a spell from it.
        import random as _random

        own_class = self.controller.hero.card_class
        other_classes = [
            cc
            for cc in CardClass
            if cc not in (CardClass.INVALID, CardClass.NEUTRAL, own_class)
            and cc.value <= 14  # exclude non-playable enums
        ]
        if not other_classes:
            return
        picked = _random.choice(other_classes)
        yield DISCOVER(RandomSpell(card_class=picked))
