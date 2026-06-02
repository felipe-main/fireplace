from ..utils import *


##
# Whizbang's Workshop — "Aura" support
#
# In data, "Aura" cards carry an Aura marker tag. Patch 29.0 used raw GameTag
# 3374 (no enum name); Patch 30.0 re-tagged them as PALADIN_AURA (3429) and made
# them OBJECTIVE-type. Accept either so detection survives the data bump. They
# read as ordinary SPELLs whose play applies a controller-attached enchantment
# that ticks down `_aura_turns_left` on OWN_TURN_END and destroys itself at zero
# (mirrors the Titans / Showdown aura pattern).

_AURA_TAGS = (3374, 3429)


def _is_aura_card(entity):
    data = getattr(entity, "data", None)
    if data is None:
        return False
    return any(data.tags.get(tag, 0) for tag in _AURA_TAGS)


# Selector matching Aura cards (used by Trinket Artist's draw).
AURA = FuncSelector(
    lambda entities, source: [e for e in entities if _is_aura_card(e)]
)


class _AuraCountdown(TargetedAction):
    """Generic N-turn aura countdown helper. Call with the enchantment entity
    as TARGET. Decrements `_aura_turns_left` and destroys the enchant once the
    counter hits zero. The enchantment initialises `_aura_turns_left` in its
    apply() (base duration + any pending duration bonus carried by the card
    that created it)."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        left = getattr(enchant, "_aura_turns_left", 0) - 1
        enchant._aura_turns_left = max(0, left)
        if left <= 0:
            enchant.game.cheat_action(enchant, [Destroy(enchant)])


class _CrafterAuraSummon(TargetedAction):
    """Crafter's Aura tick: summon a random 6-Cost minion for the enchant's
    controller at end of turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = target
        if enchant is None:
            return
        pick = RandomMinion(cost=6).evaluate(enchant)
        if not pick:
            return
        enchant.game.cheat_action(enchant, [Summon(enchant.controller, pick)])


class _CardboardGolemBump(TargetedAction):
    """Cardboard Golem — increase the duration of Auras in the controller's
    hand, deck, and battlefield by 1.

    * Battlefield: active aura enchantments (carry `_aura_turns_left`) attached
      to the controller get +1 to their remaining duration.
    * Hand & deck: Aura *cards* (GameTag 3374) get a `_aura_duration_bonus`
      attribute bumped, which the aura's enchantment adds to its base duration
      when later played."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = target
        if player is None:
            return
        # Battlefield: active aura enchants attached to the player.
        for enchant in list(getattr(player, "buffs", [])):
            if hasattr(enchant, "_aura_turns_left"):
                enchant._aura_turns_left = getattr(enchant, "_aura_turns_left", 0) + 1
        # Hand + deck: bump the pending duration bonus on aura cards.
        for card in list(player.hand) + list(player.deck):
            if _is_aura_card(card):
                card._aura_duration_bonus = getattr(card, "_aura_duration_bonus", 0) + 1


class _TarimSetStats(TargetedAction):
    """Toy Captain Tarim — set the target minion's Attack and Health to this
    minion's current Attack and Health. Clears existing stat buffs first so the
    result is a true 'set', then applies a computed enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, (list, tuple)):
            target = target[0] if target else None
        if target is None or target.zone != Zone.PLAY:
            return
        if target.type != CardType.MINION:
            return
        atk = source.atk
        health = source.health
        target.clear_buffs()
        atk_delta = atk - target.atk
        hp_delta = health - target.max_health
        source.game.cheat_action(
            source,
            [Buff(target, "TOY_813e3", atk=atk_delta, max_health=hp_delta)],
        )


class _WindUpUpgrade(TargetedAction):
    """Wind-Up Enforcer — each Trade increases the number of copies the
    battlecry summons by 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        card = target
        if card is None:
            return
        card._windup_copies = getattr(card, "_windup_copies", 1) + 1


class _WindUpSummon(TargetedAction):
    """Wind-Up Enforcer battlecry — summon `_windup_copies` copies of this
    minion (base 1, upgraded via Trade)."""

    TARGET = ActionArg()

    def do(self, source, target):
        copies = getattr(source, "_windup_copies", 1)
        if copies <= 0:
            return
        source.game.cheat_action(source, [Summon(source.controller, "TOY_880") * copies])


##
# Spells


class TOY_716:
    """Flash Sale"""

    # Summon a 1/2 Mech with Divine Shield and Taunt. Give your minions +1/+2.
    play = (
        Summon(CONTROLLER, "GVG_085"),
        Buff(FRIENDLY_MINIONS, "TOY_716e"),
    )


class TOY_716e:
    """Amazing Savings"""

    # +1/+2 (data enchant carries no stats — supply them here).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class TOY_808:
    """Crafter's Aura"""

    # At the end of your turn, summon a random 6-Cost minion. Lasts @ turns.
    play = Buff(CONTROLLER, "TOY_808e")

    # Cosmetic: the printed "@" is the fixed 3-turn duration.
    def custom_cardtext(self):
        return self.data.description.replace("@", "3")

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


@custom_card
class TOY_808e:
    """Crafter's Aura"""

    # Controller-attached aura: at end of turn summon a random 6-Cost minion.
    # Lasts 3 turns (base), extended by Cardboard Golem.
    tags = {
        GameTag.CARDNAME: "Crafter's Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = [
        OWN_TURN_END.on(_CrafterAuraSummon(SELF)),
        OWN_TURN_END.on(_AuraCountdown(SELF)),
    ]

    def apply(self, target):
        bonus = getattr(self, "_aura_duration_bonus", 0)
        creator = getattr(self, "creator", None)
        if creator is not None:
            bonus += getattr(creator, "_aura_duration_bonus", 0)
        self._aura_turns_left = 3 + bonus


class _FancyPackagingBuff(TargetedAction):
    """Fancy Packaging — give the target +2/+3, but only if it has Divine
    Shield (the printed targeting restriction; the engine has no Divine-Shield
    PlayReq, so the gate is enforced here)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, (list, tuple)):
            target = target[0] if target else None
        if target is None or target.zone != Zone.PLAY:
            return
        if not target.divine_shield:
            return
        source.game.cheat_action(source, [Buff(target, "TOY_881e")])


class TOY_881:
    """Fancy Packaging"""

    # Give a minion with Divine Shield +2/+3.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _FancyPackagingBuff(TARGET)


class TOY_881e:
    """Vacuum Sealed"""

    # +2/+3 (data enchant carries no stats — supply them here).
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 3}


##
# Minions


class TOY_809:
    """Cardboard Golem"""

    # Battlecry: Increase the duration of Auras in your hand, deck, and
    # battlefield by 1.
    play = _CardboardGolemBump(CONTROLLER)


class TOY_811:
    """Tigress Plushy"""

    # Miniaturize. Rush, Lifesteal, Divine Shield (all from data tags).
    pass


class TOY_811t:
    """Tigress Plushy"""

    # Mini. Rush, Lifesteal, Divine Shield (all from data tags).
    pass


class TOY_812:
    """Pipsi Painthoof"""

    # Deathrattle: Summon a random Divine Shield, Rush, and Taunt minion from
    # your deck.
    deathrattle = Summon(
        CONTROLLER,
        RANDOM(FRIENDLY_DECK + MINION + DIVINE_SHIELD + RUSH + TAUNT),
    )


class TOY_813:
    """Toy Captain Tarim"""

    # Miniaturize. Taunt. Battlecry: Set a minion's Attack and Health to this
    # minion's.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
    }
    play = _TarimSetStats(TARGET)


class TOY_813t:
    """Toy Captain Tarim"""

    # Mini. Taunt. Battlecry: Set a minion's Attack and Health to this minion's.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
    }
    play = _TarimSetStats(TARGET)


class TOY_880:
    """Wind-Up Enforcer"""

    # Tradeable. Battlecry: Summon @ copies of this minion. (Trade to upgrade!)
    play = _WindUpSummon(SELF)
    trade = _WindUpUpgrade(SELF)

    # Cosmetic: "@" is the current copy count (1 base, +1 per Trade), and the
    # "|4(copy, copies)" directive picks singular vs plural off that count.
    def custom_cardtext(self):
        import re

        count = getattr(self, "_windup_copies", 1)
        text = self.data.description.replace("@", str(count))
        text = re.sub(
            r"\|\d+\(([^,]*),\s*([^)]*)\)",
            lambda m: m.group(1) if count == 1 else m.group(2),
            text,
        )
        return text

    tags = {enums.CUSTOM_CARDTEXT: custom_cardtext}


class TOY_882:
    """Trinket Artist"""

    # Battlecry: Draw a Divine Shield minion and an Aura.
    play = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + DIVINE_SHIELD)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + AURA)),
    )


##
# Weapons


class TOY_810:
    """Painter's Virtue"""

    # Lifesteal. After your hero attacks, give minions in your hand +1/+1.
    events = Attack(FRIENDLY_HERO).after(Buff(FRIENDLY_HAND + MINION, "TOY_810e"))


class TOY_810e:
    """Colorful"""

    # +1/+1 (data enchant carries no stats — supply them here).
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


##
# Whizbang's Workshop mini-set


class MIS_700:
    """Whack-A-Gnoll"""

    # Discover a Paladin weapon from the past. Give it +1/+1. ("From the
    # past" = the full historic Wild-inclusive Paladin-weapon pool, so
    # suppress the Standard narrowing with from_past=True.)
    play = Discover(
        CONTROLLER, RandomWeapon(card_class=CardClass.PALADIN, from_past=True)
    ).then(Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "MIS_700e")))


MIS_700e = buff(1, 1)  # Whack! — weapon +1/+1.


class MIS_709:
    """Holy Glowsticks"""

    # Lifesteal (data). Deal 4 damage. Costs (1) if you've cast a Holy spell
    # this turn.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 4)
    # "Costs (1)" — base 4, so a -3 delta when a Holy spell was cast this turn.
    cost_mod = (Attr(CONTROLLER, "holy_spells_cast_this_turn") >= 1) & -3


class MIS_918:
    """Flickering Lightbot"""

    # Gigantify (engine). Costs (1) less for each Holy spell you've cast this
    # game.
    cost_mod = -Attr(CONTROLLER, "holy_spells_cast_this_game")


class MIS_918t(MIS_918):
    """Flickering Lightbot"""

    # Gigantic 8/8 form — same per-game Holy cost reduction.
