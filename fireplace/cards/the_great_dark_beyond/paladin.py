from ..utils import *


##
# Custom actions


class _ReduceLibrams(TargetedAction):
    """Interstellar Wayfarer / Starslicer — your Librams cost (1) less for the
    rest of the game."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.libram_discount += 1


class _YrelLibrams(TargetedAction):
    """Yrel — get three different Librams from an older timeline (Wild
    collectible Librams)."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.tags.get(GameTag.LIBRAM, 0)
            and not getattr(c, "is_standard", False)
        ]
        if len(pool) < 3:
            pool = [
                cid
                for cid, c in _db.items()
                if c.collectible and c.tags.get(GameTag.LIBRAM, 0)
            ]
        rng = source.game.random
        rng.shuffle(pool)
        for cid in pool[:3]:
            source.game.cheat_action(source, [Give(source.controller, cid)])


class _LibramReturn(TargetedAction):
    """Libram of Divinity — when cast for (0), mark this spell to return to its
    caster's hand at the end of the turn (processed in game.end_turn_cleanup)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.controller._librams_to_return.append(target)


class _CelestialAura(TargetedAction):
    """Celestial Aura — attach a continuous 2-turn aura host to the caster's
    hero. While its controller has exactly one minion, that minion is set to
    10/10; the host is torn down after the controller's second turn-end
    (game.end_turn_cleanup decrements ``_celestial_turns_left``)."""

    TARGET = ActionArg()

    def do(self, source, target):
        hero = source.controller.hero
        source.buff(hero, "GDB_140host", _celestial_turns_left=2)


##
# Minions


class GDB_144:
    """Lumia"""

    # Lifesteal. After a hero takes damage, they become Immune for the rest of
    # the turn.
    events = Damage(ALL_HEROES).on(Buff(Damage.TARGET, "GDB_144e"))


class GDB_721:
    """Interstellar Wayfarer"""

    # Divine Shield (data). Battlecry: Reduce the Cost of your Librams by (1)
    # this game.
    play = _ReduceLibrams(CONTROLLER)


class GDB_728:
    """Interstellar Researcher"""

    # Battlecry and Spellburst: Draw a Libram.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + LIBRAM))
    spellburst = ForceDraw(RANDOM(FRIENDLY_DECK + LIBRAM))


##
# Weapons


class GDB_726:
    """Interstellar Starslicer"""

    # Battlecry and Deathrattle: Reduce the Cost of your Librams by (1) this
    # game.
    play = _ReduceLibrams(CONTROLLER)
    deathrattle = _ReduceLibrams(CONTROLLER)


##
# Spells


class GDB_137:
    """Libram of Clarity"""

    # Draw 2 minions. If this costs (0), give them +2/+1. Gate on the effective
    # play cost (Attr _played_cost), not the raw COST tag, so a Libram made free
    # by Wayfarer/Starslicer discount counts.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION)).then(
        (Attr(SELF, "_played_cost") == 0) & Buff(ForceDraw.TARGET, "GDB_137e1")
    ) * 2


class GDB_138:
    """Libram of Divinity"""

    # Give a minion +3/+3. If this costs (0), return THIS to your hand at the
    # end of your turn. Gate on the effective play cost (_played_cost), so a
    # Libram made free by Wayfarer/Starslicer counts.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "GDB_138e"), (Attr(SELF, "_played_cost") == 0) & _LibramReturn(
        SELF
    )


class GDB_139:
    """Libram of Faith"""

    # Summon three 3/3 Draenei with Divine Shield. If this costs (0), give them
    # Rush.
    play = Summon(CONTROLLER, "GDB_139t") * 3, (
        Attr(SELF, "_played_cost") == 0
    ) & SetTags(FRIENDLY_MINIONS + DRAENEI, {GameTag.RUSH: True})


class GDB_140:
    """Celestial Aura"""

    # While you have exactly 1 minion in play, its Attack and Health are 10.
    # Lasts 2 turns.
    play = _CelestialAura(SELF)


class GDB_141:
    """Yrel, Beacon of Hope"""

    # Rush (data). Deathrattle: Get three different Librams from an older
    # timeline!
    deathrattle = _YrelLibrams(SELF)


class GDB_462:
    """Orbital Satellite"""

    # Discover a Draenei. If you played an adjacent card this turn, Discover
    # another.
    # Nest the conditional second Discover inside the first's .then() — a flat
    # tuple of Discovers all set player.choice at once and only the last wins.
    play = Discover(CONTROLLER, RandomMinion(race=Race.DRAENEI)).then(
        Give(CONTROLLER, Discover.CARD),
        (Attr(SELF, "adjacent_plays_this_turn") >= 1)
        & Discover(CONTROLLER, RandomMinion(race=Race.DRAENEI)).then(
            Give(CONTROLLER, Discover.CARD)
        ),
    )


##
# Tokens


class GDB_139t:
    """Lightforged Draenei"""

    # 3/3 Draenei with Divine Shield. Stats + keyword live in data.


##
# Enchantments


class GDB_137e1:
    # Clarity — +2/+1.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


class GDB_138e:
    # Divine Learnings — +3/+3.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class GDB_144e:
    # Lumia's Protection — Immune.
    tags = {GameTag.CANT_BE_DAMAGED: True}


class GDB_140e:
    # Celestial — the lone minion's Attack and Health are set to 10. Applied
    # continuously by the GDB_140host aura while you control exactly one minion.
    atk = SET(10)
    max_health = SET(10)


@custom_card
class GDB_140host:
    # Engine-internal host for Celestial Aura's continuous 2-turn aura. Lives on
    # the caster's hero; while the controller has exactly one minion it refreshes
    # the GDB_140e set-stat enchant onto it. Not a real card (no data entry).
    tags = {
        GameTag.CARDNAME: "Celestial Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = (Count(FRIENDLY + MINION + IN_PLAY) == 1) & Refresh(
        FRIENDLY_MINIONS, buff="GDB_140e"
    )
