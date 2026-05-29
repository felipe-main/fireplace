from ..utils import *

from hearthstone.enums import CardType, GameTag, Zone


##
# Custom actions


class _HydrationResurrect(TargetedAction):
    """Hydration Station — Resurrect your 3 highest Cost Taunt minions.
    Picks, from the friendly graveyard, the 3 distinct dead Taunt minions
    with the highest Cost (ties broken by death order) and resummons fresh
    copies of each."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        dead_taunts = [
            c
            for c in ctrl.graveyard
            if c.type == CardType.MINION and bool(c.tags.get(GameTag.TAUNT))
        ]
        if not dead_taunts:
            return
        # Highest Cost first; graveyard order (recency) is the tiebreaker.
        ordered = sorted(dead_taunts, key=lambda c: c.cost, reverse=True)
        chosen = ordered[:3]
        for card in chosen:
            source.game.cheat_action(source, [Summon(ctrl, card.id)])


class _MistahVistahReplay(TargetedAction):
    """Mistah Vistah battlecry — start a 3-turn timer. Record every spell the
    controller casts (including this turn) until the timer elapses, then
    recast each recorded spell at the start of the controller's turn three
    turns later. Implemented by attaching a recording enchant to the
    controller that bumps a turn counter on each of the controller's
    turn-ends and, on the third, recasts the stored spell ids."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl._mistah_vistah_spells = []
        ctrl._mistah_vistah_turns = 3
        ctrl._mistah_vistah_active = True


class _MistahVistahRecord(TargetedAction):
    """OWN_SPELL_PLAY listener — append the just-cast spell's id to the
    controller's Mistah Vistah ledger while the timer is active."""

    CARD = ActionArg()

    def do(self, source, card):
        ctrl = source.controller
        if not getattr(ctrl, "_mistah_vistah_active", False):
            return
        if card is None or card.type != CardType.SPELL:
            return
        ctrl._mistah_vistah_spells.append(card.id)


class _MistahVistahTick(TargetedAction):
    """OWN_TURN_END listener — count down the Mistah Vistah timer; when it
    reaches zero, recast every recorded spell and clear the ledger."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if not getattr(ctrl, "_mistah_vistah_active", False):
            return
        ctrl._mistah_vistah_turns -= 1
        if ctrl._mistah_vistah_turns > 0:
            return
        spells = list(ctrl._mistah_vistah_spells)
        ctrl._mistah_vistah_active = False
        ctrl._mistah_vistah_spells = []
        for sid in spells:
            source.game.cheat_action(source, [CastSpell(sid)])


##
# Minions


# [x]<b>Battlecry:</b> Summon 2 random locations.
class VAC_506:
    """Cruise Captain Lora"""

    play = Summon(
        CONTROLLER, RandomCollectible(type=CardType.LOCATION)
    ) * 2


# [x]<b>Dormant</b> for 2 turns. While <b>Dormant</b>, summon a 3/5 Dragon with
# <b>Taunt</b> at the end of your turn.
class VAC_511:
    """Dozing Dragon"""

    dormant_turns = 2
    dormant_events = OWN_TURN_END.on(Summon(CONTROLLER, "VAC_511t"))


class VAC_511e:
    # In-data "Oversleeping" — Dormant. Awaken in @ turns.
    tags = {GameTag.DORMANT: True}


class VAC_511e2:
    """Sleepy"""


# Taunt
class VAC_511t:
    """Restless Whelp"""

    # 4/3/5 Taunt Dragon — stat line, race and Taunt all live in data.


# [x]<b>Taunt</b> <b>Deathrattle:</b> Draw another <b>Taunt</b> minion. Reduce
# its Cost by (2).
class VAC_518:
    """Tortollan Traveler"""

    deathrattle = ForceDraw(RANDOM(FRIENDLY_DECK + MINION + TAUNT)).then(
        Buff(ForceDraw.TARGET, "VAC_518e")
    )


class VAC_518e:
    # In-data "Travelling" — Costs (2) less.
    tags = {GameTag.COST: -2}


# [x]<b>Mage Tourist</b> <b>Battlecry:</b> In 3 turns, replay every spell
# you've cast between now and then.
class VAC_519:
    """Mistah Vistah"""

    # TOURIST is deckbuilding-only — implement just the Battlecry.
    play = _MistahVistahReplay(SELF)
    events = (
        OWN_SPELL_PLAY.on(_MistahVistahRecord(Play.CARD)),
        OWN_TURN_END.on(_MistahVistahTick(SELF)),
    )


# In 3 turns, recast every spell you played while this was in play.
class VAC_519t3:
    """Scenic Vista"""

    # Engine-internal marker token for Mistah Vistah's delayed replay; the
    # recording + recast is driven entirely off VAC_519's listeners, so this
    # token has no script of its own.


# [x]<b>Rush, Taunt</b> Costs (1) if you have at least 10 Mana Crystals.
class VAC_950:
    """Bouldering Buddy"""

    # Rush + Taunt live in data; the conditional cost set-to-1 is the script.
    cost_mod = (Attr(CONTROLLER, "max_mana") >= 10) & SET(1)


##
# Spells


# Gain 2 Mana Crystals next turn only.
class VAC_508:
    """Trail Mix"""

    play = Buff(CONTROLLER, "VAC_508e")


class VAC_508e:
    # In-data "Sugar Rush" — Gain 2 Mana Crystals this turn only. Trail Mix
    # applies it to the controller; at the start of their NEXT turn it grants
    # 2 temporary Mana this turn, then expires.
    events = OWN_TURN_BEGIN.on(ManaThisTurn(CONTROLLER, 2), Destroy(SELF))


# [x]<b>Choose Thrice - </b>Draw 2 cards; Gain 5 Armor; Refresh 3 Mana
# Crystals.
class VAC_907:
    """Sleep Under the Stars"""

    # Choose Thrice = all three effects always happen.
    play = (
        Draw(CONTROLLER) * 2,
        GainArmor(FRIENDLY_HERO, 5),
        ManaThisTurn(CONTROLLER, 3),
    )


# Draw 2 cards. (Sleep Under the Stars — Cat Constellation)
class VAC_907t1:
    """Cat Constellation"""

    play = Draw(CONTROLLER) * 2


# Gain 5 Armor. (Sleep Under the Stars — Bear Constellation)
class VAC_907t2:
    """Bear Constellation"""

    play = GainArmor(FRIENDLY_HERO, 5)


# Refresh 3 Mana Crystals. (Sleep Under the Stars — Moonkin Constellation)
class VAC_907t3:
    """Moonkin Constellation"""

    play = ManaThisTurn(CONTROLLER, 3)


# [x]Resurrect your 3 highest Cost <b>Taunt</b> minions.
class VAC_948:
    """Hydration Station"""

    play = _HydrationResurrect(SELF)


# [x]Increase your maximum Mana by 3 and gain an empty Mana Crystal.
class VAC_949:
    """New Heights"""

    play = GainMana(CONTROLLER, 3), GainEmptyMana(CONTROLLER, 1)


##
# Locations


# <b>Discover</b> a <b>Taunt</b> minion. After you gain Armor, reopen this.
class VAC_517:
    """Hiking Trail"""

    activate = DISCOVER(
        RandomMinion(custom_filter=lambda c: bool(c.tags.get(GameTag.TAUNT)))
    )
    events = GainArmor(FRIENDLY_HERO).after(ReopenLocation(SELF))
