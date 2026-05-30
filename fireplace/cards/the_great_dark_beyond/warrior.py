from ..utils import *

from hearthstone.enums import CardType


##
# Custom actions


class _SwapStats(TargetedAction):
    """Stalwart Avenger — swap this minion's Attack and Health."""

    TARGET = ActionArg()

    def do(self, source, target):
        new_atk = target.max_health
        new_health = target.atk
        target.atk = new_atk
        target.max_health = new_health
        target.damage = 0


class _AkamaRefresh(TargetedAction):
    """Exarch Akama — after this attacks, all OTHER friendly minions can attack
    again."""

    TARGET = ActionArg()

    def do(self, source, target):
        for m in source.controller.field:
            if m is source:
                continue
            m.num_attacks = 0


class _ArmExpeditionSergeant(TargetedAction):
    """Expedition Sergeant — the next Draenei you play immediately attacks a
    random enemy."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game

        def hook(played):
            enemies = (ENEMY_CHARACTERS).eval(game, played)
            if enemies:
                game.cheat_action(
                    played, [Attack(played, game.random.choice(enemies))]
                )

        source.controller.next_draenei_hooks.append(hook)


class _ArmUnyieldingVindicator(TargetedAction):
    """Unyielding Vindicator — the next Draenei you play gives your hero its
    Attack for that turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game

        def hook(played):
            game.cheat_action(
                played,
                [Buff(played.controller.hero, "GDB_232e2", atk=max(0, played.atk))],
            )

        source.controller.next_draenei_hooks.append(hook)


class _DwarfPlanet(TargetedAction):
    """Dwarf Planet — fill your board with random 2-Cost minions, each
    attacking a random enemy."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        ctrl = source.controller
        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible and c.type == CardType.MINION and (c.cost or 0) == 2
        ]
        if not pool:
            return
        while ctrl.minion_slots > 0:
            cid = source.game.random.choice(pool)
            source.game.cheat_action(source, [Summon(ctrl, cid)])
            summoned = ctrl.field[-1] if ctrl.field else None
            enemies = (ENEMY_CHARACTERS).eval(source.game, source)
            if summoned is not None and enemies:
                source.game.cheat_action(
                    source,
                    [Attack(summoned, source.game.random.choice(enemies))],
                )


##
# Minions


class GDB_226:
    """Hostile Invader"""

    # Battlecry, Spellburst, and Deathrattle: Deal 2 damage to all other
    # minions.
    play = Hit(ALL_MINIONS - SELF, 2)
    spellburst = Hit(ALL_MINIONS - SELF, 2)
    deathrattle = Hit(ALL_MINIONS - SELF, 2)


class GDB_229:
    """Expedition Sergeant"""

    # Battlecry: The next Draenei you play immediately attacks a random enemy.
    play = _ArmExpeditionSergeant(SELF)


class GDB_230:
    """Stalwart Avenger"""

    # Immune while attacking (data). At the end of EACH turn, swap this
    # minion's Attack and Health.
    events = TURN_END.on(_SwapStats(SELF))


class GDB_232:
    """Unyielding Vindicator"""

    # Battlecry: The next Draenei you play gives your hero its Attack for that
    # turn.
    play = _ArmUnyieldingVindicator(SELF)


class GDB_234:
    """Spore Empress Moldara"""

    # Start of Game: Shuffle 7 Replicating Spores into your deck.
    class Deck:
        events = GameStart().on(Shuffle(CONTROLLER, "GDB_234t") * 7)


class GDB_235:
    """Exarch Akama"""

    # After this attacks, all other friendly minions can attack again (except
    # Exarch Akama).
    events = Attack(SELF).on(_AkamaRefresh(SELF))


##
# Weapons


class GDB_231:
    """Crystalline Greatmace"""

    # After your hero attacks, give all Draenei in your hand +2 Attack.
    events = Attack(FRIENDLY_HERO).on(Buff(FRIENDLY_HAND + DRAENEI, "GDB_231e"))


##
# Spells


class GDB_227:
    """Jettison"""

    # Discover a spell. Spend 2 Armor to Discover another.
    play = Discover(CONTROLLER, RandomSpell()).then(
        Give(CONTROLLER, Discover.CARD)
    ), (Attr(FRIENDLY_HERO, GameTag.ARMOR) >= 2) & (
        GainArmor(FRIENDLY_HERO, -2),
        Discover(CONTROLLER, RandomSpell()).then(Give(CONTROLLER, Discover.CARD)),
    )


class GDB_228:
    """Captain's Log"""

    # Draw 2 cards. Costs (1) less for each Draenei you control.
    cost_mod = -Count(FRIENDLY + DRAENEI + MINION + IN_PLAY)
    play = Draw(CONTROLLER) * 2


class GDB_233:
    """Dwarf Planet"""

    # Fill your board with random 2-Cost minions that attack random enemies.
    play = _DwarfPlanet(SELF)


##
# Enchantments


class GDB_231e:
    # Vindication — +2 Attack.
    tags = {GameTag.ATK: 2}
