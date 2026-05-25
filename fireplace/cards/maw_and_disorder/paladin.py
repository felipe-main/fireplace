from ..utils import *


##
# Spells


class MAW_015:
    """Jury Duty"""

    # Summon two Silver Hand Recruits. Give your Silver Hand Recruits
    # +1/+1.
    play = (
        Summon(CONTROLLER, "CS2_101t") * 2,
        Buff(FRIENDLY_MINIONS + ID("CS2_101t"), "MAW_015e"),
    )


class MAW_015e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class _OrderInTheCourtReorder(TargetedAction):
    """Sort the controller's deck by cost descending (highest on top, so
    that the next draw pulls the highest-cost card). After sorting, draw
    one card."""

    TARGET = ActionArg()

    def do(self, source, target):
        # In our engine, the deck is a list and draws come from the end
        # (target.draw() pops the rightmost). Sort with the highest cost
        # last so the next draw pulls the highest-cost card first.
        target.deck.sort(key=lambda c: (c.cost or 0))


class MAW_016:
    """Order in the Court"""

    # Reorder your deck from highest Cost to lowest Cost. Draw a card.
    play = _OrderInTheCourtReorder(CONTROLLER), Draw(CONTROLLER)


##
# Minions


class _ClassActionSetStats(TargetedAction):
    """If the controller's deck has no Neutral cards, set the chosen
    minion's stats to 1/1."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardClass
        deck = source.controller.starting_deck or source.controller.deck
        if any(getattr(c, "card_class", None) == CardClass.NEUTRAL for c in deck):
            return
        source.game.cheat_action(source, [Buff(target, "MAW_017e")])


class MAW_017:
    """Class Action Lawyer"""

    # Battlecry: If your deck has no Neutral cards, set a minion's
    # stats to 1/1.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _ClassActionSetStats(TARGET)


class MAW_017e:
    # Snapshot the target's current atk/health and stamp -delta so the
    # net atk = max(target.atk + delta, 1) lands at 1.  Bidirectional
    # via apply-time lambdas (Inner-Fire style: read live, snapshot on
    # apply).
    tags = {GameTag.CARDNAME: "Class Action"}
    atk = lambda self, i: 1
    max_health = lambda self, i: 1
