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


class _LifeCycleReplace(TargetedAction):
    """Life Cycle - destroy the target, then summon a random minion of the
    *same Cost* into the freed slot.

    The naive script summoned the replacement *before* the destroy resolved,
    which had two problems:
      1. A full board (7 minions including the target) made the summon a
         no-op — `is_summonable()` returns False at 7 minions, so the
         replacement was silently dropped, and only the destroy ran. The
         printed card frees the slot first, so a same-Cost minion always
         appears.
      2. The replacement landed beside the original rather than in its
         vacated position.

    This action snapshots the target's Cost up front (so cost auras at cast
    time are honoured even though the minion is gone by summon time), destroys
    the target, processes the death so its slot frees and `_dead_position` is
    recorded, then summons a same-Cost minion into that freed slot on the
    target's controller's side.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        cost = target.cost
        controller = target.controller
        source.game.cheat_action(source, [Destroy(target)])
        source.game.process_deaths()
        # Place the replacement into the vacated slot (HS slides the new
        # minion into the destroyed minion's position).
        dead_pos = getattr(target, "_dead_position", None)
        pick = RandomMinion(cost=cost).evaluate(source)
        if not pick:
            return
        card_id = pick[0] if isinstance(pick, (list, tuple)) else pick
        if len(controller.field) >= source.game.MAX_MINIONS_ON_FIELD:
            return
        replacement = controller.card(card_id, source=source)
        if dead_pos is not None:
            replacement._summon_index = dead_pos
        source.game.cheat_action(source, [Summon(controller, replacement)])


class TLC_235:
    """Life Cycle"""

    # Destroy a minion. Summon a random minion of the same Cost to replace it.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    # Destroy the target first (freeing its board slot, so the replacement
    # always lands even from a full board), then summon a same-Cost minion
    # into the vacated position. Cost is snapshotted before the destroy.
    play = _LifeCycleReplace(TARGET)


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


##
# The Lost City of Un'Goro mini-set — Dinosaurs (DINO_)


class DINO_130:
    """Longneck Egg"""

    # <b>Deathrattle:</b> Summon a 1/2 Beast. Give your minions +1/+1.
    # Summon the Little Longneck first so the "your minions +1/+1" buff
    # (FRIENDLY_MINIONS) also lands on the freshly-summoned token.
    deathrattle = Summon(CONTROLLER, "DINO_130t").then(
        Buff(FRIENDLY_MINIONS, "DINO_130e")
    )


class DINO_130t:
    """Little Longneck"""

    # 1/2 Beast (stats + Beast race live in data).


class DINO_130e:
    """Long Neck"""

    # +1/+1. (The data enchant carries only visual tags, so supply the real
    # stat buff here.)
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class DINO_421:
    """Seismopod"""

    # <b>Taunt</b>, <b>Elusive</b> <b>Deathrattle:</b> Give all minions in
    # your hand and deck +3/+3. Taunt lives in data; Elusive's data tag isn't
    # mapped to targeting flags by python-hearthstone, so restore it here.
    tags = {
        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }
    deathrattle = Buff(FRIENDLY_HAND + MINION, "DINO_421e"), Buff(
        FRIENDLY_DECK + MINION, "DINO_421e"
    )


class DINO_421e:
    """Seismic"""

    # +3/+3. (The data enchant carries only visual tags, so supply the real
    # stat buff here.)
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class DINO_432:
    """Panther Mask"""

    # Set a minion's stats to 5/4 and give it <b>Stealth</b>. Draw 2 cards.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "DINO_432e"), Draw(CONTROLLER) * 2


class DINO_432e:
    """Panther Mask"""

    # 5/4 and Stealth. Set stats (atk/max_health overrides, mirroring the
    # set-cost enchant pattern) plus the Stealth keyword tag.
    atk = SET(5)
    max_health = SET(4)
    tags = {GameTag.STEALTH: True}
