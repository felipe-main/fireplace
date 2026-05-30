from ..utils import *


##
# Custom actions


class _MystifiedTocha(TargetedAction):
    """Mystified To'cha — if the combined Health of both heroes is exactly 42,
    set your hero's Health to 42."""

    TARGET = ActionArg()

    def do(self, source, target):
        heroes = [p.hero for p in source.game.players]
        if sum(h.health for h in heroes) == 42:
            source.controller.hero.set_current_health(42)


class _AnchoriteExtraHealth(TargetedAction):
    """Anchorite — when another minion is Overhealed, give it that much extra
    Health."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if target is None or amount <= 0:
            return
        source.game.cheat_action(
            source, [Buff(target, "GDB_441e", max_health=amount)]
        )


class _ArmAskara(TargetedAction):
    """Askara — the next Draenei you play summons a copy of itself."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game

        def hook(played):
            game.cheat_action(played, [Summon(played.controller, played.id)])

        source.controller.next_draenei_hooks.append(hook)


class _GravityLapse(TargetedAction):
    """Gravity Lapse — set every minion's Attack and Health to the lower of
    the two."""

    TARGET = ActionArg()

    def do(self, source, target):
        for player in source.game.players:
            for m in list(player.field):
                low = min(m.atk, m.max_health)
                m.atk = low
                m.max_health = low
                m.damage = 0


##
# Minions


class GDB_440:
    """Mystified To'cha"""

    # Battlecry: If the combined Health of both heroes is exactly 42, set your
    # hero's Health to 42.
    play = _MystifiedTocha(SELF)


class GDB_441:
    """Anchorite"""

    # Whenever another minion is Overhealed, give it that much extra Health.
    events = Overheal(MINION - SELF).on(
        _AnchoriteExtraHealth(Overheal.TARGET, Overheal.AMOUNT)
    )


class GDB_442:
    """K'ure, the Light Beyond"""

    # Spellburst: Summon a random 3-Cost minion. (Holy spells don't remove this
    # Spellburst — approximated as a one-shot Spellburst; tracked in review.csv.)
    spellburst = Summon(CONTROLLER, RandomMinion(cost=3))


class GDB_454:
    """Overzealous Healer"""

    # Deathrattle: Restore #6 Health to the enemy hero. Spellburst: Silence
    # this minion.
    deathrattle = Heal(ENEMY_HERO, 6)
    spellburst = Silence(SELF)


class GDB_455:
    """Askara"""

    # Battlecry: The next Draenei you play summons a copy of itself.
    play = _ArmAskara(SELF)


##
# Spells


class GDB_439:
    """Orbital Halo"""

    # Give a minion +2/+1 and Divine Shield. Costs (0) if you played an
    # adjacent card this turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    cost_mod = (Attr(SELF, "adjacent_plays_this_turn") >= 1) & -100
    play = Buff(TARGET, "GDB_439e"), SetTags(
        TARGET, {GameTag.DIVINE_SHIELD: True}
    )


class GDB_457:
    """Lightspeed"""

    # Give a minion +1/+2 and Rush. Repeatable this turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(TARGET, "GDB_457e1"),
        SetTags(TARGET, {GameTag.RUSH: True}),
        Give(CONTROLLER, Buff(Copy(SELF), "GIL_000")),
    )


class GDB_460:
    """Divine Star"""

    # Deal $3 damage to a minion. Give a random minion in your hand +3 Health.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Buff(
        RANDOM(FRIENDLY_HAND + MINION), "GDB_460e2"
    )


class GDB_464:
    """Gravity Lapse"""

    # Set EVERY minion's Attack and Health to the lower of the two.
    play = _GravityLapse(SELF)


##
# Enchantments


class GDB_439e:
    # Orbiting Halo — +2/+1.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


class GDB_441e:
    # Devotion — extra Health (amount supplied at runtime).
    tags = {GameTag.HEALTH: 0}


class GDB_457e1:
    # Speed of Light — +1/+2.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class GDB_460e2:
    # Moral Compass — +3 Health.
    tags = {GameTag.HEALTH: 3}
