from ..utils import *


##
# Spells


class _FrontLinesSummon(TargetedAction):
    """Summon a minion from each player's deck. Repeat until one side of
    the battlefield is full."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        # `target` is the casting controller.
        loops = 0
        while loops < 14:
            loops += 1
            full1 = len(game.player1.field) >= game.MAX_MINIONS_ON_FIELD
            full2 = len(game.player2.field) >= game.MAX_MINIONS_ON_FIELD
            if full1 or full2:
                break
            for player in (game.player1, game.player2):
                if len(player.field) >= game.MAX_MINIONS_ON_FIELD:
                    continue
                # Pick a random minion from deck.
                candidates = [c for c in player.deck if c.type == CardType.MINION]
                if not candidates:
                    continue
                pick = game.random.choice(candidates)
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
