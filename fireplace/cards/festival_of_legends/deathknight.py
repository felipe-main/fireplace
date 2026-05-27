from ..utils import *

from hearthstone.enums import Zone


##
# Custom actions / helpers


class _BoneshredderStealDeathrattle(TargetedAction):
    """Boneshredder — pay 5 corpses, pick a random friendly minion that
    died this game and had a Deathrattle, and graft its Deathrattle onto
    Boneshredder. Approximation: copy the dead minion's `additional_deathrattles`
    + base deathrattle action set."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Friendly dead minions with deathrattles. Walk the controller's
        # graveyard (all bodies regardless of whether they were played or
        # summoned). Filter to minions with a base-scripted deathrattle
        # or any grafted additional_deathrattles.
        candidates = []
        for c in list(ctrl.graveyard):
            if c.type != CardType.MINION:
                continue
            if c is source:
                continue
            if not (c.has_deathrattle or c.additional_deathrattles):
                # Some minions (e.g. Loot Hoarder) carry the DR tag in
                # data but `has_deathrattle` only flips true once the
                # minion enters play. Fall back to reading the script
                # definition directly.
                from .. import db as _db
                data = _db.get(c.id)
                if not data or not data.deathrattle:
                    continue
            candidates.append(c)
        if not candidates:
            return
        pick = source.game.random.choice(candidates)
        # Graft the picked minion's deathrattle actions onto Boneshredder
        # via additional_deathrattles. Read directly from the data card's
        # merged scripts (PlayableCard instances don't expose `.scripts`).
        scripts = getattr(pick.data, "deathrattle", None)
        if scripts:
            if not isinstance(scripts, (list, tuple)):
                scripts = (scripts,)
            for d in scripts:
                source.additional_deathrattles.append(d)
        for d in list(pick.additional_deathrattles):
            source.additional_deathrattles.append(d)


class _ScreamingBansheeHeal(TargetedAction):
    """After friendly hero gains Health, summon a Soul (ETC_522t) with
    Atk/Health equal to the heal amount."""

    TARGET = ActionArg()
    AMOUNT = ActionArg()

    def do(self, source, target, amount):
        if isinstance(amount, list):
            amount = amount[0] if amount else 0
        amount = int(amount)
        if amount <= 0:
            return
        ctrl = source.controller
        source.game.cheat_action(source, [Summon(ctrl, "ETC_522t")])
        souls = [m for m in ctrl.field if m.id == "ETC_522t"]
        if not souls:
            return
        soul = souls[-1]
        # ETC_522t base stats are 1/1. Buff by (amount - 1)/(amount - 1).
        delta = amount - 1
        if delta > 0:
            source.game.cheat_action(
                source,
                [Buff(soul, "ETC_522te", atk=delta, max_health=delta)],
            )


class _DeathMetalKnightStamp(TargetedAction):
    """Death Metal Knight — if controller healed their hero this turn,
    stamp all in-hand copies as card_costs_health. Fires from Hand.events
    on Heal(FRIENDLY_HERO)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.card_costs_health = True


class _DeathMetalKnightUnstamp(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        target.card_costs_health = False


class _HarmonicMetalBuff(TargetedAction):
    """Buff 4 random minions in the controller's hand by +2/+2."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        minions = [c for c in ctrl.hand if c.type == CardType.MINION]
        if not minions:
            return
        picks = source.game.random.sample(minions, min(4, len(minions)))
        for m in picks:
            source.game.cheat_action(source, [Buff(m, "ETC_427e")])


class _DeathGrowlSpread(TargetedAction):
    """Death Growl — copy the chosen minion's Deathrattle onto its
    left/right neighbours."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target.type != CardType.MINION:
            return
        field = target.controller.field
        idx = field.index(target) if target in field else -1
        if idx < 0:
            return
        neighbours = []
        if idx > 0:
            neighbours.append(field[idx - 1])
        if idx < len(field) - 1:
            neighbours.append(field[idx + 1])
        # Build the deathrattle set from target. Instances expose the
        # script class via `target.data` (the merged CardDB entry), whose
        # `.deathrattle` attr is the (already-tuple-wrapped) action list.
        dr_set = []
        if target.has_deathrattle and getattr(target.data, "deathrattle", None):
            scripts = target.data.deathrattle
            if not isinstance(scripts, (list, tuple)):
                scripts = (scripts,)
            for d in scripts:
                dr_set.append(d)
        for d in target.additional_deathrattles:
            dr_set.append(d)
        if not dr_set:
            return
        for n in neighbours:
            for d in dr_set:
                n.additional_deathrattles.append(d)


class _ArcaniteRipperDeathrattle(TargetedAction):
    """Summon a (N/N) Lifesteal Undead where N is the absolute change in
    hero health while equipped. Uses ETC_423t (1/1 Lifesteal Undead) and
    buffs by (N-1)/(N-1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        n = max(1, int(getattr(source, "_health_changes_while_equipped", 1)))
        source.game.cheat_action(source, [Summon(ctrl, "ETC_423t")])
        bodies = [m for m in ctrl.field if m.id == "ETC_423t"]
        if not bodies:
            return
        body = bodies[-1]
        delta = n - 1
        if delta > 0:
            source.game.cheat_action(
                source,
                [Buff(body, "ETC_423te", atk=delta, max_health=delta)],
            )


class _ArcaniteRipperListener(TargetedAction):
    """While Arcanite Ripper is equipped, every change to hero health
    bumps a per-weapon counter — both heals and damage. Fires after
    Heal(FRIENDLY_HERO) and Damage(FRIENDLY_HERO)."""

    TARGET = ActionArg()

    def do(self, source, target):
        weapon = source.controller.weapon
        if weapon is None or weapon.id != "ETC_423":
            return
        weapon._health_changes_while_equipped = (
            getattr(weapon, "_health_changes_while_equipped", 0) + 1
        )


class _HardcoreCultistFinale(TargetedAction):
    """Hardcore Cultist — Battlecry: Deal 2 damage. Finale: To all enemies.
    The base play is just Hit(TARGET, 2); the Finale variant fans 2 damage
    onto every enemy character instead. We implement as a custom action
    rather than mixing FINALE inline so that the Finale branch *replaces*
    rather than *augments* the base hit."""

    TARGET = ActionArg()

    def do(self, source, target):
        if source.play_finale:
            # Hit all enemy characters for 2.
            for c in list(source.controller.opponent.characters):
                source.game.cheat_action(source, [Hit(c, 2)])
        else:
            source.game.cheat_action(source, [Hit(target, 2)])


class _MoshPitGiveReborn(TargetedAction):
    """Mosh Pit (Location) — spend 3 Corpses, give a friendly minion Reborn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.corpses < 3:
            return
        ctrl.corpses -= 3
        source.game.cheat_action(source, [GiveReborn(target)])


##
# Minions


# Battlecry: Deal 2 damage. Finale: To all enemies.
class ETC_209:
    """Hardcore Cultist"""

    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _HardcoreCultistFinale(TARGET)


# Battlecry: Spend 5 Corpses to trigger and gain the Deathrattle of a
# random friendly minion that died this game.
class ETC_428:
    """Boneshredder"""

    play = (CORPSES >= 5) & (
        SpendCorpses(CONTROLLER, 5),
        _BoneshredderStealDeathrattle(SELF),
    )


# Lifesteal. After your hero gains Health, summon a Soul with that much
# Attack and Health.
class ETC_522:
    """Screaming Banshee"""

    events = Heal(FRIENDLY_HERO).on(
        _ScreamingBansheeHeal(SELF, Heal.AMOUNT)
    )


class ETC_522t:
    """Die-Hard Fan"""

    # 1/1 token; stats from data.


# Taunt. Costs Health instead of Mana if your hero was healed this turn.
class ETC_523:
    """Death Metal Knight"""

    class Hand:
        # When the controller's hero takes a heal, stamp this card; when
        # the turn ends, clear the stamp. Self-targeted via Hand.events.
        events = (
            Heal(FRIENDLY_HERO).on(_DeathMetalKnightStamp(SELF)),
            OWN_TURN_END.on(_DeathMetalKnightUnstamp(SELF)),
        )


# Deathrattle: Summon a 9/9 Blight Boar with Charge and Taunt.
class ETC_526:
    """Cage Head"""

    deathrattle = Summon(CONTROLLER, "ETC_526t")


class ETC_526t:
    """Blight Boar"""

    # 9/9 Charge + Taunt; tags in data.


##
# Spells


# Lifesteal. Deal $6 damage. Summon 3 2/2 Souls. (Randomly improved by Corpses spent.)
# Approximation: fixed 6 to all enemies + 3 2/2 souls. Real card scales by spent corpses.
class _ClimacticExplosion(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Damage: 6 to all enemies (approximation; real version randomly
        # picks one of several improvement buckets based on lifetime
        # corpses spent — TODO upgrade once we wire that ladder).
        for c in list(ctrl.opponent.characters):
            source.game.cheat_action(source, [Hit(c, 6)])
        # Summon 3 2/2 Souls — use ETC_522t (Die-Hard Fan) as the soul
        # token, buffed to 2/2.
        slots = max(0, 7 - len(ctrl.field))
        for _ in range(min(3, slots)):
            source.game.cheat_action(source, [Summon(ctrl, "ETC_522t")])
            souls = [m for m in ctrl.field if m.id == "ETC_522t"]
            if souls:
                source.game.cheat_action(
                    source,
                    [Buff(souls[-1], "ETC_522te", atk=1, max_health=1)],
                )


class ETC_210:
    """Climactic Necrotic Explosion"""

    play = _ClimacticExplosion(CONTROLLER)
    tags = {GameTag.LIFESTEAL: True}


# Choose a minion. Spread its Deathrattle to adjacent minions.
class ETC_424:
    """Death Growl"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _DeathGrowlSpread(TARGET)


# Give 4 random minions in your hand +2/+2.
class ETC_427:
    """Harmonic Metal"""

    play = _HarmonicMetalBuff(CONTROLLER)


##
# Weapons


# Deathrattle: Summon a @/@ Lifesteal Undead.
class ETC_423:
    """Arcanite Ripper"""

    events = (
        Heal(FRIENDLY_HERO).on(_ArcaniteRipperListener(SELF)),
        Damage(FRIENDLY_HERO).on(_ArcaniteRipperListener(SELF)),
    )
    deathrattle = _ArcaniteRipperDeathrattle(SELF)


class ETC_423t:
    """Blighthead"""

    # 1/1 Lifesteal Undead; tags in data.


##
# Locations


# Spend 3 Corpses to give a friendly minion Reborn.
class ETC_533:
    """Mosh Pit"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    activate = _MoshPitGiveReborn(TARGET)


##
# Engine-internal enchantments


@custom_card
class ETC_522te:
    tags = {
        GameTag.CARDNAME: "Die-Hard Fan",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ETC_423te:
    tags = {
        GameTag.CARDNAME: "Blighthead",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class ETC_427e:
    # In-data buff "Harmonic Presence" — +2/+2 not parsed from data.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class ETC_424e:
    # In-data buff "Wall of Death" — marker only; the deathrattle copy is
    # done via Python-side additional_deathrattles, not a tag.
    pass


class ETC_428e:
    # In-data buff "Shredding" — same as above; marker only.
    pass
