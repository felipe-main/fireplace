from ..utils import *


##
# Spells


class _FrontLinesSummon(TargetedAction):
    """Summon a minion from each player's deck — caster first, then the
    opponent — and repeat. Stops as soon as either side of the battlefield
    is full or either deck has no minions left to summon.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        caster = target
        order = (caster, caster.opponent)
        max_field = game.MAX_MINIONS_ON_FIELD
        # Safety bound: at most 7 rounds because either side fills up by then.
        for _ in range(max_field + 1):
            if any(len(p.field) >= max_field for p in order):
                return
            # Each round, both players summon (caster first). If either
            # side can't summon (empty deck of minions), bail — the loop
            # stops repeating because the printed rule requires "a minion
            # from EACH player's deck".
            picks = []
            for player in order:
                candidates = [c for c in player.deck if c.type == CardType.MINION]
                if not candidates:
                    return
                picks.append((player, game.random.choice(candidates)))
            for player, pick in picks:
                if len(player.field) >= max_field:
                    return
                game.queue_actions(source, [Summon(player, pick)])


class TID_949:
    """Front Lines"""

    # Summon a minion from each player's deck. Repeat until either side of
    # the battlefield is full.
    play = _FrontLinesSummon(CONTROLLER)


##
# Minions


class TID_077:
    """Lightray"""

    # Taunt. Costs (1) less for each Paladin card you've played this game.
    tags = {GameTag.TAUNT: True}
    cost_mod = -Count(
        CARDS_PLAYED_THIS_GAME + FuncSelector(
            lambda entities, source: [
                e for e in entities
                if getattr(e, "card_class", CardClass.INVALID) == CardClass.PALADIN
            ]
        )
    )


class TID_098:
    """Myrmidon"""

    # After you cast a spell on this minion, draw a card.
    events = Play(CONTROLLER, SPELL, SELF).after(Draw(CONTROLLER))
