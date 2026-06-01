from ..utils import *

from hearthstone.enums import CardClass, GameTag, Race, Rarity

from ..delve_into_deepholm._bonus import roll_bonus_effects


##
# Custom actions


class _SummonShadesWithBonuses(TargetedAction):
    """Shadows of Yesterday - summon four 3/2 Anomalous Shades (TIME_610t2),
    each independently rolling TWO random Bonus Effects from the keyword-only
    pool (Taunt, Windfury, Divine Shield, Poisonous, Elusive, Rush, Lifesteal,
    Reborn). SetTags per shade so DIVINE_SHIELD / REBORN / untargetable tags
    take effect as direct instance state (a tag-only Buff would never apply)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(4):
            if len(ctrl.field) >= 7:
                break
            source.game.cheat_action(source, [Summon(ctrl, "TIME_610t2")])
            shade = ctrl.field[-1] if ctrl.field else None
            if shade is None or shade.id != "TIME_610t2":
                continue
            tags = roll_bonus_effects(source.game.random, 2)
            source.game.cheat_action(source, [SetTags(shade, tags)])


class _ResurrectHighestUndead(TargetedAction):
    """Memoriam Manifest - summon the highest-Cost friendly Undead minion that
    died this game. Scans the controller's graveyard for Undead minions, picks
    the one with the greatest base Cost (ties -> most recently dead), and
    summons a fresh copy."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        best = None
        best_cost = -1
        for card in ctrl.graveyard:
            if card.type != CardType.MINION:
                continue
            is_undead = card.race == Race.UNDEAD or Race.UNDEAD in getattr(
                card, "races", []
            )
            if not is_undead:
                continue
            cost = card.data.cost or 0
            if cost >= best_cost:
                best_cost = cost
                best = card
        if best is not None and len(ctrl.field) < 7:
            source.game.cheat_action(source, [Summon(ctrl, best.id)])


class _FillUndeadCostHealth(TargetedAction):
    """Forgotten Millennium - fill the controller's hand with random Undead
    minions. Each is stamped with TIME_615e ("Forgotten"), a one-turn-effect
    enchant carrying CARD_COSTS_HEALTH so the card pays Health instead of Mana
    this turn (the enchant self-destroys at the controller's turn end)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        guard = 0
        while len(ctrl.hand) < ctrl.max_hand_size and guard < 20:
            guard += 1
            before = len(ctrl.hand)
            source.game.cheat_action(
                source, [Give(ctrl, RandomMinion(race=Race.UNDEAD))]
            )
            if len(ctrl.hand) <= before:
                break
            card = ctrl.hand[-1]
            source.game.cheat_action(source, [Buff(card, "TIME_615e")])


class _ChronochillerSkipDraw(TargetedAction):
    """Chronochiller - at the start of the controller's turn, suppress that
    turn's start-of-turn draw. OWN_TURN_BEGIN fires (in BeginTurn.do) BEFORE
    _begin_turn performs player.draw(), so setting cant_draw here blocks the
    draw, and OWN_TURN_END restores it.

    Approximation: this blocks every draw the controller makes between their
    turn-begin and turn-end while Chronochiller is in play, not only the
    start-of-turn draw. In practice the routine draw in that window is the
    start-of-turn draw this card is meant to cancel."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.cant_draw = True


class _ChronochillerRestoreDraw(TargetedAction):
    """Chronochiller - clear the draw suppression at the controller's turn end."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.cant_draw = False


class _HuskHeroDeathrattle(TargetedAction):
    """Husk, Eternal Reaper - the hero deathrattle granted by TIME_618e.
    Spend up to 20 Corpses; the spent amount is the Health the hero would
    resurrect with. Reviving a dead hero is not expressible with available
    primitives, so this approximates by spending the Corpses."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = getattr(target, "controller", None) or source.controller
        spend = min(20, ctrl.corpses)
        if spend > 0:
            source.game.cheat_action(source, [SpendCorpses(ctrl, spend)])


# Boon token id -> keyword GameTag granted to Bwonsamdi.
_BOON_TAGS = {
    "TIME_619t3": GameTag.TAUNT,      # Boon of Power
    "TIME_619t4": GameTag.LIFESTEAL,  # Boon of Longevity
    "TIME_619t5": GameTag.RUSH,       # Boon of Speed
}


def _apply_boon(game, ctrl, source, boon_tag):
    """Grant `boon_tag` permanently to every friendly Bwonsamdi (in play, hand,
    or deck) and bump his Deathrattle-summon cost surcharge by (2)."""
    for zone in (ctrl.field, ctrl.hand, ctrl.deck):
        for card in list(zone):
            if card.id == "TIME_619t":
                game.cheat_action(source, [SetTags(card, {boon_tag: True})])
                card._bwonsamdi_boon_cost = (
                    getattr(card, "_bwonsamdi_boon_cost", 0) + 2
                )


class _ApplyBoon(TargetedAction):
    """Apply a Boon keyword permanently to every friendly Bwonsamdi (in hand,
    deck, or play). BOON_TAG names the keyword GameTag to grant. Used as the
    `play` of the Boon token spells when they are cast directly (not via the
    Talanji / Zandalar choice, which applies the boon on selection)."""

    TARGET = ActionArg()
    BOON_TAG = ActionArg()

    def get_target_args(self, source, target):
        return [self._args[1]]

    def do(self, source, target, boon_tag):
        _apply_boon(source.game, source.controller, source, boon_tag)


class _BoonChoiceAction(Choice):
    """Custom Choice — offer the Power / Longevity / Speed Boon tokens and apply
    the chosen Boon to Bwonsamdi immediately on selection (GenericChoice would
    only move the token to hand, leaving its effect uncast). All three tokens
    are discarded after the pick."""

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid choice (one of %r)" % (card, self.cards)
            )
        self.player.choice = None
        ctrl = self.player
        boon_tag = _BOON_TAGS.get(card.id)
        if boon_tag is not None:
            _apply_boon(ctrl.game, ctrl, self.source, boon_tag)
        for token in self.cards:
            token.discard()


class _BoonChoice(TargetedAction):
    """Offer the Power / Longevity / Speed Boon choice. Shared by Talanji's
    battlecry and What Befell Zandalar."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        boons = [
            ctrl.card("TIME_619t3", source=source),
            ctrl.card("TIME_619t4", source=source),
            ctrl.card("TIME_619t5", source=source),
        ]
        choice = _BoonChoiceAction(ctrl, boons)
        choice.source = source
        source.game.queue_actions(source, [choice])


class _TalanjiDrawBwonsamdi(TargetedAction):
    """Talanji of the Graves - draw Bwonsamdi (TIME_619t) from the deck, or if
    none is in the deck, get a fresh copy in hand (the "resurrect him if he has
    died" clause - a dead Bwonsamdi is in the graveyard, not the deck, so we
    create a new copy). Then offer the controller a Boon to give him."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        in_deck = next((c for c in ctrl.deck if c.id == "TIME_619t"), None)
        if in_deck is not None:
            source.game.cheat_action(source, [Draw(ctrl, in_deck)])
        else:
            source.game.cheat_action(source, [Give(ctrl, "TIME_619t")])
        source.game.cheat_action(source, [_BoonChoice(ctrl)])


##
# Spells


class TIME_610:
    """Shadows of Yesterday"""

    # Rewind. Summon four 3/2 Shades. They each gain two random Bonus Effects.
    play = _SummonShadesWithBonuses(CONTROLLER)


class TIME_611:
    """Timestop"""

    # Deal $3 damage. Freeze two random enemy minions.
    play = (
        Hit(RANDOM(ENEMY_MINIONS), 3),
        Freeze(RANDOM(ENEMY_MINIONS) * 2),
    )


class TIME_612:
    """Blood Draw"""

    # Discover a spell. This costs Health instead of Mana.
    card_costs_health = True
    play = DISCOVER(RandomSpell(card_class=CardClass.DEATHKNIGHT))


class TIME_615:
    """Forgotten Millennium"""

    # Fill your hand with random Undead. They cost Health instead of Mana
    # this turn.
    play = _FillUndeadCostHealth(CONTROLLER)


class TIME_616:
    """Memoriam Manifest"""

    # Summon the highest Cost friendly Undead that died this game.
    play = _ResurrectHighestUndead(CONTROLLER)


##
# Minions


class TIME_613:
    """Cryofrozen Champion"""

    # Deathrattle: Get a random Legendary minion. Reduce its Cost by (1).
    deathrattle = Give(CONTROLLER, RandomLegendaryMinion()).then(
        Buff(Give.CARD, "TIME_613e")
    )



class TIME_614:
    """Liferender"""

    # Battlecry: If your hero's Health changed this turn, deal 6 damage to an
    # enemy minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = (Attr(CONTROLLER, "hero_health_changed_this_turn") >= 1) & Hit(TARGET, 6)


class TIME_617:
    """Chronochiller"""

    # You no longer draw a card at the start of your turn.
    events = (
        OWN_TURN_BEGIN.on(_ChronochillerSkipDraw(CONTROLLER)),
        OWN_TURN_END.on(_ChronochillerRestoreDraw(CONTROLLER)),
    )


class TIME_618:
    """Husk, Eternal Reaper"""

    # Battlecry: Give your hero "Deathrattle: Spend up to 20 Corpses to
    # resurrect with that much Health."
    play = Buff(FRIENDLY_HERO, "TIME_618e")


class TIME_619:
    """Talanji of the Graves"""

    # Fabled. Battlecry: Draw Bwonsamdi (or resurrect him if he has died).
    # Choose a Boon to give him.
    play = _TalanjiDrawBwonsamdi(CONTROLLER)


##
# Tokens


class TIME_610t2:
    """Anomalous Shade"""

    # Vanilla 3/2 Undead token (stats + race live in data).


class TIME_619t:
    """Bwonsamdi"""

    # Deathrattle: Summon a random 4-Cost minion. (Cost = 4 in data.)
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=4))


class TIME_619t2:
    """What Befell Zandalar"""

    # Deal 2 damage to all enemies. Choose a Boon to give to Bwonsamdi.
    play = (
        Hit(ENEMY_CHARACTERS, 2),
        _BoonChoice(CONTROLLER),
    )


class TIME_619t3:
    """Boon of Power"""

    # Give Bwonsamdi Taunt permanently. Minions summoned by his Deathrattle
    # cost (2) more.
    play = _ApplyBoon(CONTROLLER, GameTag.TAUNT)


class TIME_619t4:
    """Boon of Longevity"""

    # Give Bwonsamdi Lifesteal permanently. Minions summoned by his Deathrattle
    # cost (2) more.
    play = _ApplyBoon(CONTROLLER, GameTag.LIFESTEAL)


class TIME_619t5:
    """Boon of Speed"""

    # Give Bwonsamdi Rush permanently. Minions summoned by his Deathrattle
    # cost (2) more.
    play = _ApplyBoon(CONTROLLER, GameTag.RUSH)


##
# Enchantments


@custom_card
class TIME_613e:
    # Cryofrozen Champion - the fetched Legendary costs (1) less. Not in data;
    # register a name + COST tag (engine clamps the cost floor to 0).
    tags = {
        GameTag.CARDNAME: "Frozen Solid",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class TIME_615e:
    """Forgotten"""

    # Costs Health instead of Mana (this turn). Enchant exists in data with
    # TAG_ONE_TURN_EFFECT; supply CARD_COSTS_HEALTH so pay_cost routes its
    # Cost to Health.
    tags = {GameTag.CARD_COSTS_HEALTH: True}


class TIME_618e:
    """Eternal Life Player Enchant"""

    # Hero deathrattle: spend up to 20 Corpses to resurrect. Reviving the hero
    # is an engine limitation; we spend the Corpses.
    deathrattle = _HuskHeroDeathrattle(FRIENDLY_HERO)


##
# Across the Timeways mini-set (END_, "End Time")


class _BlessingOfTheInfiniteBuff(TargetedAction):
    """Blessing of the Infinite (END_003p) — buff the first Undead the
    controller plays each turn with +N Attack (N = imbue level), then latch a
    per-turn flag so subsequent Undead this turn are untouched. The flag clears
    at OWN_TURN_END. TARGET is the just-played Undead minion (Play.CARD)."""

    TARGET = ActionArg()

    def do(self, source, target):
        # TARGET is the just-played Undead minion (Play.CARD).
        ctrl = source.controller
        if getattr(ctrl, "_blessing_infinite_consumed_this_turn", False):
            return
        if target is None or target.type != CardType.MINION:
            return
        is_undead = target.race == Race.UNDEAD or Race.UNDEAD in getattr(
            target, "races", []
        )
        if not is_undead:
            return
        ctrl._blessing_infinite_consumed_this_turn = True
        # @ scales with the number of times the Hero Power was imbued.
        amount = max(1, getattr(source, "imbue_level", 1))
        source.game.cheat_action(source, [Buff(target, "END_003pe", atk=amount)])


class _BlessingOfTheInfiniteReset(TargetedAction):
    """Clear the once-per-turn latch at the controller's turn end."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._blessing_infinite_consumed_this_turn = False


##
# Spells


class END_003:
    """Finality"""

    # Draw an Undead. Imbue your Hero Power twice.
    play = (
        ForceDraw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + UNDEAD)),
        Imbue(CONTROLLER),
        Imbue(CONTROLLER),
    )


##
# Tokens — Imbued Hero Power


class END_003p:
    """Blessing of the Infinite"""

    # Passive. The first Undead you play each turn gains +@ Attack.
    # @ scales with the imbue level (Finality imbues twice -> level >= 2).
    events = (
        Play(CONTROLLER, MINION + UNDEAD).after(
            _BlessingOfTheInfiniteBuff(Play.CARD)
        ),
        OWN_TURN_END.on(_BlessingOfTheInfiniteReset(CONTROLLER)),
    )


##
# Enchantments


class END_003pe:
    """The End is Nigh"""

    # Increased Attack. Amount set dynamically by Buff(atk=imbue_level).
