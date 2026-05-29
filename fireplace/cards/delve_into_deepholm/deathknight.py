from ..utils import *


##
# Minions


class DEEP_015:
    """Prosthetic Hand"""

    # <b>Magnetic</b>, <b>Reborn</b> Can <b>Magnetize</b> to Mechs or Undead.
    # Reborn is carried by the REBORN data tag. Magnetic merges this minion's
    # stats into the Mech OR Undead to its right (custom selector — the default
    # MAGNETIC helper only matches Mechs).
    magnetic = Find(RIGHT_OF(SELF) + (MECH | UNDEAD)) & (
        Buff(RIGHT_OF(SELF), "DEEP_015e", atk=ATK(SELF), max_health=CURRENT_HEALTH(SELF)),
        Remove(SELF),
    )


# Increased stats. (Magnetic enchantment — stats supplied at runtime.)
DEEP_015e = buff()


##
# Weapons


class DEEP_016:
    """Quartzite Crusher"""

    # <b>Lifesteal</b>. <b>Freeze</b> any character damaged by your hero.
    # Lifesteal is a data tag. Any character the equipped hero damages
    # (attacks, Hero Power, etc.) gets Frozen.
    events = Damage(ALL_CHARACTERS, source=FRIENDLY_HERO).after(Freeze(Damage.TARGET))


##
# Spells


class DEEP_017:
    """Mining Casualties"""

    # Summon two 1/1 Silver Hand Recruits with
    # "<b>Deathrattle:</b> Summon a 1/1 Frail Ghoul".
    # Summon two Silver Hand Recruits (CS2_101t), each granted the
    # Unfortunate Fate (DEEP_017e) deathrattle enchantment.
    play = Summon(CONTROLLER, "CS2_101t").then(Buff(Summon.CARD, "DEEP_017e")) * 2


# Unfortunate Fate — Deathrattle: Summon a 1/1 Frail Ghoul (HERO_11bpt).
class DEEP_017e:
    """Unfortunate Fate"""

    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Summon(CONTROLLER, "HERO_11bpt")
