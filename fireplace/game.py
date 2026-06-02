import time
from random import Random
from calendar import timegm
from itertools import chain
from typing import TYPE_CHECKING

from hearthstone.enums import BlockType, CardType, PlayState, State, Step, Zone

from .actions import (
    Attack,
    Awaken,
    BeginTurn,
    Death,
    Destroy,
    Draw,
    EndTurn,
    EventListener,
    GameStart,
    Play,
    Reward,
    Summon,
    Trade,
)
from .card import THE_COIN
from .cards import standard_board_skins
from .enums import BoardEnum
from .entity import Entity
from .exceptions import GameOver
from .managers import GameManager
from .utils import CardList

if TYPE_CHECKING:
    from .actions import Action
    from .card import Character, PlayableCard
    from .player import Player


class BaseGame(Entity):
    type = CardType.GAME
    MAX_MINIONS_ON_FIELD = 7
    MAX_SECRETS_ON_PLAY = 5
    Manager = GameManager

    def __init__(self, players: "list[Player]", seed=None):
        self.random = Random(seed)
        self.player1: Player
        self.player2: Player
        self.data = None
        self.players = players
        super().__init__()
        for player in players:
            player.game = self
        self.state = State.INVALID
        self.step = Step.BEGIN_FIRST
        self.next_step = Step.BEGIN_SHUFFLE
        self.turn = 0
        self.current_player: Player = None
        self.next_players: list[Player] = []
        self.tick = 0
        self.active_aura_buffs = CardList()
        self.setaside = CardList()
        self._action_stack = 0

    def __repr__(self):
        return "%s(players=%r)" % (self.__class__.__name__, self.players)

    def __iter__(self):
        return chain(
            self.entities,
            self.hands,
            self.decks,
            self.graveyard,
            self.setaside,
            self.removed,
        )

    @property
    def game(self):
        return self

    @property
    def is_standard(self):
        return self.player1.is_standard and self.player2.is_standard

    @property
    def board(self):
        ret = CardList(chain(self.players[0].field, self.players[1].field))
        ret.sort(key=lambda e: e.play_counter)
        return ret

    @property
    def decks(self):
        return CardList(chain(self.players[0].deck, self.players[1].deck))

    @property
    def hands(self):
        return CardList(chain(self.players[0].hand, self.players[1].hand))

    @property
    def characters(self):
        ret = CardList(chain(self.players[0].characters, self.players[1].characters))
        ret.sort(key=lambda e: e.play_counter)
        return ret

    @property
    def graveyard(self):
        return CardList(chain(self.players[0].graveyard, self.players[1].graveyard))

    @property
    def removed(self):
        return CardList(chain(self.players[0].removed, self.players[1].removed))

    @property
    def entities(self):
        ret = CardList(
            chain([self], self.players[0].entities, self.players[1].entities)
        )
        ret.sort(key=lambda e: e.play_counter)
        return ret

    @property
    def live_entities(self):
        ret = CardList(
            chain(self.players[0].live_entities, self.players[1].live_entities)
        )
        ret.sort(key=lambda e: e.play_counter)
        return ret

    @property
    def minions_killed_this_turn(self):
        return (
            self.players[0].minions_killed_this_turn
            + self.players[1].minions_killed_this_turn
        )

    @property
    def ended(self):
        return self.state == State.COMPLETE

    def action_start(self, type, source, index, target):
        self.manager.action_start(type, source, index, target)
        if type != BlockType.PLAY:
            self._action_stack += 1

    def action_end(self, type, source):
        self.manager.action_end(type, source)

        if self.ended:
            raise GameOver("The game has ended.")

        if type != BlockType.PLAY:
            self._action_stack -= 1

        if self.current_player:
            while self.current_player.opponent.choice:
                choice = self.current_player.opponent.choice
                card = self.random.choice(choice.cards)
                choice.choose(card)

        if not self._action_stack:
            self.log("Empty stack, refreshing auras and processing deaths")
            self.refresh_auras()
            self.process_reward()
            self.process_deaths()
            # Cataclysm — Shatter: if any Shattered halves are loose, merge any
            # that have become adjacent in hand back into the full card.
            if getattr(self, "_shatter_active", False):
                from .actions import process_shatter_recombine

                for player in self.players:
                    process_shatter_recombine(player)

    def action_block(
        self, source, actions, type, index=-1, target=None, event_args=None
    ):
        self.action_start(type, source, index, target)
        if actions:
            ret = self.queue_actions(source, actions, event_args)
        else:
            ret = []
        self.action_end(type, source)
        return ret

    def attack(self, source, target):
        type = BlockType.ATTACK
        actions = [Attack(source, target)]
        result = self.action_block(source, actions, type, target=target)
        if self.state != State.COMPLETE:
            self.manager.step(Step.MAIN_ACTION, Step.MAIN_END)
        return result

    def joust(self, source, challenger, defender, actions):
        type = BlockType.JOUST
        return self.action_block(
            source, actions, type, event_args=[challenger, defender]
        )

    def main_power(self, source, actions, target):
        type = BlockType.POWER
        return self.action_block(source, actions, type, target=target)

    def play_card(
        self,
        card: "PlayableCard",
        target: "Character",
        index: int,
        choose: "PlayableCard | str",
    ):
        type = BlockType.PLAY
        player = card.controller
        actions = [Play(card, target, index, choose)]
        return self.action_block(player, actions, type, index, target)

    def trade_card(self, card: "PlayableCard"):
        type = BlockType.TRADE
        actions = [Trade(card)]
        return self.action_block(card.controller, actions, type)

    def process_deaths(self):
        type = BlockType.DEATHS

        if any(card.dead for card in self.live_entities):
            self.action_start(type, self, 0, None)
            self.trigger(self, [Death(self.live_entities)], event_args=None)
            self.action_end(type, self)

    def process_reward(self):
        type = BlockType.TRIGGER

        finished_card = [card for card in self if card.is_card and card.finished]
        if finished_card:
            self.action_start(type, self, 0, None)
            self.trigger(self, [Reward(finished_card)], event_args=None)
            self.action_end(type, self)

    def trigger(self, source, actions, event_args):
        """
        Perform actions as a result of an event listener (TRIGGER)
        """
        type = BlockType.TRIGGER
        return self.action_block(source, actions, type, event_args=event_args)

    def cheat_action(self, source, actions):
        """
        Perform actions as if a card had just triggered them
        """
        return self.trigger(source, actions, event_args=None)

    def check_for_end_game(self):
        """
        Check if one or more player is currently losing.
        End the game if they are.
        """
        gameover = False
        for player in self.players:
            if player.playstate in (PlayState.CONCEDED, PlayState.DISCONNECTED):
                player.playstate = PlayState.LOSING
            if player.playstate == PlayState.LOSING:
                gameover = True

        if gameover:
            if self.players[0].playstate == self.players[1].playstate:
                for player in self.players:
                    player.playstate = PlayState.TIED
            else:
                for player in self.players:
                    if player.playstate == PlayState.LOSING:
                        player.playstate = PlayState.LOST
                    else:
                        player.playstate = PlayState.WON
            self.state = State.COMPLETE
            self.manager.step(self.next_step, Step.FINAL_WRAPUP)
            self.manager.step(self.next_step, Step.FINAL_GAMEOVER)
            self.manager.step(self.next_step)

    def queue_actions(self, source: Entity, actions: "list[Action]", event_args=None):
        """
        Queue a list of \a actions for processing from \a source.
        Triggers an aura refresh afterwards.
        """
        old_event_args = source.event_args
        source.event_args = event_args
        ret = self.trigger_actions(source, actions)
        source.event_args = old_event_args
        return ret

    def trigger_actions(self, source: Entity, actions: "list[Action]"):
        """
        Performs a list of `actions` from `source`.
        This should seldom be called directly - use `queue_actions` instead.
        """
        ret = []
        for action in actions:
            if isinstance(action, EventListener):
                # Queuing an EventListener registers it as a one-time event
                # This allows registering events from eg. play actions
                self.log("Registering event listener %r on %r", action, self)
                action.once = True
                # FIXME: Figure out a cleaner way to get the event listener target
                if source.type == CardType.SPELL:
                    listener = source.controller
                else:
                    listener = source
                listener._events.append(action)
            else:
                if not hasattr(action, "trigger"):
                    # Defensive: occasionally a card script's deathrattle
                    # / events list yields a raw function or other
                    # non-Action element (typically from a callable
                    # deathrattle returning a single item instead of a
                    # tuple). Skip rather than crash so the rest of the
                    # action queue still resolves.
                    self.log("Skipping non-Action %r in queue", action)
                    continue
                ret.append(action.trigger(source))
        return ret

    def pick_first_player(self):
        """
        Picks and returns first player, second player
        In the default implementation, the first player is always
        "Player 0". Use CoinRules to decide it randomly.
        """
        return self.players[0], self.players[1]

    def refresh_auras(self):
        refresh_queue = []
        for entity in self.entities:
            for script in entity.update_scripts:
                refresh_queue.append((entity, script))

        for hand in self.hands:
            for entity in hand.entities:
                for script in entity.data.scripts.Hand.update:
                    refresh_queue.append((entity, script))

        # Sort the refresh queue by refresh priority (used by eg. Lightspawn)
        refresh_queue.sort(key=lambda e: getattr(e[1], "priority", 50))
        for entity, action in refresh_queue:
            action.trigger(entity)

        buffs_to_destroy = []
        for buff in self.active_aura_buffs:
            if buff.tick < self.tick:
                buffs_to_destroy.append(buff)
        for buff in buffs_to_destroy:
            buff.remove()

        self.tick += 1

    def setup(self):
        self.log("Setting up game %r", self)
        self.state = State.RUNNING
        self.step = Step.BEGIN_DRAW
        self.zone = Zone.PLAY
        self.players[0].opponent = self.players[1]
        self.players[1].opponent = self.players[0]
        for player in self.players:
            player.zone = Zone.PLAY
            self.manager.new_entity(player)

        first, second = self.pick_first_player()
        self.player1 = first
        self.player1.first_player = True
        self.player2 = second
        self.player2.first_player = False

        for player in self.players:
            player.prepare_for_game()

        # The Great Dark Beyond — mark every card that started in a player's
        # deck or opening hand so "didn't start in your deck" effects
        # (Foreboding Flame, Archimonde) can tell generated cards apart.
        for player in self.players:
            for card in list(player.deck) + list(player.hand):
                card._started_in_deck = True

        if self.is_standard:
            self.skin = self.random.choice(standard_board_skins)
        else:
            self.skin = self.random.choice(list(BoardEnum))

        self.manager.start_game()

    def start(self):
        self.setup()
        self.queue_actions(self, [GameStart()])
        self.begin_turn(self.player1)

    def end_turn(self):
        for player in self.players:
            player.minions_killed_this_turn = 0
        return self.queue_actions(self, [EndTurn(self.current_player)])

    def _end_turn(self):
        self.log("%s ends turn %i", self.current_player, self.turn)
        self.manager.step(self.next_step, Step.MAIN_CLEANUP)
        self.current_player.temp_mana = 0
        self.end_turn_cleanup()

    def end_turn_cleanup(self):
        self.manager.step(self.next_step, Step.MAIN_NEXT)
        # March of the Lich King — reset the "died after your last turn"
        # window for the player whose turn just ended. Their Undead
        # death-window begins now and accumulates through the opponent's
        # turn + their own next turn (until their next OWN_TURN_END).
        self.current_player._undead_deaths_in_window = []
        # Festival of Legends — toggle the controller's Harmonic phase so
        # the next Harmonic spell they cast fires the alt branch.
        self.current_player._harmonic_phase_swapped = (
            not self.current_player._harmonic_phase_swapped
        )
        # Festival of Legends — Love Everlasting expiry. If the latch
        # never flipped this turn the player didn't cast a spell, so
        # the aura tears down (printed text: "Lasts until you don't
        # play a spell on your turn.").
        if (
            getattr(self.current_player, "_love_everlasting_active", False)
            and not getattr(
                self.current_player,
                "_love_everlasting_consumed_this_turn",
                False,
            )
        ):
            self.current_player._love_everlasting_active = False
        # Re-arm the per-turn latch for the next turn (consumed flag
        # resets so the FIRST spell next turn gets the discount).
        self.current_player._love_everlasting_consumed_this_turn = False
        # MotLK per-turn cost-substitution flags clear at OWN_TURN_END:
        # Glacial Advance (next spell -2), Anub'Rekhan (minions cost
        # armor), Blood Crusader (next paladin minion costs health),
        # Ghoulish Alchemist (next Concoction free).
        self.current_player._next_spell_cost_reduction = 0
        self.current_player.minions_cost_armor_this_turn = False
        self.current_player.next_paladin_minion_costs_health_this_turn = False
        self.current_player.next_concoction_costs_zero = False
        # MotLK — Silvermoon Arcanist: "Your spells can't target heroes
        # this turn" — one-turn marker, clear on own turn end.
        self.current_player.spells_cant_target_heroes_this_turn = False
        # The Great Dark Beyond — Libram of Divinity: a Libram cast while it
        # cost (0) returns to its caster's hand at the end of that turn (the
        # spell is in the graveyard by now; bounce it back if there's room).
        for card in list(getattr(self.current_player, "_librams_to_return", [])):
            if (
                card.zone == Zone.GRAVEYARD
                and len(self.current_player.hand) < self.current_player.max_hand_size
            ):
                card.zone = Zone.HAND
        self.current_player._librams_to_return = []
        # The Great Dark Beyond — Celestial Aura: tick down the 2-turn host
        # enchant on the caster's hero and tear it down when it expires.
        if self.current_player.hero:
            for buff in list(self.current_player.hero.buffs):
                if getattr(buff, "_celestial_turns_left", None) is not None:
                    buff._celestial_turns_left -= 1
                    if buff._celestial_turns_left <= 0:
                        buff.remove()
        # Throne of the Tides — Submerged Spacerock: cards added with the
        # discards-at-end-of-owner-turn marker are discarded now.
        for hand_card in list(self.current_player.hand):
            if getattr(hand_card, "discards_at_end_of_owner_turn", False):
                hand_card.discard()
        for character in self.current_player.characters.filter(frozen=True):
            if not character.num_attacks and not character.exhausted:
                self.log("Freeze fades from %r", character)
                character.frozen = False
        for buff in self.entities.filter(one_turn_effect=True):
            self.log("Ending One-Turn effect: %r", buff)
            buff.remove()
        for entity in self.hands:
            for buff in CardList(entity.entities).filter(one_turn_effect=True):
                self.log("Ending One-Turn effect: %r", buff)
                buff.remove()
        # Weapon enchantments live in weapon.buffs; Hero.entities yields the
        # weapon object but not its buffs, so one-turn effects buffed onto a
        # weapon (e.g. Barbed Thorn's EDR_525e1 Poisonous-this-turn) are not
        # reached by the sweeps above. Expire them explicitly.
        for player in self.players:
            if player.weapon:
                for buff in CardList(player.weapon.buffs).filter(one_turn_effect=True):
                    self.log("Ending One-Turn effect: %r", buff)
                    buff.remove()
        # Extra turn
        if self.next_players:
            next_player = self.next_players.pop(0)
        else:
            next_player = self.current_player.opponent
        self.begin_turn(next_player)

    def skip_turn(self):
        self.end_turn()
        self.end_turn()
        return self

    def begin_turn(self, player):
        ret = self.queue_actions(self, [BeginTurn(player)])
        self.manager.turn(player)
        return ret

    def _begin_turn(self, player: "Player"):
        self.manager.step(self.next_step, Step.MAIN_START)
        self.manager.step(self.next_step, Step.MAIN_ACTION)

        for p in self.players:
            p.cards_drawn_this_turn = 0

        player.turn_start = timegm(time.gmtime())
        player.last_turn = player.turn
        player.turns.append(self.turn)
        player.turn = self.turn
        # The Lost City of Un'Goro — Kindred: roll this turn's plays into
        # "last turn" so Kindred cards played this turn check the previous turn.
        player.races_played_last_turn = player.races_played_this_turn
        player.races_played_this_turn = set()
        player.schools_played_last_turn = player.schools_played_this_turn
        player.schools_played_this_turn = set()
        player.cards_played_this_turn = 0
        player.minions_played_this_turn = 0
        player.minions_killed_this_turn = 0
        player.healed_this_turn = 0
        player.combo = False
        player.max_mana += 1
        player.used_mana = 0
        player.overload_locked = player.overloaded
        player.overloaded = 0
        # Showdown in the Badlands — Azerite Giant streak. elemental_played_
        # this_turn still holds the count from this player's previous turn
        # (reset just below), so update the consecutive-turns streak here,
        # globally, regardless of where Azerite Giant currently sits.
        if player.elemental_played_this_turn > 0:
            player.azerite_elemental_streak += 1
        else:
            player.azerite_elemental_streak = 0
        player.elemental_played_last_turn = player.elemental_played_this_turn
        player.elemental_played_this_turn = 0
        player.spells_played_last_turn = player.spells_played_this_turn
        player.spells_played_this_turn = 0
        player.hero_health_changed_this_turn = 0
        # Reset accumulated opponent-turn-damage counter at start of own turn.
        player.damage_taken_on_opponents_turn = 0
        # Sunken City: per-turn flags reset at the start of own turn.
        player.spells_poisonous_this_turn = False
        player.spell_mana_spent_this_turn = 0
        # Whizbang mini-set — Holy Glowsticks (MIS_709) per-turn discount.
        player.holy_spells_cast_this_turn = 0
        # The Great Dark Beyond — Kil'jaeden: each of your turns, the portal's
        # Demons gain an additional +2/+2. Bump the running bonus (so freshly
        # conjured Demons catch up) and buff every portal Demon in deck + hand.
        if getattr(player, "_kiljaeden_active", False):
            player._kiljaeden_bonus += 2
            for card in list(player.deck) + list(player.hand):
                if getattr(card, "_kiljaeden_demon", False):
                    player.hero.buff(card, "GDB_145de", atk=2, max_health=2)
        # The Great Dark Beyond — adjacency: clear each hand card's per-turn
        # "an adjacent card was played" count.
        for hand_card in player.hand:
            hand_card.adjacent_plays_this_turn = 0
        # The Great Dark Beyond — Exarch Maladaar's "next card costs Corpses"
        # is a this-turn window; clear any unused charge.
        player.next_card_costs_corpses = 0
        # The Great Dark Beyond — Sha'tari Cloakfield first-spell discount is
        # re-armed each turn by the in-play sources via OWN_TURN_BEGIN, which
        # fires in BeginTurn.do BEFORE _begin_turn runs. So the reset lives
        # there (pre-broadcast); clearing it here would clobber the freshly
        # armed discount.
        # The Great Dark Beyond — per-turn Discover count (Parallax Cannon).
        player.discovers_this_turn = 0
        # The Great Dark Beyond — per-turn hero damage (Healthstone).
        player.hero_damage_taken_this_turn = 0
        # Heroes of StarCraft — Construct Pylons' "next Protoss card THIS TURN"
        # discount expires at the start of the player's next turn.
        player.next_protoss_card_discount = 0
        # Audiopocalypse — Ambient Lightspawn counter resets per turn.
        player.overheals_triggered_this_turn = 0
        # TITANS — Tar Slick: clear per-turn "minions take double damage" flag.
        player.minion_damage_doubled_this_turn = False
        # TITANS — Stoneskin Armorer: clear per-turn armor-gained counter.
        player.armor_gained_this_turn = 0
        # MotLK — Bonelord Frostwhisper: re-arm the "first card costs 0"
        # per-turn marker. Permanent flag stays set; only the consumed
        # latch resets.
        player._frostwhisper_consumed_this_turn = False
        # TITANS — Golganneth, the Thunderer: re-arm the per-turn "first
        # spell costs (3) less" latch. The permanent _golganneth_active
        # flag stays set; only the consumed latch resets each turn.
        if getattr(player, "_golganneth_active", False):
            player._golganneth_consumed_this_turn = False
        # Throne of the Tides: tick down per-player turn windows.
        if player.pays_health_for_cards_turns_left > 0:
            player.pays_health_for_cards_turns_left -= 1
        # Castle Nathria — tick the Location's cooldown down each turn.
        if player.location and player.location.cooldown > 0:
            player.location.cooldown -= 1
        # Caverns of Time — Disco at the End of Time: the Secrets it cast
        # are temporary ("At the start of your turn, destroy them"). They
        # persist through the opponent's turn (and may trigger), then are
        # destroyed at the start of the caster's next turn.
        if getattr(player, "_disco_active", False):
            for secret in list(player.secrets):
                if getattr(secret, "_disco_temp", False):
                    self.queue_actions(player.hero, [Destroy(secret)])
            player._disco_active = False
        # Maw and Disorder — Dew Process: while active on either player,
        # draw one extra card at the start of each turn (rest of game).
        if getattr(player, "dew_process_active", False):
            self.queue_actions(player.hero, [Draw(player)])
        # Maw and Disorder — Prosecutor Mel'tranix lockdown: tick down
        # the leftmost/rightmost-only constraint on turn begin so it
        # covers exactly the next opponent turn.
        if getattr(player, "_meltranix_lockdown_turns", 0) > 0:
            player._meltranix_lockdown_turns -= 1
        # Throne of the Tides per-card windows on the player's hand cards:
        # Coilfang's unplayable-next-turn marker and Immolate's burn timer.
        for hand_card in list(player.hand):
            if getattr(hand_card, "unplayable_next_turn", 0) > 0:
                hand_card.unplayable_next_turn -= 1
            if getattr(hand_card, "burn_turns_left", 0) > 0:
                hand_card.burn_turns_left -= 1
                if hand_card.burn_turns_left == 0:
                    self.queue_actions(hand_card, [Destroy(hand_card)])

        for entity in self.live_entities:
            if entity.type != CardType.PLAYER:
                entity.turns_in_play += 1

        for entity in player.live_entities:
            if getattr(entity, "dormant_turns", 0):
                entity.dormant_turns -= 1
                if entity.dormant_turns == 0:
                    self.queue_actions(player, [Awaken(entity)])

        # MotLK — Anachronos delayed-return scheduler. Each entry is
        # (turns_left, card_id, owner_id, atk, max_health). At the start
        # of the owner's turn, decrement turns_left; on hitting 0, summon
        # a fresh copy of the stashed minion and apply the snapshotted
        # buffed atk/health. Filters out matured entries in-place.
        scheduled = getattr(player, "_anachronos_returns", None)
        if scheduled:
            still_pending = []
            for entry in scheduled:
                turns_left = entry["turns_left"] - 1
                if turns_left <= 0:
                    cid = entry["id"]
                    self.queue_actions(player, [Summon(player, cid)])
                    # Apply atk/health snapshot if it diverged from base.
                    summoned = next(
                        (m for m in reversed(player.field) if m.id == cid),
                        None,
                    )
                    if summoned is not None:
                        if entry.get("atk") is not None and summoned.atk != entry["atk"]:
                            summoned.atk = entry["atk"]
                        if entry.get("max_health") is not None:
                            summoned.max_health = entry["max_health"]
                else:
                    entry["turns_left"] = turns_left
                    still_pending.append(entry)
            player._anachronos_returns = still_pending

        if player.hero.power:
            player.hero.power.activations_this_turn = 0
            player.hero.power.additional_activations_this_turn = 0

        for character in self.characters:
            character.num_attacks = 0
            character.damaged_this_turn = 0
            character.healed_this_turn = 0

        player.draw()
        self.manager.step(self.next_step, Step.MAIN_END)


class CoinRules(BaseGame):
    """
    Randomly determines the starting player when the Game starts.
    The second player gets "The Coin" (GAME_005).
    """

    def pick_first_player(self):
        winner = self.random.choice(self.players)
        self.log("Tossing the coin... %s wins!", winner)
        return winner, winner.opponent

    def begin_turn(self, player):
        if self.turn == 0:
            self.log("%s gets The Coin (%s)", self.player2, THE_COIN)
            self.player2.give(THE_COIN)
        super().begin_turn(player)


class MulliganRules(BaseGame):
    """
    Performs a Mulligan phase when the Game starts.
    Only begin the game after both Mulligans have been chosen.
    """

    def start(self):
        from .actions import MulliganChoice

        self.setup()
        self.next_step = Step.BEGIN_MULLIGAN
        self.log("Entering mulligan phase")
        self.step, self.next_step = self.next_step, Step.MAIN_READY

        for player in self.players:
            self.queue_actions(
                self, [MulliganChoice(player, callback=self.mulligan_done)]
            )

    def mulligan_done(self):
        self.queue_actions(self, [GameStart()])
        for player in self.players:
            player.starting_hand = CardList(player.hand[:])
            player.shuffle_deck()
        self.begin_turn(self.player1)


class Game(MulliganRules, CoinRules, BaseGame):
    pass
