from ..utils import *

from hearthstone.enums import CardType, GameTag, Zone


##
# Custom actions / evaluators


class _HandCenterBonus(LazyNum):
    """Precise Shot — 3 damage normally, 5 if this card was EXACTLY in the
    center of your hand when cast.

    The engine only snapshots `play_left_most` / `play_right_most` before the
    card leaves the hand (it is already in PLAY by the time this script runs),
    so the exact middle index is not recoverable for hands of 5+ without an
    engine change. We compute center EXACTLY for the cases the edge snapshot
    determines unambiguously:
      * original hand size 1 -> the lone card is the center;
      * original hand size 3 -> center == the only non-edge slot, i.e. neither
        leftmost nor rightmost.
    For odd hands of 5+, a non-edge card could be off-center, so we
    conservatively DON'T grant the bonus (documented approximation). Even hands
    have no center and never qualify.
    """

    def evaluate(self, source) -> int:
        left = getattr(source, "play_left_most", False)
        right = getattr(source, "play_right_most", False)
        # Original hand size was remaining + 1 (this card has left the hand).
        original = len(source.controller.hand) + 1
        if original == 1:
            return 5
        if original == 3 and not left and not right:
            return 5
        return 3


class _SylvanasRepeat(LazyNum):
    """Windrunner sisters — base 1 cast, +1 for each of the OTHER two sisters
    you've already played this game. ids: Sylvanas TIME_609, Alleria
    TIME_609t1, Vereesa TIME_609t2."""

    SISTERS = ("TIME_609", "TIME_609t1", "TIME_609t2")

    def evaluate(self, source) -> int:
        ctrl = source.controller
        played = [c.id for c in ctrl.cards_played_this_game]
        others = [s for s in self.SISTERS if s != source.id]
        repeats = sum(played.count(s) for s in others)
        return 1 + repeats


class _SylvanasNuke(TargetedAction):
    """Ranger General Sylvanas — deal 2 damage to all enemies, repeated once
    per Alleria/Vereesa already played."""

    TARGET = ActionArg()

    def do(self, source, target):
        times = _SylvanasRepeat().evaluate(source)
        for _ in range(times):
            source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 2)])


class _AlleriaDiscover(TargetedAction):
    """Ranger Captain Alleria — Discover a spell, repeated once per
    Sylvanas/Vereesa already played."""

    TARGET = ActionArg()

    def do(self, source, target):
        times = _SylvanasRepeat().evaluate(source)
        for _ in range(times):
            source.game.cheat_action(source, [DISCOVER(RandomSpell())])


class _VereesaBuffDeck(TargetedAction):
    """Ranger Initiate Vereesa — give minions in your deck +1/+1, repeated
    once per Alleria/Sylvanas already played."""

    TARGET = ActionArg()

    def do(self, source, target):
        times = _SylvanasRepeat().evaluate(source)
        for _ in range(times):
            deck_minions = (FRIENDLY_DECK + MINION).eval(source.game, source)
            for minion in deck_minions:
                source.game.cheat_action(source, [Buff(minion, "TIME_609t2e")])


class _UntimelyResummon(TargetedAction):
    """Untimely Death — when a friendly minion dies the turn after it was
    played, reveal the secret and resummon a fresh copy of it."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, list):
            target = target[0] if target else None
        if target is None:
            return
        # "The turn after being played": the minion lived through at least one
        # turn. turn_played is the (global) turn index it entered play; for
        # this to fire it must die on a strictly later turn.
        if getattr(target, "turn_played", -1) < 0:
            return
        if target.turn_played >= source.game.turn:
            return
        ctrl = source.controller
        if ctrl.minion_slots <= 0:
            return
        source.game.cheat_action(source, [Reveal(source)])
        source.game.cheat_action(source, [Summon(ctrl, target.id)])


##
# Minions


class TIME_042:
    """King Maluk"""

    # Battlecry: Discard your hand. Get an Infinite Banana.
    play = Discard(FRIENDLY_HAND), Give(CONTROLLER, "TIME_042t")


class TIME_601:
    """Arrow Retriever"""

    # Battlecry: Draw until you have 3 cards.
    play = DrawUntil(CONTROLLER, 3)


class TIME_603:
    """Ticking Timebomb"""

    # Deathrattle: Destroy a random enemy minion.
    deathrattle = Destroy(RANDOM_ENEMY_MINION)


class TIME_605:
    """Epoch Stalker"""

    # Rush, Elusive (data). Battlecry: Summon a copy of this.
    play = Summon(CONTROLLER, Copy(SELF))


class TIME_606:
    """Quel'dorei Fletcher"""

    # Your Hero Power costs (0) while your hand has 3 or less cards.
    update = (Count(FRIENDLY_HAND) <= 3) & Refresh(
        FRIENDLY_HERO_POWER, {GameTag.COST: SET(0)}
    )


class TIME_609:
    """Ranger General Sylvanas"""

    # Fabled. Battlecry: Deal 2 damage to all enemies. If you've played
    # Alleria or Vereesa, repeat for each.
    play = _SylvanasNuke(SELF)


class TIME_609t1:
    """Ranger Captain Alleria"""

    # Battlecry: Discover a spell. If you've played Sylvanas or Vereesa,
    # repeat for each.
    play = _AlleriaDiscover(SELF)


class TIME_609t2:
    """Ranger Initiate Vereesa"""

    # Battlecry: Give minions in your deck +1/+1. If you've played Alleria or
    # Sylvanas, repeat for each.
    play = _VereesaBuffDeck(SELF)


##
# Spells


class TIME_600:
    """Precise Shot"""

    # Deal 3 damage. If this is EXACTLY in the center of your hand, deal 5.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, _HandCenterBonus())


class TIME_602:
    """Wormhole"""

    # Rewind (engine-handled). Summon a random 3-Cost Beast. It attacks a
    # random enemy.
    play = Summon(CONTROLLER, RandomBeast(cost=3)).then(
        Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
    )


class TIME_620:
    """Untimely Death"""

    # Secret: When a friendly minion dies the turn after being played,
    # resummon it.
    secret = Death(FRIENDLY + MINION).after(_UntimelyResummon(Death.ENTITY))


##
# Locations


class TIME_810:
    """Past Silvermoon"""

    # Deal 5 damage to a random enemy minion. Advance to the present.
    activate = Hit(RANDOM_ENEMY_MINION, 5), Morph(SELF, "TIME_810t1")


class TIME_810t1:
    """Present Silvermoon"""

    # Deal 5 damage to a random enemy minion. Excess hits the enemy hero.
    # Advance to the future.
    activate = (
        Hit(ENEMY_HERO, HitExcessDamage(RANDOM_ENEMY_MINION, 5)),
        Morph(SELF, "TIME_810t2"),
    )


class TIME_810t2:
    """Future Silvermoon"""

    # Deal 5 damage to the lowest Health enemy minion. Excess hits the enemy
    # hero.
    activate = Hit(ENEMY_HERO, HitExcessDamage(LOWEST_HEALTH(ENEMY_MINIONS), 5))


##
# Tokens


class TIME_042t:
    """Infinite Banana"""

    # Give a minion +1/+1. (This stays in your hand — returns a fresh copy.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "TIME_042te"), Give(CONTROLLER, "TIME_042t")


##
# Enchantments


class TIME_042te:
    """Infinite Banana"""

    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class TIME_609t2e:
    """Windrunner's Allegiance"""

    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}
