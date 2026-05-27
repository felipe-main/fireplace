from ..utils import *


##
# Helpers

PLAGUE_IDS = ["TTN_450t", "TTN_450t2", "TTN_450t3"]


def _shuffle_one_plague(source, opponent):
    """Shuffle one random Plague into opponent's deck. Also increments
    `plagues_shuffled_into_enemy` on the source controller so Chained
    Guardian's cost_mod can read it."""
    from hearthstone.enums import Zone

    plague_id = source.game.random.choice(PLAGUE_IDS)
    plague = opponent.card(plague_id)
    if len(opponent.deck) < opponent.max_deck_size:
        plague.zone = Zone.DECK
        opponent.shuffle_deck()
    ctrl = source.controller
    ctrl.plagues_shuffled_into_enemy += 1


def _shuffle_two_plagues(source, opponent):
    """Shuffle two random Plagues into opponent's deck."""
    for _ in range(2):
        _shuffle_one_plague(source, opponent)


class _PlagueUnendingCheck(TargetedAction):
    """Helya — when a Plague is drawn and _plagues_are_unending is True,
    immediately shuffle a fresh copy of that Plague back into the deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if not getattr(ctrl, "_plagues_are_unending", False):
            return
        from hearthstone.enums import Zone
        new_plague = ctrl.card(source.id)
        if len(ctrl.deck) < ctrl.max_deck_size:
            new_plague.zone = Zone.DECK
            ctrl.shuffle_deck()


##
# Plague tokens (non-collectible; drawn by the opponent when shuffled in)


class TTN_450t:
    """Blood Plague"""

    draw = _PlagueUnendingCheck(SELF)


class TTN_450t2:
    """Unholy Plague"""

    draw = _PlagueUnendingCheck(SELF)


class TTN_450t3:
    """Frost Plague"""

    draw = _PlagueUnendingCheck(SELF)


##
# Minions


# Deathrattle: Shuffle two random Plagues into your opponent's deck.
class _DistressedKvaldir(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        _shuffle_two_plagues(source, source.controller.opponent)


class TTN_450:
    """Distressed Kvaldir"""

    deathrattle = _DistressedKvaldir(SELF)


# Battlecry: Destroy a Plague in your opponent's deck to deal 3 damage to
# all enemy minions.
class _TombTraitorDestroy(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone

        opp = source.controller.opponent
        plagues_in_deck = [c for c in list(opp.deck) if c.id in PLAGUE_IDS]
        if not plagues_in_deck:
            return
        victim = source.game.random.choice(plagues_in_deck)
        victim.zone = Zone.GRAVEYARD
        source.game.cheat_action(source, [Hit(ENEMY_MINIONS, 3)])


class TTN_455:
    """Tomb Traitor"""

    play = _TombTraitorDestroy(CONTROLLER)


# Battlecry: Spend 3 Corpses to deal 3 damage to all enemies.
# Forge: Gain 3 Corpses instead (and deal 3 damage).
class _EulogizerEffect(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.corpses < 3:
            return
        ctrl.corpses -= 3
        ctrl.corpses_spent_this_game += 3
        source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 3)])


class TTN_457:
    """Eulogizer"""

    forge_card = "TTN_457t"
    play = _EulogizerEffect(CONTROLLER)


# Forged Eulogizer — "Battlecry: Gain 3 Corpses. Deal 3 damage."
class _ForgedEulogizerEffect(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl.corpses += 3
        ctrl.corpses_gained_this_game += 3
        source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 3)])


class TTN_457t:
    """Eulogizer"""

    play = _ForgedEulogizerEffect(CONTROLLER)


# Rush, Reborn. Costs (1) less for each Plague shuffled into the enemy deck
# this game.
class TTN_459:
    """Chained Guardian"""

    tags = {GameTag.RUSH: True, GameTag.REBORN: True}
    cost_mod = -Attr(CONTROLLER, "plagues_shuffled_into_enemy")


##
# Spells


# Deal 3 damage to a minion. If it dies, shuffle two random Plagues into
# your opponent's deck.
class _DownWithTheShip(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone

        source.game.cheat_action(source, [Hit(target, 3)])
        if target.zone == Zone.GRAVEYARD or getattr(target, "dead", False):
            _shuffle_two_plagues(source, source.controller.opponent)


class TTN_454:
    """Down with the Ship"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _DownWithTheShip(TARGET)


# Discover a spell from your deck. If it's a Frost spell, Freeze a random
# enemy minion.
class _NorthernNavigationDiscover(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType, SpellSchool

        spells = [c for c in target.deck if c.type == CardType.SPELL]
        if not spells:
            return
        # Simplified Discover: pull one spell from the deck at random and
        # give it. Check for Frost school to Freeze.
        deck_spell_ids = list({c.id for c in spells})
        chosen_id = source.game.random.choice(deck_spell_ids)
        source.game.cheat_action(source, [Give(target, chosen_id)])
        # Find the just-given copy to check its school.
        given = [c for c in target.hand if c.id == chosen_id]
        if given:
            chosen = given[-1]
            school = getattr(chosen.data, "spell_school", None)
            if school == SpellSchool.FROST:
                source.game.cheat_action(
                    source, [Freeze(RANDOM_ENEMY_MINION)]
                )


class TTN_735:
    """Northern Navigation"""

    play = _NorthernNavigationDiscover(CONTROLLER)


# Both players draw 2 cards. Your opponent cannot play theirs next turn.
class _FrozenOverDraw(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        # Draw 2 for the controller.
        source.game.cheat_action(source, [Draw(target)])
        source.game.cheat_action(source, [Draw(target)])
        # Snapshot opponent's hand before the draws.
        before_opp_hand = set(id(c) for c in opp.hand)
        source.game.cheat_action(source, [Draw(opp)])
        source.game.cheat_action(source, [Draw(opp)])
        # Mark newly-drawn opponent cards as unplayable next turn.
        for c in opp.hand:
            if id(c) not in before_opp_hand:
                c.unplayable_next_turn = max(
                    getattr(c, "unplayable_next_turn", 0), 1
                )


class TTN_744:
    """Frozen Over"""

    play = _FrozenOverDraw(CONTROLLER)


##
# Weapons


# After your hero attacks, shuffle a random Plague into your opponent's deck.
class _StaffOfThePrimusAttack(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        _shuffle_one_plague(source, source.controller.opponent)


class TTN_736:
    """Staff of the Primus"""

    events = Attack(FRIENDLY_HERO).after(_StaffOfThePrimusAttack(CONTROLLER))


##
# Titans


# The Primus — Titan. After this uses an ability, Discover a card with that Rune.
# The per-ability Discover is embedded in each sub-card's play.
class TTN_737:
    """The Primus"""

    titan_ability_order = ["TTN_737t", "TTN_737t1", "TTN_737t3"]


def _rune_discover_picker_ttn(rune_tag):
    """Build a RandomCardPicker yielding DK cards with at least one rune
    of the requested type (COST_BLOOD / COST_FROST / COST_UNHOLY)."""
    return RandomCollectible(
        card_class=CardClass.DEATHKNIGHT,
        custom_filter=lambda c: c.tags.get(rune_tag, 0) >= 1,
    )


# Runes of Blood — Destroy an enemy minion.
# This minion and your hero gain its Health.
class _RunesOfBlood(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        health = target.health
        ctrl = source.controller
        source.game.cheat_action(source, [Destroy(target)])
        # The Primus gains the health (find it on the board).
        primus = next(
            (m for m in ctrl.field if m.id == "TTN_737"), None
        )
        if primus:
            source.game.cheat_action(
                source, [Buff(primus, "TTN_737te", max_health=health)]
            )
        # Hero gains armor equal to the minion's health.
        source.game.cheat_action(source, [GainArmor(ctrl.hero, health)])
        # Discover a Blood Rune DK card.
        picker = _rune_discover_picker_ttn(GameTag.COST_BLOOD)
        source.game.queue_actions(
            source, [Discover(ctrl, picker).then(Give(ctrl, Discover.CARD))]
        )


class TTN_737t:
    """Runes of Blood"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = _RunesOfBlood(TARGET)


# Runes of the Unholy — Summon two 3/3 Undead with Taunt and Reborn.
class _RunesOfUnholy(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(source, [Summon(ctrl, "TTN_737t2")])
        source.game.cheat_action(source, [Summon(ctrl, "TTN_737t2")])
        # Discover an Unholy Rune DK card.
        picker = _rune_discover_picker_ttn(GameTag.COST_UNHOLY)
        source.game.queue_actions(
            source, [Discover(ctrl, picker).then(Give(ctrl, Discover.CARD))]
        )


class TTN_737t1:
    """Runes of the Unholy"""

    play = _RunesOfUnholy(CONTROLLER)


class TTN_737t2:
    """Servant of the Primus"""

    tags = {GameTag.TAUNT: True, GameTag.REBORN: True}


# Runes of Frost — The next spell you cast costs (3) less and has Spell Damage +3.
class _RunesOfFrost(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Stamp the "Chill of Death" enchantment on the hero for -3 cost /
        # +3 spell damage on the next spell. Engine-level approximation:
        # we use a one-shot cost reduction on the player's next spell.
        ctrl._next_spell_cost_reduction = max(
            getattr(ctrl, "_next_spell_cost_reduction", 0), 3
        )
        # Full spell-damage bonus (TTN_737e) would require engine changes;
        # leave as approximation for now.
        # Discover a Frost Rune DK card.
        picker = _rune_discover_picker_ttn(GameTag.COST_FROST)
        source.game.queue_actions(
            source, [Discover(ctrl, picker).then(Give(ctrl, Discover.CARD))]
        )


class TTN_737t3:
    """Runes of Frost"""

    play = _RunesOfFrost(CONTROLLER)


# TTN_737e — "Chill of Death" is in the DB. Declare it so Buff() can reference it.
class TTN_737e:
    # In-data enchantment "Chill of Death".
    # Full implementation would add +3 spellpower and -3 cost to next spell;
    # approximated via _next_spell_cost_reduction in _RunesOfFrost above.
    tags = {}


##
# Helya


# Battlecry: Shuffle all three Plagues into your opponent's deck.
# Plagues they draw this game are unending.
class _HelyaPlay(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone

        opp = source.controller.opponent
        ctrl = source.controller
        # Shuffle one copy of each of the three Plagues.
        for plague_id in PLAGUE_IDS:
            plague = opp.card(plague_id)
            if len(opp.deck) < opp.max_deck_size:
                plague.zone = Zone.DECK
            ctrl.plagues_shuffled_into_enemy += 1
        opp.shuffle_deck()
        # Arm the "unending plagues" flag on the opponent: TTN_450t-family
        # cards' Draw triggers re-shuffle a copy on draw when this is True.
        opp._plagues_are_unending = True


class TTN_850:
    """Helya"""

    play = _HelyaPlay(CONTROLLER)
