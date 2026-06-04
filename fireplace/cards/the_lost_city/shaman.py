from ..utils import *

from hearthstone.enums import CardType, Race

from ...dsl.evaluator import kindred_active


# The 2/1 "Sizzling Cinder" token (TLC_249) is a collectible Neutral minion
# defined in this package's neutral.py - we summon it by id.
SIZZLING_CINDER = "TLC_249"


##
# Custom actions (defined before the cards that reference them)


class _FlightOfTheFirehawk(TargetedAction):
    """Draw two minions of different minion types from the deck, then give each
    drawn minion +2/+2 (TLC_222e). "Different minion types" = the two drawn
    minions don't share a tribe; a tribeless minion never collides."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        deck_minions = [c for c in player.deck if c.type == CardType.MINION]
        player.game.random.shuffle(deck_minions)
        drawn = []
        first_races = None
        for c in list(deck_minions):
            drawn.append(c)
            first_races = set(c.races) - {Race.INVALID}
            deck_minions.remove(c)
            break
        if drawn:
            for c in deck_minions:
                second_races = set(c.races) - {Race.INVALID}
                if not (first_races and second_races and (first_races & second_races)):
                    drawn.append(c)
                    break
        actions = []
        for c in drawn:
            actions.append(Draw(player, c))
            actions.append(Buff(c, "TLC_222e"))
        if actions:
            source.game.queue_actions(source, actions)


class _MountainMapDiscover(Discover):
    """Discover among minions whose minion type the controller has NOT played
    this game. Pool = collectible minions with at least one tribe not yet
    represented among the controller's played-this-game cards."""

    def get_target_args(self, source, target):
        from ... import cards as card_module

        player = source.controller
        played_races = set()
        for c in player.cards_played_this_game:
            for r in getattr(c, "races", []):
                if r != Race.INVALID:
                    played_races.add(r)

        pool = []
        for cid in card_module.db.filter(collectible=True, type=CardType.MINION):
            card = card_module.db[cid]
            races = [r for r in getattr(card, "races", []) if r != Race.INVALID]
            if not races:
                continue
            if any(r not in played_races for r in races):
                pool.append(cid)

        game = source.game
        if game.is_standard:
            pool = [
                cid for cid in pool
                if getattr(card_module.db[cid], "is_standard", True)
            ]
        if not pool:
            for cid in card_module.db.filter(collectible=True, type=CardType.MINION):
                card = card_module.db[cid]
                if [r for r in getattr(card, "races", []) if r != Race.INVALID]:
                    pool.append(cid)

        chosen = game.random.sample(pool, min(3, len(pool)))
        cards = [player.card(cid, source=source) for cid in chosen]
        return [cards]


##
# Minions


class _VolcanicThrasherDraw(Draw):
    """Draw a Fire spell; if the source's Kindred is active, also give the
    drawn spell the Spell Damage +2 enchant (TLC_223e). Subclassing Draw lets
    us buff the freshly-drawn card while it is in hand (the card is available
    inside Draw.do; a separately-queued draw would not have resolved yet)."""

    def do(self, source, target, card):
        ret = super().do(source, target, card)
        if card is not None and card.zone == Zone.HAND and kindred_active(source):
            source.game.queue_actions(source, [Buff(card, "TLC_223e")])
        return ret


class TLC_223:
    """Volcanic Thrasher"""

    # Battlecry: Draw a Fire spell. Kindred: Give it Spell Damage +2.
    play = _VolcanicThrasherDraw(
        CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + FIRE_SPELL)
    )


class TLC_223e:
    """Volcanic"""

    # Spell Damage +2. (Enchant exists in data but carries no stat tags.)
    tags = {GameTag.SPELLPOWER: 2}


class TLC_224:
    """Mechanized Magma"""

    # Whenever you play a Fire spell, gain stats equal to its Cost.
    events = Play(CONTROLLER, SPELL + FIRE_SPELL).after(
        Buff(SELF, "TLC_224e", atk=COST(Play.CARD), max_health=COST(Play.CARD))
    )


class TLC_225:
    """Cinderfin"""

    # Deathrattle: Summon a 2/1 Sizzling Cinder.
    deathrattle = Summon(CONTROLLER, SIZZLING_CINDER)


class TLC_228:
    """Bralma Searstone"""

    # Your Elementals deal 1 extra damage.
    #
    # APPROXIMATION: the engine has no outgoing-damage hook reachable from a
    # card script (OUTGOING_DAMAGE_ADJUSTMENT is unread), so we model "deal 1
    # extra damage" as a +1 Attack aura on friendly Elementals. Exact for
    # combat damage; does not cover an Elemental's effect damage, and it
    # raises displayed Attack. Aura removed when Bralma leaves play.
    update = Refresh(FRIENDLY_MINIONS + ELEMENTAL - SELF, {GameTag.ATK: 1})


class TLC_482:
    """Slagclaw"""

    # Battlecry: Summon two 2/1 Sizzling Cinders.
    # Kindred: Trigger your Sizzling Cinders' Deathrattles.
    play = (
        Summon(CONTROLLER, SIZZLING_CINDER) * 2,
        Kindred() & Deathrattle(FRIENDLY_MINIONS + ID(SIZZLING_CINDER)),
    )


##
# Spells


class TLC_221:
    """Sizzling Swarm"""

    # Deal $3 damage. Summon that many 2/1 Sizzling Cinders.
    # (No target requirement in data -> hits a random enemy.)
    #
    # "Summon that many" scales with Spell Damage: both the Hit (routes through
    # get_spell_damage) and the Cinder count use 3 + board Spell Damage, so the
    # two stay in lock-step (e.g. +1 SP -> 4 damage and 4 Cinders). Mirrors the
    # Scholomance "Molten Blast" pattern (Summon * SPELL_DAMAGE(N)).
    play = (
        Hit(RANDOM_ENEMY_CHARACTER, 3),
        Summon(CONTROLLER, SIZZLING_CINDER) * SPELL_DAMAGE(3),
    )


class TLC_222:
    """Flight of the Firehawk"""

    # Draw two minions of different minion types. Give them +2/+2.
    play = _FlightOfTheFirehawk(CONTROLLER)


class TLC_222e:
    """Ignited"""

    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class TLC_227:
    """Lava Flow"""

    # Deal $2 damage to the lowest Health enemy, three times. Overload: (1)
    # (Overload is applied automatically from card data.)
    play = Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 2) * 3


class TLC_464:
    """Mountain Map"""

    # Discover a minion with a type you haven't played. If you play it this
    # turn, also pick one of the others (the two un-chosen minions), via the
    # shared DiscoverPickOther machinery.
    play = _MountainMapDiscover(CONTROLLER).then(
        DiscoverPickOther(SELF, Discover.CARDS, Discover.CARD)
    )


class TLC_229:
    """Spirit of the Mountain"""

    # Quest: Play minions of unique types (total from QUEST_PROGRESS_TOTAL data
    # tag, 6 at build 226928). Reward: Ashalon.
    quest = Play(CONTROLLER, MINION).after(AddProgress(SELF, Play.CARD))
    reward = Summon(CONTROLLER, "TLC_229t14")

    def add_progress(self, card):
        # Count each NEW minion type the controller plays. Progress = number
        # of distinct tribes seen so far (a tribeless minion counts as one
        # "typeless" unit). A dual-type minion contributes every new tribe.
        seen = getattr(self, "_tlc_quest_types", None)
        if seen is None:
            seen = set()
            self._tlc_quest_types = seen
        races = [r for r in getattr(card, "races", []) if r != Race.INVALID]
        if not races:
            seen.add("__typeless__")
        else:
            for r in races:
                seen.add(r)
        self.progress = len(seen)

    def clear_progress(self):
        self._tlc_quest_types = set()
        self.progress = 0


class TLC_229t14:
    """Ashalon, Ridge Guardian"""

    # Rush. Battlecry: Adapt twice. For the rest of the game, give minions you
    # play those Adaptations.
    #
    # Rush comes straight from card data (RUSH=1). The double Adapt is fully
    # scripted: Adapt(SELF) * 2 fires two Adapt choices on Ashalon itself.
    #
    # PARTIAL: the persistent "for the rest of the game, give minions you play
    # those Adaptations" clause is NOT modeled. It requires capturing the two
    # chosen Adaptation cards and re-applying their battlecries to every future
    # friendly minion played — there is no card-reachable hook to record the
    # specific adaptation the player picked from Adapt's choice UI (Adapt.choose
    # consumes the pick internally), so it is an engine concern. The directly
    # observable battlecry (Adapt twice on Ashalon) is faithful.
    play = Adapt(SELF) * 2


##
# The Lost City of Un'Goro mini-set (DINO_ / Dinosaurs) — Shaman
#
# Tokens this file summons are defined here as their own classes (none of the
# DINO_ shaman cards summon tokens — DINO_412 GETs a random card to hand).


class _TortotemGet(TargetedAction):
    """Tortotem — get (to hand) a random collectible minion that has two or
    more minion types. We build the multi-type pool ourselves because the
    random-card pickers can't filter on tribe-count. "Multiple minion types"
    means 2+ distinct tribes (a single-tribe or tribeless minion never
    qualifies)."""

    TARGET = ActionArg()

    def do(self, source, target):
        from ... import cards as card_module

        player = source.controller
        pool = []
        for cid in card_module.db.filter(collectible=True, type=CardType.MINION):
            card = card_module.db[cid]
            races = {r for r in getattr(card, "races", []) if r != Race.INVALID}
            if len(races) >= 2:
                pool.append(cid)

        game = source.game
        if game.is_standard:
            pool = [
                cid for cid in pool
                if getattr(card_module.db[cid], "is_standard", True)
            ]
        if not pool:
            return
        cid = game.random.choice(pool)
        source.game.queue_actions(source, [Give(player, cid)])


class DINO_412:
    """Tortotem"""

    # At the end of your turn, get a random minion with multiple minion types.
    events = OWN_TURN_END.on(_TortotemGet(CONTROLLER))


class _ChillspineStegodon(TargetedAction):
    """Chillspine Stegodon battlecry — pick two random enemy minions ONCE,
    deal 2 damage to each, and (with Kindred) Freeze the same two. Capturing
    the targets up front guarantees the Freeze lands on the minions that were
    hit, not a freshly-rolled pair."""

    TARGET = ActionArg()

    def do(self, source, target):
        enemies = [m for m in source.controller.opponent.field if not m.dead]
        picks = source.game.random.sample(enemies, min(2, len(enemies)))
        if not picks:
            return
        actions = [Hit(m, 2) for m in picks]
        if kindred_active(source):
            actions += [SetTag(m, GameTag.FROZEN) for m in picks]
        source.game.queue_actions(source, actions)


class DINO_413:
    """Chillspine Stegodon"""

    # Battlecry: Deal 2 damage to two random enemy minions.
    # Kindred: And Freeze them.
    play = _ChillspineStegodon(SELF)


class DINO_406:
    """Fire Breath"""

    # Deal $4 damage. Give your Elementals +1/+1.
    # (No target requirement in data -> the 4 damage hits a random enemy.)
    play = (
        Hit(RANDOM_ENEMY_CHARACTER, 4),
        Buff(FRIENDLY_MINIONS + ELEMENTAL, "DINO_406e"),
    )


class DINO_406e:
    """Fire Breather"""

    # +1/+1. (Enchant exists in data but carries no stat tags.)
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}
