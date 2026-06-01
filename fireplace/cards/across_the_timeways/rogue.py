from ..utils import *


##
# Custom actions


class _RoyalInformantPeek(TargetedAction):
    """Royal Informant — Battlecry: Look at the rightmost card in your
    opponent's hand. Either get a copy of it or increase its Cost by (2).

    Offers the controller a two-option choice: a copy of the peeked card, or
    TIME_036t ("Mitigate Threat" — raise that card's Cost by 2). Picking the
    Mitigate token applies the TIME_036e "Costs (2) more" enchant to the
    opponent's card."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        if not opp.hand:
            return
        peeked = opp.hand[-1]  # rightmost
        copy = ctrl.card(peeked.id, source=source)
        mitigate = ctrl.card("TIME_036t", source=source)
        choice = _RoyalInformantChoice(ctrl, [copy, mitigate])
        choice._peeked = peeked
        choice._mitigate = mitigate
        source.game.queue_actions(source, [choice])


class _RoyalInformantChoice(Choice):
    # Base Choice (not GenericChoice): we place the kept card into hand
    # ourselves so the Mitigate-Threat trigger token is never retained.
    def choose(self, card):
        chose_mitigate = card is self._mitigate
        super().choose(card)
        copy = self.cards[0]
        if chose_mitigate:
            # Raise the peeked opponent card's cost; discard both tokens.
            peeked = self._peeked
            if peeked is not None and peeked.zone == Zone.HAND:
                self.source.game.cheat_action(
                    self.source, [Buff(peeked, "TIME_036e")]
                )
            copy.discard()
        else:
            # Keep the copy in hand; the mitigate token is discarded.
            self._mitigate.discard()
            if len(self.player.hand) < self.player.max_hand_size:
                copy.zone = Zone.HAND
            else:
                copy.discard()


class _DejaVuDiscover(TargetedAction):
    """Deja Vu — Discover a copy of a card in your opponent's hand. It costs
    (1) less. The discover pool is the (deduplicated) opponent's hand; the
    chosen copy is given to the controller with the TIME_039e -1 Cost
    enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        hand = list(opp.hand)
        if not hand:
            return
        seen = {}
        for c in hand:
            seen.setdefault(c.id, c)
        pool = list(seen.values())[:3]
        cards = [ctrl.card(c.id, source=source) for c in pool]
        choice = _DejaVuChoice(ctrl, cards)
        source.game.queue_actions(source, [choice])


class _DejaVuChoice(GenericChoice):
    def choose(self, card):
        super().choose(card)
        if card.zone == Zone.HAND:
            self.source.game.cheat_action(
                self.source, [Buff(card, "TIME_039e")]
            )


class _FlashbackSummon(TargetedAction):
    """Flashback — Summon two random 1-Cost minions from the past. Combo: With
    +1 Attack. When the combo is active the two summoned minions each gain +1
    Attack (TIME_711e)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        combo = ctrl.combo and getattr(source, "has_combo", False)
        for _ in range(2):
            before = set(ctrl.field)
            source.game.cheat_action(source, [Summon(ctrl, RandomMinion(cost=1))])
            new = [m for m in ctrl.field if m not in before]
            if combo:
                for m in new:
                    source.buff(m, "TIME_711e")


class _ShapeshifterMorph(TargetedAction):
    """Shapeshifter — each of your turns while this is in hand, transform into
    a copy of a random minion in your opponent's hand. We morph into a fresh
    card created from the picked minion's id (not the opponent's actual entity,
    which would steal it out of their hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        minions = [c for c in opp.hand if c.type == CardType.MINION]
        if not minions:
            return
        chosen = source.game.random.choice(minions)
        source.game.cheat_action(source, [Morph(target, chosen.id)])


class _GaronaBattlecry(TargetedAction):
    """Garona Halforcen — Battlecry: If your opponent is holding King Llane
    (TIME_875t), destroy him and cut their Health in half (rounded up)."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        llane = next((c for c in opp.hand if c.id == "TIME_875t"), None)
        if llane is None:
            return
        source.game.cheat_action(source, [Destroy(llane)])
        hero = opp.hero
        new_health = (hero.health + 1) // 2  # half, rounded up
        source.game.cheat_action(source, [SetCurrentHealth(hero, new_health)])


class _TimelessChestDeathrattle(TargetedAction):
    """Timeless Chest — Deathrattle: Fill your opponent's hand with Coins. The
    Chest is summoned for the enemy, so from the Chest's perspective "your
    opponent" is the original Hooktail caster."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        while len(opp.hand) < opp.max_hand_size:
            source.game.cheat_action(source, [Give(opp, THE_COIN)])


class _FastForwardPick(TargetedAction):
    """Fast Forward — Draw 2 cards. Pick one to have its Cost reduced by (2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        drawn = []
        for _ in range(2):
            before = set(ctrl.hand)
            source.game.cheat_action(source, [Draw(ctrl)])
            drawn.extend(c for c in ctrl.hand if c not in before)
        drawn = [c for c in drawn if c.zone == Zone.HAND]
        if not drawn:
            return
        if len(drawn) == 1:
            source.game.cheat_action(source, [Buff(drawn[0], "TIME_770e")])
            return
        source.game.queue_actions(source, [_FastForwardChoice(ctrl, drawn)])


class _FastForwardChoice(Choice):
    def choose(self, card):
        super().choose(card)
        if card.zone == Zone.HAND:
            self.source.game.cheat_action(
                self.source, [Buff(card, "TIME_770e")]
            )


##
# Collectible cards


class TIME_001:
    "Chrono Daggers"
    # Rewind Throw 3 knives at random enemies that deal 2 damage each.
    # (Rewind is engine-handled — only the base effect is scripted.)
    play = Hit(RANDOM_ENEMY_CHARACTER, 2) * 3


class TIME_036:
    "Royal Informant"
    # Battlecry: Look at the rightmost card in your opponent's hand. Either get
    # a copy of it or increase its Cost by (2).
    play = _RoyalInformantPeek(CONTROLLER)


class TIME_039:
    "Deja Vu"
    # Discover a copy of a card in your opponent's hand. It costs (1) less.
    play = _DejaVuDiscover(CONTROLLER)


class TIME_710:
    "Troubled Double"
    # Stealth (data). Combo: Summon a copy of this.
    combo = Summon(CONTROLLER, ExactCopy(SELF))


class TIME_711:
    "Flashback"
    # Summon two random 1-Cost minions from the past. Combo: With +1 Attack.
    # When combo is active the engine runs `combo` INSTEAD of `play`, so the
    # combo-aware _FlashbackSummon is wired to both (it self-detects combo and
    # applies the +1 Attack buff).
    play = _FlashbackSummon(CONTROLLER)
    combo = _FlashbackSummon(CONTROLLER)


class TIME_712:
    "Dethrone"
    # Destroy a minion. Combo: Summon a random 8-Cost minion. (Engine runs
    # `combo` instead of `play` when combo is active, so combo includes the
    # base Destroy plus the 8-Cost summon.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Destroy(TARGET)
    combo = Destroy(TARGET), Summon(CONTROLLER, RandomMinion(cost=8))


class TIME_713:
    "Time Adm'ral Hooktail"
    # Battlecry: Summon a 0/8 Chest for your opponent. It's FULL of Coins!
    play = Summon(OPPONENT, "TIME_713t")


class TIME_770:
    "Fast Forward"
    # Draw 2 cards. Pick one to have its Cost reduced by (2).
    play = _FastForwardPick(CONTROLLER)


class TIME_875:
    "Garona Halforcen"
    # Fabled. Battlecry: If your opponent is holding King Llane, destroy him
    # and cut their Health in half.
    play = _GaronaBattlecry(CONTROLLER)


class TIME_876:
    "Shapeshifter"
    # Each turn this is in your hand, transform into a random minion in your
    # opponent's hand.
    class Hand:
        events = OWN_TURN_BEGIN.on(_ShapeshifterMorph(SELF))


##
# Tokens


class TIME_713t:
    "Timeless Chest"
    # Deathrattle: Fill your opponent's hand with Coins.
    deathrattle = _TimelessChestDeathrattle(CONTROLLER)


class TIME_875t:
    "King Llane"
    # Start of Game: Hide from Garona in the enemy's deck. (Bundle / start-of-
    # game shuffling is data-driven and not modeled here.) Battlecry: Draw a
    # card. Shuffle this back into your deck.
    play = Draw(CONTROLLER), Shuffle(CONTROLLER, SELF)


class TIME_875t1:
    "The Kingslayers"
    # After your hero attacks, both players draw a Legendary card.
    events = Attack(FRIENDLY_HERO).after(
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + LEGENDARY)),
        Draw(OPPONENT, RANDOM(ENEMY_DECK + LEGENDARY)),
    )


##
# Enchantments


class TIME_036e:
    "Threat Mitigation"
    # Costs (2) more.
    tags = {GameTag.COST: 2}


class TIME_036t:
    "Mitigate Threat"
    # Increase the Cost of your opponent's card by (2). (Effect applied by
    # _RoyalInformantChoice when this token is chosen.)


@custom_card
class TIME_039e:
    # Deja Vu — the discovered copy costs (1) less. (Not in card data.)
    tags = {
        GameTag.CARDNAME: "Deja Vu",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class TIME_711e:
    "Memories"
    # +1 Attack.
    tags = {GameTag.ATK: 1}


@custom_card
class TIME_770e:
    # Fast Forward — picked drawn card costs (2) less. (Not in card data.)
    tags = {
        GameTag.CARDNAME: "Fast Forward",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class TIME_876e:
    "Shapeshifting"
    # Transforming into a random minion in your opponent's hand.


##
# Across the Timeways mini-set (END_) — End Time
#
# Custom actions


class _EventualityImbue(TargetedAction):
    """Eventuality (END_000) — Imbue your Hero Power.

    The base spell deals 2 damage (handled by Hit on END_000.play) and then
    imbues the controller's Hero Power once. Rogue's Imbued Hero Power is
    END_000p "Blessing of the Bronze" (engine-mapped in actions.IMBUED_HERO_POWERS).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Imbue(source.controller)])


class _BlessingOfTheBronze(TargetedAction):
    """Blessing of the Bronze (END_000p) — Get a random minion from another
    class. It costs (@) less, where @ scales with the imbue level
    (level 1 = (1) less, level 2 = (2) less, ...).

    Pool is collectible minions whose class is neither the controller's class
    nor Neutral ("from another class")."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        level = max(1, getattr(source, "imbue_level", 1))
        own_classes = set(ctrl.hero.classes) or {ctrl.hero.card_class}
        pool = [
            cid for cid, c in db.items()
            if (
                c.type == CardType.MINION
                and c.collectible
                and c.card_class not in own_classes
                and c.card_class != CardClass.NEUTRAL
            )
        ]
        if not pool:
            return
        chosen = source.game.random.choice(pool)
        card = ctrl.card(chosen, source=source)
        source.game.cheat_action(
            source, [Give(ctrl, card).then(Buff(Give.CARD, "END_000e", cost=-level))]
        )


##
# Collectible cards


class END_000:
    "Eventuality"
    # Deal $2 damage. Imbue your Hero Power.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2), _EventualityImbue(CONTROLLER)


##
# Imbued Hero Power token


class END_000p:
    "Blessing of the Bronze"
    # Rewind: Get a random minion from another class. It costs (@) less.
    #
    # NOTE: the printed Hero Power carries the Rewind keyword (re-run once).
    # Hero-power activation does not flow through Play.do's Rewind hook, so the
    # re-run is not modelled here; we faithfully implement the underlying
    # effect (a random off-class minion with a scaling cost reduction). The
    # cost reduction scales with the imbue level (set by Imbue at install
    # time and refreshed on every subsequent imbue).
    activate = _BlessingOfTheBronze(CONTROLLER)


##
# Enchantments


class END_000e:
    """Dimensionally Shifted"""

    # Reduced Cost (data enchant). Amount set dynamically by
    # Buff(cost=-level) at activate time.
