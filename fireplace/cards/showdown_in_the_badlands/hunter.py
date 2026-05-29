"""Showdown in the Badlands — Hunter cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions / helpers


class _TheldurinAttackAll(TargetedAction):
    """Theldurin the Lost — this minion attacks each enemy character
    (every enemy minion in board order, then the enemy hero). We iterate
    manually because Attack(SELF, ENEMY_CHARACTERS) only resolves the
    first target. Mid-cascade deaths are handled by the standard pipeline
    (the field is re-read each iteration)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        victims = list(ctrl.opponent.field) + [ctrl.opponent.hero]
        for v in victims:
            if source.dead or source.zone != Zone.PLAY:
                break
            if v.zone != Zone.PLAY:
                continue
            source.game.cheat_action(source, [Attack(source, v)])


##
# Spells


class WW_806:
    """Sneaky Snakes"""

    # Summon two 1/1 Snakes with <b>Stealth</b>.
    # WW_806t (Sidewinder) carries Stealth in data.
    play = Summon(CONTROLLER, "WW_806t") * 2


class WW_810:
    """Camouflage Mount"""

    # Give a minion +3/+3 and a random <b>bonus effect</b>. When it dies,
    # summon a Chameleon. Each WW_810t<N>e1 enchant carries +3/+3, one
    # keyword, and the matching Chameleon-summoning deathrattle.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_MINION_TARGET: 0}
    play = Buff(
        TARGET,
        RandomID(
            "WW_810t1e1",
            "WW_810t2e1",
            "WW_810t3e1",
            "WW_810t4e1",
            "WW_810t5e1",
            "WW_810t6e1",
            "WW_810t7e1",
            "WW_810t8e1",
        ),
    )


# The eight Chameleon bonus-effect enchants. Each: +3/+3, one keyword
# stamped onto the host, and a deathrattle summoning the matching
# Chameleon token. The chameleon token itself carries its keyword in data.
class WW_810t1e1:
    # +3/+3 and Divine Shield. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.DIVINE_SHIELD: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t1")


class WW_810t2e1:
    # +3/+3 and Taunt. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.TAUNT: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t2")


class WW_810t3e1:
    # +3/+3 and Rush. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.RUSH: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t3")


class WW_810t4e1:
    # +3/+3 and Windfury. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.WINDFURY: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t4")


class WW_810t5e1:
    # +3/+3 and Stealth. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.STEALTH: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t5")


class WW_810t6e1:
    # +3/+3 and Poisonous. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.POISONOUS: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t6")


class WW_810t7e1:
    # +3/+3 and Lifesteal. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.LIFESTEAL: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t7")


class WW_810t8e1:
    # +3/+3 and Reborn. Deathrattle: Summon a Chameleon.
    tags = {
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.REBORN: True,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, "WW_810t8")


class WW_811:
    """Ten Gallon Hat"""

    # Draw a minion. Give it +1/+1 and "Deathrattle: Get a Ten Gallon Hat."
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION)).then(
        Buff(ForceDraw.TARGET, "WW_811e")
    )


class WW_811e:
    # +1/+1. Deathrattle: Get a Ten Gallon Hat.
    tags = {
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Give(CONTROLLER, "WW_811")


class WW_812:
    """Saddle Up!"""

    # Give your minions "Deathrattle: Summon a random Beast that costs (3)
    # or less."
    play = Buff(FRIENDLY_MINIONS, "WW_812e")


class WW_812e:
    # Deathrattle: Summon a random Beast that costs (3) or less.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Summon(CONTROLLER, RandomBeast(cost=range(0, 4)))


##
# Weapons


class WW_813:
    """Starshooter"""

    # After your hero attacks, get an Arcane Shot.
    events = Attack(FRIENDLY_HERO).after(Give(CONTROLLER, "DS1_185"))


##
# Minions


class WW_807:
    """Messenger Buzzard"""

    # Deathrattle: Draw a Beast. Give minions in your hand +1/+1.
    deathrattle = (
        ForceDraw(RANDOM(FRIENDLY_DECK + BEAST)),
        Buff(FRIENDLY_HAND + MINION, "WW_807e"),
    )


class WW_807e:
    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class WW_808:
    """Silver Serpent"""

    # Rush, Poisonous. Quickdraw: Gain Immune this turn.
    # Rush + Poisonous live in data; the Quickdraw bonus rides on top.
    play = QUICKDRAW & Buff(SELF, "WW_808e")


class WW_808e:
    # Immune this turn. TAG_ONE_TURN_EFFECT in data auto-clears; the
    # immune tags aren't parsed from data so declare them here.
    tags = {
        GameTag.CANT_BE_DAMAGED: True,
        GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
    }


class WW_809:
    """Bovine Skeleton"""

    # Deathrattle: If this has 4 or more Attack, summon a Bovine Skeleton.
    deathrattle = (ATK(SELF) >= 4) & Summon(CONTROLLER, "WW_809")


class WW_814:
    """Spurfang"""

    # Battlecry and Deathrattle: Summon a random Beast with Cost equal to
    # this minion's Attack.
    play = Summon(CONTROLLER, RandomBeast(cost=ATK(SELF)))
    deathrattle = Summon(CONTROLLER, RandomBeast(cost=ATK(SELF)))


class WW_815:
    """Theldurin the Lost"""

    # Battlecry: If your deck has no duplicates, gain Immune this turn and
    # attack all enemies.
    powered_up = -FindDuplicates(FRIENDLY_DECK)
    play = powered_up & (
        Buff(SELF, "WW_815e"),
        _TheldurinAttackAll(CONTROLLER),
    )


class WW_815e:
    # Immune this turn. TAG_ONE_TURN_EFFECT in data auto-clears; immune
    # tags not parsed from data so declare them here.
    tags = {
        GameTag.CANT_BE_DAMAGED: True,
        GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
    }
