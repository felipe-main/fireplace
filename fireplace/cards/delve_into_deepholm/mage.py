from ..utils import *


##
# Spells


class DEEP_000:
    """Summoning Ward"""

    # [x]<b>Secret:</b> When your turn starts, summon a copy of your
    # highest Cost minion.
    secret = OWN_TURN_BEGIN.on(
        Find(FRIENDLY_MINIONS)
        & (
            Reveal(SELF),
            Summon(CONTROLLER, Copy(RANDOM(HIGHEST_COST(FRIENDLY_MINIONS)))),
        )
    )


class DEEP_002:
    """Elemental Companion"""

    # Summon a random Elemental Companion.
    entourage = ["DEEP_002t", "DEEP_002t2", "DEEP_002t3"]
    play = Summon(CONTROLLER, RandomEntourage())


class DEEP_002t:
    """Hiffar"""

    # Your spells cost (1) less.
    # DEEP_002te ("Haffir") is the data-side visual enchant the game stamps
    # onto each reduced spell; the engine applies the reduction directly via
    # the in-play aura below.
    update = Refresh(FRIENDLY_HAND + SPELL, {GameTag.COST: -1})


class DEEP_002te:
    """Haffir"""

    # Costs (1) less.
    tags = {GameTag.COST: -1}


class DEEP_002t2:
    """Luekk"""

    # <b>Spell Damage +2</b>
    tags = {GameTag.SPELLPOWER: 2}


class DEEP_002t3:
    """Me'sho"""

    # Can't be targeted by spells or Hero Powers.
    tags = {
        GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }


##
# Minions


class DEEP_004:
    """Mantle Shaper"""

    # Costs (1) less for each spell you've cast while holding this.
    cost_mod = -Attr(SELF, "spells_cast_while_holding")
