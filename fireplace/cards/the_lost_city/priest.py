from ..utils import *

from hearthstone.enums import SpellSchool


##
# Evaluators


class _GladesongDual(Evaluator):
    """True if the controller has played both a Holy and a Shadow spell this
    turn (Gladesong Siren cost reduction)."""

    def check(self, source):
        played = getattr(source.controller, "schools_played_this_turn", set())
        return SpellSchool.HOLY in played and SpellSchool.SHADOW in played


##
# Custom actions


class _ArchaiosSetHealth(TargetedAction):
    """Archaios — whenever another friendly minion attacks, set that minion's
    Health equal to Archaios's current Health. "Set Health" matches both the
    max and the current value (the minion ends undamaged at that total), and may
    raise it above the printed max, so we stamp a HEALTH enchant for the delta
    and clear damage."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None or target is source:
            return
        goal = source.health
        delta = goal - target.max_health
        if delta != 0:
            source.game.cheat_action(
                source, [Buff(target, "TLC_811e", max_health=delta)]
            )
        target.damage = 0
        source.game.manager.targeted_action(self, source, target)


class _StoryOfAmaraSetHealth(TargetedAction):
    """Story of Amara — set your hero's Health to exactly 40. Heroes cap at 30,
    so raise max via a HEALTH enchant for the overflow, then set current Health
    to 40 (clamping damage). Also lowers Health if the hero is above 40."""

    TARGET = ActionArg()

    def do(self, source, target):
        delta = 40 - target.max_health
        if delta > 0:
            source.game.cheat_action(
                source, [Buff(target, "TLC_835e", max_health=delta)]
            )
        target.damage = max(0, target.max_health - 40)
        source.game.manager.targeted_action(self, source, target)


class _ResuscitateResurrect(TargetedAction):
    """Resuscitate — resurrect one friendly minion of each Cost 1, 2 and 3 that
    died this game, picked at random from the controller's graveyard, and give
    each Reborn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for cost in (1, 2, 3):
            pool = [
                c for c in list(ctrl.graveyard)
                if c.type == CardType.MINION and (c.data.cost or 0) == cost
            ]
            if not pool:
                continue
            picked = source.game.random.choice(pool)
            source.game.cheat_action(
                source,
                [Summon(ctrl, picked.id).then(GiveReborn(Summon.CARD))],
            )


class _WiltedShadowAttack(TargetedAction):
    """Wilted Shadow — whenever you heal an enemy character, Wilted Shadow
    attacks it. Only fires while Wilted Shadow is alive in play; skips heals on
    the controller's own characters."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        if target.controller is source.controller:
            return
        if source.zone != Zone.PLAY or source.dead:
            return
        source.game.cheat_action(source, [Attack(source, target)])


class _PurifyingVines(TargetedAction):
    """Purifying Vines (token) — if the targeted minion is friendly give it +2
    Health, if it's an enemy give it -2 Health."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        if target.controller is source.controller:
            source.game.cheat_action(
                source, [Buff(target, "TLC_813e", max_health=2)]
            )
        else:
            source.game.cheat_action(
                source, [Buff(target, "TLC_813e2", max_health=-2)]
            )


class _ReachEquilibriumProgress(TargetedAction):
    """Reach Equilibrium — dual quest. The `school` ('holy'/'shadow') the action
    was constructed with says which half a freshly cast spell advances. After 5
    casts of that school, deliver the matching Sol'etos half (Life's Breath for
    Holy, Death's Touch for Shadow). Once both halves have been awarded the
    quest leaves the secret zone."""

    TARGET = ActionArg()

    def __init__(self, target, school):
        super().__init__(target)
        self._school = school

    def do(self, source, target):
        # Lazy-init the dual counters/latches on the quest card instance
        # (card scripts can't define __init__).
        if not hasattr(source, "_holy_count"):
            source._holy_count = 0
            source._shadow_count = 0
            source._holy_done = False
            source._shadow_done = False
        if self._school == "holy":
            if source._holy_done:
                return
            source._holy_count += 1
            if source._holy_count >= 5:
                source._holy_done = True
                source.game.cheat_action(
                    source, [Give(source.controller, "TLC_817t3")]
                )
        else:
            if source._shadow_done:
                return
            source._shadow_count += 1
            if source._shadow_count >= 5:
                source._shadow_done = True
                source.game.cheat_action(
                    source, [Give(source.controller, "TLC_817t4")]
                )
        if source._holy_done and source._shadow_done and source.zone == Zone.SECRET:
            source.zone = Zone.GRAVEYARD


##
# Minions


class TLC_811:
    """Archaios"""

    # Whenever another friendly minion attacks, set its Health equal to this
    # minion's Health.
    events = Attack(FRIENDLY + MINION).on(_ArchaiosSetHealth(Attack.ATTACKER))


class TLC_814:
    """Twilight Mender"""

    # Deathrattle: Get a random Holy and Shadow spell.
    deathrattle = (
        Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.HOLY)),
        Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.SHADOW)),
    )


class TLC_819:
    """Gladesong Siren"""

    # Lifesteal. Costs (1) if you've played a Holy and Shadow spell this turn.
    # The LIFESTEAL keyword is absent from the card data, so set the tag here.
    tags = {GameTag.LIFESTEAL: True}

    class Hand:
        update = _GladesongDual() & Refresh(SELF, {GameTag.COST: SET(1)})


class TLC_820:
    """Glade Ecologist"""

    # Deathrattle: Get a 1-Cost Holy spell that gives a minion +2 or -2 Health.
    deathrattle = Give(CONTROLLER, "TLC_813")


class TLC_821:
    """Wilted Shadow"""

    # Lifesteal. Whenever you heal an enemy, this attacks it.
    events = Heal(source=FRIENDLY).on(_WiltedShadowAttack(Heal.TARGET))


##
# Spells


class TLC_813:
    """Purifying Vines"""

    # Choose a minion. If it's friendly, give it +2 Health. If it's an enemy,
    # give it -2 Health.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _PurifyingVines(TARGET)


class TLC_815:
    """Gravedawn Voidbulb"""

    # Summon a random 4-Cost minion and give it Taunt. Kindred: Do it again.
    # TLC_815e ("Void Touched") is the text-only enchant; the TAUNT tag must be
    # set explicitly via the Taunt helper.
    play = (
        Summon(CONTROLLER, RandomMinion(cost=4)).then(
            Buff(Summon.CARD, "TLC_815e"), Taunt(Summon.CARD)
        ),
        Kindred()
        & Summon(CONTROLLER, RandomMinion(cost=4)).then(
            Buff(Summon.CARD, "TLC_815e"), Taunt(Summon.CARD)
        ),
    )


class TLC_816:
    """Gravedawn Sunbloom"""

    # Draw 2 cards. Kindred: This costs (2) less.
    cost_mod = -KindredCost(2)
    play = Draw(CONTROLLER) * 2


class TLC_818:
    """Resuscitate"""

    # Resurrect a 1, 2, and 3-Cost minion. Give them Reborn.
    play = _ResuscitateResurrect(CONTROLLER)


class TLC_835:
    """Story of Amara"""

    # Set your hero's Health to 40.
    play = _StoryOfAmaraSetHealth(FRIENDLY_HERO)


##
# Quest — Reach Equilibrium (TLC_817) + Sol'etos halves


# Ids of the two Sol'etos halves and the combined body they fuse into.
_SOLETOS_LIFE = "TLC_817t3"   # Sol'etos, Life's Breath  (Taunt / Battlecry copy)
_SOLETOS_DEATH = "TLC_817t4"  # Sol'etos, Death's Touch  (Reborn / 5-dmg Deathrattle)
_SOLETOS_COMBINED = "TLC_817t5"  # Sol'etos, Cycle's Rebirth


class _SoletosCombine(TargetedAction):
    """Sol'etos — "If you're holding both halves of Sol'etos, combine!".

    Both halves carry a Hand listener (below) that, whenever a card enters the
    controller's hand, runs this action. If the controller is holding BOTH
    Life's Breath and Death's Touch at that moment, the pair fuses into the
    single combined body Sol'etos, Cycle's Rebirth (TLC_817t5), which replaces
    them in hand — mirroring the engine's Shatter recombine, but card-side.

    No-op unless exactly the two distinct halves are both present, so it is
    safe to fire from either half's listener (and twice in a row): the second
    invocation finds the halves already gone and does nothing.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        # Guard against re-entrancy while we are mid-combine (the Give of the
        # combined card fires hand listeners again).
        if getattr(player.game, "_soletos_combining", False):
            return
        hand = player.hand
        life = next((c for c in hand if c.id == _SOLETOS_LIFE), None)
        death = next((c for c in hand if c.id == _SOLETOS_DEATH), None)
        if life is None or death is None:
            return
        # Remember where the halves sat so the fused card lands there. (Both
        # halves leave hand before the fused card is created, so there is always
        # room — the net hand size drops by one.)
        index = min(hand.index(life), hand.index(death))
        player.game._soletos_combining = True
        try:
            life.zone = Zone.REMOVEDFROMGAME
            death.zone = Zone.REMOVEDFROMGAME
            combined = player.card(_SOLETOS_COMBINED, source=source)
            combined._summon_index = index
            combined.zone = Zone.HAND
            combined._summon_index = None
        finally:
            player.game._soletos_combining = False
        source.game.manager.targeted_action(self, source, target)


# Each half watches for any card entering the controller's hand (drawn from
# deck, or given by the quest / a generator) and then attempts the combine.
_SOLETOS_HAND_EVENTS = (
    Draw(CONTROLLER).after(_SoletosCombine(SELF)),
    Give(CONTROLLER).after(_SoletosCombine(SELF)),
)


class TLC_817:
    """Reach Equilibrium"""

    # Quest: Cast 5 Holy spells. Reward: Life's Breath.
    # Quest: Cast 5 Shadow spells. Reward: Death's Touch.
    quest = (
        Play(CONTROLLER, SPELL + HOLY_SPELL).after(
            _ReachEquilibriumProgress(SELF, "holy")
        ),
        Play(CONTROLLER, SPELL + SHADOW_SPELL).after(
            _ReachEquilibriumProgress(SELF, "shadow")
        ),
    )


class TLC_817t3:
    """Sol'etos, Life's Breath"""

    # Taunt. Battlecry: Summon a copy of this.
    # If you're holding both halves of Sol'etos, combine! (handled in Hand)
    play = Summon(CONTROLLER, ExactCopy(SELF))

    class Hand:
        events = _SOLETOS_HAND_EVENTS


class TLC_817t4:
    """Sol'etos, Death's Touch"""

    # Reborn. Deathrattle: Deal 5 damage to a random enemy.
    # If you're holding both halves of Sol'etos, combine! (handled in Hand)
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 5)

    class Hand:
        events = _SOLETOS_HAND_EVENTS


class TLC_817t5:
    """Sol'etos, Cycle's Rebirth"""

    # Taunt, Reborn. Battlecry: Summon a copy of this. Deathrattle: Deal 5
    # damage to a random enemy.
    play = Summon(CONTROLLER, ExactCopy(SELF))
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 5)


##
# The Lost City of Un'Goro mini-set (DINO_) — Priest
#
# Custom actions


class _RitualOfLifeSummon(TargetedAction):
    """Ritual of Life — after Discovering a 3-Cost minion, summon a copy of it
    and set the copy's stats to 2/2 (the "Lasting Life" enchant). The
    Discovered card itself is the LazyValue picked option; we summon a fresh
    copy by its id rather than adding it to hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        # `target` is the Discovered card option (a real Card instance).
        if target is None:
            return
        ctrl = source.controller
        source.game.cheat_action(
            source,
            [Summon(ctrl, target.id).then(Buff(Summon.CARD, "DINO_426e"))],
        )


class _BehemothMask(TargetedAction):
    """Behemoth Mask — set the targeted minion's stats to 8/10 and give it
    Lifesteal (the DINO_428e enchant), then force a random *enemy* minion to
    attack it. "Enemy" is relative to the spell's caster, so a random minion
    controlled by the opponent of the caster is chosen as the attacker."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        source.game.cheat_action(source, [Buff(target, "DINO_428e")])
        # Pick a random enemy minion (an opponent-controlled minion) to attack
        # the masked target. The target may itself be friendly or enemy; the
        # attacker is always from the side opposing the caster.
        enemies = [
            m for m in source.controller.opponent.field
            if m is not target and not m.dead
        ]
        if not enemies:
            return
        attacker = source.game.random.choice(enemies)
        source.game.cheat_action(source, [Attack(attacker, target)])


##
# Spells


class DINO_426:
    """Ritual of Life"""

    # Discover a 3-Cost minion. Summon a 2/2 copy of it.
    play = Discover(CONTROLLER, RandomMinion(cost=3)).then(
        _RitualOfLifeSummon(Discover.CARD)
    )


class DINO_428:
    """Behemoth Mask"""

    # Set a minion's stats to 8/10 and give it Lifesteal. Force a random enemy
    # minion to attack it.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _BehemothMask(TARGET)


##
# Minions


class DINO_431:
    """Atlasaurus"""

    # Taunt. Deathrattle: Summon a random Taunt minion that costs (5) or more.
    deathrattle = Summon(
        CONTROLLER,
        RandomMinion(
            custom_filter=lambda c: bool(c.tags.get(GameTag.TAUNT))
            and (c.cost or 0) >= 5
        ),
    )


##
# Enchantments


class DINO_426e:
    # Lasting Life — the summoned copy's stats are set to 2/2.
    atk = SET(2)
    max_health = SET(2)


class DINO_428e:
    # Behemoth Mask — stats set to 8/10 and Lifesteal granted. The data enchant
    # carries no stat/keyword tags, so the SET overrides and LIFESTEAL tag are
    # supplied here. Clear damage on apply so current Health equals the new max.
    tags = {GameTag.LIFESTEAL: True}
    atk = SET(8)
    max_health = SET(10)

    def apply(self, target):
        target.damage = 0
