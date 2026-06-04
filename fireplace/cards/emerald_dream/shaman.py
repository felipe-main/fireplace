from ..utils import *


##
# Custom actions / helpers


class _PlayTopOfDeck(TargetedAction):
    """Ohn'ahra — at end of turn, play the top N cards from your deck for
    free.

    Each card is routed through the engine's *real* ``game.play_card`` pipeline
    (the same entry point a human play uses), so the full Play machinery fires:
    OWN_MINION_PLAY / play-broadcast events, Combo, Outcast, Rewind, Colossal
    limb-summons, Miniaturize/Gigantify tokens, and targeted battlecries. The
    card is briefly moved into HAND (so cost-mods, hand-position snapshots and
    ``requires_target`` all evaluate in their normal context) and its Cost is
    pinned to 0 for the duration of the play (Ohn'ahra plays them for free).

    Targeting mirrors ``CastSpellTargetsEnemiesIfPossible``: if the card needs
    a target, prefer a random enemy among its valid targets, else any valid
    target. A card that needs a target but has none available fizzles its
    effect (matching the real game — Ohn'ahra can't pick targets that don't
    exist), but the body still lands on the board for minions.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def _auto_target(self, source, card):
        # Only pick a target when the card's play action actually requires one.
        if not card.requires_target():
            return None
        targets = card.play_targets
        if not targets:
            return None
        enemy = [t for t in targets if t.controller == source.controller.opponent]
        pool = enemy or targets
        return source.game.random.choice(pool)

    def do(self, source, target, amount):
        ctrl = source.controller
        # deck[-1] is the top (next draw). Each play mutates the deck, so we
        # re-read the top each iteration.
        for _ in range(amount):
            if not ctrl.deck:
                break
            card = ctrl.deck[-1]
            if card.type == CardType.MINION and len(ctrl.field) >= 7:
                # Board full — a minion can't be played; leave it (and the rest)
                # in the deck, just as the real game stops here.
                break
            # Move into hand so the real Play pipeline sees a normal hand card
            # (cost-mods, hand snapshots, requires_target all key off HAND).
            card.zone = Zone.HAND
            # Pin the cost to 0 for the free play. `cost` clamps to max(0, ...),
            # so a large negative base override guarantees 0 regardless of any
            # in-hand cost-mod, and is undone right after the play resolves.
            saved_cost = getattr(card, "_cost", 0)
            card._cost = -1000
            play_target = self._auto_target(source, card)
            source.game.play_card(card, play_target, None, None)
            # Restore the base-cost override on the off chance the card is still
            # reachable (e.g. a minion bounced back to hand by its own effect).
            card._cost = saved_cost


class _BuffTopDeckMinions(TargetedAction):
    """Beanstalk Brute — give +4/+4 to the top 3 minions in your deck. "Top"
    is the draw order: deck[-1] is drawn first. We walk from the top down and
    buff the first 3 minions encountered."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        minions = [c for c in reversed(ctrl.deck) if c.type == CardType.MINION][:3]
        for minion in minions:
            source.game.cheat_action(source, [Buff(minion, "EDR_230e")])


class _ResurrectExpensiveDifferent(TargetedAction):
    """Merithra — resurrect all *different* friendly minions that cost (8) or
    more. "Different" = unique by card id; one copy of each distinct dead
    8+-cost friendly minion is summoned."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen = set()
        to_summon = []
        for card in ctrl.graveyard:
            if card.type != CardType.MINION:
                continue
            if getattr(card, "discarded", False):
                continue
            if (card.data.cost or 0) < 8:
                continue
            if card.id in seen:
                continue
            seen.add(card.id)
            to_summon.append(card.id)
        for cid in to_summon:
            if len(ctrl.field) >= 7:
                break
            source.game.cheat_action(source, [Summon(ctrl, cid)])


class _LockDrawnCard(TargetedAction):
    """Emerald Bounty — stamp a freshly drawn card with the 2-turn play-lock.

    The engine's `unplayable_next_turn` counter (card.py:756) is decremented
    once at the controller's begin_turn (game.py:593). "Can't play for 2 turns"
    means the card is locked for the controller's next two turns, so we set the
    counter to 3:
      drawn on turn T (no tick)         -> locked
      controller turn T+1 begin: 3 -> 2 -> locked (turn 1 of the 2-turn lock)
      controller turn T+2 begin: 2 -> 1 -> locked (turn 2 of the 2-turn lock)
      controller turn T+3 begin: 1 -> 0 -> playable
    The cosmetic "Still Growing" enchant (EDR_234e2) still rides along for the
    card-text marker.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        if hasattr(target, "unplayable_next_turn"):
            target.unplayable_next_turn = 3


class _TyphoonShuffle(TargetedAction):
    """Typhoon — each minion (both boards) gets shuffled into a random
    player's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        minions = []
        for player in game.players:
            minions.extend(list(player.field))
        for minion in minions:
            dest = game.random.choice(game.players)
            game.cheat_action(source, [Shuffle(dest, minion)])


##
# Minions


class EDR_031:
    """Ohn'ahra"""

    # At the end of your turn, play the top 3 cards from your deck.
    events = OWN_TURN_END.on(_PlayTopOfDeck(SELF, 3))


class EDR_230:
    """Beanstalk Brute"""

    # Battlecry: Give +4/+4 to the top 3 minions in your deck.
    play = _BuffTopDeckMinions(SELF)


class EDR_238:
    """Merithra"""

    # Battlecry: Resurrect all different friendly minions that cost (8) or more.
    play = _ResurrectExpensiveDifferent(SELF)


class EDR_477:
    """Glowroot Lure"""

    # Taunt. Costs (1) less for each time you used your Hero Power this game.
    cost_mod = -Attr(CONTROLLER, "times_hero_power_used_this_game")


class EDR_518:
    """Living Garden"""

    # Battlecry: Imbue your Hero Power. Reduce the Cost of a minion in your
    # hand by (1).
    play = (
        Imbue(CONTROLLER),
        Buff(RANDOM(FRIENDLY_HAND + MINION), "EDR_518e"),
    )


class EDR_529:
    """Plucky Podling"""

    # If this would transform into a minion, it transforms into one that
    # costs (2) more.
    #
    # Wired engine-side in Morph.do (actions.py): when a transform effect would
    # morph this card (EDR_529) into a minion, the would-be minion is replaced
    # with a random minion costing 2 more — same id-check approach as Baroness
    # Vashj's transform-interception branch.


##
# Spells


class EDR_231:
    """Aspect's Embrace"""

    # Restore #4 Health. Draw a card. Imbue your Hero Power.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = (
        Heal(TARGET, 4),
        Draw(CONTROLLER),
        Imbue(CONTROLLER),
    )


class EDR_232:
    """Typhoon"""

    # Each minion gets shuffled into a random player's deck.
    play = _TyphoonShuffle(SELF)


class EDR_233:
    """Spirits of the Forest"""

    # Choose One - Summon three 2/3 Wolves with Taunt; or Summon two 4/3
    # Falcons with Windfury.
    choose = ("EDR_233a", "EDR_233b")
    play = ChooseBoth(CONTROLLER) & (
        Summon(CONTROLLER, "EDR_233t1") * 3,
        Summon(CONTROLLER, "EDR_233t2") * 2,
    )


class EDR_233a:
    """Wolf's Strength"""

    # Summon three 2/3 Wolves with Taunt.
    play = Summon(CONTROLLER, "EDR_233t1") * 3


class EDR_233b:
    """Falcon's Dexterity"""

    # Summon two 4/3 Falcons with Windfury.
    play = Summon(CONTROLLER, "EDR_233t2") * 2


class EDR_234:
    """Emerald Bounty"""

    # Draw 2 cards. You can't play them for 2 turns.
    # The 2-turn play-lock is modelled via the engine's `unplayable_next_turn`
    # counter (set to 3 = locked for the controller's next two turns; see
    # _LockDrawnCard). The "Still Growing" enchant (EDR_234e2) is the card-text
    # marker.
    play = (
        Draw(CONTROLLER)
        .then(Buff(Draw.CARD, "EDR_234e2"))
        .then(_LockDrawnCard(Draw.CARD))
    ) * 2


##
# Tokens


@custom_card
class EDR_233t1:
    # 2/3 Wolf with Taunt (Spirits of the Forest — Wolf's Strength). Not in
    # card data, so registered here with explicit stats + Taunt.
    tags = {
        GameTag.CARDNAME: "Wolf",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.CLASS: CardClass.SHAMAN,
        GameTag.COST: 2,
        GameTag.ATK: 2,
        GameTag.HEALTH: 3,
        GameTag.TAUNT: True,
        GameTag.CARDRACE: Race.BEAST,
    }


class EDR_233t2:
    """Spirit Falcon"""

    # 4/3 Falcon with Windfury. Stats + Windfury live in data.


##
# Enchantments


@custom_card
class EDR_518e:
    # Living Garden — reduce the Cost of a minion in hand by (1).
    tags = {
        GameTag.CARDNAME: "Living Garden",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class EDR_230e:
    # Beanstalk Brute — Enchanted: +4/+4 (data enchant).
    tags = {GameTag.ATK: 4, GameTag.HEALTH: 4}


class EDR_234e2:
    """Still Growing"""

    # Emerald Bounty — "Can't be played for 2 turns" (data enchant). The
    # lockout is cosmetic-only in this engine (no play-lock lifetime).


##
# Firelands mini-set (FIR_ prefix) — SHAMAN


class FIR_778:
    """Avatar of Destruction"""

    # Taunt. Deathrattle: Deal 9 damage to all enemy minions.
    deathrattle = Hit(ENEMY_MINIONS, 9)


class FIR_923:
    """Flames of the Firelord"""

    # Deal 4 damage to a random enemy minion. If you're holding a card that
    # costs (8) or more, deal 8 instead.
    play = Find(FRIENDLY_HAND + (COST >= 8)) & Hit(RANDOM_ENEMY_MINION, 8) | Hit(
        RANDOM_ENEMY_MINION, 4
    )


class FIR_927:
    """Emberscarred Whelp"""

    # Battlecry: Discover a 5-Cost card. Gain 1 Mana Crystal next turn only.
    # The "next turn only" Mana rider is applied first: a Discover opens a
    # choice that halts the action queue, so any action queued *after* it in a
    # flat tuple is dropped (see CLAUDE.md "Choice sequencing"). The Mana buff
    # doesn't depend on the Discover, so it runs cleanly before it.
    play = (
        Buff(FRIENDLY_HERO, "FIR_927e"),
        DISCOVER(RandomCollectible(cost=5)),
    )


##
# Firelands enchantments


@custom_card
class FIR_927e:
    # Emberscarred Whelp — gain 1 Mana Crystal next turn only. Not in card
    # data, so registered here. At the controller's next turn-begin it grants
    # +1 temporary Mana (spent that turn only), then tears itself down.
    tags = {
        GameTag.CARDNAME: "Emberscarred Whelp",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_BEGIN.on(ManaThisTurn(CONTROLLER, 1), Destroy(SELF))
