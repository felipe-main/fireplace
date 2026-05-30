from ..utils import *

from hearthstone.enums import CardType


##
# Custom actions


class _SetNextCardCostsCorpses(TargetedAction):
    """Exarch Maladaar — the controller's next card this turn pays Corpses."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_card_costs_corpses = 1


class _SummonByAttack(TargetedAction):
    """Soulbound Spire — summon a random minion whose Cost equals the dying
    minion's Attack (capped at 10). On a launched Starship this reads the
    ship's combined Attack."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        cost = min(max(0, source.atk), 10)
        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.MINION
            and (c.cost or 0) == cost
        ]
        if pool:
            source.game.cheat_action(
                source, [Summon(source.controller, source.game.random.choice(pool))]
            )


class _Suffocate(TargetedAction):
    """Suffocate — destroy the target minion; if building a Starship, also
    destroy a random board neighbor of it."""

    TARGET = ActionArg()

    def do(self, source, target):
        board = list(target.controller.field)
        neighbors = []
        if target in board:
            i = board.index(target)
            if i > 0:
                neighbors.append(board[i - 1])
            if i < len(board) - 1:
                neighbors.append(board[i + 1])
        building = source.controller.is_building_starship
        source.game.cheat_action(source, [Destroy(target)])
        if building and neighbors:
            source.game.cheat_action(
                source, [Destroy(source.game.random.choice(neighbors))]
            )


class _DestroyDecksKeepTop8(TargetedAction):
    """The 8 Hands From Beyond — destroy both players' decks except the 8
    highest-Cost cards in each."""

    TARGET = ActionArg()

    def do(self, source, target):
        for player in source.game.players:
            ranked = sorted(player.deck, key=lambda c: (c.cost or 0), reverse=True)
            for card in ranked[8:]:
                card.zone = Zone.GRAVEYARD


##
# Minions


class GDB_106:
    """Guiding Figure"""

    # Spellburst: Trigger a random friendly minion's Deathrattle. Starship
    # Piece (banking handled by the engine).
    spellburst = Deathrattle(RANDOM(FRIENDLY_MINIONS + DEATHRATTLE))


class GDB_112:
    """Soulbound Spire"""

    # Deathrattle: Summon a minion with Cost equal to this minion's Attack
    # (up to 10). Starship Piece.
    deathrattle = _SummonByAttack(SELF)


class GDB_468:
    """Wakener of Souls"""

    # Taunt, Reborn (data). Deathrattle: Resurrect a different friendly
    # Deathrattle minion.
    deathrattle = Summon(
        CONTROLLER, Copy(RANDOM(FRIENDLY + KILLED + MINION + DEATHRATTLE - SELF))
    )


class GDB_469:
    """Auchenai Death-Speaker"""

    # After another friendly minion is Reborn, summon a copy of it.
    events = Reborn(FRIENDLY + MINION).on(Summon(CONTROLLER, Copy(Reborn.TARGET)))


class GDB_470:
    """Exarch Maladaar"""

    # Battlecry: The next card you play this turn costs Corpses instead of Mana.
    play = _SetNextCardCostsCorpses(CONTROLLER)


class GDB_477:
    """The 8 Hands From Beyond"""

    # Battlecry: Destroy both players' decks EXCEPT the 8 highest Cost cards
    # in each.
    play = _DestroyDecksKeepTop8(SELF)


##
# Spells


class GDB_113:
    """Airlock Breach"""

    # Summon a 5/5 Undead with Taunt and give your hero +5 Health. Spend 5
    # Corpses to do it again.
    play = (
        Summon(CONTROLLER, "GDB_113t"),
        Buff(FRIENDLY_HERO, "GDB_113e"),
        (CORPSES >= 5)
        & (
            SpendCorpses(CONTROLLER, 5),
            Summon(CONTROLLER, "GDB_113t"),
            Buff(FRIENDLY_HERO, "GDB_113e"),
        ),
    )


class GDB_475:
    """Orbital Moon"""

    # Give a minion Taunt and Lifesteal. If you played an adjacent card this
    # turn, also give it Reborn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        SetTags(TARGET, {GameTag.TAUNT: True, GameTag.LIFESTEAL: True}),
        (Attr(SELF, "adjacent_plays_this_turn") >= 1)
        & SetTags(TARGET, {GameTag.REBORN: True}),
    )


class GDB_476:
    """Suffocate"""

    # Destroy a minion. If you're building a Starship, also destroy a random
    # neighbor.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _Suffocate(TARGET)


class GDB_478:
    """Assimilating Blight"""

    # Discover a 3-Cost Deathrattle minion. Summon it with Reborn.
    play = Discover(CONTROLLER, RandomMinion(cost=3, deathrattle=True)).then(
        Summon(CONTROLLER, Discover.CARD).then(
            SetTags(Summon.CARD, {GameTag.REBORN: True})
        )
    )


##
# Tokens


class GDB_113t:
    """Unfortunate Soul"""

    # 5/5 Undead/Draenei with Taunt. Stats + Taunt live in data.


##
# Enchantments


class GDB_113e:
    # Breached Air — give your hero +5 Health.
    tags = {GameTag.HEALTH: 5}
