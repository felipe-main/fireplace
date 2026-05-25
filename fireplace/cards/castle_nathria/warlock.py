from ..utils import *


# Castle Nathria — "Imp" is a Demon subtype; we approximate "Imp" with
# any Demon since the engine has no IMP race selector.
IMP = DEMON


##
# Spells


class REV_239:
    """Suffocating Shadows"""

    # When you play or discard this, destroy a random enemy minion.
    play = Destroy(RANDOM_ENEMY_MINION)
    events = Discard(SELF).on(Destroy(RANDOM_ENEMY_MINION))


class REV_240:
    """Tome Tampering"""

    # Shuffle 1-Cost copies of cards in your hand into your deck, then
    # discard your hand. Approximation: shuffle copies in (no Cost
    # rewrite), then discard hand.
    play = (
        Shuffle(CONTROLLER, Copy(FRIENDLY_HAND - SELF)),
        Discard(FRIENDLY_HAND - SELF),
    )


class REV_245:
    """Impending Catastrophe"""

    # Draw a card. Repeat for each Imp you control.
    play = Draw(CONTROLLER), Draw(CONTROLLER) * Count(FRIENDLY_MINIONS + IMP)


class REV_372:
    """Shadow Waltz"""

    # Summon a 3/5 Shadow with Taunt. If a minion died this turn,
    # summon another.
    play = Summon(CONTROLLER, "REV_372t"), (
        Count(KILLED_THIS_TURN + MINION) >= 1
    ) & Summon(CONTROLLER, "REV_372t")


class REV_372t:
    """Twirling Shadow"""

    tags = {GameTag.TAUNT: True}


##
# Minions


class REV_242:
    """Flustered Librarian"""

    # Has +1 Attack for each Imp you control.
    update = Refresh(SELF, {GameTag.ATK: Count(FRIENDLY_MINIONS + IMP)})


class REV_244:
    """Mischievous Imp"""

    # Battlecry: Summon a copy of this. (Infused: Summon two instead.)
    play = Summon(CONTROLLER, Copy(SELF))


class REV_244t:
    """Mischievous Imp"""

    # Infused — Summon two copies instead.
    play = Summon(CONTROLLER, Copy(SELF)) * 2


class REV_373:
    """Lady Darkvein"""

    # Battlecry: Summon two 2/1 Shades. Each gains a Deathrattle to cast
    # your last Shadow spell. Approximation: just summon the two Shades.
    play = Summon(CONTROLLER, "REV_373t") * 2


class REV_373t:
    """Shadow Manifestation"""


class REV_374:
    """Shadowborn"""

    # Deathrattle: Reduce the Cost of the highest Cost Shadow spell in
    # your hand by (3). Approximation: -3 cost on a random Shadow spell
    # in hand.
    deathrattle = Buff(RANDOM(FRIENDLY_HAND + SHADOW_SPELL), "REV_374e")


class REV_374e:
    tags = {GameTag.COST: -3}


class REV_835:
    """Imp King Rafaam"""

    # Battlecry: Resurrect four friendly Imps. (Infused: Give your Imps
    # +2/+2.)
    play = Summon(
        CONTROLLER,
        RANDOM(FRIENDLY + KILLED + MINION + IMP),
    ) * 4


class REV_835t:
    """Imp King Rafaam"""

    # Infused — resurrect four imps AND give all your imps +2/+2.
    play = (
        Summon(
            CONTROLLER, RANDOM(FRIENDLY + KILLED + MINION + IMP)
        ) * 4,
        Buff(FRIENDLY_MINIONS + IMP, "REV_835e"),
    )


class REV_835e:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


##
# Locations


class REV_371:
    """Vile Library"""

    # Give a friendly minion +1/+1. Repeat for each Imp you control.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Buff(TARGET, "REV_371e") * (
        Count(FRIENDLY_MINIONS + IMP) + 1
    )


class REV_371e:
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}
