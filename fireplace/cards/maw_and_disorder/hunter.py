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


class _NathanosTriggerOnPick(TargetedAction):
    """Choose-callback: receives the Discover-chosen card, triggers
    its deathrattle once on Nathanos's controller's side, and grafts
    the deathrattle onto Nathanos so it fires when he dies."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards, picked):
        # `source` is Nathanos (the Discover's source).  `picked` is
        # the graveyard card the player chose.  ActionArg eval can wrap
        # a single card in a 1-list — unwrap defensively.
        if isinstance(picked, list):
            if not picked:
                return
            picked = picked[0]
        # Resolve via get_actions so a *callable*/generator deathrattle script
        # (Gigafin, Ozumat, ...) is invoked and materialised into a flat
        # action list rather than crashing list() on a bare function.
        deathrattle = list(picked.get_actions("deathrattle") or ())
        if not deathrattle:
            return
        deathrattle = tuple(deathrattle)
        nathanos = source
        source.game.cheat_action(nathanos, deathrattle)
        nathanos.additional_deathrattles.append(deathrattle)
        nathanos.has_deathrattle = True


class _NathanosOpenDiscover(TargetedAction):
    """Open a real Choice (up to 3 picks) over the friendly graveyard's
    Deathrattle minions.  The Discover's callback triggers the chosen
    card's DR and grafts it onto Nathanos."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType
        ctrl = target.controller
        pool = [
            c for c in ctrl.graveyard
            if c.type == CardType.MINION and c.data.scripts.deathrattle
        ]
        if not pool:
            return
        n = min(3, len(pool))
        picks = source.game.random.sample(pool, n)
        offered = [ctrl.card(p.id, source=source) for p in picks]
        choice = Choice(ctrl, offered).then(
            _NathanosTriggerOnPick(Choice.PLAYER, Choice.CARDS, Choice.CARD)
        )
        source.game.queue_actions(source, [choice])


class MAW_011:
    """Defense Attorney Nathanos"""

    # Battlecry: Discover a friendly Deathrattle minion that died this
    # game. Trigger and gain its Deathrattle.  Opens a real 3-card
    # Discover over the friendly graveyard's DR minions; the chosen
    # card's DR fires once and is grafted onto Nathanos.
    play = _NathanosOpenDiscover(SELF)
