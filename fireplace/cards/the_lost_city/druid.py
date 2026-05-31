from ..utils import *


##
# Minions


class TLC_233:
    """Hatchery Helper"""

    # [x]<b>Battlecry:</b> Give your other minions with 2 or less Attack
    # +1/+2 and <b>Taunt</b>.
    play = Buff(FRIENDLY_MINIONS - SELF + (ATK <= 2), "TLC_233e")


class TLC_233e:
    """Incubate"""

    # +1/+2 and Taunt. (The data enchant only carries visual tags, so the real
    # stat + keyword tags are supplied here.)
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2, GameTag.TAUNT: True}


class TLC_234:
    """Eternal Bloodpetal"""

    # <b>Deathrattle:</b> Summon a 0/1 Eternal Seedling.
    deathrattle = Summon(CONTROLLER, "TLC_234t")


class TLC_234t:
    """Eternal Seedling"""

    # <b>Deathrattle:</b> Summon a 5/1 Eternal Bloodpetal.
    deathrattle = Summon(CONTROLLER, "TLC_234")


class TLC_237:
    """Skyscreamer Eggs"""

    # <b>Deathrattle:</b> Summon four 2/1 Hatchlings.
    deathrattle = Summon(CONTROLLER, "TLC_237t") * 4


class TLC_237t:
    """Skyscreamer Hatchling"""


class TLC_257:
    """Loh, the Living Legend"""

    # <b>Battlecry:</b> Your minions cost (5) this game.
    play = Buff(FRIENDLY_HERO, "TLC_257e1")


class TLC_257e1:
    """Living Legend"""

    # Your minions cost (5) this game. Persistent enchant on the hero; the
    # update refreshes every friendly minion in hand (including ones drawn
    # later) to a flat cost of 5.
    update = Refresh(FRIENDLY_HAND + MINION, {GameTag.COST: SET(5)})


##
# Spells


class TLC_230:
    """TREEEES!!!"""

    # Choose a minion. Summon four 2/2 Treants that attack it.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = (Summon(CONTROLLER, "TLC_230t").then(Attack(Summon.CARD, TARGET))) * 4


class TLC_230t:
    """Treant"""


class TLC_231:
    """Story of Barnabus"""

    # Draw a minion. If it has 5 or more Attack, give it +5 Health and gain 5 Armor.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)).then(
        (Attr(Draw.CARD, GameTag.ATK) >= 5)
        & (Buff(Draw.CARD, "TLC_231e"), GainArmor(FRIENDLY_HERO, 5))
    )


class TLC_231e:
    """Might of Barnabus"""

    # +5 Health. (The data enchant stores the value in a script-data tag only,
    # so the real HEALTH buff is supplied here.)
    tags = {GameTag.HEALTH: 5}


class TLC_232:
    """Ravenous Flock"""

    # At the start of your next turn, summon three 2/1 Hatchlings. An OBJECTIVE
    # spell: it parks in the secret zone and fires on the controller's next
    # turn-begin, then destroys itself.
    lasts_for = 2
    events = OWN_TURN_BEGIN.on(Summon(CONTROLLER, "TLC_237t") * 3, Destroy(SELF))


class TLC_235:
    """Life Cycle"""

    # Destroy a minion. Summon a random minion of the same Cost to replace it.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    # Summon the replacement (same Cost) on the destroyed minion's side, then
    # destroy the original. COST(TARGET) is read before the destroy resolves.
    play = (
        Summon(Controller(TARGET), RandomMinion(cost=COST(TARGET))),
        Destroy(TARGET),
    )


class TLC_236:
    """Hybridization"""

    # Draw a 1, 2, 3, and 4-Cost minion. <b>Kindred:</b> They cost (1) less.
    play = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST == 1))).then(
            Kindred() & Buff(Draw.CARD, "TLC_236e")
        ),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST == 2))).then(
            Kindred() & Buff(Draw.CARD, "TLC_236e")
        ),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST == 3))).then(
            Kindred() & Buff(Draw.CARD, "TLC_236e")
        ),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST == 4))).then(
            Kindred() & Buff(Draw.CARD, "TLC_236e")
        ),
    )


@custom_card
class TLC_236e:
    """Hybridization"""

    # Costs (1) less.
    tags = {
        GameTag.CARDNAME: "Hybridization",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


##
# Quests


class TLC_239:
    """Restore the Wild"""

    # <b>Quest:</b> Fill your board on 3 of your turns. <b>Reward:</b> The Everbloom.
    progress_total = 3
    quest = OWN_TURN_END.on(FULL_BOARD & AddProgress(SELF))
    reward = Summon(CONTROLLER, "TLC_239t")


class TLC_239t:
    """The Everbloom"""

    # After your hero attacks, give your minions +2/+2.
    events = Attack(FRIENDLY_HERO).after(Buff(FRIENDLY_MINIONS, "TLC_239e"))


class TLC_239e:
    """Full Bloom"""

    # +2/+2. (The data enchant carries only visual tags, so supply the real
    # stat buff here.)
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}
