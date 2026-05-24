from ..utils import *


##
# Minions


class AV_340:
    """Brasswing"""

    # [x]At the end of your turn, deal 2 damage to all enemies. <b>Honorable
    # Kill:</b> Restore 4 Health to your hero.
    events = OWN_TURN_END.on(Hit(ENEMY_CHARACTERS, 2))
    honorable_kill = Heal(FRIENDLY_HERO, 4)


class AV_339:
    """Templar Captain"""

    # [x]<b>Rush</b>. After this attacks a minion, summon a 5/5 Defender with
    # <b>Taunt</b>.
    # AV_342t Stormpike Defender is the shared 5/5 Taunt token.
    events = Attack(SELF, MINION).after(Summon(CONTROLLER, "AV_342t"))


class AV_343:
    """Stonehearth Vindicator"""

    # [x]<b>Battlecry:</b> Draw a spell that costs (3) or less. It costs (0)
    # this turn.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST <= 3))).then(
        Buff(Draw.CARD, "AV_343e")
    )


class AV_343e:
    tags = {GameTag.COST: SET(0)}
    events = OWN_TURN_END.on(Destroy(SELF))


class AV_345:
    """Saidan the Scarlet"""

    # <b>Rush.</b> Whenever this minion gains Attack or Health, double that
    # amount <i>(wherever this is)</i>. The Buff action consults
    # target.buffs_doubled and doubles positive atk/health values before
    # applying.
    buffs_doubled = lambda self, x: True


##
# Spells


class AV_213:
    """Vitality Surge"""

    # Draw a minion. Restore Health to your hero equal to its Cost.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)).then(
        Heal(FRIENDLY_HERO, Attr(Draw.CARD, GameTag.COST))
    )


class AV_338:
    """Hold the Bridge"""

    # [x]Give a minion +2/+1 and <b>Divine Shield</b>. It gains
    # <b>Lifesteal</b> until end of turn.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "AV_338e"), GiveDivineShield(TARGET)


class AV_338e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1, GameTag.LIFESTEAL: True}


class AV_342:
    """Protect the Innocent"""

    # Summon a 5/5 Defender with <b>Taunt</b>. If your hero was healed this
    # turn, summon another.
    play = Summon(CONTROLLER, "AV_342t").then(
        (Attr(CONTROLLER, "healed_this_turn") > 0) & Summon(CONTROLLER, "AV_342t")
    )


class AV_344:
    """Dun Baldar Bridge"""

    # [x]After you summon a minion, give it +2/+2. Lasts 3 turns.
    events = Summon(CONTROLLER, MINION).after(Buff(Summon.CARD, "AV_344e"))


AV_344e = buff(atk=2, health=2)


##
# Weapons


class AV_341:
    """Cavalry Horn"""

    # <b>Deathrattle:</b> Summon the lowest Cost minion in your hand.
    deathrattle = Summon(CONTROLLER, LOWEST_COST(FRIENDLY_HAND + MINION))


##
# Heros


class AV_206:
    """Lightforged Cariel"""

    # [x]<b>Battlecry:</b> Deal 2 damage to all enemies. Equip a 2/5
    # Immovable Object.
    # AV_146 is the existing Immovable Object weapon (2/5).
    play = Hit(ENEMY_CHARACTERS, 2), Summon(CONTROLLER, "AV_146")


class AV_146:
    """The Immovable Object"""

    # This doesn't lose Durability. Your hero takes half damage, rounded up.
    doesnt_lose_durability = lambda self, x: True
    incoming_damage_divider = lambda self, x: 2
