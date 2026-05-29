from ..utils import *


##
# Custom actions / helpers


class _KaleidosaurBonusEffects(TargetedAction):
    """Fossilized Kaleidosaur — gain two random *distinct* bonus effects.

    The eight bonus effects are the standard keyword pool: Divine Shield,
    Taunt, Rush, Windfury, Stealth, Poisonous, Lifesteal, Reborn. We pick
    two distinct keywords and stamp them on this minion.

    These keywords must be applied with SetTags, not a tag-only Buff
    enchant: DIVINE_SHIELD / REBORN / STEALTH are stored as direct
    instance attributes on Minion (not aggregated from enchant tags), so a
    Buff enchant carrying GameTag.DIVINE_SHIELD never flips card.divine_shield
    nor absorbs damage. SetTags writes the tags directly and is how the
    engine grants these keywords elsewhere (cf. Darkmoon Faire paladin).
    """

    TARGET = ActionArg()

    _BONUS_KEYWORDS = (
        GameTag.DIVINE_SHIELD,
        GameTag.TAUNT,
        GameTag.RUSH,
        GameTag.WINDFURY,
        GameTag.STEALTH,
        GameTag.POISONOUS,
        GameTag.LIFESTEAL,
        GameTag.REBORN,
    )

    def do(self, source, target):
        import random

        chosen = random.sample(self._BONUS_KEYWORDS, 2)
        source.game.cheat_action(
            source, [SetTags(target, {kw: True for kw in chosen})]
        )


##
# Spells


class DEEP_018:
    """Shroomscavate"""

    # Give a minion Windfury and Divine Shield. Excavate a treasure.
    # DIVINE_SHIELD is a direct Minion instance attribute, not aggregated
    # from enchant tags, so a Buff enchant would never flip it — use SetTags
    # (the same primitive Darkmoon Faire paladin uses to grant Divine Shield).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        SetTags(TARGET, {GameTag.WINDFURY: True, GameTag.DIVINE_SHIELD: True}),
        Excavate(CONTROLLER),
    )


##
# Minions


class DEEP_007:
    """Sir Finley, the Intrepid"""

    # Battlecry: If you've Excavated twice, transform all enemy minions
    # into 1/1 Murlocs.
    play = (Attr(CONTROLLER, "excavates_this_game") >= 2) & Morph(
        ENEMY_MINIONS, "PRO_001at"
    )


class DEEP_033:
    """Fossilized Kaleidosaur"""

    # Battlecry: Gain two random bonus effects. Excavate a treasure.
    play = _KaleidosaurBonusEffects(SELF), Excavate(CONTROLLER)
