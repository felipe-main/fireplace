from ..utils import *


##
# Minions


class TSC_026:
    """Colaque"""

    # Colossal +1. Immune while you control Colaque's Shell. The shell is
    # token TSC_026t with 8 HP, Taunt, DR Gain 8 Armor.
    update = Find(FRIENDLY_MINIONS + ID("TSC_026t")) & Refresh(
        SELF,
        {
            GameTag.CANT_BE_DAMAGED: True,
            GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
        },
    )


class TSC_026t:
    """Colaque's Shell"""

    deathrattle = GainArmor(FRIENDLY_HERO, 8)


class TSC_652:
    """Green-Thumb Gardener"""

    # Battlecry: Refresh empty Mana Crystals equal to the Cost of the most
    # expensive spell in your hand.
    def play(self):
        controller = self.controller
        spells = [c for c in controller.hand if c.type == CardType.SPELL and c is not self]
        if not spells:
            return
        top_cost = max(c.cost for c in spells)
        yield GainEmptyMana(CONTROLLER, top_cost)


class TSC_653:
    """Bottomfeeder"""

    # Deathrattle: Add a Bottomfeeder to the bottom of your deck with
    # permanent +2/+2.
    def deathrattle(self):
        # Stack +2/+2 on top of any existing buffs.
        atk_bonus = max(0, self.atk - 1) + 2
        hp_bonus = max(0, self.max_health - 3) + 2
        # Defer to PutOnBottom with a fresh copy that gets a buff.
        controller = self.controller
        copy = controller.card("TSC_653", self)
        yield PutOnBottom(CONTROLLER, copy)
        yield Buff(copy, "TSC_653e", atk=atk_bonus, max_health=hp_bonus)


@custom_card
class TSC_653e:
    tags = {
        GameTag.CARDNAME: "Bottomfed",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class TSC_657:
    """Dozing Kelpkeeper"""

    # Rush. Starts Dormant. After you've cast 5 Mana worth of spells
    # (since this card was summoned), awaken. The engine tracks
    # `spell_mana_spent_in_play` per-minion, reset to 0 on summon and
    # bumped in Play.do for every spell cast by the controller.
    # Dormant minions only fire `dormant_events`, not `events`, so the
    # awaken trigger lives there.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 99  # huge cap; awakening happens via the event below.
    dormant_events = OWN_SPELL_PLAY.after(
        (Attr(SELF, "spell_mana_spent_in_play") >= 5)
        & Awaken(SELF)
    )


class TSC_658:
    """Hedra the Heretic"""

    # Battlecry: For each spell you've cast while holding this, summon a
    # minion of that spell's Cost.
    def play(self):
        history = getattr(self, "spells_history_while_holding", [])
        for _card_id, cost in history:
            yield Summon(CONTROLLER, RandomMinion(cost=cost))


##
# Spells


class TSC_650:
    """Flipper Friends"""

    # Choose One - Summon a 6/6 Orca with Taunt; or six 1/1 Otters with Rush.
    choose = ("TSC_650a", "TSC_650d")
    play = ChooseBoth(CONTROLLER) & (
        Summon(CONTROLLER, "TSC_650t"),     # Orca
        Summon(CONTROLLER, "TSC_650t4") * 6,  # Otters
    )


class TSC_650a:
    """Order the Orca"""

    play = Summon(CONTROLLER, "TSC_650t")


class TSC_650d:
    """Romp of Otters"""

    play = Summon(CONTROLLER, "TSC_650t4") * 6


class TSC_651:
    """Seaweed Strike"""

    # Deal $4 damage to a minion. If you played a Naga while holding this,
    # also give your hero +4 Attack this turn.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        Hit(TARGET, 4),
        (Attr(SELF, "nagas_played_while_holding") > 0)
        & Buff(FRIENDLY_HERO, "TSC_651e"),
    )


class TSC_651e:
    tags = {GameTag.ATK: 4, enums.TEMPORARY: 1}


class TSC_654:
    """Aquatic Form"""

    # Dredge. If you have the Mana to play the card this turn, draw it.
    play = Dredge(CONTROLLER).then(
        (COST(Dredge.CARD) <= MANA(CONTROLLER))
        & ForceDraw(Dredge.CARD)
    )


class TSC_656:
    """Miracle Growth"""

    # Draw 3 cards. Summon a Plant with Taunt and stats equal to your hand size.
    def play(self):
        yield Draw(CONTROLLER) * 3
        n = len(self.controller.hand)
        # Approximation: spawn a generic Treant 2/2 with the buff sized to
        # hand size. We'll summon a known Treant token then buff.
        yield Summon(CONTROLLER, "EX1_158t").then(
            Buff(Summon.CARD, "TSC_656e", atk=n, max_health=n),
            Taunt(Summon.CARD),
        )


@custom_card
class TSC_656e:
    tags = {
        GameTag.CARDNAME: "Plant Growth",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class TSC_927:
    """Azsharan Gardens"""

    # Give all minions in your hand +1/+1. Put a 'Sunken Gardens' on the
    # bottom of your deck.
    play = (
        Buff(FRIENDLY_HAND + MINION, "TSC_927e"),
        PutOnBottom(CONTROLLER, "TSC_927t"),
    )


TSC_927e = buff(atk=1, health=1)


class TSC_927t:
    """Sunken Gardens"""

    # Give +1/+1 to all minions in your hand, deck, and battlefield.
    play = (
        Buff(FRIENDLY_HAND + MINION, "TSC_927e"),
        Buff(FRIENDLY_DECK + MINION, "TSC_927e"),
        Buff(FRIENDLY_MINIONS, "TSC_927e"),
    )
