from ..utils import *

from ._bonus import roll_bonus_effects


##
# Custom actions / helpers


class _KaleidosaurBonusEffects(TargetedAction):
    """Fossilized Kaleidosaur — gain two random *distinct* bonus effects.

    Bonus effects are the eight-keyword pool (Taunt, Windfury, Divine Shield,
    Poisonous, Elusive, Rush, Lifesteal, Reborn) shared with Iridescent
    Gyreworm — keyword-only, no stat change. Applied via SetTags because
    DIVINE_SHIELD / REBORN / the CANT_BE_TARGETED ("Elusive") tags are direct
    instance state, not aggregated from enchant tags.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        tags = roll_bonus_effects(source.game.random, 2)
        source.game.cheat_action(source, [SetTags(target, tags)])


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
