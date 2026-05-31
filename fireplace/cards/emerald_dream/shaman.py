from ..utils import *


##
# Custom actions / helpers


class _PlayTopOfDeck(TargetedAction):
    """Ohn'ahra — at end of turn, play the top N cards from your deck for
    free. Each card is played through the real play pipeline so battlecries /
    on-play hooks fire; spells auto-target an enemy when one is required."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        ctrl = source.controller
        # deck[-1] is the top (next draw). Snapshot before playing — each play
        # mutates the deck.
        for _ in range(amount):
            if not ctrl.deck:
                break
            card = ctrl.deck[-1]
            if card.type == CardType.SPELL:
                copy_zone_card = card
                copy_zone_card.zone = Zone.HAND
                source.game.cheat_action(
                    source, [CastSpellTargetsEnemiesIfPossible(copy_zone_card)]
                )
            elif card.type == CardType.MINION:
                if len(ctrl.field) >= 7:
                    # Board full — leave the rest in the deck.
                    break
                card.zone = Zone.HAND
                source.game.cheat_action(source, [Summon(ctrl, card)])
                if card.zone == Zone.PLAY and getattr(card, "has_battlecry", False):
                    source.game.cheat_action(source, [Battlecry(card, None)])
            else:
                # Weapons / heroes / locations: equip / replay.
                card.zone = Zone.HAND
                source.game.cheat_action(source, [Replay(card)])


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
    # NOTE: the transform-upgrade redirect is an engine-side Morph hook
    # (mirrors Baroness Vashj's REV_925 special-case) and is not wired for
    # EDR_529 in this engine. Shipped as the printed 1/1/2 body; the upgrade
    # rider is inert. See uncertainties.


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
    # NOTE: the "can't be played for 2 turns" lockout is not modelled (this
    # engine has no per-card play-lock lifetime). The draw is full-fidelity;
    # the drawn cards carry the cosmetic "Still Growing" marker.
    play = Draw(CONTROLLER).then(Buff(Draw.CARD, "EDR_234e2")) * 2


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
