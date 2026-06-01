from ..utils import *

from hearthstone.enums import CardClass, GameTag, Race, Rarity


##
# Custom actions / lazynums


class _OnyxiaCostLevel(LazyNum):
    """Onyxia's Wing / Soldier of Onyxia — the random minion's Cost.

    Printed text: "get a random {0}-Cost minion". {0} starts at 1 and the
    wings upgrade with Herald (once -> 2, twice -> 3). We approximate {0} as
    ``1 + min(heralds_this_game, 2)`` (cap at 3), so the more you've Heralded
    the bigger the minion you fish out.
    """

    def evaluate(self, source) -> int:
        heralds = getattr(source.controller, "heralds_this_game", 0)
        return self.num(1 + min(heralds, 2))


class _GetCostHealthMinion(TargetedAction):
    """Onyxia's Wing / Soldier of Onyxia — "When summoned, get a random
    {0}-Cost minion. It costs Health this turn."

    Gives the controller a random minion whose Cost equals the current
    Onyxia level (see ``_OnyxiaCostLevel``) and stamps it with CATA_155e2
    ("Onyxia's Blood"), the one-turn enchant that makes the card pay Health
    instead of Mana this turn.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        heralds = getattr(ctrl, "heralds_this_game", 0)
        cost = 1 + min(heralds, 2)
        before = len(ctrl.hand)
        source.game.cheat_action(source, [Give(ctrl, RandomMinion(cost=cost))])
        if len(ctrl.hand) > before:
            card = ctrl.hand[-1]
            source.game.cheat_action(source, [Buff(card, "CATA_155e2")])


class _OnyxiaMaxHealth(TargetedAction):
    """Arisen Onyxia — "When your hero would lose Health on your turn, gain
    that much max Health instead."

    Fires off Predamage(FRIENDLY_HERO). On the controller's own turn it buffs
    the hero's max Health by the incoming amount and zeroes the damage so no
    Health is actually lost. On the opponent's turn it does nothing (the hero
    takes the hit normally).
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        ctrl = source.controller
        if ctrl is not source.game.current_player:
            return
        if amount <= 0:
            return
        hero = ctrl.hero
        source.game.cheat_action(
            source, [Buff(hero, "CATA_155e", max_health=amount)]
        )
        source.game.cheat_action(source, [Predamage(hero, 0)])


class _DragonBreathDamage(LazyNum):
    """Dragon Breath (CATA_464t) — deals damage equal to the value stamped on
    the spell when Blackwing Experiment's deathrattle created it."""

    def evaluate(self, source) -> int:
        return self.num(getattr(source, "_breath_damage", 0))


class _BlackwingDeathrattle(TargetedAction):
    """Blackwing Experiment — "Deathrattle: Get a 2-Cost spell that deals this
    minion's Attack damage." Gives CATA_464t (Dragon Breath) and stamps its
    damage with the minion's Attack at the moment it died."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        dmg = source.atk
        before = len(ctrl.hand)
        source.game.cheat_action(source, [Give(ctrl, "CATA_464t")])
        if len(ctrl.hand) > before:
            ctrl.hand[-1]._breath_damage = dmg


class _ChowDownRush(TargetedAction):
    """Chow Down — summon five 5/4 Undead Drakes. If the controller has 8
    Corpses, spend them and give every Drake summoned this way Rush."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        give_rush = ctrl.corpses >= 8
        if give_rush:
            source.game.cheat_action(source, [SpendCorpses(ctrl, 8)])
        for _ in range(5):
            if len(ctrl.field) >= 7:
                break
            source.game.cheat_action(source, [Summon(ctrl, "CATA_465t")])
            drake = ctrl.field[-1] if ctrl.field else None
            if give_rush and drake is not None and drake.id == "CATA_465t":
                source.game.cheat_action(source, [SetTags(drake, {GameTag.RUSH: True})])


class _NefariusCraft(TargetedAction):
    """Victor Nefarius — "Battlecry: Craft a custom Undead Dragon. If you're
    holding a Dragon, reduce the Creation's Cost by (3)."

    The build-a-card UI isn't expressible, so we approximate: give the
    controller Nefarian's Creation (CATA_470t1, a 1/1 Undead Dragon) and, if
    they're holding another Dragon, knock 3 off its Cost.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        holding_dragon = any(
            c is not source and Race.DRAGON in getattr(c, "races", [])
            for c in ctrl.hand
        )
        before = len(ctrl.hand)
        source.game.cheat_action(source, [Give(ctrl, "CATA_470t1")])
        if len(ctrl.hand) > before and holding_dragon:
            source.game.cheat_action(
                source, [Buff(ctrl.hand[-1], "CATA_470e")]
            )


class _ConsumptionHit(TargetedAction):
    """Consumption — deal 3 damage to two random (distinct) enemy minions, then
    draw a card for each that dies."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        enemies = [
            m for m in ctrl.opponent.field if m.zone == Zone.PLAY
        ]
        victims = source.game.random.sample(enemies, min(2, len(enemies)))
        for victim in victims:
            source.game.cheat_action(source, [Hit(victim, 3)])
        # Draw one card per victim that died.
        deaths = sum(1 for v in victims if v.dead or v.zone != Zone.PLAY)
        for _ in range(deaths):
            source.game.cheat_action(source, [Draw(ctrl)])


##
# Minions


class CATA_007:
    """Consumption"""

    # Deal 3 damage to two random enemy minions. Draw a card for each that dies.
    play = _ConsumptionHit(SELF)


class CATA_009:
    """Death's Advance"""

    # Freeze a character. Discover a spell.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Freeze(TARGET), DISCOVER(RandomSpell())


class CATA_155:
    """Arisen Onyxia"""

    # Colossal +2 (engine summons CATA_155t / CATA_155t1 limbs). Each wing's
    # printed "When summoned, get a random {0}-Cost minion that costs Health"
    # effect cannot fire as a self-summon trigger (the engine suppresses a
    # minion observing its own Summon), so we resolve both wings' rewards here
    # on the parent: get two cost-Health minions (one per wing).
    # Also: when your hero would lose Health on your turn, gain that much max
    # Health instead.
    play = _GetCostHealthMinion(SELF) * 2
    events = Predamage(FRIENDLY_HERO).on(_OnyxiaMaxHealth(SELF, Predamage.AMOUNT))


class CATA_155t:
    """Onyxia's Wing"""

    # Colossal limb (engine-summoned). When summoned, get a random {0}-Cost
    # minion that costs Health this turn.
    play = _GetCostHealthMinion(SELF)


class CATA_155t1:
    """Onyxia's Wing"""

    play = _GetCostHealthMinion(SELF)


class CATA_155e:
    """Black Scales"""

    tags = {GameTag.HEALTH: 0}


class CATA_155e2:
    """Onyxia's Blood"""

    # One-turn enchant: the stamped card pays Health instead of Mana this turn.
    tags = {GameTag.CARD_COSTS_HEALTH: True}


class CATA_161:
    """Gruesome Nightmare"""

    # Battlecry: Give a minion in your hand or battlefield Attack equal to this
    # minion's Attack. Engine hand-targeting is unsupported, so we approximate
    # by buffing a random eligible friendly minion (hand or field).
    play = Buff(
        RANDOM((FRIENDLY_HAND + MINION) | (FRIENDLY_MINIONS - SELF)),
        "CATA_161e",
        atk=Attr(SELF, GameTag.ATK),
    )


class CATA_161e:
    """Nightmarish"""

    tags = {GameTag.ATK: 0}


class CATA_464:
    """Blackwing Experiment"""

    # Deathrattle: Get a 2-Cost spell that deals this minion's Attack damage.
    deathrattle = _BlackwingDeathrattle(SELF)


class CATA_464t:
    """Dragon Breath"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, _DragonBreathDamage())


class CATA_465t:
    """Hungry Drake"""

    # Vanilla 5/4 Undead Dragon token.


class CATA_467:
    """Command Claw"""

    # After your hero attacks, give a random friendly minion +2 Attack.
    events = Attack(FRIENDLY_HERO).after(
        Buff(RANDOM(FRIENDLY_MINIONS), "CATA_467e")
    )


class CATA_467e:
    """The Clawww"""

    tags = {GameTag.ATK: 2}


class CATA_469:
    """Chromatic Broodmother"""

    # Rush. Whenever this attacks, refresh Mana Crystals equal to this minion's
    # Attack.
    events = Attack(SELF).on(FillMana(CONTROLLER, Attr(SELF, GameTag.ATK)))


class CATA_470:
    """Victor Nefarius"""

    # Battlecry: Craft a custom Undead Dragon. If holding a Dragon, reduce its
    # Cost by (3).
    play = _NefariusCraft(SELF)


class CATA_470t1:
    """Nefarian's Creation"""

    # Vanilla 1/1 Undead Dragon token (the crafted Creation).


@custom_card
class CATA_470e:
    # Nefarian's Creation cost reduction (holding a Dragon). Not in data;
    # register a name + COST tag.
    tags = {
        GameTag.CARDNAME: "Nefarius' Discount",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class CATA_780:
    """Obsessive Technician"""

    # Lifesteal (data). Battlecry: Herald {0}.
    play = Herald(CONTROLLER)


class CATA_780t:
    """Soldier of Onyxia"""

    # Token minion. When summoned, get a random {0}-Cost minion that costs
    # Health this turn. Summoned by Obsessive Technician flavor; treat its
    # summon effect like the Onyxia wings (play battlecry).
    play = _GetCostHealthMinion(SELF)


##
# Spells


class CATA_156:
    """Experimental Animation"""

    # Herald {0}. Deal 4 damage to all enemy minions.
    play = Herald(CONTROLLER), Hit(ENEMY_MINIONS, 4)


class CATA_465:
    """Chow Down"""

    # Summon five 5/4 Undead Drakes. Spend 8 Corpses to give them Rush.
    play = _ChowDownRush(CONTROLLER)


class CATA_471:
    """Talanji's Last Stand"""

    # Give your minions "Deathrattle: Summon a random 4-Cost minion."
    play = Buff(FRIENDLY_MINIONS, "CATA_471e")


class CATA_471e:
    """Talanji's Last Wish"""

    # Granted deathrattle: Summon a random 4-Cost minion.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=4))
