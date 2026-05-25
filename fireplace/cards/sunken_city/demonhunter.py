from ..utils import *


##
# Spells


class TSC_006:
    """Multi-Strike"""

    # Give your hero +2 Attack this turn. They may attack an additional enemy minion.
    play = Buff(FRIENDLY_HERO, "TSC_006e")


class TSC_006e:
    tags = {GameTag.ATK: 2, enums.TEMPORARY: 1}


class TSC_058:
    """Predation"""

    # Deal $3 damage. Costs (0) if you played a Naga while holding this.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3)
    cost_mod = -Attr(SELF, "nagas_played_while_holding") * 100


class TSC_608:
    """Abyssal Depths"""

    # Draw your two lowest Cost minions.
    play = ForceDraw(LOWEST_COST(FRIENDLY_DECK + MINION)) * 2


class TSC_915:
    """Bone Glaive"""

    # Weapon. Battlecry: Dredge.
    play = Dredge(CONTROLLER)


##
# Minions


class TSC_057:
    """Azsharan Defector"""

    # Rush. Deathrattle: Put a 'Sunken Defector' on the bottom of your deck.
    deathrattle = PutOnBottom(CONTROLLER, "TSC_057t")


class TSC_057t:
    """Sunken Defector"""

    # Charge + after this attacks, deal 5 damage to a random enemy minion.
    tags = {GameTag.CHARGE: True}
    events = Attack(SELF).after(
        Find(ENEMY_MINIONS) & Hit(RANDOM(ENEMY_MINIONS), 5)
    )


class TSC_217:
    """Wayward Sage"""

    # Outcast: Reduce the Cost of the left- and right-most cards in your
    # hand by (1).
    outcast = Buff(FRIENDLY_HAND + PLAY_OUTCAST - SELF, "TSC_217e")


class TSC_217e:
    tags = {GameTag.COST: -1}


class TSC_218:
    """Lady S'theno"""

    # Immune while attacking. After you cast a spell, attack the lowest
    # Health enemy.
    tags = {GameTag.IMMUNE_WHILE_ATTACKING: True}
    events = OWN_SPELL_PLAY.after(
        Find(ENEMY_CHARACTERS) & Attack(SELF, LOWEST_HEALTH(ENEMY_CHARACTERS))
    )


class TSC_219:
    """Xhilag of the Abyss"""

    # Colossal +4. At the start of your turn, increase the damage of
    # Xhilag's Stalks by 1. Implemented as a +1 ATK buff on stalks (the
    # stalks deal damage equal to their ATK in our scripting).
    events = OWN_TURN_BEGIN.on(
        Buff(
            FRIENDLY_MINIONS
            + (
                ID("TSC_219t")
                | ID("TSC_219t2")
                | ID("TSC_219t3")
                | ID("TSC_219t4")
            ),
            "TSC_219te",
        )
    )


class TSC_219t:
    """Xhilag's Stalk"""

    # At the end of your turn, deal damage to a random enemy equal to
    # this minion's Attack.
    events = OWN_TURN_END.on(Hit(RANDOM_ENEMY_CHARACTER, ATK(SELF)))


class TSC_219t2(TSC_219t):
    pass


class TSC_219t3(TSC_219t):
    pass


class TSC_219t4(TSC_219t):
    pass


@custom_card
class TSC_219te:
    tags = {
        GameTag.CARDNAME: "Xhilag's Wrath",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
    }


class TSC_609(ThreeSpellsProgressUtils):
    """Coilskar Commander"""

    # Taunt. Battlecry: If you've cast three spells while holding this,
    # summon two copies of this.
    play = (Attr(SELF, "spells_cast_while_holding") >= 3) & (
        Summon(CONTROLLER, "TSC_609") * 2
    )


class TSC_610:
    """Glaiveshark"""

    # Battlecry: If your hero attacked this turn, deal 2 damage to all enemies.
    play = (Attr(FRIENDLY_HERO, "num_attacks") > 0) & Hit(ENEMY_CHARACTERS, 2)
