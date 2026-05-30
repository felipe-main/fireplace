from ..utils import *

from hearthstone.enums import Race


# The eight Crewmate tokens (each a 4/4 Draenei with a distinct keyword =
# its "Bonus Effect").
CREWMATES = [
    "GDB_471t",   # Engine — Divine Shield
    "GDB_471t2",  # Tactical — Taunt
    "GDB_471t3",  # Gunner — Rush
    "GDB_471t4",  # Helm — Windfury
    "GDB_471t5",  # Recon — Elusive
    "GDB_471t6",  # Research — Poisonous
    "GDB_471t7",  # Medical — Lifesteal
    "GDB_471t8",  # Admin — Reborn
]


##
# Custom actions


class _GiveRandomCrewmate(TargetedAction):
    """Add a random 4/4 Crewmate (one of the eight keyword variants) to hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        cid = source.game.random.choice(CREWMATES)
        source.game.cheat_action(source, [Give(source.controller, cid)])


class _EmergencyMeeting(TargetedAction):
    """Get two 4/4 Crewmates with a random Demon that costs (3) or less placed
    adjacently between them in hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        rng = source.game.random
        source.game.cheat_action(source, [Give(ctrl, rng.choice(CREWMATES))])
        source.game.cheat_action(
            source, [Give(ctrl, RandomMinion(race=Race.DEMON, cost=range(0, 4)))]
        )
        source.game.cheat_action(source, [Give(ctrl, rng.choice(CREWMATES))])


class _DirdraDrawCrewmates(TargetedAction):
    """Dirdra deathrattle — draw two Crewmates from the deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(2):
            pool = [c for c in ctrl.deck if c.id in CREWMATES]
            if not pool:
                break
            source.game.cheat_action(
                source, [ForceDraw(source.game.random.choice(pool))]
            )


class _StarConverge(TargetedAction):
    """Xor'toth's Stars — at the start of each of your turns the two Stars move
    one slot toward each other. When they are adjacent they collide: deal 5
    damage to all enemies and both leave the hand. Driven from Star of
    Origination so the pair resolves only once."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        hand = ctrl.hand
        origin = next((c for c in hand if c.id == "GDB_118t"), None)
        conclusion = next((c for c in hand if c.id == "GDB_118t2"), None)
        if origin is None or conclusion is None:
            return
        cards = list(hand)
        i, j = cards.index(origin), cards.index(conclusion)
        if abs(i - j) <= 1:
            source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 5)])
            origin.discard()
            conclusion.discard()
            return
        # Step each inward by one slot.
        cards.remove(origin)
        cards.remove(conclusion)
        new_i = i + 1 if i < j else i - 1
        new_j = j - 1 if i < j else j + 1
        for card, idx in sorted(
            ((origin, new_i), (conclusion, new_j)), key=lambda p: p[1]
        ):
            cards.insert(max(0, min(idx, len(cards))), card)
        del hand[:]
        hand.extend(cards)


##
# Minions


class GDB_105:
    """Shattershard Turret"""

    # Rush, Windfury, Starship Piece. Keywords + banking handled by data/engine.


class GDB_110:
    """Felfused Battery"""

    # After this attacks, give your other minions +1 Attack. Starship Piece.
    events = Attack(SELF).on(Buff(FRIENDLY_MINIONS - SELF, "GDB_110e2"))


class GDB_116:
    """Eldritch Being"""

    # Outcast and Spellburst: Shuffle your hand.
    outcast = Shuffle(CONTROLLER, FRIENDLY_HAND)
    spellburst = Shuffle(CONTROLLER, FRIENDLY_HAND)


class GDB_117:
    """Dirdra, Rebel Captain"""

    # Rush. Battlecry: Shuffle all 8 Crewmates into your deck. Deathrattle:
    # Draw two Crewmates.
    play = tuple(Shuffle(CONTROLLER, cid) for cid in CREWMATES)
    deathrattle = _DirdraDrawCrewmates(SELF)


class GDB_118:
    """Xor'toth, Breaker of Stars"""

    # Battlecry: Add two Stars to both sides of your hand. When they collide,
    # deal 5 damage to all enemies.
    play = Give(CONTROLLER, "GDB_118t2"), Give(CONTROLLER, "GDB_118t")


class GDB_471:
    """Voronei Recruiter"""

    # At the end of your turn, get a 4/4 Crewmate with a random Bonus Effect.
    events = OWN_TURN_END.on(_GiveRandomCrewmate(SELF))


##
# Spells


class GDB_119:
    """Emergency Meeting"""

    # Get two 4/4 Crewmates. Put a random Demon that costs (3) or less between
    # them.
    play = _EmergencyMeeting(SELF)


class GDB_473:
    """Headhunt"""

    # Deal $2 damage. Get a 4/4 Crewmate with a random Bonus Effect.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 2), _GiveRandomCrewmate(SELF)


class GDB_474:
    """Warp Drive"""

    # Draw 2 cards. If you're building a Starship, they cost (2) less.
    play = Draw(CONTROLLER).then(
        BUILDING_STARSHIP(CONTROLLER) & Buff(Draw.CARD, "GDB_474e")
    ) * 2


class GDB_902:
    """Infiltrate"""

    # Choose a minion. Deal $3 damage to all OTHER minions.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(ALL_MINIONS - TARGET, 3)


##
# Stars (Xor'toth)


class GDB_118t:
    """Star of Origination"""

    # Once next to Star of Conclusion, deal 5 damage to all enemies.
    class Hand:
        events = OWN_TURN_BEGIN.on(_StarConverge(SELF))


class GDB_118t2:
    """Star of Conclusion"""

    # Once next to Star of Origination, deal 5 damage to all enemies.
    # (Resolution is driven by Star of Origination.)


##
# Enchantments


class GDB_110e2:
    # Felfused — +1 Attack.
    tags = {GameTag.ATK: 1}


class GDB_474e:
    # Warp Drive — drawn card costs (2) less.
    tags = {GameTag.COST: -2}
    events = REMOVED_IN_PLAY
