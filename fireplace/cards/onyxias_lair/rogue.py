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
        # Trigger the proper Deathrattle action on each drawn card so SELF
        # and other lazy refs inside the DR resolve against the drawn card,
        # not the Smokescreen spell.
        for card in drawn:
            if getattr(card, "has_deathrattle", False):
                yield Deathrattle(card)


class ONY_032:
    """Tooth of Nefarian"""

    # Deal $3 damage. <b>Honorable Kill:</b> <b>Discover</b> a spell from
    # another class.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3)

    def honorable_kill(self, victim):
        # Discover a spell from another class — pick from the full pool of
        # off-class spells, not from one randomly-picked class.
        from ..utils import db

        own_class = self.controller.hero.card_class
        candidates = [
            cid
            for cid, card in db.items()
            if card.collectible
            and card.type == CardType.SPELL
            and own_class not in card.classes
            and CardClass.NEUTRAL not in card.classes
            and CardClass.INVALID not in card.classes
        ]
        if len(candidates) < 3:
            return
        import random as _random

        choices = _random.sample(candidates, k=3)
        # GenericChoice already moves the chosen card into the player's
        # hand (and discards the others), so no follow-up Give is needed.
        yield GenericChoice(self.controller, choices)
