from ..utils import *

from ..delve_into_deepholm._bonus import roll_bonus_effects


##
# Custom actions / helpers


class _GiveBonusEffects(TargetedAction):
    """Give `target` `amount` random Bonus Effects (the eight keyword pool)."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        tags = roll_bonus_effects(source.game.random, amount)
        source.game.cheat_action(source, [SetTags(target, tags)])


class _GolakkaSummon(TargetedAction):
    """Dive the Golakka Depths repeatable-quest body.

    Each Murloc you summon first gets the accumulated +N/+N (one stack per
    completed quest), then counts toward the next batch of 6. On the 6th
    Murloc since the last completion the stack grows by one. The quest never
    `finishes` (progress_total stays 0) so the engine never destroys it.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        bonus = getattr(player, "_golakka_bonus", 0)
        if bonus:
            source.game.cheat_action(
                source, [Buff(target, "TLC_426e2", atk=bonus, max_health=bonus)]
            )
        count = getattr(player, "_golakka_count", 0) + 1
        if count >= 6:
            count = 0
            player._golakka_bonus = bonus + 1
        player._golakka_count = count


class _IdoStamp(TargetedAction):
    """Remember the just-given Threshfleet token on Ido so the deathrattle can
    clean it up when Ido leaves play."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        source._ido_token = card


class _IdoRemove(TargetedAction):
    """Ido of the Threshfleet: when Ido leaves play, remove the generated
    Threshfleet token still sitting in hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        token = getattr(source, "_ido_token", None)
        if token is not None and token.zone == Zone.HAND:
            token.discard()
        source._ido_token = None


class _ReadyTheFleet(TargetedAction):
    """Ready the Fleet: buff `target` +1/+2 and every other friendly minion
    that shares a minion type with it."""

    TARGET = ActionArg()

    def do(self, source, target):
        races = set(getattr(target, "races", []) or [])
        recipients = [target]
        for m in source.controller.field:
            if m is target:
                continue
            if races & set(getattr(m, "races", []) or []):
                recipients.append(m)
        for m in recipients:
            source.game.cheat_action(source, [Buff(m, "TLC_441e2")])


class _SubmergedMap(TargetedAction):
    """Submerged Map: Discover one of 3 random Murlocs; give the chosen one,
    stash the other two on the player, and arm the TLC_442e watcher so that
    playing the chosen Murloc this turn fires a second pick."""

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        picker = RandomMurloc() * 3
        return [picker.evaluate(source)]

    def do(self, source, target, cards):
        self.cards = cards
        player = source.controller
        player.choice = self
        self.player = player
        self.source = source
        self.target = target
        self.min_count = 1
        self.max_count = 1
        source.game.manager.targeted_action(self, source, target, cards)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        self.player.discovers_this_game += 1
        self.player.discovers_this_turn += 1
        others = [c.id for c in self.cards if c is not card]
        given = self.player.give(card.id)
        self.player._submerged_others = others
        self.player._submerged_card = given
        self.source.game.cheat_action(self.source, [Buff(self.player, "TLC_442e")])
        self.trigger_choice_callback()


class _ConsumeMurlocCost(TargetedAction):
    """Hot Spring Glider cost rider: when a Murloc OTHER than the Glider itself
    is played, the discount is spent — remove the enchant. (Glider is itself a
    Murloc, so its own play must not consume the buff.)"""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, played):
        if played is getattr(source, "creator", None):
            return
        source.game.cheat_action(source, [Destroy(source)])


class _ConsumeMurlocDS(TargetedAction):
    """Hot Spring Glider Kindred rider: give the next Murloc (other than the
    Glider itself) Divine Shield, then remove the enchant."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, played):
        if played is getattr(source, "creator", None):
            return
        source.game.cheat_action(
            source, [SetTag(played, GameTag.DIVINE_SHIELD), Destroy(source)]
        )


class _SubmergedSecondPick(TargetedAction):
    """Deferred half of Submerged Map: when the stamped Murloc is played this
    turn, offer a choice between the two unchosen Murlocs."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, played):
        player = source.controller
        stamped = getattr(player, "_submerged_card", None)
        if played is not stamped:
            return
        ids = getattr(player, "_submerged_others", None) or []
        player._submerged_others = None
        player._submerged_card = None
        if ids:
            cards = [player.card(cid, source=source) for cid in ids]
            source.game.cheat_action(source, [GenericChoice(player, cards)])
        source.game.cheat_action(source, [Destroy(source)])


##
# Minions


class TLC_240:
    """Tyrannogill"""

    # Rush. Deathrattle: Summon three 2/1 Murlocs. Give them each a random
    # Bonus Effect.
    deathrattle = (
        Summon(CONTROLLER, "TLC_240t").then(_GiveBonusEffects(Summon.CARD, 1)) * 3
    )


class TLC_240t:
    """Dinoloc"""


class TLC_241:
    """Ido of the Threshfleet"""

    # While this is alive, you get a 2-Cost Holy spell that gives a minion
    # +2/+2 and Divine Shield.
    # The "remove the token when Ido leaves play" cleanup is modeled as a
    # deathrattle, but TLC_241 carries no DEATHRATTLE tag in data, so it must
    # be set explicitly or the engine never fires the cleanup.
    tags = {GameTag.DEATHRATTLE: True}
    play = Give(CONTROLLER, "TLC_241t").then(_IdoStamp(SELF, Give.CARD))
    deathrattle = _IdoRemove(SELF)


class TLC_241t:
    """Call the Threshfleet!"""

    # Give a minion +2/+2 and Divine Shield.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "TLC_241e"), GiveDivineShield(TARGET)


TLC_241e = buff(+2, +2)


class TLC_428:
    """Hot Spring Glider"""

    # Battlecry: Your next Murloc costs (1) less.
    # Kindred: And gains Divine Shield.
    play = Buff(CONTROLLER, "TLC_428e"), Kindred() & Buff(CONTROLLER, "TLC_428e2")


class TLC_428e:
    # Your next Murloc this turn costs (1) less.
    update = Refresh(FRIENDLY_HAND + MURLOC, {GameTag.COST: -1})
    events = (
        Play(CONTROLLER, MURLOC).after(_ConsumeMurlocCost(SELF, Play.CARD)),
        OWN_TURN_END.on(Destroy(SELF)),
    )


@custom_card
class TLC_428e2:
    # Kindred rider: the next Murloc you play this turn gains Divine Shield.
    tags = {
        GameTag.CARDNAME: "Hot Spring Glider",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = (
        Play(CONTROLLER, MURLOC).after(_ConsumeMurlocDS(SELF, Play.CARD)),
        OWN_TURN_END.on(Destroy(SELF)),
    )


class TLC_430:
    """Creature of the Sacred Cave"""

    # At the end of your turn, recast a random Holy spell you cast this turn
    # (targets this if possible).
    events = OWN_TURN_END.on(
        CastSpellTargetsSelfIfPossible(
            Copy(RANDOM(CARDS_PLAYED_THIS_TURN + SPELL + HOLY))
        )
    )


class TLC_438:
    """Violet Treasuregill"""

    # Battlecry: Cast a random spell from your deck that costs (2) or less
    # (targets this if possible).
    play = Find(FRIENDLY_DECK + SPELL + (COST <= 2)) & CastSpellTargetsSelfIfPossible(
        RANDOM(FRIENDLY_DECK + SPELL + (COST <= 2))
    )


##
# Spells


class TLC_426:
    """Dive the Golakka Depths"""

    # Repeatable Quest: Summon 6 Murlocs. Reward: Murlocs you summon gain
    # +1/+1. (Never-finishing quest that ticks every summon; see
    # _GolakkaSummon for the repeatable/stacking semantics.)
    quest = Summon(CONTROLLER, MURLOC).after(_GolakkaSummon(Summon.CARD))


class TLC_441:
    """Ready the Fleet"""

    # Give +1/+2 to a friendly minion and your other minions that share a
    # type with it.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _ReadyTheFleet(TARGET)


TLC_441e2 = buff(+1, +2)


class TLC_442:
    """Submerged Map"""

    # Discover a Murloc. If you play it this turn, also pick one of the others.
    play = _SubmergedMap(CONTROLLER)


class TLC_442e:
    """Submerged Map Player Enchant"""

    # If you play the Discovered Murloc this turn, also pick one of the others.
    events = (
        Play(OWNER, MURLOC).after(_SubmergedSecondPick(OWNER, Play.CARD)),
        OWN_TURN_END.on(Destroy(SELF)),
    )


class TLC_444:
    """Story of Galvadon"""

    # Give a minion three random Bonus Effects.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _GiveBonusEffects(TARGET, 3)


class TLC_477:
    """Threshrider's Blessing"""

    # Give a friendly minion +4/+4 and "Deathrattle: Summon a random 4-Cost
    # minion."
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "TLC_477e")


class TLC_477e:
    # +4/+4 and Deathrattle: Summon a random 4-Cost minion.
    tags = {GameTag.ATK: 4, GameTag.HEALTH: 4, GameTag.DEATHRATTLE: True}
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=4))


##
# The Lost City of Un'Goro mini-set (Dinosaurs, DINO_)


class _HatchTick(TargetedAction):
    """Hatching Ceremony timer. The spell is cast during your turn, so the
    first OWN_TURN_END belongs to THIS turn and is skipped (counter starts at
    1). At the next OWN_TURN_END (your next turn) the counter hits 0 — buff
    every friendly minion +2/+2, then remove the timer enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        left = getattr(target, "_hatching_turns_left", 0) - 1
        target._hatching_turns_left = left
        if left <= 0:
            for minion in list(source.controller.field):
                source.game.cheat_action(source, [Buff(minion, "DINO_405e")])
            source.game.cheat_action(source, [Destroy(source)])


class DINO_404:
    """Firegill"""

    # Kindred: Give your other minions Rush.
    play = Kindred() & GiveRush(FRIENDLY_MINIONS - SELF)


class DINO_405:
    """Hatching Ceremony"""

    # At the end of your next turn, give your minions +2/+2.
    play = Buff(CONTROLLER, "DINO_405e2")


@custom_card
class DINO_405e2:
    # Engine-internal timer: fires at the end of the caster's NEXT turn.
    tags = {
        GameTag.CARDNAME: "Hatching Ceremony",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }

    def apply(self, target):
        # Start at 2 so the first OWN_TURN_END (this turn) decrements to 1,
        # and the next OWN_TURN_END (your next turn) decrements to 0 and fires.
        target._hatching_turns_left = 2

    events = OWN_TURN_END.on(_HatchTick(OWNER))


# DINO_405e "Hatched" exists in data (name + cardtype only); add the +2/+2.
DINO_405e = buff(+2, +2)


class DINO_424:
    """Hero's Welcome"""

    # Discover a Legendary minion to summon. Set its stats to 10/10.
    play = Discover(CONTROLLER, RandomLegendaryMinion()).then(
        Summon(CONTROLLER, Discover.CARD).then(Buff(Summon.CARD, "DINO_424e"))
    )


# DINO_424e "Hero's Celebration" exists in data (name + cardtype only).
# "Set its stats to 10/10" — fixed-value enchant (mirrors the set-cost pattern).
class DINO_424e:
    atk = lambda self, i: 10
    max_health = lambda self, i: 10
