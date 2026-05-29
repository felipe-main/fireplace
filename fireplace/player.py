from itertools import chain
from typing import TYPE_CHECKING

from hearthstone.enums import CardClass, CardType, GameTag, PlayState, SpellSchool, Zone

from .actions import Concede, Draw, Fatigue, Give, Hit, SpendMana, Steal, Summon
from .aura import TargetableByAuras
from .card import Card
from .deck import Deck
from .entity import Entity, slot_property, slot_buff_property
from .managers import PlayerManager
from .utils import CardList

if TYPE_CHECKING:
    from .card import (
        Character,
        Hero,
        Minion,
        PlayableCard,
        Spell,
        Quest,
        Secret,
        SideQuest,
        HeroPower,
    )
    from .game import Game


class Player(Entity, TargetableByAuras):
    Manager = PlayerManager
    all_targets_random = slot_property("all_targets_random")
    cant_overload = slot_buff_property("cant_overload")
    choose_both = slot_property("choose_both")
    extra_battlecries = slot_property("extra_battlecries")
    extra_trigger_secret = slot_property("extra_trigger_secret")
    minion_extra_battlecries = slot_property("minion_extra_battlecries")
    minion_extra_combos = slot_property("minion_extra_combos")
    extra_deathrattles = slot_property("extra_deathrattles")
    extra_end_turn_effect = slot_property("extra_end_turn_effect")
    healing_double = slot_property("healing_double", sum)
    hero_power_double = slot_property("hero_power_double", sum)
    healing_as_damage = slot_property("healing_as_damage")
    shadowform = slot_property("shadowform")
    spellpower_double = slot_property("spellpower_double", sum)
    spellpower_adjustment = slot_property("spellpower", sum)
    spellpower_arcane_adjustment = slot_property("spellpower_arcane", sum)
    spellpower_fire_adjustment = slot_property("spellpower_fire", sum)
    spellpower_frost_adjustment = slot_property("spellpower_frost", sum)
    spellpower_nature_adjustment = slot_property("spellpower_nature", sum)
    spellpower_holy_adjustment = slot_property("spellpower_holy", sum)
    spellpower_shadow_adjustment = slot_property("spellpower_shadow", sum)
    spellpower_fel_adjustment = slot_property("spellpower_fel", sum)
    spellpower_physical_adjustment = slot_property("spellpower_physical", sum)
    heropower_damage_adjustment = slot_property("heropower_damage", sum)
    spells_cost_health = slot_property("spells_cost_health")
    lifesteal_damages_opposing_hero = slot_property("lifesteal_damages_opposing_hero")
    spells_cast_twice = slot_property("spells_cast_twice")
    cant_trigger_deathrattle = slot_property("cant_trigger_deathrattle")
    type = CardType.PLAYER

    def __init__(self, name, deck: list[str], hero: str, is_standard=True):
        self.game: Game = None
        self.opponent: Player = None
        self.first_player: bool = False
        self.starting_deck = deck
        self.starting_hero = hero
        self.data = None
        self.name = name
        self.hero: Hero = None
        self.hero_power: HeroPower = None
        self.is_standard = is_standard
        super().__init__()
        self.deck = Deck()
        self.hand = CardList["PlayableCard"]()
        self.field = CardList["Minion"]()
        self.graveyard = CardList["PlayableCard"]()
        self.secrets = CardList["Secret | Quest | SideQuest"]()
        self.removed = CardList()
        self.choice = None
        self.max_hand_size = 10
        self.max_resources = 10
        self.max_deck_size = 60
        self.cant_draw = False
        self.cant_fatigue = False
        self.combo = False
        self.fatigue_counter = 0
        self.last_card_played = None
        self.overloaded = 0
        self.overload_locked = 0
        self.overloaded_this_game = 0
        self._max_mana = 0
        self._start_hand_size = 3
        self.playstate = PlayState.INVALID
        self.temp_mana = 0
        self.timeout = 75
        self.times_hero_power_used_this_game = 0
        self.used_mana = 0
        self.minions_killed_this_turn = 0
        self.minions_played_this_turn = 0
        self.weapon = None
        # Murder at Castle Nathria — sixth board slot for a Location card.
        # Holds at most one location at a time; playing a new one destroys
        # the previous occupant (see Location._set_zone).
        self.location = None
        self.zone = Zone.INVALID
        self.turn = None
        self.last_turn = None
        self.turns = []
        self.jade_golem = 1
        self.times_totem_summoned_this_game = 0
        self.elemental_played_this_turn = 0
        # Showdown in the Badlands — Azerite Giant: number of consecutive
        # *completed* turns on which this player has played an Elemental.
        # Maintained globally in game._begin_turn so it is correct even while
        # Azerite Giant is still in the deck (not yet in hand).
        self.azerite_elemental_streak = 0
        self.elemental_played_last_turn = 0
        self.cards_drawn_this_turn = 0
        self.cards_played_this_turn = 0
        self.cards_played_this_game = CardList()
        self.hero_power_damage_this_game = 0
        self.spent_mana_on_spells_this_game = 0
        self.healed_this_game = 0
        self.healed_this_turn = 0
        self.hero_health_changed_this_turn = 0
        self.cthun = None
        self.invoke_counter = 0
        self.spells_played_this_game = 0
        # Per-turn spell counts (mirrors elemental_played_*). last_turn rolls
        # over in game.begin_turn; used by Aftershocks (DEEP_010) for its
        # "Costs (2) less if you cast a spell last turn" discount.
        self.spells_played_this_turn = 0
        self.spells_played_last_turn = 0
        # Showdown in the Badlands — number of times this player has Excavated
        # this game. Drives the escalating treasure tier (Common -> Rare ->
        # Epic -> class Legendary for excavate classes, then cycles) and is
        # read by payoff cards (e.g. The Azerite Scorpion at 8 Excavates).
        self.excavates_this_game = 0
        # Per-game / per-turn counters introduced for Alterac Valley cards.
        self.num_hero_attacks_this_game = 0
        self.armor_gained_this_game = 0
        self.damage_taken_on_opponents_turn = 0
        # One-shot Hero Power modifiers — consumed on next HP use.
        self.next_hero_power_costs_zero = 0
        self.next_hero_power_freezes_target = 0
        # One-shot Choose One discount + last-Choose-One tracking.
        self.next_choose_one_discount = 0
        self.next_choose_one_combined = 0
        # Defensive default for RLK_527 Timewarden — its aura reads
        # _timewarden_turns_left via an Attr selector at each Dragon summon
        # event, which crashes on Players that never had Timewarden played.
        self._timewarden_turns_left = 0
        self.last_choose_one_parent_id = None
        self.last_choose_one_chosen_id = None
        # Per-school spell-cast history (SpellSchool → list of card-ids cast
        # this game). Populated by the CastSpell action.
        self.spells_cast_by_school = {}
        # Sunken City: actual mana spent on spells this game (Naga Giant,
        # Garden's Grace). Bumped from Play.do using the spell's paid cost.
        self.mana_spent_on_spells_this_game = 0
        self.mana_spent_on_holy_spells_this_game = 0
        # Sunken City: while True, the next damage dealt by your spells
        # also poisons the damaged minion (Urchin Spines, this-turn flag).
        self.spells_poisonous_this_turn = False
        # Sunken City: Dozing Kelpkeeper awakens after this much spell
        # mana has been spent while it's dormant on the board.
        self.spell_mana_spent_this_turn = 0
        # Throne of the Tides per-player one-shot / windowed effects.
        # Shattershambler: one-shot deathrattle discount + insta-die marker.
        self.next_deathrattle_discount = 0
        self.next_deathrattle_dies_on_play = 0
        # Clownfish: next N Murloc plays cost (2) less.
        self.next_n_murlocs_discount = 0
        # Commander Ulthok: opponent's cards cost Health instead of Mana for
        # this many of THEIR turns (decremented at their begin_turn).
        self.pays_health_for_cards_turns_left = 0
        # Castle Nathria — per-game count of friendly minions that have
        # died. Powers Sire Denathrius (every death adds +1 to the
        # battlecry damage). Bumped in Death.do; never reset.
        self.friendly_minions_died_this_game = 0
        # March of the Lich King — Death Knight Corpses. +1 per friendly
        # minion death; consumed by DK cards via Consume(n). Bumped in
        # Death.do alongside friendly_minions_died_this_game.
        self.corpses = 0
        # Per-game cumulative corpses GAINED (never decremented). Some
        # DK cards check lifetime corpses, not just current balance.
        self.corpses_gained_this_game = 0
        # Per-game cumulative corpses SPENT (never decremented). Festival
        # of Legends — Climactic Necrotic Explosion picks one of three
        # "improvement" buckets per corpse-spent threshold. Bumped by
        # SpendCorpses and by direct-decrement DK cards.
        self.corpses_spent_this_game = 0
        # March of the Lich King — precise "died after your last turn"
        # window. Tracks every friendly Undead minion that died since the
        # controller's last OWN_TURN_END. Reset at OWN_TURN_END, appended
        # in Death.do. Cards that read this: Nerubian Flyer, Bone Flinger,
        # Nerubian Vizier, Necrotic Mortician, Noxious Infiltrator,
        # Unliving Champion, Shadow Word: Undeath, High Cultist Basaleph,
        # Grave Digging. Stored as a list of Minion entities (cleared
        # references survive GC since they're in the graveyard too).
        self._undead_deaths_in_window = []
        # MotLK — Glacial Advance per-turn next-spell cost reduction.
        # Set by _ArmGlacialAdvance, consumed by pay_cost on the next
        # spell played, reset at OWN_TURN_END.
        self._next_spell_cost_reduction = 0
        # Audiopocalypse — Abyssal Bassist cost-mod reads this. Bumped
        # by Weapon._set_zone(Zone.PLAY) every time the player equips a
        # weapon; never resets per game.
        self.weapons_equipped_this_game = 0
        # Audiopocalypse — Ambient Lightspawn gate. Bumped in Heal.do
        # whenever a heal produces overheal (requested > actual); reset
        # at OWN_TURN_BEGIN in game.py begin_turn.
        self.overheals_triggered_this_turn = 0
        # TITANS — Ignis, Melted Maker synergy. Bumped in ForgeCard.do.
        # Counts Forge activations this game (never resets).
        self.cards_forged_this_game = 0
        # TITANS — Chained Guardian cost_mod. Bumped in _shuffle_one_plague
        # each time a Plague is shuffled into the opponent's deck.
        self.plagues_shuffled_into_enemy = 0
        # TITANS — Helya: when True, each Plague drawn is re-shuffled into deck.
        self._plagues_are_unending = False
        # TITANS — Starstrung Bow cost_mod. Bumped when a Secret triggers.
        self.secrets_triggered_this_game = 0
        # TITANS — Tar Slick: while True, minions take double damage this turn.
        # Set by the spell's play; cleared at OWN_TURN_END.
        self.minion_damage_doubled_this_turn = False
        # TITANS per-game minion-summon counters (bumped in Summon.do).
        # Astral Automaton (TTN_401) self-scaling, Earthen scaling for
        # Disciple of Amitus (TTN_856) + Stoneheart King (TTN_900),
        # Treant cost reduction for Cultivation (TTN_954).
        self.astral_automatons_summoned_this_game = 0
        self.earthens_summoned_this_game = 0
        self.treants_summoned_this_game = 0
        # TITANS per-turn / per-game damage & armor accumulators.
        # Imprisoned Horror (TTN_462) cost_mod reads damage_taken_on_own_turns_this_game.
        # Stoneskin Armorer (TTN_469) battlecry reads armor_gained_this_turn.
        self.damage_taken_on_own_turns_this_game = 0
        self.armor_gained_this_turn = 0
        # TITANS — The Primus Runes of Frost: next spell has Spell Damage +N.
        self.next_spell_spellpower = 0
        # TITANS — Aqua Archivist / Tram Operator one-shot cost discounts.
        # Consumed in Play.do when the next Elemental/Mech is played.
        self._next_elemental_discount = 0
        self._next_mech_cost_reduction = 0
        # MotLK per-turn cost-substitution flags. minions_cost_armor:
        # Anub'Rekhan. next_paladin_minion_costs_health: Blood Crusader.
        # next_concoction_costs_zero: Ghoulish Alchemist. All consumed
        # by pay_cost (player.py) and reset at OWN_TURN_END.
        self.minions_cost_armor_this_turn = False
        self.next_paladin_minion_costs_health_this_turn = False
        self.next_concoction_costs_zero = False
        # MotLK — Silvermoon Arcanist: one-turn marker, while True the
        # Spell.play() target picker filters heroes out. Set by the
        # battlecry, cleared at OWN_TURN_END.
        self.spells_cant_target_heroes_this_turn = False
        # MotLK — Bonelord Frostwhisper: once armed (deathrattle), the
        # *first* card the affected player plays each turn costs (0).
        # `_frostwhisper_first_card_free` is permanent (rest of game);
        # `_frostwhisper_consumed_this_turn` is reset to False at
        # OWN_TURN_BEGIN and flipped True by pay_cost on the first card.
        self._frostwhisper_first_card_free = False
        self._frostwhisper_consumed_this_turn = False
        # Festival of Legends — Harmonic spells ("Swaps each turn."). Each
        # Harmonic card reads this boolean at cast time: False = printed
        # base effect, True = the swapped alt effect. The flag toggles in
        # end_turn_cleanup so that the FIRST cast on the controller's next
        # turn fires the opposite branch of the one cast on the current
        # turn. (HS ships a 6-way rotation; we approximate as a binary
        # swap which still pins the "alternating effect" invariant the
        # tests assert.)
        self._harmonic_phase_swapped = False
        # Festival of Legends — Love Everlasting: "Your first spell each
        # turn costs (2) less. Lasts until you don't play a spell on
        # your turn." Two flags:
        #   _love_everlasting_active: rest-of-life aura armed by the
        #       spell's play.
        #   _love_everlasting_consumed_this_turn: first-spell latch
        #       (re-armed in begin_turn).
        # In OWN_TURN_END cleanup we tear down the aura if no spell
        # was consumed this turn (latch never flipped).
        self._love_everlasting_active = False
        self._love_everlasting_consumed_this_turn = False
        # MotLK — count of Outcast cards played from leftmost/rightmost
        # slot this game. Bumped in Play.do when card.has_outcast and
        # card.play_outcast. Read by Vengeful Walloper's cost_mod.
        self.outcasts_played_this_game = 0
        # MotLK — recursion guard for self-recasting effects (Vexallus,
        # Soul Barrage). Bumped when a re-cast trigger fires; checked
        # to skip cascading re-casts.
        self._recast_depth = 0
        # Castle Nathria — per-game count of Relic spells (DH) cast.
        # Each Relic reads it to scale its bonus ("Improve your future
        # Relics"). Bumped in Play.do when card.id is a known Relic.
        self.relics_played_this_game = 0
        # Castle Nathria — Relic Vault: charges that re-cast the next
        # Relic you play. Consumed one-per-Relic in Play.do; reset
        # OWN_TURN_END via Relic Vault's enchantment.
        self.next_relic_casts_twice = 0

    def dump(self):
        data = super().dump()
        # data["name"], data["avatar"] = self.name
        if self.hero:
            data["hero"] = self.hero.dump()
            if self.hero.power:
                data["heropower"] = self.hero.power.dump()
        if self.weapon:
            data["weapon"] = self.weapon.dump()
        if self.location:
            data["location"] = self.location.dump()
        data["deck"] = len(self.deck)
        data["fatigue_counter"] = self.fatigue_counter
        data["hand"] = [card.dump() for card in self.hand]
        data["field"] = [card.dump() for card in self.field]
        data["secrets"] = [card.dump() for card in self.secrets]
        if self.choice:
            choice = data["choice"] = {}
            choice["cards"] = [card.dump() for card in self.choice.cards]
            choice["max_count"] = self.choice.max_count
            choice["min_count"] = self.choice.min_count
        data["max_mana"] = self.max_mana
        data["mana"] = self.mana
        data["timeout"] = self.timeout
        data["playstate"] = int(self.playstate)
        return data

    def dump_hidden(self):
        data = super().dump()
        # data["name"], data["avatar"] = self.name
        if self.hero:
            data["hero"] = self.hero.dump()
            if self.hero.power:
                data["heropower"] = self.hero.power.dump()
        if self.weapon:
            data["weapon"] = self.weapon.dump()
        if self.location:
            data["location"] = self.location.dump()
        data["deck"] = len(self.deck)
        data["fatigue_counter"] = self.fatigue_counter
        data["hand"] = [card.dump_hidden() for card in self.hand]
        data["field"] = [card.dump() for card in self.field]
        data["secrets"] = [card.dump_hidden() for card in self.secrets]
        if self.choice:
            choice = data["choice"] = {}
            choice["cards"] = [card.dump_hidden() for card in self.choice.cards]
            choice["max_count"] = self.choice.max_count
            choice["min_count"] = self.choice.min_count
        data["max_mana"] = self.max_mana
        data["mana"] = self.mana
        data["timeout"] = self.timeout
        data["playstate"] = int(self.playstate)
        return data

    def __str__(self):
        return self.name

    def __repr__(self):
        return "%s(name=%r, hero=%r)" % (self.__class__.__name__, self.name, self.hero)

    @property
    def current_player(self):
        return self.game.current_player is self

    @property
    def controller(self):
        return self

    @property
    def mana(self):
        mana = (
            max(0, self.max_mana - self.used_mana - self.overload_locked)
            + self.temp_mana
        )
        return mana

    @property
    def max_mana(self):
        return self._max_mana

    @max_mana.setter
    def max_mana(self, amount):
        self._max_mana = min(self.max_resources, max(0, amount))
        self.log("%s is now at %i mana crystals", self, self._max_mana)

    @property
    def heropower_damage(self):
        aura_power = self.controller.heropower_damage_adjustment
        minion_power = sum(
            minion.heropower_damage for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_arcane(self):
        aura_power = self.controller.spellpower_arcane_adjustment
        minion_power = sum(
            minion.spellpower_arcane for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_fire(self):
        aura_power = self.controller.spellpower_fire_adjustment
        minion_power = sum(
            minion.spellpower_fire for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_frost(self):
        aura_power = self.controller.spellpower_frost_adjustment
        minion_power = sum(
            minion.spellpower_frost for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_nature(self):
        aura_power = self.controller.spellpower_nature_adjustment
        minion_power = sum(
            minion.spellpower_nature for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_holy(self):
        aura_power = self.controller.spellpower_holy_adjustment
        minion_power = sum(
            minion.spellpower_holy for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_shadow(self):
        aura_power = self.controller.spellpower_shadow_adjustment
        minion_power = sum(
            minion.spellpower_shadow for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_fel(self):
        aura_power = self.controller.spellpower_fel_adjustment
        minion_power = sum(
            minion.spellpower_fel for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower_physical(self):
        aura_power = self.controller.spellpower_physic_adjustment
        minion_power = sum(
            minion.spellpower_physic for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def spellpower(self):
        aura_power = self.controller.spellpower_adjustment
        minion_power = sum(
            minion.spellpower for minion in self.field.filter(dormant=False)
        )
        return aura_power + minion_power

    @property
    def start_hand_size(self):
        if not self.first_player:
            # Give the second player an extra card
            return self._start_hand_size + 1
        return self._start_hand_size

    @property
    def characters(self):
        return CardList(chain([self.hero] if self.hero else [], self.field))

    @property
    def entities(self):
        for entity in self.field:
            yield from entity.entities
        yield from self.secrets
        yield from self.buffs
        if self.hero:
            yield from self.hero.entities
        yield self

    @property
    def live_entities(self):
        yield from self.field
        if self.hero:
            yield self.hero
        if self.weapon:
            yield self.weapon
        if self.location:
            yield self.location

    @property
    def actionable_entities(self):
        yield from self.characters
        yield from self.hand
        if self.hero.power:
            yield self.hero.power

    @property
    def minion_slots(self):
        return max(0, self.game.MAX_MINIONS_ON_FIELD - len(self.field))

    def copy_cthun_buff(self, card):
        for buff in self.cthun.buffs:
            buff.source.buff(
                card,
                buff.id,
                atk=buff.atk,
                max_health=buff.max_health,
                taunt=getattr(buff, "taunt", False),
            )

    def card(self, id, source=None, parent=None, zone=Zone.SETASIDE):
        card = Card(id)
        card.controller = self
        card.zone = zone
        if source is not None:
            card.creator = source
        if parent is not None:
            card.parent_card = parent
        # C'THUN
        if self.cthun and id == self.cthun.id:
            self.copy_cthun_buff(card)
        self.game.manager.new_entity(card)
        return card

    def prepare_for_game(self):
        # Whizbang
        if self.starting_hero == "BOT_914h" or self.starting_deck == ["BOT_914"]:
            from .cards.boomsday.whizbang_decks import WHIZBANG_DECKS

            self.starting_hero, self.starting_deck = self.game.random.choice(
                WHIZBANG_DECKS
            )

        if self.starting_hero == "DAL_800h" or self.starting_deck == ["DAL_800"]:
            from .cards.dalaran.zayle_decks import ZAYLE_DECKS

            self.starting_hero, self.starting_deck = self.game.random.choice(
                ZAYLE_DECKS
            )

        self.starting_hero = self.card(self.starting_hero)

        if "SW_050" in self.starting_deck:
            # Maestra of the Masquerad
            # You start the game as a different class until you play a Rogue card.
            classes = [
                CardClass.DEATHKNIGHT,
                CardClass.DRUID,
                CardClass.HUNTER,
                CardClass.MAGE,
                CardClass.PALADIN,
                CardClass.PRIEST,
                # CardClass.ROGUE,
                CardClass.SHAMAN,
                CardClass.WARLOCK,
                CardClass.WARRIOR,
                CardClass.DEMONHUNTER,
            ]
            hero = self.game.random.choice(classes).default_hero
            self.summon(hero)
        else:
            self.summon(self.starting_hero)
        # self.game.trigger(self, [Summon(self, self.starting_hero)], event_args=None)
        # Castle Nathria — Prince Renathal: "Start of Game: Your deck size
        # and starting Health are 40." The deck-size cap is a deckbuilding
        # constraint we can't retro-apply, but the +10 starting HP and the
        # max_deck_size bump are observable in-game.
        if "REV_018" in self.starting_deck:
            self.max_deck_size = 40
            self.hero.max_health = 40
            self.hero.damage = 0
        for id in self.starting_deck:
            card = self.card(id, zone=Zone.DECK)
            # Castle Nathria — Steamcleaner reads this flag to destroy
            # only deck cards that were added after game start (i.e.
            # those whose _from_starting_deck is False).
            card._from_starting_deck = True
            if self.is_standard and not card.is_standard:
                self.is_standard = False
        self.starting_deck = CardList(self.deck[:])
        self.mulligan_shuffle_deck()
        self.cthun = self.card("OG_280")
        self.playstate = PlayState.PLAYING

        # Draw initial hand (but not any more than what we have in the deck)
        hand_size = min(len(self.deck), self.start_hand_size)
        # It's faster to move cards directly to the hand instead of drawing
        for _ in range(hand_size):
            self.deck[-1].zone = Zone.HAND

    def get_spell_damage(self, spell: "Spell", amount: int) -> int:
        """
        Returns the amount of damage \a amount will do, taking
        SPELLPOWER and SPELLPOWER_DOUBLE into account.
        """
        spell_school_power_map = {
            SpellSchool.ARCANE: self.spellpower_arcane,
            SpellSchool.FIRE: self.spellpower_fire,
            SpellSchool.FROST: self.spellpower_frost,
            SpellSchool.NATURE: self.spellpower_nature,
            SpellSchool.HOLY: self.spellpower_holy,
            SpellSchool.SHADOW: self.spellpower_shadow,
            SpellSchool.FEL: self.spellpower_fel,
        }
        if getattr(spell, "spell_school", SpellSchool.NONE) in spell_school_power_map:
            amount += spell_school_power_map[spell.spell_school]
        amount += self.spellpower
        # TITANS — The Primus Runes of Frost: next spell has Spell Damage +N.
        amount += self.next_spell_spellpower
        amount <<= self.controller.spellpower_double
        return amount

    def get_spell_heal(self, spell: "Spell", amount: int) -> int:
        """
        Returns the amount of heal \a amount will do, taking
        SPELLPOWER and SPELLPOWER_DOUBLE into account.
        """
        amount <<= self.controller.healing_double
        return amount

    def get_heropower_damage(self, heropower: "HeroPower", amount: int) -> int:
        amount += self.heropower_damage
        amount <<= self.controller.hero_power_double
        return amount

    def get_heropower_heal(self, heropower: "HeroPower", amount: int) -> int:
        amount <<= self.controller.hero_power_double
        return amount

    def discard_hand(self):
        self.log("%r discards their entire hand!", self)
        # iterate the list in reverse so we don't skip over cards in the process
        # yes it's stupid.
        for card in self.hand[::-1]:
            card.discard()

    def can_pay_cost(self, card):
        """
        Returns whether the player can pay the resource cost of a card.
        """
        if self.spells_cost_health and card.type == CardType.SPELL:
            return self.hero.health > card.cost
        if card.card_costs_health:
            return self.hero.health > card.cost
        # Throne of the Tides — Commander Ulthok: while this flag is up the
        # player pays Health for every card instead of Mana.
        if getattr(self, "pays_health_for_cards_turns_left", 0) > 0:
            return self.hero.health > card.cost
        return self.mana >= card.cost

    def pay_cost(self, source: Entity, amount: int) -> int:
        """
        Make player pay \a amount mana.
        Returns how much mana is spent, after temporary mana adjustments.
        """
        # MotLK — Bonelord Frostwhisper: while the doom-aura is armed on
        # this player, the first card they play each turn costs (0).
        # Applies to every card type (spell/minion/weapon/HP-via-card).
        if (
            getattr(self, "_frostwhisper_first_card_free", False)
            and not getattr(self, "_frostwhisper_consumed_this_turn", False)
        ):
            self._frostwhisper_consumed_this_turn = True
            self.log("%s plays %r for 0 (Bonelord Frostwhisper)", self, source)
            return 0
        # MotLK — Glacial Advance: "Your next spell this turn costs (2)
        # less." Single-use spell cost reduction (auto-cleared in
        # OWN_TURN_END cleanup via TAG_ONE_TURN_EFFECT on RLK_025e).
        if (
            source.type == CardType.SPELL
            and getattr(self, "_next_spell_cost_reduction", 0) > 0
        ):
            reduction = self._next_spell_cost_reduction
            self._next_spell_cost_reduction = 0
            amount = max(0, amount - reduction)
            self.log("%s spell %r pays %i (Glacial Advance -%i)",
                     self, source, amount, reduction)
        # Festival of Legends — Love Everlasting: "Your first spell each
        # turn costs (2) less." First spell each turn while the aura is
        # active gets -2 cost; consumes the per-turn latch so subsequent
        # spells pay full price.
        if (
            source.type == CardType.SPELL
            and getattr(self, "_love_everlasting_active", False)
            and not getattr(self, "_love_everlasting_consumed_this_turn", False)
        ):
            self._love_everlasting_consumed_this_turn = True
            amount = max(0, amount - 2)
            self.log("%s spell %r pays %i (Love Everlasting -2)",
                     self, source, amount)
        # TITANS — Golganneth, the Thunderer: "Your first spell each turn
        # costs (3) less." Mirrors Love Everlasting but for -3 and keyed
        # to _golganneth_active / _golganneth_consumed_this_turn.
        if (
            source.type == CardType.SPELL
            and getattr(self, "_golganneth_active", False)
            and not getattr(self, "_golganneth_consumed_this_turn", False)
        ):
            self._golganneth_consumed_this_turn = True
            amount = max(0, amount - 3)
            self.log("%s spell %r pays %i (Golganneth -3)",
                     self, source, amount)
        # MotLK — Ghoulish Alchemist: "Your next Concoction costs (0)."
        # Single-use Concoction cost zero (Concoctions are identified by
        # their token id range RLK_570t1..t5).
        if (
            getattr(self, "next_concoction_costs_zero", False)
            and getattr(source, "id", "") in (
                "RLK_570t1", "RLK_570t2", "RLK_570t3",
                "RLK_570t4", "RLK_570t5",
            )
        ):
            self.next_concoction_costs_zero = False
            self.log("%s Concoction %r is free (Ghoulish Alchemist)",
                     self, source)
            return 0
        # MotLK — Anub'Rekhan: "This turn, your minions cost Armor
        # instead of Mana." Pay from hero armor; if insufficient armor,
        # fall through to normal mana payment.
        if (
            getattr(self, "minions_cost_armor_this_turn", False)
            and source.type == CardType.MINION
        ):
            if self.hero.armor >= amount:
                self.hero.armor -= amount
                self.log("%s minion %r pays %i armor (Anub'Rekhan)",
                         self, source, amount)
                return amount
        # MotLK — Blood Crusader: "Your next Paladin minion this turn
        # costs Health instead of Mana." One-shot; consumed on the next
        # Paladin minion play. Saurfang's deathrattle uses the same
        # flag (its bounced copy is the "next minion" effectively).
        if (
            getattr(self, "next_paladin_minion_costs_health_this_turn", False)
            and source.type == CardType.MINION
            and (
                CardClass.PALADIN in getattr(source, "classes", [])
                or getattr(source, "card_class", None) == CardClass.PALADIN
            )
        ):
            self.next_paladin_minion_costs_health_this_turn = False
            self.log("%s minion %r pays %i health (Blood Crusader)",
                     self, source, amount)
            self.game.queue_actions(self, [Hit(self.hero, amount)])
            return amount
        if self.spells_cost_health and source.type == CardType.SPELL:
            self.log("%s spells cost %i health", self, amount)
            self.game.queue_actions(self, [Hit(self.hero, amount)])
            return amount
        if getattr(source, "card_costs_health", False):
            self.log("%s cards cost %i health", source, amount)
            self.game.queue_actions(self, [Hit(self.hero, amount)])
            return amount
        if getattr(self, "pays_health_for_cards_turns_left", 0) > 0:
            self.log("%s cards cost %i health (Ulthok)", source, amount)
            self.game.queue_actions(self, [Hit(self.hero, amount)])
            return amount
        if source.type == CardType.SPELL:
            self.spent_mana_on_spells_this_game += amount
        self.game.queue_actions(source, [SpendMana(self, amount)])
        return amount

    def mulligan_shuffle_deck(self):
        """
        Quest cards are automatically included in the player's mulligan as the left-most card
        CANT_DRAW_DURING_MULLIGAN cards never included in the player's mulligan card
        """

        def key_func(card):
            if card.tags.get(GameTag.QUEST):
                return 1, self.game.random.random()
            if card.tags.get(GameTag.CANT_DRAW_DURING_MULLIGAN):
                return -1, self.game.random.random()
            return 0, self.game.random.random()

        self.deck.sort(key=key_func)

    def shuffle_deck(self):
        self.log("%r shuffles their deck", self)
        self.game.random.shuffle(self.deck)

    def draw(self, count=1):
        if self.cant_draw:
            self.log("%s tries to draw %i cards, but can't draw", self, count)
            return None

        ret = self.game.cheat_action(self, [Draw(self) * count])[0]
        if count == 1:
            if not ret[0]:  # fatigue
                return None
            return ret[0][0]
        return ret

    def give(self, id: str) -> "PlayableCard":
        cards = self.game.cheat_action(self, [Give(self, id)])[0][0]
        if len(cards) > 0:
            return cards[0]

    def concede(self):
        ret = self.game.cheat_action(self, [Concede(self)])
        return ret

    def fatigue(self):
        return self.game.cheat_action(self, [Fatigue(self)])[0]

    def steal(self, card):
        return self.game.cheat_action(self, [Steal(card)])

    def summon(self, card) -> "PlayableCard":
        """
        Puts \a card in the PLAY zone
        """
        if isinstance(card, str):
            card = self.card(card)
        self.game.cheat_action(self, [Summon(self, card)])
        return card
