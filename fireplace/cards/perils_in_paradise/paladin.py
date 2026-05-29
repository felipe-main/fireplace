from ..utils import *


##
# Custom actions / helpers


class _LynessaRecast(TargetedAction):
    """Sunsapper Lynessa — when the controller casts a spell that costs (2)
    or less, cast a fresh copy of it (at the same target if it had one).

    `spells_cast_twice` would double *every* spell regardless of cost, so the
    cost gate is enforced here by re-casting a copy of cheap spells only.
    Guards against infinite recursion via a per-cast `_lynessa_recasting`
    marker on the copy."""

    TARGET = ActionArg()

    def do(self, source, target):
        card = target
        if card is None or card.type != CardType.SPELL:
            return
        if getattr(card, "_lynessa_recasting", False):
            return
        if (card.cost or 0) > 2:
            return
        player = source.controller
        copy = player.card(card.id, source=source)
        copy.controller = player
        copy._lynessa_recasting = True
        spell_target = card.target if card.requires_target() else None
        source.game.queue_actions(source, [CastSpell(copy, spell_target)])


class _DivineBrew(TargetedAction):
    """Divine Brew (and its Drink copies) — give a character Divine Shield. If
    it already had one, instead give it +1 Attack this turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, (list, tuple)):
            target = target[0] if target else None
        if target is None:
            return
        # "Give a character Divine Shield" — heroes can be targeted but have no
        # divine_shield attribute, so read it defensively.
        if getattr(target, "divine_shield", False):
            source.game.cheat_action(source, [Buff(target, "VAC_916e")])
        else:
            source.game.cheat_action(source, [GiveDivineShield(target)])


class _LifesavingTick(TargetedAction):
    """Lifesaving Aura countdown — decrement the remaining duration and
    destroy the enchant when it reaches zero."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        left = getattr(enchant, "_lifesaving_turns_left", 0) - 1
        enchant._lifesaving_turns_left = max(0, left)
        if left <= 0:
            enchant.game.cheat_action(enchant, [Destroy(enchant)])


class _SancAzelToLocation(TargetedAction):
    """Sanc'Azel — after the minion attacks, turn it into its Location form
    (VAC_923t), preserving its current Health via the Sandy Castle enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        minion = target
        if minion is None or minion.zone != Zone.PLAY:
            return
        if minion.type != CardType.MINION:
            return
        cur_health = minion.health
        location = source.game.queue_actions(
            source, [Morph(minion, "VAC_923t")]
        )
        loc = None
        if location and isinstance(location, list) and location[0]:
            loc = location[0][0] if isinstance(location[0], list) else location[0]
        loc = minion.controller.location
        if loc is not None and loc.id == "VAC_923t":
            # Preserve the minion's current Health on the location form.
            delta = cur_health - loc.max_health
            if delta:
                source.game.cheat_action(
                    source, [Buff(loc, "VAC_923e", max_health=delta)]
                )


class _SancAzelToMinion(TargetedAction):
    """Sanc'Azel's Location activate — give a friendly minion +3 Attack and
    Rush, then turn the location back into the Sanc'Azel minion (preserving
    its current Health)."""

    TARGET = ActionArg()

    def do(self, source, target):
        location = source
        cur_health = location.durability
        if isinstance(target, (list, tuple)):
            target = target[0] if target else None
        if target is not None and target.zone == Zone.PLAY:
            source.game.cheat_action(
                source, [Buff(target, "VAC_923e2", atk=3), GiveRush(target)]
            )
        # Turn back into the minion.
        morphed = source.game.queue_actions(location, [Morph(location, "VAC_923")])
        minion = None
        for m in location.controller.field:
            if m.id == "VAC_923":
                minion = m
        if minion is not None:
            delta = cur_health - minion.max_health
            if delta:
                source.game.cheat_action(
                    source, [Buff(minion, "VAC_923e", max_health=delta)]
                )


##
# Minions


class VAC_507:
    """Sunsapper Lynessa"""

    # Rogue Tourist. Your spells that cost (2) or less cast twice.
    # (TOURIST is deckbuilding-only; only the spell-doubling is scripted.)
    events = OWN_SPELL_PLAY.after(_LynessaRecast(Play.CARD))


class VAC_507e:
    """Sunbathing"""

    # Marker enchant (no in-game stat effect; data-only).
    pass


class VAC_917:
    """Grillmaster"""

    # Battlecry: Draw your lowest Cost card. Deathrattle: Draw your highest
    # Cost card.
    play = Draw(CONTROLLER, LOWEST_COST(FRIENDLY_DECK))
    deathrattle = Draw(CONTROLLER, HIGHEST_COST(FRIENDLY_DECK))


class VAC_917e:
    """Sunscreen"""

    # +1/+2.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class VAC_917t:
    """Sunscreen"""

    # Give a minion +1/+2.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "VAC_917e")


class VAC_919:
    """Lifeguard"""

    # Taunt. Battlecry: The next spell you cast has Lifesteal.
    play = Buff(CONTROLLER, "VAC_919e")


class VAC_919e:
    """Protection"""

    # Your next spell has Lifesteal. Grant the LIFESTEAL tag to the spell as
    # it's played (before its effect resolves), then consume the enchant.
    events = Play(CONTROLLER, SPELL).on(GiveLifesteal(Play.CARD), Destroy(SELF))


class VAC_920:
    """Service Ace"""

    # After this minion gains Attack, reduce the Cost of the highest Cost card
    # in your hand by (1).
    events = Buff(SELF, ATK > 0).after(Buff(HIGHEST_COST(FRIENDLY_HAND), "VAC_920e"))


class VAC_920e:
    """Excellent Service"""

    # Costs (1) less.
    tags = {GameTag.COST: -1}


class VAC_923:
    """Sanc'Azel"""

    # Rush. After this attacks, turn into a location.
    events = Attack(SELF).after(_SancAzelToLocation(SELF))


class VAC_923e:
    """Sandy Castle"""

    # Has the stats of Sanc'Azel (health carried across the transform; stats
    # supplied at apply time).
    pass


class VAC_923e2:
    """Sandy"""

    # Increased Attack (+3 from Sanc'Azel's location activate).
    pass


class VAC_923t:
    """Sanc'Azel"""

    # Give a friendly minion +@ Attack and Rush. Turn back into a minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = _SancAzelToMinion(TARGET)


##
# Spells


class VAC_558:
    """Sea Shanty"""

    # Summon three 5/5 Pirates. Costs (1) less for each spell you've cast on
    # characters this game.
    play = Summon(CONTROLLER, "VAC_558t") * 3
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME + SPELL)


class VAC_558t:
    """Chorus Corsair"""

    # 5/5 Pirate (vanilla token).
    pass


class VAC_915:
    """Power Spike"""

    # Deal $4 damage. Give a random friendly minion +4/+4.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = (
        Hit(TARGET, 4),
        Buff(RANDOM_FRIENDLY_MINION, "VAC_915e"),
    )


class VAC_915e:
    """Power Spike"""

    # +4/+4.
    tags = {GameTag.ATK: 4, GameTag.HEALTH: 4}


class VAC_916:
    """Divine Brew"""

    # Give a character Divine Shield. If it already had one, give it +1 Attack
    # this turn. (3 Drinks left!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = _DivineBrew(TARGET), Give(CONTROLLER, "VAC_916t2")


class VAC_916t2:
    """Divine Brew"""

    # (2 Drinks left!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = _DivineBrew(TARGET), Give(CONTROLLER, "VAC_916t3")


class VAC_916t3:
    """Divine Brew"""

    # (Last Drink!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = _DivineBrew(TARGET)


class VAC_916e:
    """Cold One"""

    # +1 Attack this turn.
    tags = {GameTag.ATK: 1}
    events = OWN_TURN_END.on(Destroy(SELF))


class VAC_922:
    """Lifesaving Aura"""

    # At the end of your turn, get a 1-Cost Sunscreen that gives +1/+2.
    # Lasts @ turns (3).
    play = Buff(CONTROLLER, "VAC_922e")

    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class VAC_922e:
    """Lifesaving Aura"""

    # Controller aura: at end of turn give a 1-Cost Sunscreen; lasts 3 turns.
    tags = {
        GameTag.CARDNAME: "Lifesaving Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [
        OWN_TURN_END.on(Give(CONTROLLER, "VAC_917t")),
        OWN_TURN_END.on(_LifesavingTick(SELF)),
    ]

    def apply(self, target):
        self._lifesaving_turns_left = 3


##
# Weapons


class VAC_921:
    """Volley Maul"""

    # After your hero attacks, get a 1-Cost Sunscreen that gives +1/+2.
    events = Attack(FRIENDLY_HERO).after(Give(CONTROLLER, "VAC_917t"))
