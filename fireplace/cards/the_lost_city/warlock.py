from ..utils import *


TEMPORARY = AttrValue(enums.TEMPORARY) == 1


class _SpelunkerArm(TargetedAction):
    """Spelunker host installer."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.buff(source.controller.hero, "TLC_450host")


class _RazidirDiscard(TargetedAction):
    """Razidir discard."""

    TARGET = ActionArg()

    def do(self, source, target):
        if kindred_active(source):
            hand = list(source.controller.opponent.hand)
        else:
            hand = [c for c in source.controller.hand if c is not source]
        if not hand:
            return
        source.game.queue_actions(source, [Discard(source.game.random.choice(hand))])


class _UnderfelRiftActivate(TargetedAction):
    """Underfel Rift activation: throw a card in (discard one random card from
    hand) and summon 2 random Fel Beasts. The Rift is a persistent untouchable
    MINION on the board (data: TLC_446t1, HEALTH 1, UNTOUCHABLE, USES_CHARGES);
    it activates once per turn. We model the once-per-turn cadence at the end of
    the controller's turn rather than as a one-shot vanishing spell."""

    TARGET = ActionArg()

    def do(self, source, target):
        # `source` is the Rift minion; throw in a card from its controller's
        # hand, never the Rift itself (it lives in PLAY, not hand).
        hand = list(source.controller.hand)
        actions = []
        if hand:
            actions.append(Discard(source.game.random.choice(hand)))
        actions.append(
            Summon(CONTROLLER, RandomID("TLC_446t2", "TLC_446t3", "TLC_446t4")) * 2
        )
        source.game.queue_actions(source, actions)


class _StoryOfLakkari(TargetedAction):
    """Story of Lakkari host installer."""

    TARGET = ActionArg()

    def do(self, source, target):
        host = source.buff(source.controller.hero, "TLC_466host")
        host._lakkari_turns_left = 3


class _StoryOfLakkariTick(TargetedAction):
    """Story of Lakkari end-of-turn tick."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target.controller
        actions = []
        hand = list(player.hand)
        if hand:
            actions.append(Discard(source.game.random.choice(hand)))
        empty = 7 - len(player.field)
        if empty > 0:
            actions.append(Summon(player, "TLC_466t") * empty)
        if actions:
            source.game.queue_actions(source, actions)
        target._lakkari_turns_left = getattr(target, "_lakkari_turns_left", 1) - 1
        if target._lakkari_turns_left <= 0:
            target.remove()


class TLC_450:
    """Spelunker"""

    # Battlecry: Your next Temporary card costs (2) less.
    play = _SpelunkerArm(SELF)


@custom_card
class TLC_450host:
    tags = {
        GameTag.CARDNAME: "Spelunker",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = Refresh(FRIENDLY_HAND + TEMPORARY, {GameTag.COST: -2})
    events = Play(CONTROLLER, TEMPORARY).after(Destroy(SELF))


class TLC_463:
    """Razidir"""

    # Battlecry: Discard a random card from your hand. Kindred: opponent's instead.
    play = _RazidirDiscard(SELF)


class TLC_467:
    """Whispering Stone"""

    # Taunt. Deathrattle: Get 2 random Fel spells. They cost Health instead of Mana.
    deathrattle = Give(
        CONTROLLER, RandomSpell(spell_school=SpellSchool.FEL)
    ).then(Buff(Give.CARD, "TLC_467e")) * 2


class TLC_467e:
    """The Stone's Whispers"""

    tags = {GameTag.CARD_COSTS_HEALTH: True}


class TLC_469:
    """Tunnel Terror"""

    # Deathrattle: Get two random Temporary 2-Cost minions.
    deathrattle = Give(CONTROLLER, RandomMinion(cost=2)).then(
        GiveTemporary(Give.CARD)
    ) * 2


class TLC_479:
    """Deathrot Maw"""

    # Taunt. Deathrattle: Summon a random Fel Beast.
    deathrattle = Summon(
        CONTROLLER, RandomID("TLC_446t2", "TLC_446t3", "TLC_446t4")
    )


class TLC_446:
    """Escape the Underfel"""

    # Quest: Play 6 Temporary cards. Reward: Underfel Rift.
    quest = Play(CONTROLLER, TEMPORARY).after(AddProgress(SELF, Play.CARD))
    reward = Give(CONTROLLER, "TLC_446t1")


class TLC_446t1:
    """Underfel Rift"""

    # Select the Rift to activate. Throw a card in to summon 2 random Fel
    # Beasts. (Once per turn.)
    #
    # In data this is a persistent untouchable MINION (HEALTH 1) that sits on
    # the board, NOT a one-shot spell. It is activated once per turn; we model
    # that activation at the end of the controller's turn (throw a card in,
    # summon 2 Fel Beasts) while the Rift body stays in play.
    events = OWN_TURN_END.on(_UnderfelRiftActivate(SELF))


class TLC_447:
    """Caustic Fumes"""

    # Destroy an enemy minion. Kindred: Deal 2 damage to all minions.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Destroy(TARGET), Kindred() & Hit(ALL_MINIONS, 2)


class _CursedCatacombsDiscover(TargetedAction):
    """Cursed Catacombs — Discover a minion from your deck. A deck-Discover
    removes ONLY the chosen card from the deck (drawn to hand); the other
    presented cards stay in the deck (a plain GenericChoice would discard them).
    Then make the drawn minion Temporary."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ids = list({c.id for c in ctrl.deck if c.type == CardType.MINION})
        if not ids:
            return
        source.game.cheat_action(
            source,
            [Discover(CONTROLLER, RandomID(*ids)).then(
                _CursedCatacombsDraw(SELF, Discover.CARD)
            )],
        )


class _CursedCatacombsDraw(TargetedAction):
    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        ctrl = source.controller
        real = next((c for c in ctrl.deck if c.id == card.id), None)
        if real is not None:
            source.game.cheat_action(
                source, [ForceDraw(real), SetTag(real, enums.TEMPORARY)]
            )


class TLC_451:
    """Cursed Catacombs"""

    # Discover a minion from your deck. Make it Temporary.
    play = _CursedCatacombsDiscover(CONTROLLER)


class TLC_466:
    """Story of Lakkari"""

    # At the end of your turn, discard a card and fill your board with 3/2 Imps. Lasts 3 turns.
    play = _StoryOfLakkari(SELF)


@custom_card
class TLC_466host:
    tags = {
        GameTag.CARDNAME: "Story of Lakkari",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(_StoryOfLakkariTick(SELF))


@custom_card
class TLC_466t:
    """Imp"""

    tags = {
        GameTag.CARDNAME: "Imp",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.CARDRACE: Race.DEMON,
        GameTag.ATK: 3,
        GameTag.HEALTH: 2,
    }


class TLC_449:
    """Bloodpetal Biome"""

    # Discover a Temporary 1-Cost minion.
    activate = Discover(CONTROLLER, RandomMinion(cost=1)).then(
        Give(CONTROLLER, Discover.CARD).then(GiveTemporary(Give.CARD))
    )


##
# Lost City of Un'Goro mini-set (DINO_) — Warlock


class DINO_131:
    """Possessed Animancer"""

    # Deathrattle: Summon a random Beast from your deck. Give it Lifesteal.
    deathrattle = Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + BEAST + MINION)).then(
        SetTags(Summon.CARD, {GameTag.LIFESTEAL: True})
    )


class DINO_132:
    """Asphyxiodon"""

    # Taunt (data). At the end of your turn, deal 5 damage to a random
    # enemy minion.
    events = OWN_TURN_END.on(Hit(RANDOM_ENEMY_MINION, 5))


class _BatMask(TargetedAction):
    """Bat Mask — set the chosen friendly minion's stats to 1/1, then fill
    the board with 1/1 copies of it."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        controller = source.controller
        # True SET-to-1/1: wipe prior atk/health buffs first, then apply a
        # fresh enchant that locks stats to 1/1.
        target.clear_buffs()
        source.game.cheat_action(source, [Buff(target, "DINO_402e")])
        while len(controller.field) < source.game.MAX_MINIONS_ON_FIELD:
            source.game.cheat_action(source, [Summon(controller, target.id)])
            copy = controller.field[-1]
            copy.atk = 1
            copy.max_health = 1
            copy.damage = 0
        source.game.manager.targeted_action(self, source, target)


class DINO_402:
    """Bat Mask"""

    # Set a friendly minion's stats to 1/1. Fill your board with copies of it.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = _BatMask(TARGET)


class DINO_402e:
    """Bat Mask"""

    # Set-stats enchant (exists in data). atk/max_health lambdas lock the
    # target to 1/1 regardless of its base stats.
    atk = lambda self, i: 1
    max_health = lambda self, i: 1
