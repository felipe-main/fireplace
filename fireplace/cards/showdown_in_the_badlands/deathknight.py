"""Showdown in the Badlands — Deathknight cards (WILD_WEST)."""

from ..utils import *


##
# Spells


# Deal $3 damage. Excavate a treasure.
class WW_352:
    """Reap What You Sow"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Hit(TARGET, 3), Excavate(CONTROLLER)


# Deal damage to a minion equal to your Corpses.
class WW_354:
    """Fistful of Corpses"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, Attr(CONTROLLER, "corpses"))


# Summon four 1/1 Undead with Rush that die at the end of turn.
class WW_368:
    """Crop Rotation"""

    play = Summon(CONTROLLER, "WW_368t") * 4


# Gnome on the Range — 1/1 Undead with Rush that dies at the end of turn.
class WW_368t:
    """Gnome on the Range"""

    events = OWN_TURN_END.on(Destroy(SELF))


# Spend up to 8 Corpses to summon a random minion of that Cost.
class _CorpseFarmSummon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spend = min(8, ctrl.corpses)
        if spend <= 0:
            return
        ctrl.corpses -= spend
        ctrl.corpses_spent_this_game += spend
        source.game.cheat_action(
            source, [Summon(ctrl, RandomMinion(cost=spend))]
        )


class WW_374:
    """Corpse Farm"""

    play = _CorpseFarmSummon(CONTROLLER)


##
# Minions


# Battlecry: Excavate a treasure. It costs (0).
class _SkeletonCrewExcavate(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        before = set(id(c) for c in ctrl.hand)
        source.game.cheat_action(source, [Excavate(ctrl)])
        new = [c for c in ctrl.hand if id(c) not in before]
        for card in new:
            source.game.cheat_action(source, [Buff(card, "WW_322e")])


class WW_322:
    """Skeleton Crew"""

    play = _SkeletonCrewExcavate(CONTROLLER)


@custom_card
class WW_322e:
    # "It costs (0)." — clamp the excavated treasure's cost to 0. The engine
    # clamps negative cost to 0, so -100 reliably zeroes any treasure.
    tags = {
        GameTag.CARDNAME: "Skeleton Crew",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -100,
    }


# Deathrattle: The next time you Excavate, resummon this.
class WW_324:
    """Pile of Bones"""

    # Stamp a persistent marker enchant on the hero (the minion itself is
    # dead by the time its deathrattle resolves, so the resummon trigger
    # must live on something that survives). The enchant listens for the
    # next Excavate, resummons a Pile of Bones, then expires.
    deathrattle = Buff(FRIENDLY_HERO, "WW_324e")


class _PileOfBonesResummon(TargetedAction):
    """After the next Excavate: resummon a Pile of Bones and remove the
    pending marker enchant (one-shot)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(source, [Summon(ctrl, "WW_324")])


class WW_324e:
    # In-data marker "Pile of Bones" applied to the hero by the deathrattle.
    events = Excavate(CONTROLLER).after(
        _PileOfBonesResummon(CONTROLLER), Destroy(SELF)
    )


# Taunt. Battlecry: If you've Excavated twice, your next card this turn
# costs (7) less.
class WW_356:
    """Harrowing Ox"""

    play = (Attr(CONTROLLER, "excavates_this_game") >= 2) & Buff(
        CONTROLLER, "WW_356t"
    )


@custom_card
class WW_356t:
    # Carrier enchant on the player: while live, the next card in hand costs
    # (7) less; consumed when the controller plays a card, and expires at
    # end of turn.
    tags = {
        GameTag.CARDNAME: "Harrowing Ox",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.TAG_ONE_TURN_EFFECT: True,
    }
    update = Refresh(FRIENDLY_HAND, {GameTag.COST: -7})
    events = Play(CONTROLLER).on(Destroy(SELF))


# WW_356e "Ox Chill" exists in data (TAG_ONE_TURN_EFFECT) but carries no
# COST tag — declare the COST so the -7 reduction lands if data ever
# references this id directly.
class WW_356e:
    tags = {GameTag.COST: -7}


# At the end of your turn, gain 5 Corpses. At the start of your turn,
# spend 5 Corpses to give your hero +5 Health.
class _MawAndPawGainCorpses(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl.corpses += 5
        ctrl.corpses_gained_this_game += 5


class _MawAndPawSpendCorpses(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.corpses < 5:
            return
        ctrl.corpses -= 5
        ctrl.corpses_spent_this_game += 5
        source.game.cheat_action(source, [Buff(ctrl.hero, "WW_357e")])


@custom_card
class WW_357e:
    tags = {
        GameTag.CARDNAME: "Maw and Paw",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.HEALTH: 5,
    }


class WW_357:
    """Maw and Paw"""

    events = (
        OWN_TURN_END.on(_MawAndPawGainCorpses(SELF)),
        OWN_TURN_BEGIN.on(_MawAndPawSpendCorpses(SELF)),
    )


# Battlecry: Discover an Undead. Quickdraw: It costs (2) less.
class _FarmHandApply(TargetedAction):
    """After the Discover resolves, give the chosen Undead and (if the
    parent was played with Quickdraw) reduce its cost by (2)."""

    PLAYER = ActionArg()
    CARD = ActionArg()

    def __init__(self, target, card, quickdraw):
        super().__init__(target, card)
        self._quickdraw = quickdraw

    def do(self, source, player, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        source.game.cheat_action(source, [Give(player, card)])
        if not self._quickdraw:
            return
        # Locate the just-given copy and shave (2) off its cost.
        for c in reversed(player.hand):
            if c.id == card.id:
                source.game.cheat_action(source, [Buff(c, "WW_358e")])
                break


class _FarmHandDiscover(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        quickdraw = getattr(source, "quickdraw_played", 0) >= 1
        picker = RandomCollectible(race=Race.UNDEAD)
        action = Discover(ctrl, picker).then(
            _FarmHandApply(Discover.TARGET, Discover.CARD, quickdraw)
        )
        source.game.queue_actions(source, [action])


class WW_358:
    """Farm Hand"""

    play = _FarmHandDiscover(SELF)


@custom_card
class WW_358e:
    tags = {
        GameTag.CARDNAME: "Farm Hand",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


# Rush. Costs (1) less for each minion that died this game.
# Deathrattle: Take control of a random enemy minion.
class WW_373:
    """Reska, the Pit Boss"""

    cost_mod = -Count(KILLED + MINION)
    deathrattle = Steal(RANDOM(ENEMY_MINIONS))
