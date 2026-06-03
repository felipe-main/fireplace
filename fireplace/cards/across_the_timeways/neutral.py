from ..utils import *

from hearthstone.enums import SpellSchool, Race

from ..emerald_dream.neutral import _GiveDarkGift


##
# Rewind minions — implement only the base play effect. The engine offers the
# Keep/Rewind choice automatically (GameTag.REWIND) and re-runs `play` once on
# a Rewind pick. Do NOT add choice/re-run logic here.


class TIME_002:
    "Aeon Wizard"
    # Rewind Battlecry: Get 2 random spells from your class.
    play = Give(CONTROLLER, RandomSpell(card_class=FRIENDLY_CLASS)) * 2


class TIME_003:
    "Portal Vanguard"
    # Rewind Battlecry: Draw a random minion. Give it +2/+2.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION)).then(
        Buff(ForceDraw.TARGET, "TIME_003e")
    )


class TIME_003e:
    "Guarding Time"
    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TIME_004:
    "Conflux Crasher"
    # Rewind Battlecry: Deal 7 damage to a random enemy.
    play = Hit(RANDOM_ENEMY_CHARACTER, 7)


class TIME_024:
    "Murozond, Unbounded"
    # Battlecry: At the start of your next turn, set this minion's Attack to
    # INFINITY!
    play = Buff(SELF, "TIME_024e2")


class TIME_024e:
    "INFINITE POWER!"
    # Attack set to INFINITY!
    atk = SET(2147483647)


class TIME_024e2:
    "Murozond, End of Time"
    # At the start of your next turn, set Murozond's Attack to INFINITY!
    events = OWN_TURN_BEGIN.on(Buff(OWNER, "TIME_024e"))


class TIME_035:
    "Time Machine"
    # Taunt Deathrattle: Get a random Rewind card.
    deathrattle = Give(
        CONTROLLER,
        RandomCard(
            collectible=True,
            custom_filter=lambda c: c.tags.get(GameTag.REWIND, 0),
        ),
    )


class TIME_038:
    "Mister Clocksworth"
    # Rewind, Rewind Battlecry: Summon 2 random Legendary minions.
    play = Summon(CONTROLLER, RandomLegendaryMinion()) * 2


class TIME_038t1:
    "Mister Clocksworth"
    # Rewind, Rewind Battlecry: Summon 2 random Legendary minions.
    play = Summon(CONTROLLER, RandomLegendaryMinion()) * 2


class TIME_038t2:
    "Mister Clocksworth"
    # Rewind Battlecry: Summon 2 random Legendary minions.
    play = Summon(CONTROLLER, RandomLegendaryMinion()) * 2


class TIME_038t3:
    "Mister Clocksworth"
    # Battlecry: Summon 2 random Legendary minions.
    play = Summon(CONTROLLER, RandomLegendaryMinion()) * 2


class TIME_040:
    "Fading Memory"
    # Deathrattle: Get a random 5-Cost minion from the past.
    deathrattle = Give(CONTROLLER, RandomMinion(cost=5, from_past=True))


class _ForefatherGuess(TargetedAction):
    """Futuristic Forefather — show three cards (one drawn from the opponent's
    actual hand when possible). If the controller picks the card that is in the
    opponent's hand, the Forefather gains +4 Health (TIME_041e2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent

        choices = []
        correct_id = None
        if opp.hand:
            real = source.game.random.choice(list(opp.hand))
            correct_id = real.id
            choices.append(ctrl.card(real.id, source=source))
        pool = db.filter(collectible=True, type=CardType.MINION)
        guard = 0
        while len(choices) < 3 and pool and guard < 200:
            guard += 1
            cid = source.game.random.choice(pool)
            if any(c.id == cid for c in choices):
                continue
            choices.append(ctrl.card(cid, source=source))
        if not choices:
            return
        # Stash the correct card object on the Forefather; the resolver compares
        # the chosen card against it by identity (avoids passing a raw id string
        # through the action pipeline, which would be coerced into a Card).
        target._ff_correct = choices[0] if correct_id is not None else None
        choice = GenericChoice(ctrl, choices).then(
            _ForefatherResolve(target, Choice.CARD)
        )
        source.game.queue_actions(source, [choice])


class _ForefatherResolve(TargetedAction):
    """Resolve the guess: buff the Forefather if the chosen card is the one
    pulled from the opponent's hand. The chosen card is supplied via Choice.CARD
    (the Choice event's third arg)."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, forefather, card):
        correct = getattr(forefather, "_ff_correct", None)
        if correct is not None and card is correct:
            source.game.queue_actions(source, [Buff(forefather, "TIME_041e2")])


class TIME_041:
    "Futuristic Forefather"
    # Taunt. Battlecry: Look at 3 cards. Guess which one is in your opponent's
    # hand to gain +4 Health.
    play = _ForefatherGuess(SELF)


class TIME_041e2:
    "Infiltration"
    # +4 Health.
    tags = {GameTag.HEALTH: 4}


class TIME_045:
    "Whelp of the Infinite"
    # Poisonous Reborn
    pass


class TIME_046:
    "Cyborg Patriarch"
    # Dormant for 3 turns. Taunt
    # Data omits the DORMANT GameTag, so declare it (like EDR_979) — otherwise
    # _set_zone leaves it awake and the timer never engages.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 3


class TIME_046e:
    "Prime Ape"
    # Dormant. Awaken in N turns.
    pass


class _EnemyHeroDamageThisTurn(LazyNum):
    """Devious Coyote cost reduction. The printed card reduces cost by 1 for
    each *time* the enemy hero took damage this turn. The engine tracks the
    distinct damage-EVENT count on each player (``times_hero_damaged_this_turn``,
    bumped +1 per hero-damage event in Damage.do), so read that — not the total
    damage *points* (``hero_damage_taken_this_turn``), which would wrongly
    reduce cost by the size of a single hit. "Enemy hero" = the controller's
    opponent's hero (Coyote sits in the controller's hand)."""

    def evaluate(self, source):
        opp = source.controller.opponent
        value = getattr(opp, "times_hero_damaged_this_turn", 0)
        # Honour the LazyNum sign/scale set by the unary minus in cost_mod.
        return self.num(value)


class TIME_047:
    "Devious Coyote"
    # Stealth. Costs (1) less for each time the enemy hero took damage this
    # turn.
    cost_mod = -_EnemyHeroDamageThisTurn()


class _ClockworkRagerBuff(TargetedAction):
    """Clockwork Rager — gain +1 Health for each turn the controller has taken
    this game (``player.turns`` records one entry per turn taken)."""

    TARGET = ActionArg()

    def do(self, source, target):
        turns = len(source.controller.turns)
        if turns > 0:
            source.game.queue_actions(
                source, [Buff(target, "TIME_048e", atk=0, max_health=turns)]
            )


class TIME_048:
    "Clockwork Rager"
    # Battlecry: Gain +1 Health for each turn you've taken this game.
    play = _ClockworkRagerBuff(SELF)


class TIME_048e:
    "Clockwork Rage"
    # Increased Health.
    pass


class TIME_049:
    "Dangerous Variant"
    # At the start of your turn, transform into a random 5-Cost minion.
    events = OWN_TURN_BEGIN.on(Morph(SELF, RandomMinion(cost=5)))


class TIME_050:
    "Sentient Hourglass"
    # Rush. After this minion survives damage, swap its stats.
    events = SELF_DAMAGE.on(Dead(SELF) | Buff(SELF, "TIME_050e"))


TIME_050e = AttackHealthSwapBuff()


class TIME_051:
    "Soldier of the Infinite"
    # Rush Battlecry: Double this minion's Attack.
    play = Buff(SELF, "TIME_051e", atk=ATK(SELF))


class TIME_051e:
    "Infinite Scales"
    # Doubled Attack.
    pass


class TIME_052:
    "Amber Warden"
    # Taunt Deathrattle: Summon a random minion from the past.
    deathrattle = Summon(CONTROLLER, RandomMinion(from_past=True))


class TIME_053:
    "Sandmaw"
    pass


class TIME_054:
    "Time Skipper"
    # At the end of each player's turn, give them a Coin.
    events = TURN_END.on(Give(CURRENT_PLAYER, THE_COIN))


class TIME_054e:
    "Skipping Time"
    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TIME_055:
    "Unknown Voyager"
    # After this survives damage, transform into a random 7-Cost minion.
    events = SELF_DAMAGE.on(Dead(SELF) | Morph(SELF, RandomMinion(cost=7)))


class TIME_056:
    "Whelp of the Bronze"
    # Lifesteal Divine Shield
    pass


class _ResetCosts(TargetedAction):
    """Wizened Truthseeker — reset every card in both hands to its printed
    (data) Cost.

    Two-stage, card-only reset so it reverses *any* cost mod, including a
    set-to-0 (a persistent ``GameTag.COST: -100`` enchantment). A plain
    additive delta (base - current) cannot undo COST:-100: the engine clamps
    the visible cost at 0, so the delta reads as ``base - 0 = base`` yet the
    new total is ``base + (-100) + base`` which still clamps to 0.

    Stage 1 strips every *pure cost-only* enchantment (one that changes Cost
    and nothing else) — this cleanly removes set-to-0 and ordinary cost
    discounts/markups carried by dedicated cost enchantments, returning the
    card to its data base. Stat-bearing buffs (e.g. a +2/+2 that also shifts
    Cost) are left intact, matching "reset only the Cost".

    Stage 2 applies the remaining additive delta for any residual mismatch
    (e.g. a mixed stat+cost buff, or a cost_mod) so the printed Cost is hit
    exactly even when no pure-cost enchant is present."""

    TARGET = ActionArg()

    @staticmethod
    def _is_cost_only(buff):
        # An enchantment is "cost-only" if its Cost contribution is non-zero
        # and it carries no stat/keyword payload we'd otherwise wipe. Read the
        # RAW underlying deltas (``_cost`` / ``_atk`` / …): the public `.cost`
        # property clamps at 0, so a set-to-0 (``_cost == -100``) would read
        # back as 0 and be missed.
        if getattr(buff, "_cost", 0) == 0:
            return False
        for attr in ("_atk", "_max_health", "_spellpower"):
            if getattr(buff, attr, 0):
                return False
        # Don't strip enchants that grant keywords / deathrattles etc.
        if getattr(buff, "has_deathrattle", False):
            return False
        return True

    def do(self, source, target):
        for player in source.game.players:
            for card in list(player.hand):
                base = card.data.cost
                # Stage 1: drop pure cost-only enchantments (reverses COST:-100).
                for buff in list(card.buffs):
                    if self._is_cost_only(buff):
                        buff.remove()
                # Stage 2: additive correction for any residual (mixed buffs,
                # cost_mod, etc.) so the card lands exactly on its base Cost.
                delta = base - card.cost
                if delta != 0:
                    source.game.queue_actions(
                        source, [Buff(card, "TIME_057e", cost=delta)]
                    )


class TIME_057:
    "Wizened Truthseeker"
    # Battlecry: Set the Cost of every card in both player's hands back to their
    # original Costs.
    play = _ResetCosts(SELF)


class TIME_057e:
    "True Wisdom"
    # Cost changed.
    pass


class TIME_058:
    "Paltry Flutterwing"
    # Deathrattle: Summon a random 2-Cost minion that is Dormant for 2 turns.
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=2)).then(
        Dormant(Summon.CARD, 2)
    )


class TIME_058e:
    "Consequences"
    # Dormant. Awaken in N turns.
    pass


class TIME_059:
    "Living Paradox"
    # Elusive Battlecry: Summon two 2/1 Living Paradoxes with Elusive.
    play = Summon(CONTROLLER, "TIME_059") * 2


class TIME_060:
    "Quantum Destabilizer"
    # This minion takes double damage from all sources.
    tags = {GameTag.INCOMING_DAMAGE_MULTIPLIER: True}


class _ReverseDeck(TargetedAction):
    """Timeless Causality — reverse the controller's deck order in place."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.deck.reverse()


class TIME_061:
    "Timeless Causality"
    # Battlecry: Reverse the order of your deck.
    play = _ReverseDeck(SELF)


class TIME_062:
    "Chronicle Keeper"
    # Battlecry: If you're holding a Dragon, gain Taunt and Divine Shield.
    play = HOLDING_DRAGON & (Taunt(SELF), GiveDivineShield(SELF))


class _NozdormuHasten(TargetedAction):
    """Timelord Nozdormu — playing a newest-expansion (TIME_) card while he is
    Dormant shaves one turn off his remaining Dormant timer (awakening him if
    it reaches zero)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not target.dormant:
            return
        if target.dormant_turns > 0:
            target.dormant_turns -= 1
        if target.dormant_turns <= 0:
            source.game.queue_actions(source, [Awaken(target)])


_NEWEST_EXPANSION = FilterSelector(
    lambda entity, source: str(getattr(entity, "id", "")).startswith("TIME_")
)


class TIME_063:
    "Timelord Nozdormu"
    # Dormant for 5 turns. Rush. After you play a card from the newest
    # expansion, awaken 1 turn sooner.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 5
    dormant_events = Play(CONTROLLER, _NEWEST_EXPANSION).on(_NozdormuHasten(SELF))


class TIME_063e1:
    "Lord of Time"
    # Dormant. Awaken in N turns.
    pass


class TIME_063e2:
    "Nozdormu Play Enchant"
    # After you play a card from the newest expansion, awaken 1 turn sooner.
    pass


class TIME_064:
    "Chrono-Lord Deios"
    # Your Battlecries, Deathrattles, Hero Power, and end of turn effects
    # trigger twice.
    # Battlecries + Deathrattles use the engine's EXTRA_* slot flags; end-of-turn
    # effects double via the EXTRA_END_TURN_EFFECT flag (EndTurn.do re-broadcasts
    # the ON event when the ending player has it set); the Hero Power is doubled
    # by re-running the activated power.
    update = Refresh(
        CONTROLLER,
        {
            enums.EXTRA_BATTLECRIES: True,
            GameTag.EXTRA_DEATHRATTLES: True,
            enums.EXTRA_END_TURN_EFFECT: True,
        },
    )
    events = Activate(FRIENDLY_HERO_POWER).after(
        PlayHeroPower(Activate.CARD, Activate.TARGET)
    )


class TIME_064e:
    "Deios' Influence"
    # Your Battlecries, Deathrattles, Hero Power, and end of turn effects
    # trigger twice.
    pass


class TIME_100:
    "Hourglass Attendant"
    # Divine Shield At the end of your turn, give all minions in your hand
    # +1/+1.
    events = OWN_TURN_END.on(Buff(FRIENDLY_HAND + MINION, "TIME_100e"))


class TIME_100e:
    "Sandy Polish"
    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TIME_101:
    "Misplaced Pyromancer"
    # Whenever you Shatter a card, deal 2 damage to all enemy minions.
    # The engine broadcasts actions.Shatter at the end of _shatter_into_halves
    # whenever the controller shatters a card.
    events = Shatter(CONTROLLER).on(Hit(ENEMY_MINIONS, 2))


class _MetaphysicalTick(TargetedAction):
    """Circadiamancer's enchant — at the start of each of the controller's
    turns, deepen the held card's cost reduction by 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        for buff in list(target.buffs):
            if buff.id == "TIME_102e":
                buff._metaphysical_reduction = (
                    getattr(buff, "_metaphysical_reduction", 0) + 1
                )


class TIME_102:
    "Circadiamancer"
    # Battlecry: Add a random 8-Cost minion to your hand. At the start of your
    # turns, reduce its Cost by (1).
    play = Give(CONTROLLER, RandomMinion(cost=8)).then(Buff(Give.CARD, "TIME_102e"))


class TIME_102e:
    "Metaphysical"
    # Reduces Cost each turn.
    cost = lambda self, i: i - getattr(self, "_metaphysical_reduction", 0)

    class Hand:
        events = OWN_TURN_BEGIN.on(_MetaphysicalTick(OWNER))


class _ChromieDraw(TargetedAction):
    """Chromie — for each card the controller has played this game, create a
    fresh copy and draw it."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for original in list(ctrl.cards_played_this_game):
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            copy = ctrl.card(original.id, source=source)
            copy.zone = Zone.DECK
            source.game.cheat_action(source, [ForceDraw(copy)])


class TIME_103:
    "Chromie"
    # Deathrattle: Draw another copy of cards you've played this game.
    deathrattle = _ChromieDraw(SELF)


class TIME_428:
    "Yesterloc"
    # At the end of your turn, give your other minions +1 Health.
    events = OWN_TURN_END.on(Buff(FRIENDLY_MINIONS - SELF, "TIME_428e"))


class TIME_428e:
    "Mrrgls of Yore"
    # +1 Health.
    tags = {GameTag.HEALTH: 1}


class TIME_434:
    "Temporal Traveler"
    # Deathrattle: Summon a 4/1 Shadow that attacks a random enemy minion.
    deathrattle = Summon(CONTROLLER, "TIME_434t").then(
        Attack(Summon.CARD, RANDOM_ENEMY_MINION)
    )


class TIME_434t:
    "Temporal Shadow"
    pass


class TIME_720:
    "Soldier of the Bronze"
    # Taunt Battlecry: Double this minion's Health.
    play = Buff(SELF, "TIME_720e")


class TIME_720e:
    "Bronze Scales"
    # Doubled Health.
    def apply(self, target):
        self._xhealth = target.health * 2

    max_health = lambda self, _: self._xhealth


##
# Across the Timeways (END_) — End Time mini-set
#
# Every collectible here is a dual-class ("Multiple Classes") card, but class
# membership is data-side only; the scripts use no class-specific machinery
# beyond Imbue/Corpses/Outcast which the engine already routes per controller.


class END_001:
    "Jagged Edge of Time"
    # Battlecry: Imbue your Hero Power.
    play = Imbue(CONTROLLER)


class _WickedDaggerDeathrattle(TargetedAction):
    """Wicked Blightspawn — equip a 1/2 Dagger (Wicked Knife, CS2_082); but if
    a weapon is already equipped, give it +2 Attack instead."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.weapon is not None:
            source.game.cheat_action(source, [Buff(ctrl.weapon, "END_002e")])
        else:
            source.game.cheat_action(source, [Summon(ctrl, "CS2_082")])


class END_002:
    "Wicked Blightspawn"
    # Reborn. Deathrattle: Equip a 1/2 Dagger. If you already have a weapon
    # equipped, give it +2 Attack instead.
    deathrattle = _WickedDaggerDeathrattle(SELF)


class END_002e:
    "Wicked"
    # +2 Attack.
    tags = {GameTag.ATK: 2}


class _MinionsDiedThisTurn(LazyNum):
    """Count every minion that died this turn, BOTH sides. The per-player
    `minions_killed_this_turn` only bumps on the controller of the minion that
    died, so reading just CONTROLLER's would miss enemy deaths — use the
    game-level both-sides aggregate (game.py minions_killed_this_turn)."""

    def evaluate(self, source):
        return self.num(source.game.minions_killed_this_turn)


class END_004:
    "Remnant of Rage"
    # Costs (1) less for each minion that died this turn (both sides).
    # Battlecry: Draw 2 cards.
    cost_mod = -_MinionsDiedThisTurn()
    play = Draw(CONTROLLER) * 2


class _BygoneSummon(TargetedAction):
    """Bygone Echoes — summon a random 4-Cost minion; then for each additional
    summon "credit" (one for spending 4 Corpses, one more for Outcast) summon
    another random 4-Cost minion. The credits are decided by the caller."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        for _ in range(amount):
            source.game.cheat_action(
                source, [Summon(source.controller, RandomMinion(cost=4))]
            )


class _BygoneEcho(TargetedAction):
    """Resolve Bygone Echoes' total summon count: 1 base, +1 if 4 Corpses are
    spent, +1 for Outcast (passed via OUTCAST)."""

    TARGET = ActionArg()
    OUTCAST = IntArg()

    def do(self, source, target, outcast):
        ctrl = source.controller
        count = 1
        if ctrl.corpses >= 4:
            source.game.cheat_action(source, [SpendCorpses(ctrl, 4)])
            count += 1
        count += outcast
        source.game.cheat_action(source, [_BygoneSummon(ctrl, count)])


class END_005:
    "Bygone Echoes"
    # Summon a random 4-Cost minion. Spend 4 Corpses to summon another.
    # Outcast: And another.
    play = _BygoneEcho(SELF, 0)
    outcast = _BygoneEcho(SELF, 1)


class END_007:
    "Press the Advantage"
    # Deal 1 damage. Give your hero +1 Attack this turn. Draw 1 card. Gain 1
    # Armor.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        Hit(TARGET, 1),
        Buff(FRIENDLY_HERO, "END_007e1"),
        Draw(CONTROLLER),
        GainArmor(FRIENDLY_HERO, 1),
    )


class END_007e1:
    "Claws of Fury"
    # +1 Attack this turn.
    tags = {GameTag.ATK: 1}


class END_008:
    "Enduring Roach"
    # After you use your Hero Power, refresh 2 Mana Crystals.
    events = Activate(FRIENDLY_HERO_POWER).after(FillMana(CONTROLLER, 2))


class END_010:
    "Twilight Timereaver"
    # Choose One - Set the Attack of all other minions to 1; or Health to 1.
    choose = ("END_010a", "END_010b")
    # If both halves are chosen (e.g. by a Choose-Both effect) apply the
    # combined "Attack and Health set to 1" enchant to all other minions.
    play = ChooseBoth(CONTROLLER) & Buff(ALL_MINIONS - SELF, "END_010e")


class END_010a:
    "Finite Will"
    # Set the Attack of all other minions to 1.
    play = Buff(ALL_MINIONS - SELF, "END_010ae")


class END_010ae:
    "Finite Will"
    # Attack set to 1.
    atk = SET(1)


class END_010b:
    "Finite Resolve"
    # Set the Health of all other minions to 1.
    play = Buff(ALL_MINIONS - SELF, "END_010be")


class END_010be:
    "Finite Resolve"
    # Health set to 1.
    max_health = SET(1)


class END_010e:
    "Finite Existence"
    # Attack and Health set to 1.
    atk = SET(1)
    max_health = SET(1)


class _AccelerationTick(TargetedAction):
    """Acceleration Aura tick — at the start of the controller's turn, grant a
    temporary Mana Crystal (ManaThisTurn) and count the aura down. The data
    ships no controller-aura enchant id, so a custom one is registered below.
    Base duration 3 turns (TAG_SCRIPT_DATA_NUM_1 = 3)."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        ctrl = enchant.controller
        enchant.game.cheat_action(enchant, [ManaThisTurn(ctrl, 1)])
        left = getattr(enchant, "_aura_turns_left", 0) - 1
        enchant._aura_turns_left = max(0, left)
        if left <= 0:
            enchant.game.cheat_action(enchant, [Destroy(enchant)])


class END_011:
    "Acceleration Aura"
    # At the start of your turn, gain a temporary Mana Crystal. Lasts 3 turns.
    play = Buff(CONTROLLER, "END_011_aura")

    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class END_011_aura:
    "Acceleration Aura"
    tags = {
        GameTag.CARDNAME: "Acceleration Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_BEGIN.on(_AccelerationTick(SELF))

    def apply(self, target):
        self._aura_turns_left = 3


class END_013:
    "Brutish Endmaw"
    # Battlecry: Discover a 1-Cost minion with a Dark Gift.
    # Same modelling as EDR Dark-Gift Discover cards (shared `_GiveDarkGift`).
    play = Discover(
        CONTROLLER,
        RandomMinion(cost=1),
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))


class END_014:
    "Synchronized Spark"
    # Deal 3 damage to an enemy. If it dies, give a random friendly minion
    # +3/+3.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Hit(TARGET, 3).then(
        Dead(TARGET) & Buff(RANDOM(FRIENDLY_MINIONS), "END_014e")
    )


class END_014e:
    "In Sync"
    # +3/+3.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class END_016:
    "Chronoclaws"
    # After your hero attacks, discard your highest Cost card.
    events = Attack(FRIENDLY_HERO).after(Discard(HIGHEST_COST(FRIENDLY_HAND)))


class _BattleEndProgress(TargetedAction):
    """Battle at the End Time quest — progresses through a fill-then-empty
    cycle, checked at the controller's turn end. Progress 1 once the hand is
    full; progress 2 once the (previously-full) hand has been emptied. Tracked
    via `_battle_filled` on the quest card."""

    TARGET = ActionArg()

    def do(self, source, quest):
        ctrl = source.controller
        if not getattr(quest, "_battle_filled", False):
            if len(ctrl.hand) >= ctrl.max_hand_size:
                quest._battle_filled = True
                source.game.cheat_action(source, [AddProgress(quest, 1)])
        else:
            if len(ctrl.hand) == 0:
                source.game.cheat_action(source, [AddProgress(quest, 1)])


class END_017(QuestRewardProtect):
    "Battle at the End Time"
    # Quest: Fill your hand, then empty it. Reward: Tick and Tock.
    # The fill->empty objective has no Play-style trigger; we evaluate the hand
    # at each of the controller's turn ends (progress 1 when full, 2 when later
    # emptied), matching the data QUEST_PROGRESS_TOTAL of 2.
    progress_total = 2
    quest = OWN_TURN_END.on(_BattleEndProgress(SELF))
    reward = Give(CONTROLLER, "END_017t")


class _TickAndTockFill(TargetedAction):
    """Tick and Tock battlecry — draw until the controller's hand is full."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        guard = 0
        while len(ctrl.hand) < ctrl.max_hand_size and guard < 20:
            guard += 1
            before = len(ctrl.hand) + len(ctrl.deck)
            source.game.cheat_action(source, [Draw(ctrl)])
            if not ctrl.deck and len(ctrl.hand) + len(ctrl.deck) >= before:
                # Drew nothing new (fatigue / empty deck) — stop.
                if not ctrl.deck:
                    break


class _EmptyOpponentHand(TargetedAction):
    """Tick and Tock deathrattle — discard the opponent's entire hand. Resolved
    via the controller's opponent directly so it works from the graveyard (a
    relative ENEMY_HAND selector evaluates to nothing once the source is dead)."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        for card in list(opp.hand):
            source.game.cheat_action(source, [Discard(card)])


class END_017t:
    "Tick and Tock"
    # Battlecry: Draw until your hand is full. Deathrattle: Empty the
    # opponent's hand.
    # The data card ships only the BATTLECRY tag (no DEATHRATTLE), so declare it
    # here or the deathrattle never fires.
    tags = {GameTag.DEATHRATTLE: True}
    play = _TickAndTockFill(SELF)
    deathrattle = _EmptyOpponentHand(SELF)


class END_019:
    "Endtime Survivor"
    # Taunt. Battlecry: If your hero took damage this turn, gain +3/+3.
    play = (Attr(FRIENDLY_HERO, "damaged_this_turn") >= 1) & Buff(
        SELF, "END_019e"
    )


class END_019e:
    "Alone in Time"
    # +3/+3.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class END_020:
    "Eternal Toil"
    # Deal 1 damage to a minion. If it survives, draw a card. If it dies,
    # summon a random 1-Cost minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 1).then(
        (Dead(TARGET) & Summon(CONTROLLER, RandomMinion(cost=1)))
        | Draw(CONTROLLER)
    )


class END_022:
    "Time-Twisted Seer"
    # Has Spell Damage +2 while damaged.
    update = Find(SELF + DAMAGED) & Refresh(SELF, {GameTag.SPELLPOWER: 2})


class END_022e:
    "Time-Twisted"
    # Spell Damage +2.
    tags = {GameTag.SPELLPOWER: 2}


class END_023:
    "Bitter End"
    # Freeze a minion and its neighbors. Destroy any that are damaged.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Freeze(TARGET),
        Freeze(ADJACENT(TARGET)),
        Find(TARGET + DAMAGED) & Destroy(TARGET),
        Destroy(ADJACENT(TARGET) + DAMAGED),
    )


class _EternalFireboltReturn(TargetedAction):
    """Eternal Firebolt — when the damaged minion dies, arm an end-of-turn
    return: a one-shot enchant on the controller that, at this turn's end,
    gives a fresh copy of the spell back to the hand and removes itself."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # `source` is the cast spell card; re-create it by id at turn end.
        spell_id = source.id
        ench = ctrl.card("END_025e", source=source)
        ench._firebolt_id = spell_id
        source.game.cheat_action(source, [Buff(ctrl, ench)])


class END_025:
    "Eternal Firebolt"
    # Lifesteal. Deal 3 damage to a minion. If it dies, return this to your hand
    # at the end of your turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3).then(Dead(TARGET) & _EternalFireboltReturn(SELF))


class _FireboltGiveBack(TargetedAction):
    """At end of turn, return the Eternal Firebolt to hand and self-destruct."""

    TARGET = ActionArg()

    def do(self, source, enchant):
        ctrl = enchant.controller
        spell_id = getattr(enchant, "_firebolt_id", "END_025")
        enchant.game.cheat_action(enchant, [Give(ctrl, spell_id)])
        enchant.game.cheat_action(enchant, [Destroy(enchant)])


@custom_card
class END_025e:
    "Eternal Firebolt"
    # Get an Eternal Firebolt at the end of the turn.
    tags = {
        GameTag.CARDNAME: "Eternal Firebolt",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(_FireboltGiveBack(SELF))


class END_026:
    "Fragment of Nothing"
    # After you cast a spell on a minion, draw a card.
    events = Play(CONTROLLER, SPELL).after(
        Find(Play.TARGET + MINION) & Draw(CONTROLLER)
    )


class END_028:
    "For All Time"
    # Destroy all minions with 4 or less Attack. Overload: (2)
    play = Destroy(ALL_MINIONS + (ATK <= 4))


class _VoodooShadowSpell(TargetedAction):
    """Voodoo Totem — get one random Shadow spell. Wrapped in a custom action so
    the random roll happens exactly ONCE: a bare Give(RANDOM(...)) placed directly
    in an `events` list is evaluated twice by the event machinery (truthy gate +
    action extraction), which rolls — and gives — two different cards per turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(
            source,
            [Give(source.controller, RandomSpell(spell_school=SpellSchool.SHADOW))],
        )


class END_029:
    "Voodoo Totem"
    # At the end of your turn, get a random Shadow spell.
    events = OWN_TURN_END.on(_VoodooShadowSpell(SELF))


class END_031:
    "Shade of the End Time"
    # Stealth. Spell Damage +1. (Both carried by data tags — vanilla body.)
    pass


class END_032:
    "Winged Aberration"
    # Rush. Combo and Overload (2): Gain Immune this turn and Windfury.
    # The combo body is only run when a card was played earlier this turn, and
    # it pays the Overload (2) itself (the data carries no OVERLOAD tag).
    combo = (
        Buff(SELF, "END_032e"),
        Overload(CONTROLLER, 2),
    )


class END_032e:
    "Aberrant"
    # Immune this turn (and Windfury — folded into this single enchant; the
    # data enchant carries only TAG_ONE_TURN_EFFECT, so supply both keywords).
    tags = {GameTag.IMMUNE: True, GameTag.WINDFURY: True}


class END_033:
    "Prescient Slitherdrake"
    # Elusive. Costs (3) less if you're holding another Dragon.
    # Elusive (CANT_BE_TARGETED_BY_SPELLS/HERO_POWERS) is carried by data tags.
    cost_mod = HOLDING_DRAGON & -3


class _CrumblecrusherDestroy(TargetedAction):
    """Crumblecrusher — destroy a random enemy minion, a random enemy location,
    and a random enemy weapon (each independently, if present)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        rng = source.game.random
        picks = []
        minions = [m for m in opp.field if not m.dead]
        locations = [c for c in opp.field if c.type == CardType.LOCATION]
        # Locations live in the same field list as minions; separate them so a
        # minion-destroy and a location-destroy are independent picks.
        real_minions = [m for m in minions if m.type == CardType.MINION]
        if real_minions:
            picks.append(rng.choice(real_minions))
        if locations:
            picks.append(rng.choice(locations))
        if opp.weapon is not None:
            picks.append(opp.weapon)
        if picks:
            source.game.cheat_action(source, [Destroy(picks)])


class END_034:
    "Crumblecrusher"
    # Battlecry: Destroy a random enemy minion, location, and weapon.
    play = _CrumblecrusherDestroy(SELF)


class _OmenDestroyTop(TargetedAction):
    """Omen of the End — if the controller's deck is empty, destroy (mill) the
    top 5 cards of the enemy deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.deck:
            return
        opp = ctrl.opponent
        for _ in range(5):
            if not opp.deck:
                break
            card = opp.deck[-1]
            source.game.cheat_action(source, [Destroy(card)])


class END_035:
    "Omen of the End"
    # Battlecry: If your deck is empty, destroy the top 5 cards of the enemy
    # deck.
    play = _OmenDestroyTop(SELF)


class END_036:
    "Morchie"
    # Your Rewinds keep BOTH potential outcomes. Battlecry: Discover a Rewind
    # card from any class.
    # "Keep BOTH outcomes" IS implemented as an aura in Play.do (actions.py):
    # while a Morchie (END_036) is on the controller's field, a Rewind card
    # skips the Keep/Rewind choice and re-runs its Battlecry once, so the effect
    # resolves twice. END_036e is a cosmetic marker only (the hook keys off the
    # minion's field presence, not the enchant); the Discover is faithful.
    play = Buff(FRIENDLY_HERO, "END_036e"), DISCOVER(
        RandomCard(
            collectible=True,
            custom_filter=lambda c: c.tags.get(GameTag.REWIND, 0),
        )
    )


class END_036e:
    "Multiversal Singularity"
    # Your Rewinds keep BOTH outcomes.
    pass


class _MurozondFillDragons(TargetedAction):
    """Endtime Murozond — fill the controller's board with random Dragons, fully
    heal the hero, then skip the controller's next turn. The skip uses the real
    engine primitive (player._skip_next_turn, consumed in game.py turn-advance),
    so the controller genuinely loses a turn rather than the opponent gaining
    one — their start-of-turn triggers, mana ramp and draw are all skipped."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        guard = 0
        while ctrl.minion_slots > 0 and guard < 14:
            guard += 1
            before = len(ctrl.field)
            source.game.cheat_action(source, [Summon(ctrl, RandomDragon())])
            if len(ctrl.field) <= before:
                break
        source.game.cheat_action(source, [Heal(ctrl.hero, 30)])
        # "Skip your next turn."
        ctrl._skip_next_turn = True


class END_037:
    "Endtime Murozond"
    # Battlecry: Fill your board with random Dragons. Fully heal your hero.
    # Skip your next turn.
    play = _MurozondFillDragons(SELF)


class _EndTimeQuestStage(TargetedAction):
    """Battle at the End Time — two-stage Quest progress, evaluated at the end of
    your turn: stage 1 completes when your hand is full, stage 2 (the reward)
    when your hand is then empty. (Approximation: the printed quest can fill and
    empty within a single turn; we sample hand size at end of turn, which still
    requires the player to have filled then emptied across their turns.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        stage = getattr(source, "_endtime_stage", 0)
        if stage == 0 and len(ctrl.hand) >= ctrl.max_hand_size:
            source._endtime_stage = 1
            source.game.cheat_action(source, [AddProgress(source, source)])
        elif stage == 1 and len(ctrl.hand) == 0:
            source._endtime_stage = 2
            source.game.cheat_action(source, [AddProgress(source, source)])


class END_017(QuestRewardProtect):
    "Battle at the End Time"
    # Quest: Fill your hand, then empty it. Reward: Tick and Tock.
    progress_total = 2
    quest = OWN_TURN_END.on(_EndTimeQuestStage(SELF))
    reward = Give(CONTROLLER, "END_017t")


class END_017t:
    "Tick and Tock"
    # Battlecry: Draw until your hand is full. Deathrattle: Empty the opponent's
    # hand. (Token data omits the DEATHRATTLE tag, so declare it for the engine.)
    tags = {GameTag.DEATHRATTLE: True}
    play = DrawUntil(CONTROLLER, 10)
    deathrattle = Discard(ENEMY_HAND)
