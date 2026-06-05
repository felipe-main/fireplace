"""Across the Timeways — Druid (TIME_)."""

from ..utils import *

from hearthstone.enums import CardType, Zone


# ---------------------------------------------------------------------------
# Support actions (all defined before the card classes that reference them)
# ---------------------------------------------------------------------------


class _DrawBottom(TargetedAction):
    """Draw the bottom ``amount`` cards of the target player's deck.

    ``deck[0]`` is the bottom of the deck (``deck[-1]`` is the next draw),
    so the bottom N cards are ``deck[:N]``.  We materialise the list first
    because ``draw()`` mutates ``deck`` as it moves each card to hand.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        for card in list(target.deck[:amount]):
            card.draw()
        return []


class _WaveshapingDiscover(TargetedAction):
    """Waveshaping — Discover a card from your deck; the OTHER two offered
    cards get put on the bottom.

    Offers up to 3 distinct deck cards (preview copies). The chosen card's
    real deck copy moves to hand; the two unchosen *offered* cards are moved
    to the bottom of the deck (the rest of the deck is untouched).
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen = set()
        distinct = []
        for c in ctrl.deck:
            if c.id not in seen:
                seen.add(c.id)
                distinct.append(c)
        if not distinct:
            return
        n = min(3, len(distinct))
        picks = source.game.random.sample(distinct, n)
        offered = [ctrl.card(c.id, source=source) for c in picks]
        choice = Choice(ctrl, offered).then(
            _WaveshapingPick(Choice.PLAYER, Choice.CARDS, Choice.CARD)
        )
        source.game.queue_actions(source, [choice])


class _WaveshapingPick(TargetedAction):
    """Choose-callback for Waveshaping: move the picked deck card to hand,
    and push the unchosen offered cards' real deck copies to the bottom."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards, picked):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if picked is None:
            return
        # The chosen real card -> hand.
        chosen_real = next((c for c in player.deck if c.id == picked.id), None)
        if chosen_real is not None:
            chosen_real.draw()
        # The other offered cards -> bottom of deck.
        for offered in cards:
            if offered.id == picked.id:
                continue
            real = next((c for c in player.deck if c.id == offered.id), None)
            if real is not None and real in player.deck:
                player.deck.remove(real)
                player.deck.insert(0, real)


class _SetBottomCostsToOne(TargetedAction):
    """Krona — set the Costs of the bottom ``amount`` cards of the target's
    deck to (1) by applying the cost-set enchant to each."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        for card in list(target.deck[:amount]):
            source.game.cheat_action(source, [Buff(card, "TIME_705e")])


class _EbbWatch(TargetedAction):
    """Mark Ebb and Flow as having seen a friendly minion played while held."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._ebb_played_minion = True


class _DodoBattlecry(TargetedAction):
    """Endangered Dodo — if you have 10 or less Health, gain +5/+5 and summon
    a copy of this. The copy is *summoned* (not played) and so carries the
    +5/+5 already baked into the Copy."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.hero.health <= 10:
            source.game.cheat_action(source, [Buff(source, "TIME_703e", atk=5, max_health=5)])
            # Summon a copy carrying the just-applied +5/+5. ExactCopy(SELF) is
            # a selector-based copy that recreates the enchant on the copy.
            source.game.cheat_action(source, [Summon(ctrl, ExactCopy(SELF))])


class _TeachPupil(TargetedAction):
    """Stamp the discovered spell's id onto the most-recent un-taught Pupil in
    the controller's hand so its battlecry can re-cast it."""

    TARGET = ActionArg()  # the chosen spell card

    def do(self, source, target):
        owner = source.controller
        for c in reversed(owner.hand):
            if c.id == "TIME_704t" and not getattr(c, "_taught_spell", None):
                c._taught_spell = target.id
                break


class _KaldoreiDiscover(TargetedAction):
    """Kaldorei Cultivator — Discover 2 Beasts; each chosen Beast is put on the
    bottom of your deck with +5/+5. Two sequential single-Beast Discovers."""

    TARGET = ActionArg()

    def do(self, source, target):
        # Two Beast discovers must be SEQUENTIAL: queuing both flat would have
        # them each set player.choice and only the last would survive. Nest the
        # second discover inside the first's resolution callback.
        second = Discover(CONTROLLER, RandomBeast()).then(
            _KaldoreiPlace(Discover.CARD)
        )
        first = Discover(CONTROLLER, RandomBeast()).then(
            _KaldoreiPlace(Discover.CARD), second
        )
        source.game.queue_actions(source, [first])


class _KaldoreiPlace(TargetedAction):
    """Put the discovered Beast on the bottom of the deck with +5/+5."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, list):
            target = target[0] if target else None
        if target is None:
            return
        ctrl = source.controller
        # Materialise a fresh copy of the chosen Beast into the deck bottom
        # (the Discover preview card itself is not a deck entity).
        beast = ctrl.card(target.id, source=source)
        beast.controller = ctrl
        beast.zone = Zone.DECK
        if beast in ctrl.deck:
            ctrl.deck.remove(beast)
            ctrl.deck.insert(0, beast)
        source.game.cheat_action(source, [Buff(beast, "TIME_730e", atk=5, max_health=5)])


class _FillTemporarySpells(TargetedAction):
    """The Well of Eternity — fill the controller's hand with random spells,
    each marked Temporary. If ``doubled`` (empowered Well), also tag each with
    the Eternalized (casts-twice) enchant."""

    TARGET = ActionArg()
    DOUBLED = ActionArg()

    def get_target_args(self, source, target):
        return [self._args[1]]

    def do(self, source, target, doubled):
        ctrl = source.controller
        # Bound the loop by hand capacity; break if a Give fails to grow hand.
        guard = 0
        while len(ctrl.hand) < ctrl.max_hand_size and guard < 12:
            guard += 1
            before = len(ctrl.hand)
            source.game.cheat_action(source, [Give(ctrl, RandomSpell())])
            if len(ctrl.hand) <= before:
                break
            spell = ctrl.hand[-1]
            spell.tags[enums.TEMPORARY] = True
            if doubled:
                source.game.cheat_action(source, [Buff(spell, "TIME_211t1te")])
                # "They cast twice": flag the spell so the engine fires its play
                # effect an extra time (per-spell, no player-wide aura needed).
                spell._casts_twice_self = True


class _SummonDoubledCopy(TargetedAction):
    """Zin-Azshari (empowered) — summon a copy of a random friendly minion with
    its stats doubled."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        minions = [m for m in ctrl.field if m is not source]
        if not minions:
            return
        original = source.game.random.choice(minions)
        atk = original.atk
        health = original.max_health
        # Build a copy carrying the original's enchantments (so it starts at the
        # original's CURRENT stats), then add a +current buff -> current + current
        # = 2 x current. A fresh BASE copy buffed by +current came out at
        # base + current, not double (wrong whenever the original was buffed).
        copy = ctrl.card(original.id, source=source)
        copy_buffs(source, original, copy)
        source.game.cheat_action(source, [Summon(ctrl, copy)])
        source.game.cheat_action(
            source,
            [Buff(copy, "TIME_211t2te", atk=atk, max_health=health)],
        )


class _SplinteredReality(TargetedAction):
    """Splintered Reality (END_009) — summon two 2/2 Treants. They gain +1/+1
    for each friendly Treant that died this game.

    "Friendly Treant that died this game" = minions in the controller's
    graveyard whose printed name ends with "Treant" (matches the TREANT
    selector convention). Each freshly-summoned Treant gets the END_009e
    enchant carrying +N/+N where N is that count.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        dead_treants = sum(
            1
            for card in ctrl.graveyard
            if card.type == CardType.MINION
            and getattr(card, "name_enUS", "").endswith("Treant")
        )
        for _ in range(2):
            if len(ctrl.field) >= 7:
                break
            treant = ctrl.card("END_009t", source=source)
            source.game.cheat_action(source, [Summon(ctrl, treant)])
            if dead_treants > 0 and treant.zone == Zone.PLAY:
                source.game.cheat_action(
                    source,
                    [Buff(treant, "END_009e", atk=dead_treants, max_health=dead_treants)],
                )


class _AlternateReality(TargetedAction):
    """Alternate Reality — replace the controller's hand and deck with random
    Choose One cards from the past; each costs (1) less.

    Implementation: clear hand and deck, then refill the deck and hand with
    random collectible Choose One cards (CHOOSE_ONE tag) up to their prior
    sizes, each buffed -1 Cost. Cards are drawn from across all classes."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        prev_hand = len(ctrl.hand)
        prev_deck = len(ctrl.deck)
        for card in list(ctrl.hand):
            card.zone = Zone.SETASIDE
        for card in list(ctrl.deck):
            card.zone = Zone.SETASIDE
        picker = RandomCard(
            collectible=True,
            from_past=True,
            custom_filter=lambda c: c.tags.get(GameTag.CHOOSE_ONE, 0) == 1,
        )

        def make(zone):
            cards = picker.find_cards(source)
            if not cards:
                return False
            cid = source.game.random.choice(cards)
            card = ctrl.card(cid, source=source)
            card.controller = ctrl
            card.zone = zone
            source.game.cheat_action(source, [Buff(card, "TIME_707e")])
            return True

        for _ in range(prev_hand):
            if not make(Zone.HAND):
                break
        for _ in range(prev_deck):
            if not make(Zone.DECK):
                break
        ctrl.shuffle_deck()


# ---------------------------------------------------------------------------
# Custom enchants not present in data
# ---------------------------------------------------------------------------


@custom_card
class TIME_705e:
    "Eternal"
    # Set-cost-to-(1) enchant (Krona). `cost` script overrides the host's cost.
    tags = {
        GameTag.CARDNAME: "Eternal",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    cost = lambda self, i: 1


@custom_card
class TIME_707e:
    "Reality Shift"
    tags = {
        GameTag.CARDNAME: "Reality Shift",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


# ---------------------------------------------------------------------------
# Spells
# ---------------------------------------------------------------------------


class TIME_023:
    """Contingency"""

    # Draw the bottom two cards from your deck.
    play = _DrawBottom(CONTROLLER, 2)


class TIME_701:
    """Waveshaping"""

    # Discover a card from your deck. The others get put on the bottom.
    play = _WaveshapingDiscover(CONTROLLER)


class TIME_702:
    """Ebb and Flow"""

    # Deal $3 damage. If you played a minion while holding this, gain 5 Armor.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }

    def play(self):
        yield Hit(self.target, 3)
        if getattr(self, "_ebb_played_minion", False):
            yield GainArmor(self.controller.hero, 5)

    class Hand:
        # OWN_CARD_PLAY broadcast args: (player, card, target, index, choose).
        # Mark when a friendly minion is played while Ebb and Flow is held.
        events = OWN_CARD_PLAY.on(
            lambda self, player, card, *rest: _EbbWatch(SELF)
            if card is not self and card.type == CardType.MINION
            else None
        )


class TIME_707:
    """Alternate Reality"""

    # Replace your hand and deck with random Choose One cards from the past.
    # They cost (1) less.
    play = _AlternateReality(CONTROLLER)


class END_009:
    """Splintered Reality"""

    # Summon two 2/2 Treants. They gain +1/+1 for each friendly Treant that
    # died this game.
    play = _SplinteredReality(CONTROLLER)


class END_009e:
    "Splintered"
    # Increased stats (in data; +N/+N applied at summon time).


class END_009t:
    """Treant"""

    # Vanilla 2/2 Treant token.


# ---------------------------------------------------------------------------
# Minions
# ---------------------------------------------------------------------------


class TIME_033:
    """Druid of Regrowth"""

    # Rewind Battlecry: Cast 2 random Nature spells. (Rewind is engine-handled.)
    play = CastSpell(RandomSpell(spell_school=SpellSchool.NATURE)) * 2


class TIME_703:
    """Endangered Dodo"""

    # Taunt Battlecry: If you have 10 or less Health, gain +5/+5 and summon a
    # copy of this.
    play = _DodoBattlecry(SELF)


class TIME_703e:
    "Endangered"
    # +5/+5 (in data).


class TIME_704:
    """Highborne Mentor"""

    # Battlecry: Get a 2/2 Pupil. Discover a spell that costs (7) or more from
    # the past to teach it.
    play = (
        Give(CONTROLLER, "TIME_704t"),
        Discover(
            CONTROLLER,
            RandomSpell(
                from_past=True,
                custom_filter=lambda c: c.cost is not None and c.cost >= 7,
            ),
        ).then(_TeachPupil(Discover.CARD)),
    )


class TIME_704t:
    """Highborne Pupil"""

    # Battlecry: Cast the spell that taught me (stored as `_taught_spell`).
    def play(self):
        taught = getattr(self, "_taught_spell", None)
        if taught:
            yield CastSpell(taught)

    def custom_cardtext(self):
        # Printed text is "<b>Battlecry:</b> Cast {0}." — fill {0} with the
        # taught spell's printed name. `_taught_spell` is the spell's card id
        # (set by `_TeachPupil`), but be defensive: it may also be a card
        # object or None (un-taught) — render the base "{0}" form gracefully.
        taught = getattr(self, "_taught_spell", None)
        name = None
        if taught is not None:
            if isinstance(taught, str):
                if taught in db:
                    name = db[taught].name
            else:
                name = getattr(taught, "name", None)
        if not name:
            return self.data.description
        return self.data.description.replace("{0}", name)

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


class TIME_705:
    """Krona, Keeper of Eons"""

    # Taunt Battlecry: Set the Costs of the bottom 5 cards of your deck to (1).
    play = _SetBottomCostsToOne(CONTROLLER, 5)


class TIME_730:
    """Kaldorei Cultivator"""

    # Battlecry: Discover 2 Beasts. Put them on the bottom of your deck with
    # +5/+5.
    play = _KaldoreiDiscover(SELF)


class TIME_730e:
    "Nurtured"
    # +5/+5 (in data).


# ---------------------------------------------------------------------------
# Lady Azshara (Fabled, Choose One) + her locations & tokens
# ---------------------------------------------------------------------------


class TIME_211:
    """Lady Azshara"""

    # Fabled. Choose One - Empower Zin-Azshari; or The Well of Eternity.
    # (The other gets destroyed!) — only one location slot exists, so summoning
    # the chosen empowered location naturally replaces/destroys the other.
    choose = ("TIME_211a", "TIME_211b")


class TIME_211a:
    """Empower Zin-Azshari"""

    # The minions summoned by Zin-Azshari will have doubled stats. Destroy The
    # Well of Eternity. -> place the empowered Zin-Azshari location.
    play = Summon(CONTROLLER, "TIME_211t2t")


class TIME_211b:
    """Empower the Well"""

    # The spells created by The Well of Eternity will cast twice. Destroy
    # Zin-Azshari. -> place the empowered Well of Eternity location.
    play = Summon(CONTROLLER, "TIME_211t1t")


class TIME_211t1:
    """The Well of Eternity"""

    # Fill your hand with random Temporary spells.
    activate = _FillTemporarySpells(CONTROLLER, False)


class TIME_211t1t:
    """The Well of Eternity"""

    # Fill your hand with random Temporary spells. They cast twice.
    activate = _FillTemporarySpells(CONTROLLER, True)


class TIME_211t1te:
    "Eternalized"
    # Casts twice (in data).


class TIME_211t2:
    """Zin-Azshari"""

    # Summon a copy of a friendly minion.
    activate = Summon(CONTROLLER, Copy(RANDOM(FRIENDLY_MINIONS)))


class TIME_211t2t:
    """Zin-Azshari"""

    # Summon a copy of a friendly minion with its stats doubled.
    activate = _SummonDoubledCopy(CONTROLLER)


class TIME_211t2te:
    "The City's Strength"
    # Doubled stats (in data).
