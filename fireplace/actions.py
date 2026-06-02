from collections import OrderedDict

from hearthstone.enums import (
    BlockType,
    CardClass,
    CardType,
    GameTag,
    Mulligan,
    PlayState,
    Race,
    SpellSchool,
    Step,
    Zone,
)

from .dsl import LazyNum, LazyValue, Selector
from .dsl.copy import Copy, RebornCopy, copy_buffs
from .dsl.random_picker import RandomMinion
from .dsl.selector import *
from .entity import Entity
from .enums import DISCARDED
from .exceptions import InvalidAction
from .logging import log
from .utils import random_class


# Castle Nathria — the three Demon Hunter "Relic" spells. Each cast
# bumps Player.relics_played_this_game; each Relic's effect reads that
# counter to scale ("Improve your future Relics"). Lives here because
# Play.do has to read it inline; not yet a GameTag.
RELIC_IDS = frozenset({"REV_508", "REV_834", "REV_943"})


def _summon_colossal_limbs(source, target, parent):
    """Summon the appendage tokens for a Colossal minion.

    Limbs are tokens whose id is ``{parent.id}t`` / ``t2`` / … and that
    carry the COLOSSAL_LIMB game tag. Some sets also flag specific limbs
    with COLOSSAL_LIMB_ON_LEFT to position them to the left of the parent
    rather than the default right side. Limbs are summoned in the same
    order they appear in the data; on-left limbs are inserted to the left
    of the parent, on-right limbs to the right.
    """
    from .cards import db

    parent_index = (
        parent.controller.field.index(parent) if parent in parent.controller.field else None
    )
    if parent_index is None:
        return

    # Collect limb ids by scanning the DB for tokens prefixed with the
    # parent's id + "t". Ordered numerically.
    limb_ids = sorted(
        cid
        for cid in db
        if cid.startswith(parent.id + "t")
        and db[cid].tags.get(GameTag.COLOSSAL_LIMB, 0)
    )

    right_offset = 1
    left_offset = 0
    placed_limbs = []
    for limb_id in limb_ids:
        limb_card = parent.controller.card(limb_id, source)
        limb_card.controller = parent.controller
        if db[limb_id].tags.get(GameTag.COLOSSAL_LIMB_ON_LEFT, 0):
            limb_card._summon_index = parent.controller.field.index(parent) - left_offset
            left_offset += 1
        else:
            limb_card._summon_index = parent.controller.field.index(parent) + right_offset
            right_offset += 1
        limb_card.zone = Zone.PLAY
        source.game.manager.targeted_action(Summon, source, parent.controller, limb_card)
        placed_limbs.append(limb_card)

    # A Colossal limb may carry a `summoned` self-effect ("When summoned, …").
    # The placement above bypasses the Summon broadcast (limbs go straight into
    # PLAY), so fire each limb's `summoned` actions explicitly here — after all
    # limbs are placed, so per-limb effects see the full board. Without this the
    # limbs' when-summoned text (e.g. Azshara's hero +Attack, Sinestra's Wings'
    # spell gift) would silently never fire when the parent is played/summoned.
    for limb_card in placed_limbs:
        summoned_actions = limb_card.get_actions("summoned")
        if summoned_actions:
            source.game.cheat_action(limb_card, summoned_actions)


def _resolve_mini_id(card):
    """Whizbang's Workshop — resolve the 1-Cost 1/1 "Mini" token paired with
    a MINIATURIZE minion. The pairing lives in the data's
    COLLECTION_RELATED_CARD_DATABASE_ID tag (dbf of the Mini); fall back to
    the "<id>t" naming convention for the few cards that omit it."""
    from .cards import db

    rel = card.data.tags.get(GameTag.COLLECTION_RELATED_CARD_DATABASE_ID, 0)
    if rel and rel in db.dbf:
        return db.dbf[rel]
    candidate = card.id + "t"
    if candidate in db:
        return candidate
    return None


def _resolve_giant_id(card):
    """Whizbang's Workshop mini-set — resolve the 8-Cost 8/8 "Gigantic" token
    paired with a GIGANTIFY minion. Every Gigantic form is an 8-mana 8/8 minion
    keeping the original's text, so pick the unambiguous candidate among the
    related-card tag and the "<id>t" / "<id>t1" naming conventions (MIS_025
    carries both a Mini and a Gigantic token, so name+stats disambiguate)."""
    from .cards import db

    candidates = []
    rel = card.data.tags.get(GameTag.COLLECTION_RELATED_CARD_DATABASE_ID, 0)
    if rel and rel in db.dbf:
        candidates.append(db.dbf[rel])
    candidates += [card.id + "t1", card.id + "t"]
    for cand in candidates:
        if cand in db:
            data = db[cand]
            if (
                data.type == CardType.MINION
                and (data.cost or 0) == 8
                and data.atk == 8
                and data.health == 8
            ):
                return cand
    return None


# The Great Dark Beyond — Starship support.
#
# A "Starship Piece" is a normal minion. When it dies, its stats and effects are
# banked into the controller's Starship: the first banked piece summons a
# Permanent Starship (a dormant, untouchable board entity that carries the
# running combined stats); each later piece adds to it. Launching the Starship
# (LaunchStarship) wakes the Permanent into a real minion whose stats and
# effects are the combined stats and effects of every banked piece.

# Per-class Starship token (the launched/building ship). Classes without a
# unique ship — Mage, Priest, Paladin, Shaman, Warrior and Neutral — fall back
# to the neutral "The Exile's Hope".
_STARSHIP_TOKENS = {
    CardClass.DEATHKNIGHT: "GDB_100t4",
    CardClass.DEMONHUNTER: "GDB_100t5",
    CardClass.DRUID: "GDB_100t6",
    CardClass.HUNTER: "GDB_100t7",
    CardClass.ROGUE: "GDB_100t8",
    CardClass.WARLOCK: "GDB_100t9",
}

# Keyword GameTags carried over from banked pieces onto the launched ship.
_STARSHIP_KEYWORD_TAGS = (
    GameTag.TAUNT,
    GameTag.WINDFURY,
    GameTag.LIFESTEAL,
    GameTag.RUSH,
    GameTag.CHARGE,
    GameTag.STEALTH,
    GameTag.POISONOUS,
    GameTag.REBORN,
    GameTag.CANT_BE_TARGETED_BY_SPELLS,
    GameTag.CANT_BE_TARGETED_BY_HERO_POWERS,
)


def _starship_token_id(player):
    cls = getattr(player.hero, "card_class", None)
    return _STARSHIP_TOKENS.get(cls, "GDB_100t2")


def _capture_starship_piece(piece):
    """Snapshot a dying Starship Piece's death-time stats, keywords and id so
    they can be combined into the ship later (the live entity is gone by
    launch time)."""
    keywords = [tag for tag in _STARSHIP_KEYWORD_TAGS if piece.tags.get(tag, 0)]
    return {
        "id": piece.id,
        "atk": max(0, piece.atk),
        "health": max(1, piece.max_health),
        "keywords": keywords,
        "divine_shield": bool(getattr(piece, "divine_shield", False)),
    }


def _bank_starship_piece(source, piece):
    """Bank a dead Starship Piece into its controller's Starship, summoning the
    Permanent ship on the first piece."""
    player = piece.controller
    if player is None:
        return
    ship = player.starship
    if ship is None or ship.zone != Zone.PLAY:
        if player.minion_slots <= 0:
            # No room for the Permanent — the piece is lost (matches the
            # full-board behaviour of other token summons).
            return
        ship = player.card(_starship_token_id(player), source)
        ship.controller = player
        ship._starship_pieces = []
        ship.dormant = True
        ship.dormant_turns = 0
        ship.cant_be_damaged = True
        player.starship = ship
        place = True
    else:
        place = False

    info = _capture_starship_piece(piece)
    ship._starship_pieces.append(info)
    total_atk = sum(p["atk"] for p in ship._starship_pieces)
    total_health = sum(p["health"] for p in ship._starship_pieces)

    if place:
        # Stamp the running stats BEFORE entering play so the 0/0 base never
        # reads as dead during death processing, then place it on the board
        # directly (a building ship is not a "real" summon — it must not
        # trigger summon synergies).
        ship.atk = total_atk
        ship.max_health = total_health
        ship.damage = 0
        ship._summon_index = None
        ship.zone = Zone.PLAY
    else:
        ship.atk = total_atk
        ship.max_health = total_health


def _eval_card(source, card):
    """
    Return a Card instance from \a card
    The card argument can be:
    - A Card instance (nothing is done)
    - The string ID of the card (the card is created)
    - A LazyValue (the card is dynamically created)
    - A Selector (take entity lists and returns a sub-list)
    """
    if isinstance(card, LazyValue):
        card = card.evaluate(source)

    if isinstance(card, Action):
        card = card.trigger(source)

    if isinstance(card, Selector):
        card = card.eval(source.game, source)

    if not isinstance(card, list):
        cards = [card]
    else:
        cards = card

    ret = []
    for card in cards:
        if isinstance(card, str):
            ret.append(source.controller.card(card, source))
        elif isinstance(card, list):
            ret += card
        else:
            ret.append(card)

    return ret


class EventListener:
    ON = 1
    AFTER = 2

    def __init__(self, trigger, actions, at):
        self.trigger = trigger
        self.actions = actions
        self.at = at
        self.once = False

    def __repr__(self):
        return "<EventListener %r>" % (self.trigger)


class ActionMeta(type):
    def __new__(metacls, name, bases, namespace):
        cls = type.__new__(metacls, name, bases, dict(namespace))
        argslist = []
        for k, v in namespace.items():
            if not isinstance(v, ActionArg):
                continue
            v._setup(len(argslist), k, cls)
            argslist.append(v)
        cls.ARGS = tuple(argslist)
        return cls

    @classmethod
    def __prepare__(metacls, name, bases):
        return OrderedDict()


class ActionArg(LazyValue):
    def _setup(self, index, name, owner):
        self.index = index
        self.name = name
        self.owner = owner

    def __repr__(self):
        return "<%s.%s>" % (self.owner.__name__, self.name)

    def evaluate(self, source):
        # This is used when an event listener triggers and the callback
        # Action has arguments of the type Action.FOO
        # XXX we rely on source.event_args to be set, but it's very racey.
        # If multiple events happen on an entity at once, stuff will go wrong.
        assert source.event_args
        # Defensive bounds check — concurrent event broadcasts (a
        # listener firing during another listener's resolution) can
        # leave source.event_args with fewer slots than this ActionArg
        # expects. Return None instead of crashing so downstream callers
        # (which mostly tolerate None via isinstance/list checks) can
        # skip the no-op rather than the soak collapsing.
        if self.index >= len(source.event_args):
            return None
        return source.event_args[self.index]


class CardArg(ActionArg):
    # Type hint
    pass


class IntArg(ActionArg, LazyNum):
    def evaluate(self, source):
        ret = super().evaluate(source)
        return self.num(ret)


class SourceArg(CardArg):
    def __init__(self):
        self.index = -1

    def __repr__(self):
        return "<SOURCE>"


SOURCE = SourceArg()


class Action(metaclass=ActionMeta):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self.callback = ()
        self.times = 1
        self.event_queue = []
        self.choice_callback = []

    def __repr__(self):
        args = ["%s=%r" % (k, v) for k, v in zip(self.ARGS, self._args)]
        return "<Action: %s(%s)>" % (self.__class__.__name__, ", ".join(args))

    def after(self, *actions):
        return EventListener(self, actions, EventListener.AFTER)

    def on(self, *actions):
        return EventListener(self, actions, EventListener.ON)

    def then(self, *args):
        """
        Create a callback containing an action queue, called upon the
        action's trigger with the action's arguments available.
        """
        ret = self.__class__(*self._args, **self._kwargs)
        ret.callback = args
        ret.times = self.times
        return ret

    def _broadcast(self, entity, source, at, *args):
        for event in entity.events:
            if event.at != at:
                continue
            if isinstance(event.trigger, self.__class__) and event.trigger.matches(
                entity, source, args
            ):
                log.info("%r triggers off %r from %r", entity, self, source)
                entity.trigger_event(source, event, args)
                if (
                    entity.type == CardType.SPELL
                    and entity.data.secret
                    and entity.controller.extra_trigger_secret
                ):
                    entity.trigger_event(source, event, args)

    def broadcast(self, source, at, *args):
        source.game.action_start(BlockType.TRIGGER, source, 0, None)

        for entity in source.game.entities:
            self._broadcast(entity, source, at, *args)
        for hand in source.game.hands:
            for entity in hand.entities:
                self._broadcast(entity, source, at, *args)
        for deck in source.game.decks:
            for entity in deck.entities:
                self._broadcast(entity, source, at, *args)

        source.game.action_end(BlockType.TRIGGER, source)

    def queue_broadcast(self, obj, args):
        self.event_queue.append((obj, args))

    def resolve_broadcasts(self):
        for obj, args in self.event_queue:
            obj.broadcast(*args)
        self.event_queue = []

    def get_args(self, source):
        ret = []
        for k, v in zip(self.ARGS, self._args):
            v = _eval_card(source, v)
            if isinstance(k, IntArg) or isinstance(k, CardArg):
                while hasattr(v, "__iter__"):
                    if len(v) == 0:
                        v = None
                    else:
                        v = v[0]
            ret.append(v)
        return ret

    def matches(self, entity, source, args):
        for arg, match in zip(args, self._args):
            if match is None:
                # Allow matching Action(None, None, z) to Action(x, y, z)
                continue
            if arg is None:
                # We got an arg of None and a match not None. Bad.
                return False
            if callable(match):
                res = match(arg)
                if not res:
                    return False
            else:
                # this stuff is stupidslow
                res = match.eval([arg], entity)
                if not res or res[0] is not arg:
                    return False
        if hasattr(self, "source") and self.source:
            res = self.source.eval([source], entity)
            if not res or res[0] is not source:
                return False
        return True

    def trigger_choice_callback(self):
        callbacks = self.choice_callback
        self.choice_callback = []
        for callback in callbacks:
            callback()


class GameAction(Action):
    def trigger(self, source):
        args = self.get_args(source)
        self.do(source, *args)


class Attack(GameAction):
    """
    Make \a ATTACKER attack \a DEFENDER
    """

    ATTACKER = CardArg()
    DEFENDER = CardArg()

    def do(self, source, attacker, defender):
        log.info("%r attacks %r", attacker, defender)
        if not attacker or not defender:
            return
        attacker.attack_target = defender
        defender.defending = True
        source.game.proposed_attacker = attacker
        source.game.proposed_defender = defender
        source.game.manager.step(Step.MAIN_COMBAT, Step.MAIN_ACTION)
        source.game.refresh_auras()  # XXX Needed for Gorehowl
        source.game.manager.game_action(self, source, attacker, defender)
        self.broadcast(source, EventListener.ON, attacker, defender)

        defender = source.game.proposed_defender
        source.game.proposed_attacker = None
        source.game.proposed_defender = None
        if attacker.should_exit_combat:
            log.info("Attack has been interrupted.")
            attacker.attack_target = None
            if defender is not None:
                defender.defending = False
            return
        if defender is None:
            # An on-attack trigger nullified the defender (e.g. a
            # redirect that didn't propagate a replacement). Treat as
            # interrupted — clean up and bail rather than crashing on
            # defender.atk below.
            log.info("Attack defender was nullified mid-resolution; bailing.")
            attacker.attack_target = None
            return

        assert attacker is not defender, "Why are you hitting yourself %r?" % (attacker)

        # Save the attacker/defender atk values in case they change during the attack
        # (eg. in case of Enrage)
        def_atk = defender.atk
        source.game.queue_actions(attacker, [Hit(defender, attacker.atk)])
        if def_atk:
            source.game.queue_actions(defender, [Hit(attacker, def_atk)])

        self.broadcast(source, EventListener.AFTER, attacker, defender)

        attacker.attack_target = None
        defender.defending = False
        if source == attacker:
            attacker.num_attacks += 1
        if attacker.type == CardType.HERO:
            attacker.controller.num_hero_attacks_this_game += 1


class BeginTurn(GameAction):
    """
    Make \a player begin the turn
    """

    PLAYER = CardArg()

    def do(self, source, player):
        source.manager.step(source.next_step, Step.MAIN_READY)
        source.turn += 1
        source.log("%s begins turn %i", player, source.turn)
        source.current_player = player
        source.manager.step(source.next_step, Step.MAIN_START_TRIGGERS)
        source.manager.step(source.next_step, source.next_step)
        source.game.manager.game_action(self, source, player)
        # The Great Dark Beyond — clear Sha'tari Cloakfield's first-spell
        # discount BEFORE OWN_TURN_BEGIN so in-play sources re-arm it cleanly
        # (resetting it in _begin_turn, which runs after this broadcast, would
        # wipe the freshly armed discount).
        player.first_spell_discount = 0
        self.broadcast(source, EventListener.ON, player)
        if player.choice:
            player.choice.choice_callback.append(lambda: source._begin_turn(player))
        else:
            source._begin_turn(player)


class Concede(GameAction):
    """
    Make \a player concede
    """

    PLAYER = CardArg()

    def do(self, source, player):
        player.playstate = PlayState.CONCEDED
        source.game.manager.game_action(self, source, player)
        source.game.check_for_end_game()


class Disconnect(GameAction):
    """
    Make \a player disconnect
    """

    PLAYER = ActionArg()

    def do(self, source, player):
        player.playstate = PlayState.DISCONNECTED
        source.game.manager.game_action(self, source, player)


class Deaths(GameAction):
    """
    Process all deaths in the PLAY Zone.
    """

    def do(self, source, *args):
        source.game.process_deaths()


class Death(GameAction):
    """
    Move target to the GRAVEYARD Zone.
    """

    ENTITY = ActionArg()

    def _broadcast(self, entity, source, at, *args):
        # https://github.com/jleclanche/fireplace/issues/126
        target = args[0]
        if (not self._trigger) and entity.play_counter > target.play_counter:
            self._trigger = True
            if at == EventListener.ON and target.has_deathrattle:
                source.game.queue_actions(target, [Deathrattle(target)])
            if (
                at == EventListener.AFTER
                and target.type == CardType.MINION
                and target.reborn
            ):
                source.game.queue_actions(
                    target,
                    [Summon(target.controller, RebornCopy(SELF)), Reborn(target)],
                )
        return super()._broadcast(entity, source, at, *args)

    def do(self, source, cards):
        for card in cards:
            if not card.dead:
                continue
            if card.zone == Zone.PLAY:
                card._dead_position = card.zone_position - 1
            card.zone = Zone.GRAVEYARD
            # The Great Dark Beyond — The Ceaseless Expanse cost ledger.
            source.game.cards_dpd_this_game = (
                getattr(source.game, "cards_dpd_this_game", 0) + 1
            )
            source.game.check_for_end_game()
            source.game.refresh_auras()
            log.info("Processing Deathrattle for %r", card)
            # Castle Nathria — Infuse: every friendly minion death bumps
            # `infuse_progress` on Infuse cards in the dying minion's
            # controller's hand. When the threshold is reached, the card
            # morphs into its infused twin. Also bump the per-game
            # friendly-minion-deaths counter (Sire Denathrius reads it).
            if card.type == CardType.MINION and card.controller:
                # The Great Dark Beyond — a dying Starship Piece banks its
                # stats and effects into its controller's Starship.
                if card.data.tags.get(GameTag.STARSHIP_PIECE, 0):
                    _bank_starship_piece(source, card)
                card.controller.friendly_minions_died_this_game += 1
                # March of the Lich King — every friendly minion death
                # gives the controller a Corpse, even non-DK players
                # (Corpses just sit unused for non-DK). Falric doubles the gain.
                _corpse_gain = 2 if card.controller.corpses_doubled else 1
                card.controller.corpses += _corpse_gain
                card.controller.corpses_gained_this_game += _corpse_gain
                # MotLK — precise "died after your last turn" window for
                # Undead-synergy cards. Reset at OWN_TURN_END (see
                # game.py:end_turn_cleanup).
                if Race.UNDEAD in getattr(card, "races", []):
                    card.controller._undead_deaths_in_window.append(card)
                # Maw and Disorder — Afterlife Attendant (MAW_031): while
                # any friendly Afterlife Attendant is on the board, the
                # controller's deck cards also infuse alongside the hand.
                infuse_zones = list(card.controller.hand)
                if any(m.id == "MAW_031" for m in card.controller.field):
                    infuse_zones += list(card.controller.deck)
                # snapshot the iter — morph() mutates the hand mid-loop
                for hand_card in infuse_zones:
                    threshold = hand_card.infuse_threshold
                    if threshold <= 0:
                        continue
                    hand_card.infuse_progress += 1
                    # Castle Nathria — Sinfueled Golem reads this to gain
                    # stats equal to the sum of Attacks of the minions
                    # that Infused it. Bump in the same pass.
                    hand_card.infused_by_atk_total += getattr(card, "atk", 0)
                    if (
                        hand_card.infuse_progress >= threshold
                        and hand_card.infused_card_id
                    ):
                        # Stash the atk-total before morph; the new
                        # card needs to read it (Sinfueled Golem).
                        atk_total = hand_card.infused_by_atk_total
                        infused_id = hand_card.infused_card_id
                        hand_card.morph(infused_id)
                        new_card = hand_card.morphed
                        if new_card is not None:
                            new_card.infused_by_atk_total = atk_total
                            # Sinfueled Golem twin — apply the stats
                            # buff so the gained atk/health are
                            # visible while sitting in hand.
                            if infused_id == "REV_843t":
                                source.game.cheat_action(
                                    new_card.controller,
                                    [Buff(new_card, "REV_843e")],
                                )
            self._trigger = False
            source.game.manager.game_action(self, source, card)
            self.broadcast(source, EventListener.ON, card)

        for card in cards:
            if not card.dead:
                continue
            self._trigger = False
            self.broadcast(source, EventListener.AFTER, card)


class EndTurn(GameAction):
    """
    End the current turn
    """

    PLAYER = CardArg()

    def do(self, source, player):
        if player.choice:
            raise InvalidAction(
                "%r cannot end turn with the open choice %r." % (player, player.choice)
            )
        source.game.manager.game_action(self, source, player)
        self.broadcast(source, EventListener.ON, player)
        # Snapshot the hand: card.discard() mutates player.hand, so iterating
        # the live list skips the neighbour of each discarded card. (Surfaced
        # by Sweetened Snowflurry, the first card to grant two temporary cards
        # at once — without the copy one of the two survived end of turn.)
        for card in list(player.hand):
            if card.temporary:
                card.discard()
        if player.extra_end_turn_effect:
            self.broadcast(source, EventListener.ON, player)
        source.game._end_turn()


class Joust(GameAction):
    """
    Perform a joust between \a challenger and \a defender.
    Note that this does not evaluate the results of the joust. For that,
    see dsl.evaluators.JoustEvaluator.
    """

    CHALLENGER = CardArg()
    DEFENDER = CardArg()

    def do(self, source, challenger, defender):
        log.info("Jousting %r vs %r", challenger, defender)
        source.game.manager.game_action(self, source, challenger, defender)
        source.game.joust(source, challenger, defender, self.callback)


class MulliganChoice(GameAction):
    PLAYER = CardArg()

    def __init__(self, *args, callback):
        super().__init__(*args)
        self.callback = callback

    def do(self, source, player):
        player.mulligan_state = Mulligan.INPUT
        player.choice = self
        # NOTE: Ideally, we give The Coin when the Mulligan is over.
        # Unfortunately, that's not compatible with Blizzard's way.
        self.cards = player.hand.exclude(id="GAME_005")
        self.source = source
        self.player = player
        self.min_count = 0
        # but weirdly, the game server includes the coin in the mulligan count
        self.max_count = len(player.hand)
        source.game.manager.game_action(self, source, player)

    def choose(self, *cards):
        for card in cards:
            assert card in self.cards
        self.player.choice = None
        for card in cards:
            card._summon_index = 0
            new_card = self.player.deck[-1]
            new_card._summon_index = card.zone_position
            card.zone = Zone.DECK
            new_card.zone = Zone.HAND
        self.player.shuffle_deck()
        self.player.mulligan_state = Mulligan.DONE

        if self.player.opponent.mulligan_state == Mulligan.DONE:
            self.callback()


class Play(GameAction):
    """
    Make the source player play \a card, on \a target or None.
    Choose play action from \a choose or None.
    """

    PLAYER = CardArg()
    CARD = CardArg()
    TARGET = CardArg()
    INDEX = IntArg()
    CHOOSE = CardArg()

    def _broadcast(self, entity, source, at, *args):
        # Prevent cards from triggering off their own play
        if entity is args[1]:
            return
        return super()._broadcast(entity, source, at, *args)

    def do(self, source, card, target, index, choose):
        player = source
        log.info("%s plays %r (target=%r, index=%r)", player, card, target, index)

        # The Great Dark Beyond — adjacency ("Orbital" cards / Red Giant): the
        # cards immediately left and right of this one in hand remember that an
        # adjacent card was played, both this turn and cumulatively while they
        # sit in hand. Captured before the card leaves the hand zone.
        if card in player.hand:
            _idx = player.hand.index(card)
            for _nb in (_idx - 1, _idx + 1):
                if 0 <= _nb < len(player.hand):
                    neighbor = player.hand[_nb]
                    neighbor.adjacent_plays_this_turn += 1
                    neighbor.adjacent_plays_while_in_hand += 1

        # Snapshot the effective cost at play time (still in hand, all discounts
        # applied) so battlecries can gate on "if this costs (0)" — the raw COST
        # tag misses player-level discounts like Libram cost reduction.
        card._played_cost = card.cost
        player.pay_cost(card, card.cost)

        # Festival of Legends — Finale flag captured at the post-pay-cost
        # moment. If pay_cost left the controller with 0 mana, the card
        # was played as a Finale (spent all remaining mana). Read by
        # FINALE-gated card scripts.
        card.play_finale = (player.mana == 0)

        # Showdown in the Badlands — Quickdraw snapshot. Capture whether the
        # card is being played the same turn it entered hand BEFORE its zone
        # changes to PLAY (quickdraw_active reads HAND zone). Read by
        # QUICKDRAW-gated `play`/battlecry actions.
        card.quickdraw_played = card.quickdraw_active

        card.target = target
        card._summon_index = index

        battlecry_card = choose or card
        # We check whether the battlecry will trigger, before the card.zone changes
        if battlecry_card.battlecry_requires_target() and not target:
            log.info("%r requires a target for its battlecry. Will not trigger.")
            trigger_battlecry = False
        else:
            trigger_battlecry = True

        card.play_left_most = card is card.controller.hand[0]
        card.play_right_most = card is card.controller.hand[-1]

        card.zone = Zone.PLAY

        # Remember cast on friendly characters
        if card.type == CardType.SPELL and target and target.controller == source:
            card.cast_on_friendly_characters = True
            if target.type == CardType.MINION:
                card.cast_on_friendly_minions = True

        # Perils — Sea Shanty: count spells cast on a character (any side).
        if card.type == CardType.SPELL and target and target.type in (
            CardType.MINION, CardType.HERO
        ):
            source.spells_cast_on_characters_this_game += 1

        source.game.manager.game_action(self, source, card, target, index, choose)
        # NOTE: A Play is not a summon! But it sure looks like one.
        # We need to fake a Summon broadcast.
        summon_action = Summon(player, card)

        if card.echo:
            source.game.queue_actions(card, [Give(player, Buff(Copy(SELF), "GIL_000"))])

        if card.type == CardType.SPELL and card.twinspell:
            source.game.queue_actions(card, [Give(player, card.twinspell_copy)])

        actions = card.get_actions("magnetic")
        if actions:
            # TITANS — Invent-o-matic: notify on-board listeners BEFORE the
            # magnetic action fires so the magnetizer's stats (which merge
            # into the host) include any buffs the listeners apply.
            for listener in list(player.field):
                if listener is card:
                    continue
                handler = getattr(getattr(listener.data, "scripts", None),
                                  "on_friendly_magnetize", None)
                if handler:
                    source.game.cheat_action(listener, handler(listener, card))
            source.game.trigger(card, actions, event_args=None)

        for hand in player.hand[:]:
            if hand.corrupt and hand.cost < card.cost:
                source.game.queue_actions(player, [Corrupt(hand)])

        # Sunken City: bump spell/Naga "while holding" trackers and the
        # per-minion spell-mana counter BEFORE event broadcasts so that
        # OWN_SPELL_PLAY listeners (Dozing Kelpkeeper, etc.) read the
        # post-cast values.
        if card.type == CardType.SPELL:
            paid_cost = max(0, card.cost)
            player.mana_spent_on_spells_this_game += paid_cost
            player.spell_mana_spent_this_turn += paid_cost
            school = card.spell_school
            if school and int(school) == int(SpellSchool.HOLY):
                player.mana_spent_on_holy_spells_this_game += paid_cost
            for minion in player.field:
                minion.spell_mana_spent_in_play += paid_cost
        for hand_card in player.hand:
            if hand_card is card:
                continue
            if card.type == CardType.SPELL:
                hand_card.spells_cast_while_holding += 1
                hand_card.spells_history_while_holding.append(
                    (card.id, max(0, card.cost))
                )
                school = getattr(card, "spell_school", None)
                if school and int(school) != int(SpellSchool.NONE):
                    hand_card.spell_schools_cast_while_holding.add(int(school))
            if card.type == CardType.MINION and Race.NAGA in card.races:
                hand_card.nagas_played_while_holding += 1

        if card.type in (CardType.MINION, CardType.WEAPON):
            self.queue_broadcast(
                summon_action, (player, EventListener.ON, player, card)
            )
        self.broadcast(player, EventListener.ON, player, card, target)
        self.resolve_broadcasts()

        # Colossal: when a Colossal minion is *played* (rather than summoned
        # via a Summon action), the Summon.do hook never fires — Play moves
        # the card straight into PLAY. We mirror the hook here so the limb
        # tokens get summoned alongside the parent.
        if (
            card.type == CardType.MINION
            and card.data.tags.get(GameTag.COLOSSAL, 0)
            and not card.data.tags.get(GameTag.COLOSSAL_LIMB, 0)
        ):
            _summon_colossal_limbs(card, player, card)

        # TITANS — Aqua Archivist / Tram Operator: apply one-shot cost discounts
        # BEFORE the battlecry fires so the card cannot consume its own discount.
        # Clamp the refund to the cost actually paid for this card so a card
        # already reduced below the discount can't yield free mana.
        if card.type == CardType.MINION:
            paid = max(0, card.cost)
            if Race.ELEMENTAL in card.races and player._next_elemental_discount > 0:
                refund = min(paid, player._next_elemental_discount)
                player.used_mana = max(0, player.used_mana - refund)
                player._next_elemental_discount = 0
            if Race.MECHANICAL in card.races and player._next_mech_cost_reduction > 0:
                refund = min(paid, player._next_mech_cost_reduction)
                player.used_mana = max(0, player.used_mana - refund)
                player._next_mech_cost_reduction = 0

        # Whizbang's Workshop — Miniaturize: when a minion with the
        # MINIATURIZE keyword is played, add its paired 1-Cost 1/1 "Mini"
        # token to hand. Fires on play BEFORE the battlecry (matches the
        # printed timing), and only for the real play (not summons).
        if card.type == CardType.MINION and card.data.tags.get(
            GameTag.MINIATURIZE, 0
        ):
            mini_id = _resolve_mini_id(card)
            if mini_id:
                source.game.queue_actions(player, [Give(player, mini_id)])

        # Whizbang's Workshop mini-set — Gigantify: like Miniaturize but
        # bigger. Playing a GIGANTIFY minion adds its 8-Cost 8/8 "Gigantic"
        # copy (same text, fixed 8/8 stats) to hand. Same timing as
        # Miniaturize — on the real play, before the battlecry.
        if card.type == CardType.MINION and card.data.tags.get(
            GameTag.GIGANTIFY, 0
        ):
            giant_id = _resolve_giant_id(card)
            if giant_id:
                source.game.queue_actions(player, [Give(player, giant_id)])

        # The Great Dark Beyond — "the next Draenei you play …" effects. Fire
        # and clear any pending hooks on this freshly-played Draenei BEFORE its
        # battlecry, so the minion benefits from prior registrations but does
        # not consume the hook its own battlecry is about to register.
        if card.type == CardType.MINION and Race.DRAENEI in card.races:
            if getattr(card, "received_draenei_discount", False):
                player.next_draenei_discount = 0
                card.received_draenei_discount = False
            hooks = player.next_draenei_hooks
            player.next_draenei_hooks = []
            for hook in hooks:
                hook(card)
            player.last_draenei_played = card.id

        # Heroes of StarCraft — consume one-shot Protoss cost reductions on the
        # card that actually took them (stamped in card.cost), and count Protoss
        # spells cast this game (Colossus scales off this). Done before the
        # battlecry so a Protoss card's own battlecry can't re-consume the hook.
        if card.data.tags.get(GameTag.PROTOSS, 0):
            if getattr(card, "received_protoss_minion_discount", False):
                player.next_protoss_minion_discount = 0
                card.received_protoss_minion_discount = False
            if getattr(card, "received_protoss_spell_discount", False):
                player.next_protoss_spell_discount = 0
                card.received_protoss_spell_discount = False
            if getattr(card, "received_protoss_card_discount", False):
                player.next_protoss_card_discount = 0
                card.received_protoss_card_discount = False
            if card.type == CardType.SPELL:
                player.protoss_spells_cast_this_game += 1
        # Heroes of StarCraft — the Launch Starship button consumes the pending
        # "next Starship launch costs (2) less" reduction.
        if card.id == "GDB_905" and player.starship_launch_discount:
            player.starship_launch_discount = 0

        # "Can't Play" (aka Counter) means triggers don't happen either
        if not card.cant_play:
            if trigger_battlecry:
                source.game.queue_actions(
                    card, [Battlecry(battlecry_card, card.target)]
                )

            # If the play action transforms the card (eg. Druid of the Claw), we
            # have to broadcast the morph result as minion instead.
            played_card = card.morphed or card
            played_card.play_right_most = card.play_right_most
            if played_card.type in (CardType.MINION, CardType.WEAPON):
                summon_action.broadcast(
                    player, EventListener.AFTER, player, played_card
                )
            self.broadcast(player, EventListener.AFTER, player, played_card, target)

            # Across the Timeways — Rewind: once the play effect has fired (and
            # its AFTER triggers resolved), offer Keep Timeline vs Rewind
            # Timeline. Only when the effect actually triggered (trigger_battlecry
            # gates this whole block), so a Rewind battlecry that fizzled for
            # lack of a target never offers a pointless rewind.
            if trigger_battlecry and card.data.tags.get(GameTag.REWIND, 0):
                # Across the Timeways mini-set — Morchie (END_036): "Your Rewinds
                # keep BOTH potential outcomes." While a Morchie is in play the
                # player skips the Keep/Rewind choice and gets both: the effect
                # already resolved (Keep), and it re-runs once more (Rewind).
                if any(m.id == "END_036" for m in player.field):
                    source.game.queue_actions(card, [Battlecry(card, card.target)])
                else:
                    keep = player.card("TIME_000ta", source=card)
                    rewind = player.card("TIME_000tb", source=card)
                    source.game.queue_actions(
                        card, [_RewindChoice(player, [keep, rewind])]
                    )

        player.combo = True
        player.last_card_played = card
        if card.type == CardType.MINION:
            player.minions_played_this_turn += 1
            if Race.TOTEM in card.races:
                card.controller.times_totem_summoned_this_game += 1
            if Race.ELEMENTAL in card.races:
                player.elemental_played_this_turn += 1
        elif card.type == CardType.SPELL:
            player.spells_played_this_game += 1
            player.spells_played_this_turn += 1
            # Ledger of every spell cast this game (hand-plays here, effect
            # casts in CastSpell.do). Appended here — AFTER the battlecry was
            # queued above — so a spell whose own effect reads this ledger
            # (e.g. The Galactic Projection Orb) does not see itself.
            player.spells_cast_this_game.append(card)
            # TITANS — Primus Runes of Frost: consume one-shot Spell Damage
            # boost. The spell already saw it via get_spell_damage; reset now.
            player.next_spell_spellpower = 0
            # Per-school history (NONE bucket excluded — not a real school).
            school = card.spell_school
            if school and int(school) != 0:
                player.spells_cast_by_school.setdefault(int(school), []).append(
                    card.id
                )
            # Whizbang mini-set — Holy spell counters (Flickering Lightbot
            # MIS_918 per-game cost_mod; Holy Glowsticks MIS_709 per-turn cost).
            if school and int(school) == int(SpellSchool.HOLY):
                player.holy_spells_cast_this_game += 1
                player.holy_spells_cast_this_turn += 1
            # Castle Nathria — Relic counter. Hardcoded id list since
            # the data has no GameTag.RELIC; bump on each Relic cast so
            # "Improve your future Relics" scales subsequent casts.
            if card.id in RELIC_IDS:
                player.relics_played_this_game += 1
                # Relic Vault: re-cast this Relic once if a charge is
                # waiting. Bump the counter again for the re-cast (it
                # bypasses Play.do via CastSpell so the normal bump
                # wouldn't fire), and decrement the Vault charge BEFORE
                # the re-cast so the second cast can't recursively
                # double-fire.
                if player.next_relic_casts_twice > 0:
                    player.next_relic_casts_twice -= 1
                    player.relics_played_this_game += 1
                    source.game.queue_actions(player, [CastSpell(card.id)])
            # Minions AND the weapon can carry Spellburst (e.g. Parallax
            # Cannon), so scan the weapon too — it never sits in player.field.
            # The Galaxy's Lens (GDB_136t) is a Location with Spellburst, so
            # include the location as well.
            spellburst_sources = player.field[:]
            if player.weapon is not None:
                spellburst_sources.append(player.weapon)
            if player.location is not None:
                spellburst_sources.append(player.location)
            for entity in spellburst_sources:
                if getattr(entity, "has_spellburst", False):
                    source.game.queue_actions(card, [Spellburst(entity, card)])
        # MotLK Outcast counter: bump if this card has the OUTCAST tag
        # and was played from the leftmost or rightmost slot. Single
        # engine bump replaces per-card listeners (Wretched Exile used
        # to be the only thing keeping the counter alive).
        if card.has_outcast and card.play_outcast:
            player.outcasts_played_this_game += 1
        player.cards_played_this_turn += 1
        player.cards_played_this_game.append(card)
        # The Lost City of Un'Goro — Kindred: record this card's minion type(s)
        # and spell school so a Kindred card of a matching type, played on your
        # next turn, activates its bonus.
        for race in getattr(card, "races", []):
            player.races_played_this_turn.add(race)
        school = getattr(card, "spell_school", SpellSchool.NONE)
        if school and school != SpellSchool.NONE:
            player.schools_played_this_turn.add(school)
        card.turn_played = source.game.turn
        card.choose = None

        # Throne of the Tides post-play one-shots.
        # Shattershambler: next deathrattle minion costs (1) less and
        # immediately dies when played.
        if card.type == CardType.MINION and card.has_deathrattle:
            if player.next_deathrattle_discount > 0:
                player.next_deathrattle_discount -= 1
            if player.next_deathrattle_dies_on_play > 0:
                player.next_deathrattle_dies_on_play -= 1
                if card.zone == Zone.PLAY:
                    source.game.queue_actions(card, [Destroy(card), Deaths()])
        # Clownfish: consume one Murloc discount charge per Murloc that
        # actually received the discount (flagged in card.cost). Skipping
        # this for Clownfish itself, whose battlecry sets the counter
        # *after* its own cost is paid.
        if (
            card.type == CardType.MINION
            and Race.MURLOC in card.races
            and player.next_n_murlocs_discount > 0
            and getattr(card, "received_murloc_discount", False)
        ):
            player.next_n_murlocs_discount -= 1
            card.received_murloc_discount = False
        # The Great Dark Beyond — Spacerock Collector: consume the one-shot
        # Combo discount for a Combo card that actually took it.
        if (
            getattr(card, "has_combo", False)
            and player.next_combo_discount > 0
            and getattr(card, "received_combo_discount", False)
        ):
            player.next_combo_discount -= 1
            card.received_combo_discount = False
        # The Great Dark Beyond — Infernal Stratagem: consume the one-shot Demon
        # discount for a Demon that took it.
        if (
            card.type == CardType.MINION
            and Race.DEMON in getattr(card, "races", [])
            and player.next_demon_discount > 0
            and getattr(card, "received_demon_discount", False)
        ):
            player.next_demon_discount -= 1
            card.received_demon_discount = False
        # Cataclysm — Tichondrius: consume the one-shot "next Demon costs (0)"
        # when a Demon that took it is played.
        if (
            card.type == CardType.MINION
            and Race.DEMON in getattr(card, "races", [])
            and getattr(player, "next_demon_free_this_turn", False)
            and getattr(card, "received_demon_free", False)
        ):
            player.next_demon_free_this_turn = False
            card.received_demon_free = False
        # The Great Dark Beyond — Space Pirate: consume the next-weapon discount
        # when a weapon is played.
        if card.type == CardType.WEAPON and player.next_weapon_discount > 0:
            player.next_weapon_discount -= 1
        # The Great Dark Beyond — The Ceaseless Expanse cost ledger (a card was
        # played).
        source.game.cards_dpd_this_game = (
            getattr(source.game, "cards_dpd_this_game", 0) + 1
        )
        # The Great Dark Beyond — Exarch Hataaru: playing a marked discovered
        # spell the same turn repeats Hataaru's effect (re-run the source's
        # play script, generically — no card import needed here).
        hat = getattr(card, "_hataaru_source", None)
        if hat is not None and getattr(card, "_hataaru_turn", -1) == source.turn:
            card._hataaru_source = None
            play_script = getattr(hat.data.scripts, "play", None)
            if play_script:
                actions = (
                    list(play_script)
                    if isinstance(play_script, (list, tuple))
                    else [play_script]
                )
                source.game.queue_actions(hat, actions)


class Activate(GameAction):
    CARD = CardArg()
    TARGET = CardArg()
    CHOOSE = CardArg()

    def do(self, source, heropower, target, choose):
        player = heropower.controller
        cost = heropower.cost
        if player.next_hero_power_costs_zero > 0:
            cost = 0
            player.next_hero_power_costs_zero -= 1
        player.pay_cost(heropower, cost)
        source.game.manager.game_action(self, source, heropower, target, choose)
        self.broadcast(source, EventListener.ON, heropower, target, choose)

        card = choose or heropower
        source.game.action_start(BlockType.PLAY, heropower, 0, target)
        source.game.queue_actions(source, [PlayHeroPower(card, target)])
        source.game.action_end(BlockType.PLAY, heropower)

        # One-shot freeze-the-target modifier (e.g. Amplified Snowflurry).
        if player.next_hero_power_freezes_target > 0:
            if target is not None and hasattr(target, "frozen"):
                target.frozen = True
            player.next_hero_power_freezes_target -= 1

        for entity in player.live_entities:
            if not entity.ignore_scripts:
                actions = entity.get_actions("inspire")
                if actions:
                    source.game.trigger(entity, actions, event_args=None)

        self.broadcast(source, EventListener.AFTER, heropower, target, choose)
        heropower.activations_this_turn += 1
        heropower.activations_this_game += 1


class UseLocation(GameAction):
    """
    Murder at Castle Nathria — fire a Location's activate script, then
    decrement its durability, set a 2-turn cooldown, and destroy it if
    it ran out of charges.
    """

    LOCATION = CardArg()
    TARGET = CardArg()

    def do(self, source, location, target):
        player = location.controller
        source.game.manager.game_action(self, source, location, target)
        self.broadcast(source, EventListener.ON, location, target)

        source.game.action_start(BlockType.PLAY, location, 0, target)
        actions_to_run = location.get_actions("activate") or location.get_actions(
            "play"
        )
        if actions_to_run:
            source.game.main_power(location, actions_to_run, target)
        source.game.action_end(BlockType.PLAY, location)

        # Consume one durability and lock for two turns.
        location.damage += 1
        location.cooldown = 2

        self.broadcast(source, EventListener.AFTER, location, target)

        if location.durability <= 0:
            source.game.queue_actions(location, [Destroy(location)])
            source.game.process_deaths()


class UseTitanAbility(GameAction):
    """TITANS — use the next sequential ability of a Titan minion.

    Fires the `play` actions from the ability sub-card (e.g. TTN_075t),
    increments _titan_ability_index, then broadcasts events.  After all
    three abilities are used the Titan may finally attack.
    """

    TITAN = CardArg()
    TARGET = CardArg()

    def do(self, source, titan, target):
        from fireplace.cards import db as _db, get_script_definition
        ability_order = getattr(getattr(titan.data, "scripts", None), "titan_ability_order", None)
        if not ability_order:
            return
        idx = titan._titan_ability_index
        if idx >= len(ability_order):
            return

        sub_id = ability_order[idx]
        sub_script = get_script_definition(sub_id, _db.get(sub_id))

        source.game.manager.game_action(self, source, titan, target)
        self.broadcast(source, EventListener.ON, titan, target)

        # Set titan.target so TARGET selectors in sub-card actions resolve
        # correctly when the ability requires a target (e.g. Hit(TARGET, 20)).
        old_target = getattr(titan, "target", None)
        titan.target = target
        source.game.action_start(BlockType.PLAY, titan, 0, target)
        if sub_script:
            # Prefer the merged card's scripts.play (already normalised to a
            # tuple by the card-DB merge) so that single-action sub-cards
            # (e.g. `play = Hit(...)`) don't trigger a TypeError when
            # trigger_actions tries to iterate over a bare Action object.
            merged = _db.get(sub_id)
            if merged is not None and hasattr(merged, "scripts"):
                actions_to_run = getattr(merged.scripts, "play", None)
            else:
                actions_to_run = getattr(sub_script, "play", None)
            if actions_to_run:
                source.game.main_power(titan, actions_to_run, target)
        source.game.action_end(BlockType.PLAY, titan)
        titan.target = old_target

        titan._titan_ability_index += 1

        self.broadcast(source, EventListener.AFTER, titan, target)


class Overload(GameAction):
    PLAYER = CardArg()
    AMOUNT = IntArg()

    def do(self, source, player, amount):
        if player.cant_overload:
            log.info("%r cannot overload %s", source, player)
            return
        log.info("%r overloads %s for %i", source, player, amount)
        source.game.manager.game_action(self, source, player, amount)
        self.broadcast(source, EventListener.ON, player, amount)
        player.overloaded += amount
        player.overloaded_this_game += amount


class TargetedAction(Action):
    TARGET = ActionArg()

    def __init__(self, *args, **kwargs):
        self.source = kwargs.pop("source", None)
        super().__init__(*args, **kwargs)
        self.trigger_index = 0

    def __repr__(self):
        args = ["%s=%r" % (k, v) for k, v in zip(self.ARGS[1:], self._args[1:])]
        return "<TargetedAction: %s(%s)>" % (self.__class__.__name__, ", ".join(args))

    def __mul__(self, value):
        self.times = value
        return self

    def eval(self, selector, source):
        if isinstance(selector, Entity):
            return [selector]
        else:
            return selector.eval(source.game, source)

    def get_target_args(self, source, target):
        ret = []
        for k, v in zip(self.ARGS[1:], self._args[1:]):
            v = _eval_card(source, v)
            if isinstance(k, IntArg) or isinstance(k, CardArg):
                while hasattr(v, "__iter__"):
                    if len(v) == 0:
                        v = None
                    else:
                        v = v[0]
            ret.append(v)
        return ret

    def get_targets(self, source):
        ret = _eval_card(source, self._args[0])
        if not ret:
            return []
        if not hasattr(ret, "__iter__"):
            # Bit of a hack to ensure we always get a list back
            ret = [ret]
        return ret

    def trigger(self, source):
        ret = []

        if self.source is not None and isinstance(self.source, Selector):
            source = self.source.eval(source.game, source)
            assert len(source) == 1
            source = source[0]

        times = self.times
        if isinstance(times, LazyValue):
            times = times.evaluate(source)
        elif isinstance(times, Action):
            times = times.trigger(source)[0]
        elif isinstance(times, Selector):
            times = times.eval(source.game, source)

        for i in range(times):
            ret += self._trigger(i, source)

        self.resolve_broadcasts()

        return ret

    def _trigger(self, i, source):
        if source.controller.choice:
            self.choice_callback.append(lambda: self._trigger(i, source))
            return []
        ret = []
        self.trigger_index = i
        targets = self.get_targets(source)
        log.info("%r triggering %r targeting %r", source, self, targets)
        for target in targets:
            if target is None:
                continue
            target_args = self.get_target_args(source, target)
            ret.append(self.do(source, target, *target_args))

            for action in self.callback:
                log.info("%r queues up callback %r", self, action)
                ret += source.game.queue_actions(
                    source, [action], event_args=[target] + target_args
                )
        return ret


class Buff(TargetedAction):
    """
    Buff character targets with Enchantment \a id
    NOTE: Any Card can buff any other Card. The controller of the
    Card that buffs the target becomes the controller of the buff.
    """

    TARGET = ActionArg()
    BUFF = CardArg()

    def do(self, source, target, buff):
        kwargs = self._kwargs.copy()
        for k, v in kwargs.items():
            if isinstance(v, LazyValue):
                v = v.evaluate(source)
            setattr(buff, k, v)
        buff.source = source
        # Buff amplification — Saidan the Scarlet doubles positive stat buffs
        # landing on it.
        if getattr(target, "buffs_doubled", False):
            for attr in ("atk", "max_health", "health"):
                current = getattr(buff, attr, None)
                if isinstance(current, int) and current > 0:
                    setattr(buff, attr, current * 2)
        buff.apply(target)
        source.game.manager.targeted_action(self, source, target, buff)
        self.broadcast(source, EventListener.AFTER, target, buff)
        return target


class MultiBuff(TargetedAction):
    TARGET = ActionArg()
    BUFFS = ActionArg()

    def do(self, source, target, buffs):
        for buff in buffs:
            buff.source = source
            kwargs = self._kwargs.copy()
            for k, v in kwargs.items():
                if isinstance(v, LazyValue):
                    v = v.evaluate(source)
                setattr(buff, k, v)
            buff.apply(target)
            source.game.manager.targeted_action(self, source, target, buff)
        return target


class StoringBuff(TargetedAction):
    TARGET = ActionArg()
    BUFF = CardArg()
    CARD = ActionArg()

    def do(self, source, target, buff, cards):
        log.info("%r store card %r", buff, cards)
        buff.source = source
        buff.store_card = cards
        buff.apply(target)
        return target


class Bounce(TargetedAction):
    """
    Bounce minion targets on the field back into the hand.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        if len(target.controller.hand) >= target.controller.max_hand_size:
            log.info("%r is bounced to a full hand and gets destroyed", target)
            return source.game.queue_actions(source, [Destroy(target)])
        else:
            log.info("%r is bounced back to %s's hand", target, target.controller)
            target.zone = Zone.HAND
            source.game.manager.targeted_action(self, source, target)
            # Broadcast so cards can react to entering hand from the battlefield
            # (e.g. Harbinger of the Blighted EDR_781). The destroy-on-full-hand
            # path above does NOT broadcast — the minion never reaches the hand.
            self.broadcast(source, EventListener.AFTER, target)


class Choice(TargetedAction):
    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def get_target_args(self, source, target):
        cards = self._args[1]
        if isinstance(cards, Selector):
            cards = cards.eval(source.game, source)
        elif isinstance(cards, LazyValue):
            cards = cards.evaluate(source)
        elif isinstance(cards, list):
            eval_cards = []
            for card in cards:
                if isinstance(card, LazyValue):
                    eval_cards.append(card.evaluate(source)[0])
                elif isinstance(card, str):
                    eval_cards.append(source.controller.card(card, source))
                elif isinstance(card, Selector):
                    eval_cards += card.eval(source.game, source)
                else:
                    eval_cards.append(card)
            cards = eval_cards

        return [cards]

    def do(self, source, player, cards):
        self._callback = self.callback
        self.callback = []
        if len(cards) == 0:
            return
        log.info("%r choice from %r", player, cards)
        player.choice = self
        self.source = source
        self.game = source.game
        self.player = player
        self.cards = cards
        self.min_count = 1
        self.max_count = 1
        source.game.manager.targeted_action(self, source, player, cards)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        for action in self._callback:
            self.source.game.trigger(
                self.source, [action], [self.player, self.cards, card]
            )
        self.callback = self._callback
        self.trigger_choice_callback()


class GenericChoice(Choice):
    def choose(self, card):
        super().choose(card)
        for _card in self.cards:
            if _card == card:
                if _card.type == CardType.HERO_POWER:
                    _card.zone = Zone.PLAY
                elif len(self.player.hand) < self.player.max_hand_size:
                    _card.zone = Zone.HAND
                else:
                    _card.discard()
            else:
                _card.discard()


class ChoiceTarget(Choice):
    pass


class _RewindChoice(Choice):
    """Across the Timeways — Rewind.

    After a Rewind card's play effect resolves, the controller chooses between
    two timeline tokens: "Keep Timeline" (TIME_000ta, a no-op) or "Rewind
    Timeline" (TIME_000tb, re-run the parent card's play effect once, re-rolling
    any random outcomes). Both tokens are discarded after the choice; only the
    "Rewind" pick re-queues the effect. The re-run goes through Battlecry, which
    never re-offers Rewind (the choice is queued from Play.do, not Battlecry),
    so a single Rewind triggers exactly one optional repeat.
    """

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        parent = self.source
        # self.cards == [keep_token, rewind_token]; the second is "Rewind".
        rewind_token = self.cards[1]
        for token in self.cards:
            token.discard()
        if card is rewind_token:
            self.game.queue_actions(parent, [Battlecry(parent, parent.target)])
        for action in self._callback:
            self.game.trigger(self.source, [action], [self.player, self.cards, card])
        self.callback = self._callback
        self.trigger_choice_callback()


class CopyDeathrattleBuff(TargetedAction):
    """
    Copy the deathrattles from a card onto the target
    """

    TARGET = ActionArg()
    Buff = ActionArg()

    def get_target_args(self, source, target):
        buff = self._args[1]
        buff = source.controller.card(buff, source=source)
        buff.tags[GameTag.DEATHRATTLE] = True
        buff.source = source
        return [buff]

    def create_buff(self, source):
        buff = self._args[1]
        buff = source.controller.card(buff, source=source)
        buff.tags[GameTag.DEATHRATTLE] = True
        buff.source = source
        return buff

    def do(self, source, target, buff):
        log.info("%r copy deathrattle from %r by %r", source, target, buff)
        if target.has_deathrattle:
            for deathrattle in target.deathrattles:
                source.additional_deathrattles.append(deathrattle)
            buff.apply(source)
            for entity in target.buffs:
                if not entity.has_deathrattle:
                    continue
                new_buff = self.create_buff(source)
                if hasattr(entity, "store_card"):
                    new_buff.store_card = entity.store_card
                for deathrattle in entity.deathrattles:
                    new_buff.additional_deathrattles.append(deathrattle)
                new_buff.apply(source)
        source.game.manager.targeted_action(self, source, target, buff)


class Counter(TargetedAction):
    """
    Counter a card, making it unplayable.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        target.cant_play = True
        source.game.manager.targeted_action(self, source, target)


class Predamage(TargetedAction):
    """
    Predamage target by \a amount.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        amount += target.incoming_damage_adjustment
        amount <<= target.incoming_damage_multiplier
        if source.type == CardType.SPELL:
            amount <<= target.incoming_damage_multiplier_from_spell
        # TITANS — Tar Slick: minions take double damage this turn.
        if (target.type == CardType.MINION
                and getattr(target.controller, "minion_damage_doubled_this_turn", False)):
            amount *= 2
        if target.heavily_armored:
            amount = min(amount, 1)
        divider = target.incoming_damage_divider
        if divider > 1:
            # Ceiling division — matches "half damage, rounded up" semantics
            # used by The Immovable Object.
            amount = -(-amount // divider)
        # TITANS — Amitus: cap incoming damage at incoming_damage_max if > 0.
        cap = target.incoming_damage_max
        if cap > 0:
            amount = min(amount, cap)
        target.predamage = amount
        if amount:
            self.broadcast(source, EventListener.ON, target, amount)
            return source.game.trigger_actions(source, [Damage(target)])[0][0]
        return 0


class PutOnTop(TargetedAction):
    """
    Put card on deck top
    """

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, cards):
        log.info("%r put on %s's deck top", cards, target)
        if not isinstance(cards, list):
            cards = [cards]

        for card in cards:
            if card.controller != target:
                card.zone = Zone.SETASIDE
                card.controller = target
            if card.zone != Zone.DECK and len(target.deck) >= target.max_deck_size:
                log.info("Put(%r) fails because %r's deck is full", card, target)
                continue
            card.zone = Zone.DECK
            target.deck.remove(card)
            target.deck.append(card)
            source.game.manager.targeted_action(self, source, target, card)


class PutOnBottom(TargetedAction):
    """
    Put card on deck bottom
    """

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, cards):
        log.info("%r put on %s's deck bottom", cards, target)
        if not isinstance(cards, list):
            cards = [cards]

        for card in cards:
            if card.controller != target:
                card.zone = Zone.SETASIDE
                card.controller = target
            if card.zone != Zone.DECK and len(target.deck) >= target.max_deck_size:
                log.info("Put(%r) fails because %r's deck is full", card, target)
                continue
            card._summon_index = 0
            card.zone = Zone.DECK
            target.deck.remove(card)
            target.deck.insert(0, card)
            source.game.manager.targeted_action(self, source, target, card)


class Damage(TargetedAction):
    """
    Damage target by \a amount.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount=None):
        if not amount:
            amount = target.predamage
        # Emerald Dream (Firelands) — Fyrakk the Blazing: "Immune to Fire
        # spells." A minion flagged `_immune_to_fire_spells` takes no damage
        # from a Fire-school spell source (its own Fire-spell barrage and any
        # opponent Fire spell pass straight through it).
        if (
            amount
            and getattr(target, "_immune_to_fire_spells", False)
            and getattr(source, "type", None) == CardType.SPELL
            and getattr(source, "spell_school", None) == SpellSchool.FIRE
        ):
            target.predamage = 0
            return
        # Perils in Paradise — Aranna, Thrill Seeker: damage the controller's
        # hero would take on the controller's turn is REDIRECTED (pre-damage)
        # to a random enemy, so the hero never takes it (armor untouched, no
        # on-hero-damage triggers fire).
        if (amount and target.type == CardType.HERO
                and target.controller.current_player
                and any(m.id == "VAC_501" for m in target.controller.field)):
            opp = target.controller.opponent
            enemies = [c for c in [opp.hero] + list(opp.field)
                       if c is not None and not c.dead]
            if enemies:
                target.predamage = 0
                target = target.game.random.choice(enemies)
        # Whizbang's Workshop — Shudderblock: a boosted battlecry can't damage
        # the enemy hero. The enemy hero's controller's opponent is the player
        # whose battlecry is resolving; if that player has the flag set, drop
        # the damage to the hero to 0.
        if amount and target.type == CardType.HERO:
            bc_player = getattr(target.controller, "opponent", None)
            if bc_player is not None and getattr(
                bc_player, "_shudder_no_enemy_hero_dmg", False
            ):
                amount = 0
        amount = target._hit(amount)
        target.predamage = 0
        # TITANS — Fate Splitter: record the source of the killing blow so
        # the target's deathrattle can identify the card that killed it.
        if amount and getattr(target, "health", 1) <= 0:
            target._last_damage_source_id = getattr(source, "id", None)
        if (
            source.type == CardType.MINION or source.type == CardType.HERO
        ) and source.stealthed:
            # TODO this should be an event listener of sorts
            source.stealthed = False
        source.game.manager.targeted_action(self, source, target, amount)
        if amount:
            # check hasattr: some sources of damage are game or player (like fatigue)
            # weapon damage itself after hero attack, but does not trigger lifesteal
            if (
                hasattr(source, "lifesteal")
                and source.lifesteal
                and source.type != CardType.WEAPON
            ):
                if source.controller.lifesteal_damages_opposing_hero:
                    source.game.queue_actions(source.controller, [Hit(target, amount)])
                else:
                    source.heal(source.controller.hero, amount)
            self.broadcast(source, EventListener.ON, target, amount, source)
            # poisonous can not destroy hero
            if (
                hasattr(source, "poisonous")
                and source.poisonous
                and (target.type != CardType.HERO and source.type != CardType.WEAPON)
            ):
                target.destroy()
            # Sunken City: Urchin Spines — your spells are Poisonous this
            # turn. Spell damage on a minion destroys it.
            if (
                source.type == CardType.SPELL
                and target.type != CardType.HERO
                and getattr(source.controller, "spells_poisonous_this_turn", False)
            ):
                target.destroy()
            if (
                hasattr(source, "has_overkill")
                and source.has_overkill
                and source.controller.current_player
                and target.type != CardType.WEAPON
                and target.health < 0
            ):
                if source.type == CardType.HERO:
                    actions = source.controller.weapon.get_actions("overkill")
                else:
                    actions = source.get_actions("overkill")
                if actions:
                    source.game.trigger(source, actions, event_args=None)
            if (
                source.type in (CardType.MINION, CardType.HERO, CardType.SPELL)
                and getattr(source, "has_honorable_kill", False)
                and source.controller.current_player
                and target.type == CardType.MINION
                and target.health == 0
            ):
                # Mark the victim so its own deathrattle can branch on
                # whether the kill was honorable (e.g. Korrak the Bloodrager).
                target.honorably_killed = True
                source.game.queue_actions(
                    source, [HonorableKill(source, target)]
                )
            if target.type == CardType.MINION:
                if target.has_frenzy:
                    source.game.queue_actions(source, [Frenzy(target, amount)])
                # Audiopocalypse — Reverberations glass copies destroy
                # themselves on any damage. The copy carries _glass_dies;
                # destroy via queued action so we don't interrupt the
                # current damage broadcast.
                if getattr(target, "_glass_dies", False) and target.zone == Zone.PLAY:
                    source.game.queue_actions(source, [Destroy(target)])
            target.damaged_this_turn += amount
            if target.type == CardType.HERO:
                target.controller.hero_health_changed_this_turn += 1
                # The Great Dark Beyond — Healthstone restores this turn's hero
                # damage.
                target.controller.hero_damage_taken_this_turn += amount
                if not target.controller.current_player:
                    # Damage dealt to the hero while it's the opponent's turn.
                    target.controller.damage_taken_on_opponents_turn += amount
                else:
                    # TITANS — Imprisoned Horror: cost_mod reads total
                    # hero damage taken on the controller's own turns.
                    target.controller.damage_taken_on_own_turns_this_game += amount
                    # Perils — Sauna Regular: count of distinct damage events.
                    target.controller.hero_damage_events_on_own_turn_this_game += 1
            if source.type == CardType.HERO_POWER:
                source.controller.hero_power_damage_this_game += amount
            self.broadcast(source, EventListener.AFTER, target, amount, source)
        return amount


class Deathrattle(TargetedAction):
    """
    Trigger deathrattles on card targets.
    """

    def do(self, source, target):
        if not target.has_deathrattle:
            return

        if source.controller.cant_trigger_deathrattle:
            log.info(
                "Deathrattle cannot be triggered because cant_trigger_deathrattle is True"
            )
            return

        for entity in target.entities:
            source.game.manager.targeted_action(self, source, target)
            for deathrattle in entity.deathrattles:
                if callable(deathrattle):
                    actions = deathrattle(entity)
                else:
                    actions = deathrattle
                source.game.queue_actions(entity, actions)

                if target.controller.extra_deathrattles:
                    log.info("Triggering deathrattles for %r again", target)
                    source.game.queue_actions(entity, actions)


class Battlecry(TargetedAction):
    """
    Trigger Battlecry on card targets
    """

    CARD = CardArg()
    TARGET = ActionArg()

    def get_target_args(self, source, target):
        arg = self._args[1]
        if isinstance(arg, Selector):
            arg = arg.eval(source.game, source)
            assert len(arg) == 1
            arg = arg[0]
        elif isinstance(arg, LazyValue):
            arg = arg.evaluate(source)
            if hasattr(arg, "__iter__"):
                arg = arg[0]
        else:
            arg = _eval_card(source, arg)[0]
        return [arg]

    def has_extra_battlecries(self, player, card):
        # Brann Bronzebeard
        if player.extra_battlecries and card.has_battlecry:
            return True

        if player.spells_cast_twice and card.type == CardType.SPELL:
            return True

        # Across the Timeways — the empowered Well of Eternity (Lady Azshara)
        # marks each spell it creates so that spell alone casts twice, even
        # without the player-wide spells_cast_twice aura.
        if card.type == CardType.SPELL and getattr(card, "_casts_twice_self", False):
            return True

        # Spirit of the Shark
        if card.type == CardType.MINION:
            if player.minion_extra_combos and card.has_combo and player.combo:
                return True
            if player.minion_extra_battlecries and card.has_battlecry:
                return True

        return False

    def do(self, source, card, target=None):
        player = source.controller

        if card.has_combo and player.combo:
            log.info("Activating %r combo targeting %r", card, target)
            actions = card.get_actions("combo")
        elif card.has_outcast and card.play_outcast:
            log.info("Activating %r outcast targeting %r", card, target)
            actions = card.get_actions("outcast")
        else:
            log.info("Activating %r action targeting %r", card, target)
            actions = card.get_actions("play")

        if card.battlecry_requires_target() and not target:
            log.info("%r requires a target for its battlecry. Will not trigger.")
            return

        # Whizbang's Workshop — Shudderblock: the NEXT battlecry triggers N
        # extra times and can't damage the enemy hero while it resolves.
        # Captured before main_power so a Shudderblock that sets the counter
        # in its own battlecry does not boost itself.
        extra = getattr(player, "next_battlecry_extra", 0)
        if extra and card.has_battlecry:
            player.next_battlecry_extra = 0
            player._shudder_no_enemy_hero_dmg = True
        else:
            extra = 0

        # The Great Dark Beyond — Lucky Comet: the next Combo minion played
        # triggers its Combo an extra time. One-shot per armed charge, separate
        # from Spirit of the Shark's standing minion_extra_combos aura.
        combo_twice = 0
        if (
            card.type == CardType.MINION
            and card.has_combo
            and player.combo
            and getattr(player, "next_combo_triggers_twice", 0) > 0
        ):
            player.next_combo_triggers_twice -= 1
            combo_twice = 1

        source.game.manager.targeted_action(self, source, card, target)
        source.target = target
        source.game.main_power(source, actions, target)

        if self.has_extra_battlecries(player, card):
            source.game.main_power(source, actions, target)

        for _ in range(extra):
            source.game.main_power(source, actions, target)

        for _ in range(combo_twice):
            source.game.main_power(source, actions, target)

        if extra:
            player._shudder_no_enemy_hero_dmg = False

        if card.overload:
            source.game.queue_actions(card, [Overload(player, card.overload)])


class LaunchStarship(TargetedAction):
    """The Great Dark Beyond — launch the player target's Starship: wake the
    Permanent into a real minion with the combined stats and effects of all
    banked Starship Pieces."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .cards import db

        player = target
        ship = getattr(player, "starship", None)
        if ship is None or ship.zone != Zone.PLAY:
            return
        pieces = getattr(ship, "_starship_pieces", [])

        # Wake the ship: no longer a dormant, untouchable Permanent. It launches
        # with summoning sickness (turns_in_play 0) unless a piece gave it Rush
        # or Charge.
        ship.dormant = False
        ship.dormant_turns = 0
        ship.cant_be_damaged = False
        ship.turns_in_play = 0

        spellbursts = []
        launch_effects = []
        for info in pieces:
            data = db[info["id"]]
            scripts = data.scripts
            for tag in info["keywords"]:
                ship.tags[tag] = True
            if info["divine_shield"]:
                ship.divine_shield = True
            deathrattle = getattr(scripts, "deathrattle", None)
            if deathrattle:
                ship.additional_deathrattles.append(deathrattle)
                ship.has_deathrattle = True
            events = getattr(scripts, "events", None)
            if events:
                ship._events.extend(events)
            spellburst = getattr(scripts, "spellburst", None)
            if spellburst:
                spellbursts.append(spellburst)
            # Heroes of StarCraft — Starship Pieces with a "When this is
            # launched, …" effect declare it as `launch`; it fires once,
            # immediately, as the ship launches (distinct from Spellburst).
            launch = getattr(scripts, "launch", None)
            if launch:
                launch_effects.append(launch)
        if spellbursts:
            ship._starship_spellbursts = spellbursts
            ship.has_spellburst = True
        # Retain the banked launch effects on the ship so Jim Raynor can
        # relaunch it (re-fire its "when launched" effects) later this game.
        ship._starship_launch_effects = launch_effects

        # Heroes of StarCraft — count this launch (Thor / Jim Raynor scale off
        # the number of Starships launched this game).
        player._sc_starships_launched += 1

        player.starship = None
        # Record the just-launched ship so battlecries that fire alongside the
        # launch (The Exodar's Protocol choice) can read its assembled stats and
        # banked Pieces.
        player._last_launched_ship = ship
        source.game.manager.targeted_action(self, source, target)
        source.game.refresh_auras()
        # Fire each banked Piece's immediate "when launched" effect now, with
        # the assembled ship as the source.
        for launch in launch_effects:
            actions = launch
            if callable(actions):
                actions = actions(ship, None)
            if not isinstance(actions, (list, tuple)):
                actions = [actions]
            source.game.queue_actions(ship, list(actions))
        # The Gravitational Displacer — if banked, the launch summons a copy of
        # the assembled ship. Build the copy explicitly under the launching
        # player and transfer the combined stats/keywords/effects (a fresh
        # token only carries base stats).
        if any(info["id"] == "GDB_466" for info in pieces):
            copy = player.card(ship.id, source=ship)
            copy.controller = player
            copy.dormant = False
            copy.cant_be_damaged = False
            copy._starship_pieces = list(getattr(ship, "_starship_pieces", []))
            # Check specific keyword tags directly — iterating ship.tags.items()
            # would touch the description tag and format its {0} placeholder.
            for tag in (
                GameTag.TAUNT,
                GameTag.RUSH,
                GameTag.CHARGE,
                GameTag.WINDFURY,
                GameTag.LIFESTEAL,
                GameTag.POISONOUS,
                GameTag.REBORN,
                GameTag.DIVINE_SHIELD,
            ):
                if ship.tags.get(tag):
                    copy.tags[tag] = True
            copy.divine_shield = getattr(ship, "divine_shield", False)
            copy.additional_deathrattles = list(
                getattr(ship, "additional_deathrattles", [])
            )
            if copy.additional_deathrattles:
                copy.has_deathrattle = True
            copy._events = list(getattr(ship, "_events", []))
            sb = list(getattr(ship, "_starship_spellbursts", []))
            if sb:
                copy._starship_spellbursts = sb
                copy.has_spellburst = True
            # Match the assembled ship's stats BEFORE summoning — a fresh ship
            # token has base 0/0 and would die on entry otherwise.
            copy.atk = ship.atk
            copy.max_health = ship.max_health
            copy.damage = 0
            source.game.cheat_action(player, [Summon(player, copy)])
        return ship


class _StarshipSpellburst(TargetedAction):
    """Spellburst delegation for a launched Starship — replay each banked
    piece's own spellburst with the ship as the source."""

    TARGET = ActionArg()

    def do(self, source, target):
        for spellburst in getattr(target, "_starship_spellbursts", []):
            actions = spellburst
            if callable(actions):
                actions = actions(target, None)
            if not isinstance(actions, (list, tuple)):
                actions = [actions]
            source.game.queue_actions(target, list(actions))


class Reborn(TargetedAction):
    """Broadcast-only marker fired after a minion returns via the Reborn
    keyword. `target` is the minion that was reborn — listeners (e.g. Auchenai
    Death-Speaker) react to it."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.manager.targeted_action(self, source, target)
        self.broadcast(source, EventListener.ON, target)


class Overheal(TargetedAction):
    """Broadcast-only marker fired when a heal overheals its target. `target`
    is the overhealed character; `amount` is the overheal amount. Listeners
    (e.g. Anchorite) react to it."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        source.game.manager.targeted_action(self, source, target, amount)
        self.broadcast(source, EventListener.ON, target, amount)


class Discovered(TargetedAction):
    """Broadcast-only marker fired after a player resolves a Discover.
    `target` is the discovering player; `card` is the chosen card. Listeners
    (e.g. Rangari Scout) react to it."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        source.game.manager.targeted_action(self, source, target, card)
        self.broadcast(source, EventListener.ON, target, card)


class ExtraBattlecry(Battlecry):
    def has_extra_battlecries(self, player, card):
        return False

    def do(self, source, card, target=None):
        if target is None:
            old_requirements = source.requirements
            source.requirements = card.requirements
            if source.requires_target():
                # ExtraBattlecry can fire when the original target is
                # no longer valid (it died, moved zones, etc.). With
                # no playable target, fall through with target=None
                # — the battlecry_requires_target() check below skips
                # the extra trigger cleanly. Without this guard,
                # random.choice([]) crashes the soak.
                targets = source.play_targets
                if targets:
                    target = source.game.random.choice(targets)
            source.requirements = old_requirements

        if source == "GIL_820" and card == "GIL_820":
            return

        if card.battlecry_requires_target() and not target:
            log.info("%r requires a target for its battlecry. Will not trigger.")
            return

        source.target = target
        old_target = card.target
        card.target = target
        actions = card.get_actions("play")
        source.game.manager.targeted_action(self, source, card, target)
        source.game.main_power(source, actions, target)
        card.target = old_target


class PlayHeroPower(TargetedAction):
    HERO_POWER = CardArg()
    TARGET = ActionArg()

    def do(self, source, heropower, targets):
        actions = heropower.get_actions("activate")
        if not hasattr(targets, "__iter__"):
            targets = [targets]
        for target in targets:
            heropower.target = target
            source.game.manager.targeted_action(self, source, heropower, target)
            source.game.main_power(heropower, actions, target)


class Destroy(TargetedAction):
    """
    Destroy character targets.
    """

    def do(self, source, target):
        if getattr(target, "dormant", False) and target.zone == Zone.PLAY:
            log.info("%r is dormant cannot be destroyed", target)
            return
        if target.delayed_destruction:
            #  If the card is in PLAY, it is instead scheduled to be destroyed
            # It will be moved to the graveyard on the next Death event
            log.info("%r marks %r for imminent death", source, target)
            target.to_be_destroyed = True
            source.game.manager.targeted_action(self, source, target)
        else:
            log.info("%r destroys %r", source, target)
            if target.type == CardType.ENCHANTMENT:
                target.remove()
            else:
                target.zone = Zone.GRAVEYARD
                source.game.manager.targeted_action(self, source, target)


class Discard(TargetedAction):
    """
    Discard card targets in a player's hand
    """

    TARGET = ActionArg()

    def do(self, source, target):
        self.broadcast(source, EventListener.ON, target)
        log.info("Discarding %r", target)
        old_zone = target.zone
        target.zone = Zone.REMOVEDFROMGAME
        source.game.manager.targeted_action(self, source, target)
        if old_zone == Zone.HAND:
            target.tags[DISCARDED] = True
            actions = target.get_actions("discard")
            source.game.cheat_action(target, actions)


class Dredge(TargetedAction):
    """
    Look at the bottom 3 cards of your deck; choose one to put on top.
    Exposes Dredge.CARD so follow-up effects can predicate on the choice.
    """

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        # Bottom 3 — deck[-1] is the top (next draw), deck[0] is the bottom.
        cards = list(target.deck[:3])
        return [cards]

    def do(self, source, target, cards):
        log.info("%r dredges %r for %s", source, cards, target)
        if not cards:
            # Empty deck — no choice to offer. Subsequent .then() clauses
            # will see Dredge.CARD = None.
            self.cards = []
            return
        player = source.controller
        player.choice = self
        self._callback = self.callback
        self.callback = []
        self.player = player
        self.source = source
        self.target = target
        self.cards = cards
        self.min_count = 1
        self.max_count = 1
        source.game.manager.targeted_action(self, source, target, cards)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid Dredge choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        # Move the chosen card to the TOP of the deck (deck[-1]). Keep the
        # other dredged cards in their original positions at the bottom.
        deck = self.target.deck
        if card in deck:
            deck.remove(card)
            deck.append(card)
        for action in self._callback:
            self.source.game.trigger(
                self.source, [action], [self.target, self.cards, card]
            )
        self.callback = self._callback
        self.trigger_choice_callback()


class Discover(TargetedAction):
    """
    Opens a generic choice for three random cards matching a filter.
    """

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        if target.hero.data.card_class != CardClass.NEUTRAL:
            # use hero class for Discover if not neutral (eg. Ragnaros)
            discover_class = target.hero.data.card_class
        elif source.data.card_class != CardClass.NEUTRAL:
            # use card class for neutral hero classes
            discover_class = source.data.card_class
        else:
            # use random class for neutral hero classes with neutral cards
            discover_class = target.starting_hero.data.card_class
        if "card_class" in self._args[1].filters:
            picker = self._args[1] * 3
            return [picker.evaluate(source)]
        picker = self._args[1] * 3
        picker = picker.copy_with_weighting(1, card_class=CardClass.NEUTRAL)
        picker = picker.copy_with_weighting(1, card_class=discover_class)
        cards = picker.evaluate(source)
        if len(cards) == 0:
            picker = self._args[1] * 3
            # When discover random secret
            discover_class = source.data.card_class
            picker = picker.copy_with_weighting(1, card_class=discover_class)
            cards = picker.evaluate(source)
        return [cards]

    def do(self, source, target, cards):
        log.info("%r discovers %r for %s", source, cards, target)
        self.cards = cards
        player = source.controller
        player.choice = self
        self._callback = self.callback
        self.callback = []
        self.player = player
        self.source = source
        self.target = target
        self.cards = cards
        self.min_count = 1
        self.max_count = 1
        source.game.manager.targeted_action(self, source, target, cards)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        # The Great Dark Beyond — Discover tracking + "After you Discover" event.
        self.player.discovers_this_game += 1
        self.player.discovers_this_turn += 1
        for action in self._callback:
            self.source.game.trigger(
                self.source, [action], [self.target, self.cards, card]
            )
        self.callback = self._callback
        self.trigger_choice_callback()
        self.source.game.queue_actions(self.source, [Discovered(self.player, card)])


def make_kiljaeden_demon(player):
    """Create one Demon for Kil'jaeden's endless portal, in the player's deck,
    carrying the portal's current accumulated +2/+2 bonus."""
    pool = getattr(player, "_kiljaeden_pool", None)
    if not pool:
        return None
    cid = player.game.random.choice(pool)
    card = player.card(cid, source=player.hero)
    card.controller = player
    card.zone = Zone.DECK
    card._kiljaeden_demon = True
    bonus = getattr(player, "_kiljaeden_bonus", 0)
    if bonus:
        player.hero.buff(card, "GDB_145de", atk=bonus, max_health=bonus)
    return card


class Draw(TargetedAction):
    """
    Make player targets draw a card from their deck.
    """

    TARGET = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        args = super().get_target_args(source, target)
        if args:
            card = args[0]
            if hasattr(card, "__iter__"):
                card = card[0]
            return [card]
        if target.deck:
            card = target.deck[-1]
        elif getattr(target, "_kiljaeden_active", False):
            # Kil'jaeden's endless portal: instead of running dry (and
            # fatiguing), conjure a fresh Demon carrying the portal's current
            # escalating +2/+2 bonus.
            card = make_kiljaeden_demon(target)
        else:
            card = None
        return [card]

    def do(self, source, target, card):
        if card is None:
            target.fatigue()
            return []
        if len(target.hand) >= target.max_hand_size:
            log.info("%s overdraws and loses %r!", target, card)
            card.discard()
        else:
            log.info("%s draws %r", target, card)
            card.zone = Zone.HAND
            card.turn_drawn = source.game.turn
            source.controller.cards_drawn_this_turn += 1
            # Cataclysm — Shatter: a SHATTER card shatters when drawn, splitting
            # into its two "Shattered" half-cards which replace it in hand. A
            # card that has already been recombined carries `_no_reshatter` and
            # is drawn whole (the permanent "won't Shatter again" enchant).
            if card.data.tags.get(GameTag.SHATTER, 0) and not getattr(
                card, "_no_reshatter", False
            ):
                _shatter_into_halves(card, target)
                return [card]
            # The Great Dark Beyond — The Ceaseless Expanse cost ledger.
            source.game.cards_dpd_this_game = (
                getattr(source.game, "cards_dpd_this_game", 0) + 1
            )
            source.game.manager.targeted_action(self, source, target, card)
            self.broadcast(source, EventListener.ON, target, card, source)
            if source.game.step > Step.BEGIN_MULLIGAN:
                # Proc the draw script, but only if we are past mulligan
                # Materialize to a list: a card may define `draw` as a
                # generator method (def draw: yield ...) — e.g. Emerald Portal
                # EDR_445pt3 — and the casts-when-drawn branch below appends a
                # tuple, which a generator does not support (`gen += tuple`).
                actions = list(card.get_actions("draw"))
                if card.casts_when_drawn and card.type == CardType.SPELL:
                    # "Cast When Drawn" SPELLS: cast for free, then draw a
                    # replacement. MINIONS with CASTS_WHEN_DRAWN are
                    # "Summoned When Drawn" — they rely on their own `draw`
                    # script (Summon SELF), never the spell cast path (which
                    # would Destroy+Draw+Battlecry and, with the Summon script,
                    # recurse). Modern data tags such minions with
                    # CASTS_WHEN_DRAWN (e.g. Frost Tyrant, VAC Parachutes).
                    actions += (Destroy(SELF), Draw(CONTROLLER), Battlecry(SELF, None))
                source.game.cheat_action(card, actions)

        return [card]


class Fatigue(TargetedAction):
    """
    Hit a player with a tick of fatigue
    """

    TARGET = ActionArg()

    def do(self, source, target):
        if target.cant_fatigue:
            log.info("%s can't fatigue and does not take damage", target)
            return
        target.fatigue_counter += 1
        log.info("%s takes %i fatigue damage", target, target.fatigue_counter)
        source.game.manager.targeted_action(self, source, target)
        return source.game.queue_actions(
            source, [Hit(target.hero, target.fatigue_counter)]
        )


class ForceDraw(TargetedAction):
    """
    Draw card targets into their owners hand
    """

    TARGET = ActionArg()

    def do(self, source, target):
        target.draw()
        return [target]


class DrawUntil(TargetedAction):
    """
    Make target player target draw up to \a amount cards minus their hand count.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if target not in target.game.players:
            raise InvalidAction("%r is not a player" % target)
        difference = max(0, amount - len(target.hand))
        if difference > 0:
            return source.game.queue_actions(source, [Draw(target) * difference])


class FullHeal(TargetedAction):
    """
    Fully heal character targets.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        source.heal(target, target.max_health)


class GainArmor(TargetedAction):
    """
    Make hero targets gain \a amount armor.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        target.armor += amount
        if amount > 0 and hasattr(target, "controller"):
            target.controller.armor_gained_this_game += amount
            # TITANS — Stoneskin Armorer reads per-turn armor gained.
            target.controller.armor_gained_this_turn += amount
        source.game.manager.targeted_action(self, source, target, amount)
        self.broadcast(source, EventListener.ON, target, amount)


class SpendCorpses(TargetedAction):
    """
    March of the Lich King — spend \a amount Corpses from player targets.
    Decrements `controller.corpses`. Caller is responsible for gating
    on availability (most cards check `Attr(CONTROLLER, "corpses") >= n`
    before queueing Spend).
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        spent = min(target.corpses, max(amount, 0))
        target.corpses = max(target.corpses - amount, 0)
        target.corpses_spent_this_game += spent
        source.game.manager.targeted_action(self, source, target, amount)


class GainMana(TargetedAction):
    """
    Give player targets \a Mana crystals.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def get_target_args(self, source, target):
        ret = super().get_target_args(source, target)
        amount = ret[0]
        if target.max_mana + amount > target.max_resources:
            amount = target.max_resources - target.max_mana
        return [amount]

    def do(self, source, target, amount):
        target.max_mana = max(target.max_mana + amount, 0)
        source.game.manager.targeted_action(self, source, target, amount)


class SpendMana(TargetedAction):
    """
    Make player targets spend \a amount Mana.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        log.info("%s pays %i mana", target, amount)
        _amount = amount
        if target.temp_mana:
            # Coin, Innervate etc
            used_temp = min(target.temp_mana, amount)
            _amount -= used_temp
            target.temp_mana -= used_temp
        target.used_mana = max(target.used_mana + _amount, 0)
        source.game.manager.targeted_action(self, source, target, amount)
        self.broadcast(source, EventListener.AFTER, target, amount)


class SetMana(TargetedAction):
    """
    Set player to targets Mana crystals.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        old_mana = target.mana
        target.max_mana = amount
        target.used_mana = max(
            0, target.max_mana - target.overload_locked - old_mana + target.temp_mana
        )
        source.game.manager.targeted_action(self, source, target, amount)


class Give(TargetedAction):
    """
    Give player targets card \a id.
    """

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, cards):
        log.info("Giving %r to %s", cards, target)
        ret = []
        to_shatter = []
        if not hasattr(cards, "__iter__"):
            # Support Give on multiple cards at once (eg. Echo of Medivh)
            cards = [cards]
        for card in cards:
            if len(target.hand) >= target.max_hand_size:
                log.info("Give(%r) fails because %r's hand is full", card, target)
                continue
            # Cross-controller Give (e.g. stealing from the opponent's deck):
            # detach from the OLD controller's zone cache via the shared
            # SETASIDE first, so the controller switch doesn't leave _set_zone
            # trying to remove the card from the NEW controller's cache (which
            # raises ValueError). Limited to deck/hand/graveyard so play-zone
            # bounces are unaffected.
            if card.controller is not target and card.zone in (
                Zone.DECK,
                Zone.HAND,
                Zone.GRAVEYARD,
            ):
                card.zone = Zone.SETASIDE
            card.controller = target
            card.zone = Zone.HAND
            ret.append(card)
            source.game.manager.targeted_action(self, source, target, card)
            self.broadcast(source, EventListener.AFTER, target, card)
            # MotLK — Concoction Mix: if `card` is a Concoction and the
            # target already holds another Concoction, transform the
            # held one into the corresponding Mixed Concoction.
            _concoction_mix_on_give(target, card)
            # Cataclysm — Shatter: a Shatter card also splits when GENERATED
            # into hand (Discover, "get a card", etc.), not just when drawn.
            # Skip a recombined card (_no_reshatter), a card handed over
            # "already combined" (Stolen Power sets _giving_combined_shatter),
            # and re-entrant gives from a split already in progress.
            if (
                card.data.tags.get(GameTag.SHATTER, 0)
                and not getattr(card, "_no_reshatter", False)
                and not getattr(source.game, "_giving_combined_shatter", False)
                and not getattr(source.game, "_shattering", False)
            ):
                to_shatter.append((card, target))
        for scard, starget in to_shatter:
            _shatter_into_halves(scard, starget)
        return ret


# MotLK — Concoction Mix lookup. Maps (held_id, given_id) → mixed token
# id. The data only ships a sparse set of explicit pairs; (a, b) and
# (b, a) map to the same product. Unmapped pairs leave the held card
# untouched (the engine has no token for the combination).
CONCOCTION_IDS = {
    "RLK_570t1", "RLK_570t2", "RLK_570t3", "RLK_570t4", "RLK_570t5",
}
_CONCOCTION_MIXES_RAW = {
    ("RLK_570t1", "RLK_570t1"): "RLK_570t1t4",  # Slimy + Slimy
    ("RLK_570t1", "RLK_570t2"): "RLK_570t1t2",  # Slimy + Dreadful
    ("RLK_570t1", "RLK_570t3"): "RLK_570t1t3",  # Slimy + Bubbling
    ("RLK_570t1", "RLK_570t4"): "RLK_570t1t1",  # Slimy + Hazy
    ("RLK_570t1", "RLK_570t5"): "RLK_570tt1",   # Slimy + Gleaming
    ("RLK_570t2", "RLK_570t2"): "RLK_570t2t2",  # Dreadful + Dreadful
    ("RLK_570t2", "RLK_570t3"): "RLK_570t2t1",  # Dreadful + Bubbling
    ("RLK_570t2", "RLK_570t4"): "RLK_570t4t1",  # Dreadful + Hazy
    ("RLK_570t3", "RLK_570t3"): "RLK_570t3t",   # Bubbling + Bubbling
    ("RLK_570t3", "RLK_570t4"): "RLK_570t4t2",  # Bubbling + Hazy
    ("RLK_570t4", "RLK_570t4"): "RLK_570t4t3",  # Hazy + Hazy
}
# Symmetric lookup (both orderings of the pair).
CONCOCTION_MIXES = {}
for (a, b), mix in _CONCOCTION_MIXES_RAW.items():
    CONCOCTION_MIXES[(a, b)] = mix
    CONCOCTION_MIXES[(b, a)] = mix


def _concoction_mix_on_give(player, given_card):
    """If the just-given card is a Concoction and the player holds at
    least one other Concoction, morph the held one into the matching
    Mixed Concoction. Only one held Concoction mixes per give — pick
    the leftmost in hand for determinism."""
    if given_card.id not in CONCOCTION_IDS:
        return
    for held in list(player.hand):
        if held is given_card:
            continue
        if held.id not in CONCOCTION_IDS:
            continue
        mix_id = CONCOCTION_MIXES.get((held.id, given_card.id))
        if mix_id is None:
            return
        player.game.cheat_action(given_card, [Morph(held, mix_id)])
        return


class Hit(TargetedAction):
    """
    Hit character targets by \a amount.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        amount = source.get_damage(amount, target)
        if amount:
            source.game.manager.targeted_action(self, source, target, amount)
            return source.game.queue_actions(source, [Predamage(target, amount)])[0][0]
        return 0


class HitExcessDamage(TargetedAction):
    """
    Hit character targets by \a amount and excess damage to other.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()
    EXCEDSS_AMOUNT = IntArg()

    def get_target_args(self, source, target):
        amount = _eval_card(source, self._args[1])
        while hasattr(amount, "__iter__"):
            if len(amount) == 0:
                amount = None
            else:
                amount = amount[0]
        amount = source.get_damage(amount, target)
        excess_amount = 0
        if target.health < amount:
            excess_amount = amount - target.health
        return [amount, excess_amount]

    def do(self, source, target, amount, excess_amount):
        if amount:
            source.game.manager.targeted_action(self, source, target, amount)
            source.game.queue_actions(source, [Predamage(target, amount)])
        return excess_amount


class Heal(TargetedAction):
    """
    Heal character targets by \a amount.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if source.controller.healing_as_damage:
            return source.game.queue_actions(source.controller, [Hit(target, amount)])

        # Cataclysm — Ruby Sanctum: "Your next Healing effect this turn deals
        # damage instead." Single-use: the next healing effect (amount > 0) is
        # consumed and converted to damage of the same magnitude, then the flag
        # clears. (Distinct from healing_as_damage, which converts the whole
        # turn's heals.)
        if amount > 0 and source.controller.next_heal_deals_damage:
            source.controller.next_heal_deals_damage = False
            return source.game.queue_actions(source.controller, [Hit(target, amount)])

        # Festival of Legends — track requested heal vs. actually-applied
        # on the target so Overheal-aware listeners (Hedanis, Heartthrob,
        # Dreamboat) can read the overheal amount. Pure-overheal calls
        # (target was already full) do NOT broadcast a Heal event — that
        # would break Lightwarden / Northshire Cleric / Truesilver, which
        # gate on "an actual heal happened".
        requested = source.get_heal(amount, target)
        # Cataclysm — Cleansing Cleric: "Your healing effects restore 2 more
        # Health this game." Flat additive bonus on every healing effect
        # (applied after spellpower/doubling); only real heals (amount > 0) get
        # the bonus.
        if amount > 0 and source.controller.extra_healing_this_game:
            requested += source.controller.extra_healing_this_game
        actual = min(requested, target.damage)
        target._last_heal_requested = requested
        overheal_amount = max(0, requested - actual)
        target._last_heal_overheal = overheal_amount
        if overheal_amount > 0:
            # Audiopocalypse — per-turn counter for Ambient Lightspawn.
            # Bumped only when an actual overheal happens; reset at
            # OWN_TURN_BEGIN.
            source.controller.overheals_triggered_this_turn += 1
            # The Great Dark Beyond — Anchorite reacts to any overheal (even a
            # pure overheal, which broadcasts no Heal event).
            source.game.queue_actions(
                source, [Overheal(target, overheal_amount)]
            )
        amount = actual
        if amount:
            # Undamaged targets do not receive heals
            log.info("%r heals %r for %i", source, target, amount)
            target.damage -= amount
            source.game.manager.targeted_action(self, source, target, amount)
            self.queue_broadcast(self, (source, EventListener.ON, target, amount))
            target.healed_this_turn += amount
            source.controller.healed_this_game += amount
            if target.type == CardType.HERO:
                source.controller.hero_health_changed_this_turn += 1


class ManaThisTurn(TargetedAction):
    """
    Give player targets \a amount Mana this turn.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        target.temp_mana += min(target.max_resources - target.mana, amount)
        source.game.manager.targeted_action(self, source, target, amount)


class Mill(TargetedAction):
    """
    Mill \a count cards from the top of the player targets' deck.
    """

    TARGET = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        if target.deck:
            card = target.deck[-1]
        else:
            card = None
        return [card]

    def do(self, source, target, card):
        if card is None:
            return []
        source.game.manager.targeted_action(self, source, target, card)
        card.discard()
        self.broadcast(source, EventListener.ON, target, card, source)

        return [card]


class Morph(TargetedAction):
    """
    Morph minion target into \a minion id
    """

    TARGET = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        card = _eval_card(source, self._args[1])
        assert len(card) == 1
        card = card[0]
        card.controller = target.controller
        return [card]

    def do(self, source, target, card):
        log.info("Morphing %r into %r", target, card)
        # Castle Nathria — Baroness Vashj: "If this would transform
        # into a minion, summon that minion instead." Vashj stays; the
        # would-be morph target is summoned to the board. No
        # general-purpose aura yet (CardManager.update drops
        # non-GameTag keys), so we id-check directly — same pattern as
        # Halkias's soul-in-secret marker.
        if (
            getattr(target, "id", None) == "REV_925"
            and card.type == CardType.MINION
            and target.zone == Zone.PLAY
        ):
            log.info("%r redirects transform — summoning %r instead", target, card)
            source.game.queue_actions(
                target.controller, [Summon(target.controller, card)]
            )
            return card
        target_zone = target.zone
        if card.zone != target_zone:
            # Transfer the zone position
            card._summon_index = target.zone_position
            # In-place morph is OK, eg. in the case of Lord Jaraxxus
            card.zone = target_zone
        target.clear_buffs()
        target.zone = Zone.SETASIDE
        target.morphed = card
        source.game.manager.targeted_action(self, source, target, card)
        return card


class FillMana(TargetedAction):
    """
    Refill \a amount mana crystals from player targets.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        target.used_mana = max(0, target.used_mana - amount)
        source.game.manager.targeted_action(self, source, target, amount)


class Retarget(TargetedAction):
    TARGET = ActionArg()
    NEW_TARGET = CardArg()

    def do(self, source, target, new_target):
        if not new_target:
            return
        if isinstance(new_target, list):
            assert len(new_target) == 1
            new_target = new_target[0]
        if target.type in (CardType.HERO, CardType.MINION) and target.attacking:
            log.info("Retargeting %r's attack to %r", target, new_target)
            # proposed_defender can be None if the original defender already
            # left the proposed-attack state (rare board interactions); guard
            # the deref before clearing it.
            if source.game.proposed_defender is not None:
                source.game.proposed_defender.defending = False
            source.game.proposed_defender = new_target
        else:
            log.info("Retargeting %r from %r to %r", target, target.target, new_target)
            target.target = new_target
        source.game.manager.targeted_action(self, source, target, new_target)

        return new_target


class Reveal(TargetedAction):
    """
    Reveal secret targets.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        log.info("Revealing %r", target)
        if target.zone == Zone.SECRET and target.data.secret:
            self.broadcast(source, EventListener.ON, target)
            target.triggered_secret = True
            # TITANS — Starstrung Bow: count friendly secrets that have triggered.
            target.controller.secrets_triggered_this_game += 1
            # Whizbang mini-set — Product 9: remember each triggered Secret's
            # id so it can recast them all later.
            target.controller.secrets_triggered_cards_this_game.append(target.id)
            target.zone = Zone.GRAVEYARD
            # Castle Nathria — Halkias's soul: if this secret was
            # marked, resummon Halkias when it triggers.
            if getattr(target, "_resummons_halkias", False):
                target._resummons_halkias = False
                source.game.queue_actions(
                    target.controller, [Summon(target.controller, "REV_829")]
                )
        source.game.manager.targeted_action(self, source, target)


class SetCurrentHealth(TargetedAction):
    """
    Sets the current health of the character target to \a amount.
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        log.info("Setting current health on %r to %i", target, amount)
        maxhp = target.max_health
        target.damage = max(0, maxhp - amount)
        source.game.manager.targeted_action(self, source, target, amount)
        return target


class SetTags(TargetedAction):
    """
    Sets targets' given tags.
    """

    TARGET = ActionArg()
    TAGS = ActionArg()

    def do(self, source, target, tags_list):
        for tags in tags_list:
            if isinstance(tags, dict):
                for tag, value in tags.items():
                    target.tags[tag] = _eval_card(source, value)[0]
            else:
                for tag in tags:
                    target.tags[tag] = True
        self.broadcast(source, EventListener.AFTER, target)


class UnsetTags(TargetedAction):
    """
    Unset targets' given tags.
    """

    TARGET = ActionArg()
    TAGS = ActionArg()

    def do(self, source, target, tags_list):
        for tags in tags_list:
            for tag in tags:
                target.tags[tag] = False


class GetTag(TargetedAction):
    TARGET = ActionArg()
    TAG = CardArg()

    def do(self, source, target, tag):
        return target.tags[tag]


class Silence(TargetedAction):
    """
    Silence minion targets.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        log.info("Silencing %r", self)
        if target.type != CardType.MINION:
            return
        self.broadcast(source, EventListener.ON, target)
        target.clear_buffs()
        for attr in target.silenceable_attributes:
            if getattr(target, attr):
                setattr(target, attr, False)

        # Wipe the event listeners
        target._events = []
        target.silenced = True
        source.game.manager.targeted_action(self, source, target)


class Summon(TargetedAction):
    """
    Make player targets summon \a id onto their field.
    This works for equipping weapons as well as summoning minions.
    """

    TARGET = ActionArg()
    CARD = ActionArg()

    def _broadcast(self, entity, source, at, *args):
        # Prevent cards from triggering off their own summon
        if entity is args[1]:
            return
        return super()._broadcast(entity, source, at, *args)

    def get_summon_index(self, source_index):
        return source_index + 1

    def do(self, source, target, cards):
        log.info("%s summons %r", target, cards)
        if not isinstance(cards, list):
            cards = [cards]

        for card in cards:
            # Defensive: Summon can only place summonable card types
            # (Minion / Weapon / Hero / HeroPower). Random card pools
            # occasionally hand back Enchantments which have no
            # is_summonable; skip those instead of crashing.
            if not hasattr(card, "is_summonable") or not card.is_summonable():
                continue
            if card.controller != target:
                card.controller = target
            # Poisoned Blade
            if (
                card.controller.weapon
                and card.controller.weapon.id == "AT_034"
                and source.type == CardType.HERO_POWER
                and card.type == CardType.WEAPON
            ):
                continue
            if card.zone != Zone.PLAY:
                if source.type == CardType.MINION:
                    if source.zone == Zone.PLAY:
                        source_index = source.controller.field.index(source)
                        card._summon_index = self.get_summon_index(source_index)
                    elif source.zone == Zone.GRAVEYARD:
                        card._summon_index = getattr(source, "_dead_position", None)
                        if card._summon_index is not None:
                            card._summon_index += cards.index(card)
                card.zone = Zone.PLAY
            if card.type == CardType.MINION and Race.TOTEM in card.races:
                card.controller.times_totem_summoned_this_game += 1
            # TITANS per-game minion-id summon counters.
            if card.type == CardType.MINION:
                _cid = card.id
                if _cid == "TTN_401":
                    card.controller.astral_automatons_summoned_this_game += 1
                elif _cid == "TTN_900t":
                    card.controller.earthens_summoned_this_game += 1
                elif _cid in ("TTN_926a", "TTN_950t2", "ETC_373t", "EX1_158t"):
                    card.controller.treants_summoned_this_game += 1
            source.game.manager.targeted_action(self, source, target, card)
            self.queue_broadcast(self, (source, EventListener.ON, target, card))
            self.broadcast(source, EventListener.AFTER, target, card)

            # A minion may carry a `summoned` script — a self-effect that fires
            # when IT enters play via Summon. The summon broadcast above excludes
            # a card from its own summon event, so this is how "When summoned, …"
            # tokens (e.g. Cataclysm's Soldier of Azshara) react to their own
            # arrival. Called directly on the card, so it can't recurse into the
            # summon-event loop the self-exclusion guards against.
            summoned_actions = card.get_actions("summoned")
            if summoned_actions:
                source.game.cheat_action(card, summoned_actions)

            # Colossal: when a parent Colossal minion is summoned, also
            # summon its appendages alongside it. Limbs are tokens named
            # {parent_id}t, t2, … with COLOSSAL_LIMB=1. Limbs do NOT
            # themselves re-trigger this hook (they don't have COLOSSAL).
            if (
                card.type == CardType.MINION
                and card.data.tags.get(GameTag.COLOSSAL, 0)
                and not card.data.tags.get(GameTag.COLOSSAL_LIMB, 0)
            ):
                _summon_colossal_limbs(source, target, card)

            # Thornmantle Musician (ETC_831) Finale: the NEXT Beast the
            # controller summons gets +1/+1. Consume the one-shot
            # `next_beast_summon_bonus` counter here so it lands on the
            # first eligible Beast and self-clears.
            if (
                card.type == CardType.MINION
                and getattr(target, "next_beast_summon_bonus", 0) > 0
                and Race.BEAST in getattr(card, "races", [])
            ):
                target.next_beast_summon_bonus -= 1
                source.game.cheat_action(
                    source,
                    [Buff(card, "ETC_831e")],
                )

        return cards


class SummonBothSides(Summon):
    TARGET = ActionArg()
    CARD = ActionArg()

    def get_summon_index(self, source_index):
        return source_index + ((self.trigger_index + 1) % 2)


class SummonCustomMinion(TargetedAction):
    """
    Summon custom minion with cost/atk/max_health
    """

    TARGET = ActionArg()
    CARD = ActionArg()
    COST = IntArg()
    ATK = IntArg()
    HEALTH = IntArg()

    def do(self, source, target, cards, cost, atk, health):
        if health <= 0:
            return
        if not isinstance(cards, list):
            cards = [cards]
        for card in cards:
            card.custom_card = True

            def create_custom_card(card):
                card.cost = cost
                card.atk = atk
                card.max_health = health

            card.create_custom_card = create_custom_card
            card.create_custom_card(card)

            if card.is_summonable():
                source.game.queue_actions(source, [Summon(target, card)])


class Shuffle(TargetedAction):
    """
    Shuffle card targets into player target's deck.
    """

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, cards):
        log.info("%r shuffles into %s's deck", cards, target)
        if not isinstance(cards, list):
            cards = [cards]

        for card in cards:
            if card.controller != target:
                card.zone = Zone.SETASIDE
                card.controller = target
            if len(target.deck) >= target.max_deck_size:
                log.info("Shuffle(%r) fails because %r's deck is full", card, target)
                continue
            card.zone = Zone.DECK
            target.shuffle_deck()
            source.game.manager.targeted_action(self, source, target, card)
            self.broadcast(source, EventListener.AFTER, target, card)


class PutOnBottom(TargetedAction):
    """
    Put card targets on the BOTTOM of the player target's deck — used by
    the Sunken City "Azsharan" cards which seed a 'Sunken' counterpart at
    the bottom of the deck. Bottom = deck[0] (deck[-1] is the next draw).
    """

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, cards):
        log.info("%r placed on the bottom of %s's deck", cards, target)
        if not isinstance(cards, list):
            cards = [cards]
        for card in cards:
            if card.controller != target:
                card.zone = Zone.SETASIDE
                card.controller = target
            if len(target.deck) >= target.max_deck_size:
                log.info(
                    "PutOnBottom(%r) fails because %r's deck is full", card, target
                )
                continue
            # Set zone to DECK then move to the bottom (index 0).
            card.zone = Zone.DECK
            if card in target.deck:
                target.deck.remove(card)
                target.deck.insert(0, card)
            source.game.manager.targeted_action(self, source, target, card)
            self.broadcast(source, EventListener.AFTER, target, card)


class Swap(TargetedAction):
    TARGET = ActionArg()
    OTHER = CardArg()

    def clear_buff(self, target, old_zone):
        if old_zone == Zone.PLAY and target.zone not in (
            Zone.PLAY,
            Zone.GRAVEYARD,
            Zone.SETASIDE,
        ):
            if not target.keep_buff:
                target.clear_buffs()
            if target.id == target.controller.cthun.id:
                target.controller.copy_cthun_buff(target)

    def do(self, source, target, other):
        if other is not None:
            other._summon_index = target.zone_position - 1
            target._summon_index = other.zone_position - 1
            target_old_zone = target.zone
            other_old_zone = other.zone
            target.zone = Zone.SETASIDE
            other.zone = Zone.SETASIDE
            target.controller, other.controller = other.controller, target.controller
            target.zone = other_old_zone
            other.zone = target_old_zone
            self.clear_buff(target, target_old_zone)
            self.clear_buff(other, other_old_zone)
            source.game.manager.targeted_action(self, source, target, other)


class Steal(TargetedAction):
    """
    Make the controller take control of targets.
    The controller is the controller of the source of the action.
    """

    TARGET = ActionArg()
    CONTROLLER = ActionArg()

    def get_target_args(self, source, target):
        if len(self._args) > 1:
            # Controller was specified
            controller = self.eval(self._args[1], source)
            assert len(controller) == 1
            controller = controller[0]
        else:
            # Default to the source's controller
            controller = source.controller
        return [controller]

    def do(self, source, target, controller):
        log.info("%s takes control of %r", controller, target)
        zone = target.zone
        target.zone = Zone.SETASIDE
        target.controller = controller
        target.turns_in_play = 0  # To ensure summoning sickness
        target.zone = zone
        source.game.manager.targeted_action(self, source, target, controller)


class UnlockOverload(TargetedAction):
    """
    Unlock the target player's overload, both current and owed.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        log.info("%s overload gets cleared", target)
        target.overloaded = 0
        target.overload_locked = 0
        source.game.manager.targeted_action(self, source, target)


class SummonJadeGolem(TargetedAction):
    """
    Summons a Jade Golem for target player according to his Jade Golem Status
    """

    TARGET = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        jade_id = f"CFM_712_t{target.jade_golem:02d}"
        return _eval_card(source, jade_id)

    def do(self, source, target, card):
        log.info("%s summons a Jade Golem for %s", source, target)
        target.jade_golem = min(
            30, target.jade_golem + 1
        )  # Jade golem maximum of 30/30.
        if card.is_summonable():
            source.game.queue_actions(source, [Summon(target, card)])


class CastSpell(TargetedAction):
    """
    Cast a spell target random
    """

    TARGET = ActionArg()
    SPELL_TARGET = ActionArg()

    def get_target_args(self, source, target):
        ret = super().get_target_args(source, target)
        spell_target = [None]
        if ret:
            spell_target = ret[0]
        return [spell_target]

    def choose_target(self, source, card):
        return source.game.random.choice(card.targets)

    def do(self, source, card, targets):
        if source.type == CardType.MINION and (
            source.dead or source.silenced or source.zone != Zone.PLAY
        ):
            return

        player = source.controller
        old_choice = player.choice
        player.choice = None

        # `twinspell` is only defined on Spell; guard for the rare path
        # where this CastSpell-style branch resolves a Minion (e.g. a
        # Discover chain that lands a non-spell card).
        if getattr(card, "twinspell", None):
            source.game.queue_actions(card, [Give(player, card.twinspell_copy)])
        if card.must_choose_one:
            card = source.game.random.choice(card.choose_cards)
        for target in targets:
            if card.requires_target() and not target:
                if len(card.targets) > 0:
                    if target not in card.targets:
                        target = self.choose_target(source, card)
                else:
                    log.info("%s cast spell %s don't have a legal target", source, card)
                    return
            card.target = target
            card.zone = Zone.PLAY
            log.info("%s cast spell %s target %s", source, card, target)
            # Record this effect-driven cast in the controller's cast ledger
            # (hand-plays are recorded in Play.do). CastSpell.do sets the
            # zone directly and bypasses Play.do's append, so without this an
            # effect-cast spell (Yogg in the Box, random casts, another Orb)
            # would never count toward "spells you've cast this game".
            if card.type == CardType.SPELL:
                player.spells_cast_this_game.append(card)
            source.game.manager.targeted_action(self, source, card, target)
            source.game.queue_actions(card, [Battlecry(card, card.target)])
            while player.choice:
                choice = source.game.random.choice(player.choice.cards)
                log.info("Choosing card %r" % (choice))
                player.choice.choose(choice)
            while player.opponent.choice:
                choice = source.game.random.choice(player.opponent.choice.cards)
                log.info("Choosing card %r" % (choice))
                player.opponent.choice.choose(choice)
            player.choice = old_choice


class CastSpellTargetsEnemiesIfPossible(CastSpell):
    def choose_target(self, source, card):
        enemy_targets = []
        for entity in card.targets:
            if entity.controller == source.controller.opponent:
                enemy_targets.append(entity)
        if enemy_targets:
            return source.game.random.choice(enemy_targets)
        return source.game.random.choice(card.targets)


class CastSpellTargetsSelfIfPossible(CastSpell):
    def choose_target(self, source, card):
        if source in card.targets:
            return source
        return source.game.random.choice(card.targets)


class Evolve(TargetedAction):
    """
    Transform your minions into random minions that cost (\a amount) more
    """

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        cost = target.cost + amount
        card_set = RandomMinion(cost=cost).find_cards(source)
        if card_set:
            card = source.game.random.choice(card_set)
            return source.game.queue_actions(source, [Morph(target, card)])[0]


class ExtraAttack(TargetedAction):
    """
    Get target an extra attack change
    """

    TARGET = ActionArg()

    def do(self, source, target):
        log.info("%s gets an extra attack change.", target)
        target.num_attacks -= 1
        source.game.manager.targeted_action(self, source, target)


class SwapStateBuff(TargetedAction):
    """
    Swap stats between two minions using \a buff.
    """

    TARGET = ActionArg()
    OTHER = CardArg()
    BUFF = CardArg()

    def do(self, source, target, other, buff):
        log.info("swap state %s and %s", target, other)
        if not target or not other:
            return
        buff1 = buff
        buff1.source = source
        buff1._xcost = other.cost
        if other.type == CardType.MINION:
            buff1._xatk = other.atk
            buff1._xhealth = other.health
        buff2 = source.controller.card(buff.id, source=source)
        buff2.source = source
        buff2._xcost = target.cost
        if target.type == CardType.MINION:
            buff2._xatk = target.atk
            buff2._xhealth = target.health
        buff1.apply(target)
        buff2.apply(other)
        source.game.manager.targeted_action(self, source, target, other, buff)


class CopyStateBuff(TargetedAction):
    """
    Copy target state, buff on self
    """

    TARGET = ActionArg()
    OTHER = CardArg()
    BUFF = CardArg()

    def do(self, source, target, buff):
        target = target
        buff = source.controller.card(buff, source=source)
        buff.source = source
        buff._xatk = target.atk
        buff._xhealth = target.health
        buff.apply(source)
        source.game.manager.targeted_action(self, source, target, buff)


class SetStateBuff(TargetedAction):
    """
    Set target state, buff on target
    """

    TARGET = ActionArg()
    OTHER = CardArg()
    BUFF = CardArg()

    def do(self, source, target, other, buff):
        target = target
        buff = source.controller.card(buff, source=source)
        buff.source = source
        buff._xcost = other.cost
        buff._xatk = other.atk
        buff._xhealth = other.health
        buff.apply(target)
        source.game.manager.targeted_action(self, source, target, buff)


class RefreshHeroPower(TargetedAction):
    """
    Helper to Refresh Hero Power
    """

    HEROPOWER = ActionArg()

    def do(self, source, heropower):
        log.info("Refresh Hero Power %s.", heropower)
        if heropower.heropower_disabled:
            return
        if not heropower.exhausted:
            return
        heropower.additional_activations_this_turn += 1
        source.game.manager.targeted_action(self, source, heropower)


# Into the Emerald Dream — IMBUE.
# Maps a player's class to its Imbued Hero Power token. Only six classes
# have one in the 219197 data; the other four (DK / DH / Rogue / Warlock /
# Warrior) have no Imbued token, so neutral Imbue cards still *count* (bump
# imbues_this_game) but leave the Hero Power unchanged.
IMBUED_HERO_POWERS = {
    CardClass.DRUID: "EDR_847p",     # Blessing of the Golem
    CardClass.HUNTER: "EDR_850p",    # Blessing of the Wolf
    CardClass.MAGE: "EDR_851p",      # Blessing of the Wisp
    CardClass.PALADIN: "EDR_445p",   # Blessing of the Dragon
    CardClass.PRIEST: "EDR_449p",    # Blessing of the Moon
    CardClass.SHAMAN: "EDR_448p",    # Blessing of the Wind
    # Across the Timeways mini-set adds Imbued Hero Powers for two more classes.
    CardClass.ROGUE: "END_000p",     # Blessing of the Bronze
    CardClass.DEATHKNIGHT: "END_003p",  # Blessing of the Infinite
}


def imbued_hero_power_for(player):
    """Return the Imbued Hero Power id for *player*'s class, or None."""
    for card_class in player.hero.classes:
        if card_class in IMBUED_HERO_POWERS:
            return IMBUED_HERO_POWERS[card_class]
    return IMBUED_HERO_POWERS.get(player.hero.card_class, None)


class Imbue(TargetedAction):
    """
    Into the Emerald Dream — "Imbue your Hero Power."

    Replaces *target* player's Hero Power with their class's Imbued Hero
    Power token and bumps the per-game ``imbues_this_game`` counter. On
    subsequent imbues the counter keeps climbing, so the Imbued Hero
    Power's effect scales (its ``activate`` reads
    ``controller.imbues_this_game``). The token also caches the level on
    its ``imbue_level`` attribute for convenience / cosmetics.

    Classes without an Imbued Hero Power still increment the counter so
    payoff cards (e.g. EDR_860 "Imbued twice", EDR_888 "Imbued 4 times")
    behave consistently regardless of class.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        # Accept a player directly, or a hero / character whose controller
        # is the player to imbue.
        if hasattr(target, "imbues_this_game"):
            player = target
        else:
            player = getattr(target, "controller", target)
        log.info("%r imbues %s's Hero Power", source, player)
        player.imbues_this_game += 1
        source.game.manager.targeted_action(self, source, player)

        power_id = imbued_hero_power_for(player)
        if power_id is None:
            # Class with no Imbued Hero Power — count only, HP unchanged.
            return

        existing = player.hero_power
        if existing is not None and existing.id == power_id:
            # Already imbued this class's power — keep the same token but
            # refresh its cached level so its scaling stays in sync.
            existing.imbue_level = player.imbues_this_game
            return

        new_power = player.card(power_id, source=source)
        new_power.imbue_level = player.imbues_this_game
        source.game.queue_actions(player, [Summon(player, new_power)])
        return new_power


class Herald(TargetedAction):
    """Cataclysm — "Herald".

    Advances the controller toward Deathwing: bumps the per-game
    ``heralds_this_game`` counter. Deathwing, Worldbreaker (CATA_190h) reads it
    to choose more Cataclysms to unleash and to reduce its own Cost, and other
    Herald payoffs (e.g. Ultraxion) read it too. Like Imbue, this is purely a
    counter — the payoff lives on the cards that consume it.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        player = target if hasattr(target, "heralds_this_game") else target.controller
        player.heralds_this_game += 1
        log.info("%r heralds (now %i)", player, player.heralds_this_game)
        source.game.manager.targeted_action(self, source, player)


def _shatter_into_halves(card, player):
    """Cataclysm — Shatter: replace a SHATTER card with its two "Shattered"
    half-cards in the player's hand, and bump the per-game shatter counter. The
    full card never resolves; you play the halves independently.

    Most SHATTER cards name their halves ``<id>t`` + ``<id>t2``, but Schism
    (CATA_306) uniquely uses ``<id>t1`` + ``<id>t2``. Probe all three suffixes
    and give whichever actually exist in the data so both conventions work (the
    suffixes are mutually exclusive per card — no card defines both ``t`` and
    ``t1``).

    Per the wiki, one half is placed at the **left-most** hand slot so the pair
    starts apart; if they later become adjacent again they recombine (see
    ``process_shatter_recombine``). Both halves are tagged with their parent id
    and a shared "birth" token so an un-separated freshly-split pair does not
    instantly re-merge."""
    from .cards import db

    game = player.game
    base = card.id
    card.discard()
    game._shatter_active = True
    token = getattr(game, "_shatter_split_counter", 0) + 1
    game._shatter_split_counter = token

    # Suppress the recombine scan while we are mid-split: each Give runs an
    # action_end (which would otherwise re-merge the first half with the
    # not-yet-tagged second half right back into the parent).
    game._shattering = True
    try:
        given = []
        for half in (base + "t", base + "t1", base + "t2"):
            if half not in db:
                continue
            before = len(player.hand)
            game.cheat_action(player, [Give(player, half)])
            if len(player.hand) > before:
                h = player.hand[-1]
                h._shatter_parent = base
                h._shatter_sibling = token
                h._shatter_separated = False
                given.append(h)
        # One half goes to the left-most position (wiki) so the pair is not
        # adjacent in a non-trivial hand; the other stays where it was given.
        if given:
            first = given[0]
            try:
                player.hand.remove(first)
                player.hand.insert(0, first)
            except ValueError:
                pass
    finally:
        game._shattering = False
    player.shatters_this_game += 1


# Lazily-built map: Shattered-half id -> (parent id, tuple of all half ids).
_SHATTER_HALF_INDEX = None


def _shatter_half_index():
    global _SHATTER_HALF_INDEX
    if _SHATTER_HALF_INDEX is not None:
        return _SHATTER_HALF_INDEX
    from .cards import db

    idx = {}
    for cid in db:
        if not db[cid].tags.get(GameTag.SHATTER, 0):
            continue
        halves = tuple(cid + s for s in ("t", "t1", "t2") if (cid + s) in db)
        for h in halves:
            idx[h] = (cid, halves)
    _SHATTER_HALF_INDEX = idx
    return idx


def _shatter_pair_parent(a, b, idx):
    """Return the shared parent id if ``a`` and ``b`` are the two DISTINCT halves
    that together make one Shatter parent, else None. Halves from different
    copies of the same card still match (only their suffixes must complete the
    set); two copies of the SAME half do not."""
    ia = idx.get(getattr(a, "id", None))
    ib = idx.get(getattr(b, "id", None))
    if not ia or not ib or ia[0] != ib[0] or a.id == b.id:
        return None
    return ia[0]


def process_shatter_recombine(player):
    """Cataclysm — Shatter recombine: when the two matching Shattered halves are
    adjacent in hand they merge back into the full card. The recombined card
    appears where they met, combines both halves' enchantments (and direct cost
    deltas), and is permanently marked so it never Shatters again. Run after
    every settled action block (cheap no-op unless the player holds halves)."""
    if getattr(player.game, "_shattering", False):
        return  # mid-split: don't merge half-tagged siblings back together
    idx = _shatter_half_index()
    hand = player.hand

    # 1) A born-together sibling pair that is NOT currently adjacent has been
    #    pulled apart; mark it so that re-meeting later triggers a recombine
    #    (a fresh split that is still adjacent must NOT instantly re-merge).
    for i, card in enumerate(hand):
        sib = getattr(card, "_shatter_sibling", None)
        if sib is None:
            continue
        neighbours = []
        if i > 0:
            neighbours.append(hand[i - 1])
        if i + 1 < len(hand):
            neighbours.append(hand[i + 1])
        partner_adjacent = any(
            _shatter_pair_parent(card, nb, idx)
            and getattr(nb, "_shatter_sibling", None) == sib
            for nb in neighbours
        )
        if not partner_adjacent:
            card._shatter_separated = True

    # 2) Recombine adjacent completing pairs (restart after each merge — indices
    #    shift). Skip an un-separated born-together sibling pair.
    changed = True
    while changed:
        changed = False
        for i in range(len(hand) - 1):
            a, b = hand[i], hand[i + 1]
            parent_id = _shatter_pair_parent(a, b, idx)
            if not parent_id:
                continue
            sib_a = getattr(a, "_shatter_sibling", None)
            same_birth = sib_a is not None and sib_a == getattr(
                b, "_shatter_sibling", None
            )
            separated = getattr(a, "_shatter_separated", True) or getattr(
                b, "_shatter_separated", True
            )
            if same_birth and not separated:
                continue
            _do_shatter_recombine(player, i, a, b, parent_id)
            changed = True
            break


def _do_shatter_recombine(player, index, a, b, parent_id):
    # Capture, before the halves leave play:
    #  - the combined cost DISCOUNT each half carries below its own printed cost
    #    (reading live .cost folds in both direct _cost edits and cost-reduction
    #    enchants — every half prints at the parent's cost), and
    #  - every enchantment id, to re-apply (Spell Damage +1, stat buffs, …).
    total_discount = sum(max(0, (half.data.cost or 0) - half.cost) for half in (a, b))
    buff_ids = [buff.id for half in (a, b) for buff in list(half.buffs)]
    a.zone = Zone.REMOVEDFROMGAME
    b.zone = Zone.REMOVEDFROMGAME
    # Rebuild the full card where the halves met; it never Shatters again.
    parent = player.card(parent_id, source=a)
    parent._no_reshatter = True
    parent._summon_index = index
    parent.zone = Zone.HAND
    parent._summon_index = None
    # Combine enchantments first…
    for bid in buff_ids:
        try:
            parent.buff(parent, bid)
        except Exception:
            pass
    # …then set the recombined cost last so it wins over any cost-enchant's own
    # _cost adjustment (that reduction is already folded into total_discount).
    parent._cost = max(0, (parent.data.cost or 0) - total_discount)


class MultipleChoice(TargetedAction):
    PLAYER = ActionArg()
    choose_times = 2

    def do(self, source, player):
        self.player = player
        self.source = source
        self.min_count = 1
        self.max_count = 1
        self.choosed_cards = []
        self.player.choice = self
        self._callback = self.callback
        self.callback = []
        getattr(self, "do_step1")()
        source.game.manager.targeted_action(self, source, player)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.choosed_cards.append(card)
        lens = len(self.choosed_cards)
        if lens < self.choose_times:
            getattr(self, f"do_step{lens+1}")()
        else:
            self.player.choice = None
            self.done()
            self.callback = self._callback
            self.trigger_choice_callback()


class GameStart(GameAction):
    """
    Setup game
    """

    def do(self, source):
        log.info("Game start")
        source.game.manager.game_action(self, source)
        self.broadcast(source, EventListener.ON)


class Adapt(TargetedAction):
    """
    Adapt target
    """

    TARGET = ActionArg()
    CARDS = ActionArg()
    CARD = CardArg()

    def get_target_args(self, source, target):
        choices = [
            "UNG_999t10",
            "UNG_999t2",
            "UNG_999t3",
            "UNG_999t4",
            "UNG_999t5",
            "UNG_999t6",
            "UNG_999t7",
            "UNG_999t8",
            "UNG_999t13",
            "UNG_999t14",
        ]
        cards = source.game.random.sample(choices, 3)
        cards = [source.controller.card(card, source=source) for card in cards]
        return [cards]

    def do(self, source, target, cards):
        log.info("%r adapts %r for %s", source, cards, target)
        self.cards = cards
        player = source.controller
        player.choice = self
        self.player = player
        self.source = source
        self.target = target
        self.cards = cards
        self.min_count = 1
        self.max_count = 1
        source.game.manager.targeted_action(self, source, target, cards)

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        self.source.game.trigger(self.source, (Battlecry(card, self.target),), None)
        self.trigger_choice_callback()


class AddProgress(TargetedAction):
    """
    Add Progress for target, such as quest card and upgradeable card
    """

    TARGET = ActionArg()
    CARD = CardArg()
    AMOUNT = IntArg()

    def do(self, source, target, card=None, amount=1):
        log.info("%r add progress from %r", target, card)
        if not target:
            return
        # Progress is tracked on cards (quests / upgradeable cards), never on a
        # Player. A few quests gate AddProgress behind a Find() over a
        # player-returning selector (e.g. TLC_631 Unleash the Colossus uses
        # `Find(CURRENT_PLAYER + CONTROLLER) & AddProgress(SELF, 1)`); on rare
        # evaluation paths a Player can slip through as the target. Ignore any
        # target that can't take progress rather than crashing.
        if not hasattr(target, "add_progress"):
            return
        target.add_progress(card, amount)
        source.game.manager.targeted_action(self, source, target, card, amount)


class ClearProgress(TargetedAction):
    """
    Clear Progress for target
    """

    TARGET = ActionArg()

    def do(self, source, target):
        log.info("%r clear progress", target)
        target.clear_progress()
        source.game.manager.targeted_action(self, source, target)


class Reward(GameAction):
    """
    Reward
    """

    CARDS = ActionArg()

    def do(self, source, cards):
        source.game.manager.game_action(self, source, cards)
        for card in cards:
            if not card.is_card or not card.finished:
                return
            log.info("%r is finished", card)
            if card.zone == Zone.SECRET:
                card.zone = Zone.GRAVEYARD
                card.destroy()
            source.game.trigger(card, card.get_actions("reward"), event_args=None)
            card.clear_progress()


class LosesDivineShield(TargetedAction):
    """
    Losses Divine Shield
    """

    TARGET = ActionArg()

    def do(self, source, target):
        target.divine_shield = False
        source.game.manager.targeted_action(self, source, target)
        self.broadcast(source, EventListener.AFTER, target)


class Remove(TargetedAction):
    """
    Remove character targets
    """

    TARGET = ActionArg()

    def do(self, source, target):
        target.zone = Zone.REMOVEDFROMGAME
        source.game.manager.targeted_action(self, source, target)


class Replay(TargetedAction):
    """
    Cast it if it's spell, otherwise summon it (minion, weapon, hero).
    Now only for Tess Greymane (GIL_598)
    """

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.manager.targeted_action(self, source, target)
        if target.type == CardType.SPELL:
            source.game.queue_actions(source, [CastSpell(target)])
        else:
            source.game.queue_actions(source, [Summon(source.controller, target)])


class Invoke(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, galakrond):
        source.game.manager.targeted_action(self, source, galakrond)
        source.controller.invoke_counter += 1
        if galakrond is not None:
            source.game.queue_actions(
                source,
                [
                    Reveal(galakrond),
                    PlayHeroPower(galakrond.data.hero_power, None),
                    AddProgress(galakrond, source),
                ],
            )


class Awaken(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        if not target.dormant:
            return
        target.dormant = False
        target.turns_in_play = 0
        source.game.manager.targeted_action(self, source, target)
        self.broadcast(source, EventListener.ON, target, source)
        actions = target.get_actions("awaken")
        if actions:
            source.game.trigger(target, actions, event_args=None)


class Dormant(TargetedAction):
    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        target.dormant = True
        target.dormant_turns += amount
        source.game.manager.targeted_action(self, source, target, amount)


class ReopenLocation(TargetedAction):
    """Perils in Paradise — "reopen" a Location: clear its cooldown so it can
    be used again immediately (this turn), keeping its remaining durability.
    No-op if the location has left play (e.g. it ran out of charges)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None or target.zone != Zone.PLAY:
            return
        target.cooldown = 0
        source.game.manager.targeted_action(self, source, target)


class SwapDecks(GameAction):
    """
    Swap decks between two players
    """

    def do(self, source):
        game = source.game
        player1 = game.player1
        player2 = game.player2
        player1.deck, player2.deck = player2.deck, player1.deck
        for card in player1.deck:
            card.controller = player1
        for card in player2.deck:
            card.controller = player2


class SwapHands(GameAction):
    """
    Swap hands between two players
    """

    def do(self, source):
        game = source.game
        player1 = game.player1
        player2 = game.player2
        player1.hand, player2.hand = player2.hand, player1.hand
        for card in player1.hand:
            card.controller = player1
        for card in player2.hand:
            card.controller = player2


class Corrupt(TargetedAction):
    """
    Corrupt target
    """

    TARGET = ActionArg()

    def get_corrupt_card(self, source, target):
        corrupt_card = getattr(target, "corrupt_card", None)
        if isinstance(corrupt_card, str):
            return source.controller.card(corrupt_card)
        if callable(corrupt_card):
            return corrupt_card(target)
        return None

    def do(self, source, target):
        corrupt_card = self.get_corrupt_card(source, target)
        if not corrupt_card:
            return
        copy_buffs(source, target, corrupt_card)
        source.game.queue_actions(source, [Morph(target, corrupt_card)])
        source.game.manager.targeted_action(self, source, target)
        return corrupt_card


class ForgeCard(TargetedAction):
    """TITANS — Forge a card in hand.

    Spends 2 extra mana (the universal Forge premium) and morphs the card
    into its Forged version.  `forge_card` is a class attribute on the card
    script (a string card ID, e.g. "TTN_042t").  Also bumps
    `controller.cards_forged_this_game` for Ignis / Melted Maker synergy.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        # forge_card may be on the card instance OR on its script class
        # (card.data.scripts). Check both so tests that forge cards directly
        # work even when the card instance doesn't shadow the class attribute.
        forge_id = getattr(target, "forge_card", None)
        if not forge_id:
            forge_id = getattr(
                getattr(getattr(target, "data", None), "scripts", None),
                "forge_card", None,
            )
        if not forge_id:
            return
        ctrl = target.controller
        if ctrl.used_mana + 2 > ctrl.max_mana:
            return
        ctrl.used_mana += 2
        forged = ctrl.card(forge_id)
        copy_buffs(source, target, forged)
        source.game.queue_actions(source, [Morph(target, forged)])
        ctrl.cards_forged_this_game += 1
        source.game.manager.targeted_action(self, source, target)
        # Broadcast AFTER event so Melted Maker can listen for Forge activations.
        # Pass `forged` — after Morph runs, the forged instance is the card now
        # living in the player's hand, so FRIENDLY_HAND listeners can match it.
        # (The original `target` has been moved to SETASIDE by Morph and would
        # not match any in-hand selector.)
        self.broadcast(source, EventListener.AFTER, forged)


class Spellburst(TargetedAction):
    """
    Spellburst
    """

    TARGET = CardArg()
    SPELL = CardArg()

    def get_actions(self, target, spell):
        actions = getattr(target.data.scripts, "spellburst")
        if callable(actions):
            actions = actions(target, spell)
        if actions is None:
            actions = []
        elif not isinstance(actions, (list, tuple)):
            actions = [actions]
        else:
            actions = list(actions)
        # Per-instance spellbursts grafted onto this minion (e.g. Nexus-Prince
        # Shaffar propagating its Spellburst onto a buffed hand minion).
        actions += list(getattr(target, "_instance_spellbursts", []))
        return actions

    def do(self, source, target, spell):
        if not target.has_spellburst:
            log.info("%r does not have spellburst", target)
            return

        actions = self.get_actions(target, spell)
        source.game.queue_actions(target, actions, event_args=[target, spell])
        # A spellburst script may request to keep its Spellburst (K'ara keeps
        # it on Shadow spells); honour that one-shot flag, else clear as usual.
        if getattr(target, "_rearm_spellburst", False):
            target._rearm_spellburst = False
        else:
            target.has_spellburst = False
        source.game.manager.targeted_action(self, source, target, spell)


class Frenzy(TargetedAction):
    """
    Frenzy
    """

    TARGET = CardArg()
    AMOUNT = IntArg()

    def get_actions(self, target, amount):
        actions = getattr(target.data.scripts, "frenzy")
        if callable(actions):
            actions = actions(target, amount)
        return actions

    def do(self, source, target, amount):
        if not target.has_frenzy or target.dead:
            log.info("%s does not have frenzy or is dead", target)
            return

        actions = self.get_actions(target, amount)
        source.game.queue_actions(target, actions, event_args=[target, amount])
        target.has_frenzy = False
        source.game.manager.targeted_action(self, source, target)


class HonorableKill(TargetedAction):
    """
    Honorable Kill — fires when an attacker's combat damage exactly destroys
    its target. Scripts reference the killed minion via HonorableKill.TARGET.
    """

    TARGET = CardArg()
    VICTIM = CardArg()

    def get_actions(self, target, victim):
        scripts = target.data.scripts
        if target.type == CardType.HERO:
            scripts = target.controller.weapon.data.scripts
        actions = getattr(scripts, "honorable_kill")
        if callable(actions):
            actions = actions(target, victim)
        return actions

    def do(self, source, target, victim):
        actions = self.get_actions(target, victim)
        if not actions:
            return
        source.game.queue_actions(target, actions, event_args=[target, victim])
        source.game.manager.targeted_action(self, source, target, victim)


class IncreaseAttr(TargetedAction):
    """
    Increase a named instance attribute on the target by `amount`. Used for
    ad-hoc Player counters (next-hero-power flags, Choose-One discounts,
    etc.) where defining a dedicated action class is overkill.

    The attribute name is passed verbatim as a string and NOT routed through
    the card-id resolver, so we override get_target_args.
    """

    TARGET = ActionArg()
    ATTR = ActionArg()
    AMOUNT = IntArg()

    def get_target_args(self, source, target):
        # Skip _eval_card for the ATTR string; keep IntArg eval for AMOUNT.
        attr = self._args[1]
        amount = _eval_card(source, self._args[2])
        if isinstance(amount, list):
            amount = amount[0] if amount else 0
        return [attr, amount]

    def do(self, source, target, attr, amount):
        setattr(target, attr, getattr(target, attr, 0) + amount)


class TickObjective(TargetedAction):
    """
    Decrement an Objective spell's remaining-turns counter; destroy it when
    the counter reaches zero. Fires at the end of the controller's turn.
    """

    TARGET = CardArg()

    def do(self, source, target):
        target.turns_remaining -= 1
        if target.turns_remaining <= 0:
            source.game.queue_actions(source, [Destroy(target)])


class Trade(GameAction):
    """
    Trade
    """

    TARGET = CardArg()

    def do(self, source, target):
        player = target.controller
        if len(player.deck) == 0:
            log.info("%s does not have a card to trade", player)
            return
        player.pay_cost(player, 1)
        target.zone = Zone.SETASIDE
        self.broadcast(source, EventListener.ON, target)
        player.draw()
        target._summon_index = source.game.random.randint(0, len(player.deck))
        target.zone = Zone.DECK
        source.game.manager.targeted_action(self, source, target)
        actions = target.get_actions("trade")
        if actions:
            source.game.trigger(target, actions, event_args=None)


# Showdown in the Badlands — Excavate treasure pools (non-collectible
# WILD_WEST cards). Each Excavate digs one tier deeper; the controller's
# class decides whether tier 4 (a class Legendary) is reachable.
EXCAVATE_TIERS = {
    # DEEP_999t1/t2/t3 (Heartblossom / Deepholm Geode / World Pillar Fragment)
    # are the three neutral treasures the Delve into Deepholm mini-set added to
    # the shared tier pools (rarity Common/Rare/Epic -> tiers 1/2/3).
    1: ["WW_001t", "WW_001t18", "WW_001t2", "WW_001t3", "WW_001t4", "DEEP_999t1"],
    2: ["WW_001t16", "WW_001t5", "WW_001t7", "WW_001t8", "WW_001t9", "DEEP_999t2"],
    3: ["WW_001t11", "WW_001t12", "WW_001t13", "WW_001t14", "WW_001t17", "DEEP_999t3"],
}
# Tier-4 class Legendary treasures. Five Excavate classes shipped in Patch
# 28.0; Paladin and Shaman gained theirs in the Delve into Deepholm mini-set
# (DEEP_999t4 The Azerite Dragon / DEEP_999t5 The Azerite Murloc). A class
# absent from this map tops out at tier 3.
EXCAVATE_LEGENDARY = {
    CardClass.ROGUE: "WW_001t23",
    CardClass.MAGE: "WW_001t24",
    CardClass.WARLOCK: "WW_001t25",
    CardClass.DEATHKNIGHT: "WW_001t26",
    CardClass.WARRIOR: "WW_001t27",
    CardClass.PALADIN: "DEEP_999t4",
    CardClass.SHAMAN: "DEEP_999t5",
}


class Excavate(TargetedAction):
    """
    Showdown in the Badlands — the target player Excavates a treasure.

    Each Excavate digs one tier deeper: 1st = random 1-mana Common, 2nd =
    2-mana Rare, 3rd = 3-mana Epic. Excavate-identity classes (those in
    EXCAVATE_LEGENDARY) dig a 4th tier for their unique 4-mana Legendary.
    After the deepest tier the cycle restarts at tier 1.
    """

    TARGET = ActionArg()

    def _tier_for(self, player):
        max_tier = 4 if player.hero.data.card_class in EXCAVATE_LEGENDARY else 3
        # excavates_this_game is bumped before this call, so it is the
        # 1-indexed ordinal of the dig being resolved.
        n = player.excavates_this_game
        return ((n - 1) % max_tier) + 1

    def do(self, source, target):
        player = target
        player.excavates_this_game += 1
        tier = self._tier_for(player)
        if tier == 4:
            card_id = EXCAVATE_LEGENDARY[player.hero.data.card_class]
        else:
            card_id = source.game.random.choice(EXCAVATE_TIERS[tier])
        log.info("%s Excavates (tier %i) -> %s", player, tier, card_id)
        if len(player.hand) >= player.max_hand_size:
            log.info("%s's hand is full; Excavated treasure is lost", player)
            return []
        card = player.card(card_id, source=source)
        card.zone = Zone.HAND
        source.game.manager.targeted_action(self, source, target)
        self.broadcast(source, EventListener.AFTER, target, card)
        return [card]
