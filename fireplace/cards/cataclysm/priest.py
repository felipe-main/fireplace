from ..utils import *

from hearthstone.enums import CardType


##
# Custom actions


class _CaliaResurrect(TargetedAction):
    """Calia Menethil — Battlecry: Resurrect your highest-Cost minion that died
    this game. Scans the controller's graveyard for the minion with the greatest
    base Cost (ties -> most recently dead) and summons a fresh copy by id."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        best = None
        best_cost = -1
        for card in ctrl.graveyard:
            if card.type != CardType.MINION:
                continue
            cost = card.data.cost or 0
            if cost >= best_cost:
                best_cost = cost
                best = card
        if best is not None and len(ctrl.field) < 7:
            source.game.cheat_action(source, [Summon(ctrl, best.id)])


##
# Minions


class CATA_002:
    """Calia Menethil"""

    # Battlecry: Resurrect your highest-Cost minion that died this game.
    play = _CaliaResurrect(SELF)


class CATA_216:
    """Cleansing Cleric"""

    # Battlecry: Your healing effects restore 2 more Health this game.
    # ENGINE LIMITATION: there is no additive "+N healing this game" slot
    # property — only HEALING_DOUBLE (a doubler). We approximate the +2 by
    # doubling all of the controller's healing for the rest of the game via
    # CATA_216e (HEALING_DOUBLE). Close for the common 1-3 heal range; over-
    # estimates large heals. Noted as an approximation.
    play = Buff(CONTROLLER, "CATA_216e")


class CATA_216e:
    # Free From Corruption — exists in data; refresh HEALING_DOUBLE onto the
    # controller so its heals are amplified (additive +2 is not expressible).
    # healing_double is a slot_property, so it must be granted via an aura
    # (update=Refresh) rather than static tags on a player buff.
    update = Refresh(
        CONTROLLER,
        {
            GameTag.HEALING_DOUBLE: 1,
        },
    )


class _BlackBloodAttack(TargetedAction):
    """The Black Blood — after you restore Health to a character, the SELF
    minion (the listener host) attacks a random enemy minion. Skipped if the
    host is no longer in play or cannot attack."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None or target.zone != Zone.PLAY:
            return
        if target.exhausted or not target.can_attack():
            return
        enemies = [m for m in target.controller.opponent.field if m.zone == Zone.PLAY]
        if not enemies:
            return
        import random

        victim = random.choice(enemies)
        source.game.queue_actions(source, [Attack(target, victim)])


class CATA_300:
    """The Black Blood"""

    # Colossal +3. After you restore Health to a character, attack a random
    # enemy minion. (Limbs CATA_300t1/t2/t3 are engine-summoned.)
    # The body swings on every friendly heal.
    events = Heal(source=FRIENDLY).on(_BlackBloodAttack(SELF))


class _BlackBloodBodyHeal(TargetedAction):
    """Black Blood's Body — at end of turn restore 3 Health to a random
    damaged friendly character. TARGET is the limb (its controller is used)."""

    TARGET = ActionArg()

    def do(self, source, target):
        import random

        ctrl = target.controller
        victims = [
            c
            for c in ctrl.characters
            if c.zone == Zone.PLAY and c.damage > 0
        ]
        if not victims:
            return
        victim = random.choice(victims)
        source.game.queue_actions(source, [Heal(victim, 3)])


class _BlackBloodLimb:
    # Black Blood's Body (limb): at end of your turn, restore 3 Health to a
    # random damaged friendly character. (The "attack on heal" text belongs to
    # the parent CATA_300, not the limbs.)
    events = OWN_TURN_END.on(_BlackBloodBodyHeal(SELF))


class CATA_300t1(_BlackBloodLimb):
    """Black Blood's Body"""


class CATA_300t2(_BlackBloodLimb):
    """Black Blood's Body"""


class CATA_300t3(_BlackBloodLimb):
    """Black Blood's Body"""


class CATA_304:
    """Injured Attendant"""

    # Lifesteal Battlecry: Deal 4 damage to this minion.
    play = Hit(SELF, 4)


class _IncensedMatriarch(TargetedAction):
    """Incensed Matriarch — at end of turn, if at full Health, gain +3
    Health (CATA_305e). TARGET is the minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target.zone == Zone.PLAY and target.damage == 0:
            source.game.queue_actions(source, [Buff(target, "CATA_305e")])


class CATA_305:
    """Incensed Matriarch"""

    # At the end of your turn, if this is at full Health, gain +3 Health.
    events = OWN_TURN_END.on(_IncensedMatriarch(SELF))


CATA_305e = buff(health=3)


class _AlexstraszaReprisal(TargetedAction):
    """Alexstrasza, Guardian of Life — when the controller's hero reaches full
    Health, deal 15 damage to the opponent's hero. TARGET is the enchantment;
    its controller's hero is checked."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = target.controller
        hero = ctrl.hero
        if hero and hero.damage == 0:
            source.game.queue_actions(source, [Hit(ctrl.opponent.hero, 15)])


class CATA_307:
    """Alexstrasza, Guardian of Life"""

    # Battlecry: Set your remaining Health to 15. When you reach full Health,
    # deal 15 damage to your opponent.
    play = (
        SetCurrentHealth(FRIENDLY_HERO, 15),
        Buff(FRIENDLY_HERO, "CATA_307e"),
    )


class CATA_307e:
    # Cleansed of Corruption — when the controller's hero is healed and is now
    # at full Health, blast the opponent for 15.
    events = Heal(FRIENDLY_HERO).on(_AlexstraszaReprisal(SELF))


##
# Spells


class CATA_302:
    """Mend"""

    # Restore a minion to full Health. Draw a card.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = FullHeal(TARGET), Draw(CONTROLLER)


class CATA_303:
    """Purifying Breath"""

    # Deal 5 damage to a minion. If it dies, restore 5 Health to the enemy
    # hero.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 5).then(Dead(TARGET) & Heal(ENEMY_HERO, 5))


class CATA_306:
    """Schism"""

    # Shatter. Give a friendly minion +2/+3 and Elusive. Summon a copy of it.
    # The parent never resolves: the engine splits a SHATTER card into its
    # two "Shattered" half-cards when it is drawn. Schism uniquely names its
    # halves CATA_306t1 / CATA_306t2 (every other SHATTER card uses <id>t /
    # <id>t2); the splitter probes all three suffixes so both halves are given.
    pass


CATA_306e = buff(atk=2, health=3)


class _SchismElusive(TargetedAction):
    """Apply Elusive (untargetable by spells / hero powers) to the target,
    since CATA_306e only carries the +2/+3 stats."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.queue_actions(
            source,
            [
                SetTags(
                    target,
                    (
                        GameTag.CANT_BE_TARGETED_BY_ABILITIES,
                        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS,
                    ),
                )
            ],
        )


class CATA_306t1:
    """Schism"""

    # Shattered: Give a friendly minion +2/+3 and Elusive.
    requirements = {
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Buff(TARGET, "CATA_306e"), _SchismElusive(TARGET)


class CATA_306t2:
    """Schism"""

    # Shattered: Summon a copy of a friendly minion.
    requirements = {
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Summon(CONTROLLER, ExactCopy(TARGET))


class CATA_308:
    """Medivh's Triumph"""

    # Deal 4 damage to all minions. Costs (1) if you control a Legendary card.
    # Base cost 5 -> "Costs (1)" is a flat -4 reduction.
    cost_mod = Find(IN_PLAY + FRIENDLY + LEGENDARY) & -4
    play = Hit(ALL_MINIONS, 4)


##
# Locations


class CATA_301:
    """Ruby Sanctum"""

    # Your next Healing effect this turn deals damage instead.
    # APPROXIMATION: the engine's healing-as-damage is a turn-long slot
    # property (EMBRACE_THE_SHADOW), not a single-use trigger, so EVERY heal
    # this turn is converted (not just the next one). CATA_301e carries
    # TAG_ONE_TURN_EFFECT so it auto-expires at the controller's turn end.
    activate = Buff(CONTROLLER, "CATA_301e")


class CATA_301e:
    # Lifebind — convert this turn's healing into damage. Data carries only
    # TAG_ONE_TURN_EFFECT (auto-expires at the controller's turn end). The
    # healing_as_damage flag is a slot_property, so grant EMBRACE_THE_SHADOW
    # via an aura (update=Refresh) rather than a static tag on a player buff.
    tags = {
        GameTag.TAG_ONE_TURN_EFFECT: True,
    }
    update = Refresh(
        CONTROLLER,
        {
            GameTag.EMBRACE_THE_SHADOW: True,
        },
    )
