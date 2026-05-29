"""Showdown in the Badlands — Mage cards (WILD_WEST)."""

from ..utils import *


##
# Spells


class WW_009:
    """Cryopreservation"""

    # <b>Freeze</b> an enemy. <b>Excavate</b> a treasure.
    play = Freeze(TARGET), Excavate(CONTROLLER)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }


class WW_377:
    """Heat Wave"""

    # Deal $2 damage to an enemy minion and its neighbors. Quickdraw: To all
    # enemies instead.
    play = (QUICKDRAW & Hit(ENEMY_CHARACTERS, 2)) | Hit(TARGET | TARGET_ADJACENT, 2)
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }


class _AzeriteVeinTrigger(TargetedAction):
    """Azerite Vein — when the enemy plays a card that entered their hand
    this turn, reveal the Secret and give its owner a 0-cost copy. Custom
    action so the entered-this-turn gate + Reveal + copy all resolve once
    (lambdas in events fire twice)."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        # `card` is the card the opponent just played. The Secret triggers
        # only if that card entered the opponent's hand on this same turn.
        if getattr(card, "_turn_entered_hand", -1) != source.game.turn:
            return []
        if source.zone != Zone.SECRET:
            # Already revealed/consumed this turn.
            return []
        ctrl = source.controller
        source.game.queue_actions(source, [Reveal(source)])
        if len(ctrl.hand) >= ctrl.max_hand_size:
            return []
        copy = ExactCopy(card).copy(source, card)
        copy.controller = ctrl
        source.game.cheat_action(
            source, [Give(ctrl, copy).then(Buff(Give.CARD, "WW_422t_cost0e"))]
        )
        return []


@custom_card
class WW_422t_cost0e:
    # Engine-internal enchant: this copy costs (0).
    tags = {
        GameTag.CARDNAME: "Azerite Copy",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -100,
    }


class WW_422:
    """Azerite Vein"""

    # Secret: When the enemy plays a card on the turn that it entered their
    # hand, get a copy that costs (0).
    secret = Play(OPPONENT).after(_AzeriteVeinTrigger(CONTROLLER, Play.CARD))


class _StargazingDraw(TargetedAction):
    """Stargazing — draw a random Arcane spell from the deck other than
    Stargazing itself, then mark it so it casts twice if played this turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        candidates = [
            c
            for c in ctrl.deck
            if c.type == CardType.SPELL
            and c.spell_school == SpellSchool.ARCANE
            and c.id != source.id
        ]
        if not candidates:
            return []
        pick = source.game.random.choice(candidates)
        source.game.queue_actions(source, [ForceDraw(pick)])
        if pick.zone == Zone.HAND:
            source.game.queue_actions(source, [Buff(pick, "WW_425e")])
        return []


class WW_425:
    """Stargazing"""

    # Draw a different Arcane spell. If you play it this turn, it casts twice.
    play = _StargazingDraw(CONTROLLER)


class WW_425e:
    """Gazing"""

    # Casts twice if played this turn. Re-run the spell's effect on play,
    # then expire (whether played or not, at end of the controller's turn).
    events = [
        Play(CONTROLLER, OWNER).after(Battlecry(Play.CARD, Play.TARGET), Destroy(SELF)),
        OWN_TURN_END.on(Destroy(SELF)),
    ]


class WW_427:
    """Sunset Volley"""

    # Deal $10 damage randomly split among all enemies. Summon a random
    # 10-Cost minion.
    play = (
        Hit(RANDOM_ENEMY_CHARACTER, 1) * SPELL_DAMAGE(10),
        Summon(CONTROLLER, RandomMinion(cost=10)),
    )


##
# Minions


class _ElementalStreakTick(TargetedAction):
    """Maintain the controller's per-game "Elementals played in a row" streak.

    Runs at the end of every turn from whatever zone Overflow Surger occupies
    (deck / hand / play). Idempotent: keyed on the turn number so multiple
    Surger copies (or the deck + hand copy) update the streak exactly once.
    If an Elemental was played this turn the streak grows by one, otherwise it
    resets to zero — exactly the live-card semantics.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        turn = source.game.turn
        if getattr(ctrl, "_elem_streak_turn", None) == turn:
            return []
        ctrl._elem_streak_turn = turn
        if ctrl.elemental_played_this_turn > 0:
            ctrl._elem_streak = getattr(ctrl, "_elem_streak", 0) + 1
        else:
            ctrl._elem_streak = 0
        return []


class _OverflowSurgerStreak(TargetedAction):
    """Overflow Surger — summon a copy of this minion for each turn in a row
    the controller has played an Elemental. Surger is itself the Elemental
    being played on the current turn, so the current turn always contributes
    one; prior consecutive turns are read from the maintained `_elem_streak`.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        prior = getattr(ctrl, "_elem_streak", 0)
        copies = prior + 1
        source.game.queue_actions(source, [Summon(ctrl, Copy(SELF)) * copies])
        return []


class WW_424:
    """Overflow Surger"""

    # Battlecry: Summon a copy of this for each turn in a row you've played an
    # Elemental.
    play = _OverflowSurgerStreak(CONTROLLER)

    events = OWN_TURN_END.on(_ElementalStreakTick(CONTROLLER))

    class Hand:
        events = OWN_TURN_END.on(_ElementalStreakTick(CONTROLLER))

    class Deck:
        events = OWN_TURN_END.on(_ElementalStreakTick(CONTROLLER))


class WW_426:
    """Blastmage Miner"""

    # Battlecry: Excavate a treasure. For each card in your hand, deal 1
    # damage to a random enemy.
    play = (
        Excavate(CONTROLLER),
        Hit(RANDOM_ENEMY_CHARACTER, 1) * Count(FRIENDLY_HAND),
    )


class _MesAduneSplit(TargetedAction):
    """Mes'Adune the Fractured — draw an Elemental, then replace it in hand
    with two copies whose Attack and Health are each broken in half (rounded
    up, per the live card)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        elementals = [
            c
            for c in ctrl.deck
            if c.type == CardType.MINION and Race.ELEMENTAL in c.races
        ]
        if not elementals:
            return []
        drawn = source.game.random.choice(elementals)
        source.game.queue_actions(source, [ForceDraw(drawn)])
        if drawn.zone != Zone.HAND:
            return []
        base_atk = drawn.atk
        base_health = drawn.max_health
        # Half, rounded up (a 3/3 -> two 2/2; a 4/4 -> two 2/2).
        half_atk = (base_atk + 1) // 2
        half_health = (base_health + 1) // 2
        d_atk = half_atk - base_atk
        d_health = half_health - base_health
        # Remove the original drawn elemental; replace with two halves.
        drawn.zone = Zone.SETASIDE
        for _ in range(2):
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            copy = ctrl.card(drawn.id, source=source)
            copy.zone = Zone.HAND
            source.game.queue_actions(
                source, [Buff(copy, "WW_429e", atk=d_atk, max_health=d_health)]
            )
        return []


@custom_card
class WW_429e:
    # Fractured — Attack and Health broken in half. Delta applied dynamically
    # by _MesAduneSplit (atk= / health= kwargs).
    tags = {
        GameTag.CARDNAME: "Fractured",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class WW_429:
    """Mes'Adune the Fractured"""

    # Battlecry: Draw an Elemental. Split it into two halves.
    play = _MesAduneSplit(CONTROLLER)


class WW_430:
    """Tae'thelan Bloodwatcher"""

    # Cards that didn't start in your deck cost (4) less (but not less than 1).
    update = Refresh(FRIENDLY_HAND - STARTING_DECK, buff="WW_430e")


class WW_430e:
    cost = lambda self, i: min(i, max(i - 4, 1))
    events = REMOVED_IN_PLAY


class WW_432:
    """Reliquary Researcher"""

    # Battlecry: If you've Excavated twice, cast two random Mage Secrets.
    play = (Attr(CONTROLLER, "excavates_this_game") >= 2) & (
        CastSpell(RandomSpell(card_class=CardClass.MAGE, secret=True)) * 2
    )
