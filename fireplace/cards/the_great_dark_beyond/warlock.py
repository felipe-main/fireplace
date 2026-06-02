from ..utils import *

from hearthstone.enums import CardType, SpellSchool


##
# Custom actions


class _ArmForebodingFlame(TargetedAction):
    """Foreboding Flame — Demons that didn't start in your deck cost (1) less
    this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.foreboding_flame += 1


class _ArmNextDemonDiscount(TargetedAction):
    """Infernal Stratagem — your next Demon costs (2) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_demon_discount += 2


class _BadOmen(TargetedAction):
    """Bad Omen — in 2 turns summon two 6/6 Demons with Taunt; if building a
    Starship, summon them now."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.is_building_starship:
            for _ in range(2):
                source.game.cheat_action(source, [Summon(ctrl, "GDB_124t2")])
        else:
            source.game.cheat_action(source, [Buff(ctrl.hero, "GDB_124countdown")])


class _BadOmenTick(TargetedAction):
    """Bad Omen countdown — summon the two Demons after two of your turns."""

    TARGET = ActionArg()

    def do(self, source, target):
        ticks = getattr(source, "_bad_omen_ticks", 0) + 1
        source._bad_omen_ticks = ticks
        if ticks >= 2:
            ctrl = source.controller
            for _ in range(2):
                source.game.cheat_action(source, [Summon(ctrl, "GDB_124t2")])
            source.game.cheat_action(source, [Destroy(source)])


class _Healthstone(TargetedAction):
    """Healthstone — restore all damage your hero has taken this turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        amount = getattr(source.controller, "hero_damage_taken_this_turn", 0)
        if amount > 0:
            source.game.cheat_action(source, [Heal(source.controller.hero, amount)])


class _StealHealth(TargetedAction):
    """K'ara — steal 2 Health from a random enemy (it loses 2 max Health; your
    hero gains 2)."""

    TARGET = ActionArg()
    SPELL = ActionArg()

    def do(self, source, target, spell):
        enemies = (ENEMY_MINIONS).eval(source.game, source)
        if enemies:
            victim = source.game.random.choice(enemies)
            source.game.cheat_action(
                source,
                [
                    Buff(victim, "GDB_127eb", max_health=-2),
                    Buff(source.controller.hero, "GDB_127e2b", max_health=2),
                ],
            )
        # "Shadow spells don't remove this Spellburst" — re-arm so the next
        # spell triggers it again (the steal still fires on Shadow spells).
        if isinstance(spell, (list, tuple)):
            spell = spell[0] if spell else None
        if (
            spell is not None
            and spell.spell_school is not None
            and int(spell.spell_school) == int(SpellSchool.SHADOW)
        ):
            target._rearm_spellburst = True


class _Archimonde(TargetedAction):
    """Archimonde — summon every Demon you played this game that didn't start
    in your deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for card in list(ctrl.cards_played_this_game):
            if ctrl.minion_slots <= 0:
                break
            if (
                card.type == CardType.MINION
                and Race.DEMON in getattr(card, "races", [])
                and not getattr(card, "_started_in_deck", False)
            ):
                source.game.cheat_action(source, [Summon(ctrl, card.id)])


class _Consume(TargetedAction):
    """Consume — remove 1 Durability from a friendly location, then restore 8
    Health to your hero. (No effect if you control no location.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        locations = (IN_PLAY + FRIENDLY + LOCATION_CARD).eval(source.game, source)
        if not locations:
            return
        loc = locations[0]
        # Spend one durability; destroy the location if it runs out.
        loc.damage += 1
        if loc.durability <= 0:
            source.game.cheat_action(source, [Destroy(loc)])
        source.game.cheat_action(source, [Heal(ctrl.hero, 8)])


##
# Minions


class GDB_104:
    """Felfire Thrusters"""

    # Spellburst: Deal this minion's Attack damage to 2 random enemy minions.
    # Starship Piece.
    spellburst = Hit(RANDOM(ENEMY_MINIONS) * 2, ATK(SELF))


class GDB_121:
    """Foreboding Flame"""

    # Battlecry: Demons that didn't start in your deck cost (1) less this game.
    play = _ArmForebodingFlame(CONTROLLER)


class GDB_127:
    """K'ara, the Dark Star"""

    # Spellburst: Steal 2 Health from a random enemy. Shadow spells don't
    # remove this Spellburst (it re-arms so the next spell triggers it again).
    spellburst = _StealHealth(SELF, Spellburst.SPELL)


class GDB_128:
    """Archimonde"""

    # Battlecry: Summon every Demon you played this game that didn't start in
    # your deck.
    play = _Archimonde(SELF)


class SC_023:
    """Spine Crawler"""

    # Taunt, Can't attack (both in data). Has +3 Attack if you control a
    # location.
    update = (Count(IN_PLAY + FRIENDLY + LOCATION_CARD) >= 1) & Refresh(
        SELF, {GameTag.ATK: 3}
    )


##
# Locations


class SC_019:
    """Ultralisk Cavern"""

    # Deal 1 damage to all enemies. Deathrattle: Summon an 8/8 Ultralisk with
    # Rush (SC_006).
    activate = Hit(ENEMY_CHARACTERS, 1)
    deathrattle = Summon(CONTROLLER, "SC_006")


##
# Spells


class GDB_122:
    """Infernal Stratagem"""

    # Give a minion +3/+3. If it's a Demon, your next one costs (2) less.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "GDB_122e"), Find(TARGET + DEMON) & _ArmNextDemonDiscount(
        CONTROLLER
    )


class GDB_123:
    """Abduction Ray"""

    # Get a random Demon. Reduce its Cost by (2). Repeatable this turn.
    play = (
        Give(CONTROLLER, RandomMinion(race=Race.DEMON)).then(
            Buff(Give.CARD, "GDB_123e")
        ),
        Give(CONTROLLER, Buff(Copy(SELF), "GIL_000")),
    )


class GDB_124:
    """Bad Omen"""

    # In 2 turns, summon two 6/6 Demons with Taunt. If you're building a
    # Starship, summon them now.
    play = _BadOmen(SELF)


class GDB_125:
    """Healthstone"""

    # Tradeable. Restore all damage your hero has taken this turn.
    play = _Healthstone(SELF)


class GDB_126:
    """Black Hole"""

    # Destroy all minions except Demons.
    play = Destroy(ALL_MINIONS - DEMON)


class SC_020:
    """Consume"""

    # Remove 1 Durability from a friendly location to restore 8 Health to your
    # hero. Only playable while you control a friendly Location (the printed
    # REQ the engine doesn't auto-load from data), so it can't be wasted with
    # no Location in play.
    requirements = {PlayReq.REQ_FRIENDLY_LOCATION: 0}
    play = _Consume(SELF)


##
# Tokens


class GDB_124t2:
    """Felborne Overfiend"""

    # 6/6 Demon with Taunt. Stats + keyword live in data.


##
# Enchantments


class GDB_122e:
    # Infernal Strategy — +3/+3.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


@custom_card
class GDB_124countdown:
    # Bad Omen countdown — summons two 6/6 Taunt Demons after two turns.
    tags = {
        GameTag.CARDNAME: "Bad Omen",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_BEGIN.on(_BadOmenTick(SELF))


@custom_card
class GDB_123e:
    # Abduction Ray — the Demon costs (2) less.
    tags = {
        GameTag.CARDNAME: "Abduction",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class GDB_127eb:
    # Void Consumed — reduced max Health (amount supplied at Buff time).
    tags = {GameTag.HEALTH: 0}


class GDB_127e2b:
    # Consuming Void — increased max Health (amount supplied at Buff time).
    tags = {GameTag.HEALTH: 0}
