"""Showdown in the Badlands — Paladin cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions


class _AuraCountdown(TargetedAction):
    """Generic N-turn aura countdown helper. Call with the enchantment entity
    as TARGET. Decrements `_aura_turns_left` on the enchant and destroys it
    once the counter hits zero. The enchantment must initialise
    `_aura_turns_left` in its apply()."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        left = getattr(enchant, "_aura_turns_left", 0) - 1
        enchant._aura_turns_left = max(0, left)
        if left <= 0:
            enchant.game.cheat_action(enchant, [Destroy(enchant)])


class _BadlandsBandits(TargetedAction):
    """The Badlands Bandits — get all eight 3/2 Bandit tokens. Each one goes
    to hand if there is room, otherwise it is summoned to the battlefield."""

    TARGET = ActionArg()

    BANDITS = ["WW_345t%i" % i for i in range(1, 9)]

    def do(self, source, target):
        for bandit in self.BANDITS:
            if len(target.hand) < target.max_hand_size:
                source.game.cheat_action(source, [Give(target, bandit)])
            else:
                source.game.cheat_action(source, [Summon(target, bandit)])


class _LawfulLongarmBuff(TargetedAction):
    """Lawful Longarm battlecry — gain +1 Attack for each card in your hand
    (counted at resolution; the Longarm itself is already in play)."""

    TARGET = ActionArg()

    def do(self, source, target):
        n = len(source.controller.hand)
        for _ in range(n):
            source.game.cheat_action(source, [Buff(source, "WW_342e")])


##
# Minions


class WW_335:
    """Holy Cowboy"""

    # <b>Battlecry:</b> Your next Holy spell costs (2) less.
    play = Buff(CONTROLLER, "WW_335e")


class WW_335e:
    """Holy Cowboy"""

    # Controller-attached aura: friendly Holy spells in hand cost (2) less.
    # The discount lives until the next Holy spell is played, then the
    # enchant destroys itself ("next Holy spell").
    update = Refresh(FRIENDLY_HAND + HOLY_SPELL, {GameTag.COST: -2})
    events = Play(CONTROLLER, HOLY_SPELL).after(Destroy(SELF))


class WW_337:
    """Spirit of the Badlands"""

    # <b>Battlecry:</b> If your deck has no duplicates, get a permanent Mirage.
    powered_up = -FindDuplicates(FRIENDLY_DECK)
    play = powered_up & Give(CONTROLLER, "WW_337t")


class WW_337t:
    """Mirage"""

    # At the start of your turn, transform into a copy of a minion in your
    # deck. (This stays in your hand.)
    class Hand:
        events = OWN_TURN_BEGIN.on(
            Find(FRIENDLY_DECK + MINION)
            & Morph(SELF, RANDOM(FRIENDLY_DECK + MINION))
        )


class WW_342:
    """Lawful Longarm"""

    # <b>Rush</b>, <b>Lifesteal</b> <b>Battlecry:</b> Gain +1 Attack for each
    # card in your hand.
    play = _LawfulLongarmBuff(SELF)


class WW_342e:
    """Law Abiding"""

    tags = {GameTag.ATK: 1}


class WW_344:
    """Hi Ho Silverwing"""

    # <b>Divine Shield</b> <b>Deathrattle:</b> Draw a Holy spell.
    deathrattle = ForceDraw(RANDOM(FRIENDLY_DECK + SPELL + HOLY_SPELL))


class WW_366:
    """Living Horizon"""

    # <b>Taunt</b>, <b>Divine Shield</b> Costs (1) less for each other card in
    # your hand.
    cost_mod = -Count(FRIENDLY_HAND - SELF)


##
# Spells


class WW_051:
    """Showdown!"""

    # Both players summon three 3/3 Outlaws. Give yours <b>Rush</b>.
    play = (
        Summon(CONTROLLER, ["WW_051t"] * 3).then(GiveRush(Summon.CARD)),
        Summon(OPPONENT, ["WW_051t"] * 3),
    )


class WW_051t:
    """Outlaw"""

    # Vanilla 3/3 token — all data-driven.
    pass


class WW_336:
    """Prismatic Beam"""

    # Deal $3 damage to all enemies. Costs (1) less for each enemy minion.
    play = Hit(ENEMY_CHARACTERS, 3)
    cost_mod = -Count(ENEMY_MINIONS)


class WW_341:
    """Deputization Aura"""

    # Your left-most minion has +3 Attack and <b>Lifesteal</b>. Lasts 3 turns.
    play = Buff(CONTROLLER, "WW_341e")


class WW_341e:
    """My Favorite Deputy"""

    # Controller-attached aura: the controller's left-most minion gains
    # +3 Attack and Lifesteal. Expires after 3 turn-ends.
    update = Refresh(
        LEFTMOST(FRIENDLY_MINIONS),
        {GameTag.ATK: 3, GameTag.LIFESTEAL: 1},
    )
    events = OWN_TURN_END.on(_AuraCountdown(SELF))

    def apply(self, target):
        self._aura_turns_left = 3


class WW_345:
    """The Badlands Bandits"""

    # Get eight 3/2 Bandits with bonus effects. Any that can't fit in your
    # hand are summoned instead.
    play = _BadlandsBandits(CONTROLLER)


class WW_345t1:
    """Crusty"""

    pass


class WW_345t2:
    """Rusty"""

    pass


class WW_345t3:
    """Sandy Red"""

    pass


class WW_345t4:
    """Pearly"""

    pass


class WW_345t5:
    """Surly"""

    pass


class WW_345t6:
    """Dusty"""

    pass


class WW_345t7:
    """Moe"""

    pass


class WW_345t8:
    """Burly"""

    pass


class WW_365:
    """Lay Down the Law"""

    # <b>Tradeable</b> Set a minion's Attack and Health to 1.
    # <b>Quickdraw:</b> Then deal $1 damage to it.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(TARGET, "WW_365e"),
        SetCurrentHealth(TARGET, 1),
        QUICKDRAW & Hit(TARGET, 1),
    )


class WW_365e:
    atk = SET(1)
    max_health = SET(1)
