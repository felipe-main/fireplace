from ..utils import *

from ..castle_nathria.utils import InfuseCardtextMixin


##
# Spells


class _MotionDeniedFireIfThreshold(TargetedAction):
    """Motion Denied secret: only fire (Reveal + Hit hero) if the
    opponent has played >=3 cards this turn. The Secret is set up to
    fire on Play(OPPONENT) after; this gate trims to the threshold."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        # Play.do broadcasts AFTER the played card lands but BEFORE the
        # `cards_played_this_turn` bump, so the counter at this point
        # reads N-1 for the Nth play.  Check >= 2 to fire on the 3rd
        # opponent play this turn.
        opp = source.controller.opponent
        if opp.cards_played_this_turn >= 2:
            source.game.cheat_action(
                source, [Reveal(source), Hit(opp.hero, amount)]
            )


class MAW_010:
    """Motion Denied"""

    # Secret: After your opponent plays three cards in a turn, deal 6
    # damage to the enemy hero.
    secret = Play(OPPONENT).after(_MotionDeniedFireIfThreshold(CONTROLLER, 6))


class MAW_010t:
    """Improved Motion Denied"""

    # Same secret pattern as MAW_010, but deals 9 instead.
    secret = Play(OPPONENT).after(_MotionDeniedFireIfThreshold(CONTROLLER, 9))


##
# Minions


class MAW_009(InfuseCardtextMixin):
    """Shadehound"""

    # Whenever this attacks, give your other Beasts +2/+2.
    # (Infuse (3 Beasts): Gain Rush.)
    events = Attack(SELF).on(Buff(FRIENDLY_MINIONS + BEAST - SELF, "MAW_009e"))


class MAW_009e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class MAW_009t:
    """Shadehound"""

    # Infused — Rush + the attack trigger.
    events = Attack(SELF).on(Buff(FRIENDLY_MINIONS + BEAST - SELF, "MAW_009e"))


class _NathanosTriggerAndGain(TargetedAction):
    """Defense Attorney Nathanos: pick a random friendly Deathrattle
    minion from this game's graveyard, queue its deathrattle to fire,
    and gain a copy of the deathrattle on Nathanos. Approximation of
    the Discover (no live UI).  No-op if the friendly graveyard has no
    Deathrattle minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType
        pool = [
            c for c in target.controller.graveyard
            if c.type == CardType.MINION and c.data.scripts.deathrattle
        ]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        # Trigger the chosen card's deathrattle once on Nathanos's
        # controller's side (cheat_action accepts a list of actions).
        deathrattle = list(pick.data.scripts.deathrattle)
        source.game.cheat_action(target, deathrattle)
        # Gain the deathrattle on Nathanos so it fires when he dies.
        # `additional_deathrattles` expects iterables of actions (the
        # engine iterates twice: outer over deathrattles, inner over
        # actions in each).  Stamp HAS_DEATHRATTLE so the engine
        # consults the list at all (the gate in card.deathrattles).
        target.additional_deathrattles.append(tuple(deathrattle))
        target.has_deathrattle = True


class MAW_011:
    """Defense Attorney Nathanos"""

    # Battlecry: Discover a friendly Deathrattle minion that died this
    # game. Trigger and gain its Deathrattle. Approximated as random.
    play = _NathanosTriggerAndGain(SELF)
