from ..utils import *

from hearthstone.enums import CardType, SpellSchool


##
# Custom actions


class _ArmFirstSpellDiscount(TargetedAction):
    """Sha'tari Cloakfield — while in play, the controller's first spell each
    turn costs (1) less (armed each turn)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.first_spell_discount += 1


class _SetGivenCostToOne(TargetedAction):
    """Final Frontier — set the just-given minion's Cost to (1). 'Set' (not
    reduce), so apply the per-card delta (1 - card.cost) via the buff kwarg."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        source.game.cheat_action(
            source, [Buff(target, "GDB_857e", cost=1 - target.cost)]
        )


class _StarlightRecast(TargetedAction):
    """Starlight Reactor — recast the just-cast Arcane spell with random
    targets. Re-entrancy guarded so the recast doesn't chain endlessly."""

    TARGET = ActionArg()
    SPELL = ActionArg()

    def do(self, source, target, spell):
        if isinstance(spell, (list, tuple)):
            spell = spell[0] if spell else None
        if spell is None:
            return
        if getattr(source, "_starlight_recasting", False):
            return
        source._starlight_recasting = True
        try:
            source.game.cheat_action(
                source, [CastSpellTargetsEnemiesIfPossible(spell.id)]
            )
        finally:
            source._starlight_recasting = False


class _DiscoverArcaneDiscounted(TargetedAction):
    """Exarch Othaar — get 3 different Arcane spells and reduce their Cost by
    (2) (only when building a Starship)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        from .. import db as _db

        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.SPELL
            and c.spell_school is not None
            and int(c.spell_school) == int(SpellSchool.ARCANE)
        ]
        rng = source.game.random
        rng.shuffle(pool)
        for cid in pool[:3]:
            source.game.cheat_action(
                source, [Give(ctrl, cid).then(Buff(Give.CARD, "GDB_856e"))]
            )


# Uluu's curated pool of "random Choose One" choices. The exact in-game pool
# isn't in the card data, so use a soak-safe set of self-resolving 0-Cost
# effect tokens (no targeting prompts, no nested choices).
_ULUU_POOL = [
    "GDB_854o1",
    "GDB_854o2",
    "GDB_854o3",
    "GDB_854o4",
    "GDB_854o5",
    "GDB_854o6",
]


class _UluuGainChoices(TargetedAction):
    """Uluu — each turn it is in hand, gain two more random Choose One choices
    (accumulated on the card)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if getattr(target, "_uluu_options", None) is None:
            target._uluu_options = []
        for _ in range(2):
            target._uluu_options.append(source.game.random.choice(_ULUU_POOL))


class _CastUluuOption(TargetedAction):
    """Resolve the chosen Uluu option's effect (its play script)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(target, target.get_actions("play"))


class _UluuChoose(TargetedAction):
    """Uluu — on play, Choose One among all the accumulated random options."""

    TARGET = ActionArg()

    def do(self, source, target):
        opts = getattr(target, "_uluu_options", None)
        if not opts:
            return
        cards = [source.controller.card(oid, source) for oid in opts]
        source.game.cheat_action(
            source,
            [Choice(source.controller, cards).then(_CastUluuOption(Choice.CARD))],
        )


class _ConstructPylons(TargetedAction):
    """Construct Pylons — your next Protoss card this turn costs (2) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.next_protoss_card_discount += 2


class _CarrierInterceptors(TargetedAction):
    """Carrier — summon four 4/1 Interceptors, each attacking a random enemy.
    Summon all four first, then have them swing (so a later Interceptor can't
    be picked as an earlier one's target)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        summoned = []
        for _ in range(4):
            before = set(ctrl.field)
            source.game.cheat_action(source, [Summon(ctrl, "SC_756t")])
            summoned.extend(m for m in ctrl.field if m not in before)
        for minion in summoned:
            if minion.dead:
                continue
            enemies = [e for e in ENEMY_CHARACTERS.eval(source.game, source)
                       if not e.dead]
            if enemies:
                source.game.cheat_action(
                    source,
                    [Attack(minion, source.game.random.choice(enemies))],
                )


class _ImmortalDoubleStats(TargetedAction):
    """Immortal — Battlecry: spend 4 Mana to double this minion's stats."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        ctrl = source.controller
        if ctrl.mana < 4:
            return
        ctrl.used_mana += 4
        source.game.cheat_action(
            source,
            [Buff(target, "SC_763e", atk=target.atk, max_health=target.max_health)],
        )


##
# Minions


class GDB_103:
    """Sha'tari Cloakfield"""

    # Elusive. Your first spell each turn costs (1) less. Starship Piece.
    # This build's data carries Elusive as the unmapped tag 3684 (python-
    # hearthstone doesn't know it), so the targeting code never sees it. Restore
    # it via the legacy split flags that targeting.py honors.
    tags = {
        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }
    events = OWN_TURN_BEGIN.on(_ArmFirstSpellDiscount(SELF))


class GDB_108:
    """Starlight Reactor"""

    # After you cast an Arcane spell, recast it (targets chosen randomly).
    # Starship Piece.
    events = Play(CONTROLLER, ARCANE_SPELL).after(
        _StarlightRecast(SELF, Play.CARD)
    )


class GDB_854:
    """Uluu, the Everdrifter"""

    # Each turn this is in your hand, gain two random Choose One choices; on
    # play, Choose One among everything accumulated. (Pool curated below — the
    # real option set isn't in the card data.)
    class Hand:
        events = OWN_TURN_BEGIN.on(_UluuGainChoices(SELF))

    play = _UluuChoose(SELF)


class GDB_855:
    """Star Grazer"""

    # Elusive, Taunt. Spellburst: Give your hero +8 Attack this turn and gain
    # 8 Armor.
    spellburst = Buff(FRIENDLY_HERO, "GDB_855e"), GainArmor(FRIENDLY_HERO, 8)


class GDB_856:
    """Exarch Othaar"""

    # Battlecry: If you're building a Starship, get 3 different Arcane spells
    # and reduce their Costs by (2).
    play = BUILDING_STARSHIP(CONTROLLER) & _DiscoverArcaneDiscounted(SELF)


##
# Spells


class GDB_851:
    """Astral Phaser"""

    # Choose One - Deal $2 damage to two random enemy minions; or Make one
    # Dormant for 2 turns.
    choose = ("GDB_851a", "GDB_851b")
    play = ChooseBoth(CONTROLLER) & (
        Hit(RANDOM(ENEMY_MINIONS) * 2, 2),
        Dormant(RANDOM(ENEMY_MINIONS), 2),
    )


class GDB_851a:
    """Lethal Rays"""

    # Deal $2 damage to two random enemy minions.
    play = Hit(RANDOM(ENEMY_MINIONS) * 2, 2)


class GDB_851b:
    """Stunning Star"""

    # Choose an enemy minion. It goes Dormant for 2 turns.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Dormant(TARGET, 2)


class GDB_852:
    """Arkonite Revelation"""

    # Draw a card. If it's a spell, it costs (1) less.
    play = Draw(CONTROLLER).then(
        Find(Draw.CARD + SPELL) & Buff(Draw.CARD, "GDB_852e")
    )


class GDB_857:
    """Final Frontier"""

    # Discover a 10-Cost minion from the past. Set its Cost to (1).
    play = Discover(
        CONTROLLER, RandomMinion(cost=10, is_standard=None)
    ).then(Give(CONTROLLER, Discover.CARD).then(_SetGivenCostToOne(Give.CARD)))


class GDB_882:
    """Cosmic Phenomenon"""

    # Summon three 2/3 Elementals with Taunt. If your board is full, give your
    # minions +1/+1.
    play = Summon(CONTROLLER, "GDB_882t") * 3, FULL_BOARD & Buff(
        FRIENDLY_MINIONS, "GDB_882e"
    )


class GDB_883:
    """Distress Signal"""

    # Summon two random 2-Cost minions. Refresh 2 Mana Crystals.
    play = (
        Summon(CONTROLLER, RandomMinion(cost=2)) * 2,
        ManaThisTurn(CONTROLLER, 2),
    )


##
# Heroes of StarCraft — Protoss (Druid)


class SC_755:
    """Construct Pylons"""

    # Your next Protoss card this turn costs (2) less.
    play = _ConstructPylons(SELF)


class SC_756:
    """Carrier"""

    # At the end of your turn, summon four 4/1 Interceptors that attack random
    # enemies.
    events = OWN_TURN_END.on(_CarrierInterceptors(SELF))


class SC_763:
    """Immortal"""

    # Taunt, Divine Shield (data). Battlecry: Spend 4 Mana to double this
    # minion's stats.
    play = _ImmortalDoubleStats(SELF)


##
# Tokens


class GDB_882t:
    """Living Pulsar"""

    # 2/3 Elemental with Taunt. Stats + Taunt live in data.


##
# Enchantments


@custom_card
class GDB_852e:
    # Arkonite Revelation — drawn spell costs (1) less.
    tags = {
        GameTag.CARDNAME: "Arkonite Revelation",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }
    events = REMOVED_IN_PLAY


class GDB_855e:
    # Whale Strike — +8 Attack this turn (hero).
    tags = {GameTag.ATK: 8}


@custom_card
class GDB_856e:
    # Exarch Othaar — Arcane spell costs (2) less.
    tags = {
        GameTag.CARDNAME: "Exarch Othaar",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


@custom_card
class GDB_857e:
    # Final Frontier — set the discovered minion's Cost to (1). The COST delta
    # is supplied per-card via the `cost=` buff kwarg (1 - card.cost).
    tags = {
        GameTag.CARDNAME: "Final Frontier",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: 0,
    }


class GDB_882e:
    # Phenomenal — +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


##
# Uluu Choose-One option tokens (engine-internal; not in card data)


@custom_card
class GDB_854o1:
    tags = {
        GameTag.CARDNAME: "Cosmic Bulwark",
        GameTag.CARDTYPE: CardType.SPELL,
        GameTag.COST: 0,
    }
    # Gain 5 Armor.
    play = GainArmor(FRIENDLY_HERO, 5)


@custom_card
class GDB_854o2:
    tags = {
        GameTag.CARDNAME: "Cosmic Insight",
        GameTag.CARDTYPE: CardType.SPELL,
        GameTag.COST: 0,
    }
    # Draw a card.
    play = Draw(CONTROLLER)


@custom_card
class GDB_854o3:
    tags = {
        GameTag.CARDNAME: "Cosmic Renewal",
        GameTag.CARDTYPE: CardType.SPELL,
        GameTag.COST: 0,
    }
    # Restore 6 Health to your hero.
    play = Heal(FRIENDLY_HERO, 6)


@custom_card
class GDB_854o4:
    tags = {
        GameTag.CARDNAME: "Cosmic Strike",
        GameTag.CARDTYPE: CardType.SPELL,
        GameTag.COST: 0,
    }
    # Deal 3 damage to a random enemy.
    play = Hit(RANDOM(ENEMY_CHARACTERS), 3)


@custom_card
class GDB_854o5:
    tags = {
        GameTag.CARDNAME: "Cosmic Might",
        GameTag.CARDTYPE: CardType.SPELL,
        GameTag.COST: 0,
    }
    # Give your minions +2/+2.
    play = Buff(FRIENDLY_MINIONS, "GDB_854oe")


@custom_card
class GDB_854o6:
    tags = {
        GameTag.CARDNAME: "Cosmic Swarm",
        GameTag.CARDTYPE: CardType.SPELL,
        GameTag.COST: 0,
    }
    # Summon two 1/1 Wisps.
    play = Summon(CONTROLLER, "CS2_231") * 2


@custom_card
class GDB_854oe:
    tags = {
        GameTag.CARDNAME: "Cosmic Might",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
    }
