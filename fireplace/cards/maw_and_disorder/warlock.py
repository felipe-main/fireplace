from ..utils import *


##
# Spells


from .priest import _AccusationFireArson


class _ArsonAccuse(TargetedAction):
    """Stamp the chosen minion onto controller._arson_accused and arm
    the per-controller hero-damage trigger via Buff(MAW_001e)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl._arson_accused = list(getattr(ctrl, "_arson_accused", [])) + [target]
        if not getattr(ctrl, "_arson_armed", False):
            ctrl._arson_armed = True
            source.buff(ctrl.hero, "MAW_001e")


class MAW_001:
    """Arson Accusation"""

    # Choose a minion. Destroy it after your hero takes damage.
    # Approximation: silence on the accused does not break the deathlink
    # (the link lives on the caster's hero, not on the accused).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _ArsonAccuse(TARGET)


@custom_card
class MAW_001e:
    tags = {
        GameTag.CARDNAME: "Arson Trial",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = Damage(OWNER).on(_AccusationFireArson(CONTROLLER))


class _HabeasResurrect(TargetedAction):
    """Discover-from-graveyard approximation: pick a random friendly
    minion that died this game, resurrect it with Rush and an end-of-
    turn auto-destroy."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType
        pool = [c for c in target.graveyard if c.type == CardType.MINION]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        source.game.cheat_action(source, [Summon(target, pick.id)])
        # Find the just-summoned copy and stamp Rush + end-of-turn death.
        for m in target.field:
            if m.id == pick.id and not getattr(m, "_habeas_marked", False):
                m._habeas_marked = True
                source.game.cheat_action(
                    source, [GiveRush(m), Buff(m, "MAW_002e")]
                )
                break


class MAW_002:
    """Habeas Corpses"""

    # Discover a friendly minion to resurrect and give it Rush. It dies
    # at the end of turn. Approximated as a random resurrection from the
    # friendly graveyard (Discover UI not modeled).
    play = _HabeasResurrect(CONTROLLER)


@custom_card
class MAW_002e:
    tags = {
        GameTag.CARDNAME: "Habeas Corpse",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(Destroy(OWNER))


##
# Minions


class _ImpOsterMorph(TargetedAction):
    """Pick a random friendly Imp on the board (excluding Imp-oster) and
    morph Imp-oster into a copy of it. No-op if no other Imps."""

    TARGET = ActionArg()

    def do(self, source, target):
        from fireplace.dsl.selector import IMP
        pool = IMP.eval(target.controller.field, source)
        pool = [m for m in pool if m is not target]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        source.game.cheat_action(source, [Morph(target, pick.id)])


class MAW_000:
    """Imp-oster"""

    # Battlecry: Choose a friendly Imp. Transform into a copy of it.
    # Approximated as random-friendly-Imp transform (no UI choice).
    play = _ImpOsterMorph(SELF)
