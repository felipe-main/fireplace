from ..utils import *


##
# Minions


class AV_312:
    """Sacrificial Summoner"""

    # <b>Battlecry:</b> Destroy a friendly minion. Summon a minion from your
    # deck that costs (1) more.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Destroy(TARGET).then(
        Summon(
            CONTROLLER,
            RANDOM(FRIENDLY_DECK + MINION + (COST == Attr(TARGET, GameTag.COST) + 1)),
        )
    )


class AV_313:
    """Hollow Abomination"""

    # [x]<b>Battlecry:</b> Deal 1 damage to all enemy minions. <b>Honorable
    # Kill:</b> Gain the minion's Attack.
    play = Hit(ENEMY_MINIONS, 1)
    honorable_kill = Buff(SELF, "AV_313e", atk=Attr(HonorableKill.VICTIM, GameTag.ATK))


class AV_313e:
    tags = {GameTag.ATK: 0}  # Atk amount overridden via Buff kwarg at runtime


class AV_308:
    """Grave Defiler"""

    # <b>Battlecry:</b> Copy a Fel spell in your hand.
    play = Give(CONTROLLER, Copy(RANDOM(FRIENDLY_HAND + SPELL + FEL_SPELL)))


class AV_286:
    """Felwalker"""

    # <b>Taunt</b>. <b>Battlecry</b>: Cast the highest Cost Fel spell from
    # your hand.
    play = CastSpell(HIGHEST_COST(FRIENDLY_HAND + SPELL + FEL_SPELL))


##
# Spells


class AV_317:
    """Tamsin's Phylactery"""

    # <b>Discover</b> a friendly <b>Deathrattle</b> minion that died this
    # game. Give your minions its <b>Deathrattle</b>.
    play = DISCOVER(
        RandomCollectible(card_class=CardClass.WARLOCK, type=CardType.MINION)
    ).then(CopyDeathrattleBuff(FRIENDLY_MINIONS, Discover.CARD))


class AV_277:
    """Seeds of Destruction"""

    # [x]Shuffle four Rifts into your deck. They summon a 3/3 Dread Imp when
    # drawn.
    # AV_316t4 Fel Rift is the existing cast-when-drawn token that summons
    # AV_316t Dread Imp.
    play = Shuffle(CONTROLLER, "AV_316t4") * 4


class AV_316t4:
    """Fel Rift"""

    # <b>Casts When Drawn</b> Summon a 3/3 Dread Imp.
    play = Summon(CONTROLLER, "AV_316t")


class AV_281:
    """Felfire in the Hole!"""

    # Draw a spell and deal $2 damage to all enemies. If it's a Fel spell,
    # deal $1 more.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)).then(
        Hit(ENEMY_CHARACTERS, 2),
        (Attr(Draw.CARD, GameTag.SPELL_SCHOOL) == int(SpellSchool.FEL))
        & Hit(ENEMY_CHARACTERS, 1),
    )


class AV_285:
    """Full-Blown Evil"""

    # Deal $5 damage randomly split among all enemy minions. Repeatable this
    # turn.
    play = Hit(RANDOM(ENEMY_MINIONS), 1) * 5


class AV_657:
    """Desecrated Graveyard"""

    # [x]At the end of your turn, destroy your lowest Attack minion to
    # summon a 4/4 Shade. Lasts 3 turns.
    events = OWN_TURN_END.on(
        Destroy(LOWEST_ATK(FRIENDLY_MINIONS)),
        Summon(CONTROLLER, "AV_657t"),
    )


##
# Heros


class AV_316:
    """Dreadlich Tamsin"""

    # [x]<b>Battlecry:</b> Deal 3 damage to all minions. Shuffle 3 Rifts
    # into your deck. Draw 3 cards.
    play = (
        Hit(ALL_MINIONS, 3),
        Shuffle(CONTROLLER, "AV_316t4") * 3,
        Draw(CONTROLLER) * 3,
    )
