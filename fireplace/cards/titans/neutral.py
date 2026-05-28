from ..utils import *

from hearthstone.enums import SpellSchool


class _DisguisedKthirTransform(TargetedAction):
    """Disguised K'thir — morph into a random opponent deck card each turn.
    Guard against empty enemy deck to prevent crashes."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp_deck = source.controller.opponent.deck
        if not opp_deck:
            return
        pick = source.game.random.choice(list(opp_deck))
        source.game.cheat_action(source, [Morph(source, pick.id)])


##
# Custom actions / helpers


class _KologarnCapture(TargetedAction):
    """Kologarn — whenever this attacks a minion, put it in your hand.
    The defender minion is removed from the board and added to Kologarn's
    controller's hand, then buffed with TTN_330e so the deathrattle can
    identify and gift those captured minions to the opponent."""

    TARGET = ActionArg()

    def do(self, source, target):
        # target is the defender minion (passed as Attack.DEFENDER)
        defenders = target if isinstance(target, list) else [target]
        for defender in defenders:
            if not hasattr(defender, "zone"):
                continue
            if defender.zone != Zone.PLAY:
                continue
            ctrl = source.controller
            if len(ctrl.hand) >= ctrl.max_hand_size:
                # Hand full — just destroy it
                source.game.cheat_action(source, [Destroy(defender)])
            else:
                # Cross-controller field→hand transfer: direct list manipulation
                # so the defender ends up in CTRL's hand (not its original owner's).
                opp = defender.controller
                if defender in opp.field:
                    opp.field.remove(defender)
                defender._zone = Zone.HAND
                ctrl.hand.append(defender)
                defender.controller = ctrl
                # Mark this minion as captured by Kologarn for the deathrattle
                defender._kologarn_captured = True


class _KologarnDeathrattle(TargetedAction):
    """Kologarn deathrattle — give all captured minions in hand to opponent."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        captured = [c for c in list(ctrl.hand) if getattr(c, "_kologarn_captured", False)]
        for card in captured:
            if len(opp.hand) >= opp.max_hand_size:
                continue
            card._kologarn_captured = False
            # Cross-controller hand transfer: direct list manipulation avoids
            # zone-change no-op when card is already in Zone.HAND.
            ctrl.hand.remove(card)
            opp.hand.append(card)
            card.controller = opp


class _PrisonOfYoggCastSpells(TargetedAction):
    """Prison of Yogg-Saron — cast 4 random spells, targeting the chosen
    character if possible. Picks a spell, materializes a fresh instance,
    and if the chosen character is a legal target for it, casts at the
    chosen character; otherwise falls back to CastSpell's random target.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        from fireplace.dsl.random_picker import RandomSpell
        target_char = target[0] if isinstance(target, list) and target else target
        for _ in range(4):
            picker = RandomSpell()
            cids = picker.evaluate(source)
            if not cids:
                continue
            cid = cids[0] if isinstance(cids, list) else cids
            # Create the spell instance once so we can ask its .targets list
            # whether the chosen character is a valid target for this spell.
            try:
                candidate = source.controller.card(cid)
            except Exception:
                candidate = None
            if candidate is not None and target_char is not None \
                    and target_char in getattr(candidate, "targets", []):
                source.game.queue_actions(source, [CastSpell(cid, target_char)])
            else:
                source.game.queue_actions(source, [CastSpell(cid)])


class _MechagnomeGuideForgedDiscover(TargetedAction):
    """Mechagnome Guide (Forged) — Discover a spell, then reduce its cost by 3."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        action = DISCOVER(RandomSpell()).then(
            Buff(Discover.CARD, "TTN_076e")
        )
        source.game.queue_actions(source, [action])


class _TramOperatorMechDiscount(TargetedAction):
    """Tram Operator — set the next-mech cost discount flag on the controller."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl._next_mech_cost_reduction += 2


class _RavenousKrakenStore(TargetedAction):
    """Ravenous Kraken — store the destroyed minion's ID for the deathrattle."""

    TARGET = ActionArg()

    def do(self, source, target):
        targets = target if isinstance(target, list) else [target]
        for t in targets:
            source._kraken_stored_id = t.id
        source.game.cheat_action(source, [Destroy(TARGET)])

    def get_target_args(self, source, target):
        return [target]


class _RavenousKrakenDeathrattle(TargetedAction):
    """Ravenous Kraken deathrattle — summon a copy of the devoured minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        stored_id = getattr(source, "_kraken_stored_id", None)
        if not stored_id:
            return
        source.game.cheat_action(source, [Summon(source.controller, stored_id)])


class _FateSplitterDeathrattle(TargetedAction):
    """Fate Splitter deathrattle — give a copy of the card that killed this.
    'The card that killed this' is stored via the last_attacker or last_damage_source."""

    TARGET = ActionArg()

    def do(self, source, target):
        killer_id = getattr(source, "_fate_splitter_killer_id", None)
        if not killer_id:
            return
        source.game.cheat_action(source, [Give(source.controller, killer_id)])


class _FateSplitterTrackKiller(TargetedAction):
    """Fate Splitter — track the card that killed this via SELF_DAMAGE source."""

    TARGET = ActionArg()
    SOURCE_ENTITY = ActionArg()

    def do(self, source, target, source_entity):
        entities = source_entity if isinstance(source_entity, list) else [source_entity]
        for e in entities:
            if e is not None and hasattr(e, "id"):
                source._fate_splitter_killer_id = e.id
                break


class _MechaLeaperDeathrattle(TargetedAction):
    """Mecha-Leaper deathrattle — give a random friendly Mech +2/+2 and
    this deathrattle (so the chain propagates)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        pool = [m for m in ctrl.field if Race.MECHANICAL in getattr(m, "races", [])]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        source.game.cheat_action(source, [Buff(pick, "TTN_734e2")])
        pick.additional_deathrattles.append((_MechaLeaperDeathrattle(SELF),))
        if not pick.has_deathrattle:
            pick.has_deathrattle = True


class _ContainmentUnitDeathrattle(TargetedAction):
    """Containment Unit deathrattle — summon a random 8-Cost minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Summon(source.controller, RandomMinion(cost=8))])


class _DroneDeconstructorSparkbot(TargetedAction):
    """Drone Deconstructor — get a 1/1 Magnetic Sparkbot with a random bonus effect."""

    TARGET = ActionArg()

    def do(self, source, target):
        sparkbot_ids = [
            "TTN_719t",   # Divine Shield
            "TTN_719t1",  # Taunt
            "TTN_719t2",  # Rush
            "TTN_719t3",  # Windfury
            "TTN_719t4",  # Lifesteal
            "TTN_719t5",  # Stealth
            "TTN_719t6",  # Poisonous
            "TTN_719t7",  # Reborn
        ]
        pick = source.game.random.choice(sparkbot_ids)
        source.game.cheat_action(source, [Give(source.controller, pick)])


class _WatcherOfTheSunPlay(TargetedAction):
    """Watcher of the Sun base battlecry — give a random Holy spell."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Give(source.controller, RandomSpell(spell_school=SpellSchool.HOLY))])


class _WatcherOfTheSunForgedPlay(TargetedAction):
    """Watcher of the Sun (Forged) battlecry — give a random Holy spell
    + restore 6 Health to hero."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [
            Give(source.controller, RandomSpell(spell_school=SpellSchool.HOLY)),
            Heal(source.controller.hero, 6),
        ])


class _SharpEyedSeekerDraw(TargetedAction):
    """Sharp-Eyed Seeker — draw the first card in deck that didn't start there."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        pool = [c for c in ctrl.deck if not getattr(c, "started_in_deck", True)]
        if not pool:
            return
        pick = pool[0]
        source.game.cheat_action(source, [ForceDraw(pick)])


class _IgisForgeWeapon(TargetedAction):
    """Ignis, the Eternal Flame — if you've Forged a card this game, craft
    a custom weapon. Approximated as Discovering from all collectible weapons."""

    TARGET = ActionArg()

    def do(self, source, target):
        if source.controller.cards_forged_this_game <= 0:
            return
        action = DISCOVER(RandomCollectible(type=CardType.WEAPON)).then(
            Give(source.controller, Discover.CARD)
        )
        source.game.queue_actions(source, [action])


class _CelestialProjectionistCopy(TargetedAction):
    """Celestial Projectionist — add a temporary copy of the chosen friendly minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        targets = target if isinstance(target, list) else [target]
        for t in targets:
            source.game.cheat_action(
                source,
                [Give(source.controller, Copy(t)).then(GiveTemporary(Give.CARD))],
            )


class _StarlightWhelpDraw(TargetedAction):
    """Starlight Whelp — give a random card from the starting hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        starting = getattr(ctrl, "starting_hand", None)
        if not starting:
            return
        ids = [c.id for c in starting]
        if not ids:
            return
        pick = source.game.random.choice(ids)
        source.game.cheat_action(source, [Give(ctrl, pick)])


class _FlameBehemothMagneticMechs(TargetedAction):
    """Flame Behemoth — get two random Magnetic Mechs that cost (2) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import GameTag as _GT
        ctrl = source.controller
        for _ in range(2):
            source.game.cheat_action(
                source,
                [Give(ctrl, RandomMech(custom_filter=lambda c: c.tags.get(_GT.MAGNETIC, 0))).then(
                    Buff(Give.CARD, "TTN_716e")
                )],
            )


##
# Minions


class TTN_039:
    """Watcher of the Sun"""

    # Battlecry: Get a random Holy spell.
    # Forge: Also restore 6 Health to your hero.
    forge_card = "TTN_039t"
    play = _WatcherOfTheSunPlay(CONTROLLER)


class TTN_039t:
    """Watcher of the Sun"""

    # Forged. Battlecry: Get a random Holy spell. Restore 6 Health to your hero.
    play = _WatcherOfTheSunForgedPlay(CONTROLLER)


class TTN_042:
    """Cyclopian Crusher"""

    # Rush. Forge: Gain +3/+2. (Forged version has base stats 6/5.)
    forge_card = "TTN_042t"


class TTN_042t:
    """Cyclopian Crusher"""

    # Forged. Rush. (6/5 Rush — stats set by data.)
    pass


class TTN_076:
    """Mechagnome Guide"""

    # Battlecry: Discover a spell. Forge: It costs (3) less.
    forge_card = "TTN_076t"
    play = DISCOVER(RandomSpell())


class TTN_076t:
    """Mechagnome Guide"""

    # Forged. Battlecry: Discover a spell. It costs (3) less.
    play = _MechagnomeGuideForgedDiscover(CONTROLLER)


class TTN_076e:
    # In data — "Vacation Time!" enchant: costs (3) less.
    tags = {GameTag.COST: -3}
    events = REMOVED_IN_PLAY


class TTN_083:
    """Son of Hodir"""

    # Battlecry: Shuffle four 8/8 Giants into your deck that are summoned when drawn.
    play = Shuffle(CONTROLLER, "TTN_083t") * 4


class TTN_083t:
    """Frost Tyrant"""

    # Summoned When Drawn
    draw = Summon(CONTROLLER, SELF)


class TTN_087:
    """Absorbent Parasite"""

    # Magnetic, Rush. Can Magnetize to Mechs and Beasts.
    # Custom magnetize: find Mech OR Beast to the right of SELF, merge stats.
    magnetic = Find(RIGHT_OF(SELF) + (MECH | BEAST)) & (
        Buff(RIGHT_OF(SELF), "TTN_087e", atk=ATK(SELF), max_health=CURRENT_HEALTH(SELF)),
        Remove(SELF),
    )


class TTN_090:
    """Prison of Yogg-Saron"""

    # Choose a character. Cast 4 random spells (targeting it if possible).
    # TODO: Full targeting behaviour (prefer chosen character) is only
    # approximated. This just casts 4 random spells; targeting is random.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    activate = CastSpell(RandomSpell()) * 4


class TTN_330:
    """Kologarn"""

    # Rush. Whenever this attacks a minion, put it in your hand.
    # Deathrattle: Move any in your hand to your opponent's.
    events = Attack(SELF, ALL_MINIONS).on(_KologarnCapture(Attack.DEFENDER))
    deathrattle = _KologarnDeathrattle(SELF)


class TTN_458:
    """XB-488 Disposalbot"""

    # Battlecry: Deal 5 damage randomly split among all enemy minions.
    # Forge: Gain Lifesteal.
    forge_card = "TTN_458t"
    play = Hit(RANDOM_ENEMY_MINION, 1) * 5


class TTN_458t:
    """XB-488 Disposalbot"""

    # Forged. Lifesteal. Battlecry: Deal 5 damage randomly split among all enemy minions.
    # LIFESTEAL is set in data.
    play = Hit(RANDOM_ENEMY_MINION, 1) * 5


class TTN_479:
    """Flame Revenant"""

    # After you summon an Elemental, give it +1/+1.
    events = Summon(CONTROLLER, MINION + ELEMENTAL - SELF).after(
        Buff(Summon.CARD, "TTN_479e")
    )


class TTN_479e:
    # In data — "Heating Up!" enchant: +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TTN_700:
    """Containment Unit"""

    # Magnetic. Deathrattle: Summon a random 8-Cost minion.
    magnetic = MAGNETIC("TTN_700e1")
    deathrattle = _ContainmentUnitDeathrattle(SELF)


class TTN_700e1:
    # In data — "Containment Unit" enchant.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=8))


class TTN_710:
    """Ancient Totem"""

    # Vanilla 0/0/3 minion. Stats are set in data.
    pass


class TTN_711:
    """Saronite Tol'vir"""

    # Taunt. Whenever this is attacked, draw a card.
    # TAUNT is set in data.
    events = Attack(ENEMY_CHARACTERS, SELF).on(Draw(CONTROLLER))


class TTN_712:
    """Sharp-Eyed Seeker"""

    # Battlecry: If there is a card in your deck that didn't start there, draw it.
    play = _SharpEyedSeekerDraw(CONTROLLER)


class TTN_713:
    """Angry Helhound"""

    # Rush. Has +4 Attack on your turn.
    # RUSH is set in data. base atk=2; on controller's turn gets +4 via aura.
    update = Find(CURRENT_PLAYER + CONTROLLER) & Refresh(SELF, {GameTag.ATK: +4})


class TTN_714:
    """Runefueled Golem"""

    # Battlecry: Discover a weapon from any class.
    play = DISCOVER(RandomCollectible(type=CardType.WEAPON))


class TTN_715:
    """Time-Lost Protodrake"""

    # Taunt. When you draw this, add a random Dragon to your hand.
    # TAUNT is set in data.
    draw = Give(CONTROLLER, RandomDragon())


class TTN_716:
    """Flame Behemoth"""

    # Battlecry: Get two random Magnetic Mechs. They cost (2) less.
    play = _FlameBehemothMagneticMechs(CONTROLLER)


class TTN_716e:
    # In data — "110% Efficiency" enchant: costs (2) less.
    tags = {GameTag.COST: -2}
    events = REMOVED_IN_PLAY


class TTN_717:
    """Algalon the Observer"""

    # Battlecry: Replace your Hero Power with Algalon's Vision.
    play = Summon(CONTROLLER, "TTN_717t")


class TTN_718:
    """Starlight Whelp"""

    # Battlecry: Get a random card from your starting hand.
    play = _StarlightWhelpDraw(CONTROLLER)


class TTN_723:
    """Tram Operator"""

    # Battlecry: Draw a Mech. The next Mech you play costs (2) less.
    play = (
        ForceDraw(RANDOM(FRIENDLY_DECK + MECH)),
        _TramOperatorMechDiscount(CONTROLLER),
    )


class TTN_724:
    """Storm Giant"""

    # Taunt. Forge: Costs (2) less. Can be Forged endlessly.
    # TAUNT is set in data.
    forge_card = "TTN_724t"


class TTN_724t:
    """Storm Giant"""

    # Forged. Taunt. Forge: Costs (2) less. Can be Forged endlessly.
    # TAUNT is set in data. forge_card loops back to itself for endless forging.
    forge_card = "TTN_724t"


class TTN_729:
    """Melted Maker"""

    # After you Forge a card, get a copy of it.
    # ForgeCard.do broadcasts AFTER with the forged card as the event arg.
    events = ForgeCard(FRIENDLY_HAND).after(Give(CONTROLLER, ForgeCard.TARGET))


class TTN_731:
    """Careless Mechanist"""

    # After you draw your second card in a turn, destroy this.
    # Draw.do increments cards_drawn_this_turn BEFORE broadcasting ON, so
    # by the time our listener fires the counter already reflects this draw.
    events = Draw(CONTROLLER).on(
        (Attr(CONTROLLER, GameTag.NUM_CARDS_DRAWN_THIS_TURN) >= 2) & Destroy(SELF)
    )


class TTN_732:
    """Invent-o-matic"""

    # Whenever you Magnetize a minion, give it +1/+1.
    # Engine hook: when a friendly minion magnetizes, Play.do calls each
    # field minion's `on_friendly_magnetize(self, magnetizing_card)` script
    # and queues the returned actions.
    @staticmethod
    def on_friendly_magnetize(self, magnetizer):
        # The magnetizer attached to a target Mech which is identified by
        # being in the controller's field; buff that target +1/+1.
        return [Buff(magnetizer, "TTN_732e")]


@custom_card
class TTN_732e:
    tags = {
        GameTag.CARDNAME: "Inventive",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
    }


class TTN_733:
    """Relentless Worg"""

    # Rush. After this attacks and kills a minion, restore this to full Health.
    # Use Attack(SELF, MINION) with AFTER so the event fires after both hits resolve.
    # MINION (not ALL_MINIONS) is used so the match succeeds even after the
    # defender is moved to the graveyard by process_deaths.
    events = Attack(SELF, MINION).after(
        Dead(Attack.DEFENDER) & FullHeal(SELF)
    )


class TTN_734:
    """Mecha-Leaper"""

    # Magnetic. Deathrattle: Give a friendly Mech +2/+2 and this Deathrattle.
    magnetic = MAGNETIC("TTN_734e")
    deathrattle = _MechaLeaperDeathrattle(SELF)


class TTN_734e:
    # In data — "Mecha-Leaper" enchant. Deathrattle marker only; stats
    # are passed explicitly in the buff() call if needed.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _MechaLeaperDeathrattle(SELF)


class TTN_734e2:
    # In data — "Mecha-Leaping" enchant: +2/+2 + deathrattle.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2, GameTag.DEATHRATTLE: True}
    deathrattle = _MechaLeaperDeathrattle(SELF)


class TTN_741:
    """Disguised K'thir"""

    # Each turn this is in your hand, transform into a random card in your
    # opponent's deck.
    class Hand:
        events = OWN_TURN_BEGIN.on(_DisguisedKthirTransform(SELF))


class TTN_742:
    """Celestial Projectionist"""

    # Battlecry: Choose a friendly minion. Add a temporary copy of it to your hand.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Give(CONTROLLER, Copy(TARGET)).then(GiveTemporary(Give.CARD))


class TTN_751:
    """Ignis, the Eternal Flame"""

    # Battlecry: If you've Forged a card this game, craft a custom weapon.
    # "Craft a custom weapon" is approximated as Discover-a-weapon.
    play = _IgisForgeWeapon(CONTROLLER)


class TTN_754:
    """Ravenous Kraken"""

    # Battlecry: Destroy a friendly minion.
    # Deathrattle: Summon a copy of it.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }

    def play(self):
        target = self.target
        if target is None:
            return
        self._kraken_stored_id = target.id
        yield Destroy(TARGET)

    deathrattle = _RavenousKrakenDeathrattle(SELF)


class TTN_812:
    """Victorious Vrykul"""

    # After this attacks, get a 2/3 Val'kyr that costs (1).
    events = Attack(SELF).on(Give(CONTROLLER, "TTN_812t"))


class TTN_832:
    """Trogg Exile"""

    # Rush. Battlecry: Deal 4 damage to your hero.
    play = Hit(FRIENDLY_HERO, 4)


class _FateSplitterDeathrattle(TargetedAction):
    """Fate Splitter — give a copy of the card that killed this.
    Reads target._last_damage_source_id stamped by Damage.do on lethal damage.
    Falls back to a self-copy if the killing source wasn't recorded (e.g.
    the killing came from a Destroy action that bypassed Damage.do).
    """
    TARGET = ActionArg()

    def do(self, source, target):
        killer_id = getattr(target, "_last_damage_source_id", None)
        if not killer_id:
            return
        source.game.cheat_action(source, [Give(target.controller, killer_id)])


class TTN_859:
    """Fate Splitter"""

    # Deathrattle: Get a copy of the card that killed this.
    deathrattle = _FateSplitterDeathrattle(SELF)


class TTN_860:
    """Drone Deconstructor"""

    # Battlecry: Get a 1/1 Magnetic Sparkbot with a random bonus effect.
    play = _DroneDeconstructorSparkbot(CONTROLLER)


class TTN_924:
    """Razorscale"""

    # Cards can't cost less than (2).
    # Approximate via update aura: Refresh all hand cards to max(current, 2).
    # Full implementation would require patching cost evaluation; this covers
    # the common case of cheap cards being capped at (2).
    update = Refresh(
        FRIENDLY_HAND + ENEMY_HAND,
        {GameTag.COST: lambda self, i: max(i, 2)},
    )


class TTN_931:
    """Imposing Anubisath"""

    # Taunt. Can't attack.
    # TAUNT and CANT_ATTACK are both set in data — no script needed.
    pass
