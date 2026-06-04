from ..utils import *

from hearthstone.enums import CardClass, GameTag, Race, Zone


##
# Minions


class TLC_220:
    """Windswept Pageturner"""

    # After you summon an Elemental, deal 3 damage to a random enemy.
    events = Summon(CONTROLLER, MINION + ELEMENTAL - SELF).after(
        Hit(RANDOM_ENEMY_CHARACTER, 3)
    )


class TLC_226:
    """Conjured Bookkeeper"""

    # Deathrattle: Draw a spell. Kindred: Summon a copy of this.
    deathrattle = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)),
        Kindred() & Summon(CONTROLLER, "TLC_226"),
    )


##
# TLC_452 — Titanographer Osk
# "Gains a random Titan ability in your hand that changes each turn."
#
# Osk grafts one of 31 "Titan ability" battlecry tokens (TLC_452t1..t35;
# t10/t11/t12/t25 absent in this build). We model the graft as a per-card
# `_titan_ability` token id, re-rolled at the start of each of your turns while
# Osk is in hand (Hand.events) and fired when Osk is played (def play). Each
# token's battlecry below is reproduced with existing primitives; effects that
# would prompt for a target auto-resolve to a random legal target (the grafted
# battlecry cannot pop a chooser). A couple of stateful abilities (t2 spell
# damage, t15 enemy tax) are best-effort approximations, noted inline.


# --- summon-bodies not present in this build's data ---
@custom_card
class TLC_452t3t:
    tags = {
        GameTag.CARDNAME: "Titan's Undead",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.TAUNT: True,
        GameTag.REBORN: True,
        GameTag.CARDRACE: Race.UNDEAD,
    }


@custom_card
class TLC_452t6t:
    tags = {
        GameTag.CARDNAME: "Titan's Elemental",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
        GameTag.TAUNT: True,
        GameTag.CARDRACE: Race.ELEMENTAL,
    }


# --- enchants ---
@custom_card
class _OskSet2e:
    # t16 — set a minion's Attack and Health to 2.
    tags = {
        GameTag.CARDNAME: "Titanic Equality",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: 2
    max_health = lambda self, i: 2


@custom_card
class _OskSet2Cost2e:
    # t18 — set a drawn minion's Attack, Health, and Cost to 2.
    tags = {
        GameTag.CARDNAME: "Titanic Downsizing",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: 2
    max_health = lambda self, i: 2
    cost = lambda self, i: 2


@custom_card
class _OskCostMore1e:
    # t15 — enemy cards cost (1) more next turn (drops at the start of your
    # next turn). Mirrors Forensic Duster's persistent-aura approximation.
    tags = {
        GameTag.CARDNAME: "Titanic Tax",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = Refresh(ENEMY_HAND, {GameTag.COST: 1})
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


@custom_card
class _OskSpellDmg3e:
    # t2 — best-effort +3 Spell Damage for the turn (the printed effect is
    # "+3 for your next spell"; we grant it board-wide for the turn).
    tags = {
        GameTag.CARDNAME: "Titanic Focus",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.SPELLPOWER: 3,
        GameTag.TAG_ONE_TURN_EFFECT: True,
    }


@custom_card
class _OskStatBuff:
    # Generic stat enchant — Attack/Health supplied per-call via atk=/max_health=
    # kwargs on the Buff action (t1, t17, t22, t23, t30, t31, t32).
    tags = {
        GameTag.CARDNAME: "Titanic Might",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class _OskElusivee:
    # t24 — +3 Health and Elusive.
    tags = {
        GameTag.CARDNAME: "Titanic Ward",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.HEALTH: 3,
        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }


@custom_card
class _OskCostLess2e:
    # t5 — minions in hand cost (2) less.
    tags = {
        GameTag.CARDNAME: "Titanic Bargain",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


@custom_card
class _OskCostLess3e:
    # t4 — the Discovered Deathrattle minion costs (3) less.
    tags = {
        GameTag.CARDNAME: "Titanic Discount",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


# --- compound battlecry actions ---
class _OskGainHealthDestroy(TargetedAction):
    """t1 — Destroy an enemy minion. Osk and your hero gain its Health."""

    TARGET = ActionArg()  # SELF (Osk)

    def do(self, source, target):
        victims = (ENEMY_MINIONS - DEAD).eval(source.game, source)
        if not victims:
            return
        victim = source.game.random.choice(victims)
        gained = victim.health
        source.game.cheat_action(source, [Destroy(victim)])
        if gained > 0:
            source.game.cheat_action(
                source,
                [
                    Buff(target, "_OskStatBuff", max_health=gained),
                    Buff(FRIENDLY_HERO, "_OskStatBuff", max_health=gained),
                ],
            )


class _OskNextSpell(TargetedAction):
    """t2 — Your next spell costs (3) less and has Spell Damage +3."""

    TARGET = ActionArg()

    def do(self, source, target):
        p = source.controller
        p._next_spell_cost_reduction = getattr(p, "_next_spell_cost_reduction", 0) + 3
        source.game.cheat_action(source, [Buff(FRIENDLY_HERO, "_OskSpellDmg3e")])


class _OskDrawUntilFull(TargetedAction):
    """t7 — Draw cards until your hand is full."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        guard = 0
        while len(ctrl.hand) < ctrl.max_hand_size and ctrl.deck and guard < 20:
            source.game.cheat_action(source, [Draw(ctrl)])
            guard += 1


class _OskCastMageSecret(TargetedAction):
    """t14 — Cast 1 random Mage Secret."""

    TARGET = ActionArg()

    def do(self, source, target):
        picker = RandomCardPicker(
            type=CardType.SPELL,
            card_class=CardClass.MAGE,
            custom_filter=lambda c: bool(c.tags.get(GameTag.SECRET)),
        )
        ids = picker.evaluate(source)
        if ids:
            card = source.controller.card(ids[0], source=source)
            source.game.cheat_action(source, [CastSpell(card)])


class _OskDraw2SetStats(TargetedAction):
    """t18 — Draw 2 minions. Set their Attack, Health, and Cost to 2."""

    TARGET = ActionArg()

    def do(self, source, target):
        for _ in range(2):
            cands = (FRIENDLY_DECK + MINION).eval(source.game, source)
            if not cands:
                break
            card = source.game.random.choice(cands)
            source.game.cheat_action(source, [ForceDraw(card)])
            source.game.cheat_action(source, [Buff(card, "_OskSet2Cost2e")])


class _OskCopyNonTitan(TargetedAction):
    """t19 — Choose a non-Titan minion. Summon a copy of it with +2/+2."""

    TARGET = ActionArg()

    def do(self, source, target):
        titan_tag = getattr(GameTag, "TITAN", None)
        cands = [
            m
            for m in (ALL_MINIONS - SELF).eval(source.game, source)
            if not (titan_tag and m.tags.get(titan_tag))
        ]
        if not cands:
            return
        chosen = source.game.random.choice(cands)
        copy = source.controller.card(chosen.id, source=source)
        source.game.cheat_action(source, [Summon(source.controller, copy)])
        source.game.cheat_action(source, [Buff(copy, "_OskStatBuff", atk=2, max_health=2)])


class _OskFillTendrils(TargetedAction):
    """t33 — Fill your hand with 1/1 Chaotic Tendrils."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        guard = 0
        while len(ctrl.hand) < ctrl.max_hand_size and guard < 20:
            source.game.cheat_action(source, [Give(ctrl, "YOG_514")])
            guard += 1


class _OskForceAttacks(TargetedAction):
    """t34 — Force each enemy minion to attack a random enemy minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        for attacker in list((ENEMY_MINIONS - DEAD).eval(source.game, source)):
            if attacker.dead or attacker.zone != Zone.PLAY:
                continue
            others = [
                m
                for m in (ENEMY_MINIONS - DEAD).eval(source.game, source)
                if m is not attacker
            ]
            if not others:
                continue
            defender = source.game.random.choice(others)
            source.game.cheat_action(source, [Attack(attacker, defender)])


class _OskReroll(TargetedAction):
    """Re-roll the held Titan ability at the start of each of your turns."""

    TARGET = ActionArg()  # OWNER (the Osk card in hand)

    def do(self, source, target):
        target._titan_ability = source.game.random.choice(OSK_ABILITY_IDS)


# Token id -> the actions that token's battlecry runs (reused across plays, like
# any class-level `play` script). Targeted effects use random selectors so the
# grafted battlecry resolves without a chooser.
OSK_ABILITIES = {
    "TLC_452t1": (_OskGainHealthDestroy(SELF),),
    "TLC_452t2": (_OskNextSpell(SELF),),
    "TLC_452t3": (Summon(CONTROLLER, "TLC_452t3t") * 2,),
    "TLC_452t4": (
        Discover(CONTROLLER, RandomMinion(deathrattle=True)).then(
            Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "_OskCostLess3e"))
        ),
    ),
    "TLC_452t5": (Buff(FRIENDLY_HAND + MINION, "_OskCostLess2e"),),
    "TLC_452t6": (Summon(CONTROLLER, "TLC_452t6t") * 4,),
    "TLC_452t7": (_OskDrawUntilFull(SELF),),
    "TLC_452t8": (Heal(FRIENDLY_HERO, 99),),
    "TLC_452t9": (FillMana(CONTROLLER, 10),),
    "TLC_452t13": (Hit(RANDOM_ENEMY_CHARACTER, 5),),
    "TLC_452t14": (_OskCastMageSecret(SELF),),
    "TLC_452t15": (Buff(OPPONENT, "_OskCostMore1e"),),
    "TLC_452t16": (Buff(ENEMY_MINIONS, "_OskSet2e"),),
    "TLC_452t17": (Buff(FRIENDLY_MINIONS - SELF, "_OskStatBuff", atk=2, max_health=2),),
    "TLC_452t18": (_OskDraw2SetStats(SELF),),
    "TLC_452t19": (_OskCopyNonTitan(SELF),),
    "TLC_452t20": (
        Summon(CONTROLLER, RandomMinion(cost=6)).then(
            SetTags(Summon.CARD, {GameTag.TAUNT: True, GameTag.LIFESTEAL: True})
        ),
    ),
    "TLC_452t21": (Remove(RANDOM_ENEMY_MINION), Remove(RANDOM_ENEMY_MINION)),
    "TLC_452t22": (Buff(SELF, "_OskStatBuff", atk=2, max_health=1), Hit(RANDOM_ENEMY_CHARACTER, 4)),
    "TLC_452t23": (Buff(SELF, "_OskStatBuff", atk=1, max_health=2), Draw(CONTROLLER)),
    "TLC_452t24": (Buff(SELF, "_OskElusivee"),),
    "TLC_452t26": (Hit(RANDOM_OTHER_MINION, 20),),
    "TLC_452t27": (Hit(ENEMY_CHARACTERS, 3), Heal(FRIENDLY_CHARACTERS, 6)),
    "TLC_452t28": (Summon(CONTROLLER, "EX1_tk34") * 2,),
    "TLC_452t29": (Destroy(ALL_MINIONS - SELF),),
    "TLC_452t30": (Buff(SELF, "_OskStatBuff", max_health=5), GainArmor(FRIENDLY_HERO, 5)),
    "TLC_452t31": (Buff(SELF, "_OskStatBuff", atk=5), Buff(FRIENDLY_HERO, "TLC_903e")),
    "TLC_452t32": (Buff(SELF, "_OskStatBuff", atk=2, max_health=2), Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + WEAPON))),
    "TLC_452t33": (_OskFillTendrils(SELF),),
    "TLC_452t34": (_OskForceAttacks(SELF),),
    "TLC_452t35": (Steal(RANDOM_ENEMY_MINION),),
}

OSK_ABILITY_IDS = list(OSK_ABILITIES.keys())


class TLC_452:
    """Titanographer Osk"""

    # Gains a random Titan ability in your hand that changes each turn, and
    # fires that ability's battlecry on play.
    class Hand:
        events = OWN_TURN_BEGIN.on(_OskReroll(SELF))

    def play(self):
        cid = getattr(self, "_titan_ability", None)
        if cid not in OSK_ABILITIES:
            cid = self.controller.game.random.choice(OSK_ABILITY_IDS)
            self._titan_ability = cid
        yield from OSK_ABILITIES[cid]


class TLC_461:
    """Scrappy Scavenger"""

    # Battlecry: Discover a card with Cost equal to your remaining Mana
    # Crystals.
    play = DISCOVER(RandomCollectible(cost=CURRENT_MANA(CONTROLLER)))


class TLC_483:
    """Vault Breaker"""

    # After you Discover a card, reduce its Cost by (1).
    events = Discovered(CONTROLLER).on(Buff(Discovered.CARD, "TLC_483e"))


@custom_card
class TLC_483e:
    # Vault Breaker — discovered card costs (1) less.
    tags = {
        GameTag.CARDNAME: "Vault Breaker",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


##
# Spells


class TLC_334:
    """Relic of Kings"""

    # Discover a spell from any class that costs (8) or more. It costs (1).
    play = Discover(
        CONTROLLER,
        RandomSpell(custom_filter=lambda c: (c.cost or 0) >= 8, card_class=None),
    ).then(Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "TLC_334e")))


@custom_card
class TLC_334e:
    # Relic of Kings — set the discovered spell's Cost to (1).
    tags = {
        GameTag.CARDNAME: "Relic of Kings",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    cost = SET(1)


class TLC_364:
    """Story of the Waygate"""

    # Reduce the Cost of cards in your hand that didn't start in your deck
    # by (1).
    play = Buff(FRIENDLY_HAND - STARTING_DECK - SELF, "TLC_364e")


@custom_card
class TLC_364e:
    # Story of the Waygate — costs (1) less.
    tags = {
        GameTag.CARDNAME: "Story of the Waygate",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class TLC_365:
    """Storage Scuffle"""

    # Deal 3 damage to a minion. Costs (0) if you've Discovered this turn.
    # COST: -100 delta clamps to 0 (engine floors cost at 0).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3)
    cost_mod = (Attr(CONTROLLER, "discovers_this_turn") >= 1) & -100


class TLC_462:
    """Unearthed Artifacts"""

    # Summon a random 2-Cost minion. If you've Discovered this turn, summon a
    # random 4-Cost minion instead.
    play = (Attr(CONTROLLER, "discovers_this_turn") >= 1) & Summon(
        CONTROLLER, RandomMinion(cost=4)
    ) | Summon(CONTROLLER, RandomMinion(cost=2))


##
# Quest


class TLC_460:
    """The Forbidden Sequence"""

    # Quest: Discover cards (total from QUEST_PROGRESS_TOTAL data tag, 7 at
    # build 226928). Reward: The Origin Stone.
    quest = Discovered(CONTROLLER).on(AddProgress(SELF, Discovered.CARD))
    reward = Give(CONTROLLER, "TLC_460t")


class _OriginStonePlayOthers(TargetedAction):
    """The Origin Stone — after a Discover, play the two un-chosen options and
    lose 1 Durability. The engine retains the un-chosen cards on
    ``player._discover_leftovers`` (set in Discover.choose); here we cast/summon
    each one for free. Durability is spent first and gates the effect, so any
    Discover chain (a leftover that is itself a Discover card re-triggers this)
    is bounded by the weapon's remaining durability."""

    TARGET = ActionArg()  # the weapon (SELF)

    def do(self, source, target):
        weapon = target
        player = weapon.controller
        # Snapshot and clear immediately so nested Discovers (spawned by playing
        # the leftovers) start from a clean slate rather than re-consuming this.
        leftovers = list(getattr(player, "_discover_leftovers", []) or [])
        player._discover_leftovers = []
        if weapon.durability <= 0:
            return
        # "Lose 1 Durability." Spend it up front so the chain self-limits.
        weapon.damage += 1
        for card in leftovers:
            if card is None:
                continue
            card.controller = player
            source.game.cheat_action(weapon, [CastSpell(card)])


class TLC_460t:
    """The Origin Stone"""

    # After you Discover a card, this plays the other options. Lose 1
    # Durability.
    events = Discovered(CONTROLLER).on(_OriginStonePlayOthers(SELF))


##
# The Lost City of Un'Goro mini-set (Dinosaurs, DINO_)


class DINO_409:
    """Techysaurus"""

    # Taunt. Costs (1) less for each card you played this game that didn't
    # start in your deck.
    # cards_played_this_game records hand-plays; subtract the starting deck so
    # only "didn't start in your deck" cards count.
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME - STARTING_DECK)


class _TributeDanceMorph(TargetedAction):
    """Tribute Dance — transform the first chosen minion (TARGET) into a copy
    of a second, different minion (FORM)."""

    TARGET = ActionArg()
    FORM = CardArg()

    def get_target_args(self, source, target):
        from ...actions import _eval_card

        form = _eval_card(source, self._args[1])
        form = form[0] if isinstance(form, list) and form else form
        return [form]

    def do(self, source, target, form):
        if target is None or form is None:
            return
        source.game.queue_actions(source, [Morph(target, form.id)])


class DINO_414:
    """Tribute Dance"""

    # Choose a minion. Choose a different minion to transform it into.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }

    def play(self):
        target = self.target
        if target is None:
            return
        # Second pick: any minion other than the one being transformed.
        target_eid = target.entity_id
        others = FuncSelector(
            lambda entities, source: [
                m
                for m in ALL_MINIONS.eval(source.game, source)
                if m.entity_id != target_eid
            ]
        )
        yield Find(others) & ChoiceTarget(CONTROLLER, others).then(
            _TributeDanceMorph(target, ChoiceTarget.CARD)
        )


class DINO_429:
    """Sheep Mask"""

    # Set a minion's stats to 1/1 and give it "Deathrattle: Deal 2 damage to
    # all minions."
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "DINO_429e")


class DINO_429e:
    # Sheep Mask — stats set to 1/1, plus the Deathrattle.
    tags = {GameTag.DEATHRATTLE: True}
    atk = lambda self, i: 1
    max_health = lambda self, i: 1
    deathrattle = Hit(ALL_MINIONS, 2)
