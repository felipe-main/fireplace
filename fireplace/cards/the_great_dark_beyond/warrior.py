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
        # Fill the board first, then have the new minions attack — the printed
        # card resolves the summons together and only afterwards swings (so a
        # later summon can't be picked as an earlier one's attack target).
        summoned = []
        while ctrl.minion_slots > 0:
            cid = source.game.random.choice(pool)
            before = set(ctrl.field)
            source.game.cheat_action(source, [Summon(ctrl, cid)])
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


def _launched_starship_this_game(player):
    """Heroes of StarCraft — "if you launched a Starship this game". The engine
    records the most-recently-launched ship on the player and never clears it
    during a game, so a non-None value is a faithful flag."""

    return getattr(player, "_last_launched_ship", None) is not None


class _StarshipLaunchDiscount(TargetedAction):
    """Heroes of StarCraft — "Your next Starship launch costs (N) less." Bumps
    the player attr the Launch Starship button (GDB_905) consumes."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        target.starship_launch_discount += amount


class _Thor(TargetedAction):
    """Thor — Battlecry: deal 5 damage to the target. If you launched a Starship
    this game, transform into Thor, Explosive Payload first and run ITS
    battlecry instead (deal 5 to the target, then repeat 5 at a random enemy for
    each Starship you've launched this game)."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        if _launched_starship_this_game(source.controller):
            game.cheat_action(source, [Morph(source, "SC_414t")])
            if target is not None and not target.dead:
                game.cheat_action(source, [Hit(target, 5)])
            launched = getattr(source.controller, "_sc_starships_launched", 0)
            for _ in range(max(0, launched)):
                enemies = [
                    c
                    for c in ENEMY_CHARACTERS.eval(game, source)
                    if not c.dead
                ]
                if not enemies:
                    break
                game.cheat_action(
                    source, [Hit(game.random.choice(enemies), 5)]
                )
        else:
            if target is not None and not target.dead:
                game.cheat_action(source, [Hit(target, 5)])


##
# Heroes of StarCraft — Terran (Warrior)


class SC_406:
    """Yamato Cannon"""

    # Starship Piece. Battlecry: Destroy a random enemy minion. Also triggers on
    # launch.
    play = Destroy(RANDOM(ENEMY_MINIONS))
    launch = Destroy(RANDOM(ENEMY_MINIONS))


class SC_411:
    """Concussive Shells"""

    # Deal $2 damage and gain 2 Armor. Your next Starship launch costs (2) less.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = (
        Hit(TARGET, 2),
        GainArmor(FRIENDLY_HERO, 2),
        _StarshipLaunchDiscount(CONTROLLER, 2),
    )


class SC_414:
    """Thor"""

    # Battlecry: Deal 5 damage.
    # (Transforms into Thor, Explosive Payload if you launched a Starship this
    # game.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = _Thor(TARGET)


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

    # Discover a spell. Spend 2 Armor to Discover another. Nest the second
    # Discover inside the first's .then() so the two choices don't collide
    # (flat-tuple Discovers all set player.choice at once — only the last wins).
    play = Discover(CONTROLLER, RandomSpell()).then(
        Give(CONTROLLER, Discover.CARD),
        (Attr(FRIENDLY_HERO, GameTag.ARMOR) >= 2)
        & (
            GainArmor(FRIENDLY_HERO, -2),
            Discover(CONTROLLER, RandomSpell()).then(
                Give(CONTROLLER, Discover.CARD)
            ),
        ),
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
