from ..utils import *


##
# Shared Excavate treasures (DEEP_999t*)


class DEEP_999t1:
    """Heartblossom"""

    # Give a friendly minion +2/+2. Deal $2 damage to a random enemy minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "DEEP_999t1e"), Hit(RANDOM_ENEMY_MINION, 2)


# +2/+2.
DEEP_999t1e = buff(+2, +2)


class DEEP_999t2:
    """Deepholm Geode"""

    # At the end of your turn, deal 2 damage to all enemies.
    events = OWN_TURN_END.on(Hit(ENEMY_CHARACTERS, 2))


class _WorldPillarFragment(TargetedAction):
    """World Pillar Fragment (DEEP_999t3) Discover callback — summon the
    chosen Elemental, then add the other two offered Elementals to hand.
    """

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards_offered, chosen):
        if isinstance(chosen, list):
            chosen = chosen[0] if chosen else None
        if chosen is None:
            return
        # Summon the chosen Elemental.
        source.game.cheat_action(source, [Summon(player, chosen.id)])
        # Add the OTHER offered Elementals to hand.
        others = [c for c in cards_offered if c is not chosen]
        for c in others:
            source.game.cheat_action(source, [Give(player, c.id)])


class DEEP_999t3:
    """World Pillar Fragment"""

    # Discover an Elemental to summon. Add the others to your hand.
    play = Discover(CONTROLLER, RandomElemental()).then(
        _WorldPillarFragment(Discover.TARGET, Discover.CARDS, Discover.CARD)
    )


class DEEP_999t4:
    """The Azerite Dragon"""

    # Battlecry: Give all other minions in your hand, deck, and battlefield
    # +3/+3.
    play = Buff(
        (FRIENDLY + (IN_DECK | IN_HAND | IN_PLAY) + MINION - DORMANT) - SELF,
        "DEEP_999t4e",
    )


# +3/+3.
DEEP_999t4e = buff(+3, +3)


class _AzeriteMurlocTransform(TargetedAction):
    """The Azerite Murloc (DEEP_999t5) battlecry — transform ALL the
    controller's OTHER minions (hand, deck, and battlefield) into random
    minions costing (original_cost + 3), keeping their original Costs.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Exclude DORMANT minions, mirroring The Azerite Dragon's selector
        # (FRIENDLY + ... + MINION - DORMANT); dormant minions are inert and
        # both Azerite Legendaries leave them alone for consistency.
        targets = [
            c
            for c in (list(ctrl.field) + list(ctrl.hand) + list(ctrl.deck))
            if c is not source
            and c.type == CardType.MINION
            and not getattr(c, "dormant", False)
        ]
        from fireplace import cards as _cards

        # Snapshot every original Cost up-front: morphing earlier targets
        # can perturb the cost read of later in-hand/in-deck targets, so we
        # capture all costs before mutating anything.
        original_costs = {id(m): m.cost for m in targets}
        for m in targets:
            original_cost = original_costs[id(m)]
            target_cost = original_cost + 3
            candidates = _cards.db.filter(
                collectible=True, type=CardType.MINION, cost=target_cost
            )
            if not candidates:
                continue
            chosen_id = source.game.random.choice(candidates)
            source.game.cheat_action(source, [Morph(m, chosen_id)])
            # Keep the original Cost (printed "keeping their original Costs").
            new_card = getattr(m, "morphed", None) or m
            new_card.cost = original_cost
            source.game.cheat_action(source, [Buff(new_card, "DEEP_999t5e")])


class DEEP_999t5:
    """The Azerite Murloc"""

    # Battlecry: Transform ALL your other minions into ones that cost (3)
    # more (keeping their original Costs).
    play = _AzeriteMurlocTransform(CONTROLLER)


# Cost adjusted.
class DEEP_999t5e:
    """Azerite Shimmer"""

    tags = {}
