from ..utils import *


##
# Custom actions


class _EldritchSweep(TargetedAction):
    """Eldritch Tentacles — deal ``amount`` damage to all minions, then repeat
    with 1 less damage until the damage would drop to 0. Re-entrant: each tier
    re-queues the next via cheat_action so the broadcast/death pipeline resolves
    between waves (matching the card's repeated AoE)."""

    TARGET = ActionArg()
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if amount <= 0:
            return
        minions = source.game.board[:]  # all minions in play, both sides
        if minions:
            source.game.queue_actions(source, [Hit(minions, amount)])
        source.game.cheat_action(source, [_EldritchSweep(source, amount - 1)])


class _CursedChainsReturn(TargetedAction):
    """Cursed Chains return-control tick. The enchant fires on every TURN_END;
    return the minion to its original owner only once the opponent of its
    *current* controller has finished a turn — i.e. skip the turn-end of the
    player who stole it, returning at the end of *their* (the original owner's)
    turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        owner = source  # the enchant
        minion = owner.owner
        # Return at any TURN_END that is NOT the stealing player's own turn end,
        # i.e. the original owner's turn (the enemy's turn from the thief's POV).
        thief = minion.controller
        if minion.game.current_player is thief:
            return  # still the thief's turn — keep the minion one more turn
        minion.game.cheat_action(
            owner, [Steal(minion, minion.controller.opponent), Destroy(owner)]
        )


##
# Minions


class _OcularOccultist(TargetedAction):
    """Taunt. Battlecry: Choose a card in your hand to discard."""

    TARGET = ActionArg()

    def do(self, source, target):
        choose_hand_card(
            source,
            lambda s, c: s.game.cheat_action(s, [Discard(c)]),
        )


class CATA_490:
    """Ocular Occultist"""

    # Taunt. Battlecry: Choose a card in your hand to discard.
    play = _OcularOccultist(SELF)


class CATA_493:
    """Duke of Below"""

    # Rush. Has +2/+2 for each card you've discarded this game.
    play = (Count(FRIENDLY + DISCARDED) >= 1) & Buff(
        SELF,
        "CATA_493e",
        atk=Count(FRIENDLY + DISCARDED) * 2,
        max_health=Count(FRIENDLY + DISCARDED) * 2,
    )


class CATA_493e:
    """Binding Nightmare"""

    tags = {GameTag.ATK: 0, GameTag.HEALTH: 0}


class CATA_494:
    """Maloriak"""

    # After you discard a minion, summon a copy of it.
    events = Discard(FRIENDLY + MINION).on(
        Summon(CONTROLLER, Copy(Discard.TARGET))
    )


class CATA_725:
    """Shadowsworn Disciple"""

    # Battlecry: Herald {0}. Deathrattle: Restore 3 Health to your hero.
    play = Herald(CONTROLLER)
    deathrattle = Heal(FRIENDLY_HERO, 3)


class CATA_726:
    """Cho'gall, Mastermind"""

    # Colossal +2. (Arms are engine-summoned from CATA_726t / CATA_726t1.)
    # "Your Arms and Soldiers destroy minions in the enemy's deck instead" is a
    # board-state aura we approximate as the limbs' default destroy-the-right
    # behaviour (the deck-destruction variant is cosmetic at our fidelity).
    pass


##
# Spells


class CATA_491:
    """Eldritch Tentacles"""

    # Deal 3 damage to all minions. Repeat this with 1 less damage.
    play = _EldritchSweep(CONTROLLER, 3)


class CATA_496:
    """Cursed Chains"""

    # Take control of an enemy minion until the end of their turn.
    # It can't attack this turn.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Steal(TARGET), Buff(TARGET, "CATA_496e")


class CATA_496e:
    """Cursed Chains"""

    # Switched control, but can't attack this turn; return at end of their turn.
    events = TURN_END.on(_CursedChainsReturn(SELF))
    tags = {GameTag.CANT_ATTACK: True}


class CATA_498(SchemeUtils):
    """Rafaams' Last Stand"""

    # Deal $@ damage to two random enemy minions. (Upgrades each turn!)
    # Base damage from TAG_SCRIPT_DATA_NUM_1 (2), +1 per turn held (progress).
    play = Hit(
        RANDOM_ENEMY_MINION * 2,
        Attr(SELF, GameTag.TAG_SCRIPT_DATA_NUM_1) + Attr(SELF, GameTag.QUEST_PROGRESS),
    )


class CATA_499:
    """Disposable Acolytes"""

    # When you play or discard this, summon two random 1-Cost minions.
    play = Summon(CONTROLLER, RandomMinion(cost=1)) * 2
    discard = Summon(CONTROLLER, RandomMinion(cost=1)) * 2


##
# Location


class CATA_492:
    """Shrine of Twilight"""

    # Herald {0}. Draw a card.
    activate = Herald(CONTROLLER), Draw(CONTROLLER)


##
# Tokens (Soldier / Arms — shared end-of-turn "destroy the minion to the right
# to gain +N/+N" effect). N = base (2) + heralds, approximating the
# "Herald twice/once to upgrade" ramp.


class _SoulConsumeGain(LazyNum):
    """+N/+N gain = base TAG_SCRIPT_DATA_NUM_1 (2) plus Heralds, capped at two
    upgrades ("Herald twice to upgrade" then "once") = base + min(heralds, 2),
    matching every sibling Cataclysm Herald-upgrade token."""

    def evaluate(self, source):
        base = source.data.tags.get(GameTag.TAG_SCRIPT_DATA_NUM_1, 2)
        return base + min(source.controller.heralds_this_game, 2)


class _SoulConsume(TargetedAction):
    """At the end of your turn, destroy the minion to the right; gain +N/+N."""

    TARGET = ActionArg()

    def do(self, source, target):
        if source.zone != Zone.PLAY:
            return
        right = source.right_minion
        if not right:
            return  # nothing to the right -> no destroy, no gain
        gain = _SoulConsumeGain().evaluate(source)
        source.game.cheat_action(
            source,
            [Destroy(right[0]), Buff(source, "CATA_726te", atk=gain, max_health=gain)],
        )


class CATA_725t:
    """Soldier of Cho'gall"""

    events = OWN_TURN_END.on(_SoulConsume(SELF))


class CATA_726t:
    """Cho's Arm"""

    events = OWN_TURN_END.on(_SoulConsume(SELF))


class CATA_726t1:
    """Gall's Arm"""

    events = OWN_TURN_END.on(_SoulConsume(SELF))


class CATA_726te:
    """Souldrain"""

    tags = {GameTag.ATK: 0, GameTag.HEALTH: 0}


class CATA_726e2:
    """Embiggened"""

    tags = {GameTag.ATK: 0, GameTag.HEALTH: 0}
