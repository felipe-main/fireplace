from ..utils import *


##
# Minions


# Rush. Starts Dormant. After you draw 4 cards, this awakens.
class TTN_840:
    """Crystalline Statue"""

    tags = {GameTag.RUSH: True, GameTag.DORMANT: True}
    # dormant_turns set large — awakening is event-driven, not timer-driven.
    dormant_turns = 99
    # progress_total = 4: AddProgress tracks draw count; awaken at 4.
    progress_total = 4
    dormant_events = Draw(CONTROLLER).on(
        AddProgress(SELF, Draw.CARD),
        (CURRENT_PROGRESS(SELF) >= 4) & Awaken(SELF),
    )


# Whenever you draw a card, summon a 1/1 Demon with Rush.
# TTN_843t1 "Invading Felbat" is the 1/1 Demon Rush token.
class TTN_843:
    """Eredar Deceptor"""

    events = Draw(CONTROLLER).on(Summon(CONTROLLER, "TTN_843t1"))


# Has +1 Attack for each card you've drawn this turn.
# Dynamic aura reads the per-turn draw counter.
class TTN_844:
    """Argunite Golem"""

    update = Refresh(
        SELF,
        {GameTag.ATK: Attr(CONTROLLER, GameTag.NUM_CARDS_DRAWN_THIS_TURN)},
    )


# Battlecry: For the rest of the game, cast a copy of the first spell you
# draw each turn at enemies.
# Implementation: stamp a permanent enchantment on the hero that:
#   — listens for Draw(CONTROLLER) and casts the first spell drawn each turn;
#   — resets the "already cast this turn" flag at OWN_TURN_BEGIN.
class _JotunDrawEffect(TargetedAction):
    """Cast-when-drawn handler: if it's a spell and no spell has been cast
    by Jotun yet this turn, cast a copy at a random enemy."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType

        ctrl = source.controller
        if not hasattr(target, "type") or target.type != CardType.SPELL:
            return
        if getattr(ctrl, "_jotun_cast_this_turn", False):
            return
        ctrl._jotun_cast_this_turn = True
        source.game.cheat_action(
            source, [CastSpellTargetsEnemiesIfPossible(target)]
        )


class _JotunResetTurn(TargetedAction):
    """Reset per-turn Jotun flag at the start of each turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller._jotun_cast_this_turn = False


@custom_card
class TTN_842e:
    tags = {
        GameTag.CARDNAME: "Jotun's Eternal Grasp",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [
        Draw(CONTROLLER).on(_JotunDrawEffect(Draw.CARD)),
        OWN_TURN_BEGIN.on(_JotunResetTurn(SELF)),
    ]


class TTN_842:
    """Jotun, the Eternal"""

    play = Buff(FRIENDLY_HERO, "TTN_842e")


# TTN_842t1 "Jotun's Swiftness" is in data; no class needed.


# Deathrattle: Summon two 2/2 Elementals with Taunt.
# TTN_862t4 "Crystal Elemental" is the 2/2 Elemental with Taunt in data.
class TTN_861:
    """Disciple of Argus"""

    deathrattle = Summon(CONTROLLER, "TTN_862t4") * 2


# Titan. Minions to the left of this have Rush, and ones to the right have
# Lifesteal.
# Aura: positional. Implemented as a custom update method via a FuncSelector
# approach — we use `Refresh` per-category inside a custom action.
class _ArgusUpdateAura(TargetedAction):
    """Per-game-tick: grant Rush to all friendlies to Argus's left,
    Lifesteal to all friendlies to Argus's right."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone

        argus = target  # SELF
        if argus.zone != Zone.PLAY or getattr(argus, "dead", False):
            return
        try:
            argus_pos = argus.zone_position
        except Exception:
            return
        ctrl = argus.controller
        for minion in list(ctrl.field):
            if minion is argus:
                continue
            try:
                pos = minion.zone_position
            except Exception:
                continue
            if pos < argus_pos:
                source.game.cheat_action(source, [GiveRush(minion)])
            elif pos > argus_pos:
                source.game.cheat_action(source, [GiveLifesteal(minion)])


class TTN_862:
    """Argus, the Emerald Star"""

    titan_ability_order = ["TTN_862t1", "TTN_862t2", "TTN_862t3"]
    # Positional aura — applied at the start of each turn (approximation).
    # Full continuous aura would need engine changes; approximate with event.
    events = [
        OWN_TURN_BEGIN.on(_ArgusUpdateAura(SELF)),
        OWN_MINION_PLAY.on(_ArgusUpdateAura(SELF)),
    ]


# Crystal Carving — Discover a Deathrattle minion. It costs (3) less.
class _CrystalCarving(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        picker = RandomCollectible(
            card_class=None,
            custom_filter=lambda c: c.tags.get(GameTag.DEATHRATTLE, False),
        )

        def _after_discover(chosen_card):
            if not chosen_card:
                return
            # Apply -3 cost to the chosen card via a custom enchantment.
            source.game.cheat_action(
                source, [Buff(chosen_card, "TTN_862ec")]
            )

        action = Discover(ctrl, picker).then(
            Give(ctrl, Discover.CARD),
            _CrystalCarvingDiscount(ctrl, Discover.CARD),
        )
        source.game.queue_actions(source, [action])


class _CrystalCarvingDiscount(TargetedAction):
    TARGET = ActionArg()
    CHOSEN = ActionArg()

    def do(self, source, target, chosen):
        if isinstance(chosen, list):
            chosen = chosen[0] if chosen else None
        if not chosen:
            return
        # Find the just-given card in the hand (it was given by Discover chain).
        ctrl = target if hasattr(target, "hand") else source.controller
        matches = [c for c in ctrl.hand if c.id == chosen.id]
        if matches:
            source.game.cheat_action(source, [Buff(matches[-1], "TTN_862ec")])


@custom_card
class TTN_862ec:
    tags = {
        GameTag.CARDNAME: "Crystal Carving",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class TTN_862t1:
    """Crystal Carving"""

    play = _CrystalCarving(CONTROLLER)


# Show of Force — Reduce the Cost of all minions in your hand by (2).
class TTN_862t2:
    """Show of Force"""

    play = Buff(FRIENDLY_HAND + MINION, "TTN_862esom")


@custom_card
class TTN_862esom:
    tags = {
        GameTag.CARDNAME: "Show of Force",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


# Argunite Army — Summon four 2/2 Elementals with Taunt.
class TTN_862t3:
    """Argunite Army"""

    play = Summon(CONTROLLER, "TTN_862t4") * 4


class TTN_862t4:
    """Crystal Elemental"""

    tags = {GameTag.TAUNT: True}


# Mythical Terror — Lifesteal. At the end of your turn, force all enemy
# minions to attack this.
class _MythicalTerrorForceAttack(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone

        myth = target  # SELF
        if myth.zone != Zone.PLAY or getattr(myth, "dead", False):
            return
        ctrl = myth.controller
        enemies = list(ctrl.opponent.field)
        for enemy in enemies:
            if getattr(enemy, "dead", False):
                continue
            if myth.zone != Zone.PLAY or getattr(myth, "dead", False):
                break
            source.game.cheat_action(source, [Attack(enemy, myth)])


class TTN_866:
    """Mythical Terror"""

    tags = {GameTag.LIFESTEAL: True}
    events = OWN_TURN_END.on(_MythicalTerrorForceAttack(SELF))


##
# Spells


# Give your hero +4 Attack this turn. Costs (1) less for each card you've
# drawn this turn.
class TTN_841:
    """Momentum"""

    cost_mod = -Attr(CONTROLLER, GameTag.NUM_CARDS_DRAWN_THIS_TURN)
    play = Buff(FRIENDLY_HERO, "TTN_841e1")


# TTN_841e1 "Agile" is in data — grants +4 Attack this turn to the hero.


# Discover a spell that costs (3) or less. Shuffle 2 copies into your deck
# that Cast When Drawn.
class _RunicAdornmentDiscover(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        picker = RandomCollectible(
            card_class=None,
            custom_filter=lambda c: c.type.name == "SPELL" and (c.cost or 0) <= 3,
        )
        action = Discover(ctrl, picker).then(
            _RunicAdornmentShuffle(ctrl, Discover.CARD)
        )
        source.game.queue_actions(source, [action])


class _RunicAdornmentShuffle(TargetedAction):
    TARGET = ActionArg()
    CHOSEN = ActionArg()

    def do(self, source, target, chosen):
        if isinstance(chosen, list):
            chosen = chosen[0] if chosen else None
        if not chosen:
            return
        ctrl = target if hasattr(target, "hand") else source.controller
        # Shuffle 2 copies with Cast When Drawn into the deck.
        for _ in range(2):
            source.game.cheat_action(source, [Give(ctrl, chosen.id)])
            copies = [c for c in ctrl.hand if c.id == chosen.id]
            if copies:
                copy = copies[-1]
                # Stamp Cast When Drawn.
                source.game.cheat_action(source, [Buff(copy, "TTN_845e")])
                source.game.cheat_action(source, [Shuffle(ctrl, copy)])


class TTN_845:
    """Runic Adornment"""

    play = _RunicAdornmentDiscover(CONTROLLER)


# TTN_845e "Jotun's Haste" is in data — marks Cast When Drawn.


# Draw 2 cards. Forge: Draw cards until you have as many in hand as your
# opponent, then draw 2 more.
class TTN_865:
    """Weight of the World"""

    forge_card = "TTN_865t"
    play = Draw(CONTROLLER) * 2


# Forged Weight of the World.
class _ForgedWeightOfTheWorld(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        target_count = len(opp.hand)
        # Draw until we reach opponent's hand size.
        while len(ctrl.hand) < target_count and len(ctrl.hand) < ctrl.max_hand_size:
            before = len(ctrl.hand)
            source.game.cheat_action(source, [Draw(ctrl)])
            if len(ctrl.hand) == before:
                break  # Deck empty or hand full — stop.
        # Then draw 2 more.
        source.game.cheat_action(source, [Draw(ctrl)])
        source.game.cheat_action(source, [Draw(ctrl)])


class TTN_865t:
    """Weight of the World"""

    play = _ForgedWeightOfTheWorld(CONTROLLER)
