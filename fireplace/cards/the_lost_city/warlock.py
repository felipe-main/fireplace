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
    """Underfel Rift activate."""

    TARGET = ActionArg()

    def do(self, source, target):
        hand = [c for c in source.controller.hand if c is not source]
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

    # Throw a card in to summon 2 random Fel Beasts. (Approximation.)
    play = _UnderfelRiftActivate(SELF)


class TLC_447:
    """Caustic Fumes"""

    # Destroy an enemy minion. Kindred: Deal 2 damage to all minions.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Destroy(TARGET), Kindred() & Hit(ALL_MINIONS, 2)


class TLC_451:
    """Cursed Catacombs"""

    # Discover a minion from your deck. Make it Temporary.
    play = GenericChoice(
        CONTROLLER, RANDOM(FRIENDLY_DECK + MINION) * 3
    ).then(GiveTemporary(GenericChoice.CARD))


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
