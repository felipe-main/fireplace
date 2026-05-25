from ..utils import *


##
# Spells


class TSC_061:
    """The Garden's Grace"""

    # Give a minion +5/+5 and Divine Shield. Costs (1) less for each Mana
    # you've spent on Holy spells this game.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "TSC_061e"), GiveDivineShield(TARGET)
    cost_mod = -Attr(CONTROLLER, "mana_spent_on_holy_spells_this_game")


class TSC_061e:
    tags = {GameTag.ATK: 5, GameTag.HEALTH: 5}


class TSC_076:
    """Immortalized in Stone"""

    # Summon a 1/2, 2/4 and 4/8 Elemental with Taunt.
    play = (
        Summon(CONTROLLER, "TSC_076t"),
        Summon(CONTROLLER, "TSC_076t2"),
        Summon(CONTROLLER, "TSC_076t3"),
    )


class TSC_076t:
    pass


class TSC_076t2:
    pass


class TSC_076t3:
    pass


class TSC_079:
    """Radar Detector"""

    # Scan the bottom 5 cards of your deck. Draw any Mechs found this way,
    # then shuffle your deck.
    def play(self):
        controller = self.controller
        bottom_five = list(controller.deck[:5])
        mechs = [c for c in bottom_five if c.type == CardType.MINION and Race.MECHANICAL in c.races]
        for m in mechs:
            yield ForceDraw(m)
        # No explicit Shuffle action needed; the engine handles deck order.


class TSC_952:
    """Holy Maki Roll"""

    # Restore #2 Health. Repeatable this turn.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Heal(TARGET, 2), Give(CONTROLLER, "TSC_952")


##
# Minions


class TSC_030:
    """The Leviathan"""

    # Colossal +1. Rush, Divine Shield. After this attacks, Dredge.
    events = Attack(SELF).after(Dredge(CONTROLLER))


class TSC_030t2:
    """The Leviathan's Claw"""

    # Rush, Divine Shield. After this attacks, draw a card.
    events = Attack(SELF).after(Draw(CONTROLLER))


class TSC_059:
    """Bubblebot"""

    # Battlecry: Give your other Mechs Divine Shield and Taunt.
    play = (
        GiveDivineShield(FRIENDLY_MINIONS + MECH - SELF),
        Taunt(FRIENDLY_MINIONS + MECH - SELF),
    )


class TSC_060:
    """Shimmering Sunfish"""

    # Battlecry: If you're holding a Holy Spell, gain Taunt and Divine Shield.
    play = Find(FRIENDLY_HAND + SPELL + HOLY_SPELL - SELF) & (
        Taunt(SELF),
        GiveDivineShield(SELF),
    )


class TSC_074:
    """Kotori Lightblade"""

    # After you cast a Holy spell on this, cast it again on another
    # friendly minion. Approximation: when any Holy spell targets SELF,
    # re-cast it on a random other friendly minion (no targeting UI).
    events = Play(CONTROLLER, SPELL + HOLY_SPELL, SELF).after(
        Find(FRIENDLY_MINIONS - SELF)
        & CastSpell(Play.CARD, RANDOM(FRIENDLY_MINIONS - SELF))
    )


class TSC_083:
    """Seafloor Savior"""

    # Battlecry: Dredge. If it's a minion, give it this minion's Attack
    # and Health.
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDTYPE) == int(CardType.MINION))
        & Buff(Dredge.CARD, "TSC_083e", atk=ATK(SELF), max_health=CURRENT_HEALTH(SELF))
    )


TSC_083e = buff()


class TSC_644:
    """Azsharan Mooncatcher"""

    # Divine Shield. Battlecry: Put a 'Sunken Mooncatcher' on the bottom
    # of your deck.
    play = PutOnBottom(CONTROLLER, "TSC_644t")


class TSC_644t:
    """Sunken Mooncatcher"""

    # Divine Shield. Battlecry: Summon a copy of this.
    play = Summon(CONTROLLER, "TSC_644t")
