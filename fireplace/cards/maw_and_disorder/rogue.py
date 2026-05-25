from ..utils import *



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


class _ApplyMurderTrial(TargetedAction):
    """Apply MAW_019e to the accused and re-parent the enchantment to
    the accused's controller so the FRIENDLY filter in the listener
    matches the enemy-side minions (the printed semantics)."""

    TARGET = ActionArg()

    def do(self, source, target):
        enchant = source.buff(target, "MAW_019e")
        enchant.controller = target.controller


class MAW_019:
    """Murder Accusation"""

    # Choose a minion. Destroy it after another enemy minion dies.
    # The buff lives on the accused; re-parented to the accused's
    # controller so FRIENDLY in the listener filter matches the
    # accused-side minions (i.e. enemy minions from caster's POV).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _ApplyMurderTrial(TARGET)


@custom_card
class MAW_019e:
    tags = {
        GameTag.CARDNAME: "Murder Trial",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    # `Death(FRIENDLY_MINIONS - SELF)`: from the enchantment's
    # perspective, FRIENDLY = same controller as accused = the enemy
    # player.  Self-exclusion via `- SELF` ensures the accused's own
    # death doesn't retrigger.  Use MINION + FRIENDLY (no zone gate)
    # because Death fires after zone moves to GRAVEYARD.
    events = Death(MINION + FRIENDLY - SELF).after(Destroy(OWNER))


##
# Minions


class MAW_020:
    """Scribbling Stenographer"""

    # Rush (in data). Costs (1) less for each card you've played this
    # turn.
    cost_mod = -Attr(CONTROLLER, GameTag.NUM_CARDS_PLAYED_THIS_TURN)
