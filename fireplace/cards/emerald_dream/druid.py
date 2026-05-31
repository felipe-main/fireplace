from ..utils import *

from hearthstone.enums import CardClass, CardType, GameTag, SpellSchool


##
# Custom actions / helpers


def _all_deck_spells_nature(player):
    """True iff every spell in *player*'s starting deck is a Nature spell. A
    deck with no spells trivially satisfies "each spell is Nature"."""

    for card in player.starting_deck:
        if card.type != CardType.SPELL:
            continue
        school = getattr(card, "spell_school", None)
        if school is None or int(school) != int(SpellSchool.NATURE):
            return False
    return True


class _HamuulStartOfGame(TargetedAction):
    """Hamuul Runetotem — Start of Game: if each spell in your deck is Nature,
    Imbue your Hero Power, and arm the every-2-spells repeat."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        if _all_deck_spells_nature(player):
            player._hamuul_armed = True
            source.game.cheat_action(source, [Imbue(player)])


class _HamuulSpellCast(TargetedAction):
    """Hamuul Runetotem — repeat the Imbue every 2 spells you cast (only when
    the start-of-game all-Nature condition held)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        if not getattr(player, "_hamuul_armed", False):
            return
        player._hamuul_spell_counter = getattr(player, "_hamuul_spell_counter", 0) + 1
        if player._hamuul_spell_counter % 2 == 0:
            source.game.cheat_action(source, [Imbue(player)])


class _NextHeroPowerFree(TargetedAction):
    """Dreambound Disciple — your next Hero Power costs (0)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.next_hero_power_costs_zero += 1


class _PresentDiscover(TargetedAction):
    """Present a fixed list of cards as a Discover, then give the chosen one and
    reduce its Cost by (1) (Symbiosis)."""

    TARGET = ActionArg()
    CARDS = ActionArg()

    def do(self, source, target, cards):
        disc = Discover(CONTROLLER, RandomCard())
        disc.player = target
        disc.source = source
        disc.target = target
        disc.cards = cards
        disc.min_count = 1
        disc.max_count = 1
        disc._callback = []
        disc.callback = []

        def _on_choose(card):
            target.choice = None
            target.discovers_this_game += 1
            target.discovers_this_turn += 1
            source.game.cheat_action(
                source,
                [Give(target, card.id).then(Buff(Give.CARD, "EDR_273e"))],
            )

        disc.choose = _on_choose
        target.choice = disc


class _SymbiosisDiscover(TargetedAction):
    """Symbiosis — Discover a Choose One card from another class. It costs (1)
    less. The pool (Choose One collectibles whose class is neither Druid nor
    Neutral) isn't expressible as a plain RandomCardPicker filter, so build it
    here and present it as a Discover choice."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        ctrl = source.controller
        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.tags.get(GameTag.CHOOSE_ONE, 0)
            and CardClass.DRUID not in (getattr(c, "classes", None) or [c.card_class])
            and CardClass.NEUTRAL not in (getattr(c, "classes", None) or [c.card_class])
        ]
        if not pool:
            return
        rng = source.game.random
        rng.shuffle(pool)
        cards = [ctrl.card(cid, source=source) for cid in pool[:3]]
        source.game.cheat_action(source, [_PresentDiscover(ctrl, cards)])


class _ReforestationDoBoth(TargetedAction):
    """Reforestation — count turns held in hand; once held the required number
    of turns, arm the controller's combined-Choose-One flag so the next play of
    this card does BOTH halves (engine's ChooseBoth path), and stop counting."""

    TARGET = ActionArg()

    def do(self, source, target):
        held = getattr(target, "_reforest_turns_held", 0) + 1
        target._reforest_turns_held = held
        if held >= 3 and not getattr(target, "_reforest_both_armed", False):
            target._reforest_both_armed = True
            target.controller.next_choose_one_combined += 1


class _GroveShaperSummon(TargetedAction):
    """Grove Shaper — summon the Treant token and stamp the cast spell's id on
    it so its deathrattle can re-create a copy of that exact spell."""

    TARGET = ActionArg()
    SPELL = ActionArg()

    def do(self, source, target, spell):
        if isinstance(spell, (list, tuple)):
            spell = spell[0] if spell else None
        if spell is None:
            return
        ctrl = source.controller
        treant = ctrl.card("EDR_271t", source=source)
        treant._copied_spell_id = spell.id
        source.game.cheat_action(source, [Summon(ctrl, treant)])


class _TreantGiveSpell(TargetedAction):
    """Treant of Life — Deathrattle: add a copy of the stored spell to hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        spell_id = getattr(target, "_copied_spell_id", None)
        if spell_id is None:
            return
        source.game.cheat_action(source, [Give(target.controller, spell_id)])


##
# Spells


class EDR_060:
    """Ward of Earth"""

    # Gain 5 Armor. Summon a random 5-Cost minion and give it Taunt.
    play = (
        GainArmor(FRIENDLY_HERO, 5),
        Summon(CONTROLLER, RandomMinion(cost=5)).then(
            SetTags(Summon.CARD, {GameTag.TAUNT: True})
        ),
    )


class EDR_270:
    """Horn of Plenty"""

    # Discover a Nature spell. It costs (2) less.
    play = Discover(CONTROLLER, RandomSpell(spell_school=SpellSchool.NATURE)).then(
        Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "EDR_270e"))
    )


class EDR_273:
    """Symbiosis"""

    # Discover a Choose One card from another class. It costs (1) less.
    play = _SymbiosisDiscover(SELF)


class EDR_843:
    """Reforestation"""

    # Choose One - Draw a spell; or Draw a minion.
    # (Hold this for 3 turns to do both!)
    # The Hand event below arms next_choose_one_combined once held 3 turns, so
    # the engine's ChooseBoth path runs BOTH halves on the next play.
    choose = ("EDR_843a", "EDR_843b")
    play = ChooseBoth(CONTROLLER) & (
        ForceDraw(RANDOM(FRIENDLY_DECK + SPELL)),
        ForceDraw(RANDOM(FRIENDLY_DECK + MINION)),
    )

    class Hand:
        events = OWN_TURN_BEGIN.on(_ReforestationDoBoth(SELF))


class EDR_843a:
    """Aid of the Forest"""

    # Draw a spell.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + SPELL))


class EDR_843b:
    """Fertilize"""

    # Draw a minion.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION))


class EDR_848:
    """Photosynthesis"""

    # Restore #6 Health. Get 3 random Druid spells.
    play = (
        Heal(FRIENDLY_HERO, 6),
        Give(CONTROLLER, RandomSpell(card_class=CardClass.DRUID)) * 3,
    )


##
# Minions


class EDR_209:
    """Forest Lord Cenarius"""

    # Choose Thrice - Give your other minions +1/+3; or Summon a 5/5 Ancient
    # with Taunt. (With only two options and three picks, the same option can
    # be chosen multiple times.)
    class CenariusChoice(MultipleChoice):
        PLAYER = ActionArg()
        choose_times = 3
        options = ("EDR_209a", "EDR_209b")

        def do_step1(self):
            self.cards = [self.player.card(c) for c in self.options]

        def do_step2(self):
            self.cards = [self.player.card(c) for c in self.options]

        def do_step3(self):
            self.cards = [self.player.card(c) for c in self.options]

        def done(self):
            # Resolve each pick with Cenarius as the source so "your OTHER
            # minions" correctly excludes Cenarius himself.
            cenarius = self.source
            for chosen in self.choosed_cards:
                if chosen.id == self.options[0]:
                    # Cenarius is the source here, so SELF == Cenarius and
                    # "FRIENDLY_MINIONS - SELF" is "your OTHER minions".
                    action = Buff(FRIENDLY_MINIONS - SELF, "EDR_209e2")
                else:
                    action = Summon(CONTROLLER, "EDR_209t5")
                cenarius.game.cheat_action(cenarius, [action])

    play = CenariusChoice(CONTROLLER)


class EDR_209a:
    """Growth of Dreams"""

    # Give your other minions +1/+3.
    play = Buff(FRIENDLY_MINIONS - SELF, "EDR_209e2")


class EDR_209b:
    """Ancients of the Dream"""

    # Summon a 5/5 Ancient with Taunt.
    play = Summon(CONTROLLER, "EDR_209t5")


class EDR_271:
    """Grove Shaper"""

    # After you cast a Nature spell, summon a 2/2 Treant with
    # "Deathrattle: Get a copy of that spell."
    # NOTE: use the ON phase (not AFTER). When the cast Nature spell itself
    # opens a Discover/choice (e.g. Horn of Plenty, EDR_270), the play action
    # suspends the action queue to wait for the choice, and the AFTER-phase
    # broadcast never runs — so the Treant was silently skipped. The ON-phase
    # broadcast fires inside the same action block before the queue suspends,
    # matching the printed "After you cast a Nature spell" for every Nature
    # spell including the Discover ones.
    events = Play(CONTROLLER, NATURE_SPELL).on(_GroveShaperSummon(SELF, Play.CARD))


class EDR_271t:
    """Treant of Life"""

    # Deathrattle: Get a copy of the Nature spell that summoned this. The data
    # token carries its deathrattle text on an unmapped tag, so set the
    # DEATHRATTLE flag explicitly to register the scripted deathrattle.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _TreantGiveSpell(SELF)


class EDR_272:
    """Evergreen Stag"""

    # Elusive, Lifesteal, Taunt. Lifesteal + Taunt live in data; restore Elusive
    # via the legacy split flags targeting honors (the data's ELUSIVE tag is on
    # an id python-hearthstone doesn't map to targeting).
    tags = {
        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }


class EDR_845:
    """Hamuul Runetotem"""

    # Start of Game: If each spell in your deck is Nature, Imbue your Hero
    # Power. Repeat this every 2 spells you cast.
    # The start-of-game effect arms a persistent player-side counter, so the
    # "every 2 spells" repeat must fire wherever Hamuul is (deck, hand, or
    # play) — register the spell-cast trigger in all three scopes.
    class Deck:
        events = (
            GameStart().on(_HamuulStartOfGame(SELF)),
            OWN_SPELL_PLAY.on(_HamuulSpellCast(SELF)),
        )

    class Hand:
        events = (
            GameStart().on(_HamuulStartOfGame(SELF)),
            OWN_SPELL_PLAY.on(_HamuulSpellCast(SELF)),
        )

    events = OWN_SPELL_PLAY.on(_HamuulSpellCast(SELF))


class EDR_847:
    """Dreambound Disciple"""

    # Battlecry and Deathrattle: Your next Hero Power costs (0).
    play = _NextHeroPowerFree(SELF)
    deathrattle = _NextHeroPowerFree(SELF)


##
# Tokens


class EDR_209t5:
    """Ancient"""

    # 5/5 Taunt. Stats + Taunt live in data.


##
# Enchantments


class EDR_209e2:
    # Guidance of the Forest — +1/+3.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 3}


@custom_card
class EDR_270e:
    # Horn of Plenty — discovered Nature spell costs (2) less.
    tags = {
        GameTag.CARDNAME: "Horn of Plenty",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


@custom_card
class EDR_273e:
    # Symbiosis — discovered Choose One card costs (1) less.
    tags = {
        GameTag.CARDNAME: "Symbiosis",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


##
# Emerald Dream mini-set (Firelands, FIR_) — DRUID
#
# Custom actions for the FIR_ trio.


class _OverheatDiscard(TargetedAction):
    """Overheat (FIR_906) — discard a random Nature spell from hand; only if one
    was actually discarded, give your minions +1/+1 MORE (a second FIR_906e).
    The extra buff is conditional on a Nature spell existing, so it must run
    after the discard resolves — hence a custom action, not a flat tuple."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        nature_spells = [
            c
            for c in player.hand
            if c.type == CardType.SPELL
            and c.spell_school is not None
            and int(c.spell_school) == int(SpellSchool.NATURE)
        ]
        if not nature_spells:
            return
        victim = source.game.random.choice(nature_spells)
        source.game.cheat_action(
            source,
            [Discard(victim), Buff(FRIENDLY_MINIONS, "FIR_906e")],
        )


class _CharredChameleonBattlecry(TargetedAction):
    """Charred Chameleon (FIR_908) — Battlecry: if the controller has used their
    Hero Power this turn, give the chosen friendly minion +1/+2 and Rush.

    "Used your Hero Power this turn" is read from the Hero Power card's per-turn
    `activations_this_turn` counter (bumped in HeroPower.do, reset each turn).
    FIR_908e3 in data carries only visual tags, so the +1/+2 comes from the
    locally-declared FIR_908e3 stat enchant; Rush is granted via SetTags."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        hp = player.hero_power
        if hp is None or hp.activations_this_turn <= 0:
            return
        if isinstance(target, (list, tuple)):
            target = target[0] if target else None
        if target is None:
            return
        source.game.cheat_action(
            source,
            [Buff(target, "FIR_908e3"), SetTags(target, {GameTag.RUSH: True})],
        )


class _AmirdrassilUse(TargetedAction):
    """Amirdrassil (FIR_907) — location activate. Each use is one level higher
    than the last ("Improves each use!"): level N summons a random N-Cost
    minion, gains N Armor, draws N cards, and refreshes N Mana Crystals. The
    per-use level counter lives on the location card (`_amir_uses`), starting at
    1 on the first use.

    NOTE: the printed @ values are server-resolved (not in CardXML). Modelled as
    level = number-of-times-used. Flagged as a best-fidelity approximation."""

    TARGET = ActionArg()

    def do(self, source, target):
        location = source
        level = getattr(location, "_amir_uses", 0) + 1
        location._amir_uses = level
        player = location.controller
        source.game.cheat_action(
            location,
            [
                Summon(player, RandomMinion(cost=level)),
                GainArmor(player.hero, level),
                Draw(player) * level,
                ManaThisTurn(player, level),
            ],
        )


##
# Spells


class FIR_906:
    """Overheat"""

    # Give your minions +1/+1. Discard a random Nature spell to give them
    # +1/+1 more.
    play = (
        Buff(FRIENDLY_MINIONS, "FIR_906e"),
        _OverheatDiscard(SELF),
    )


##
# Locations


class FIR_907:
    """Amirdrassil"""

    # Summon a @-Cost minion. Gain @ Armor. Draw @ card(s). Refresh @ Mana
    # Crystal. (Improves each use!)
    activate = _AmirdrassilUse(SELF)


##
# Minions


class FIR_908:
    """Charred Chameleon"""

    # Battlecry: If you've used your Hero Power this turn, give a friendly
    # minion +1/+2 and Rush.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    play = _CharredChameleonBattlecry(TARGET)


##
# FIR_ enchantments
#
# FIR_906e and FIR_908e3 exist in data but carry only visual tags (no
# ATK/HEALTH), so declare them with explicit stat tags — the merge code grafts
# these onto the data cards (no @custom_card needed for in-data enchants).


class FIR_906e:
    # Overheated — +1/+1 (applied once or twice by Overheat).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class FIR_908e3:
    # Spreading Flames — +1/+2.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}
