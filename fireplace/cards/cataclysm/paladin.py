from ..utils import *
from hearthstone.enums import SpellSchool


##
# Cataclysm — Paladin
#
# Theme: Dragons + "end of turn effects". Several minions in this set carry an
# end-of-turn (OWN_TURN_END) effect; two cards interact with those effects in a
# general way:
#   * Inspiring Maul (CATA_472) — "Trigger a random friendly minion's end of
#     turn effect."
#   * Sandfury Aura (CATA_480) — "Your minions' end of turn effects trigger
#     twice."
#
# The engine has no general "this minion has an end-of-turn effect" concept, so
# we build a small registry: every minion with an EOT effect registers a factory
# under its card id in ``_EOT_EFFECTS`` (mapping id -> callable(minion) ->
# action-list) and exposes its OWN_TURN_END trigger via ``_RunEot(SELF)``.
# ``_RunEot`` runs the effect once, plus one extra time per active Sandfury Aura
# (so "trigger twice" composes for every registered minion). Inspiring Maul's
# deathrattle picks a random friendly minion whose id is in the registry and runs
# its effect once via ``cheat_action``.


# id -> callable(minion) -> list[Action]
_EOT_EFFECTS = {}


def _register_eot(card_id):
    def deco(fn):
        _EOT_EFFECTS[card_id] = fn
        return fn

    return deco


def _sandfury_extra_triggers(player):
    """Number of *extra* times EOT effects fire this turn (one per active
    Sandfury Aura attached to the controller)."""
    n = 0
    for buff in getattr(player, "buffs", []):
        if getattr(buff, "_is_sandfury_aura", False):
            n += 1
    return n


class _RunEot(TargetedAction):
    """Run a registered minion's end-of-turn effect. Fires once normally, plus
    one extra time per active Sandfury Aura (the controller's "trigger twice")."""

    TARGET = ActionArg()

    def do(self, source, target):
        fn = _EOT_EFFECTS.get(source.id)
        if fn is None:
            return
        times = 1 + _sandfury_extra_triggers(source.controller)
        for _ in range(times):
            actions = fn(source)
            if actions:
                source.game.cheat_action(source, list(actions))


##
# CATA_432 — Chromatus  (Colossal +4, 8/8)
# Colossal +4. Taunt, Lifesteal, Elusive, Divine Shield.
#
# The four heads (limbs CATA_432t1..t4) are summoned automatically by the
# engine's Colossal hook. Each head's deathrattle removes the matching keyword
# from the Chromatus body. The body itself is a vanilla 8/8 whose keywords come
# from its data tags; we only need a valid docstring + the keyword tags (already
# in data).


class CATA_432:
    """Chromatus"""

    # Keywords are baked into data tags (Taunt/Lifesteal/Elusive/Divine Shield);
    # limbs are engine-summoned. No script body required.


def _find_chromatus(source):
    """Locate the Chromatus body on the limb's controller's board."""
    for minion in source.controller.field:
        if minion.id == "CATA_432":
            return minion
    return None


class _RemoveChromatusKeyword(TargetedAction):
    """A head's deathrattle: remove one keyword tag from the Chromatus body."""

    TARGET = ActionArg()
    TAG = ActionArg()

    def do(self, source, target, tag):
        if isinstance(tag, (list, tuple)):
            tag = tag[0]
        body = _find_chromatus(source)
        if body is not None:
            body.tags[tag] = False


class CATA_432t1:
    """Green Head of Chromatus"""

    # Taunt. Deathrattle: Remove Taunt from Chromatus.
    deathrattle = _RemoveChromatusKeyword(SELF, GameTag.TAUNT)


class CATA_432t2:
    """Red Head of Chromatus"""

    # Lifesteal. Deathrattle: Remove Lifesteal from Chromatus.
    deathrattle = _RemoveChromatusKeyword(SELF, GameTag.LIFESTEAL)


class CATA_432t3:
    """Blue Head of Chromatus"""

    # Elusive. Deathrattle: Remove Elusive from Chromatus.
    # NOTE: the engine's targeting check reads Elusive off the *static* card
    # data (target.data.tags[GameTag.ELUSIVE]), which can't be toggled per
    # entity, so clearing the live tag here is cosmetic — the body stays
    # untargetable. Documented approximation (the other three heads remove
    # Taunt / Lifesteal / Divine Shield correctly, as those read live tags).
    deathrattle = _RemoveChromatusKeyword(SELF, GameTag.ELUSIVE)


class CATA_432t4:
    """Bronze Head of Chromatus"""

    # Divine Shield. Deathrattle: Remove Divine Shield from Chromatus.
    deathrattle = _RemoveChromatusKeyword(SELF, GameTag.DIVINE_SHIELD)


##
# CATA_472 — Inspiring Maul  (Weapon 2/2)
# Deathrattle: Trigger a random friendly minion's end of turn effect.


class _InspiringMaulTrigger(TargetedAction):
    """Pick a random friendly minion that has a registered end-of-turn effect
    and run it once."""

    TARGET = ActionArg()

    def do(self, source, target):
        candidates = [m for m in source.controller.field if m.id in _EOT_EFFECTS]
        if not candidates:
            return
        pick = source.game.random.choice(candidates)
        fn = _EOT_EFFECTS[pick.id]
        actions = fn(pick)
        if actions:
            source.game.cheat_action(source, list(actions))


class CATA_472:
    """Inspiring Maul"""

    deathrattle = _InspiringMaulTrigger(SELF)


##
# CATA_473 — Nozdormu, Bronze Aspect  (5/4/4)
# At the end of your turn, give your minions Divine Shield. Any that already had
# one gain +3/+3 instead.


class _NozdormuEot(TargetedAction):
    """For each friendly minion: if it already has Divine Shield, buff +3/+3;
    otherwise grant Divine Shield."""

    TARGET = ActionArg()

    def do(self, source, target):
        for minion in list(source.controller.field):
            if minion.divine_shield:
                source.game.cheat_action(source, [Buff(minion, "CATA_473e")])
            else:
                source.game.cheat_action(source, [GiveDivineShield(minion)])


@_register_eot("CATA_473")
def _nozdormu_eot(minion):
    return [_NozdormuEot(minion)]


class CATA_473:
    """Nozdormu, Bronze Aspect"""

    events = OWN_TURN_END.on(_RunEot(SELF))


class CATA_473e:
    """Nozdormu's Nimbus"""

    # +3/+3.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


##
# CATA_474 — Spearheart Sentry  (4/3/4, Dragon)
# At the end of your turn, get a random Holy Spell. Reduce its Cost by (3).


class _SpearheartEot(TargetedAction):
    """Give a random Holy spell, reduced by (3)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(
            source,
            [
                Give(source.controller, RandomSpell(spell_school=SpellSchool.HOLY)).then(
                    Buff(Give.CARD, "CATA_474e")
                )
            ],
        )


@_register_eot("CATA_474")
def _spearheart_eot(minion):
    return [_SpearheartEot(minion)]


class CATA_474:
    """Spearheart Sentry"""

    events = OWN_TURN_END.on(_RunEot(SELF))


@custom_card
class CATA_474e:
    """Bronze Discount"""

    # Reduce Cost by (3). No data enchant ships for this, so register it.
    tags = {
        GameTag.CARDNAME: "Bronze Discount",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


##
# CATA_475 — Scalebreaker Bulwark  (6/3/6)
# At the end of your turn, deal 2 damage to all enemies.


@_register_eot("CATA_475")
def _scalebreaker_eot(minion):
    return [Hit(ENEMY_CHARACTERS, 2)]


class CATA_475:
    """Scalebreaker Bulwark"""

    events = OWN_TURN_END.on(_RunEot(SELF))


##
# CATA_477 — Chamber of Aspects  (Location, 2 durability)
# Choose a minion in your hand. Give it +2/+2.
#
# Engine hand-targeting is unsupported; approximate by buffing a RANDOM minion in
# the controller's hand (precedent: REV_511). Noted approximation.


class CATA_477:
    """Chamber of Aspects"""

    activate = Buff(RANDOM(FRIENDLY_HAND + MINION), "CATA_477e")


class CATA_477e:
    """Aspects' Blessing"""

    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


##
# CATA_478 — Bronze Redeemer  (5/3/3)
# At the end of your turn, summon a Dragon with stats equal to this minion's.


class _BronzeRedeemerEot(TargetedAction):
    """Summon a Bronze Brute, then set its Attack/Health to match the
    Redeemer's current stats."""

    TARGET = ActionArg()

    def do(self, source, target):
        atk = source.atk
        health = source.health
        source.game.cheat_action(source, [Summon(source.controller, "CATA_478t")])
        token = None
        for minion in reversed(source.controller.field):
            if minion.id == "CATA_478t" and not getattr(minion, "_bronze_set", False):
                token = minion
                break
        if token is None:
            return
        token._bronze_set = True
        token._bronze_atk = atk
        token._bronze_health = health
        source.game.cheat_action(source, [Buff(token, "CATA_478te")])


@_register_eot("CATA_478")
def _bronze_redeemer_eot(minion):
    return [_BronzeRedeemerEot(minion)]


class CATA_478:
    """Bronze Redeemer"""

    events = OWN_TURN_END.on(_RunEot(SELF))


class CATA_478t:
    """Bronze Brute"""

    # Vanilla 1/1 Dragon token; stats are overwritten by CATA_478te.


@custom_card
class CATA_478te:
    """Bronze Might"""

    # Sets the Brute's Attack/Health to the Redeemer's stats (read off the
    # token's per-minion attrs stashed at summon time).
    tags = {
        GameTag.CARDNAME: "Bronze Might",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }

    def apply(self, target):
        target.damage = 0

    def atk(self, i):
        return getattr(self.owner, "_bronze_atk", i)

    def max_health(self, i):
        return getattr(self.owner, "_bronze_health", i)


##
# CATA_479 — Flight Maneuvers  (Spell, Shatter, cost 4)
# Shatter:
#   * CATA_479t  (Shattered): Summon two 4/2 Drakes.
#   * CATA_479t2 (Shattered): Give your minions +1/+1 and Divine Shield.
#
# The engine splits the SHATTER parent into its two halves when DRAWN, so the
# parent never resolves. We implement the two half tokens. The Drake token is
# CATA_479t3 (Sky Drake, 4/2 Dragon).


class CATA_479:
    """Flight Maneuvers"""

    # SHATTER parent — never resolves directly; split into halves on draw.


class CATA_479t:
    """Flight Maneuvers"""

    # Shattered: Summon two 4/2 Drakes.
    play = Summon(CONTROLLER, "CATA_479t3") * 2


class _FlightManeuversBuff(TargetedAction):
    """Give all friendly minions +1/+1 and Divine Shield."""

    TARGET = ActionArg()

    def do(self, source, target):
        for minion in list(source.controller.field):
            source.game.cheat_action(
                source, [Buff(minion, "CATA_479e"), GiveDivineShield(minion)]
            )


class CATA_479t2:
    """Flight Maneuvers"""

    # Shattered: Give your minions +1/+1 and Divine Shield.
    play = _FlightManeuversBuff(SELF)


class CATA_479e:
    """Courageous"""

    # +1/+1 (Divine Shield granted separately).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class CATA_479t3:
    """Sky Drake"""

    # Vanilla 4/2 Dragon token.


##
# CATA_480 — Sandfury Aura  (Spell, cost 3, PALADIN_AURA)
# Your minions' end of turn effects trigger twice. Lasts 3 turns.
#
# Installs a controller-attached aura enchant flagged ``_is_sandfury_aura`` that
# the EOT registry reads to add an extra trigger. Counts down over 3 turns (the
# extra turn from Gelbin's Triumph is honoured via ``_next_aura_bonus_turns``).


class _AuraCountdown(TargetedAction):
    """Decrement the aura's turn counter; destroy it once it reaches zero."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        left = getattr(enchant, "_aura_turns_left", 0) - 1
        enchant._aura_turns_left = max(0, left)
        if left <= 0:
            enchant.game.cheat_action(enchant, [Destroy(enchant)])


class CATA_480:
    """Sandfury Aura"""

    play = Buff(CONTROLLER, "CATA_480_aura")

    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class CATA_480_aura:
    """Sandfury Aura"""

    tags = {
        GameTag.CARDNAME: "Sandfury Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    # Only counts down (the doubling is read live off this enchant by _RunEot).
    events = [OWN_TURN_END.on(_AuraCountdown(SELF))]

    def apply(self, target):
        self._is_sandfury_aura = True
        bonus = getattr(target, "_next_aura_bonus_turns", 0)
        target._next_aura_bonus_turns = 0
        self._aura_turns_left = 3 + bonus


##
# CATA_621 — Gelbin's Triumph  (Spell, cost 1)
# Get a random Paladin Aura. It lasts an additional turn.


_PALADIN_AURA_TAG = 3429  # PALADIN_AURA


def _paladin_aura_ids():
    ids = []
    for cid, c in db.items():
        if c.tags.get(_PALADIN_AURA_TAG, 0) and c.collectible:
            ids.append(cid)
    return ids


class _GelbinsTriumph(TargetedAction):
    """Give a random collectible Paladin Aura card, and mark the controller so
    the next aura they install lasts one extra turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ids = _paladin_aura_ids()
        if not ids:
            return
        pick = source.game.random.choice(ids)
        ctrl._next_aura_bonus_turns = getattr(ctrl, "_next_aura_bonus_turns", 0) + 1
        source.game.cheat_action(source, [Give(ctrl, pick)])


class CATA_621:
    """Gelbin's Triumph"""

    play = _GelbinsTriumph(SELF)
