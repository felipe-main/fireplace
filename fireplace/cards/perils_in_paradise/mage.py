from ..utils import *


##
# Custom actions / helpers


class _UnderTheSeaSummon(TargetedAction):
    """Under the Sea — Draw a different spell from your deck, then summon a
    random collectible minion whose Cost equals that drawn spell's Cost.
    "A different spell" = a spell other than Under the Sea itself; we draw a
    random spell from the deck and read its Cost at draw time, then summon a
    random minion of that exact Cost."""

    TARGET = ActionArg()

    def do(self, source, player):
        from .. import db
        spells = [c for c in player.deck if c.type == CardType.SPELL]
        if not spells:
            return
        pick = source.game.random.choice(spells)
        source.game.cheat_action(source, [Draw(player, pick)])
        cost = pick.cost or 0
        pool = [
            cid for cid, c in db.items()
            if c.collectible
            and c.type == CardType.MINION
            and (c.cost or 0) == cost
            and (not source.game.is_standard or c.is_standard)
        ]
        if not pool:
            return
        cid = source.game.random.choice(pool)
        source.game.cheat_action(source, [Summon(player, cid)])


class _RisingWaves(TargetedAction):
    """Rising Waves — Deal $2 damage to all minions. If none die, deal $2
    more. We snapshot the live minion set, hit each for (2 + spellpower),
    process deaths, and if every snapshotted minion is still in play, hit
    them all again for the same amount."""

    TARGET = ActionArg()

    def do(self, source, player):
        from hearthstone.enums import Zone
        amount = source.controller.get_spell_damage(source, 2)
        minions = list(source.game.board)
        minions = [c for c in minions if c.type == CardType.MINION]
        if not minions:
            return
        for m in minions:
            source.game.cheat_action(source, [Hit(m, amount)])
        source.game.process_deaths()
        # "If none die" — every minion we hit is still on the board.
        if all(m.zone == Zone.PLAY for m in minions):
            for m in minions:
                if m.zone == Zone.PLAY:
                    source.game.cheat_action(source, [Hit(m, amount)])


class _KingTideStartAura(TargetedAction):
    """King Tide — arm the "both players' spells cost (5)" window on the
    CONTROLLER (so it persists even if King Tide leaves play) and attach the
    persistent aura enchant. Lasts until the end of your next turn = two of the
    controller's OWN_TURN_END ticks (end of this turn + end of your next)."""

    TARGET = ActionArg()

    def do(self, source, player):
        ctrl = source.controller
        ctrl._king_tide_turns_left = 2
        source.game.cheat_action(source, [Buff(ctrl, "VAC_524e3")])


class _KingTideTick(TargetedAction):
    """King Tide — decrement the window at each OWN_TURN_END (carried by the
    controller aura enchant so it ticks regardless of King Tide's presence)."""

    TARGET = ActionArg()

    def do(self, source, player):
        ctrl = source.controller
        ctrl._king_tide_turns_left = getattr(ctrl, "_king_tide_turns_left", 0) - 1
        # `source` is the controller aura enchant; retire it when the window
        # closes so its SET(5) refresh stops (spells revert to normal cost).
        if ctrl._king_tide_turns_left <= 0 and source.type == CardType.ENCHANTMENT:
            source.game.cheat_action(source, [Destroy(source)])


##
# Spells


class VAC_428e:
    # In-data buff "Going with the Flow" — Spell Damage +1. Tags not parsed
    # from data XML; declare so Buff() lands the spellpower bonus.
    tags = {GameTag.SPELLPOWER: 1}


class VAC_428:
    """Go with the Flow"""

    # Choose a minion. If it's an enemy, Freeze it. If it's friendly, give
    # it Spell Damage +1.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Find(TARGET + ENEMY) & Freeze(TARGET) | Buff(TARGET, "VAC_428e")


class VAC_431:
    """Under the Sea"""

    # Draw a different spell. Summon a random minion of that spell's Cost.
    play = _UnderTheSeaSummon(CONTROLLER)


class VAC_509t:
    """Water Elemental"""

    # Freeze any character damaged by this minion.
    events = Damage(CHARACTER, None, SELF).on(Freeze(Damage.TARGET))


class VAC_509:
    """Tsunami"""

    # Summon three 3/6 Water Elementals that Freeze. They attack random
    # enemies. (The token's printed stats are 4/3/6 — a 3/6 body.)
    play = (
        Summon(CONTROLLER, "VAC_509t").then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
        )
        * 3
    )


class VAC_520:
    """Seabreeze Chalice"""

    # Deal $2 damage randomly split among all enemies. (3 Drinks left!)
    play = (
        Hit(RANDOM(ENEMY_CHARACTERS), 1) * SPELL_DAMAGE(2),
        Give(CONTROLLER, "VAC_520t"),
    )


class VAC_520t:
    """Seabreeze Chalice"""

    # Deal $2 damage randomly split among all enemies. (2 Drinks left!)
    play = (
        Hit(RANDOM(ENEMY_CHARACTERS), 1) * SPELL_DAMAGE(2),
        Give(CONTROLLER, "VAC_520t2"),
    )


class VAC_520t2:
    """Seabreeze Chalice"""

    # Deal $2 damage randomly split among all enemies. (Last Drink!)
    play = Hit(RANDOM(ENEMY_CHARACTERS), 1) * SPELL_DAMAGE(2)


class VAC_953:
    """Rising Waves"""

    # Deal $2 damage to all minions. If none die, deal $2 more.
    play = _RisingWaves(CONTROLLER)


##
# Locations


class VAC_522:
    """Tide Pools"""

    # Discover a spell that costs (3) or less. After you cast a spell,
    # reopen this. The activate script opens a Discover over spells costing
    # <= 3; the OWN_SPELL_PLAY trigger clears its cooldown so it can be used
    # again immediately.
    activate = DISCOVER(
        RandomSpell(custom_filter=lambda c: (c.cost or 0) <= 3)
    )
    events = OWN_SPELL_PLAY.on(ReopenLocation(SELF))


##
# Minions


class VAC_424:
    """Raylla, Sand Sculptor"""

    # Paladin Tourist. After you cast a spell, summon a random 2-Cost
    # minion and give it Divine Shield. (Tourist is a deckbuilding-only
    # keyword — no in-game trigger.)
    events = OWN_SPELL_PLAY.after(
        Summon(CONTROLLER, RandomMinion(cost=2)).then(
            GiveDivineShield(Summon.CARD)
        )
    )


class VAC_435e:
    # In-data buff "Marooned" — your first spell each turn costs (2) less.
    # Cost delta not parsed from data XML; declare it.
    tags = {GameTag.COST: -2}


class VAC_435:
    """Marooned Archmage"""

    # Your first spell each turn costs (2) less. Conditional aura: only
    # while you've cast no spell yet this turn.
    update = (Count(CARDS_PLAYED_THIS_TURN + SPELL) == 0) & Refresh(
        FRIENDLY_HAND + SPELL, buff="VAC_435e"
    )


class VAC_443e2:
    # "Ride the Wave 2" — stamps Casts When Drawn onto the next spell drawn.
    tags = {GameTag.CASTS_WHEN_DRAWN: True}


class VAC_443e:
    # "Ride the Wave" — progress controller on the player: the NEXT spell
    # drawn becomes Casts When Drawn, then this enchant removes itself.
    progress_total = 1
    events = Draw(CONTROLLER).on(
        (CURRENT_PROGRESS(SELF) < 1)
        & Find(Draw.CARD + SPELL)
        & Buff(Draw.CARD, "VAC_443e2"),
        Find(Draw.CARD + SPELL) & AddProgress(SELF, Draw.CARD),
    )
    reward = Destroy(SELF)


class VAC_443:
    """Surfalopod"""

    # Battlecry: The next spell you draw is Cast When Drawn.
    play = Buff(CONTROLLER, "VAC_443e")


class VAC_524e:
    # "Waveriding" — all spells cost (5). Applied as a SET via aura.
    cost = SET(5)


class VAC_524e2:
    # "Waveriding Rival" — same SET(5), separate id for the opponent's copy.
    cost = SET(5)


@custom_card
class VAC_524e3:
    # Persistent CONTROLLER aura for King Tide: while the controller's
    # _king_tide_turns_left > 0, both players' hand spells are SET to cost 5.
    # Ticks down at each OWN_TURN_END and destroys itself when the window ends.
    # Lives on the player, so the effect persists even if King Tide dies.
    tags = {
        GameTag.CARDNAME: "King Tide",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = (Attr(CONTROLLER, "_king_tide_turns_left") > 0) & (
        Refresh(FRIENDLY_HAND + SPELL, buff="VAC_524e"),
        Refresh(ENEMY_HAND + SPELL, buff="VAC_524e2"),
    )
    events = OWN_TURN_END.on(_KingTideTick(CONTROLLER))


class VAC_524:
    """King Tide"""

    # Battlecry: Both players' spells cost (5) until the end of your next turn.
    # A persistent CONTROLLER enchant (VAC_524e3) carries the window so it
    # survives King Tide leaving play.
    play = _KingTideStartAura(SELF)
