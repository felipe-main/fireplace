from ..utils import *


##
# Minions


class AV_101:
    """Herald of Lokholar"""

    # <b>Battlecry:</b> Draw a Frost spell.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL))


class AV_215:
    """Frantic Hippogryph"""

    # <b>Rush</b>. <b>Honorable Kill</b>: Gain <b>Windfury</b>.
    honorable_kill = GiveWindfury(SELF)


class AV_219:
    """Ram Commander"""

    # [x]<b>Battlecry:</b> Add two 1/1 Rams with <b>Rush</b> to your hand.
    play = Give(CONTROLLER, "AV_219t") * 2


class AV_238:
    """Gankster"""

    # [x]<b>Stealth</b> After your opponent plays a minion, attack it.
    events = Play(OPPONENT, MINION).after(Attack(SELF, Play.CARD))


class AV_309:
    """Piggyback Imp"""

    # <b>Deathrattle:</b> Summon a 4/1 Imp.
    deathrattle = Summon(CONTROLLER, "AV_309t")


class AV_704:
    """Humongous Owl"""

    # <b>Deathrattle:</b> Deal 8 damage to a random enemy.
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 8)


class AV_121:
    """Gnome Private"""

    # [x]<b>Honorable Kill:</b> Gain +2 Attack.
    honorable_kill = Buff(SELF, "AV_121e")


AV_121e = buff(atk=2)


class AV_122:
    """Corporal"""

    # <b>Honorable Kill:</b> Give your other minions <b>Divine Shield</b>.
    honorable_kill = GiveDivineShield(FRIENDLY_MINIONS - SELF)


class AV_123:
    """Sneaky Scout"""

    # [x]<b>Stealth</b> <b>Honorable Kill:</b> Your next Hero Power costs (0).
    honorable_kill = IncreaseAttr(CONTROLLER, "next_hero_power_costs_zero", 1)


class AV_124:
    """Direwolf Commander"""

    # <b>Honorable Kill:</b> Summon a 2/2 Wolf with <b>Stealth</b>.
    honorable_kill = Summon(CONTROLLER, "AV_211t")


class AV_125:
    """Tower Sergeant"""

    # <b>Battlecry:</b>  If you control at_least 2 other minions, gain +2/+2.
    play = (Count(FRIENDLY_MINIONS - SELF) >= 2) & Buff(SELF, "AV_125e")


AV_125e = buff(atk=2, health=2)


class AV_126:
    """Bunker Sergeant"""

    # [x]<b>Battlecry:</b> If your opponent has 2 or more minions, deal 1
    # damage to all enemy minions.
    play = (Count(ENEMY_MINIONS) >= 2) & Hit(ENEMY_MINIONS, 1)


class AV_127:
    """Ice Revenant"""

    # Whenever you cast a Frost spell, gain +2/+2.
    events = Play(CONTROLLER, SPELL + FROST_SPELL).on(Buff(SELF, "AV_127e"))


AV_127e = buff(atk=2, health=2)


class AV_129:
    """Blood Guard"""

    # Whenever this minion takes damage, give your minions +1 Attack.
    events = Damage(SELF).on(Buff(FRIENDLY_MINIONS, "AV_129e"))


AV_129e = buff(atk=1)


class AV_130:
    """Legionnaire"""

    # <b>Deathrattle:</b> Give all minions in your hand +2/+2.
    deathrattle = Buff(FRIENDLY_HAND + MINION, "AV_130e")


AV_130e = buff(atk=2, health=2)


class AV_131:
    """Knight-Captain"""

    # [x]<b>Battlecry:</b> Deal 3 damage. <b>Honorable Kill:</b> Gain +3/+3.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 3)
    honorable_kill = Buff(SELF, "AV_131e")


AV_131e = buff(atk=3, health=3)


class AV_132:
    """Troll Centurion"""

    # [x]<b>Rush</b>. <b>Honorable Kill:</b> Deal 8 damage to the enemy hero.
    honorable_kill = Hit(ENEMY_HERO, 8)


class AV_133:
    """Icehoof Protector"""

    # <b>Taunt</b> <b>Freeze</b> any character damaged by this minion.
    events = Damage(ALL_CHARACTERS, source=SELF).after(Freeze(Damage.TARGET))


class AV_401:
    """Stormpike Quartermaster"""

    # After you cast a spell, give a random minion in your hand +1/+1.
    events = Play(CONTROLLER, SPELL).after(
        Buff(RANDOM(FRIENDLY_HAND + MINION), "AV_401e")
    )


AV_401e = buff(atk=1, health=1)


class AV_256:
    """Reflecto Engineer"""

    # <b>Battlecry:</b> Swap the Attack and Health of all minions in both
    # players' hands. AV_256e "Reflected" is Blizzard's real swap enchant.
    play = (
        Buff(FRIENDLY_HAND + MINION, "AV_256e"),
        Buff(ENEMY_HAND + MINION, "AV_256e"),
    )


AV_256e = AttackHealthSwapBuff()
