from ..utils import *


# ---------------------------------------------------------------------------
# Custom actions
# ---------------------------------------------------------------------------


class _SummonManaWorth(TargetedAction):
    """Instant Multiverse — summon random minions whose total Cost adds up to
    `BUDGET` Mana (12). Mirrors the Fyrakk / Rune of the Archmage idiom: pick a
    random collectible minion whose Cost fits the remaining budget, summon it,
    drain the budget, repeat. Only costed (>0) minions are eligible so the loop
    always terminates; the board cap (7) also bounds it."""

    TARGET = ActionArg()
    BUDGET = IntArg()

    def do(self, source, target, budget):
        if isinstance(budget, (list, tuple)):
            budget = budget[0]
        controller = source.controller
        for _ in range(budget):  # at most `budget` one-Cost summons
            if budget <= 0:
                return
            if len(controller.field) >= source.game.MAX_MINIONS_ON_FIELD:
                return
            candidates = [
                cid for cid, c in db.items()
                if (
                    c.collectible
                    and c.type == CardType.MINION
                    and c.cost is not None
                    and 0 < c.cost <= budget
                )
            ]
            if not candidates:
                return
            pick = source.game.random.choice(candidates)
            budget -= db[pick].cost
            source.game.cheat_action(source, [Summon(controller, pick)])


class _NatureDamageBuff(TargetedAction):
    """Flux Revenant — when a Nature spell *would* damage this minion, it gains
    +2/+1 instead (no damage is dealt). The Predamage trigger is gated to
    Nature-spell sources (`source=NATURE_SPELL`), so here we only cancel the
    queued damage and buff. The outer Predamage.do reads `target.predamage`
    when it queues the Damage action, so zeroing it cancels the hit."""

    TARGET = ActionArg()

    def do(self, source, target):
        # `source` == `target` here (the listener host minion).
        target.predamage = 0
        target.game.cheat_action(target, [Buff(target, "TIME_214e")])


class _NatureDamageSummon(TargetedAction):
    """Stormrook — when a Nature spell *would* damage this minion, summon a
    random 5-Cost minion instead (no damage is dealt). Predamage trigger is
    gated to Nature-spell sources."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.predamage = 0
        target.game.cheat_action(
            target,
            [Summon(target.controller, RandomMinion(cost=5))],
        )


def _cast_nature_while_holding(card):
    """True if any spell recorded in `spells_history_while_holding` is a Nature
    spell. History stores (id, cost) tuples."""
    history = getattr(card, "spells_history_while_holding", [])
    for entry in history:
        cid = entry[0] if isinstance(entry, (tuple, list)) else entry
        c = db.get(cid)
        if c is not None and getattr(c, "spell_school", None) == SpellSchool.NATURE:
            return True
    return False


class _OverseerBattlecry(TargetedAction):
    """Primordial Overseer — if you've cast a Nature spell while holding this,
    gain +1/+1 and draw a card."""

    TARGET = ActionArg()

    def do(self, source, target):
        if _cast_nature_while_holding(source):
            source.game.cheat_action(
                source,
                [Buff(source, "TIME_213e"), Draw(source.controller)],
            )


##
# Minions


class TIME_013:
    "Farseer Wo"
    # Elusive (in data). After you cast a spell, Discover a Nature spell from
    # the past.
    events = OWN_SPELL_PLAY.after(
        DISCOVER(RandomSpell(spell_school=SpellSchool.NATURE))
    )


class TIME_209:
    "Muradin, High King"
    # Fabled, Rush (in data). Battlecry: Equip the High King's Hammer.
    # Deathrattle: Add it to your hand.
    play = Summon(CONTROLLER, "TIME_209t")
    deathrattle = Give(CONTROLLER, "TIME_209t")


class TIME_209t:
    "High King's Hammer"
    # Windfury (in data). Deathrattle: Shuffle this into your deck with +2
    # Attack permanently.
    deathrattle = Shuffle(CONTROLLER, ExactCopy(SELF)).then(
        Buff(Shuffle.CARD, "TIME_209te")
    )


@custom_card
class TIME_209te:
    # +2 Attack (permanent, travels with the shuffled weapon copy). Not in
    # data, so registered as a custom enchantment.
    tags = {
        GameTag.CARDNAME: "High King's Hammer",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
    }


class TIME_209t2:
    "Avatar Form"
    # Give a friendly character +2 Attack and "After this attacks, deal 2
    # damage to all enemies" this turn.
    requirements = {PlayReq.REQ_FRIENDLY_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "TIME_209t2e")


class TIME_209t2e:
    "Avatar Form"
    # +2 Attack and "After this attacks, deal 2 damage to all enemies" this
    # turn. (TAG_ONE_TURN_EFFECT is in data, so the buff auto-clears at end of
    # turn — including its attack trigger.)
    tags = {GameTag.ATK: 2}
    events = Attack(OWNER).after(Hit(ENEMY_CHARACTERS, 2))


class TIME_213:
    "Primordial Overseer"
    # Battlecry: If you've cast a Nature spell while holding this, gain +1/+1
    # and draw a card.
    play = _OverseerBattlecry(SELF)


@custom_card
class TIME_213e:
    # +1/+1. Not in data, so registered as a custom enchantment.
    tags = {
        GameTag.CARDNAME: "Primordial Power",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
    }


class TIME_214:
    "Flux Revenant"
    # Taunt (in data). Whenever you would damage this with a Nature spell, it
    # gains +2/+1 instead.
    events = Predamage(SELF, source=NATURE_SPELL).on(_NatureDamageBuff(SELF))


class TIME_214e:
    "Flux Overcapacity"
    # +2/+1.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


class TIME_217:
    "Stormrook"
    # Whenever you would damage this with a Nature spell, summon a random
    # 5-Cost minion instead.
    events = Predamage(SELF, source=NATURE_SPELL).on(_NatureDamageSummon(SELF))


##
# Spells


class TIME_014:
    "Instant Multiverse"
    # Rewind. Summon 12 Mana worth of random minions. Overload: (3).
    # (Rewind + Overload are engine/data handled; only the base effect here.)
    play = _SummonManaWorth(CONTROLLER, 12)


class TIME_212:
    "Lightning Rod"
    # Deal $2 damage to a friendly minion to deal $4 damage to a random enemy
    # minion.
    requirements = {
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2), Hit(RANDOM_ENEMY_MINION, 4)


class TIME_215:
    "Thunderquake"
    # Deal $1 damage to all minions. Get a Static Shock.
    play = Hit(ALL_MINIONS, 1), Give(CONTROLLER, "TIME_218")


class TIME_216:
    "Nascent Bolt"
    # Deal $5 damage to a minion. If it survives, draw 2 cards.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 5), Dead(TARGET) | (Draw(CONTROLLER) * 2)


class TIME_218:
    "Static Shock"
    # Deal $1 damage to a minion. Give your hero +1 Attack this turn.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 1), Buff(FRIENDLY_HERO, "TIME_218e")


class TIME_218e:
    "Statically Charged"
    # +1 Attack this turn. (TAG_ONE_TURN_EFFECT is in data.)
    tags = {GameTag.ATK: 1}


# ===========================================================================
# Across the Timeways mini-set (END_ — "End Time")
# ===========================================================================


class END_030:
    "Haywire Hornswog"
    # Elusive, Taunt (both in data). Costs (1) less for each Mana Crystal
    # you've Overloaded this game. (Mirrors ICC_090 Snowfury Giant exactly.)
    cost_mod = -Attr(CONTROLLER, GameTag.OVERLOAD_THIS_GAME)
