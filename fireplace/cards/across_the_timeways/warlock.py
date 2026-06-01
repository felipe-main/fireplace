from ..utils import *


##
# Rafaam family helpers
#
# The ten "Rafaam" minions that make up Timethief Rafaam's deck. Baaaafam
# (TIME_005t9t) is a Sheep token and is explicitly NOT a Rafaam.
RAFAAM_IDS = [
    "TIME_005",     # Timethief Rafaam
    "TIME_005t1",   # Tiny Rafaam
    "TIME_005t2",   # Green Rafaam
    "TIME_005t3",   # Explorer Rafaam
    "TIME_005t4",   # Warchief Rafaam
    "TIME_005t5",   # Mindflayer R'faam
    "TIME_005t6",   # Calamitous Rafaam
    "TIME_005t7",   # Giant Rafaam
    "TIME_005t8",   # Murloc Rafaam
    "TIME_005t9",   # Archmage Rafaam
]
RAFAAM = IDS(RAFAAM_IDS)
# The nine OTHER Rafaams that Timethief checks for "if you played the rest".
OTHER_RAFAAM_IDS = [i for i in RAFAAM_IDS if i != "TIME_005"]


class _TimethiefDestroy(TargetedAction):
    """Timethief Rafaam — destroy the enemy hero only if every OTHER Rafaam
    has been played this game (the "if you played the rest" clause)."""

    TARGET = ActionArg()

    def do(self, source, target):
        played = {c.id for c in source.controller.cards_played_this_game}
        if all(i in played for i in OTHER_RAFAAM_IDS):
            source.game.cheat_action(source, [Destroy(ENEMY_HERO)])


class TIME_005:
    "Timethief Rafaam"
    # Fabled+. Your deck size is 40, but has 10 Rafaams! Battlecry: If you
    # played the rest, destroy the enemy hero.
    play = _TimethiefDestroy(CONTROLLER)


class TIME_005t1:
    "Tiny Rafaam"
    # Deathrattle: Draw a Rafaam.
    deathrattle = ForceDraw(RANDOM(FRIENDLY_DECK + RAFAAM))


class TIME_005t2:
    "Green Rafaam"
    # Battlecry: Give Rafaams in your hand +2/+2.
    play = Buff(FRIENDLY_HAND + RAFAAM, "TIME_005t2e")


TIME_005t2e = buff(+2, +2)


class _ExplorerDiscover(TargetedAction):
    """Explorer Rafaam — Discover a Rafaam from your deck (gives a copy to
    hand). No-op if the deck has no Rafaams."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ids = list({c.id for c in ctrl.deck if c.id in RAFAAM_IDS})
        if not ids:
            return
        source.game.cheat_action(
            source,
            [Discover(CONTROLLER, RandomID(*ids)).then(Give(CONTROLLER, Discover.CARD))],
        )


class TIME_005t3:
    "Explorer Rafaam"
    # Battlecry: Discover a Rafaam from your deck.
    play = _ExplorerDiscover(CONTROLLER)


class TIME_005t4:
    "Warchief Rafaam"
    # Battlecry: Gain 5 Armor. If you control another Rafaam, gain 5 more.
    play = (
        GainArmor(FRIENDLY_HERO, 5),
        Find(FRIENDLY_MINIONS + RAFAAM - SELF) & GainArmor(FRIENDLY_HERO, 5),
    )


class TIME_005t5:
    "Mindflayer R'faam"
    # Taunt. Battlecry: If you're holding another Rafaam, summon a copy of this.
    play = Find(FRIENDLY_HAND + RAFAAM - SELF) & Summon(CONTROLLER, ExactCopy(SELF))


class TIME_005t6:
    "Calamitous Rafaam"
    # Battlecry: Deal 6 damage to all minions that aren't Rafaam.
    play = Hit(ALL_MINIONS - RAFAAM, 6)


class TIME_005t7:
    "Giant Rafaam"
    # Rush. Costs (1) less for each Rafaam you've played this game.
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME + RAFAAM)


class _StampRafaamCreator(TargetedAction):
    """Record which Rafaam created the discount enchant so its own Play does
    not immediately consume the discount."""

    TARGET = ActionArg()
    BUFF = CardArg()

    def do(self, source, target, buff):
        buff.creator = source


class TIME_005t8:
    "Murloc Rafaam"
    # Battlecry: The next Rafaam you play costs (3) less.
    play = Buff(CONTROLLER, "TIME_005t8e").then(_StampRafaamCreator(SELF, Buff.BUFF))


class _ConsumeRafaamCost(TargetedAction):
    """Murloc Rafaam cost rider: spend the discount when a Rafaam OTHER than
    the enchant's creator (Murloc Rafaam itself) is played."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, played):
        if played is getattr(source, "creator", None):
            return
        source.game.cheat_action(source, [Destroy(source)])


class TIME_005t8e:
    # Your next Rafaam costs (3) less.
    update = Refresh(FRIENDLY_HAND + RAFAAM, {GameTag.COST: -3})
    events = Play(CONTROLLER, RAFAAM).after(_ConsumeRafaamCost(SELF, Play.CARD))


class TIME_005t9:
    "Archmage Rafaam"
    # Battlecry: Transform all minions that aren't Rafaam into 1/1 Sheep.
    play = Morph(ALL_MINIONS - RAFAAM, "TIME_005t9t")


class TIME_005t9t:
    "Baaaafam"
    # Vanilla 1/1 Beast.


##
# Standalone collectibles


class TIME_008:
    "Bygone Doomspeaker"
    # Rewind Battlecry: Both players discard a random card.
    play = (
        Discard(RANDOM(FRIENDLY_HAND)),
        Discard(RANDOM(ENEMY_HAND)),
    )


class TIME_025:
    "Twilight Timehopper"
    # Battlecry: Shuffle 2 Shreds of Time into your deck. When drawn, deal 3
    # damage to your hero.
    play = Shuffle(CONTROLLER, "TIME_025t") * 2


class TIME_025t:
    "Shred of Time"
    # Casts When Drawn: Deal 3 damage to your hero.
    play = Hit(FRIENDLY_HERO, 3)


class TIME_026:
    "Entropic Continuity"
    # Give your minions +1/+1. Shuffle 2 Shreds of Time into your deck.
    play = (
        Buff(FRIENDLY_MINIONS, "TIME_026e"),
        Shuffle(CONTROLLER, "TIME_025t") * 2,
    )


TIME_026e = buff(+1, +1)


class TIME_027:
    "Tachyon Barrage"
    # Deal 6 damage split among all enemies. Shuffle 2 Shreds of Time into your
    # deck.
    play = (
        Hit(RANDOM(ENEMY_CHARACTERS), 1) * 6,
        Shuffle(CONTROLLER, "TIME_025t") * 2,
    )


class TIME_028:
    "Fatebreaker"
    # Lifesteal Battlecry: Cast a Shred of Time from your deck to gain +3/+3.
    play = Find(FRIENDLY_DECK + ID("TIME_025t")) & (
        CastSpell(RANDOM(FRIENDLY_DECK + ID("TIME_025t"))),
        Buff(SELF, "TIME_028e"),
    )


TIME_028e = buff(+3, +3)


class TIME_029:
    "Ruinous Velocidrake"
    # Rush Battlecry: Cast a Shred of Time from your deck to summon a copy of
    # this.
    play = Find(FRIENDLY_DECK + ID("TIME_025t")) & (
        CastSpell(RANDOM(FRIENDLY_DECK + ID("TIME_025t"))),
        Summon(CONTROLLER, ExactCopy(SELF)),
    )


class _DivergenceSplit(TargetedAction):
    """Divergence — pick a random minion in hand, replace it with two copies
    whose Cost and stats are each halved (rounded up, per the live card)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        minions = [c for c in ctrl.hand if c.type == CardType.MINION]
        if not minions:
            return
        original = source.game.random.choice(minions)
        base_atk = original.atk
        base_health = original.max_health
        base_cost = original.cost
        # Half, rounded up.
        half_atk = (base_atk + 1) // 2
        half_health = (base_health + 1) // 2
        half_cost = (base_cost + 1) // 2
        d_atk = half_atk - base_atk
        d_health = half_health - base_health
        d_cost = half_cost - base_cost
        original.zone = Zone.SETASIDE
        for _ in range(2):
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            copy = ctrl.card(original.id, source=source)
            copy.zone = Zone.HAND
            source.game.queue_actions(
                source,
                [
                    Buff(copy, "TIME_030e2", atk=d_atk, max_health=d_health),
                    Buff(copy, "TIME_030e1", cost=d_cost),
                ],
            )


class TIME_030:
    "Divergence"
    # Split a random minion in your hand into two halves.
    play = _DivergenceSplit(CONTROLLER)


class TIME_030e1:
    "Divergent"
    # Cost split in half (delta supplied dynamically by _DivergenceSplit).


class TIME_030e2:
    "Diverged"
    # Attack and Health split in half (delta supplied dynamically).


class _RafaamLadderDraw(TargetedAction):
    """RAFAAM LADDER!! — draw 3 cards of different Costs (no two share a Cost)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen_costs = set()
        drawn = 0
        # Snapshot the deck order (top = deck[-1]) and pick distinct-cost cards.
        for card in reversed(list(ctrl.deck)):
            if drawn >= 3:
                break
            if card.cost in seen_costs:
                continue
            seen_costs.add(card.cost)
            source.game.cheat_action(source, [ForceDraw(card)])
            drawn += 1


class TIME_031:
    "RAFAAM LADDER!!"
    # Draw 3 cards of different Costs.
    play = _RafaamLadderDraw(CONTROLLER)


class _ChronogorDraw(TargetedAction):
    """Chronogor — you draw your 2 highest-Cost cards; your opponent draws
    your 2 lowest-Cost cards (moved from your deck into their hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        deck = sorted(list(ctrl.deck), key=lambda c: c.cost)
        # 2 lowest -> opponent, 2 highest -> you. Resolve disjoint slices so a
        # tiny deck never double-counts a card.
        lowest = deck[:2]
        highest = [c for c in deck[::-1] if c not in lowest][:2]
        for card in highest:
            source.game.cheat_action(source, [ForceDraw(card)])
        for card in lowest:
            if card.zone != Zone.DECK:
                continue
            if len(opp.hand) >= opp.max_hand_size:
                card.discard()
                continue
            # Move cross-controller via SETASIDE: removing from p1.deck while
            # the card still belongs to p1, then re-home it to the opponent's
            # hand. (Switching controller before leaving the deck would make
            # _set_zone try to remove it from the opponent's deck and crash.)
            card.zone = Zone.SETASIDE
            card.controller = opp
            card.zone = Zone.HAND


class TIME_032:
    "Chronogor"
    # Battlecry: You draw your 2 highest Cost cards. Your opponent draws your 2
    # lowest Cost cards.
    play = _ChronogorDraw(CONTROLLER)


##
# Across the Timeways mini-set (END_, CardSet TIME_TRAVEL)


class _AcolyteSetInfinity(TargetedAction):
    """Acolyte of Infinity battlecry — set a random card in the controller's
    hand to INFINITY Cost (END_018e) and remember which card was buffed so the
    deathrattle can change it back."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        hand = list(ctrl.hand)
        if not hand:
            return
        chosen = source.game.random.choice(hand)
        source._infinity_target = chosen
        source.game.queue_actions(source, [Buff(chosen, "END_018e")])


class _AcolyteRestore(TargetedAction):
    """Acolyte of Infinity deathrattle — strip the INFINITY-Cost enchant from
    the card it was placed on and tag it with the cosmetic "returned to normal"
    enchant (END_018e2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        victim = getattr(source, "_infinity_target", None)
        if victim is None:
            return
        removed = False
        for b in list(victim.buffs):
            if b.id == "END_018e":
                # Enchantments are removed via remove(), not destroy() (which is
                # a minion/weapon method) — calling destroy() here crashes.
                b.remove()
                removed = True
        if removed and victim.zone == Zone.HAND:
            source.game.queue_actions(source, [Buff(victim, "END_018e2")])


class END_018:
    "Acolyte of Infinity"
    # Battlecry: Set the Cost of a random card in your hand to INFINITY!
    # Deathrattle: Change it back.
    play = _AcolyteSetInfinity(SELF)
    deathrattle = _AcolyteRestore(SELF)


class END_018e:
    "Infinite Delay"
    # Cost set to INFINITY!
    cost = SET(2147483647)


class END_018e2:
    "Preserved Essence"
    # Cost returned to normal. (Cosmetic marker — removing END_018e already
    # restores the printed Cost.)
    pass
