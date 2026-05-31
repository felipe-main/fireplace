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
                    Buff(m, "GDB_877e", atk=1, max_health=1),
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
            # Re-home the card into YOUR hand: a cross-player Draw() flips the
            # controller but leaves the card registered in the opponent's hand
            # list, so move zones explicitly (SETASIDE clears it from the
            # opponent's deck, then HAND adds it under the new controller).
            card.zone = Zone.SETASIDE
            card.controller = source.controller
            card.zone = Zone.HAND
            # Remember it so we can put it back at end of turn if unplayed.
            source._doom_card = card


class _DoommaidenReturn(TargetedAction):
    """Doommaiden — at the end of your turn, if the stolen card is still in your
    hand (you didn't play it), put it back in the opponent's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        card = getattr(source, "_doom_card", None)
        if card is None:
            return
        source._doom_card = None
        if card.zone == Zone.HAND and card.controller is source.controller:
            opp = source.controller.opponent
            card.zone = Zone.SETASIDE
            card.controller = opp
            card.zone = Zone.DECK


class _ArmStarlightWanderer(TargetedAction):
    """Starlight Wanderer — the next Draenei you play gains +2/+1."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game

        def hook(played):
            # GDB_720e1 carries no stat tags in data — supply +2/+1 via kwargs.
            game.cheat_action(
                played, [Buff(played, "GDB_720e1", atk=2, max_health=1)]
            )

        source.controller.next_draenei_hooks.append(hook)


##
# Custom actions


class _GainBonusEffects(TargetedAction):
    """Gain N random Bonus Effects (keyword-only)."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        # roll_bonus_effects returns ONE merged tag dict for all `amount`
        # effects — apply it in a single SetTags (iterating it would yield
        # bare GameTag keys).
        tags = roll_bonus_effects(source.game.random, amount)
        source.game.cheat_action(source, [SetTags(target, tags)])


class _ArmAceWayfinder(TargetedAction):
    """Ace Wayfinder — gain two random Bonus Effects; the next Draenei you play
    gains them too."""

    TARGET = ActionArg()

    def do(self, source, target):
        # One merged tag dict for both effects (see _GainBonusEffects).
        rolled = roll_bonus_effects(source.game.random, 2)
        source.game.cheat_action(source, [SetTags(source, rolled)])
        game = source.game

        def hook(played):
            game.cheat_action(played, [SetTags(played, rolled)])

        source.controller.next_draenei_hooks.append(hook)


class _VelenTrigger(TargetedAction):
    """Velen — trigger the Battlecries and Deathrattles of all other Draenei
    you played this game. Targeted battlecries are re-fired against a random
    valid target."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Re-entrancy guard: a re-triggered Draenei's play might itself be a
        # Velen, which would re-trigger every Draenei again — recurse forever.
        if getattr(ctrl, "_velen_retriggering", False):
            return
        ctrl._velen_retriggering = True
        try:
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
                    if not actions:
                        continue
                    proxy = ctrl.card(card.id, source)
                    proxy.controller = ctrl
                    # Give a targeted battlecry a random valid target so it
                    # isn't silently dropped.
                    if kind == "play":
                        try:
                            targets = proxy.play_targets
                        except Exception:
                            targets = []
                        if targets:
                            proxy.target = source.game.random.choice(targets)
                    source.game.queue_actions(proxy, list(actions))
        finally:
            ctrl._velen_retriggering = False


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
        # The Spellburst SPELL arg can arrive as a single card or a 1-element
        # list depending on the trigger path — normalize to one card.
        if isinstance(spell, (list, tuple)):
            spell = spell[0] if spell else None
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
            # SET the cost (not add): COST tag is additive, so the delta brings
            # the spell to exactly this minion's Cost.
            source.game.cheat_action(
                source, [Buff(victim, "GDB_863e", cost=source.cost - victim.cost)]
            )


class _KiljaedenPortal(TargetedAction):
    """Kil'jaeden — replace your deck with an endless portal of Demons. The
    portal never runs dry (Draw conjures fresh Demons; see Draw.get_target_args)
    and the Demons gain an additional +2/+2 at the start of each of your turns
    (escalation in game._begin_turn)."""

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
        ctrl._kiljaeden_pool = pool
        ctrl._kiljaeden_active = True
        ctrl._kiljaeden_bonus = 0
        for _ in range(ctrl.max_deck_size):
            cid = source.game.random.choice(pool)
            new = ctrl.card(cid, source)
            new.controller = ctrl
            new.zone = Zone.DECK
            new._kiljaeden_demon = True
        # Marker enchant so the portal status reads on the hero (cosmetic).
        source.game.cheat_action(source, [Buff(ctrl.hero, "GDB_145e")])


def _launched_ship(player):
    """The Starship most recently launched by this player (read by the
    Protocols, which resolve right after The Exodar's launch)."""
    ship = getattr(player, "_last_launched_ship", None)
    if ship is not None and ship.zone == Zone.PLAY:
        return ship
    return max(
        (m for m in player.field if m.id.startswith("GDB_100t")),
        key=lambda m: m.max_health,
        default=None,
    )


class _ProtocolArmor(TargetedAction):
    """Emergency Repairs — gain Armor equal to the Starship's Health, twice."""

    TARGET = ActionArg()

    def do(self, source, target):
        ship = _launched_ship(source.controller)
        hp = ship.health if ship is not None else 0
        source.game.cheat_action(source, [GainArmor(source.controller.hero, hp * 2)])


class _OffensiveFormation(TargetedAction):
    """Offensive Formation — deal damage equal to the Starship's Attack,
    randomly split between all enemies."""

    TARGET = ActionArg()

    def do(self, source, target):
        ship = _launched_ship(source.controller)
        amount = ship.atk if ship is not None else 0
        for _ in range(amount):
            enemies = [
                c
                for c in ENEMY_CHARACTERS.eval(source.game, source)
                if not c.dead
            ]
            if not enemies:
                break
            source.game.cheat_action(
                source, [Hit(source.game.random.choice(enemies), 1)]
            )


class _CrewTransport(TargetedAction):
    """Crew Transport — get copies of all of the Starship's Pieces and set
    their Costs to (1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ship = _launched_ship(source.controller)
        pieces = list(getattr(ship, "_starship_pieces", [])) if ship else []
        for info in pieces:
            source.game.cheat_action(source, [Give(source.controller, info["id"])])
            copy = source.controller.hand[-1] if source.controller.hand else None
            if copy is not None:
                source.game.cheat_action(
                    source, [Buff(copy, "GDB_100ce", cost=1 - copy.cost)]
                )


class _CastProtocol(TargetedAction):
    """Run the chosen Protocol spell's effect immediately (the choice cards sit
    in SETASIDE, so trigger their play script directly rather than handing them
    to the player)."""

    TARGET = ActionArg()

    def do(self, source, target):
        actions = target.get_actions("play")
        source.game.cheat_action(target, actions)


##
# Minions


class GDB_100:
    """Arkonite Defense Crystal"""

    # Taunt (data). Deathrattle: Gain 6 Armor. Starship Piece.
    deathrattle = GainArmor(FRIENDLY_HERO, 6)


class GDB_120:
    """The Exodar"""

    # Battlecry: If you're building a Starship, launch it and choose a Protocol!
    # Launch, then offer the three Protocols (Emergency Repairs / Offensive
    # Formation / Crew Transport); the chosen one fires immediately.
    play = BUILDING_STARSHIP(CONTROLLER) & (
        LaunchStarship(CONTROLLER),
        Choice(CONTROLLER, ["GDB_100a", "GDB_100b", "GDB_100c"]).then(
            _CastProtocol(Choice.CARD)
        ),
    )


class GDB_129:
    """Doommaiden"""

    # Battlecry: Draw a card from your opponent's deck. If you don't play it
    # this turn, put it back.
    play = _Doommaiden(SELF)
    events = OWN_TURN_END.on(_DoommaidenReturn(SELF))


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


class _CardsDrawnPlayedDestroyed(LazyNum):
    """Game-wide count of cards drawn, played, or destroyed this game (both
    players) — drives The Ceaseless Expanse's cost reduction."""

    def evaluate(self, source):
        return self.base * getattr(source.game, "cards_dpd_this_game", 0)


class GDB_142:
    """The Ceaseless Expanse"""

    # Costs (1) less for each time a card was drawn, played, or destroyed
    # (by either player). Battlecry: Destroy all other minions.
    cost_mod = -_CardsDrawnPlayedDestroyed()
    play = Destroy(ALL_MINIONS - SELF)


class _ShaffarSpellburst(TargetedAction):
    """Nexus-Prince Shaffar — give a random minion in your hand +3/+3 and this
    same Spellburst, which propagates as those minions are later played."""

    TARGET = ActionArg()

    def do(self, source, target):
        hand_minions = [
            c for c in source.controller.hand if c.type == CardType.MINION
        ]
        if not hand_minions:
            return
        victim = source.game.random.choice(hand_minions)
        source.game.cheat_action(
            source, [Buff(victim, "GDB_143e", atk=3, max_health=3)]
        )
        # Grant the buffed minion this same Spellburst (manifests once it is in
        # play and you cast a spell).
        victim.has_spellburst = True
        if not hasattr(victim, "_instance_spellbursts"):
            victim._instance_spellbursts = []
        victim._instance_spellbursts.append(_ShaffarSpellburst(SELF))


class GDB_143:
    """Nexus-Prince Shaffar"""

    # Spellburst: Give a minion in your hand +3/+3 and this Spellburst.
    spellburst = _ShaffarSpellburst(SELF)


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


class _SpacePirateNextWeapon(TargetedAction):
    """Space Pirate — your next weapon costs (1) less (player-level discount;
    a flat COST tag on the player does not reach a weapon in hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.next_weapon_discount += 1


class GDB_333:
    """Space Pirate"""

    # Deathrattle: Your next weapon costs (1) less.
    deathrattle = _SpacePirateNextWeapon(CONTROLLER)


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


class GDB_720:
    """Starlight Wanderer"""

    # Battlecry: The next Draenei you play gains +2/+1.
    play = _ArmStarlightWanderer(SELF)


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


class _AstrobiologistDiscover(TargetedAction):
    """Astrobiologist — at the start of your next turn, Discover a spell, then
    remove the countdown enchant so it only fires once."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(
            source,
            [Discover(ctrl, RandomSpell()).then(Give(ctrl, Discover.CARD))],
        )
        source.game.cheat_action(source, [Destroy(source)])


class GDB_874:
    """Astrobiologist"""

    # Battlecry: At the start of your next turn, Discover a spell.
    play = Buff(FRIENDLY_HERO, "GDB_874e")


class GDB_874e:
    # Astrobiologist — fires once at the start of the controller's next turn.
    tags = {
        GameTag.CARDNAME: "Astrobiologist",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_BEGIN.on(_AstrobiologistDiscover(SELF))


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


class GDB_100b:
    """Offensive Formation"""

    play = _OffensiveFormation(SELF)


class GDB_100c:
    """Crew Transport"""

    play = _CrewTransport(SELF)


##
# Enchantments


class GDB_130e:
    # Welding Complete — +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


@custom_card
class GDB_311e:
    # Deep Space Curator — set the minion's Cost to (0). COST: -100 clamps to 0.
    tags = {
        GameTag.CARDNAME: "Deep Space Curator",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -100,
    }


@custom_card
class GDB_100ce:
    # Crew Transport — set a copied Piece's Cost to (1) (delta supplied at run).
    tags = {
        GameTag.CARDNAME: "Crew Transport",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: 0,
    }


@custom_card
class GDB_145de:
    # Kil'jaeden's Portal — each escalation grants +2/+2 (amount via kwargs).
    tags = {
        GameTag.CARDNAME: "Kil'jaeden's Portal",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 0,
        GameTag.HEALTH: 0,
    }


class GDB_333e:
    # Space Piracy — your next weapon costs (1) less.
    tags = {GameTag.COST: -1}


class GDB_722e:
    # Red Shirt — +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


@custom_card
class GDB_862e:
    # Galactic Crusader — the Holy spell costs (3) less.
    tags = {
        GameTag.CARDNAME: "Galactic Crusader",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class GDB_878e:
    # MRGLGIGA BRAIN — Deathrattle: Draw a card.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Draw(CONTROLLER)
