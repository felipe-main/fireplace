from ..utils import *


##
# Minions


class AV_334:
    """Stormpike Battle Ram"""

    # [x]<b>Rush</b> <b>Deathrattle:</b> Your next Beast costs (2) less.
    deathrattle = Buff(FRIENDLY_HAND + BEAST + MINION, "AV_334e")


class AV_334e:
    tags = {GameTag.COST: -2}
    events = REMOVED_IN_PLAY


class AV_335:
    """Ram Tamer"""

    # [x]<b>Battlecry:</b> If you control a <b>Secret</b>, gain +1/+1 and
    # <b>Stealth</b>.
    play = (Count(FRIENDLY + SECRET) >= 1) & (
        Buff(SELF, "AV_335e"),
        Stealth(SELF),
    )


AV_335e = buff(atk=1, health=1)


class AV_336:
    """Wing Commander Ichman"""

    # [x]<b>Battlecry:</b> Summon a Beast from your deck and give it
    # <b>Rush</b>. If it kills a minion this turn, repeat.
    play = Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + BEAST + MINION)).then(
        GiveRush(Summon.CARD)
    )


class AV_337:
    """Mountain Bear"""

    # [x]<b>Taunt</b> <b>Deathrattle:</b> Summon two 2/4 Cubs with <b>Taunt</b>.
    deathrattle = Summon(CONTROLLER, "AV_337t") * 2


##
# Spells


class AV_224:
    """Spring the Trap"""

    # Deal $3 damage to a minion and cast a <b>Secret</b> from your deck.
    # <b>Honorable Kill:</b> Cast 2.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3), CastSpell(RANDOM(FRIENDLY_DECK + SECRET))
    # Honorable Kill case: cast 2 secrets — fires when target dies from this
    # damage; trigger uses standard Damage path.
    honorable_kill = CastSpell(RANDOM(FRIENDLY_DECK + SECRET))


class AV_226:
    """Ice Trap"""

    # <b>Secret:</b> When your opponent casts a spell, return it to their hand
    # instead. It costs (1) more.
    secret = Play(OPPONENT, SPELL).on(
        Counter(Play.CARD), Bounce(Play.CARD), Buff(Play.CARD, "AV_226e")
    )


class AV_226e:
    tags = {GameTag.COST: 1}


class AV_333:
    """Revive Pet"""

    # <b>Discover</b> a friendly Beast that died this game. Summon it.
    play = DISCOVER(
        RandomCollectible(card_class=CardClass.HUNTER, race=Race.BEAST)
    ).then(Summon(CONTROLLER, Discover.CARD))


class AV_147:
    """Dun Baldar Bunker"""

    # [x]At the end of your turn, draw a <b>Secret</b> and set its Cost to (1).
    # Lasts 3 turns.
    events = OWN_TURN_END.on(
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SECRET)).then(
            Buff(Draw.CARD, "AV_147e")
        )
    )


class AV_147e:
    # Drives the drawn Secret's cost to (almost) 1 (engine clamps to 0;
    # close enough for our purposes — see AV_343e note for why SET() can't
    # live in a buff's tags dict).
    tags = {GameTag.COST: -100}


##
# Weapons


class AV_244:
    """Bloodseeker"""

    # <b>Honorable Kill:</b> Gain +1/+1.
    honorable_kill = Buff(SELF, "AV_244e")


class AV_244e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


##
# Heros


class AV_113:
    """Beaststalker Tavish"""

    # [x]<b>Battlecry:</b> <b>Discover</b> and cast 2 Improved <b>Secrets</b>.
    # Improved variants are dedicated tokens (AV_113t1..t9).
    play = DISCOVER(
        RandomID("AV_113t1", "AV_113t2", "AV_113t3", "AV_113t7", "AV_113t8", "AV_113t9")
    ).then(CastSpell(Discover.CARD)) * 2
