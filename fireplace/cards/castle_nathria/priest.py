from ..utils import *


##
# Spells


class REV_248:
    """Boon of the Ascended"""

    # Give a minion +2 Health. Summon a Kyrian with its stats and Taunt.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(TARGET, "REV_248e"),
        Summon(CONTROLLER, "REV_248t").then(
            Buff(Summon.CARD, "REV_248k", atk=ATK(TARGET), max_health=CURRENT_HEALTH(TARGET)),
            Taunt(Summon.CARD),
        ),
    )


@custom_card
class REV_248k:
    tags = {
        GameTag.CARDNAME: "Ascended Kyrian Stats",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class REV_248e:
    tags = {GameTag.HEALTH: 2}


class REV_248t:
    """Ascended Kyrian"""


class REV_249:
    """The Light! It Burns!"""

    # Deal damage to a minion equal to its Attack.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, ATK(TARGET))


class REV_252:
    """Clean the Scene"""

    # Destroy all minions with 3 or less Attack. (Infused: 6 or less.)
    play = Destroy(ALL_MINIONS + (ATK <= 3))


class REV_252t:
    """Clean the Scene"""

    # Infused.
    play = Destroy(ALL_MINIONS + (ATK <= 6))


class REV_253:
    """Identity Theft"""

    # Discover a copy of a card from your opponent's hand and deck.
    # Approximation: copy a random card from opponent's hand.
    play = Give(CONTROLLER, Copy(RANDOM(ENEMY_HAND)))


##
# Minions


class REV_002:
    """Suspicious Usher"""

    # Battlecry: Discover a Legendary minion. If your opponent guesses
    # your choice, they get a copy. Approximated as Discover a Legendary
    # minion (no guess mini-game).
    play = DISCOVER(RandomLegendaryMinion())


class REV_011:
    """The Harvester of Envy"""

    # After you play a card copied from the opponent, steal the original.
    # Engine doesn't track "copied from opponent"; approximated as a
    # no-op trigger.
    pass


class REV_246:
    """Mysterious Visitor"""

    # Battlecry: Reduce the Cost of cards copied from your opponent by
    # (2). Approximated as a -2 cost buff on a random hand card.
    play = Buff(RANDOM(FRIENDLY_HAND - SELF), "REV_246e")


@custom_card
class REV_246e:
    tags = {
        GameTag.CARDNAME: "Mysterious Visitor Discount",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class REV_247:
    """Partner in Crime"""

    # Battlecry: Summon a copy of this minion at the end of your turn.
    play = Buff(CONTROLLER, "REV_247e")


class REV_247e:
    events = OWN_TURN_END.on(
        Summon(CONTROLLER, "REV_247"), Destroy(SELF)
    )


class REV_250:
    """Pelagos"""

    # After you cast a spell on a friendly minion, set its Attack and
    # Health to the higher of the two. Engine doesn't have a max() of
    # two LazyNums; approximation: copy ATK→max_health when target has
    # ATK > HEALTH, otherwise buff ATK by health-atk so it matches.
    events = OWN_SPELL_PLAY.after(
        (Find(Play.TARGET + MINION + FRIENDLY))
        & Buff(Play.TARGET, "REV_250e")
    )


@custom_card
class REV_250e:
    # Approximation buff — adds +1/+1 each spell instead of equalizing.
    tags = {
        GameTag.CARDNAME: "Pelagos Spell Buff",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
    }


##
# Locations


class REV_290:
    """Cathedral of Atonement"""

    # Give a minion +2/+1 and draw a card.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Buff(TARGET, "REV_290e"), Draw(CONTROLLER)


class REV_290e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}
