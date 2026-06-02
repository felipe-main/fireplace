from ..utils import *
from hearthstone.enums import SpellSchool


##
# Across the Timeways — Paladin "Aura" support
#
# Like Whizbang's Workshop, "Aura" spells (GameTag PALADIN_AURA = 3429) read as
# ordinary SPELLs whose `play` installs a controller-attached enchantment that
# fires an effect on OWN_TURN_END and ticks down `_aura_turns_left`, destroying
# itself once the counter reaches zero ("Lasts @ turns"). The data does not ship
# a controller-aura enchant id for these, so we register custom enchants via
# @custom_card. The base duration is 3 turns (TAG_SCRIPT_DATA_NUM_1 = 3).

_AURA_TAG = 3429  # PALADIN_AURA


def _is_aura_card(entity):
    data = getattr(entity, "data", None)
    if data is None:
        return False
    return bool(data.tags.get(_AURA_TAG, 0))


# Selector matching Aura cards (used by Gelbin's battlecry to scan the deck).
AURA_CARD = FuncSelector(
    lambda entities, source: [e for e in entities if _is_aura_card(e)]
)


class _AuraCountdown(TargetedAction):
    """Generic N-turn aura countdown. Call with the enchantment entity as
    TARGET. Decrements `_aura_turns_left` and destroys the enchant once the
    counter hits zero. The enchant initialises `_aura_turns_left` in apply()."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        left = getattr(enchant, "_aura_turns_left", 0) - 1
        enchant._aura_turns_left = max(0, left)
        if left <= 0:
            enchant.game.cheat_action(enchant, [Destroy(enchant)])


class _GnomishAuraHeal(TargetedAction):
    """Gnomish Aura tick — restore 4 Health to all the controller's
    characters (hero + friendly minions) at end of turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        ctrl = enchant.controller
        chars = [ctrl.hero] + list(ctrl.field)
        enchant.game.cheat_action(enchant, [Heal(chars, 4)])


class _MekkatorqueAuraBuff(TargetedAction):
    """Mekkatorque's Aura tick — give a random friendly minion +4/+4 and
    Divine Shield at end of turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        ctrl = enchant.controller
        if not ctrl.field:
            return
        pick = enchant.game.random.choice(list(ctrl.field))
        enchant.game.cheat_action(
            enchant, [Buff(pick, "TIME_009t2e"), GiveDivineShield(pick)]
        )


class _ChronologicalAuraSummon(TargetedAction):
    """Chronological Aura tick — summon a 3/5 Dragon with Taunt at end of
    turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        enchant.game.cheat_action(
            enchant, [Summon(enchant.controller, "TIME_700t")]
        )


##
# TIME_009t1 — Gnomish Aura
# [x]Tradeable. At the end of your turn, restore #4 Health to all your
# characters. Lasts @ turns.


class TIME_009t1:
    """Gnomish Aura"""

    play = Buff(CONTROLLER, "TIME_009t1_aura")

    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class TIME_009t1_aura:
    """Gnomish Aura"""

    tags = {
        GameTag.CARDNAME: "Gnomish Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [
        OWN_TURN_END.on(_GnomishAuraHeal(SELF)),
        OWN_TURN_END.on(_AuraCountdown(SELF)),
    ]

    def apply(self, target):
        self._aura_turns_left = 3


##
# TIME_009t2 — Mekkatorque's Aura
# [x]Tradeable. At the end of your turn, give a random friendly minion +4/+4
# and Divine Shield. Lasts @ turns.


class TIME_009t2:
    """Mekkatorque's Aura"""

    play = Buff(CONTROLLER, "TIME_009t2_aura")

    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class TIME_009t2_aura:
    """Mekkatorque's Aura"""

    tags = {
        GameTag.CARDNAME: "Mekkatorque's Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [
        OWN_TURN_END.on(_MekkatorqueAuraBuff(SELF)),
        OWN_TURN_END.on(_AuraCountdown(SELF)),
    ]

    def apply(self, target):
        self._aura_turns_left = 3


class TIME_009t2e:
    """For Gnomeregan!"""

    # +4/+4 (data enchant carries no stats — supply them here).
    tags = {GameTag.ATK: 4, GameTag.HEALTH: 4}


##
# TIME_009 — Gelbin of Tomorrow
# [x]Fabled Battlecry: Put one of each Aura from your deck into the battlefield.


class _GelbinPutAuras(TargetedAction):
    """Gelbin — cast one of each distinct Aura card from the controller's
    deck. The aura spells install their controller-attached enchant when
    cast (their `play` effect)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen = set()
        picks = []
        for card in list(ctrl.deck):
            if _is_aura_card(card) and card.id not in seen:
                seen.add(card.id)
                picks.append(card)
        for card in picks:
            source.game.cheat_action(source, [CastSpell(card)])


class TIME_009:
    """Gelbin of Tomorrow"""

    play = _GelbinPutAuras(SELF)


##
# TIME_015 — Hardlight Protector
# [x]Divine Shield Battlecry: Restore #3 Health to your hero and give them
# Divine Shield.


class TIME_015:
    """Hardlight Protector"""

    play = Heal(FRIENDLY_HERO, 3), GiveDivineShield(FRIENDLY_HERO)


##
# TIME_016 — Neon Innovation
# Discover a Paladin Mech from the past. Give it +5/+5.


class TIME_016:
    """Neon Innovation"""

    play = Discover(
        CONTROLLER,
        RandomMinion(card_class=CardClass.PALADIN, race=Race.MECHANICAL, from_past=True),
    ).then(Give(CONTROLLER, Discover.CARD), Buff(Discover.CARD, "TIME_016e"))


class TIME_016e:
    """Neon Sign"""

    tags = {GameTag.ATK: 5, GameTag.HEALTH: 5}


##
# TIME_017 — Tankgineer
# [x]Divine Shield Deathrattle: Summon a 7/7 Tank with Divine Shield.


class TIME_017:
    """Tankgineer"""

    deathrattle = Summon(CONTROLLER, "TIME_017t")


@custom_card
class TIME_017t:
    """Tank"""

    # 7/7 with Divine Shield. Not shipped in data, so register it here.
    tags = {
        GameTag.CARDNAME: "Tank",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.ATK: 7,
        GameTag.HEALTH: 7,
        GameTag.DIVINE_SHIELD: True,
        GameTag.CARDRACE: Race.MECHANICAL,
    }


##
# TIME_018 — Mend the Timeline
# Rewind Get 2 random Holy spells. Restore Health to your hero equal to their
# Costs. (Rewind handling is engine-automatic — only the base effect here.)


class _MendTheTimeline(TargetedAction):
    """Get 2 random Holy spells; heal the hero by the sum of their Costs."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        total_cost = 0
        for _ in range(2):
            pick = RandomSpell(spell_school=SpellSchool.HOLY).evaluate(source)
            if isinstance(pick, list):
                pick = pick[0] if pick else None
            if not pick:
                continue
            source.game.cheat_action(source, [Give(ctrl, pick)])
            card_id = pick if isinstance(pick, str) else getattr(pick, "id", None)
            if card_id and card_id in db:
                total_cost += db[card_id].cost or 0
        if total_cost:
            source.game.cheat_action(source, [Heal(ctrl.hero, total_cost)])


class TIME_018:
    """Mend the Timeline"""

    play = _MendTheTimeline(SELF)


##
# TIME_019 — Manifested Timeways
# Battlecry: If you control an Aura, deal 3 damage to all enemies.


def _controls_aura(source):
    """True if the controller has an active aura enchantment attached
    (carrying _aura_turns_left)."""
    for buff in getattr(source.controller, "buffs", []):
        if hasattr(buff, "_aura_turns_left"):
            return True
    return False


class _ManifestedDamage(TargetedAction):
    """If you control an Aura, deal 3 damage to all enemies."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not _controls_aura(source):
            return
        opp = source.controller.opponent
        enemies = [opp.hero] + list(opp.field)
        source.game.cheat_action(source, [Hit(enemies, 3)])


class TIME_019:
    """Manifested Timeways"""

    play = _ManifestedDamage(SELF)


##
# TIME_043 — PMM Infinitizer
# Battlecry: Set a friendly minion's Attack and Health to 8. It can't attack
# heroes this turn.


class TIME_043:
    """PMM Infinitizer"""

    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
    }
    play = Buff(TARGET, "TIME_043e"), Buff(TARGET, "TIME_043e2")


@custom_card
class TIME_043e:
    """Infinitized"""

    # Dynamic stat enchant — set Attack and Health to exactly 8.
    tags = {
        GameTag.CARDNAME: "Infinitized",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }

    def apply(self, target):
        target.damage = 0

    def atk(self, i):
        return 8

    def max_health(self, i):
        return 8


class TIME_043e2:
    """Pacifitized"""

    # Can't attack heroes this turn (one-turn effect in data).
    tags = {GameTag.CANNOT_ATTACK_HEROES: True, GameTag.TAG_ONE_TURN_EFFECT: True}


##
# TIME_044 — Past Gnomeregan (Location)
# [x]Give a minion +2/+1. Advance to the present!
#
# Each Gnomeregan location has 3 durability and buffs a minion on use. On its
# final use (durability about to hit 0) it advances to the next stage (Present,
# then Future). Locations don't carry the DEATHRATTLE GameTag in data, so the
# engine's Death.do deathrattle pipeline never fires for them — instead the
# upgrade is queued from the activate script on the last charge (UseLocation
# decrements durability *after* the play script, so durability == 1 here means
# this is the last use).


class _GnomereganAdvance(TargetedAction):
    """If this is the location's final charge, summon the next Gnomeregan
    stage after the current location is consumed."""

    TARGET = ActionArg()
    NEXT = ActionArg()

    def do(self, source, target, next_id):
        if isinstance(next_id, (list, tuple)):
            next_id = next_id[0] if next_id else None
        if not next_id:
            return
        # Pre-decrement durability: == 1 means this use will destroy it.
        if getattr(source, "durability", 0) <= 1:
            source.game.cheat_action(source, [Summon(source.controller, next_id)])


class TIME_044:
    """Past Gnomeregan"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "TIME_044e"), _GnomereganAdvance(SELF, "TIME_044t1")


class TIME_044e:
    """Gnomish Strength"""

    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


class TIME_044t1:
    """Present Gnomeregan"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(TARGET, "TIME_044e"),
        Buff(TARGET, "TIME_044t1e"),
        _GnomereganAdvance(SELF, "TIME_044t2"),
    )


@custom_card
class TIME_044t1e:
    """Leper Strength"""

    # Carrier of "Deathrattle: Deal 2 damage to the enemy hero."
    tags = {
        GameTag.CARDNAME: "Leper Strength",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Hit(ENEMY_HERO, 2)


class TIME_044t2:
    """Future Gnomeregan"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(TARGET, "TIME_044e"),
        GiveDivineShield(TARGET),
        Buff(TARGET, "TIME_044t1e"),
    )


##
# TIME_700 — Chronological Aura
# At the end of your turn, summon a 3/5 Dragon with Taunt. Lasts @ turns.


class TIME_700:
    """Chronological Aura"""

    play = Buff(CONTROLLER, "TIME_700_aura")

    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class TIME_700_aura:
    """Chronological Aura"""

    tags = {
        GameTag.CARDNAME: "Chronological Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [
        OWN_TURN_END.on(_ChronologicalAuraSummon(SELF)),
        OWN_TURN_END.on(_AuraCountdown(SELF)),
    ]

    def apply(self, target):
        self._aura_turns_left = 3


class TIME_700t:
    """Chronological Drake"""

    # 3/5 Dragon with Taunt (vanilla token — Taunt comes from data).


##
# TIME_706 — The Fins Beyond Time
# [x]Battlecry: Replace your hand with your starting hand. Swap back at the end
# of your turn.


class _FinsSwapHand(TargetedAction):
    """Replace the controller's current hand with copies of their starting
    hand, stashing the live hand cards (to setaside) so they can be restored
    at end of turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        starting = list(getattr(ctrl, "starting_hand", []) or [])
        if not starting:
            return
        # Stash the current hand (move live cards out to setaside).
        current = list(ctrl.hand)
        ctrl._time706_stashed_hand = current
        for card in current:
            card.zone = Zone.SETASIDE
        # Materialise copies of the starting hand into the now-empty hand.
        for card in starting:
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            new = ctrl.card(card.id, zone=Zone.SETASIDE)
            new.zone = Zone.HAND


class _FinsSwapBack(TargetedAction):
    """Swap back at end of turn — discard the starting-hand copies and restore
    the stashed live hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        ctrl = enchant.controller
        stashed = list(getattr(ctrl, "_time706_stashed_hand", []))
        # Clear the starting-hand copies currently in hand.
        for card in list(ctrl.hand):
            card.zone = Zone.SETASIDE
        # Restore the stashed live hand.
        for card in stashed:
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            card.zone = Zone.HAND
        ctrl._time706_stashed_hand = []
        enchant.game.cheat_action(enchant, [Destroy(enchant)])


class TIME_706:
    """The Fins Beyond Time"""

    play = _FinsSwapHand(SELF), Buff(CONTROLLER, "TIME_706e3")


@custom_card
class TIME_706e3:
    """Beyond Time"""

    tags = {
        GameTag.CARDNAME: "Beyond Time",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [OWN_TURN_END.on(_FinsSwapBack(SELF))]


class TIME_706e2:
    """Time Altered"""

    # Cleanup enchant for TIME_706 — no mechanical effect in our engine.
    tags = {}


##
# END_012 — Hand of Infinity (Weapon, 4/2, cost 3)
# [x]Can't attack heroes. Battlecry: Set this weapon's Attack to INFINITY this
# turn!
#
# CANNOT_ATTACK_HEROES is baked into the weapon's data tags. The battlecry buffs
# the weapon with END_012e (a TAG_ONE_TURN_EFFECT enchant already in data) which
# sets Attack to INFINITY for the current turn (precedent: TIME_024e in neutral).


class END_012:
    """Hand of Infinity"""

    # "Can't attack heroes" lives in the weapon's data under an unmapped tag
    # (321), so the engine never reads it. We restore it on the weapon entity
    # via the mapped GameTag.CANNOT_ATTACK_HEROES. NOTE: the engine's
    # attack-target filter checks `cannot_attack_heroes` on the attacking
    # *character* (the hero), and Hero does not aggregate this flag from its
    # weapon — so hero-level enforcement is an engine gap we don't patch here.
    # The flag is correct on the weapon entity itself.
    tags = {GameTag.CANNOT_ATTACK_HEROES: True}
    play = Buff(SELF, "END_012e")


class END_012e:
    """Infinite Sharpness"""

    # Attack set to INFINITY this turn (TAG_ONE_TURN_EFFECT carried by data).
    atk = SET(2147483647)
