from ..utils import *

from .priest import _AccusationFireMurder


##
# Spells


class _PerjuryFire(TargetedAction):
    """Perjury secret: when controller's turn starts, Discover (random
    pick) and cast a Secret from another class."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardClass, GameTag, CardType
        from fireplace.cards import db
        hero_class = target.hero.card_class
        pool = [
            c for c in db.values()
            if c.type == CardType.SPELL
            and c.tags.get(GameTag.SECRET)
            and c.collectible
            and c.card_class not in (CardClass.NEUTRAL, hero_class)
        ]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        source.game.cheat_action(
            source, [Reveal(source), CastSpell(pick.id)]
        )


class MAW_018:
    """Perjury"""

    # Secret: When your turn starts, Discover and cast a Secret from
    # another class. Approximated as random Secret from another class.
    secret = OWN_TURN_BEGIN.on(_PerjuryFire(CONTROLLER))


class _MurderAccuse(TargetedAction):
    """Stamp the chosen enemy minion onto controller._murder_accused;
    arm the controller via Buff(MAW_019e). The arm listens for any
    enemy-minion death (the printed condition is 'after another enemy
    minion dies' — i.e., excluding the accused itself; we approximate
    by checking the dying minion is not the accused)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl._murder_accused = list(getattr(ctrl, "_murder_accused", [])) + [target]
        if not getattr(ctrl, "_murder_armed", False):
            ctrl._murder_armed = True
            # Direct .buff() bypasses the selector eval path; cheat_action
            # context doesn't resolve a hero entity passed in literally.
            source.buff(ctrl.hero, "MAW_019e")


class MAW_019:
    """Murder Accusation"""

    # Choose a minion. Destroy it after another enemy minion dies.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _MurderAccuse(TARGET)


@custom_card
class MAW_019e:
    tags = {
        GameTag.CARDNAME: "Murder Trial",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    # Death(MINION + ENEMY) — note: the engine sets card.zone = GRAVEYARD
    # BEFORE broadcasting the Death event, so ENEMY_MINIONS (which has
    # an IN_PLAY constraint) never matches.  Use MINION + ENEMY (no
    # zone gate).  Per-friendly-controller filter happens via the
    # ENEMY selector (controller == opponent of source).
    events = Death(MINION + ENEMY).after(_AccusationFireMurder(CONTROLLER))


##
# Minions


class MAW_020:
    """Scribbling Stenographer"""

    # Rush (in data). Costs (1) less for each card you've played this
    # turn.
    cost_mod = -Attr(CONTROLLER, GameTag.NUM_CARDS_PLAYED_THIS_TURN)
