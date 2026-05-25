from ..utils import *


##
# Custom actions used by neutral cards (forward-declared).


class _NeptulonRedirect(TargetedAction):
    """If Neptulon controls any of his Hands, queue an extra attack from
    one Hand against Neptulon's intended target. Approximation of "Hands
    attack instead": we add a single Hand attack rather than cancelling
    Neptulon's own swing. Guards against the target dying mid-resolution.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        controller = target.controller
        hands = [
            m for m in controller.field
            if m.id in ("TID_712t", "TID_712t2") and m is not target
        ]
        if not hands:
            return
        args = source.event_args or []
        attack_target = None
        if len(args) >= 2:
            attack_target = args[1]
        if attack_target is None:
            return
        # Pick the first Hand that can still attack the (still-alive) target.
        for hand in hands:
            if (
                attack_target is not None
                and getattr(attack_target, "zone", None) == Zone.PLAY
                and not getattr(attack_target, "dead", False)
                and hand.can_attack(attack_target)
            ):
                source.game.queue_actions(source, [Attack(hand, attack_target)])
                return


class _BubblerCheck(TargetedAction):
    """Destroy the Bubbler if the most recent damage to it was exactly 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        args = source.event_args or []
        # Damage event args layout: (target, amount, source_of_damage)
        amount = None
        for arg in args:
            if isinstance(arg, int):
                amount = arg
                break
        if amount == 1:
            source.game.queue_actions(source, [Destroy(target)])


class _LookChoice(Choice):
    """Choice that does NOT move cards around — used when the picker is
    selecting from cards already in some zone (eg. opponent's hand)."""

    def choose(self, card):
        # Skip GenericChoice's move-to-HAND-and-discard-rest behavior.
        super().choose(card)


class _CoilfangMark(TargetedAction):
    """Stamp the picked card from the preceding _LookChoice with
    unplayable_next_turn = 2 (decremented at controller's next begin_turn).
    Pulled from source.event_args = [player, cards, chosen]."""

    TARGET = ActionArg()

    def do(self, source, target):
        args = source.event_args or []
        chosen = args[-1] if args else None
        if chosen is None or not hasattr(chosen, "unplayable_next_turn"):
            return
        chosen.unplayable_next_turn = 2


class _CoilfangChoose(TargetedAction):
    """Look at 3 random cards in the opponent's hand, choose one, and mark
    it unplayable until the controller's next turn begins."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp_hand = list(target.opponent.hand)
        if not opp_hand:
            return
        rng = source.game.random
        sample = rng.sample(opp_hand, min(3, len(opp_hand)))
        chain = _LookChoice(target, sample).then(_CoilfangMark(target))
        source.game.queue_actions(source, [chain])


##
# Cards


class TID_710:
    """Snapdragon"""

    # Battlecry: Give all Battlecry minions in your deck +1/+1.
    play = Buff(FRIENDLY_DECK + MINION + BATTLECRY, "TID_710e")


class TID_710e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TID_711:
    """Ozumat"""

    # Colossal +6. Deathrattle: For each of Ozumat's Tentacles, destroy a
    # random enemy minion. Picks distinct targets (no repeats).
    def deathrattle(self):
        tentacle_ids = {
            "TID_711t", "TID_711t2", "TID_711t3",
            "TID_711t4", "TID_711t5", "TID_711t6",
        }
        n = sum(1 for m in self.controller.field if m.id in tentacle_ids)
        enemies = list(self.controller.opponent.field)
        self.controller.game.random.shuffle(enemies)
        for victim in enemies[:n]:
            yield Destroy(victim)


class TID_711t:
    """Ozumat's Tentacle"""


class TID_711t2(TID_711t):
    pass


class TID_711t3(TID_711t):
    pass


class TID_711t4(TID_711t):
    pass


class TID_711t5(TID_711t):
    pass


class TID_711t6(TID_711t):
    pass


class TID_712:
    """Neptulon the Tidehunter"""

    # Colossal +2, Rush, Windfury. Whenever Neptulon attacks, if you
    # control any Hands, they attack instead. Approximation: AFTER
    # Neptulon's swing resolves, queue a follow-up swing from a Hand at
    # the same target. The .after() hook avoids re-entrancy with the outer
    # Attack action's proposed_defender bookkeeping.
    events = Attack(SELF).after(_NeptulonRedirect(SELF))


class TID_712t:
    """Neptulon's Hand"""

    tags = {GameTag.IMMUNE_WHILE_ATTACKING: True}


class TID_712t2(TID_712t):
    pass


class TID_713:
    """Bubbler"""

    # After this minion takes exactly one damage, destroy it. (Pop!)
    events = Damage(SELF).on(_BubblerCheck(SELF))


class TID_744:
    """Coilfang Constrictor"""

    # Battlecry: Look at 3 cards in your opponent's hand and choose one.
    # It can't be played next turn.
    play = _CoilfangChoose(CONTROLLER)
