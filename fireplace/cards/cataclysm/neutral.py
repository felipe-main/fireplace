from ..utils import *


##
# Minions


class CATA_111:
    "Darkscale Broodmother"
    # Battlecry: If you're holding a Dragon, refresh 2 Mana Crystals.
    play = HOLDING_DRAGON & FillMana(CONTROLLER, 2)


class _WarlocCostHealth(TargetedAction):
    """War'loc — arm "your next Murloc that costs (3) or less costs Health
    instead of Mana": a per-player one-shot flag consumed in pay_cost when the
    next qualifying Murloc is played (whenever it is drawn). No time limit."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.next_cheap_murloc_costs_health = True


class CATA_180:
    "War'loc"
    # Battlecry: Your next Murloc that costs (3) or less costs Health
    # instead of Mana.
    play = _WarlocCostHealth(SELF)


class CATA_180e:
    "Doom!"
    # Costs Health instead of Mana. (Cosmetic marker; the cost substitution is
    # driven by the controller's next_cheap_murloc_costs_health flag.)


class _FacelessReplicatorDeathrattle(TargetedAction):
    """Faceless Replicator — Elusive Deathrattle: transform the minion that
    killed this into a Faceless Replicator. The killer's id is stamped on the
    target by Damage.do (``_last_damage_source_id``); we locate the live
    entity in play and Morph it."""

    TARGET = ActionArg()

    def do(self, source, target):
        killer_id = getattr(target, "_last_damage_source_id", None)
        if not killer_id:
            return
        killer = None
        for player in source.game.players:
            for m in player.field:
                if getattr(m, "id", None) == killer_id:
                    killer = m
                    break
            if killer:
                break
        if killer is None:
            return
        source.game.cheat_action(source, [Morph(killer, "CATA_185")])


class CATA_185:
    "Faceless Replicator"
    # Elusive Deathrattle: Transform the minion that killed this into a
    # Faceless Replicator.
    deathrattle = _FacelessReplicatorDeathrattle(SELF)


class CATA_186:
    "Stickybomb Saboteur"
    # Battlecry: Give your opponent a 2-Cost Sabotage. Cards next to it in hand
    # cost (1) more (live hand-adjacency aura on the Sabotage token).
    play = Give(OPPONENT, "CATA_186t")


def _sabotage_hand_neighbors(entities, source):
    """The cards immediately left and right of `source` in its owner's hand."""
    hand = source.controller.hand
    if source not in hand:
        return []
    i = hand.index(source)
    return [hand[j] for j in (i - 1, i + 1) if 0 <= j < len(hand)]


_SABOTAGE_NEIGHBORS = FuncSelector(_sabotage_hand_neighbors)


class CATA_186t:
    "Sabotage!"
    # Cards adjacent to this in hand cost (1) more — a live hand-position aura
    # refreshed every tick (Hand.update): whichever cards currently sit
    # immediately left/right of the Sabotage get +1 Cost, and the buff is
    # auto-removed the moment they stop being adjacent (hand shuffles / plays).
    class Hand:
        update = Refresh(_SABOTAGE_NEIGHBORS, {GameTag.COST: 1})


class CATA_186te:
    "Sabotaged"
    # Costs (1) more. (Unused now that the aura applies an inline COST buff;
    # kept as the data enchant declaration.)
    tags = {GameTag.COST: 1}


# Twisted Monstrosity's "Bonus Effects" pool (per hearthstone.wiki.gg): the
# eight grantable keywords. Elusive is a live boolean_property, not a GameTag,
# so it is applied separately.
_TWISTED_TAG_KEYWORDS = {
    "DIVINE_SHIELD": GameTag.DIVINE_SHIELD,
    "LIFESTEAL": GameTag.LIFESTEAL,
    "POISONOUS": GameTag.POISONOUS,
    "REBORN": GameTag.REBORN,
    "RUSH": GameTag.RUSH,
    "TAUNT": GameTag.TAUNT,
    "WINDFURY": GameTag.WINDFURY,
}
_TWISTED_POOL = list(_TWISTED_TAG_KEYWORDS) + ["ELUSIVE"]


class _TwistedMonstrositySwap(TargetedAction):
    """Twisted Monstrosity — each turn in hand, swap its two Bonus-Effect
    keywords for two new random ones from the eight-keyword pool (Divine Shield,
    Elusive, Lifesteal, Poisonous, Reborn, Rush, Taunt, Windfury). It starts
    with Taunt + Elusive (its data keywords); each tick re-rolls two distinct
    keywords (which may repeat across turns)."""

    TARGET = ActionArg()

    def do(self, source, target):
        new = tuple(source.game.random.sample(_TWISTED_POOL, 2))
        # Set every pool tag-keyword on/off in one pass so the previous pair is
        # cleared and the new pair applied; Elusive rides its own property.
        tagvals = {gt: (name in new) for name, gt in _TWISTED_TAG_KEYWORDS.items()}
        source.game.cheat_action(source, [SetTags(target, tagvals)])
        target.elusive = "ELUSIVE" in new
        target._twisted_keywords = new


class CATA_206:
    "Twisted Monstrosity"
    # Taunt, Elusive. Each turn this is in your hand, swap between two random
    # Bonus Effects (the 8-keyword pool).
    class Hand:
        events = OWN_TURN_BEGIN.on(_TwistedMonstrositySwap(SELF))


class CATA_206t:
    "Twisted Monstrosity"
    # Token copy — same body.
    class Hand:
        events = OWN_TURN_BEGIN.on(_TwistedMonstrositySwap(SELF))


class CATA_208:
    "Selfless Protector"
    # Taunt. Takes one extra damage from all sources.
    # INCOMING_DAMAGE_ADJUSTMENT is honoured by Damage.do (amount += adj).
    update = Refresh(SELF, {GameTag.INCOMING_DAMAGE_ADJUSTMENT: 1})


class _BattlefieldBlaster(TargetedAction):
    """Battlecry: Choose a spell in your hand to give Spell Damage +1."""

    TARGET = ActionArg()

    def do(self, source, target):
        choose_hand_card(
            source,
            lambda s, c: s.game.cheat_action(s, [Buff(c, "CATA_209e")]),
            filter=lambda c: c.type == CardType.SPELL,
        )


class CATA_209:
    "Battlefield Blaster"
    # Battlecry: Choose a spell in your hand to give Spell Damage +1.
    play = _BattlefieldBlaster(SELF)


class CATA_209e:
    "Battlefield Channeler Spellpower"
    # Spell Damage +1. (Carried by the cast spell via spell._getattr.)
    tags = {GameTag.SPELLPOWER: 1}


class CATA_210:
    "Twilight Egg"
    # Deathrattle: Summon a Whelp that gains +1/+1 at the start of your turns.
    deathrattle = Summon(CONTROLLER, "CATA_210t")


class CATA_210t:
    "Accelerated Whelp"
    # Gains +1/+1 at the start of your turns.
    events = OWN_TURN_BEGIN.on(Buff(SELF, "CATA_210te"))


@custom_card
class CATA_210te:
    "Accelerated"
    tags = {
        GameTag.CARDNAME: "Accelerated",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
    }


class _VyranothSplit(TargetedAction):
    """Vyranoth — if the total Cost of your starting minions was 100, split
    100 stats among minions in your deck. We check the actual starting deck's
    minion-cost sum; on match, distribute 100 total stat points (alternating
    +Attack / +Health) randomly across minions remaining in the deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        starting = getattr(ctrl, "starting_deck", None) or []
        minion_cost = sum(
            (c.cost or 0)
            for c in starting
            if getattr(c, "type", None) == CardType.MINION
        )
        if minion_cost != 100:
            return
        deck_minions = [c for c in ctrl.deck if c.type == CardType.MINION]
        if not deck_minions:
            return
        for i in range(100):
            pick = source.game.random.choice(deck_minions)
            enchant = "CATA_213e" if i % 2 == 0 else "CATA_213e2"
            source.game.cheat_action(source, [Buff(pick, enchant)])


class CATA_213:
    "Vyranoth"
    # Battlecry: If the total Cost of your starting minions was 100, split
    # 100 stats among minions in your deck.
    play = _VyranothSplit(SELF)


class CATA_213e:
    "Stormcharged"
    # Increased Attack.
    tags = {GameTag.ATK: 1}


class CATA_213e2:
    "Stormcharged"
    # Increased Health.
    tags = {GameTag.HEALTH: 1}


class CATA_476:
    "Bronze Keeper"
    # At the end of your turn, summon a 6/6 Elemental Dragon with Divine Shield.
    events = OWN_TURN_END.on(Summon(CONTROLLER, "CATA_476t"))


class CATA_476t:
    "Sandscale Dragon"
    # Divine Shield. (Carried by data tags — vanilla 6/6.)


class _UltraxionHerald(TargetedAction):
    """Ultraxion — Herald, then reduce Deathwing's Cost by (heralds_this_game).
    Banks the reduction on a per-player accumulator
    (Player.deathwing_cost_reduction) instead of stamping the in-hand copy, so a
    Deathwing (CATA_190h) drawn AFTER the reduction still benefits (Deathwing's
    cost_mod reads the accumulator)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl.heralds_this_game += 1
        ctrl.deathwing_cost_reduction += ctrl.heralds_this_game


class _DeathwingDiscount(LazyNum):
    """Ultraxion's banked Deathwing cost reduction for the holder's controller."""

    def evaluate(self, source):
        return self.num(getattr(source.controller, "deathwing_cost_reduction", 0))


class CATA_497:
    "Ultraxion"
    # Battlecry: Herald {0}. Reduce Deathwing's Cost by ({1}).
    play = _UltraxionHerald(SELF)


class CATA_497e:
    "Ultraxion Heralded"
    # Reduced Cost.
    tags = {GameTag.COST: -1}


class CATA_556:
    "Carrier Whelp"
    # Battlecry: Get a random Dragon that costs (3) or less.
    play = Give(
        CONTROLLER, RandomDragon(custom_filter=lambda c: (c.cost or 0) <= 3)
    )


class CATA_612:
    "Frostbitten Imp"
    # Battlecry: Freeze this.
    play = Freeze(SELF)


class CATA_613:
    "Survivalist"
    # Has Immune while you control no other minions.
    update = (Count(FRIENDLY_MINIONS - SELF) == 0) & Refresh(
        SELF, {GameTag.IMMUNE: True}
    )


class _ShadowedInformantDiscover(TargetedAction):
    """Shadowed Informant — Discover a spell from a class that swaps each turn.
    Neutral minion, so we rotate the discover class by the controller's turn
    count to emulate the "swaps class each turn" gimmick."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        classes = [
            CardClass.DEMONHUNTER,
            CardClass.DRUID,
            CardClass.HUNTER,
            CardClass.MAGE,
            CardClass.PALADIN,
            CardClass.PRIEST,
            CardClass.ROGUE,
            CardClass.SHAMAN,
            CardClass.WARLOCK,
            CardClass.WARRIOR,
        ]
        idx = len(getattr(ctrl, "turns", [])) % len(classes)
        cls = classes[idx]
        source.game.queue_actions(
            source,
            [
                Discover(ctrl, RandomSpell(card_class=cls)).then(
                    Give(ctrl, Discover.CARD)
                )
            ],
        )


class CATA_614:
    "Shadowed Informant"
    # Battlecry: Discover a spell from your class. (Swaps class each turn!)
    play = _ShadowedInformantDiscover(SELF)


class _GennCursedTransform(TargetedAction):
    """Genn, Cursed King — while holding this, if the rest of your hand is all
    even or all odd Cost, transform into Genn, Worgen King. Checked each of the
    controller's turns while in hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        rest = [c for c in ctrl.hand if c is not target]
        if not rest:
            return
        costs = [c.cost or 0 for c in rest]
        all_even = all(x % 2 == 0 for x in costs)
        all_odd = all(x % 2 == 1 for x in costs)
        if all_even or all_odd:
            source.game.cheat_action(source, [Morph(target, "CATA_615t")])


class CATA_615:
    "Genn, Cursed King"
    # While holding this, if the rest of your hand is all even or all odd,
    # transform into the Worgen King.
    class Hand:
        events = OWN_TURN_BEGIN.on(_GennCursedTransform(SELF))


class CATA_615e:
    "The Moooon"
    # Your Hero Power costs (1). (SET() must be a class attr, not in a tags
    # dict — SET() inside buff tags crashes.)
    cost = SET(1)


class CATA_615t:
    "Genn, Worgen King"
    # Battlecry: Upgrade your starting Hero Power. It costs (1).
    play = UPGRADE_HERO_POWER, Buff(FRIENDLY_HERO_POWER, "CATA_615e")


class _GronnGiantCost(LazyNum):
    """Gronn Giant — Cost reduced by the Cost of the last card you played."""

    def evaluate(self, source):
        last = getattr(source.controller, "last_card_played", None)
        value = (last.cost if last is not None else 0) or 0
        return self.num(value)


class CATA_616:
    "Gronn Giant"
    # This minion's Cost is reduced by the Cost of the last card you played.
    cost_mod = -_GronnGiantCost()


class _BlackhornDestroyCheapDeckCards(TargetedAction):
    """Warmaster Blackhorn — destroy all cards costing (2) or less in both
    players' decks."""

    TARGET = ActionArg()

    def do(self, source, target):
        for player in source.game.players:
            for card in list(player.deck):
                if (card.cost or 0) <= 2:
                    card.zone = Zone.GRAVEYARD


class CATA_720:
    "Warmaster Blackhorn"
    # Battlecry: Destroy all cards that cost (2) or less in both players' decks.
    play = _BlackhornDestroyCheapDeckCards(SELF)


class _ShelteredSurvivorShuffle(TargetedAction):
    """Sheltered Survivor — Battlecry: choose a card in hand to shuffle into
    your deck, then draw a card. The draw is unconditional (it still happens if
    no other card is in hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if any(c is not source for c in ctrl.hand):
            choose_hand_card(
                source,
                lambda s, c: s.game.cheat_action(
                    s, [Shuffle(ctrl, c), Draw(ctrl)]
                ),
            )
        else:
            source.game.cheat_action(source, [Draw(ctrl)])


class CATA_721:
    "Sheltered Survivor"
    # Battlecry: Choose a card in your hand to shuffle into your deck. Draw a
    # card.
    play = _ShelteredSurvivorShuffle(SELF)


class CATA_722:
    "Envoy of the End"
    # Taunt. Battlecry: Herald {0}.
    play = Herald(CONTROLLER)


class CATA_723:
    "Drakeadon Mongrel"
    # Deathrattle: Summon two random 4-Cost minions.
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=4)) * 2


class _GemstoneHoarderDiscard(TargetedAction):
    """Gemstone Hoarder — Battlecry: choose a card in hand to discard;
    deathrattle gets it back at (1) less (remember its id on the minion)."""

    TARGET = ActionArg()

    def _absorb(self, source, chosen):
        source._hoarded_id = chosen.id
        source.game.cheat_action(source, [Discard(chosen)])

    def do(self, source, target):
        choose_hand_card(source, self._absorb)


class _GemstoneHoarderReturn(TargetedAction):
    """Gemstone Hoarder deathrattle — get back the discarded card at (1) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        stored = getattr(source, "_hoarded_id", None)
        if not stored:
            return
        source.game.cheat_action(
            source, [Give(source.controller, stored).then(Buff(Give.CARD, "CATA_897e3"))]
        )


class CATA_897:
    "Gemstone Hoarder"
    # Battlecry: Choose a card in your hand to discard. Deathrattle: Get it
    # back. It costs (1) less.
    play = _GemstoneHoarderDiscard(SELF)
    deathrattle = _GemstoneHoarderReturn(SELF)


class CATA_897e3:
    "Hoarded Gemstone"
    # Discarded {0}. (Costs (1) less.)
    tags = {GameTag.COST: -1}


class CATA_898:
    "Scaled Lancer"
    # All enemy minions have Taunt.
    update = Refresh(ENEMY_MINIONS, {GameTag.TAUNT: True})


class CATA_898e:
    "Scalebound"
    # Scaled Lancer grants Taunt.
    tags = {GameTag.TAUNT: True}


class CATA_999:
    "Earthen Drake"
    # At the end of your turn, deal 4 damage to the enemy hero.
    events = OWN_TURN_END.on(Hit(ENEMY_HERO, 4))


##
# Deathwing, Worldbreaker (HERO) + Cataclysm tokens


class _DeathwingUnleash(TargetedAction):
    """Deathwing, Worldbreaker — Battlecry: choose N Cataclysms to unleash,
    where N = 1 + min(heralds_this_game, 2). Re-entrant GenericChoice: pick one
    of the four Cataclysm spells, cast it, then re-queue until N picks are made.
    Already-picked Cataclysms are removed from the offered pool."""

    TARGET = ActionArg()

    CATACLYSMS = ["CATA_190t10", "CATA_190t11", "CATA_190t12", "CATA_190t13"]

    def do(self, source, target):
        ctrl = source.controller
        n = 1 + min(getattr(ctrl, "heralds_this_game", 0), 2)
        source._dw_picks_left = n
        source._dw_remaining = list(self.CATACLYSMS)
        _deathwing_open_choice(source)


def _deathwing_open_choice(deathwing):
    """Queue the next Cataclysm GenericChoice for the Deathwing entity, if any
    picks remain and any Cataclysms are still on offer."""
    if getattr(deathwing, "_dw_picks_left", 0) <= 0 or not getattr(
        deathwing, "_dw_remaining", None
    ):
        return
    ctrl = deathwing.controller
    choices = [ctrl.card(cid, source=deathwing) for cid in deathwing._dw_remaining]
    deathwing.game.queue_actions(
        deathwing,
        [GenericChoice(ctrl, choices).then(_DeathwingResolve(deathwing, Choice.CARD))],
    )


class _DeathwingResolve(TargetedAction):
    """Cast the chosen Cataclysm, decrement the counter, and re-open the choice."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, deathwing, card):
        chosen_id = getattr(card, "id", None)
        if chosen_id in getattr(deathwing, "_dw_remaining", []):
            deathwing._dw_remaining.remove(chosen_id)
        deathwing._dw_picks_left = getattr(deathwing, "_dw_picks_left", 1) - 1
        source.game.cheat_action(source, [PlayCataclysm(deathwing.controller, card)])
        _deathwing_open_choice(deathwing)


class PlayCataclysm(TargetedAction):
    """Resolve a single Cataclysm spell's effect (the tokens have 0 cost and
    are cast directly rather than played from hand)."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        cid = getattr(card, "id", None)
        ctrl = target
        if cid == "CATA_190t10":
            # Dragon's Reign — summon a 12/12 Dragon.
            source.game.cheat_action(source, [Summon(ctrl, "CATA_190t14")])
        elif cid == "CATA_190t11":
            # Topple — destroy the highest-Health enemy minion.
            enemies = list(ctrl.opponent.field)
            if enemies:
                top = max(enemies, key=lambda m: m.health)
                source.game.cheat_action(source, [Destroy(top)])
        elif cid == "CATA_190t12":
            # Raze — deal 4 damage to all enemy minions.
            for m in list(ctrl.opponent.field):
                source.game.cheat_action(source, [Hit(m, 4)])
        elif cid == "CATA_190t13":
            # Enthrall — shuffle five random Legendary Dragons (cost 1) into
            # your deck.
            for _ in range(5):
                source.game.cheat_action(
                    source,
                    [
                        Give(ctrl, RandomDragon(rarity=Rarity.LEGENDARY)).then(
                            Buff(Give.CARD, "CATA_190t13e"),
                            Shuffle(ctrl, Give.CARD),
                        )
                    ],
                )


@custom_card
class CATA_190t13e:
    "Enthralled"
    tags = {
        GameTag.CARDNAME: "Enthralled",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    cost = SET(1)


class CATA_190h:
    "Deathwing, Worldbreaker"
    # Battlecry: Choose {0} Cataclysm(s) to unleash! Herald twice to upgrade.
    # Cost reduced by the controller's banked Ultraxion reduction
    # (Player.deathwing_cost_reduction) — applies wherever this card is held or
    # drawn (the engine clamps cost at 0).
    cost_mod = -_DeathwingDiscount()
    play = _DeathwingUnleash(SELF)


class CATA_190p:
    "Ruthless"
    # Hero Power: +5 Attack this turn.
    activate = Buff(FRIENDLY_HERO, "CATA_190pe")


class CATA_190pe:
    "Ruthless"
    # +5 Attack this turn. (TAG_ONE_TURN_EFFECT carried by data.)
    tags = {GameTag.ATK: 5}


class CATA_190t10:
    "Dragon's Reign"
    # Summon a 12/12 Dragon. (Resolved via PlayCataclysm.)


class CATA_190t11:
    "Topple"
    # Destroy the highest Health enemy minion. (Resolved via PlayCataclysm.)


class CATA_190t12:
    "Raze"
    # Deal 4 damage to all enemy minions. (Resolved via PlayCataclysm.)


class CATA_190t13:
    "Enthrall"
    # Shuffle five random Legendary Dragons into your deck. They cost (1).
    # (Resolved via PlayCataclysm.)


class CATA_190t14:
    "Progeny of Deathwing"
    # Vanilla 12/12 Dragon token.
