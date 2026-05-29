"""Showdown in the Badlands — Rogue cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions


# Velarok Windblade reveals on the third foreign-class card played while
# it is in hand. Shared by the progress action and the in-hand cardtext.
_VELAROK_TARGET = 3


class _DartThrow(TargetedAction):
    """Dart Throw (WW_006): throw two 2-damage darts at random enemy
    minions, picked independently. If BOTH darts land on the SAME minion,
    the caster gets a Coin. Resolves each dart against a freshly-sampled
    random enemy minion so the "both hit the same one" condition is the
    real in-game probability — not a pre-picked single target."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        # First dart: pick a random LIVE enemy minion and hit it.
        live = list(player.opponent.field)
        if not live:
            return []
        first = source.game.random.choice(live)
        source.game.queue_actions(source, [Hit(first, 2)])
        # The first dart may have killed its target — flush deaths so the
        # board reflects only minions that are still alive before the
        # second dart re-picks.
        source.game.process_deaths()
        # Second dart: re-sample from whatever is still alive. A dead first
        # target is no longer in the field, so it cannot be picked again.
        live = list(player.opponent.field)
        if not live:
            return []
        second = source.game.random.choice(live)
        source.game.queue_actions(source, [Hit(second, 2)])
        # Coin only if a single minion absorbed BOTH darts. This is only
        # possible when the first dart did not kill its target and the
        # second dart re-picked that same (still-live) minion.
        if second is first:
            source.game.queue_actions(source, [Give(player, THE_COIN)])
        return []


class _VelarokProgress(TargetedAction):
    """Velarok Windblade (WW_364): while in hand, each time the controller
    plays a card from another class, tick the counter. On the third such
    card, transform into Velarok, the Deceiver (WW_364t)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target.zone != Zone.HAND:
            return []
        target._velarok_count = getattr(target, "_velarok_count", 0) + 1
        if target._velarok_count >= _VELAROK_TARGET:
            source.game.cheat_action(source, [Morph(target, "WW_364t")])
        return []


class _WishingWellReward(TargetedAction):
    """Wishing Well (WW_415): after the controller plays a Coin, get a
    random Legendary minion from another class and set its Cost to (1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        own_class = player.hero.card_class
        from ... import cards as card_module

        pool = [
            cid
            for cid in card_module.db.filter(
                collectible=True, type=CardType.MINION, rarity=Rarity.LEGENDARY
            )
            if card_module.db[cid].card_class not in (own_class, CardClass.NEUTRAL)
        ]
        if not pool:
            return []
        cid = source.game.random.choice(pool)
        if len(player.hand) >= player.max_hand_size:
            return []
        card = player.card(cid, source=source)
        card.zone = Zone.HAND
        card.cost = 1
        return [card]



# "From another class" as a list of CardClass values for RandomCard's
# card_class filter (matches a card if ANY of its classes is in the list).
# Excludes the controller's own hero class and the non-playable buckets
# (NEUTRAL / INVALID / DREAM / WHIZBANG), so the result is a real card
# from a *different* playable class.
_PLAYABLE_CLASSES = [
    CardClass.DEATHKNIGHT,
    CardClass.DRUID,
    CardClass.HUNTER,
    CardClass.MAGE,
    CardClass.PALADIN,
    CardClass.PRIEST,
    CardClass.ROGUE,
    CardClass.SHAMAN,
    CardClass.WARLOCK,
    CardClass.WARRIOR,
    CardClass.DEMONHUNTER,
]
FOREIGN_CLASS = FuncSelector(
    lambda entities, source: [
        cc
        for cc in _PLAYABLE_CLASSES
        if cc != getattr(source.controller.hero, "card_class", CardClass.INVALID)
    ]
)


##
# Spells


class WW_006:
    """Dart Throw"""

    # [x]Throw two $2 damage darts at random enemy minions. (If both hit
    # the same minion, get a Coin!)
    play = _DartThrow(CONTROLLER)


class WW_410:
    """Triple Sevens"""

    # Deal $7 damage to a minion. Draw 7 cards.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 7), Draw(CONTROLLER) * 7


class WW_411:
    """Stick Up"""

    # Discover a Quickdraw card from another class.
    play = DISCOVER(
        RandomCard(
            collectible=True,
            card_class=FOREIGN_CLASS,
            custom_filter=lambda c: bool(c.tags.get(GameTag.QUICKDRAW)),
        )
    )


class WW_416:
    """Shell Game"""

    # Get a random Epic, Rare, and Common card from other classes.
    play = (
        Give(CONTROLLER, RandomCard(collectible=True, rarity=Rarity.EPIC, card_class=FOREIGN_CLASS)),
        Give(CONTROLLER, RandomCard(collectible=True, rarity=Rarity.RARE, card_class=FOREIGN_CLASS)),
        Give(CONTROLLER, RandomCard(collectible=True, rarity=Rarity.COMMON, card_class=FOREIGN_CLASS)),
    )


##
# Minions


class WW_363:
    """Bounty Wrangler"""

    # Quickdraw or Combo: Get a Coin. The engine routes a COMBO card to its
    # `combo` actions when combo is live (Battlecry.do), otherwise to `play`
    # — the two branches are mutually exclusive, so at most one Coin:
    #   * combo live  -> `combo` always gives the Coin.
    #   * combo off   -> `play` gives the Coin only when Quickdraw fired.
    combo = Give(CONTROLLER, THE_COIN)
    play = QUICKDRAW & Give(CONTROLLER, THE_COIN)


class WW_364:
    """Velarok Windblade"""

    # [x]While this is in your hand, play three cards from other classes
    # to reveal Velarok's true form!
    #
    # Printed text ships as 3 `@`-delimited segments: base text,
    # " ({0} left!)" template (rendered while still counting down), and
    # " (Ready!)" template (rendered when the third card has been played).
    # {0} renders the remaining count = 3 - foreign-class plays so far.
    def custom_cardtext(self):
        segments = self.data.description.split("@")
        if len(segments) < 3:
            return self.data.description
        count = getattr(self, "_velarok_count", 0)
        if count >= _VELAROK_TARGET:
            return segments[0] + segments[2]
        return segments[0] + segments[1]

    def cardtext_entity_0(self):
        count = getattr(self, "_velarok_count", 0)
        return max(0, _VELAROK_TARGET - count)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }

    class Hand:
        events = Play(CONTROLLER, OTHER_CLASS - SELF).after(_VelarokProgress(SELF))


class WW_364t:
    """Velarok, the Deceiver"""

    # Charge (data). After this attacks, Discover a card from another
    # class. It costs (3) less.
    events = Attack(SELF).after(
        Discover(CONTROLLER, RandomCard(collectible=True, card_class=FOREIGN_CLASS)).then(
            Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "WW_364te"))
        )
    )


class WW_413:
    """Antique Flinger"""

    # Battlecry: If you've Excavated twice, destroy an enemy minion.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = (Attr(CONTROLLER, "excavates_this_game") >= 2) & Destroy(TARGET)


class WW_415:
    """Wishing Well"""

    # [x]After you play a Coin, get a random Legendary minion from another
    # class and set its Cost to (1).
    events = Play(CONTROLLER, IDS([THE_COIN])).after(_WishingWellReward(CONTROLLER))


class WW_417:
    """Drilly the Kid"""

    # Battlecry, Quickdraw, and Deathrattle: Excavate a treasure.
    # Battlecry always excavates; Quickdraw adds a second excavate on top.
    play = Excavate(CONTROLLER), QUICKDRAW & Excavate(CONTROLLER)
    deathrattle = Excavate(CONTROLLER)


##
# Enchantments


class WW_364te:
    """Velarok, the Deceiver"""

    # "Costs (3) less." — the data enchant ships without the COST tag, so
    # declare it here. Additive -3 matches the printed Discover discount.
    tags = {GameTag.COST: -3}


##
# Weapons


class WW_412:
    """Bloodrock Co. Shovel"""

    # Deathrattle: Excavate a treasure.
    deathrattle = Excavate(CONTROLLER)
