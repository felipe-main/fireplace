from ..utils import *


##
# Custom actions


class _AsteroidStrike(TargetedAction):
    """Asteroid — when drawn, deal (2 + Bolide bonus) damage to a random
    enemy."""

    TARGET = ActionArg()

    def do(self, source, target):
        dmg = 2 + getattr(source.controller, "asteroid_damage_bonus", 0)
        amount = source.controller.get_spell_damage(source, dmg)
        source.game.cheat_action(source, [Hit(RANDOM(ENEMY_CHARACTERS), amount)])


class _ArmAsteroidBonus(TargetedAction):
    """Bolide Behemoth — your Asteroids deal 1 more damage this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.asteroid_damage_bonus += 1


class _ArmPlanetaryNavigator(TargetedAction):
    """Planetary Navigator — the next Draenei you play costs (2) less but has
    Overload: (2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.next_draenei_discount = 2
        game = source.game

        def hook(played):
            game.queue_actions(played, [Overload(played.controller, 2)])

        target.next_draenei_hooks.append(hook)


class _Triangulate(TargetedAction):
    """Triangulate — Discover a different spell from your deck, then shuffle 3
    copies of it into your deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.queue_actions(
            source,
            [
                Discover(ctrl, FRIENDLY_DECK + SPELL).then(
                    Shuffle(ctrl, Discover.CARD) * 3
                )
            ],
        )


##
# Minions


class GDB_434:
    """Bolide Behemoth"""

    # Battlecry: Your Asteroids deal 1 more damage this game. Spellburst:
    # Shuffle 3 of them into your deck.
    play = _ArmAsteroidBonus(CONTROLLER)
    spellburst = Shuffle(CONTROLLER, "GDB_430") * 3


class GDB_443:
    """Cosmonaut"""

    # Battlecry: Discover a spell from your deck. Reduce its Cost by (5).
    play = Discover(CONTROLLER, FRIENDLY_DECK + SPELL).then(
        Buff(Discover.CARD, "GDB_443e")
    )


class GDB_444:
    """Planetary Navigator"""

    # Battlecry: The next Draenei you play costs (2) less, but has Overload: (2).
    play = _ArmPlanetaryNavigator(CONTROLLER)


class GDB_447:
    """Farseer Nobundo"""

    # Deathrattle: Open the Galaxy's Lens. It absorbs the power of the next
    # spell you cast. (Approximation: summons the Galaxy's Lens Location; the
    # spell-absorb interaction is simplified. Tracked in review.csv.)
    deathrattle = Summon(CONTROLLER, "GDB_136t")


class GDB_448:
    """Murmur"""

    # Your Battlecry minions cost (1), but immediately die after being played.
    # (Approximation: the cost-to-(1)/die-on-play aura is not modelled — plays
    # as a 6/6 Elemental. Tracked in review.csv.)


##
# Spells


class GDB_445:
    """Meteor Storm"""

    # Deal $5 damage to all minions. Shuffle 5 Asteroids into your deck.
    play = Hit(ALL_MINIONS, 5), Shuffle(CONTROLLER, "GDB_430") * 5


class GDB_451:
    """Triangulate"""

    # Discover a different spell from your deck. Shuffle 3 copies of it into
    # your deck.
    play = _Triangulate(SELF)


class GDB_479:
    """Nebula"""

    # Discover two 8-Cost minions to summon with Taunt and Elusive.
    play = (
        Discover(CONTROLLER, RandomMinion(cost=8)).then(
            Summon(CONTROLLER, Discover.CARD).then(
                SetTags(
                    Summon.CARD,
                    {
                        GameTag.TAUNT: True,
                        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
                        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
                    },
                )
            )
        )
    ) * 2


class GDB_864:
    """First Contact"""

    # Summon two random 1-Cost minions. Overload: (1) (data).
    play = Summon(CONTROLLER, RandomMinion(cost=1)) * 2


class GDB_901:
    """Ultraviolet Breaker"""

    # Battlecry: Deal 3 damage to an enemy minion. Shuffle 3 Asteroids into
    # your deck.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Hit(TARGET, 3), Shuffle(CONTROLLER, "GDB_430") * 3


##
# Tokens


class GDB_430:
    """Asteroid"""

    # Casts When Drawn: Deal damage to a random enemy (2 + Bolide bonus).
    play = _AsteroidStrike(SELF)


##
# Enchantments


class GDB_443e:
    # Cosmonaut — the discovered spell costs (5) less.
    tags = {GameTag.COST: -5}
