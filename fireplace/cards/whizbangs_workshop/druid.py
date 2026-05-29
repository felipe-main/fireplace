from ..utils import *

from hearthstone.enums import CardType, Zone


##
# Custom actions


class _SparklingPhialDiscount(TargetedAction):
    """Sparkling Phial — after the $2 damage resolves, reduce the Cost of the
    controller's next card this turn by the amount of damage actually dealt
    (2 + Spell Damage, doubled by SPELLPOWER_DOUBLE). The magnitude is stored
    on the enchant so its `update` aura can reduce in-hand cards by exactly
    that much; the enchant is consumed when the next card is played and also
    expires at end of turn (TAG_ONE_TURN_EFFECT)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        amount = ctrl.get_spell_damage(source, 2)
        if amount <= 0:
            return
        source.game.cheat_action(
            source, [Buff(ctrl, "TOY_800e1", cost_amount=amount)]
        )


class _JadeDisplayDeathrattle(TargetedAction):
    """Jade Display — Deathrattle: give every friendly Jade Display (in play,
    hand, and deck) +1/+1 this game, then shuffle 2 fresh Jade Displays into
    your deck carrying the full accumulated buff. A per-controller counter
    tracks the cumulative this-game bonus so newly created copies match the
    ones already on the board."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        stacks = getattr(ctrl, "_jade_display_stacks", 0) + 1
        ctrl._jade_display_stacks = stacks
        # Bump every existing friendly Jade Display by +1/+1.
        existing = [
            c
            for c in list(ctrl.field) + list(ctrl.hand) + list(ctrl.deck)
            if c.id == "TOY_803"
        ]
        for card in existing:
            source.game.cheat_action(source, [Buff(card, "TOY_803e2")])
        # Shuffle 2 new copies and bring them up to the accumulated bonus.
        for _ in range(2):
            source.game.cheat_action(source, [Shuffle(ctrl, "TOY_803")])
            new_card = None
            for c in ctrl.deck:
                if c.id == "TOY_803" and c not in existing:
                    new_card = c
            if new_card is None:
                continue
            existing.append(new_card)
            for _ in range(stacks):
                source.game.cheat_action(source, [Buff(new_card, "TOY_803e2")])


class _WindUpSaplingRefresh(TargetedAction):
    """Wind-Up Sapling — Battlecry: Refresh 4 Mana Crystals (restore up to 4
    spent Mana Crystals this turn)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl.used_mana = max(0, ctrl.used_mana - 4)


class _BottomlessToyChestDiscover(TargetedAction):
    """Bottomless Toy Chest — Discover a card from your deck. If you have
    Spell Damage, also add a copy of it to your hand. Presents up to three
    distinct real deck cards; the chosen card is moved to hand (it leaves the
    deck), and when the controller has Spell Damage a fresh copy is added."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        deck = list(ctrl.deck)
        if not deck:
            return
        seen = {}
        for c in deck:
            seen.setdefault(c.id, c)
        ids = list(seen.keys())
        sample = source.game.random.sample(ids, min(3, len(ids)))
        cards = [seen[cid] for cid in sample]
        copy_it = ctrl.spellpower > 0
        source.game.queue_actions(
            source,
            [
                GenericChoice(ctrl, cards).then(
                    _BottomlessToyChestPick(GenericChoice.PLAYER, GenericChoice.CARD)
                )
            ],
        )
        # Stash whether to copy on the controller so the pick callback knows.
        ctrl._bottomless_copy = copy_it


class _BottomlessToyChestPick(TargetedAction):
    """Choose-callback: move the picked deck card to hand; if the controller
    had Spell Damage when the Discover started, also add a copy to hand."""

    PLAYER = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, picked):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if picked is None:
            return
        real = next((c for c in player.deck if c.id == picked.id), None)
        if real is not None:
            real.zone = Zone.HAND
        if getattr(player, "_bottomless_copy", False):
            source.game.cheat_action(source, [Give(player, picked.id)])
        player._bottomless_copy = False


##
# Spells


# [x]Deal $2 damage. Your next card this turn costs that much less.
class TOY_800:
    """Sparkling Phial"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 2), _SparklingPhialDiscount(TARGET)


class TOY_800e1:
    # In-data "Sparkling" — your next card this turn costs (X) less, where X is
    # the damage Sparkling Phial dealt (stored as `cost_amount` on apply).
    # Consumed when the next card is played; also a one-turn effect.
    #
    # Consume on the NEXT card's ON-play broadcast — the same pattern as
    # Sandbox Scoundrel (TOY_521e1). `.on()` (not `.after()`) matters: the
    # ON-play broadcast for Sparkling Phial itself fires BEFORE the phial's
    # battlecry applies this enchant (actions.py Play.do), so the enchant
    # cannot catch its own source's play and self-destruct prematurely. The
    # next card the player plays this turn triggers ON-play with the enchant
    # already present, so it is consumed after exactly one discounted card.
    tags = {GameTag.TAG_ONE_TURN_EFFECT: True}
    update = Refresh(FRIENDLY_HAND, {GameTag.COST: -Attr(SELF, "cost_amount")})
    events = Play(CONTROLLER).on(Destroy(SELF))


# Reduce the Cost and Attack of minions in your deck by (1).
class TOY_805:
    """Ensmallen"""

    play = (
        Buff(FRIENDLY_DECK + MINION, "TOY_805e"),
        Buff(FRIENDLY_DECK + MINION, "TOY_805e2"),
    )


class TOY_805e:
    # In-data "Ensmallened Cost" — Costs (1) less.
    tags = {GameTag.COST: -1}


class TOY_805e2:
    # In-data "Ensmallened" — -1 Attack.
    tags = {GameTag.ATK: -1}


# Summon two 1/5 Beetles with Taunt. Costs (3) less if you have Spell Damage.
class TOY_804:
    """Woodland Wonders"""

    cost_mod = (Attr(CONTROLLER, "spellpower") >= 1) & -3
    play = Summon(CONTROLLER, "TOY_804t") * 2


# Taunt
class TOY_804t:
    """Grove Beetle"""

    # Taunt lives in data; 1/5 stat line + Beast race are in data too.


# Discover a card from your deck. If you have Spell Damage, copy it.
class TOY_851:
    """Bottomless Toy Chest"""

    play = _BottomlessToyChestDiscover(SELF)


##
# Minions


# Miniaturize Choose One - Gain Spell Damage +1; or Draw a spell.
class TOY_801:
    """Chia Drake"""

    choose = ("TOY_801b", "TOY_801a")
    play = ChooseBoth(CONTROLLER) & (
        Buff(SELF, "TOY_801e"),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)),
    )


# Mini Choose One - Gain Spell Damage +1; or Draw a spell.
class TOY_801t:
    """Chia Drake"""

    choose = ("TOY_801b", "TOY_801a")
    play = ChooseBoth(CONTROLLER) & (
        Buff(SELF, "TOY_801e"),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)),
    )


# Draw a spell. (Chia Drake Choose One — Cultivate)
class TOY_801a:
    """Cultivate"""

    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL))


# Gain Spell Damage +1. (Chia Drake Choose One — Seedling Growth)
class TOY_801b:
    """Seedling Growth"""

    play = Buff(SELF, "TOY_801e")


class TOY_801e:
    # In-data "Ch-Ch-Ch-Chia" — Spell Damage +1.
    tags = {GameTag.SPELLPOWER: 1}


# Tradeable Battlecry: Refresh 4 Mana Crystals. (Trade to upgrade!)
class TOY_802:
    """Wind-Up Sapling"""

    play = _WindUpSaplingRefresh(SELF)


# Deathrattle: Your Jade Displays have +1/+1 this game. Shuffle 2 of them into
# your deck.
class TOY_803:
    """Jade Display"""

    deathrattle = _JadeDisplayDeathrattle(SELF)


class TOY_803e2:
    # In-data "Jade Profits" — +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


# Battlecry: Shuffle 10 random Legendary minions into your deck. They cost (1).
class TOY_806:
    """Sky Mother Aviana"""

    def play(self):
        controller = self.controller
        for _ in range(10):
            yield Shuffle(
                CONTROLLER, RandomMinion(rarity=Rarity.LEGENDARY)
            ).then(Buff(Shuffle.CARD, "TOY_806e"))


class TOY_806e:
    # In-data "Harpy's Blessing" — Costs (1). Sets the host card's Cost to 1
    # regardless of its base cost or other modifiers.
    cost = lambda self, i: 1


# Spell Damage +1. Your spells get double bonus from Spell Damage.
class TOY_807:
    """Owlonius"""

    # Spell Damage +1, and "your spells get DOUBLE BONUS from Spell Damage" —
    # only the Spell Damage bonus is doubled, not the spell's base damage.
    tags = {GameTag.SPELLPOWER: 1}
    update = Refresh(CONTROLLER, {enums.SPELLPOWER_BONUS_DOUBLE: 1})


##
# Locations


# Gain Spell Damage +1 this turn only.
class TOY_850:
    """Magical Dollhouse"""

    activate = Buff(CONTROLLER, "TOY_850e")


class TOY_850e:
    # In-data "Magical Harvest" — Spell Damage +1 this turn.
    tags = {GameTag.TAG_ONE_TURN_EFFECT: True}
    update = Refresh(CONTROLLER, {GameTag.SPELLPOWER: 1})
