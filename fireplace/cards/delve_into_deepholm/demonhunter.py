from ..utils import *


##
# Custom actions / helpers


class _ShadestoneTakeWeapon(TargetedAction):
    """Shadestone Skulker — Battlecry. Take the controller's equipped weapon
    (remove it from play, stashing the exact instance so the Deathrattle can
    hand it back) and grant this minion the weapon's stats (+ATK = weapon ATK,
    +Health = weapon durability) via the "Borrowed" enchant (DEEP_012e)."""

    TARGET = ActionArg()

    def do(self, source, target):
        weapon = source.controller.weapon
        if weapon is None:
            return
        # Stash the live weapon instance on the minion so the Deathrattle can
        # re-equip the very same weapon (preserving its buffs / durability).
        atk = weapon.atk
        durability = weapon.durability
        # Remove the weapon from play without destroying it (SETASIDE keeps the
        # entity alive). Weapon._set_zone clears controller.weapon for us.
        weapon.zone = Zone.SETASIDE
        source._borrowed_weapon = weapon
        # Gain its stats. Buff supplies the runtime delta from the weapon.
        source.game.cheat_action(
            source,
            [Buff(source, "DEEP_012e", atk=atk, max_health=durability)],
        )


class _ShadestoneGiveBack(TargetedAction):
    """Shadestone Skulker — Deathrattle. Give the borrowed weapon back by
    re-equipping the stashed instance (re-entering PLAY restores it as the
    controller's weapon)."""

    TARGET = ActionArg()

    def do(self, source, target):
        weapon = getattr(source, "_borrowed_weapon", None)
        if weapon is None:
            return
        source._borrowed_weapon = None
        # Re-equip the same instance. Weapon._set_zone destroys any current
        # weapon and sets controller.weapon = this one.
        weapon.controller = source.controller
        weapon.zone = Zone.PLAY


##
# Minions


class DEEP_012:
    """Shadestone Skulker"""

    # <b>Rush</b>. <b>Battlecry:</b> Take your weapon and gain its stats.
    # <b>Deathrattle:</b> Give it back.
    play = _ShadestoneTakeWeapon(SELF)
    deathrattle = _ShadestoneGiveBack(SELF)


class DEEP_012e:
    '"Borrowed"'

    # Holding {0}.
    # Cosmetic: render the name of the borrowed weapon in the {0} slot.
    def cardtext_entity_0(self):
        weapon = getattr(self.owner, "_borrowed_weapon", None)
        return weapon if weapon is not None else None

    tags = {
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


##
# Spells


class DEEP_013:
    """Fel Fissure"""

    # Deal $2 damage to all minions. At the start of your next turn, deal $2
    # more damage to all minions.
    play = Hit(ALL_MINIONS, 2), Summon(CONTROLLER, "DEEP_013t")


class DEEP_013t:
    """Fel Fissure"""

    # At the start of your next turn, deal $2 more damage to all minions.
    events = OWN_TURN_BEGIN.on(Hit(ALL_MINIONS, 2), Destroy(SELF))
