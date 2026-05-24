from ..utils import *


##
# Minions


class ONY_018:
    """Boomkin"""

    # <b>Choose One -</b> Restore 8 Health to your hero; or Deal 4 damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    choose = ("ONY_018t", "ONY_018t2")
    play = ChooseBoth(CONTROLLER) & (
        Heal(FRIENDLY_HERO, 8),
        Hit(TARGET, 4),
    )


class ONY_018t:
    """Eyes of the Moon"""

    play = Heal(FRIENDLY_HERO, 8)


class ONY_018t2:
    """Heart of the Sun"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 4)


class ONY_019:
    """Raid Negotiator"""

    # <b>Battlecry:</b> <b>Discover</b> a <b>Choose One</b> card. It has both
    # effects combined.
    def play(self):
        controller = self.controller
        # Build a candidate pool of collectible Choose One cards from the
        # full DB, filtered to the player's class (and neutral).
        from ..utils import db

        candidates = [
            cid
            for cid, card in db.items()
            if card.collectible
            and getattr(card.scripts, "choose", None)
            and (
                CardClass.NEUTRAL in card.classes
                or controller.hero.card_class in card.classes
            )
        ]
        if not candidates:
            return
        import random as _random

        choices = _random.sample(candidates, k=min(3, len(candidates)))
        yield GenericChoice(controller, choices).then(
            IncreaseAttr(CONTROLLER, "next_choose_one_combined", 1)
        )


class ONY_019e:
    # "Decisive" — marker enchant for the next Choose One being combined.
    # We model the actual combining via the player attribute
    # `next_choose_one_combined`, consumed at play-time of a Choose One card.
    pass


##
# Spells


class ONY_021:
    """Scale of Onyxia"""

    # Fill your board with 2/1 Whelps with <b>Rush</b>.
    def play(self):
        controller = self.controller
        empty_slots = 7 - len(controller.field)
        for _ in range(empty_slots):
            yield Summon(CONTROLLER, "ONY_001t")
