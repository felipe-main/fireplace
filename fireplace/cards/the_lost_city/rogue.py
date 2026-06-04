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
        # are no-ops and must not advance the counter). Credit the deck owner
        # only for shuffles THEY initiated ("each time YOU'VE shuffled cards
        # into your deck"): a shuffle driven by an opponent's effect (an enemy
        # curse seeding cards into your deck) must not bump your counter.
        added = len(target.deck) - before
        initiator = getattr(source, "controller", source)
        if added > 0 and initiator is target:
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
    """Cultist Map — Discover a card from the controller's own deck and draw the
    real copy out. If you play it this turn, also pick one of the other two deck
    cards shown (DiscoverPickOtherDraw stamps the drawn card and arms the
    one-turn watcher; the second pick is likewise a real deck draw)."""

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
                    DiscoverPickOtherDraw(SELF, Discover.CARDS, Discover.CARD)
                )
            ],
        )


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


class _WayOfTheShellDraw(TargetedAction):
    """Way of the Shell (Master Dusk hero power) — draw up to 2 cards from your
    deck that didn't start in your deck (generated / shuffled-in cards). Cards
    that were part of the opening decklist carry `_started_in_deck = True`
    (stamped at game setup in game.py); anything minted afterwards has it
    False, so those are the valid draw candidates."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # deck[-1] is the top of the deck; honour draw order (top first) so the
        # picks line up with what the player would naturally draw next.
        candidates = [
            c
            for c in reversed(list(ctrl.deck))
            if not getattr(c, "_started_in_deck", False)
        ]
        for card in candidates[:2]:
            source.game.cheat_action(source, [ForceDraw(card)])


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


class TLC_513hp:
    """Way of the Shell"""

    # Hero Power (equipped by the Master Dusk hero TLC_513t): Draw 2 cards that
    # didn't start in your deck. Hero powers fire their `activate` script (see
    # PlayHeroPower.get_actions("activate")), not `play`.
    activate = _WayOfTheShellDraw(CONTROLLER)


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
    #
    # The $@ magnitude carries a base floor of 1 (data TAG_SCRIPT_DATA_NUM_1 = 1),
    # improved by one for each card you've shuffled into your deck. So at 0
    # shuffles it still deals 1, and N shuffles deals 1 + N.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, _TimesShuffled() + 1)


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


##
# ============================================================================
# The Lost City of Un'Goro — MINI-SET (Dinosaurs, DINO_ prefix) — ROGUE
# ============================================================================


##
# Engine glue — track the last MINION each player played (for Mirrex), and
# keep any "Mirrex copy" cards sitting in a player's hand continuously
# re-synced to the *current* last-opponent-minion.
#
# Mirrex reads "the last minion your OPPONENT played", so each player records
# the last minion THEY played in `_dino_last_minion_played`; Mirrex (in your
# hand) copies its controller's opponent's value. We wrap Play.do once (the
# single chokepoint every play flows through) to (a) stamp the played minion
# and (b) refresh every Mirrex copy in the just-played player's opponent's
# hand. Refresh is also driven by `Hand.update` for the in-hand-from-turn-1
# / drawn-after-the-fact cases.

if not getattr(Play, "_dino_mirrex_patched", False):
    _dino_orig_play_do = Play.do

    def _dino_play_do(self, source, card, target=None, *args, **kwargs):
        result = _dino_orig_play_do(self, source, card, target, *args, **kwargs)
        try:
            player = card.controller
            if card.type == CardType.MINION:
                player._dino_last_minion_played = card.id
                # The card *they* just played is the opponent's "last minion"
                # from the other player's point of view — refresh that
                # player's Mirrex copies in hand.
                _dino_refresh_mirrex(player.opponent)
        except Exception:
            pass
        return result

    Play.do = _dino_play_do
    Play._dino_mirrex_patched = True


def _dino_refresh_mirrex(player):
    """Re-sync every Mirrex copy in `player`'s hand to a 3/3 copy of the last
    minion that player's OPPONENT played. A Mirrex copy is any hand card that
    still carries the `_mirrex` marker (set when the copy is minted, and
    re-stamped on every fresh copy so the chain keeps updating)."""
    if player is None:
        return
    # Re-entrancy guard: Morph below triggers an aura refresh, which re-runs
    # Mirrex's Hand.update -> this function. Without the guard the same entity
    # is morphed twice in one pass and the second _set_zone hits an empty zone
    # cache (utils.py remove ValueError).
    if getattr(player, "_mirrex_refreshing", False):
        return
    last_id = getattr(player.opponent, "_dino_last_minion_played", None)
    if not last_id:
        return
    from .. import db as _db

    if last_id not in _db:
        return
    player._mirrex_refreshing = True
    try:
        for entity in list(player.hand):
            if not getattr(entity, "_mirrex", False):
                continue
            # Only morph a card that is actually still in hand.
            if entity.zone != Zone.HAND:
                continue
            # Already showing this minion — nothing to do.
            if getattr(entity, "_mirrex_shows", None) == last_id:
                continue
            copy = player.card(last_id, source=entity)
            copy.controller = player
            copy._mirrex = True
            copy._mirrex_shows = last_id
            # DINO_407e2 "Crystalline" pins the copy to 3/4 at Cost 3; DINO_407e
            # "Reflecting" is the cosmetic defining enchant the real card carries
            # while in hand (tag-only — no stats, completes the display fidelity).
            player.game.cheat_action(
                entity,
                [Morph(entity, copy), Buff(copy, "DINO_407e2"),
                 Buff(copy, "DINO_407e")],
            )
    finally:
        player._mirrex_refreshing = False


class _MirrexHandUpdate(TargetedAction):
    """Hand.update driver for Mirrex (and its minted copies). Each aura refresh
    it re-syncs the copy to the last minion the opponent played. Mirrex itself
    carries the `_mirrex` marker via this action's first run."""

    TARGET = ActionArg()

    def do(self, source, target):
        # Mark the base Mirrex so the global refresher recognises it.
        source._mirrex = True
        _dino_refresh_mirrex(source.controller)


class DINO_407:
    """Mirrex, the Crystalline"""

    # While in your hand, this is a 3/4 copy of the last minion your opponent
    # played. (Engine model: a Hand.update + a Play.do hook continuously
    # morph this — and every copy it becomes — into a 3/4 clone of the
    # opponent's most-recently-played minion, re-syncing whenever the
    # opponent plays a new one. The DINO_407e2 "Crystalline" enchant pins the
    # copy's stats to 3/4.)
    class Hand:
        update = _MirrexHandUpdate(SELF)


class DINO_407e2:
    """Crystalline"""

    # Sets the copied minion's stats to 3/4 (Mirrex is always a 3/4 copy).
    atk = lambda self, i: 3
    max_health = lambda self, i: 4
    # Mirrex stays a 3-mana card even though it Morphs into the copied minion's
    # full card (which would otherwise inherit that minion's cost). Pinning cost
    # here keeps the in-hand copy at Mirrex's printed 3 mana — you can't cheat
    # out an expensive body for free. This enchant is only ever applied to the
    # Mirrex copy (see _dino_refresh_mirrex), so the cost pin is scoped to it.
    cost = lambda self, i: 3


##
# Weapon


class _CrystalTuskShuffleLeftmost(TargetedAction):
    """Crystal Tusk battlecry: shuffle the LEFT-most card in your hand into your
    deck. (deck-left = hand index 0; the weapon itself has already left the
    hand by the time its battlecry resolves.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        hand = list(ctrl.hand)
        if not hand:
            return
        leftmost = hand[0]
        source.game.cheat_action(source, [Shuffle(ctrl, leftmost)])


class DINO_408:
    """Crystal Tusk"""

    # Battlecry: Shuffle the left-most card in your hand into your deck.
    # Deathrattle: Draw 2 cards.
    play = _CrystalTuskShuffleLeftmost(CONTROLLER)
    deathrattle = Draw(CONTROLLER) * 2


##
# Costume Merchant


# The five "Mask" spells, one per OTHER class (Costume Merchant is Rogue, so
# all five qualify as "from another class").
_DINO_MASKS = ("DINO_402", "DINO_403", "DINO_428", "DINO_429", "DINO_432")


class _CostumeMerchantGetMask(TargetedAction):
    """Costume Merchant battlecry: get a random Mask from another class. When
    `combo` is True (subclass), the freshly-created Mask also gets a "costs
    (2) less" enchant stamped on it while it sits in hand."""

    TARGET = ActionArg()
    combo_buff = False

    def do(self, source, target):
        ctrl = source.controller
        before = set(ctrl.hand)
        source.game.cheat_action(source, [Give(ctrl, RandomID(*_DINO_MASKS))])
        new = [c for c in ctrl.hand if c not in before]
        if new and self.combo_buff:
            source.game.cheat_action(source, [Buff(new[0], "DINO_427e")])


class _CostumeMerchantGetMaskCombo(_CostumeMerchantGetMask):
    combo_buff = True


# "Costs (2) less" — Combo discount on the minted Mask. Not present in data,
# so register it as a custom enchant.
@custom_card
class DINO_427e:
    tags = {
        GameTag.CARDNAME: "Disguise Discount",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class DINO_427:
    """Costume Merchant"""

    # Battlecry: Get a random Mask from another class. Combo: It costs (2)
    # less. (Data already carries the COMBO GameTag, so `has_combo` is set;
    # the combo script supersedes play when a card was played first this turn
    # and adds the cost reduction on top of the base "get a Mask" effect.)
    play = _CostumeMerchantGetMask(CONTROLLER)
    combo = _CostumeMerchantGetMaskCombo(CONTROLLER)
