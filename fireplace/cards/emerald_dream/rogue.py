from ..utils import *

from .neutral import _GiveDarkGift


##
# Custom helpers / actions


class FixedCard(LazyValue):
    """Wrap a concrete entity so Copy() can lazily copy that exact card."""

    def __init__(self, entity):
        self.entity = entity

    def evaluate(self, source):
        return self.entity


class _CopyLowestCostInEnemyHand(TargetedAction):
    """Tricky Satyr — get a copy of the lowest Cost card in the opponent's
    hand. When several cards tie for lowest cost, Hearthstone picks one at
    random, so resolve ties via game.random rather than leftmost."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp_hand = list(ctrl.opponent.hand)
        if not opp_hand:
            return
        lowest = min(c.cost for c in opp_hand)
        tied = [c for c in opp_hand if c.cost == lowest]
        chosen = source.game.random.choice(tied)
        source.game.cheat_action(source, [Give(ctrl, Copy(FixedCard(chosen)))])


class _MimicryDrawCopy(TargetedAction):
    """Mimicry — the opponent draws 2 cards; you get copies of each."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        for _ in range(2):
            before = set(id(c) for c in opp.hand)
            source.game.cheat_action(source, [Draw(opp)])
            drawn = [c for c in opp.hand if id(c) not in before]
            for card in drawn:
                source.game.cheat_action(source, [Give(ctrl, Copy(FixedCard(card)))])


class _ShadowcloakedShuffle(TargetedAction):
    """Shadowcloaked Assailant — if you're holding one of the same cards as
    your opponent, shuffle theirs into their deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        my_ids = {c.id for c in ctrl.hand if c is not source}
        matches = [c for c in opp.hand if c.id in my_ids]
        if not matches:
            return
        source.game.cheat_action(source, [Shuffle(opp, matches)])


class _RenferalTrap(TargetedAction):
    """Renferal, the Malignant — trap N random cards in the opponent's hand
    for a turn, where N = 1 + the number of times you've already played
    Renferal this game. A trapped card can't be played through the
    opponent's next turn (unplayable_next_turn = 2 ticks down at their next
    two begin_turns)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        prior = sum(1 for c in ctrl.cards_played_this_game if c.id == "EDR_526")
        n = 1 + prior
        opp_hand = [c for c in ctrl.opponent.hand]
        if not opp_hand:
            return
        rng = source.game.random
        victims = rng.sample(opp_hand, min(n, len(opp_hand)))
        for card in victims:
            if hasattr(card, "unplayable_next_turn"):
                card.unplayable_next_turn = 2
                source.game.cheat_action(source, [Buff(card, "EDR_526e")])


class _AshamaneFill(TargetedAction):
    """Ashamane — fill your hand with copies of cards from your opponent's
    deck. The copies cost (3) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        deck = [c for c in ctrl.opponent.deck]
        if not deck:
            return
        rng = source.game.random
        # "Fill your hand" — keep adding discounted copies (picked at random
        # from the opponent's deck, with repeats) until the hand is full.
        while len(ctrl.hand) < ctrl.max_hand_size:
            original = rng.choice(deck)
            source.game.cheat_action(
                source,
                [
                    Give(ctrl, Copy(FixedCard(original))).then(
                        Buff(Give.CARD, "EDR_527e")
                    )
                ],
            )


class _WebweaverDraw(TargetedAction):
    """Twisted Webweaver — when you play a minion you've already played this
    game, draw a card. Play broadcasts BEFORE the played card is appended to
    cards_played_this_game, so a prior entry with the same id == a repeat."""

    TARGET = ActionArg()

    def do(self, source, target):
        args = source.event_args or []
        played = args[1] if len(args) > 1 else None
        if played is None:
            return
        ctrl = source.controller
        if any(c.id == played.id for c in ctrl.cards_played_this_game):
            source.game.cheat_action(source, [Draw(ctrl)])


class _HarbingerSummon(TargetedAction):
    """Harbinger of the Blighted — summon two random 2-Cost minions. The
    printed trigger ("whenever this enters your hand from the battlefield")
    needs an engine bounce/zone-change event that does not exist yet; this
    action carries the effect so it can be wired once that hook lands."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(
            source, [Summon(source.controller, RandomMinion(cost=2)) * 2]
        )


##
# Minions


class EDR_521:
    """Tricky Satyr"""

    # Battlecry: Get a copy of the lowest Cost card in your opponent's hand.
    play = _CopyLowestCostInEnemyHand(SELF)


class EDR_524:
    """Shadowcloaked Assailant"""

    # Battlecry: If you're holding one of the same cards as your opponent,
    # shuffle theirs into their deck.
    play = _ShadowcloakedShuffle(SELF)


class EDR_526:
    """Renferal, the Malignant"""

    # Battlecry: Trap @ random card(s) in your opponent's hand for a turn.
    # (Improved for each time you've played this.)
    play = _RenferalTrap(SELF)


class EDR_526e:
    # Webbed! — Can't be played for a turn. (Data enchant; the real lockout is
    # carried by unplayable_next_turn — this is the visual marker on the card.)
    tags = {GameTag.CARDNAME: "Webbed!"}


class EDR_527:
    """Ashamane"""

    # Battlecry: Fill your hand with copies of cards from your opponent's deck.
    # They cost (3) less.
    play = _AshamaneFill(SELF)


@custom_card
class EDR_527e:
    # Ashamane — the copied card costs (3) less.
    tags = {
        GameTag.CARDNAME: "Ashamane",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class EDR_540:
    """Twisted Webweaver"""

    # Whenever you play another minion you've already played, draw a card.
    events = Play(CONTROLLER, MINION - SELF).after(_WebweaverDraw(SELF))


class EDR_781:
    """Harbinger of the Blighted"""

    # Whenever this enters your hand from the battlefield, summon two random
    # 2-Cost minions. (See _HarbingerSummon — trigger awaits an engine
    # bounce/zone-change event; the effect itself is fully implemented.)
    play = None


##
# Spells


class EDR_522:
    """Mimicry"""

    # Your opponent draws 2 cards. You get copies of them.
    play = _MimicryDrawCopy(SELF)


class EDR_528:
    """Nightmare Fuel"""

    # Discover a copy of a minion in your opponent's deck.
    # Combo: With a Dark Gift.
    #
    # The Combo half attaches a Dark Gift through the shared set-wide helper
    # (_GiveDarkGift in neutral.py) so it is consistent with every other EDR
    # Dark-Gift card (Jumpscare, Avant-Gardening, Treacherous Tormentor, ...)
    # instead of a one-off flat +1/+1. The genuine Dark Gift pool is not
    # enumerated in the card data (a single EDR_102t "Dark Gift" spell that
    # "executes nightmare bonus" script-side), so the helper's random-keyword
    # Bonus Effect remains a faithful-shape approximation, not the exact pool.
    play = Choice(CONTROLLER, RANDOM(DeDuplicate(ENEMY_DECK + MINION)) * 3).then(
        Give(CONTROLLER, Copy(Choice.CARD))
    )
    combo = Choice(CONTROLLER, RANDOM(DeDuplicate(ENEMY_DECK + MINION)) * 3).then(
        Give(CONTROLLER, Copy(Choice.CARD)).then(_GiveDarkGift(Give.CARD))
    )


class EDR_523:
    """Web of Deception"""

    # Return a friendly minion to your hand to summon a 4/4 Spider with Stealth.
    requirements = {
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
    }
    play = Bounce(TARGET), Summon(CONTROLLER, "EDR_523t")


class EDR_523t:
    """Skittering Spiderling"""

    # 4/4 with Stealth (Stealth carried by the data tags).


##
# Weapons


class EDR_525:
    """Barbed Thorn"""

    # Choose One - Gain Poisonous this turn; or Gain "Deathrattle: Deal 2
    # damage to all enemies."
    choose = ("EDR_525A", "EDR_525B")
    play = ChooseBoth(CONTROLLER) & (
        Buff(FRIENDLY_WEAPON, "EDR_525e1"),
        Buff(FRIENDLY_WEAPON, "EDR_525e"),
    )


class EDR_525A:
    """Extra Eyes"""

    # Gain Poisonous this turn.
    play = Buff(FRIENDLY_WEAPON, "EDR_525e1")


class EDR_525B:
    """Extra Thorns"""

    # Gain "Deathrattle: Deal 2 damage to all enemies."
    play = Buff(FRIENDLY_WEAPON, "EDR_525e")


class EDR_525e:
    # Barbed Upgrade — grants the host weapon "Deathrattle: Deal 2 damage to
    # all enemies." Data enchant; supply DEATHRATTLE tag + script so the weapon
    # fires it on destruction.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Hit(ENEMY_CHARACTERS, 2)


class EDR_525e1:
    # Corrupted Toxins — Poisonous this turn. Data enchant; supply POISONOUS +
    # the one-turn marker. NOTE: the engine's one-turn sweep (and all event
    # broadcasts) iterate player.entities, which does NOT yield the weapon or
    # its buffs, so this enchant cannot self-expire from a card file. The
    # marker is correct and will clear automatically once the engine includes
    # weapons in that sweep. (Engine-owned gap; see test for details.)
    tags = {GameTag.POISONOUS: True, GameTag.TAG_ONE_TURN_EFFECT: True}
