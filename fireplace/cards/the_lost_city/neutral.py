from ..utils import *

from hearthstone.enums import CardType, Rarity, Race


##
# Tokens (shared / referenced ids)

PLANT_TOKEN = "UNG_999t2t1"   # 1/1 Plant
ROCK_TOKEN = "WW_001t"        # 1-Cost Rock spell, "Deal 3 damage."


def _custom_buff(card_id, name, tags):
    """Register an enchantment id that does NOT exist in the card data."""

    full_tags = dict(tags)
    full_tags[GameTag.CARDNAME] = name
    full_tags[GameTag.CARDTYPE] = CardType.ENCHANTMENT

    cls = type(card_id, (), {"tags": full_tags})
    return custom_card(cls)


# Enchantments not present in the card data.
_custom_buff("TLC_242_plusbuff", "Ancient Might",
             {GameTag.ATK: 1, GameTag.HEALTH: 1})
_custom_buff("TLC_245_atk", "Primal Fury", {GameTag.ATK: 3})
_custom_buff("TLC_253_buff", "Petrified Growth",
             {GameTag.ATK: 2, GameTag.HEALTH: 2})
_custom_buff("TLC_244_cost", "Curious", {GameTag.COST: -2})
_custom_buff("TLC_829se_dyn", "Devoured", {})
_custom_buff("TLC_831e_dyn", "Stolen Health", {})


##
# Choose-to-gain (3-option) battlecry helper.
#
# TLC_242 / TLC_245 / TLC_246 each say "Battlecry: Choose to gain <A>, <B>,
# or <C>." but the data carries no choose sub-cards, so we present the three
# options as ENCHANTMENT marker cards through a custom Choice; on pick we run
# the option's action list against the parent battlecry minion (SELF) and
# discard the marker cards (nothing enters the hand).


class _GainChoice(Choice):
    """Choice variant for "Choose to gain": the picked option card's
    `_gain_actions` are queued against the parent minion, no card kept."""

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        parent = self.source
        actions = getattr(card, "_gain_actions", None)
        if actions:
            self.source.game.queue_actions(parent, list(actions))
        for c in self.cards:
            c.discard()
        self.trigger_choice_callback()


class _ChooseGain(TargetedAction):
    """Queue a `_GainChoice` of the given (label_id, actions) options; the
    chosen option's actions run against `source` (the battlecry minion)."""

    TARGET = ActionArg()

    def get_target_args(self, source, target):
        return [self._args[1]]

    def do(self, source, target, options):
        player = source.controller
        cards = []
        for label_id, actions in options:
            c = player.card(label_id, source=source)
            c.controller = player
            c._gain_actions = actions
            cards.append(c)
        choice = _GainChoice(CONTROLLER, cards)
        source.game.queue_actions(source, [choice])


# Marker label cards for the three-option choices (no data backing). They are
# SPELL tokens so they can be cleanly discarded after the choice resolves.
@custom_card
class TLC_CHOICE_A:
    tags = {
        GameTag.CARDNAME: "Option A",
        GameTag.CARDTYPE: CardType.SPELL,
    }


@custom_card
class TLC_CHOICE_B:
    tags = {
        GameTag.CARDNAME: "Option B",
        GameTag.CARDTYPE: CardType.SPELL,
    }


@custom_card
class TLC_CHOICE_C:
    tags = {
        GameTag.CARDNAME: "Option C",
        GameTag.CARDTYPE: CardType.SPELL,
    }


##
# Custom actions


class _RelicMinerMill(TargetedAction):
    """Destroy the top card of the controller's deck, then Discover a card
    of the same Rarity."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        if not player.deck:
            return
        top = player.deck[-1]
        rarity = Rarity(int(top.rarity))
        top.discard()
        picker = RandomCard(rarity=rarity, collectible=True)
        # Guard against an empty pool (e.g. a FREE/basic top card has no
        # standard-collectible peers) so we don't leave a stuck empty choice.
        if not picker.find_cards(source):
            return
        source.game.queue_actions(
            source, [Discover(player, picker).then(Give(player, Discover.CARD))]
        )


class _EshoCheck(TargetedAction):
    """If every minion in the controller's deck shares a minion type, give
    the controller's other minions +2/+2 (wherever they are)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        deck_minions = [c for c in player.deck if c.type == CardType.MINION]
        if not deck_minions:
            return
        shared = None
        for m in deck_minions:
            races = set(m.races or [])
            if not races:
                return
            shared = races if shared is None else (shared & races)
            if not shared:
                return
        targets = (
            [c for c in player.field if c is not source]
            + [c for c in player.hand if c.type == CardType.MINION]
            + [c for c in player.deck if c.type == CardType.MINION]
        )
        for t in targets:
            source.game.queue_actions(source, [Buff(t, "TLC_110e")])


class _DissolvingOoze(TargetedAction):
    """Destroy a friendly minion; put a Bones card carrying its Attack and
    Health into the controller's hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        atk = target.atk
        health = target.health
        source.game.queue_actions(source, [Destroy(target)])
        bones = source.controller.card("TLC_829t", source=source)
        bones.controller = source.controller
        bones.zone = Zone.HAND
        if bones.zone == Zone.HAND:
            source.game.queue_actions(
                source, [Buff(bones, "TLC_829te", atk=atk, max_health=health)]
            )


class _PetrifiedTurn(TargetedAction):
    """While Dormant at the start of the controller's turn: 50% to awaken,
    else gain +2/+2."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not target.dormant:
            return
        if source.game.random.random() < 0.5:
            source.game.queue_actions(source, [Awaken(target)])
        else:
            source.game.queue_actions(source, [Buff(target, "TLC_253_buff")])


class _TortollanBuff(TargetedAction):
    """At end of turn, give +1/+1 to each friendly minion of a different
    minion type (one buff per distinct type signature)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        seen = set()
        for m in list(player.field):
            key = tuple(sorted(r.value for r in (m.races or [])))
            if key in seen:
                continue
            seen.add(key)
            source.game.queue_actions(source, [Buff(m, "TLC_254e")])


class _CrystalTender(TargetedAction):
    """Gain empty Mana Crystals until both players have the same max Mana."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        diff = player.opponent.max_mana - player.max_mana
        if diff > 0:
            source.game.queue_actions(source, [GainEmptyMana(player, diff)])


class _ScalehideKodo(TargetedAction):
    """Destroy the lowest-Attack enemy minion; with Kindred, the highest
    Attack instead."""

    TARGET = ActionArg()

    def do(self, source, target):
        enemies = list(source.controller.opponent.field)
        if not enemies:
            return
        if kindred_active(source):
            pick = max(enemies, key=lambda m: m.atk)
        else:
            pick = min(enemies, key=lambda m: m.atk)
        source.game.queue_actions(source, [Destroy(pick)])


class _StranglevineDeath(TargetedAction):
    """Give a random friendly minion a random Bonus Effect and this
    Deathrattle (TLC_465e)."""

    TARGET = ActionArg()

    BONUS_EFFECTS = [
        {GameTag.TAUNT: True},
        {GameTag.DIVINE_SHIELD: True},
        {GameTag.POISONOUS: True},
        {GameTag.WINDFURY: True},
        {GameTag.RUSH: True},
        {GameTag.LIFESTEAL: True},
    ]

    def do(self, source, target):
        friendly = list(source.controller.field)
        if not friendly:
            return
        pick = source.game.random.choice(friendly)
        tags = source.game.random.choice(self.BONUS_EFFECTS)
        source.game.queue_actions(source, [SetTags(pick, tags)])
        source.game.queue_actions(source, [Buff(pick, "TLC_465e")])


class _KrogSetStats(TargetedAction):
    """Set the Attack and Health of all enemy minions to 1 via a dynamic
    override enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        targets = target if isinstance(target, list) else [target]
        for m in targets:
            source.game.queue_actions(source, [Buff(m, "TLC_480e_dyn")])


class _PlatysaurDraw(TargetedAction):
    """Draw a card and remember it for the Deathrattle discard."""

    TARGET = ActionArg()

    def do(self, source, target):
        before = set(id(c) for c in target.hand)
        source.game.queue_actions(source, [Draw(target)])
        drawn = [c for c in target.hand if id(c) not in before]
        source._platysaur_card = drawn[0] if drawn else None


class _PlatysaurDiscard(TargetedAction):
    """Discard the card drawn by the battlecry, if still in hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        card = getattr(source, "_platysaur_card", None)
        if card is not None and card.zone == Zone.HAND:
            card.discard()


class _RavenousDevilsaur(TargetedAction):
    """Destroy a minion; with Kindred, gain its stats first."""

    TARGET = ActionArg()

    def do(self, source, target):
        if kindred_active(source):
            atk = target.atk
            health = target.health
            source.game.queue_actions(
                source, [Buff(source, "TLC_829se_dyn", atk=atk, max_health=health)]
            )
        source.game.queue_actions(source, [Destroy(target)])


class _PterrordaxSteal(TargetedAction):
    """The summoned Pterrordax steals 1 Health from all OTHER minions: this is
    a permanent Health *steal* (mirror the GDB K'ara pattern) — each other
    minion has its max Health reduced by 1 (TLC_831e "Pterrified | Reduced
    Health."), and the Pterrordax gains +1 max Health per minion stolen from.
    It is NOT removable damage: victims end undamaged at their new lower max."""

    TARGET = ActionArg()

    def do(self, source, target):
        pterrordax = target
        others = [
            m for m in source.game.board
            if m.type == CardType.MINION and m is not pterrordax
        ]
        if not others:
            return
        for m in others:
            source.game.queue_actions(
                source, [Buff(m, "TLC_831e", max_health=-1)]
            )
        source.game.queue_actions(
            source, [Buff(pterrordax, "TLC_831e_dyn", max_health=len(others))]
        )


class _QuestingAssistant(TargetedAction):
    """If the controller played a Quest this game, deal 2 damage to target."""

    TARGET = ActionArg()

    def do(self, source, target):
        played_quest = any(
            c.tags.get(GameTag.QUEST) or c.tags.get(GameTag.SIDEQUEST)
            for c in source.controller.cards_played_this_game
        )
        if played_quest and target is not None:
            source.game.queue_actions(source, [Hit(target, 2)])


class _PrimalfinArm(TargetedAction):
    """Set the controller's next-Kindred-double flag (Primalfin Challenger).
    Approximation: not all Kindred bonuses honour the flag yet."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_kindred_double = 1


##
# Crater Gator — "enemy hero can't be healed" by swapping in a heal-blocking
# subclass on the hero instance; restored at our next turn start.


def _heal_block_active(hero):
    return any(getattr(b, "_tlc_is_heal_block", False) for b in hero.buffs)


def _install_heal_block(hero):
    if getattr(hero, "_tlc_heal_block_installed", False):
        return
    base = type(hero)

    class _HealBlocked(base):
        @property
        def damage(self):
            return self.__dict__.get("_tlc_damage_value", 0)

        @damage.setter
        def damage(self, value):
            cur = self.__dict__.get("_tlc_damage_value", 0)
            # Block heals (damage decreases) while a heal-block enchant is live.
            if value < cur and _heal_block_active(self):
                return
            self.__dict__["_tlc_damage_value"] = value

    hero.__dict__["_tlc_damage_value"] = getattr(hero, "damage", 0)
    hero._tlc_heal_block_installed = True
    hero.__class__ = _HealBlocked


##
# Dynamic stat enchant: set Attack and Health to exactly 1 (Krog).

@custom_card
class TLC_480e_dyn:
    tags = {
        GameTag.CARDNAME: "Cratered",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }

    def apply(self, target):
        target.damage = 0

    def atk(self, i):
        return 1

    def max_health(self, i):
        return 1


##
# Minions


class TLC_100:
    """Elise the Navigator"""

    # Battlecry: If your deck started with 10 cards of different Costs, craft
    # a custom location.
    # Approximation: the "10 different costs" deckbuilding constraint is not
    # checked; we always craft the basic Un'Goro Jungle custom location.
    play = Summon(CONTROLLER, "TLC_100t1")


class TLC_101:
    """Undercover Cultist"""

    # Taunt, Reborn. Has +3 Attack while damaged.
    update = Find(SELF + DAMAGED) & Refresh(SELF, {GameTag.ATK: 3})


class TLC_102:
    """Torga"""

    # Battlecry: Draw a Kindred card and another card that activates it.
    # Approximation: draws two cards (no Kindred-pair identification).
    play = Draw(CONTROLLER) * 2


class TLC_106:
    """Endbringer Umbra"""

    # Battlecry: Trigger the Deathrattles of 5 friendly minions that died
    # this game.
    def play(self):
        triggered = 0
        for minion in list(self.controller.graveyard):
            if triggered >= 5:
                break
            if minion.type == CardType.MINION and minion.has_deathrattle:
                triggered += 1
                yield Deathrattle(minion)


class TLC_107:
    """Stormbrewer"""

    # Whenever this attacks, deal 3 damage to the target first.
    # Kindred: Gain Rush.
    events = Attack(SELF).on(Hit(Attack.DEFENDER, 3))
    play = Kindred() & SetTags(SELF, {GameTag.RUSH: True})


class TLC_109:
    """Relic Miner"""

    # Battlecry: Destroy the top card of your deck. Discover a card of the
    # same Rarity.
    play = _RelicMinerMill(CONTROLLER)


class TLC_110:
    """City Chief Esho"""

    # Battlecry: If every minion in your deck shares a minion type, give your
    # other minions +2/+2 (wherever they are).
    play = _EshoCheck(CONTROLLER)


class TLC_110e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TLC_242:
    """Ancient Stegodon"""

    # Battlecry: Choose to gain Taunt, Poisonous, or +1/+1.
    play = _ChooseGain(SELF, [
        ("TLC_CHOICE_A", [SetTags(SELF, {GameTag.TAUNT: True})]),
        ("TLC_CHOICE_B", [SetTags(SELF, {GameTag.POISONOUS: True})]),
        ("TLC_CHOICE_C", [Buff(SELF, "TLC_242_plusbuff")]),
    ])


class TLC_243:
    """Whirling Stormdrake"""

    # Rush, Windfury. Kindred: Gain Immune this turn.
    play = Kindred() & Buff(SELF, "TLC_243_immune")


@custom_card
class TLC_243_immune:
    tags = {
        GameTag.CARDNAME: "Immune (Stormdrake)",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.CANT_BE_DAMAGED: True,
        GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
    }
    events = OWN_TURN_END.on(Destroy(SELF))


class TLC_244:
    """Curious Explorer"""

    # Deathrattle: Reduce the Cost of a minion in your opponent's hand by (2).
    deathrattle = Buff(RANDOM(ENEMY_HAND + MINION), "TLC_244_cost")


class TLC_245:
    """Ancient Raptor"""

    # Battlecry: Choose to gain +3 Attack, Divine Shield, or "Deathrattle:
    # Summon two 1/1 Plants."
    play = _ChooseGain(SELF, [
        ("TLC_CHOICE_A", [Buff(SELF, "TLC_245_atk")]),
        ("TLC_CHOICE_B", [SetTags(SELF, {GameTag.DIVINE_SHIELD: True})]),
        ("TLC_CHOICE_C", [Buff(SELF, "TLC_245_deathrattle")]),
    ])


@custom_card
class TLC_245_deathrattle:
    tags = {
        GameTag.CARDNAME: "Hatching Plants",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, PLANT_TOKEN) * 2


class TLC_246:
    """Ancient Pterrordax"""

    # Battlecry: Choose to gain Stealth until your next turn, Elusive, or
    # Windfury.
    play = _ChooseGain(SELF, [
        ("TLC_CHOICE_A", [Buff(SELF, "TLC_246_stealth")]),
        ("TLC_CHOICE_B", [SetTags(SELF, {
            GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
            GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
        })]),
        ("TLC_CHOICE_C", [SetTags(SELF, {GameTag.WINDFURY: True})]),
    ])


@custom_card
class TLC_246_stealth:
    tags = {
        GameTag.CARDNAME: "Stealthed (Pterrordax)",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.STEALTH: True,
    }
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


class TLC_247:
    """Primal Sabretooth"""

    # Stealth. After this attacks and kills a minion, get a copy of it.
    events = Attack(SELF, ALL_MINIONS).after(
        Dead(Attack.DEFENDER) & Give(CONTROLLER, Copy(Attack.DEFENDER))
    )


class TLC_248:
    """Ultragigasaur"""

    # Vanilla 11/14/28 (Rush is a data tag).
    pass


class TLC_249:
    """Sizzling Cinder"""

    # Deathrattle: Deal 2 damage randomly split among all enemies.
    deathrattle = Hit(RANDOM(ENEMY_CHARACTERS), 1) * 2


class TLC_250:
    """Crater Gator"""

    # Battlecry: Until the start of your next turn, the enemy hero can't be
    # healed.
    play = Buff(ENEMY_HERO, "TLC_250e")


class TLC_250e:
    def apply(self, target):
        self._tlc_is_heal_block = True
        _install_heal_block(target)

    events = OWN_TURN_BEGIN.on(Destroy(SELF))


class TLC_251:
    """Primalfin Challenger"""

    # Battlecry: Your next Kindred triggers twice.
    play = _PrimalfinArm(CONTROLLER)


class TLC_252:
    """Dissolving Ooze"""

    # Battlecry: Destroy a friendly minion. Spit out the Bones of its Attack
    # and Health into your hand.
    play = _DissolvingOoze(TARGET)
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
    }


class TLC_253:
    """Petrified Ogre"""

    # Starts Dormant. While Dormant, gain +2/+2 at the start of your turn.
    # (50% chance to awaken instead.)
    tags = {GameTag.DORMANT: True}
    dormant_events = OWN_TURN_BEGIN.on(_PetrifiedTurn(SELF))


class TLC_254:
    """Tortollan Storyteller"""

    # At the end of your turn, give +1/+1 to each friendly minion of a
    # different type.
    events = OWN_TURN_END.on(_TortollanBuff(CONTROLLER))


class TLC_254e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TLC_255:
    """Crystal Tender"""

    # Tradeable. Battlecry: Gain empty Mana Crystals until both players have
    # the same Mana. (Tradeable is a data tag handled by the engine.)
    play = _CrystalTender(CONTROLLER)


class TLC_256:
    """Marshland Thresher"""

    # After you cast a spell, gain Divine Shield.
    events = Play(CONTROLLER, SPELL).after(
        SetTags(SELF, {GameTag.DIVINE_SHIELD: True})
    )


class TLC_427:
    """Rockskipper"""

    # Battlecry: Get a 1-Cost Rock that deals 3 damage.
    play = Give(CONTROLLER, ROCK_TOKEN)


class TLC_429:
    """Steamfin Thief"""

    # Kindred: Summon two 1/1 Murlocs with Rush.
    play = Kindred() & (Summon(CONTROLLER, "TLC_429t") * 2)


class TLC_454:
    """Scalehide Kodo"""

    # Battlecry: Destroy the lowest Attack enemy minion. Kindred: The highest
    # Attack instead.
    play = _ScalehideKodo(SELF)


class TLC_465:
    """Stranglevine"""

    # Deathrattle: Give a random friendly minion a random Bonus Effect and
    # this Deathrattle.
    # Data bump (Patch 35.0, build 237510) dropped the DEATHRATTLE GameTag
    # from the base card data, so declare it here to keep has_deathrattle
    # live and fire the scripted deathrattle.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _StranglevineDeath(CONTROLLER)


class TLC_465e:
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _StranglevineDeath(CONTROLLER)


class TLC_468:
    """Blob of Tar"""

    # Poisonous, Taunt. Deathrattle: Summon a 1/2 Blob with Poisonous and a
    # 1/2 Blob with Taunt.
    deathrattle = (
        Summon(CONTROLLER, "TLC_468t1"),
        Summon(CONTROLLER, "TLC_468t2"),
    )


class TLC_480:
    """Krog, Crater King"""

    # At the end of your turn, set the Attack and Health of all enemy minions
    # to 1.
    events = OWN_TURN_END.on(_KrogSetStats(ENEMY_MINIONS))


class TLC_603:
    """Platysaur"""

    # Battlecry: Draw a card. Deathrattle: Discard it.
    play = _PlatysaurDraw(CONTROLLER)
    deathrattle = _PlatysaurDiscard(SELF)


class TLC_605:
    """Tar Tyrant"""

    # Taunt, Lifesteal. Has +6 Attack during your opponent's turn.
    update = Find(CURRENT_PLAYER + OPPONENT) & Refresh(SELF, {GameTag.ATK: 6})


class TLC_621:
    """Willful Watcher"""

    # Taunt. Deathrattle: Destroy the top 3 cards of your deck.
    deathrattle = Mill(CONTROLLER) * 3


class TLC_829:
    """Ravenous Devilsaur"""

    # Battlecry: Destroy a minion. Kindred: Gain its stats.
    play = _RavenousDevilsaur(TARGET)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }


class TLC_831:
    """Pterrordax Egg"""

    # Deathrattle: Summon a 3/3 Pterrordax that steals 1 Health from all
    # other minions.
    deathrattle = Summon(CONTROLLER, "TLC_831t").then(
        _PterrordaxSteal(Summon.CARD)
    )


class TLC_888:
    """Cloud Serpent"""

    # Battlecry: Get a copy of another Elemental or Dragon in your hand.
    play = Give(
        CONTROLLER,
        Copy(RANDOM((FRIENDLY_HAND + (ELEMENTAL | DRAGON)) - SELF)),
    )


class TLC_987:
    """Questing Assistant"""

    # Battlecry: If you played a Quest this game, deal 2 damage.
    play = _QuestingAssistant(TARGET)
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}


##
# ---------------------------------------------------------------------------
# The Lost City of Un'Goro MINI-SET — Dinosaurs (DINO_ prefix), NEUTRAL.
# ---------------------------------------------------------------------------


class _TakaGain(TargetedAction):
    """Beast Speaker Taka — gain the Discovered Legendary Beast's stats and
    remember it so the Deathrattle can summon a real copy of it."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        if card is None:
            return
        if isinstance(card, list):
            if not card:
                return
            card = card[0]
        source._taka_card_id = card.id
        source.game.queue_actions(
            source,
            [Buff(source, "DINO_430e", atk=card.atk, max_health=card.health)],
        )


class _TakaDeathrattle(TargetedAction):
    """Summon the Legendary Beast that Taka gained its stats from."""

    TARGET = ActionArg()

    def do(self, source, target):
        cid = getattr(source, "_taka_card_id", None)
        if cid:
            source.game.queue_actions(source, [Summon(source.controller, cid)])


class DINO_410:
    """The Egg of Khelos"""

    # Deathrattle: Summon a slightly cracked Egg. (Break 5 times to hatch into
    # a 20/20 Beast!)  The egg chain is a sequence of tokens, each whose own
    # Deathrattle summons the next, until the 20/20 Khelos hatches.
    deathrattle = Summon(CONTROLLER, "DINO_410t2")


class DINO_410t2:
    """The Egg of Khelos"""

    # Deathrattle: Summon a more cracked Egg.
    deathrattle = Summon(CONTROLLER, "DINO_410t3")


class DINO_410t3:
    """The Egg of Khelos"""

    # Deathrattle: Summon a very cracked Egg.
    deathrattle = Summon(CONTROLLER, "DINO_410t4")


class DINO_410t4:
    """The Egg of Khelos"""

    # Deathrattle: Summon the most cracked Egg.
    deathrattle = Summon(CONTROLLER, "DINO_410t5")


class DINO_410t5:
    """The Egg of Khelos"""

    # Deathrattle: Summon a 20/20 Khelos. (Break to hatch!)
    deathrattle = Summon(CONTROLLER, "DINO_410t")


class DINO_410t:
    """Khelos"""

    # 20/20 Beast — the hatched dinosaur (vanilla stats from data).
    pass


class DINO_411:
    """Holy Eggbearer"""

    # Battlecry: Draw a 0-Attack minion.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (ATK == 0)))


class DINO_419:
    """Herbivore Assistant"""

    # Battlecry: Give a friendly Beast +2/+2 and Rush.
    play = (
        Buff(TARGET, "DINO_419e", atk=2, max_health=2),
        SetTags(TARGET, {GameTag.RUSH: True}),
    )
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_RACE: Race.BEAST,
    }


class DINO_430:
    """Beast Speaker Taka"""

    # Battlecry: Discover a Legendary Beast from any class to gain its stats.
    # Deathrattle: Summon it.
    play = Discover(CONTROLLER, RandomBeast(rarity=Rarity.LEGENDARY)).then(
        _TakaGain(SELF, Discover.CARD)
    )
    deathrattle = _TakaDeathrattle(SELF)


class DINO_435:
    """Crater Experiment"""

    # Kindred: Summon a copy of this.
    play = Kindred() & Summon(CONTROLLER, Copy(SELF))
