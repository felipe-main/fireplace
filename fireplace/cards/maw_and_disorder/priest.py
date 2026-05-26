from ..utils import *


##
# Spells


class MAW_021:
    """Clear Conscience"""

    # Give a friendly minion +2/+3 and "Only you can target this with
    # spells and Hero Powers."
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = Buff(TARGET, "MAW_021e")


class MAW_021e:
    tags = {
        GameTag.ATK: 2,
        GameTag.HEALTH: 3,
        GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
    }


class _TheftAccuse(TargetedAction):
    """Stamp the chosen minion onto controller._theft_accused and arm
    the controller via Buff(MAW_023e).  Per-card provenance
    (`_copied_from_opponent`) is now tracked — see the gate in
    _TheftFireIfCopied."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl._theft_accused = list(getattr(ctrl, "_theft_accused", [])) + [target]
        if not getattr(ctrl, "_theft_armed", False):
            ctrl._theft_armed = True
            source.buff(ctrl.hero, "MAW_023e")


class _TheftFireIfCopied(TargetedAction):
    """Theft Trial: only destroy accused minions if the played card
    carries the `_copied_from_opponent` flag.  Otherwise no-op."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import Zone
        if not source.event_args:
            return
        played_card = source.event_args[1] if len(source.event_args) > 1 else None
        if not played_card or not getattr(played_card, "_copied_from_opponent", False):
            return
        accused = list(getattr(target, "_theft_accused", []))
        live = [m for m in accused if getattr(m, "zone", None) == Zone.PLAY]
        setattr(target, "_theft_accused", [])
        if live:
            source.game.cheat_action(source, [Destroy(live)])


def _make_accusation_fire(flag):
    """Build a TargetedAction that destroys minions in
    controller._<flag>_accused that are still in PLAY. We can't pass
    the flag as an ActionArg (TargetedAction's evaluator runs every
    arg through card-lookup); subclass per-flag instead.

    For Death-triggered flags (murder), skip if the dying minion IS the
    only accused — printed text says "ANOTHER enemy minion dies"."""

    class _AccusationFire(TargetedAction):
        TARGET = ActionArg()
        FLAG = flag

        def do(self, source, target):
            from hearthstone.enums import Zone
            attr = f"_{self.FLAG}_accused"
            accused = list(getattr(target, attr, []))
            # Death triggers pass the dying card in event_args[0].
            # Drop it from the "other minion dies" trigger so the
            # accused doesn't fire from its own death.
            dying = None
            if source.event_args:
                dying = source.event_args[0]
            still_accused = [m for m in accused if m is not dying]
            live = [
                m for m in still_accused
                if getattr(m, "zone", None) == Zone.PLAY
            ]
            # Reset the accused list — but if the dying card was an
            # accused, leave it out (it's already in graveyard); if
            # ALL accused are still alive (Damage / Play triggers),
            # they fire and the list resets.
            setattr(target, attr, [m for m in accused if m is dying and m is not None])
            if live:
                source.game.cheat_action(source, [Destroy(live)])

    _AccusationFire.__name__ = f"_AccusationFire_{flag}"
    return _AccusationFire


_AccusationFireTheft = _make_accusation_fire("theft")
_AccusationFireMurder = _make_accusation_fire("murder")
_AccusationFireArson = _make_accusation_fire("arson")


class MAW_023:
    """Theft Accusation"""

    # Choose a minion. Destroy it after you play a card copied from the
    # opponent. Approximation: fires on the next Play(CONTROLLER) since
    # we don't track per-card 'copied from opponent' provenance.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _TheftAccuse(TARGET)


@custom_card
class MAW_023e:
    tags = {
        GameTag.CARDNAME: "Theft Trial",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = Play(CONTROLLER).after(_TheftFireIfCopied(CONTROLLER))


##
# Minions


class _IncriminatingPsychicCopy(TargetedAction):
    """Deathrattle: copy a random card from the opponent's hand into
    the controller's hand.  Stamps the copy with
    `_copied_from_opponent = True` so Theft Accusation can recognize
    it (the printed text uses "card copied from the opponent")."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp_hand = list(target.opponent.hand)
        if not opp_hand:
            return
        pick = source.game.random.choice(opp_hand)
        before_ids = {id(c) for c in target.hand}
        source.game.cheat_action(source, [Give(target, pick.id)])
        for c in target.hand:
            if id(c) not in before_ids:
                c._copied_from_opponent = True


class MAW_022:
    """Incriminating Psychic"""

    # Taunt (in data). Deathrattle: Copy a random card from your
    # opponent's hand into your hand.
    deathrattle = _IncriminatingPsychicCopy(CONTROLLER)
