from ..utils import *
from ...dsl.random_picker import RandomCardPicker

# "When summoned" trigger. The engine provides OWN_SUMMON (a self-observing
# Summon event that, unlike the plain Summon event, is NOT suppressed for the
# minion's own summon — see Summon._broadcast's self-block). Fall back to a
# plain Summon(CONTROLLER, SELF) if an older engine lacks it so the module
# still imports.
try:
    OWN_SUMMON
except NameError:
    OWN_SUMMON = Summon(CONTROLLER, SELF)


##
# Custom pickers / actions for Cataclysm Rogue


class RandomOtherClassSpell(RandomCardPicker):
    """Pick a random collectible spell whose primary class is neither the
    controller's hero class nor Neutral. Used by Sinestra's Wing tokens
    ("get a random spell from another class") and Chaos Supplicant (with a
    ``cost`` filter to match "of the same Cost")."""

    def evaluate(self, source):
        from hearthstone.enums import CardClass, CardType
        from ...dsl.lazynum import LazyValue

        controller_class = getattr(
            source.controller.hero, "card_class", CardClass.INVALID
        )
        want_cost = self.filters.get("cost", None)
        if isinstance(want_cost, LazyValue):
            want_cost = want_cost.evaluate(source)
        if isinstance(want_cost, list):
            want_cost = want_cost[0] if want_cost else None
        filtered = []
        for cid in db.filter(collectible=True, type=CardType.SPELL):
            c = db[cid]
            classes = getattr(c, "classes", None) or [c.card_class]
            if controller_class in classes:
                continue
            if classes == [CardClass.NEUTRAL]:
                continue
            if want_cost is not None and (c.cost or 0) != want_cost:
                continue
            filtered.append(cid)
        if not filtered:
            return []
        return [source.game.random.choice(filtered)]


class RandomOtherClassShatter(RandomCardPicker):
    """Pick a random collectible SHATTER card from another class (Stolen
    Power). "It's already combined" — we hand over the full collectible
    parent, which the engine only splits into halves when it is *drawn*;
    giving it straight to hand keeps it whole here, an acceptable
    approximation."""

    def evaluate(self, source):
        from hearthstone.enums import CardClass, GameTag

        controller_class = getattr(
            source.controller.hero, "card_class", CardClass.INVALID
        )
        filtered = []
        for cid in db.filter(collectible=True):
            c = db[cid]
            if not c.tags.get(GameTag.SHATTER, 0):
                continue
            classes = getattr(c, "classes", None) or [c.card_class]
            if controller_class in classes:
                continue
            if classes == [CardClass.NEUTRAL]:
                continue
            filtered.append(cid)
        if not filtered:
            return []
        return [source.game.random.choice(filtered)]


class _SinestraDoubleAura(TargetedAction):
    """Sinestra — "Your spells from other classes cast twice." Run as an
    aura ``update``: each refresh, mark every other-class spell in the
    controller's hand with ``_casts_twice_self`` (the per-spell flag the
    engine reads in Play.do), and clear it from own-class spells. Because
    it recomputes from scratch every refresh, the flag is removed
    automatically once Sinestra leaves play (its update stops running, but
    the flag is only ever *set* while it runs)."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardClass, CardType

        player = target
        controller_class = getattr(player.hero, "card_class", CardClass.INVALID)
        for card in player.hand:
            if card.type != CardType.SPELL:
                continue
            classes = getattr(card.data, "classes", None) or [card.card_class]
            other = controller_class not in classes and classes != [CardClass.NEUTRAL]
            card._casts_twice_self = bool(other)


class _IsorathDevour(TargetedAction):
    """Iso'rath — devour 2 random cards from the opponent's hand (set them
    aside, banking the exact entities) then go Dormant for 2 turns. The
    deathrattle returns the banked cards to the opponent's hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        opponent = source.controller.opponent
        pool = opponent.hand[:]
        chosen = []
        for _ in range(min(2, len(pool))):
            card = source.game.random.choice(pool)
            pool.remove(card)
            chosen.append(card)
        for card in chosen:
            card.zone = Zone.SETASIDE
        source._devoured = chosen


##
# Cards


class CATA_154:
    """Sinestra"""

    # Colossal +2. Your spells from other classes cast twice.
    # Colossal limbs (CATA_154t / CATA_154t1) are summoned by the engine and
    # fire their own "get a random other-class spell" effect via the `summoned`
    # hook (see the tokens below), so the parent needs no netting play.
    update = _SinestraDoubleAura(CONTROLLER)


class CATA_154e:
    """Sinestra's Song"""

    # Your spells from other classes cast twice. (Aura is driven by the
    # parent's update; this enchant exists only for the data card.)


class _SinestraWingSummon(TargetedAction):
    """Sinestra's Wing / Soldier of Sinestra — when summoned, give the
    controller a random spell from another class, costing (heralds, capped
    at 2) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        before = len(player.hand)
        source.game.cheat_action(source, [Give(player, RandomOtherClassSpell())])
        if len(player.hand) > before:
            spell = player.hand[-1]
            discount = min(getattr(player, "heralds_this_game", 0), 2)
            if discount:
                # Mirror Sinestra's own path: an instance `cost_mod` attr is
                # never read by the cost property — only `_cost` is honored.
                spell._cost = getattr(spell, "_cost", 0) - discount


class CATA_154t:
    """Sinestra's Wing"""

    # When summoned, get a random spell from another class. It costs less.
    # `summoned` fires the effect on the token's own summon (works for the
    # engine's Colossal-limb summon, which OWN_SUMMON would miss).
    summoned = _SinestraWingSummon(SELF)


class CATA_154t1:
    """Sinestra's Wing"""

    summoned = _SinestraWingSummon(SELF)


class CATA_158:
    """Maniacal Follower"""

    # Stealth. Deathrattle: Herald.
    deathrattle = Herald(CONTROLLER)


class CATA_158t:
    """Soldier of Sinestra"""

    # When summoned, get a random spell from another class. It costs less.
    summoned = _SinestraWingSummon(SELF)


class _AgentOfTheOldOnes(TargetedAction):
    """Battlecry: Choose a card in your hand to transform into a Coin."""

    TARGET = ActionArg()

    def do(self, source, target):
        choose_hand_card(
            source,
            lambda s, c: s.game.cheat_action(s, [Morph(c, "CATA_COIN1")]),
        )


class CATA_200:
    """Agent of the Old Ones"""

    # Battlecry: Choose a card in your hand to transform into a Coin.
    play = _AgentOfTheOldOnes(SELF)


class CATA_201:
    """Twilight Mistress"""

    # Battlecry: Return all enemy minions to their owner's hand.
    play = Bounce(ENEMY_MINIONS)


class _StolenPowerGive(TargetedAction):
    """Give a random other-class Shatter card, but "already combined" — the
    engine's generation-shatter hook is suppressed for this one Give via the
    per-game ``_giving_combined_shatter`` guard, so the whole card is handed
    over instead of being split into its halves."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        game._giving_combined_shatter = True
        try:
            game.cheat_action(
                source, [Give(target, RandomOtherClassShatter())]
            )
        finally:
            game._giving_combined_shatter = False


class CATA_202:
    """Stolen Power"""

    # Get a random Shatter card from another class. (It's already combined.)
    play = _StolenPowerGive(CONTROLLER)


class CATA_203:
    """Garona's Last Stand"""

    # Tradeable. Destroy a Legendary minion. (Tradeable is engine-handled.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_LEGENDARY_TARGET: 0,
    }
    play = Destroy(TARGET)


class _DazeMark(TargetedAction):
    """Stop the bounced minion being played on its owner's next turn.

    The actual lock uses the engine's ``unplayable_next_turn`` counter (the
    same primitive Renferal/Coilfang use), which ``is_playable`` honors and
    which ticks down at the owner's begin_turn — value 2 blocks exactly their
    next turn. The CATA_215e enchant is only the visual "Dazed" marker; it is
    anchored to the OWNER (not the caster) so its OWN_TURN_END self-destroy
    lines up with the owner's turn rather than vanishing on the caster's turn.
    (The enchant's CANT_PLAY tag does not propagate to the host, so it can't be
    the gate on its own.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        if hasattr(target, "unplayable_next_turn"):
            target.unplayable_next_turn = 2
        ench = target.controller.card("CATA_215e", source)
        ench.source = source
        ench.apply(target)


class CATA_215:
    """Daze"""

    # Return an enemy minion to its owner's hand. They can't play it next turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Bounce(TARGET).then(_DazeMark(Bounce.TARGET))


class CATA_215e:
    """Dazed"""

    # Can't be played this turn. Expires at the end of the card-owner's turn
    # (the enchant is anchored to the bounced minion's owner via _DazeMark).
    tags = {GameTag.CANT_PLAY: True}
    events = OWN_TURN_END.on(Destroy(SELF))


class CATA_481:
    """Iso'rath"""

    # Battlecry: Devour 2 random cards from the opponent's hand, then go
    # Dormant for 2 turns. Deathrattle: Return them.
    play = _IsorathDevour(SELF), Dormant(SELF, 2)

    def deathrattle(self):
        devoured = getattr(self, "_devoured", None) or []
        actions = []
        opponent = self.controller.opponent
        for card in devoured:
            if card.zone == Zone.SETASIDE:
                if len(opponent.hand) < opponent.max_hand_size:
                    card.zone = Zone.HAND
                else:
                    card.zone = Zone.GRAVEYARD
        self._devoured = []
        return actions


class CATA_481e:
    """Watch and Wait"""

    # Dormant. Awaken in N turns. (Engine-internal dormant marker.)


class _RiteOfTwilightCombo(TargetedAction):
    """Rite of Twilight Combo — let the player choose an enemy character and
    deal 3 to it. The enemy hero is always a valid character, so there is always
    at least one candidate (auto-resolves to the hero on an empty enemy board);
    with enemy minions present the player picks. The soak's auto-chooser picks
    at random, matching "Deal 3 damage" with a legal target."""

    TARGET = ActionArg()

    def do(self, source, target):
        enemies = ENEMY_CHARACTERS.eval(source.game, source)
        choose_card(
            source,
            enemies,
            lambda s, c: s.game.cheat_action(s, [Hit(c, 3)]),
        )


class CATA_785:
    """Rite of Twilight"""

    # Herald. Combo: Deal 3 damage.
    # The data omits the COMBO GameTag, so declare it — otherwise has_combo is
    # False and Play.do never takes the combo branch.
    # The non-combo line (Herald only) takes no target, but this engine treats
    # REQ_TARGET_FOR_COMBO as an always-on targeting prerequisite, which would
    # make the Herald-only play unplayable on an empty board. So we drop the
    # target requirement and let the Combo branch run an ENTITY_CHOICE over enemy
    # characters (player-chosen target; the enemy hero guarantees playability).
    tags = {GameTag.COMBO: True}
    play = Herald(CONTROLLER)
    combo = Herald(CONTROLLER), _RiteOfTwilightCombo(CONTROLLER)


class _ChaosSupplicantCast(TargetedAction):
    """Chaos Supplicant — after you cast a spell, cast a random spell of the
    same Cost from another class. ``target`` is the spell that was just cast;
    we read its Cost and cast a random same-Cost other-class spell with a
    random legal target (CastSpell handles targeting + Choose One)."""

    TARGET = ActionArg()

    def do(self, source, target):
        cost = target.cost if target is not None else 0
        picker = RandomOtherClassSpell(cost=cost)
        source.game.queue_actions(source, [CastSpell(picker)])


class CATA_786:
    """Chaos Supplicant"""

    # After you cast a spell, cast a random spell of the same Cost from
    # another class.
    events = OWN_SPELL_PLAY.after(_ChaosSupplicantCast(Play.CARD))
