from ..utils import *


##
# Custom actions


class _ShapeTheStarsSummon(TargetedAction):
    """Shape the Stars (TTN_429t) — Summon a copy of TARGET with +2/+2."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(
            source,
            [
                Summon(source.controller, ExactCopy(target)).then(
                    Buff(Summon.CARD, "TTN_429e")
                )
            ],
        )


class _StrikeFromHistoryBanish(TargetedAction):
    """Strike from History (TTN_429t2) — Remove TARGET from the game
    (Banish approximation: move to SETASIDE zone).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone
        if target is None:
            return
        target.zone = Zone.SETASIDE


class _StrikeFromHistoryChooseSecond(TargetedAction):
    """Strike from History — after the first banish, open a board-pick
    Choice for the second enemy minion. The player chooses among remaining
    enemy minions; falls back to random if no Choice infrastructure is
    consumed (e.g. only one enemy minion left or none).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone
        ctrl = source.controller
        enemies = [m for m in ctrl.opponent.field if m.zone == Zone.PLAY]
        if not enemies:
            return
        if len(enemies) == 1:
            enemies[0].zone = Zone.SETASIDE
            return
        # Open a GenericChoice on remaining enemy minions. The auto-resolver
        # in soak/tests picks cards[0]; a real player picks one. The chosen
        # minion is then banished. We do NOT use GenericChoice (which moves
        # the choice into hand); we use a bespoke Choice that just banishes.
        choice = _BanishChoice(source, ctrl, enemies)
        ctrl.choice = choice


class _BanishChoice:
    """Lightweight choice handle: when .choose(card) is called, banish that
    card. Mirrors the Choice protocol that prepare_game and soak expect
    (player.choice = obj with .cards and .choose method)."""

    def __init__(self, source, player, cards):
        self.source = source
        self.player = player
        self.cards = cards
        self.min_count = 1
        self.max_count = 1
        self.callback = []
        self._callback = []

    def choose(self, card):
        from hearthstone.enums import Zone
        from fireplace.exceptions import InvalidAction
        if card not in self.cards:
            raise InvalidAction(
                f"{card!r} is not a valid choice (one of {self.cards!r})"
            )
        self.player.choice = None
        if card.zone == Zone.PLAY:
            card.zone = Zone.SETASIDE


class _StudentShuffleWithBuff(TargetedAction):
    """Student of the Stars (TTN_482) deathrattle — shuffle a fresh copy
    of TTN_482 into the controller's deck with a permanent +3/+3 already
    applied.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        card = ctrl.card("TTN_482")
        source.game.cheat_action(source, [Buff(card, "TTN_482e")])
        source.game.cheat_action(source, [Shuffle(ctrl, card)])


class _GraceOfHighfatherHeal(TargetedAction):
    """Grace of the Highfather (TTN_745) — Heal TARGET for 8, then
    Discover a card costing the amount overhealed (if any).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Heal(target, 8)])
        overheal = getattr(target, "_last_heal_overheal", 0)
        if overheal <= 0:
            return
        pool = DISCOVER(RandomCollectible(cost=overheal))
        source.game.cheat_action(source, [pool])


class _SerenityDebuff(TargetedAction):
    """Serenity (TTN_483) — Give all enemy minions -2 Attack via the
    in-data TTN_483e buff, then destroy any with 0 or less Attack.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        enemies = list(ENEMY_MINIONS.eval(source.game, source))
        for m in enemies:
            source.game.cheat_action(source, [Buff(m, "TTN_483e")])
        for m in enemies:
            if m.atk <= 0:
                source.game.cheat_action(source, [Destroy(m)])


class _TheStarsAlignTransform(TargetedAction):
    """The Stars Align (TTN_485) — Each minion in hand is transformed
    into a random minion costing (original_cost + 3). The transformed
    copy retains the original mana cost (the printed card clause "they
    keep their original Cost" — we restore via direct assignment).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        hand_minions = [c for c in list(ctrl.hand) if c.type == CardType.MINION]
        for m in hand_minions:
            original_cost = m.cost
            target_cost = original_cost + 3
            from fireplace import cards as _cards
            candidates = _cards.db.filter(
                collectible=True, type=CardType.MINION, cost=target_cost
            )
            if not candidates:
                continue
            chosen_id = source.game.random.choice(candidates)
            source.game.cheat_action(source, [Morph(m, chosen_id)])
            # Restore original mana cost as printed card specifies
            m.cost = original_cost


class _ShapelessConstellationMorph(TargetedAction):
    """Shapeless Constellation (TTN_441) — Transform SELF into an 8/8
    copy of a random minion from the controller's hand.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        hand_minions = [c for c in ctrl.hand if c.type == CardType.MINION]
        if not hand_minions:
            return
        chosen = source.game.random.choice(hand_minions)
        source.game.cheat_action(source, [Morph(source, chosen.id)])
        source.atk = 8
        source.max_health = 8
        source.damage = 0


class _RadenDeathrattle(TargetedAction):
    """Ra-den (TTN_481) deathrattle — Summon each minion played this game
    that didn't start in the controller's deck.

    Approximation: iterates cards_played_this_game, excluding Ra-den
    itself and any card whose id was in starting_deck.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        starting_ids = {c.id for c in ctrl.starting_deck}
        for c in ctrl.cards_played_this_game:
            if c is source:
                continue
            if c.type != CardType.MINION:
                continue
            if c.id in starting_ids:
                continue
            if len(ctrl.field) >= 7:
                break
            source.game.cheat_action(source, [Summon(ctrl, c.id)])


##
# Minions


class TTN_401:
    """Astral Automaton"""

    # Has +1/+1 for each OTHER Astral Automaton you've summoned this game.
    # Counter is bumped at this minion's own summon so its value == final stats.
    # (counter=1 -> 1/1, counter=2 -> 2/2, counter=3 -> 3/3.)
    # Lambda return value replaces the stat (see AuraBuff._getattr).
    update = Refresh(SELF, {
        GameTag.ATK: lambda self, i: max(1, self.controller.astral_automatons_summoned_this_game),
        GameTag.HEALTH: lambda self, i: max(1, self.controller.astral_automatons_summoned_this_game),
    })


class TTN_429:
    """Aman'Thul"""

    # Titan. After this uses an ability, Discover any Legendary minion.
    titan_ability_order = ["TTN_429t", "TTN_429t2", "TTN_429t3"]


class TTN_441:
    """Shapeless Constellation"""

    # Battlecry: Transform into an 8/8 copy of a random minion in your hand.
    play = _ShapelessConstellationMorph(SELF)


class TTN_481:
    """Ra-den"""

    # Deathrattle: Summon each other minion you've played this game
    # that didn't start in your deck.
    deathrattle = _RadenDeathrattle(SELF)


class TTN_482:
    """Student of the Stars"""

    # Deathrattle: Shuffle a copy of this into your deck with permanent +3/+3.
    deathrattle = _StudentShuffleWithBuff(SELF)


class TTN_484:
    """False Disciple"""

    # Battlecry: Discover a Legendary Priest minion from the past.
    # Approximation: Discover any collectible Legendary Priest minion
    # (no set filter for "past" — covers all historical pools).
    play = DISCOVER(RandomLegendaryMinion(card_class=CardClass.PRIEST))


##
# Spells


class TTN_430:
    """Creation Protocol"""

    # Discover a copy of a minion in your deck. Forge: Get another copy.
    # Pre-sample 3 unique minion IDs for a real 3-card Discover.
    def play(self):
        ctrl = self.controller
        deck_minions = [c for c in ctrl.deck if c.type == CardType.MINION]
        if not deck_minions:
            return
        unique_ids = list({c.id for c in deck_minions})
        picks = self.game.random.sample(unique_ids, min(3, len(unique_ids)))
        cards = [ctrl.card(cid) for cid in picks]
        yield GenericChoice(ctrl, cards).then(
            Give(ctrl, Copy(GenericChoice.CARD))
        )

    forge_card = "TTN_430t"


class TTN_430t:
    """Creation Protocol"""

    # Forged: Discover a copy of a minion in your deck. Get another copy of it.
    def play(self):
        ctrl = self.controller
        deck_minions = [c for c in ctrl.deck if c.type == CardType.MINION]
        if not deck_minions:
            return
        unique_ids = list({c.id for c in deck_minions})
        picks = self.game.random.sample(unique_ids, min(3, len(unique_ids)))
        cards = [ctrl.card(cid) for cid in picks]
        yield GenericChoice(ctrl, cards).then(
            Give(ctrl, Copy(GenericChoice.CARD)),
            Give(ctrl, Copy(GenericChoice.CARD)),
        )


class TTN_483:
    """Serenity"""

    # Give all enemy minions -2 Attack. Destroy any with 0 Attack.
    play = _SerenityDebuff(CONTROLLER)


class TTN_485:
    """The Stars Align"""

    # Transform minions in your hand into ones that cost (3) more.
    # (They keep their original Cost.)
    play = _TheStarsAlignTransform(CONTROLLER)


class TTN_745:
    """Grace of the Highfather"""

    # Restore 8 Health. Discover a card that costs the amount Overhealed.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_HERO_OR_MINION_TARGET: 0,
    }
    play = _GraceOfHighfatherHeal(TARGET)


##
# Titan ability sub-cards


class TTN_429t:
    """Shape the Stars"""

    # Choose a non-Titan minion. Summon a copy of it with +2/+2.
    # After using this ability, Discover any Legendary minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        _ShapeTheStarsSummon(TARGET),
        DISCOVER(RandomLegendaryMinion()),
    )


class TTN_429t2:
    """Strike from History"""

    # Choose two enemy minions. Remove them from the game.
    # After using this ability, Discover any Legendary minion.
    # Approximation: targets one enemy minion + banishes a random second enemy.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = (
        _StrikeFromHistoryBanish(TARGET),
        _StrikeFromHistoryChooseSecond(SELF),
        DISCOVER(RandomLegendaryMinion()),
    )


class TTN_429t3:
    """Vision of Heroes"""

    # Summon a random 6-Cost minion. Give it Taunt and Lifesteal.
    # After using this ability, Discover any Legendary minion.
    play = (
        Summon(CONTROLLER, RandomMinion(cost=6)).then(
            Taunt(Summon.CARD),
            GiveLifesteal(Summon.CARD),
        ),
        DISCOVER(RandomLegendaryMinion()),
    )


##
# Enchantments


class TTN_429e:
    """Power of the Highfather"""

    # +2/+2 — used by Shape the Stars ability
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TTN_483e:
    """Serene"""

    # -2 Attack — applied by Serenity
    tags = {GameTag.ATK: -2}


@custom_card
class TTN_482e:
    """Studied"""

    tags = {
        GameTag.CARDNAME: "Studied",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
    }


class TTN_485e1:
    """Fate of the Stars"""

    # In-data cost-adjustment marker for The Stars Align.
    # Actual cost restore is handled inline in _TheStarsAlignTransform.
