from ..utils import *


##
# Custom actions / helpers


# The six "Drink" starter spells (the (3 Drinks left!) head of each chain).
DRINK_SPELLS = [
    "VAC_323",  # Malted Magma
    "VAC_338",  # Cup o' Muscle
    "VAC_404",  # Nightshade Tea
    "VAC_520",  # Seabreeze Chalice
    "VAC_916",  # Divine Brew
    "VAC_951",  # "Health" Drink
]


class _IncindiusUpgrade(TargetedAction):
    """Incindius — at the end of your turn, upgrade your Eruptions. Each
    Eruption (VAC_321t) tracks its damage on the per-card `_eruption_damage`
    attribute (starts at 1). This bumps every Eruption the controller owns
    (in hand or deck) by 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for c in list(ctrl.hand) + list(ctrl.deck):
            if c.id == "VAC_321t":
                c._eruption_damage = getattr(c, "_eruption_damage", 1) + 1


class _EruptionDamage(LazyNum):
    """Eruption — deal $@ damage to all enemies, where @ is this copy's
    current upgrade level (starts at 1, bumped by Incindius)."""

    def evaluate(self, source):
        return self.num(getattr(source, "_eruption_damage", 1))


class _LamplighterDamage(LazyNum):
    """Lamplighter — Battlecry: deal damage equal to the number of turns in a
    row you've played an Elemental. The engine maintains
    `azerite_elemental_streak` (completed consecutive turns); Lamplighter is
    itself this turn's Elemental, so add 1 for the current turn."""

    def evaluate(self, source):
        player = source.controller
        # azerite_elemental_streak counts prior completed consecutive turns;
        # Lamplighter being played IS this turn's Elemental (the counter is
        # bumped only after the battlecry), so always add 1 for the current
        # turn.
        streak = player.azerite_elemental_streak + 1
        return self.num(max(streak, 1))


class _PackageDealerDraw(TargetedAction):
    """Package Dealer — after you draw a card, 50% chance to draw another.
    Guarded with a re-entrancy flag so the chain doesn't recurse infinitely
    inside the Draw broadcast; each extra draw is itself a Draw and will
    re-trigger this listener naturally, matching the printed cascade."""

    TARGET = ActionArg()

    def do(self, source, target):
        # 50% to draw another. The extra Draw re-broadcasts ON and re-triggers
        # this listener, so the cascade continues naturally (bounded by the
        # coinflip and an empty deck, which draws nothing and stops).
        if source.game.random.randint(0, 1) != 1:
            return
        source.game.cheat_action(source, [Draw(source.controller)])


class _BayfinDestroyToken(TargetedAction):
    """Bayfin Bodybuilder — after a minion is summoned for your opponent
    during your turn, Silence and destroy it."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        # `card` is the opponent's just-summoned minion (Summon.CARD); `target`
        # is Bayfin itself.
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        if source.controller.current_player:
            source.game.cheat_action(source, [Silence(card), Destroy(card)])


class _LocationUseCounter(TargetedAction):
    """Maintain the controller's per-game "locations used" counter. Attached to
    Seaside Giant in every zone so it observes every friendly location
    activation across the whole game (UseLocation broadcasts to deck + hand +
    play)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl.locations_used_this_game = (
            getattr(ctrl, "locations_used_this_game", 0) + 1
        )


class _SeasideGiantCost(LazyNum):
    """Seaside Giant — costs (2) less for each time you've used a location
    this game."""

    def evaluate(self, source):
        used = getattr(source.controller, "locations_used_this_game", 0)
        return self.num(used * 2)


class _MarinChooseTreasure(TargetedAction):
    """Marin the Manager — Battlecry: Choose a fantastic treasure (a Discover
    over the 4 treasures); shuffle the other 3 into your deck."""

    TARGET = ActionArg()

    TREASURES = ["VAC_702t", "VAC_702t2", "VAC_702t3", "VAC_702t4"]

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomID(*self.TREASURES)).then(
                    Give(ctrl, Discover.CARD).then(
                        _MarinShuffleRest(SELF, Give.CARD)
                    )
                )
            ],
        )


class _MarinShuffleRest(TargetedAction):
    """Marin — after the treasure is chosen and given to hand, shuffle the
    other three treasures into the deck."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        chosen_id = card.id if card is not None else None
        ctrl = source.controller
        for tid in _MarinChooseTreasure.TREASURES:
            if tid != chosen_id:
                source.game.cheat_action(source, [Shuffle(ctrl, tid)])


class _GoldenKoboldReplace(TargetedAction):
    """Golden Kobold — Battlecry: Replace your hand with Legendary minions."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        held = [c for c in ctrl.hand if c is not source]
        n = len(held)
        for c in held:
            c.discard()
        for _ in range(n):
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            source.game.cheat_action(source, [Give(ctrl, RandomLegendaryMinion())])


class _TolinGobletFill(TargetedAction):
    """Tolin's Goblet — Draw a card. Fill your hand with copies of it."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        before = set(ctrl.hand)
        source.game.cheat_action(source, [Draw(ctrl)])
        drawn = [c for c in ctrl.hand if c not in before]
        if not drawn:
            return
        card = drawn[0]
        while len(ctrl.hand) < ctrl.max_hand_size:
            source.game.cheat_action(source, [Give(ctrl, card.id)])


class _CarryOnPack(TargetedAction):
    """Carry-On Grub — get a 1-Cost Suitcase, then pack the top 2 cards of your
    deck into it. The packed cards are removed from the deck (set aside) and
    stored on the given Suitcase token; the Suitcase delivers them when
    played."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        top = list(reversed(ctrl.deck))[:2]
        suitcase_id = "VAC_935t" if len(top) >= 2 else "VAC_935t2"
        source.game.cheat_action(source, [Give(ctrl, suitcase_id)])
        given = [c for c in ctrl.hand if c.id == suitcase_id]
        if not given:
            return
        suitcase = given[-1]
        packed = []
        for c in top:
            c.zone = Zone.SETASIDE
            packed.append(c)
        suitcase._packed_cards = packed


class _CarryOnOpen(TargetedAction):
    """Carry-On Suitcase — get the packed cards (give the stored card entities
    to hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for c in getattr(source, "_packed_cards", []):
            ctrl.give(c.id)


class _GorgonzormuUpgrade(TargetedAction):
    """Delicious Cheese — upgrades each turn: the minions it summons grow by
    one Cost per turn (starts at 1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        for c in list(source.controller.hand) + list(source.controller.deck):
            if c.id == "VAC_955t":
                c._cheese_cost = getattr(c, "_cheese_cost", 1) + 1


class _CheeseCost(LazyNum):
    def evaluate(self, source):
        return self.num(getattr(source, "_cheese_cost", 1))


class _AmuletGiveBoth(TargetedAction):
    """Griftah, Trusted Vendor — Discover an amazing Amulet; give the real
    version to you and the phony version to the opponent."""

    TARGET = ActionArg()

    # Real amulet -> phony (opponent) variant id.
    PHONY = {
        "VAC_959t01": "VAC_959t01t",
        "VAC_959t05": "VAC_959t05t",
        "VAC_959t06": "VAC_959t06t",
        "VAC_959t07": "VAC_959t07t",
        "VAC_959t08": "VAC_959t08t",
        "VAC_959t09": "VAC_959t09t",
        "VAC_959t10": "VAC_959t10t",
    }

    def do(self, source, target):
        ctrl = source.controller
        reals = list(self.PHONY.keys())
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomID(*reals)).then(
                    _AmuletDeliver(SELF, Discover.CARD)
                )
            ],
        )


class _AmuletDeliver(TargetedAction):
    """After Griftah's Discover picks an amulet, give the real one to the
    controller and the phony version to the opponent."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        ctrl = source.controller
        source.game.cheat_action(source, [Give(ctrl, card.id)])
        phony = _AmuletGiveBoth.PHONY.get(card.id, card.id)
        source.game.cheat_action(source, [Give(ctrl.opponent, phony)])


class _AmuletTrackingGet(TargetedAction):
    """Amulet of Tracking (phony) — Get 3 random Legendary cards, then
    transform them into Commons."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(3):
            before = set(ctrl.hand)
            # "Legendary cards" = all collectible legendaries, any card type.
            source.game.cheat_action(
                source, [Give(ctrl, RandomCollectible(rarity=Rarity.LEGENDARY))]
            )
            new = [c for c in ctrl.hand if c not in before]
            for c in new:
                # Downgrade to a random Common of the same card type.
                common = RandomCollectible(
                    rarity=Rarity.COMMON, type=c.type
                ).evaluate(source)
                if common:
                    cid = common[0] if isinstance(common, list) else common
                    source.game.cheat_action(source, [Morph(c, cid)])


class _MixologistCraft(TargetedAction):
    """Mixologist — Battlecry: Craft a custom 1-Cost Potion. Gives the
    Mixologist's Special token (a custom potion combining two random effects).
    The combined effect is data-driven cosmetic placeholders, so the token is
    a benign no-op spell here."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Give(source.controller, "VAC_523t")])


class _OctoDamage(TargetedAction):
    """Octo-masseuse — deals octuple damage to minions. The normal attack
    deals ATK once; add 7x more to the defending minion to reach octuple
    total."""

    TARGET = ActionArg()
    DEFENDER = ActionArg()

    def do(self, source, target, defender):
        if isinstance(defender, list):
            defender = defender[0] if defender else None
        if defender is None:
            return
        extra = (source.atk or 0) * 7
        if extra:
            source.game.cheat_action(source, [Hit(defender, extra)])


class _ZookeeperRampage(TargetedAction):
    """Rampaging Beast — after being summoned for the opponent, it attacks all
    of its controller's other minions."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, list):
            target = target[0] if target else None
        if target is None:
            return
        victims = [m for m in target.controller.field if m is not target]
        for m in victims:
            if target.dead or m.dead:
                continue
            source.game.cheat_action(target, [Attack(target, m)])


class _ChefRemember(TargetedAction):
    """Terrible Chef — remember the Nerubian Egg it summoned so the deathrattle
    can destroy that specific egg."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        source._chef_egg = card


class _ChefDestroyEgg(TargetedAction):
    """Terrible Chef deathrattle — destroy the egg it summoned (if still in
    play)."""

    TARGET = ActionArg()

    def do(self, source, target):
        egg = getattr(source, "_chef_egg", None)
        if egg is not None and egg.zone == Zone.PLAY:
            source.game.cheat_action(source, [Destroy(egg)])


class _TidepoolDiscover(TargetedAction):
    """Tidepool Pupil — Discover one of the spells you cast while holding this.
    The per-card `spells_history_while_holding` list records the ids."""

    TARGET = ActionArg()

    def do(self, source, target):
        # spells_history_while_holding stores (id, cost) tuples; Discover needs
        # the bare ids.
        history = list(getattr(source, "spells_history_while_holding", []))
        ids = [h[0] if isinstance(h, (tuple, list)) else h for h in history]
        if not ids:
            return
        source.game.cheat_action(
            source,
            [
                Discover(source.controller, RandomID(*ids)).then(
                    Give(source.controller, Discover.CARD)
                )
            ],
        )


class _OverplannerDiscover(TargetedAction):
    """Overplanner — Discover three cards from your deck (in sequence) and put
    each on top of your deck. Stacking them one after another leaves the last
    chosen on top — matching "put on top in that order"."""

    TARGET = ActionArg()
    REMAINING = ActionArg()

    def do(self, source, target, remaining=None):
        ctrl = source.controller
        if isinstance(remaining, (list, tuple)):
            remaining = remaining[0] if remaining else None
        n = 3 if remaining is None else remaining
        if n <= 0:
            return
        ids = list({c.id for c in ctrl.deck})
        if not ids:
            return
        source.game.cheat_action(
            source,
            [
                Discover(ctrl, RandomID(*ids)).then(
                    _OverplannerPutOnTop(SELF, Discover.CARD, n)
                )
            ],
        )


class _OverplannerPutOnTop(TargetedAction):
    """Pull the chosen card-id out of the deck, put it on top, then chain the
    next Discover (one fewer remaining)."""

    TARGET = ActionArg()
    CARD = ActionArg()
    REMAINING = ActionArg()

    def do(self, source, target, card, remaining):
        if isinstance(card, list):
            card = card[0] if card else None
        if isinstance(remaining, (list, tuple)):
            remaining = remaining[0] if remaining else 0
        ctrl = source.controller
        if card is not None:
            real = next((c for c in ctrl.deck if c.id == card.id), None)
            if real is not None:
                source.game.cheat_action(source, [PutOnTop(ctrl, real)])
        source.game.cheat_action(source, [_OverplannerDiscover(SELF, remaining - 1)])


##
# Minions


class VAC_304(ThreeSpellsProgressUtils):
    """Tidepool Pupil"""

    # Battlecry: If you've cast 3 spells while holding this, Discover one of
    # them. ({0} left!) / (Ready!)
    play = (Attr(SELF, "spells_cast_while_holding") >= 3) & _TidepoolDiscover(SELF)


class VAC_321:
    """Incindius"""

    # At the end of your turn, upgrade your Eruptions. Battlecry: Shuffle 5
    # Eruptions in your deck.
    play = Shuffle(CONTROLLER, "VAC_321t") * 5
    events = OWN_TURN_END.on(_IncindiusUpgrade(SELF))


class VAC_321t:
    """Eruption"""

    # Casts When Drawn. Deal $@ damage to all enemies.
    play = Hit(ENEMY_CHARACTERS, _EruptionDamage())

    def custom_cardtext(self):
        return self.data.description.replace(
            "@", str(getattr(self, "_eruption_damage", 1))
        )

    def cardtext_entity_0(self):
        return getattr(self, "_eruption_damage", 1)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


class VAC_327:
    """Cryopractor"""

    # Battlecry: Give a minion +3/+3 and Freeze it.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_MINION_TARGET: 0}
    play = Buff(TARGET, "VAC_327e"), Freeze(TARGET)


class VAC_327e:
    """Cryo-bout It"""

    # +3/+3.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class VAC_406:
    """Sleepy Resident"""

    # Taunt Deathrattle: ALL other minions fall asleep (= Freeze). A buff
    # carrying GameTag.FROZEN does not set the `frozen` state (which reads the
    # _frozen attr), so use the Freeze action.
    deathrattle = Freeze(ALL_MINIONS - SELF)


class VAC_406e:
    """Asleep"""

    # "Fall asleep" = cannot attack until their controller's next turn. The
    # engine's FROZEN flag models exactly "can't attack this turn", which is
    # how asleep is rendered.
    tags = {GameTag.FROZEN: 1}


class VAC_421:
    """Snoozin' Zookeeper"""

    # Battlecry: Summon an 8/8 Beast for your opponent. It attacks all of
    # their minions.
    play = Summon(OPPONENT, "VAC_421t").then(_ZookeeperRampage(Summon.CARD))


class VAC_421t:
    """Rampaging Beast"""


class VAC_430:
    """Bloodsail Recruiter"""

    # Battlecry: Discover a Pirate.
    play = DISCOVER(RandomMinion(race=Race.PIRATE))


class VAC_432:
    """Resort Valet"""

    # Battlecry: Discover a card from the newest expansion.
    play = DISCOVER(RandomCollectible(card_set=CardSet.ISLAND_VACATION))


class VAC_438:
    """Travel Agent"""

    # Battlecry: Discover a location from any class.
    play = DISCOVER(RandomCollectible(type=CardType.LOCATION))


class VAC_439:
    """Seaside Giant"""

    # Costs (2) less for each time you've used a location this game.
    cost_mod = -_SeasideGiantCost()
    # Observe every friendly location use from any zone to keep the per-game
    # counter accurate even before this card is drawn.
    events = UseLocation(FRIENDLY + LOCATION_CARD).after(_LocationUseCounter(SELF))

    class Hand:
        events = UseLocation(FRIENDLY + LOCATION_CARD).after(_LocationUseCounter(SELF))

    class Deck:
        events = UseLocation(FRIENDLY + LOCATION_CARD).after(_LocationUseCounter(SELF))


class VAC_440:
    """Customs Enforcer"""

    # Enemy cards that didn't start in their deck cost (2) more.
    update = Refresh(ENEMY_HAND - STARTING_DECK, {GameTag.COST: 2})


class VAC_441:
    """Package Dealer"""

    # After you draw a card, 50% chance to draw another. (Draw broadcasts ON,
    # not AFTER, so listen on ON.)
    events = Draw(CONTROLLER).on(_PackageDealerDraw(SELF))


class VAC_442:
    """Lamplighter"""

    # Battlecry: Deal @ damage (Improved by each turn in a row you've played an
    # Elemental).
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, _LamplighterDamage())

    def custom_cardtext(self):
        player = getattr(self, "controller", None)
        n = 1
        if player is not None:
            # Playing Lamplighter counts this turn's Elemental, so preview
            # streak + 1 (matches the damage it would deal).
            n = max(player.azerite_elemental_streak + 1, 1)
        return self.data.description.replace("@", str(n))

    def cardtext_entity_0(self):
        player = getattr(self, "controller", None)
        if player is None:
            return 1
        n = player.azerite_elemental_streak
        if player.elemental_played_this_turn > 0:
            n += 1
        return max(n, 1)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


class VAC_444:
    """Overplanner"""

    # Battlecry: Discover 3 cards in your deck to put on top in that order.
    play = _OverplannerDiscover(SELF)


class VAC_446:
    """A. F. Kay"""

    # At the end of your turn, give all other friendly minions that didn't
    # attack +2/+2.
    events = OWN_TURN_END.on(
        Buff(FRIENDLY_MINIONS - SELF - (NUM_ATTACKS_THIS_TURN >= 1), "VAC_446e")
    )


class VAC_446e:
    """AFK"""

    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class VAC_447:
    """Dread Deserter"""

    # Has Charge if this didn't start in your deck.
    update = Find(SELF - STARTING_DECK) & Refresh(SELF, {GameTag.CHARGE: 1})


class VAC_461:
    """Drink Server"""

    # Deathrattle: Get a random Drink spell. (It has 3 uses!)
    deathrattle = Give(CONTROLLER, RandomID(*DRINK_SPELLS))


class VAC_463:
    """Concierge"""

    # Your cards from another class cost (1) less.
    update = Refresh(FRIENDLY_HAND + OTHER_CLASS, {GameTag.COST: -1})


class VAC_521:
    """Bumbling Bellhop"""

    # Taunt Battlecry: If you're holding a spell that costs (5) or more, summon
    # a copy of this.
    play = Find(FRIENDLY_HAND + SPELL + (COST >= 5)) & Summon(CONTROLLER, Copy(SELF))


class VAC_523:
    """Mixologist"""

    # Battlecry: Craft a custom 1-Cost Potion.
    play = _MixologistCraft(SELF)


class VAC_523t:
    """Mixologist's Special"""

    # {0} {1} — a custom potion combining two random potion halves. The
    # combined effect is data-driven cosmetic placeholders; rendered here as a
    # benign no-op so it can be played without crashing.
    play = None


class VAC_529:
    """Scrapbooking Student"""

    # Battlecry: Summon a copy of a friendly location.
    play = Summon(CONTROLLER, Copy(RANDOM(IN_PLAY + FRIENDLY + LOCATION_CARD)))


class VAC_531:
    """Bayfin Bodybuilder"""

    # After a minion is summoned for your opponent during your turn, Silence
    # and destroy it.
    events = Summon(OPPONENT, MINION).after(_BayfinDestroyToken(SELF, Summon.CARD))


class VAC_532:
    """Coconut Cannoneer"""

    # After an adjacent minion attacks, deal 1 damage to a random enemy.
    events = Attack(ADJACENT(SELF) + FRIENDLY).after(Hit(RANDOM(ENEMY_CHARACTERS), 1))


class VAC_702:
    """Marin the Manager"""

    # Battlecry: Choose a fantastic treasure. Shuffle the other 3 into your
    # deck.
    play = _MarinChooseTreasure(SELF)


class VAC_702t:
    """Zarog's Crown"""

    # Discover a Legendary minion. Summon two copies of it. (ExactCopy per
    # summon — re-summoning Discover.CARD directly would no-op the second.)
    play = Discover(CONTROLLER, RandomLegendaryMinion()).then(
        Summon(CONTROLLER, ExactCopy(Discover.CARD)) * 2
    )


class VAC_702t2:
    """Tolin's Goblet"""

    # Draw a card. Fill your hand with copies of it.
    play = _TolinGobletFill(SELF)


class VAC_702t3:
    """Wondrous Wand"""

    # Draw 3 cards. Reduce their Costs to (0).
    play = Draw(CONTROLLER).then(Buff(Draw.CARD, "VAC_702t3e")) * 3


@custom_card
class VAC_702t3e:
    tags = {
        GameTag.CARDNAME: "Wondrous Wand",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -100,
    }


class VAC_702t4:
    """Golden Kobold"""

    # Taunt Battlecry: Replace your hand with Legendary minions.
    play = _GoldenKoboldReplace(SELF)


class VAC_924:
    """Weapons Attendant"""

    # Battlecry: If you control another Pirate, equip a random weapon from your
    # deck.
    play = Find(FRIENDLY_MINIONS + PIRATE - SELF) & Summon(
        CONTROLLER, RANDOM(FRIENDLY_DECK + WEAPON)
    )


class VAC_934:
    """Beached Whale"""

    # Taunt Battlecry: Deal 10 damage to this minion.
    play = Hit(SELF, 10)


class VAC_935:
    """Carry-On Grub"""

    # Battlecry: Get a 1-Cost Suitcase. Pack the top 2 cards of your deck into
    # it.
    play = _CarryOnPack(SELF)


class VAC_935e:
    """Carry-On Enchantment Tracker"""


class VAC_935t:
    """Carry-On Suitcase"""

    # Get {0} and {1}.
    play = _CarryOnOpen(SELF)


class VAC_935t2:
    """Carry-On Suitcase"""

    # Get {0}.
    play = _CarryOnOpen(SELF)


class VAC_936:
    """Octo-masseuse"""

    # Deals octuple damage to minions.
    events = Attack(SELF, MINION).on(_OctoDamage(SELF, Attack.DEFENDER))


class VAC_937:
    """Sailboat Captain"""

    # Battlecry: Give a friendly Pirate Windfury.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_RACE: Race.PIRATE,
    }
    play = GiveWindfury(TARGET)


class VAC_938:
    """Hozen Roughhouser"""

    # Whenever another friendly Pirate attacks, give it +1/+1.
    events = Attack(FRIENDLY + PIRATE - SELF).on(Buff(Attack.ATTACKER, "VAC_938e"))


class VAC_938e:
    """Roughhousing"""

    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class VAC_946:
    """Terrible Chef"""

    # Battlecry: Summon a 0/2 Nerubian Egg. Deathrattle: Destroy it.
    play = Summon(CONTROLLER, "FP1_007").then(_ChefRemember(SELF, Summon.CARD))
    deathrattle = _ChefDestroyEgg(SELF)


class VAC_947:
    """Wave Pool Thrasher"""

    # Battlecry: Give all other minions -1/-1. Deathrattle: Give all other
    # minions +1/+1.
    play = Buff(ALL_MINIONS - SELF, "VAC_947e1")
    deathrattle = Buff(ALL_MINIONS - SELF, "VAC_947e2")


class VAC_947e1:
    """Low Tide"""

    # -1/-1.
    tags = {GameTag.ATK: -1, GameTag.HEALTH: -1}


class VAC_947e2:
    """High Tide"""

    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class VAC_955:
    """Gorgonzormu"""

    # Battlecry: Get a 2-Cost Cheese that summons three 1-Cost minions. It
    # upgrades each turn.
    play = Give(CONTROLLER, "VAC_955t")


class VAC_955t:
    """Delicious Cheese"""

    # Summon three random @-Cost minions. (Upgrades each turn!)
    play = Summon(CONTROLLER, RandomMinion(cost=_CheeseCost())) * 3

    class Hand:
        events = OWN_TURN_END.on(_GorgonzormuUpgrade(SELF))

    def custom_cardtext(self):
        return self.data.description.replace(
            "@", str(getattr(self, "_cheese_cost", 1))
        )

    def cardtext_entity_0(self):
        return getattr(self, "_cheese_cost", 1)

    tags = {
        enums.CUSTOM_CARDTEXT: custom_cardtext,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


class VAC_956:
    """XB-931 Housekeeper"""

    # After you use a location, gain 3 Armor.
    events = UseLocation(FRIENDLY + LOCATION_CARD).after(GainArmor(FRIENDLY_HERO, 3))


class VAC_958:
    """Adaptive Amalgam"""

    # This has all minion types. Deathrattle: Shuffle this into your deck. It
    # keeps any enchantments.
    deathrattle = Shuffle(CONTROLLER, SELF)


class VAC_959:
    """Griftah, Trusted Vendor"""

    # Battlecry: Discover an amazing Amulet to give to both players. (The
    # enemy's is a phony version!)
    play = _AmuletGiveBoth(SELF)


##
# Griftah amulets — real (controller) versions and phony (opponent) versions.


class VAC_959t01:
    """Amulet of Passions"""

    # Take control of an enemy minion until the end of your turn. (It has 1
    # Attack this turn!) — the REAL version (controller) has no attack
    # penalty.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Steal(TARGET), Buff(TARGET, "VAC_959t01e")


class VAC_959t01e:
    """Powerful Passions"""

    # This minion has switched controllers this turn — return it to its owner
    # at end of turn.
    events = [
        TURN_END.on(Steal(OWNER, OWNER_OPPONENT)),
        Silence(OWNER).on(Steal(OWNER, OWNER_OPPONENT)),
    ]
    tags = {GameTag.CHARGE: True}


class VAC_959t01t:
    """Amulet of Passions"""

    # Phony version (given to the enemy): take control of an enemy minion but
    # it only has 1 Attack this turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Steal(TARGET), Buff(TARGET, "VAC_959t01e"), Buff(TARGET, "VAC_959t01e2")


class VAC_959t01e2:
    """Phony Passions"""

    # Attack set to 1 this turn.
    atk = lambda self, i: 1


class VAC_959t05:
    """Amulet of Tracking"""

    # Get 3 random Legendary cards. (Then transform them into Commons!) —
    # phony given to enemy.
    play = _AmuletTrackingGet(SELF)


class VAC_959t05t:
    """Amulet of Tracking"""

    # Real version: Get 3 random Legendary cards (any type).
    play = Give(CONTROLLER, RandomCollectible(rarity=Rarity.LEGENDARY)) * 3


class VAC_959t06:
    """Amulet of Critters"""

    # Summon a random 4-Cost minion and give it Taunt. (It can't attack!) —
    # phony given to enemy.
    play = Summon(CONTROLLER, RandomMinion(cost=4)).then(
        Taunt(Summon.CARD), Buff(Summon.CARD, "VAC_959t06e")
    )


class VAC_959t06e:
    """Forgery"""

    # Can't attack. (CANT_ATTACK tag lives in data.)


class VAC_959t06t:
    """Amulet of Critters"""

    # Real version: Summon a random 4-Cost minion and give it Taunt.
    play = Summon(CONTROLLER, RandomMinion(cost=4)).then(Taunt(Summon.CARD))


class VAC_959t07:
    """Amulet of Warding"""

    # Deal $6 damage. (To a minion!) — phony given to enemy.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_MINION_TARGET: 0}
    play = Hit(TARGET, 6)


class VAC_959t07t:
    """Amulet of Warding"""

    # Real version: Deal $6 damage (any target).
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 6)


class VAC_959t08:
    """Amulet of Energy"""

    # Restore #12 Health to your hero. (Then take $6 damage!) — phony.
    play = Heal(FRIENDLY_HERO, 12), Hit(FRIENDLY_HERO, 6)


class VAC_959t08t:
    """Amulet of Energy"""

    # Real version: Restore #12 Health to your hero.
    play = Heal(FRIENDLY_HERO, 12)


class VAC_959t09:
    """Amulet of Mobility"""

    # Draw 3 cards. (Discard 2 of them!) — phony.
    play = Draw(CONTROLLER) * 3, Discard(RANDOM(FRIENDLY_HAND)) * 2


class VAC_959t09t:
    """Amulet of Mobility"""

    # Real version: Draw 3 cards.
    play = Draw(CONTROLLER) * 3


class VAC_959t10:
    """Amulet of Strides"""

    # Reduce the Cost of all cards in your hand by (1). (Except for spells!) —
    # phony.
    play = Buff(FRIENDLY_HAND - SPELL, "VAC_959t10e")


@custom_card
class VAC_959t10e:
    tags = {
        GameTag.CARDNAME: "Amulet of Strides",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class VAC_959t10t:
    """Amulet of Strides"""

    # Real version: Reduce the Cost of all cards in your hand by (1).
    play = Buff(FRIENDLY_HAND, "VAC_959t10e")


##
# Ungrouped non-collectible tokens


class VAC_320:
    """Seafloor Trawler"""

    # Battlecry: Dredge. Each player draws a card.
    play = Dredge(CONTROLLER), Draw(CONTROLLER), Draw(OPPONENT)


class VAC_422e:
    """Tourist VFX Enchantment"""


class VAC_COIN1:
    """The Coin"""

    # Gain 1 Mana Crystal this turn only.
    play = GainMana(CONTROLLER, 1)


class VAC_COIN2:
    """The Coin"""

    # Gain 1 Mana Crystal this turn only.
    play = GainMana(CONTROLLER, 1)
