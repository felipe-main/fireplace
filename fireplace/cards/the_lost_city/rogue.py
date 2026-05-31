from ..utils import *


##
# Engine glue — "times you've shuffled cards into your deck"
#
# Several Lost City Rogue cards (Lie in Wait, Knockback, Underbrush Tracker)
# scale off a *game-wide* running count of how many cards the player has
# shuffled into their OWN deck. No engine counter exists for this, and the
# Shuffle action is the single chokepoint every shuffle flows through, so we
# wrap Shuffle.do once at import time to bump a per-player attribute
# (`_tlc_times_shuffled`). It is read lazily everywhere via
# `Attr(CONTROLLER, "_tlc_times_shuffled")` (defaults to 0 on a fresh Player).

if not getattr(Shuffle, "_tlc_count_patched", False):
    _tlc_orig_shuffle_do = Shuffle.do

    def _tlc_shuffle_do(self, source, target, cards):
        before = len(target.deck)
        result = _tlc_orig_shuffle_do(self, source, target, cards)
        # Count each card that actually entered the deck (deck-full shuffles
        # are no-ops and must not advance the counter).
        added = len(target.deck) - before
        if added > 0:
            target._tlc_times_shuffled = (
                getattr(target, "_tlc_times_shuffled", 0) + added
            )
        return result

    Shuffle.do = _tlc_shuffle_do
    Shuffle._tlc_count_patched = True


##
# Custom actions


class _NeferyaWeaponsmith(TargetedAction):
    """Neferset Weaponsmith — give the controller a random weapon from another
    class. Class attr `combo_buff` (True on the subclass used by the Combo
    script) decides whether to also stamp +2 Attack (TLC_516e) on the
    just-created weapon card while it sits in hand."""

    TARGET = ActionArg()
    combo_buff = False

    def do(self, source, target):
        ctrl = source.controller
        before = set(ctrl.hand)
        source.game.cheat_action(
            source, [Give(ctrl, RandomWeapon(card_class=ANOTHER_CLASS))]
        )
        new = [c for c in ctrl.hand if c not in before]
        if new and self.combo_buff:
            source.game.cheat_action(source, [Buff(new[0], "TLC_516e")])


class _NeferyaWeaponsmithCombo(_NeferyaWeaponsmith):
    combo_buff = True


# TLC_516e "Wicked Weaponry" exists in data but carries no ATK tag (the +2 is
# script-supplied). Declare the +2 Attack here.
TLC_516e = buff(atk=2)


class _MerchantOfLegend(TargetedAction):
    """Merchant of Legend — Discover callback. Give the chosen Legendary minion
    to hand and shuffle the other two offered Legendaries into the deck."""

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, cards, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        ctrl = source.controller
        source.game.cheat_action(source, [Give(ctrl, card.id)])
        for other in cards:
            if other is card:
                continue
            shuffled = ctrl.card(other.id, source=source)
            shuffled.controller = ctrl
            source.game.cheat_action(source, [Shuffle(ctrl, shuffled)])


class _CultistMapDiscoverDeck(TargetedAction):
    """Cultist Map — Discover a card from the controller's own deck, then draw
    the real copy out of the deck. (The secondary "if you play it this turn,
    also pick one of the others" upside is an approximation — see review.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ids = list({c.id for c in ctrl.deck})
        if not ids:
            return
        source.game.cheat_action(
            source,
            [
                Discover(CONTROLLER, RandomID(*ids)).then(
                    _CultistMapDrawChosen(SELF, Discover.CARD)
                )
            ],
        )


class _CultistMapDrawChosen(TargetedAction):
    """Pull the actual deck card matching the Discovered id into hand."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        ctrl = source.controller
        real = next((c for c in ctrl.deck if c.id == card.id), None)
        if real is not None:
            source.game.cheat_action(source, [ForceDraw(real)])


class _EyesInTheSkyPeek(TargetedAction):
    """Eyes in the Sky — look at the top 3 cards of the ENEMY deck and put one
    on top (so it's the opponent's next draw). Reuses the Dredge choice UI but
    scoped to the opponent's deck. Falls back to a no-op on an empty deck."""

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        # deck[-1] is the top (next draw); take the top 3.
        cards = list(target.deck[-3:])
        return [cards]

    def do(self, source, target, cards):
        if not cards:
            self.cards = []
            return
        player = source.controller
        player.choice = self
        self._callback = self.callback
        self.callback = []
        self.player = player
        self.source = source
        self.target = target
        self.cards = cards
        self.min_count = 1
        self.max_count = 1
        source.game.manager.targeted_action(self, source, target, cards)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid Eyes in the Sky choice (one of %r)"
                % (card, self.cards)
            )
        self.player.choice = None
        deck = self.target.deck
        if card in deck:
            deck.remove(card)
            deck.append(card)  # top = next draw
        for action in self._callback:
            self.source.game.trigger(
                self.source, [action], [self.target, self.cards, card]
            )
        self.callback = self._callback
        self.trigger_choice_callback()


class _TimesShuffled(LazyNum):
    """Number of cards the source's controller has shuffled into their own deck
    this game (defaults to 0 on a fresh Player — never raises). Used by both
    Knockback (damage) and Underbrush Tracker (cost reduction)."""

    def evaluate(self, source):
        return self.num(getattr(source.controller, "_tlc_times_shuffled", 0))


class _OpuFanOfKnives(TargetedAction):
    """Opu the Unseen — cast Fan of Knives (EX1_129). Routed through the
    controller's hero as the cast source so it fires correctly from the
    Deathrattle too (CastSpell bails when its source is a dead minion, which
    Opu is by the time its deathrattle resolves)."""

    TARGET = ActionArg()

    def do(self, source, target):
        hero = source.controller.hero
        source.game.cheat_action(hero, [CastSpell("EX1_129")])


##
# Minions


class TLC_514:
    """Merchant of Legend"""

    # Battlecry: Discover a Legendary minion. Shuffle the other two into your
    # deck.
    play = Discover(CONTROLLER, RandomLegendaryMinion()).then(
        _MerchantOfLegend(Discover.TARGET, Discover.CARDS, Discover.CARD)
    )


class TLC_516:
    """Neferset Weaponsmith"""

    # Battlecry: Get a random weapon from another class. Combo: Give it +2
    # Attack. (Data omits the COMBO GameTag, so flag it here to enable the
    # combo script.)
    tags = {GameTag.COMBO: 1}
    play = _NeferyaWeaponsmith(CONTROLLER)
    combo = _NeferyaWeaponsmithCombo(CONTROLLER)


class TLC_520:
    """Underbrush Tracker"""

    # Rush. Costs (1) less for each time you've shuffled cards into your deck.
    cost_mod = -_TimesShuffled()


class TLC_521:
    """Eyes in the Sky"""

    # Battlecry: Look at 3 cards in your enemy's deck. Pick one to put on top.
    play = _EyesInTheSkyPeek(OPPONENT)


class TLC_522:
    """Opu the Unseen"""

    # Battlecry, Combo, and Deathrattle: Cast 'Fan of Knives'.
    # Fan of Knives (EX1_129): deal 1 damage to all enemy minions, draw a card.
    play = _OpuFanOfKnives(CONTROLLER)
    combo = _OpuFanOfKnives(CONTROLLER)
    deathrattle = _OpuFanOfKnives(CONTROLLER)


##
# Spells


class TLC_513(QuestRewardProtect):
    """Lie in Wait"""

    # Quest: Shuffle cards into your deck, 5 times. Reward: Master Dusk.
    # The reward summons the Master Dusk hero (replacing the hero + hero power
    # from data) and resolves its battlecry directly — Summon does not fire a
    # hero card's battlecry the way Play does, so we run the effects here.
    progress_total = 5
    quest = Shuffle(CONTROLLER).after(AddProgress(SELF, Shuffle.CARD))
    reward = (
        Summon(CONTROLLER, "TLC_513t"),
        Summon(CONTROLLER, "TLC_513t2") * 2,
        Buff(CONTROLLER, "TLC_513e2"),
    )


class TLC_513t:
    """Master Dusk"""

    # Battlecry: Summon two 3/3 Ninjas with Stealth. Your Ninjas now shuffle
    # back into your deck when they die. (Battlecry resolved by the Lie in Wait
    # reward; this play is the fallback if Master Dusk is ever played directly.)
    play = (
        Summon(CONTROLLER, "TLC_513t2") * 2,
        Buff(CONTROLLER, "TLC_513e2"),
    )


class TLC_513t2:
    """Tortollan Ninja"""

    # Summoned When Drawn. Stealth. (3/3 Ninja — stats + keywords in data.)
    draw = Summon(CONTROLLER, SELF)


class TLC_513e2:
    """Master Dusk Reshuffle Player Enchant"""

    # When a friendly Tortollan Ninja dies, shuffle a copy into your deck.
    events = Death(FRIENDLY + ID("TLC_513t2")).after(
        Shuffle(CONTROLLER, ExactCopy(Death.ENTITY))
    )


class TLC_515:
    """Cultist Map"""

    # Discover a card from your deck. If you play it this turn, also pick one of
    # the others.
    play = _CultistMapDiscoverDeck(CONTROLLER)


class TLC_517:
    """Knockback"""

    # Deal $@ damage to a minion (improved for each time you've shuffled cards
    # into your deck).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, _TimesShuffled())


class TLC_518:
    """Interrogation"""

    # Shuffle three 3/3 Ninjas with Stealth into your deck that are Summoned
    # When Drawn. (Reuses the Tortollan Ninja token TLC_513t2.)
    play = Shuffle(CONTROLLER, "TLC_513t2") * 3


class TLC_519:
    """Ambush Predators"""

    # Summon a 1/1 Spitter with Stealth and Poisonous. Kindred: Do it again.
    play = (
        Summon(CONTROLLER, "TLC_519t"),
        Kindred() & Summon(CONTROLLER, "TLC_519t"),
    )
