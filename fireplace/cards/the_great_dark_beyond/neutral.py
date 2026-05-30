from ..utils import *

from hearthstone.enums import CardType, SpellSchool

from ..delve_into_deepholm._bonus import roll_bonus_effects


##
# Misc custom actions for cards needing runtime state


class _AstralVigilant(TargetedAction):
    """Astral Vigilant — get a copy of the last Draenei you played."""

    TARGET = ActionArg()

    def do(self, source, target):
        cid = getattr(source.controller, "last_draenei_played", None)
        if cid:
            source.game.cheat_action(source, [Give(source.controller, cid)])


class _ArmStrandedSpaceman(TargetedAction):
    """Stranded Spaceman — the next Draenei you play gains +2 Health and Rush."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game

        def hook(played):
            game.cheat_action(
                played,
                [
                    Buff(played, "GDB_861e2", max_health=2),
                    SetTags(played, {GameTag.RUSH: True}),
                ],
            )

        source.controller.next_draenei_hooks.append(hook)


class _EscapePod(TargetedAction):
    """Escape Pod — Deathrattle: give adjacent minions +1/+1 and Rush."""

    TARGET = ActionArg()

    def do(self, source, target):
        pos = getattr(source, "_dead_position", None)
        field = source.controller.field
        neighbors = []
        if pos is not None:
            for i in (pos - 1, pos):
                if 0 <= i < len(field):
                    neighbors.append(field[i])
        for m in neighbors:
            source.game.cheat_action(
                source,
                [
                    Buff(m, "GDB_877e2", atk=1, max_health=1),
                    SetTags(m, {GameTag.RUSH: True}),
                ],
            )


class _Doommaiden(TargetedAction):
    """Doommaiden — draw a random card from the opponent's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        if opp.deck:
            card = source.game.random.choice(list(opp.deck))
            source.game.cheat_action(source, [Draw(source.controller, card)])


##
# Custom actions


class _GainBonusEffects(TargetedAction):
    """Gain N random Bonus Effects (keyword-only)."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        for tags in roll_bonus_effects(source.game.random, amount):
            source.game.cheat_action(source, [SetTags(target, tags)])


class _ArmAceWayfinder(TargetedAction):
    """Ace Wayfinder — gain two random Bonus Effects; the next Draenei you play
    gains them too."""

    TARGET = ActionArg()

    def do(self, source, target):
        rolled = roll_bonus_effects(source.game.random, 2)
        for tags in rolled:
            source.game.cheat_action(source, [SetTags(source, tags)])
        game = source.game

        def hook(played):
            for tags in rolled:
                game.cheat_action(played, [SetTags(played, tags)])

        source.controller.next_draenei_hooks.append(hook)


class _VelenTrigger(TargetedAction):
    """Velen — trigger the Battlecries and Deathrattles of all other Draenei
    you played this game. (Approximation: re-fires their deathrattle scripts;
    battlecries that require a target are skipped. Tracked in review.csv.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen = []
        for card in list(ctrl.cards_played_this_game):
            if card is source or card.id in seen:
                continue
            if card.type != CardType.MINION or Race.DRAENEI not in getattr(
                card, "races", []
            ):
                continue
            seen.append(card.id)
            data = card.data
            for kind in ("play", "deathrattle"):
                actions = getattr(data.scripts, kind, None)
                if actions:
                    proxy = ctrl.card(card.id, source)
                    proxy.controller = ctrl
                    source.game.queue_actions(proxy, list(actions))


class _StarVulpera(TargetedAction):
    """Star Vulpera — destroy an enemy Starship or Starship Piece."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        targets = [
            m
            for m in opp.field
            if m.data.tags.get(GameTag.STARSHIP_PIECE, 0)
            or m.data.tags.get(GameTag.STARSHIP, 0)
        ]
        if opp.starship is not None and opp.starship.zone == Zone.PLAY:
            # The Permanent ship is untargetable normally, but Star Vulpera
            # explicitly destroys it.
            opp.starship.dormant = False
            opp.starship.cant_be_damaged = False
            source.game.cheat_action(source, [Destroy(opp.starship)])
            opp.starship = None
            return
        if targets:
            source.game.cheat_action(
                source, [Destroy(source.game.random.choice(targets))]
            )


class _DeepSpaceCurator(TargetedAction):
    """Deep Space Curator — get a random minion of the cast spell's Cost and
    set its Cost to (0)."""

    TARGET = ActionArg()
    SPELL = ActionArg()

    def do(self, source, target, spell):
        cost = spell.cost if spell is not None else 0
        source.game.cheat_action(
            source,
            [
                Give(source.controller, RandomMinion(cost=cost)).then(
                    Buff(Give.CARD, "GDB_311e")
                )
            ],
        )


class _LunarTrailblazer(TargetedAction):
    """Lunar Trailblazer — set the Cost of a random spell in your hand to this
    minion's Cost."""

    TARGET = ActionArg()

    def do(self, source, target):
        spells = [c for c in source.controller.hand if c.type == CardType.SPELL]
        if spells:
            victim = source.game.random.choice(spells)
            source.game.cheat_action(
                source, [Buff(victim, "GDB_863e", cost=source.cost)]
            )


class _KiljaedenPortal(TargetedAction):
    """Kil'jaeden — replace your deck with an endless portal of Demons that
    gain +2/+2 each turn. (Approximation: fills the deck with random Demons and
    arms an escalating buff via the hero. Tracked in review.csv.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        ctrl = source.controller
        for card in list(ctrl.deck):
            card.zone = Zone.SETASIDE
        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.MINION
            and Race.DEMON in getattr(c, "races", [])
        ]
        for _ in range(ctrl.max_deck_size):
            cid = source.game.random.choice(pool)
            new = ctrl.card(cid, source)
            new.controller = ctrl
            new.zone = Zone.DECK
        source.game.cheat_action(source, [Buff(ctrl.hero, "GDB_145e")])


class _ProtocolArmor(TargetedAction):
    """The Exodar Protocol — Emergency Repairs: gain Armor equal to the
    Starship's Health, twice."""

    TARGET = ActionArg()

    def do(self, source, target):
        ship = max(
            (m for m in source.controller.field if m.id.startswith("GDB_100t")),
            key=lambda m: m.max_health,
            default=None,
        )
        hp = ship.health if ship is not None else 0
        source.game.cheat_action(source, [GainArmor(source.controller.hero, hp * 2)])


##
# Minions


class GDB_100:
    """Arkonite Defense Crystal"""

    # Taunt (data). Deathrattle: Gain 6 Armor. Starship Piece.
    deathrattle = GainArmor(FRIENDLY_HERO, 6)


class GDB_120:
    """The Exodar"""

    # Battlecry: If you're building a Starship, launch it and choose a Protocol!
    # (Approximation: launches the Starship; the Protocol choice is simplified
    # to Emergency Repairs. Tracked in review.csv.)
    play = BUILDING_STARSHIP(CONTROLLER) & (
        LaunchStarship(CONTROLLER),
        _ProtocolArmor(SELF),
    )


class GDB_129:
    """Doommaiden"""

    # Battlecry: Draw a card from your opponent's deck. If you don't play it
    # this turn, put it back. (Approximation: draws from the opponent's deck;
    # the put-back rider is not modelled. Tracked in review.csv.)
    play = _Doommaiden(SELF)


class GDB_130:
    """Crystal Welder"""

    # Taunt (data). Battlecry: If you're building a Starship, gain +2/+2.
    play = BUILDING_STARSHIP(CONTROLLER) & Buff(SELF, "GDB_130e")


class GDB_131:
    """Velen, Leader of the Exiled"""

    # Taunt (data). Deathrattle: Trigger the Battlecries and Deathrattles of
    # all other Draenei you played this game.
    deathrattle = _VelenTrigger(SELF)


class GDB_132:
    """Relentless Wrathguard"""

    # Battlecry: Deal 2 damage to an enemy minion. If it dies, Discover a Demon.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Hit(TARGET, 2).then(
        Dead(TARGET) & DISCOVER(RandomMinion(race=Race.DEMON))
    )


class GDB_142:
    """The Ceaseless Expanse"""

    # Costs (1) less for each time a card was drawn, played, or destroyed.
    # Battlecry: Destroy all other minions. (Cost approximation: counts the
    # controller's cards played this game. Tracked in review.csv.)
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME)
    play = Destroy(ALL_MINIONS - SELF)


class GDB_145:
    """Kil'jaeden"""

    # Battlecry: Replace your deck with an endless portal of Demons. Each turn,
    # they gain an additional +2/+2.
    play = _KiljaedenPortal(SELF)


class GDB_310:
    """Ethereal Oracle"""

    # Spell Damage +1 (data). Spellburst: Draw 2 spells.
    spellburst = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)) * 2


class GDB_311:
    """Deep Space Curator"""

    # Spellburst: Get a random minion of the spell's Cost. Set its Cost to (0).
    spellburst = _DeepSpaceCurator(SELF, Spellburst.SPELL)


class GDB_320:
    """Eredar Brute"""

    # Taunt, Lifesteal (data). Costs (1) less for each enemy minion.
    cost_mod = -Count(ENEMY_MINIONS)


class GDB_321:
    """Mutating Lifeform"""

    # After this survives damage, gain a random Bonus Effect.
    events = SELF_DAMAGE.after(Find(SELF + IN_PLAY) & _GainBonusEffects(SELF, 1))


class GDB_322:
    """Lightfused Manasaber"""

    # Rush (data). Spellburst: Gain Divine Shield.
    spellburst = SetTags(SELF, {GameTag.DIVINE_SHIELD: True})


class GDB_330:
    """Ur'zul Rager"""

    # Lifesteal (data). Spellburst: Attack a random enemy minion.
    spellburst = Attack(SELF, RANDOM(ENEMY_MINIONS))


class GDB_331:
    """Splitting Spacerock"""

    # Deathrattle: Summon two 4/4 Splitting Boulders.
    deathrattle = Summon(CONTROLLER, "GDB_331t1") * 2


class GDB_333:
    """Space Pirate"""

    # Deathrattle: Your next weapon costs (1) less.
    deathrattle = Buff(CONTROLLER, "GDB_333e")


class GDB_340:
    """Star Vulpera"""

    # Tradeable (data). Battlecry: Destroy an enemy Starship or Starship Piece.
    play = _StarVulpera(SELF)


class GDB_341:
    """Red Giant"""

    # Costs (1) less for each adjacent card played while in hand.
    cost_mod = -Attr(SELF, "adjacent_plays_while_in_hand")


class GDB_343:
    """Perplexing Anomaly"""

    # Rush, Taunt, ...Stealth? Keywords live in data.


class GDB_435:
    """Moonstone Mauler"""

    # Battlecry: Shuffle 3 Asteroids into your deck that deal damage to a random
    # enemy when drawn.
    play = Shuffle(CONTROLLER, "GDB_430") * 3


class GDB_450:
    """Ace Wayfinder"""

    # Battlecry: Gain two random Bonus Effects. The next Draenei you play gains
    # them as well.
    play = _ArmAceWayfinder(SELF)


class GDB_461:
    """Astral Vigilant"""

    # Battlecry: Get a copy of the last Draenei you played.
    play = _AstralVigilant(SELF)


class GDB_463:
    """Troubled Mechanic"""

    # Divine Shield (data). Spellburst: Draw a Draenei.
    spellburst = ForceDraw(RANDOM(FRIENDLY_DECK + DRAENEI))


class GDB_722:
    """Crimson Commander"""

    # Battlecry and Deathrattle: Give all Draenei in your hand +1/+1.
    play = Buff(FRIENDLY_HAND + DRAENEI, "GDB_722e")
    deathrattle = Buff(FRIENDLY_HAND + DRAENEI, "GDB_722e")


class GDB_723:
    """Hologram Operator"""

    # Battlecry: Get 3 random Temporary Draenei.
    play = (
        Give(CONTROLLER, RandomMinion(race=Race.DRAENEI)).then(
            GiveTemporary(Give.CARD)
        )
    ) * 3


class GDB_860:
    """Starscale Constellar"""

    # Spellburst: Double this minion's Attack.
    spellburst = Buff(SELF, "GDB_860e", atk=ATK(SELF))


class GDB_861:
    """Stranded Spaceman"""

    # Battlecry: The next Draenei you play gains +2 Health and Rush.
    play = _ArmStrandedSpaceman(SELF)



class GDB_862:
    """Galactic Crusader"""

    # Taunt (data). Deathrattle: Get two random Holy spells. They cost (3) less.
    deathrattle = (
        Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.HOLY)).then(
            Buff(Give.CARD, "GDB_862e")
        )
    ) * 2


class GDB_863:
    """Lunar Trailblazer"""

    # Battlecry: Set the Cost of a random spell in your hand to this minion's
    # Cost.
    play = _LunarTrailblazer(SELF)


class GDB_874:
    """Astrobiologist"""

    # Battlecry: At the start of your next turn, Discover a spell.
    play = Buff(CONTROLLER, "GDB_874e")


class GDB_877:
    """Escape Pod"""

    # Rush (data). Deathrattle: Give adjacent minions +1/+1 and Rush.
    deathrattle = _EscapePod(SELF)


class GDB_878:
    """Braingill"""

    # Battlecry: Give all friendly Murlocs "Deathrattle: Draw a card."
    play = Buff(FRIENDLY_MINIONS + MURLOC, "GDB_878e")


##
# Tokens


class GDB_331t1:
    """Splitting Boulder"""

    # 4/4 Elemental. Deathrattle: Summon two 2/2 Splitting Stones.
    deathrattle = Summon(CONTROLLER, "GDB_331t2") * 2


class GDB_331t2:
    """Splitting Stone"""

    # 2/2 Elemental. Deathrattle: Summon two 1/1 Pebbles.
    deathrattle = Summon(CONTROLLER, "GDB_331t3") * 2


class GDB_331t3:
    """Pebble"""

    # 1/1 Elemental vanilla token.


##
# Protocols (The Exodar)


class GDB_100a:
    """Emergency Repairs"""

    play = _ProtocolArmor(SELF)


##
# Enchantments


class GDB_130e:
    # Welding Complete — +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class GDB_311e:
    # Deep Space Curator — set the minion's Cost to (0).
    cost = SET(0)


class GDB_333e:
    # Space Piracy — your next weapon costs (1) less.
    tags = {GameTag.COST: -1}


class GDB_722e:
    # Red Shirt — +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class GDB_862e:
    # Galactic Crusader — the Holy spell costs (3) less.
    tags = {GameTag.COST: -3}


class GDB_878e:
    # MRGLGIGA BRAIN — Deathrattle: Draw a card.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Draw(CONTROLLER)
