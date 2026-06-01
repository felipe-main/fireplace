from ..utils import *


##
# Custom engine-internal actions for this class' cards


class _NextBeastDiscount(TargetedAction):
    """Cower in Fear refund: arm a one-shot Beast discount on the controller;
    the first Beast played this turn refunds up to 2 mana (clamped to paid)."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount=2):
        target._next_beast_discount = getattr(
            target, "_next_beast_discount", 0
        ) + amount


class _ConsumeNextBeastDiscount(TargetedAction):
    """Refund the armed Beast discount when a Beast is played, then disarm."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        disc = getattr(target, "_next_beast_discount", 0)
        if disc <= 0 or card is None:
            return
        paid = max(0, card.cost)
        refund = min(paid, disc)
        if refund:
            source.game.cheat_action(source, [SpendMana(target, -refund)])
        target._next_beast_discount = 0


class _ClearBeastDiscount(TargetedAction):
    """Disarm the next-Beast discount (end of turn, if unused)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._next_beast_discount = 0


class _NiriDoubleStats(TargetedAction):
    """Niri of the Crater — whenever you play a 1-Cost minion, double its
    stats (current Attack and max Health)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, list):
            target = target[0] if target else None
        if target is None:
            return
        source.game.cheat_action(
            source,
            [Buff(target, "TLC_836e", atk=max(0, target.atk),
                  max_health=max(0, target.max_health))],
        )


class _NiriCastTwice(TargetedAction):
    """Niri of the Crater — whenever you cast a 1-Cost spell, cast it twice.
    Recast the just-cast spell once more, guarded against recursion via the
    player's _recast_depth so the echo does not re-trigger Niri itself."""

    TARGET = ActionArg()
    SPELL = ActionArg()
    SPELL_TARGET = ActionArg()

    def do(self, source, target, spell, spell_target):
        if isinstance(spell, list):
            spell = spell[0] if spell else None
        if isinstance(spell_target, list):
            spell_target = spell_target[0] if spell_target else None
        if spell is None:
            return
        if target._recast_depth > 0:
            return
        target._recast_depth += 1
        try:
            source.game.cheat_action(source, [CastSpell(spell.id, spell_target)])
        finally:
            target._recast_depth -= 1


class _OddMapDiscover(TargetedAction):
    """Odd Map — Discover an odd-Attack Beast. If you play it this turn, also
    pick one of the other two options. Discover among odd-Attack Beasts, give
    the chosen card stamped with the two runners-up, and arm a one-shot player
    enchant (TLC_824e) that, when that exact card is played this turn,
    Discovers one of the two remembered options."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomBeast(custom_filter=_odd_attack)).then(
                    _OddMapRememberRunnersUp(SELF, Discover.CARDS, Discover.CARD)
                )
            ],
        )


class _OddMapRememberRunnersUp(TargetedAction):
    """After Odd Map's first Discover, give the chosen card and stamp the two
    unchosen options on it. Arm the player-level second-pick watcher."""

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, cards, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        ctrl = source.controller
        runners = [c.id for c in cards if c is not card] if cards else []
        given = ctrl.card(card.id)
        given._odd_map_runners_up = runners
        ctrl.give(given)
        source.game.cheat_action(source, [Buff(ctrl, "TLC_824e")])


class _OddMapSecondPick(TargetedAction):
    """When an Odd-Map-chosen Beast is played this turn, Discover one of the
    two remembered runner-up options."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        runners = getattr(card, "_odd_map_runners_up", None)
        if not runners:
            return
        card._odd_map_runners_up = None
        ctrl = source.controller
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomID(*runners)).then(
                    Give(ctrl, Discover.CARD)
                )
            ],
        )


class _ShokkBattlecry(TargetedAction):
    """Shokk, Jungle Tyrant — Get a random 8, 6, and 4-Attack Beast. Set their
    Costs to (2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for attack in (8, 6, 4):
            picker = RandomBeast(custom_filter=lambda c, a=attack: (c.atk or 0) == a)
            before = set(ctrl.hand)
            source.game.cheat_action(source, [Give(ctrl, picker)])
            for c in ctrl.hand:
                if c not in before:
                    # "Set their Costs to (2)" — a set-cost enchant rather than
                    # assigning .cost, which a dynamic cost_mod would override.
                    source.game.cheat_action(source, [Buff(c, "TLC_830te")])


@custom_card
class TLC_830te:
    # Shokk, Jungle Tyrant — set the Beast's Cost to (2).
    tags = {
        GameTag.CARDNAME: "Jungle Tyrant",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    cost = lambda self, i: 2


def _odd_attack(card):
    return (card.atk or 0) % 2 == 1


##
# Minions


class TLC_366:
    """Pterrorwing Ravager"""

    # Rush
    # Kindred: Costs (2) less.
    cost_mod = -KindredCost(2)


class TLC_822:
    """Dinositter"""

    # At the end of your turn, reduce the Cost of a random Beast in your hand
    # by (1).
    events = OWN_TURN_END.on(
        Buff(RANDOM(FRIENDLY_HAND + BEAST), "TLC_822e")
    )


@custom_card
class TLC_822e:
    tags = {
        GameTag.CARDNAME: "Dinositter",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class TLC_825:
    """Ravasaur Matriarch"""

    # Kindred: Deal damage to an enemy minion equal to this minion's Attack.
    play = Kindred() & Hit(RANDOM_ENEMY_MINION, ATK(SELF))


class TLC_827:
    """Grazing Stegodon"""

    # At the end of your turn, gain +1 Attack (even while in hand or deck).
    events = OWN_TURN_END.on(Buff(SELF, "TLC_827e"))

    class Hand:
        events = OWN_TURN_END.on(Buff(SELF, "TLC_827e"))

    class Deck:
        events = OWN_TURN_END.on(Buff(SELF, "TLC_827e"))


@custom_card
class TLC_827e:
    tags = {
        GameTag.CARDNAME: "Grazing Stegodon",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
    }


class TLC_836:
    """Niri of the Crater"""

    # Whenever you play a 1-Cost minion, double its stats.
    # Whenever you cast a 1-Cost spell, cast it twice.
    events = (
        Play(CONTROLLER, MINION + (COST == 1)).after(
            _NiriDoubleStats(Play.CARD)
        ),
        Play(CONTROLLER, SPELL + (COST == 1)).after(
            _NiriCastTwice(CONTROLLER, Play.CARD, Play.TARGET)
        ),
    )


@custom_card
class TLC_836e:
    tags = {
        GameTag.CARDNAME: "Endemic Fauna",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


# Story of Carnassa token reuses the original Un'Goro Carnassa's Brood
# (1-Cost 3/2 Beast, "Battlecry: Draw a card"); UNG_920t2 already ships that
# script, so we just shuffle its id (no new class needed here).


##
# Spells


class TLC_823:
    """Cower in Fear"""

    # Deal $3 damage to a minion. The next Beast you play this turn costs (2)
    # less.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Hit(TARGET, 3),
        _NextBeastDiscount(CONTROLLER, 2),
        Buff(CONTROLLER, "TLC_823e"),
    )


@custom_card
class TLC_823e:
    # Controller-attached marker that refunds the armed Beast discount when a
    # Beast is played this turn, then removes itself (one-shot; expires at end
    # of turn). Lives on the controller so it survives Cower leaving the hand.
    tags = {
        GameTag.CARDNAME: "Cower in Fear",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = (
        Play(OWNER, BEAST).after(
            _ConsumeNextBeastDiscount(OWNER, Play.CARD), Destroy(SELF)
        ),
        OWN_TURN_END.on(_ClearBeastDiscount(OWNER), Destroy(SELF)),
    )


class TLC_824:
    """Odd Map"""

    # Discover an odd-Attack Beast. If you play it this turn, also pick one of
    # the others.
    play = _OddMapDiscover(CONTROLLER)


class TLC_824e:
    """Odd Map Player Enchant"""

    # If you play the Discovered card this turn, also choose one of the other
    # two options. (Enchant exists in data.) Watches friendly minion plays and
    # fires the second pick for the stamped card; self-removes at end of turn.
    events = (
        Play(OWNER, MINION).after(_OddMapSecondPick(OWNER, Play.CARD)),
        OWN_TURN_END.on(Destroy(SELF)),
    )


class TLC_826:
    """Story of Carnassa"""

    # Shuffle ten 1-Cost 3/2 Raptors into your deck with "Battlecry: Draw a
    # card."
    play = Shuffle(CONTROLLER, "UNG_920t2") * 10


class TLC_828:
    """Supreme Dinomancy"""

    # Give +2/+2 to all Beasts in your hand, deck, and battlefield.
    play = (
        Buff(FRIENDLY_HAND + BEAST, "TLC_828e"),
        Buff(FRIENDLY_DECK + BEAST, "TLC_828e"),
        Buff(FRIENDLY_MINIONS + BEAST, "TLC_828e"),
    )


class TLC_828e:
    """Supremely Dinomanced"""

    # +2/+2. (Enchant exists in data.)
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TLC_830(QuestRewardProtect):
    """The Food Chain"""

    # Quest: Play a 1, 3, 5, and 7-Attack Beast.
    # Reward: Shokk.
    progress_total = 4
    quest = Play(CONTROLLER, BEAST + MINION).after(AddProgress(SELF, Play.CARD))
    reward = Give(CONTROLLER, "TLC_830t")

    def clear_progress(self):
        self._food_chain = set()

    def progress(self):
        return len(getattr(self, "_food_chain", set()))

    def add_progress(self, card):
        seen = getattr(self, "_food_chain", None)
        if seen is None:
            seen = self._food_chain = set()
        atk = card.atk or 0
        if atk in (1, 3, 5, 7):
            seen.add(atk)


class TLC_830t:
    """Shokk, Jungle Tyrant"""

    # Rush
    # Battlecry: Get a random 8, 6, and 4-Attack Beast. Set their Costs to (2).
    play = _ShokkBattlecry(CONTROLLER)


##
# The Lost City of Un'Goro mini-set (DINO_)


class DINO_403:
    """Devilsaur Mask"""

    # Set a minion's stats to 8/8. Give it Charge.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "DINO_403e")


class DINO_403e:
    # Devilsaur Mask — 8/8 and Charge. (Enchant exists in data; supply the
    # set-stats lambdas + Charge tag.) atk/max_health ignore the base value and
    # clamp the minion to a fixed 8/8 body.
    atk = lambda self, i: 8
    max_health = lambda self, i: 8
    tags = {GameTag.CHARGE: True}


class DINO_422:
    """Ankylodon"""

    # Taunt. Deathrattle: Summon two random 3-Cost Beasts. They attack random
    # enemies.
    deathrattle = (
        Summon(CONTROLLER, RandomBeast(cost=3)).then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
        )
        * 2
    )


class DINO_434:
    """Raptor-Nest Nurse"""

    # Battlecry: Get a random 1-Cost minion.
    # Deathrattle: Get a random 1-Cost spell.
    play = Give(CONTROLLER, RandomMinion(cost=1))
    deathrattle = Give(CONTROLLER, RandomSpell(cost=1))
