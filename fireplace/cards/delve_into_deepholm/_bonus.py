from ..utils import *


# The eight Delve into Deepholm / Badlands "bonus effects" are keyword-only
# (no stat change). Pool per hearthstone.wiki.gg/wiki/Bonus_effect:
#   Taunt, Windfury, Divine Shield, Poisonous, Elusive, Rush, Lifesteal, Reborn
# "Elusive" = can't be targeted by spells or Hero Powers (two engine tags).
#
# These are applied with SetTags rather than tag-only Buff enchants:
# DIVINE_SHIELD / REBORN / the CANT_BE_TARGETED tags are stored as direct
# instance state, not aggregated from enchant tags, so a Buff enchant carrying
# them would never take effect. (Reusing the Showdown "Chameleon" enchants
# WW_810t*e1 would also be wrong: those grant +3/+3 AND a spurious
# "Deathrattle: Summon a Chameleon".)
BONUS_EFFECTS = (
    {GameTag.TAUNT: True},
    {GameTag.WINDFURY: True},
    {GameTag.DIVINE_SHIELD: True},
    {GameTag.POISONOUS: True},
    {GameTag.CANT_BE_TARGETED_BY_SPELLS: True,
     GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True},  # Elusive
    {GameTag.RUSH: True},
    {GameTag.LIFESTEAL: True},
    {GameTag.REBORN: True},
)


def roll_bonus_effects(rng, count):
    """Return a merged tag dict of `count` distinct random bonus effects,
    drawn from the eight-keyword pool using the game's deterministic RNG."""
    merged = {}
    for spec in rng.sample(BONUS_EFFECTS, count):
        merged.update(spec)
    return merged
