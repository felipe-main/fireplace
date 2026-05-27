from ..utils import *

from hearthstone.enums import Race as _Race
from ...actions import IntArg


##
# Custom actions and helpers


class _CopyOneOfEachRaceFromHand(TargetedAction):
    """Rock Master Voone — for each minion type represented in the
    controller's hand, ExactCopy one minion of that race and add it back
    to the hand. Iterates races deterministically so the picked card per
    race is the first minion of that race in the hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen_races = set()
        chosen = []
        for card in list(ctrl.hand):
            if card.type != CardType.MINION:
                continue
            for race in getattr(card, "races", []):
                if race in seen_races or race == _Race.INVALID:
                    continue
                seen_races.add(race)
                chosen.append(card)
                break
        for card in chosen:
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            # ExactCopy is a LazyValue (expects Selector); when we already
            # have the entity, drive the copy directly via .copy().
            copy = ExactCopy(card).copy(source, card)
            copy.controller = ctrl
            source.game.cheat_action(source, [Give(ctrl, copy)])


class _RazorfenRockstarBoost(TargetedAction):
    """Razorfen Rockstar — after the controller gains Armor, give 2
    additional Armor. Wrapped in a custom action so we can self-guard
    against recursive re-entry (the bonus armor gain would otherwise
    re-trigger this listener forever)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if getattr(ctrl, "_razorfen_armoring", False):
            return
        ctrl._razorfen_armoring = True
        try:
            source.game.cheat_action(source, [GainArmor(FRIENDLY_HERO, 2)])
        finally:
            ctrl._razorfen_armoring = False


class _PlayLastRiff(TargetedAction):
    """Finale on Riff spells — replay the controller's last-played Riff
    spell (if any). Reads Player.last_riff_played which is stamped by
    each Riff's play action."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        last = getattr(ctrl, "last_riff_played", None)
        if not last:
            return
        # Re-entry guard so Finale's replay can't itself call Finale.
        if getattr(ctrl, "_riff_replaying", False):
            return
        ctrl._riff_replaying = True
        try:
            source.game.cheat_action(source, [CastSpell(last)])
        finally:
            ctrl._riff_replaying = False


class _StampRiff(TargetedAction):
    TARGET = ActionArg()

    def __init__(self, target, riff_id):
        super().__init__(target)
        self._riff_id = riff_id

    def do(self, source, target):
        # Only stamp on the original cast, not the Finale-triggered replay,
        # to avoid surprising "last riff = the one we just replayed" loops.
        if getattr(target, "_riff_replaying", False):
            return
        target.last_riff_played = self._riff_id


class _BlackrockNRollBuff(TargetedAction):
    """Blackrock 'n' Roll — give all minions in the controller's deck
    Attack/Health equal to their printed cost via a per-card buff."""

    TARGET = ActionArg()

    def do(self, source, target):
        for card in list(target.deck):
            if card.type != CardType.MINION:
                continue
            cost = max(0, card.cost)
            if cost <= 0:
                continue
            source.game.cheat_action(
                source,
                [Buff(card, "ETC_417e", atk=cost, max_health=cost)],
            )


class _CountMinionTypesPlayed(LazyNum):
    """LazyValue resolving to the number of distinct minion types the
    controller has played this game (read from
    Player.minion_types_played, a set of Race ints maintained by
    Play.do via a per-card or per-game hook). If the engine doesn't
    track it explicitly, we derive on demand from cards_played_this_game."""

    def evaluate(self, source):
        ctrl = source.controller
        seen = set()
        for card in ctrl.cards_played_this_game:
            if card.type != CardType.MINION:
                continue
            for race in getattr(card, "races", []):
                if race != _Race.INVALID:
                    seen.add(int(race))
        return len(seen)


class _CountMinionTypesOnBoard(LazyNum):
    def evaluate(self, source):
        ctrl = source.controller
        seen = set()
        for m in ctrl.field:
            for race in getattr(m, "races", []):
                if race != _Race.INVALID:
                    seen.add(int(race))
        return len(seen)


class _KodoArmorListener(TargetedAction):
    """While Kodohide Drumkit is equipped, count armor gains so its
    deathrattle can scale damage."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        # source is the weapon itself (the listener host); bump our
        # per-weapon counter by the GainArmor amount carried in event_args.
        if source.zone != Zone.PLAY:
            return
        if amount <= 0:
            return
        source._armor_gained_while_equipped = (
            getattr(source, "_armor_gained_while_equipped", 0) + amount
        )


class _KodoDeathrattleHit(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        amt = getattr(source, "_armor_gained_while_equipped", 0)
        if amt <= 0:
            return
        source.game.cheat_action(source, [Hit(ALL_MINIONS, amt)])


##
# Minions


# Taunt. Battlecry: If you control no other minions, gain +2/+2 and Rush.
class ETC_035:
    """Drum Soloist"""

    # EMPTY_BOARD counts FRIENDLY_MINIONS which includes SELF at battlecry
    # time; subtract SELF to check "no *other* minions".
    play = (Count(FRIENDLY_MINIONS - SELF) == 0) & (
        Buff(SELF, "ETC_035e"),
        GiveRush(SELF),
    )


# Battlecry: Copy a minion of each minion type in your hand.
class ETC_121:
    """Rock Master Voone"""

    play = _CopyOneOfEachRaceFromHand(SELF)


# After you gain Armor, gain 2 more.
class ETC_355:
    """Razorfen Rockstar"""

    events = GainArmor(FRIENDLY_HERO).on(_RazorfenRockstarBoost(SELF))


# Rush. Battlecry: Gain +1/+1 for each minion type you've played this game.
class ETC_408:
    """Power Slider"""

    play = Buff(SELF, "ETC_408e", atk=_CountMinionTypesPlayed(),
                max_health=_CountMinionTypesPlayed())


##
# Spells


# Give your hero +2 Attack this turn. Gain 2 Armor. Finale: Play your last Riff.
class ETC_363:
    """Verse Riff"""

    play = (
        Buff(FRIENDLY_HERO, "ETC_363e"),
        GainArmor(FRIENDLY_HERO, 2),
        FINALE & _PlayLastRiff(CONTROLLER),
        _StampRiff(CONTROLLER, "ETC_363"),
    )


# Draw a minion. Give it +2/+2. Finale: Play your last Riff.
class _DrawMinionAndBuff(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone
        minions = [c for c in list(target.deck) if c.type == CardType.MINION]
        if not minions:
            return
        pick = source.game.random.choice(minions)
        if len(target.hand) >= target.max_hand_size:
            pick.discard()
            return
        pick.zone = Zone.HAND
        source.game.cheat_action(source, [Buff(pick, "ETC_364e")])


class ETC_364:
    """Chorus Riff"""

    play = (
        _DrawMinionAndBuff(CONTROLLER),
        FINALE & _PlayLastRiff(CONTROLLER),
        _StampRiff(CONTROLLER, "ETC_364"),
    )


# Summon a 3/4 with Taunt and a 4/3 with Rush. Finale: Play your last Riff.
class ETC_365:
    """Bridge Riff"""

    play = (
        Summon(CONTROLLER, "ETC_365t"),
        Summon(CONTROLLER, "ETC_365t2"),
        FINALE & _PlayLastRiff(CONTROLLER),
        _StampRiff(CONTROLLER, "ETC_365"),
    )


class ETC_365t:
    """Tough Rocker"""

    # Taunt; 3/4 stats from data.


class ETC_365t2:
    """Hyped Rocker"""

    # Rush; 4/3 stats from data.


# Draw a card. Repeat for each minion type you control.
class ETC_372:
    """Roaring Applause"""

    play = Draw(CONTROLLER) * (_CountMinionTypesOnBoard() + 1)


# Give all minions in your deck Attack and Health equal to their Cost.
class ETC_417:
    """Blackrock 'n' Roll"""

    play = _BlackrockNRollBuff(CONTROLLER)


##
# Weapons


# Deathrattle: Deal @ damage to all minions.
# (Gain Armor while equipped to improve!)
class ETC_520:
    """Kodohide Drumkit"""

    # Armor-gain listener bumps the per-weapon counter; deathrattle reads
    # it and hits all minions. The armor listener fires on every GainArmor
    # event but is gated to the equipped weapon's lifetime.
    events = GainArmor(FRIENDLY_HERO).on(
        _KodoArmorListener(SELF, GainArmor.AMOUNT)
    )
    deathrattle = _KodoDeathrattleHit(SELF)


##
# Engine-internal enchantments — register the ones the data XML doesn't carry.


@custom_card
class ETC_355e:
    tags = {
        GameTag.CARDNAME: "Razorfen Rockstar",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ETC_520e:
    tags = {
        GameTag.CARDNAME: "Kodohide Drumkit",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


# Buff stat tags missing from data XML.


class ETC_035e:
    # In-data buff "Drum Solo" — +2/+2 not parsed from data.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class ETC_363e:
    # +2 Attack this turn. The TEMPORARY tag in data auto-expires at end
    # of turn; only the +2 ATK needs to be supplied.
    tags = {GameTag.ATK: 2}


class ETC_364e:
    # +2/+2 to a drawn minion. Stats not parsed from data.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class ETC_408e:
    # +N/+N stats supplied at Buff() time (atk/max_health kwargs).
    pass


class ETC_417e:
    # Stats supplied at Buff() time via atk/max_health kwargs.
    pass
