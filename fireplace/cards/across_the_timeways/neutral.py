from ..utils import *


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
    deathrattle = Give(CONTROLLER, RandomMinion(cost=5))


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
    each *time* the enemy hero took damage this turn; the engine only tracks
    total damage taken (``hero_damage_taken_this_turn``), not the instance
    count, so this approximates 1-per-damage-point (audit-noted)."""

    def evaluate(self, source):
        opp = source.controller.opponent
        value = getattr(opp, "hero_damage_taken_this_turn", 0)
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
    deathrattle = Summon(CONTROLLER, RandomMinion())


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
    (data) Cost via a dynamic cost buff (delta = base - current)."""

    TARGET = ActionArg()

    def do(self, source, target):
        for player in source.game.players:
            for card in list(player.hand):
                base = card.data.cost
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
    # Battlecries + Deathrattles use the engine's EXTRA_* slot flags; the Hero
    # Power is doubled by re-running the activated power. (End-of-turn doubling
    # has no general engine hook — audit-noted approximation.)
    update = Refresh(
        CONTROLLER,
        {enums.EXTRA_BATTLECRIES: True, GameTag.EXTRA_DEATHRATTLES: True},
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
    # NOTE: "Shatter" is a Timeways keyword with no engine event/action yet, and
    # no neutral-scope card actually Shatters a card, so there is nothing to
    # listen for. Implemented as a vanilla body; wiring the trigger would
    # require an engine Shatter primitive (audit-noted approximation).
    pass


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
