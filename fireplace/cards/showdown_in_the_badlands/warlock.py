"""Showdown in the Badlands — Warlock cards (WILD_WEST)."""

from ..utils import *


# ---------------------------------------------------------------------------
# Sludge / "When this is played, discarded, or destroyed" support.
#
# Barrel of Sludge (WW_044t) and Furnace Fuel (WW_441) each carry an effect
# that fires on three triggers:
#   * played    -> handled by the card's `play` script.
#   * discarded -> handled by the card's `discard` script (the engine runs
#                  `get_actions("discard")` from inside Discard.do).
#   * destroyed -> there is no engine event for a card being destroyed while
#                  it sits in the deck.  The only things in this set that
#                  destroy deck cards are Waste Remover (WW_042) and Fracking
#                  (WW_092), so both route their destruction through the
#                  custom `_SludgeDestroy` action below, which fires the
#                  destroyed-trigger before moving the card to the graveyard.
#
# The destroyed-trigger is registered per card id in `_SLUDGE_ON_DESTROY`.
# The effect is queued with the destroyed card itself as the source, so e.g.
# Barrel of Sludge's damage is attributed to the Barrel.
# ---------------------------------------------------------------------------

# id -> a function (source_card) -> list of actions to queue when destroyed.
_SLUDGE_ON_DESTROY = {
    # Barrel of Sludge: deal 3 damage to the lowest Health enemy.
    "WW_044t": lambda card: [Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 3)],
    # Furnace Fuel: draw 2 cards.
    "WW_441": lambda card: [Draw(CONTROLLER) * 2],
}


def _destroy_with_trigger(source, card):
    """Fire a card's destroyed-trigger (if any), then move it to the
    graveyard.  The trigger is queued with the destroyed card as source."""
    effect = _SLUDGE_ON_DESTROY.get(card.id)
    if effect is not None:
        card.game.cheat_action(card, effect(card))
    card.zone = Zone.GRAVEYARD


class _Fracking(Dredge):
    """
    Fracking: look at the bottom 3 cards of the deck, draw the chosen one
    and destroy the other two (firing their destroyed-triggers).  Reuses
    Dredge's choice UI, overriding `choose` to draw + destroy instead of
    putting the pick on top.
    """

    def choose(self, card):
        if card not in self.cards:
            raise InvalidAction(
                "%r is not a valid Fracking choice (one of %r)"
                % (card, self.cards)
            )
        self.player.choice = None
        others = [c for c in self.cards if c is not card]
        # Draw the chosen card.
        self.source.game.queue_actions(self.source, [Draw(self.player, card)])
        # Destroy the rest, firing their destroyed-triggers.
        for other in others:
            _destroy_with_trigger(self.source, other)
        for action in self._callback:
            self.source.game.trigger(
                self.source, [action], [self.target, self.cards, card]
            )
        self.callback = self._callback
        self.trigger_choice_callback()


class _WasteRemove(TargetedAction):
    """
    Destroy the bottom 3 cards of the target player's deck (Waste Remover).
    deck[0] is the bottom, so the bottom 3 are deck[:3].  Fires each
    destroyed card's destroyed-trigger.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        for card in list(target.deck[:3]):
            _destroy_with_trigger(source, card)
            source.game.manager.targeted_action(self, source, target)
        return []


##
# Minions


class WW_041:
    """Disposal Assistant"""

    # Battlecry and Deathrattle: Put a Barrel of Sludge on the bottom of
    # your deck.
    play = PutOnBottom(CONTROLLER, "WW_044t")
    deathrattle = PutOnBottom(CONTROLLER, "WW_044t")


class WW_042:
    """Waste Remover"""

    # At the end of your turn, destroy the bottom 3 cards of your deck.
    events = OWN_TURN_END.on(_WasteRemove(CONTROLLER))


class WW_043:
    """Sludge on Wheels"""

    # Rush. Whenever this takes damage, get a Barrel of Sludge and add one
    # to the bottom of your deck.
    events = SELF_DAMAGE.on(
        Give(CONTROLLER, "WW_044t"), PutOnBottom(CONTROLLER, "WW_044t")
    )


class WW_091:
    """Pop'gar the Putrid"""

    # Your Fel spells cost (1) less and have Lifesteal.
    # Battlecry: Get two Barrels of Sludge.
    update = Refresh(
        FRIENDLY + SPELL + FEL_SPELL,
        {GameTag.COST: -1, GameTag.LIFESTEAL: True},
    )
    play = Give(CONTROLLER, "WW_044t") * 2


class WW_437:
    """Tram Conductor Gerry"""

    # Battlecry: If you've Excavated twice, summon six 3/3 Tram Cars with
    # Rush.
    play = (Attr(CONTROLLER, "excavates_this_game") >= 2) & (
        Summon(CONTROLLER, "WW_437t") * 6
    )


class WW_442:
    """Mo'arg Drillfist"""

    # Taunt. Deathrattle: Excavate a treasure.
    deathrattle = Excavate(CONTROLLER)


##
# Spells


class WW_092:
    """Fracking"""

    # Look at the bottom 3 cards of your deck. Draw one and destroy the
    # others.  _Fracking reuses the Dredge UI: the chosen card is drawn and
    # the other two dredged cards are destroyed (firing their triggers).
    play = _Fracking(CONTROLLER)


class WW_378:
    """Smokestack"""

    # Deal 1 damage to a minion. If it dies, Excavate a treasure.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 1), Dead(TARGET) & Excavate(CONTROLLER)


class WW_436:
    """Trolley Problem"""

    # Discard your lowest Cost spell. Summon two 3/3 Tram Cars with Rush.
    # Quickdraw: Don't discard.
    play = (
        (Summon(CONTROLLER, "WW_437t") * 2),
        -QUICKDRAW & Discard(LOWEST_COST(FRIENDLY_HAND + SPELL)),
    )


class WW_441:
    """Furnace Fuel"""

    # When this is played, discarded, or destroyed, draw 2 cards.
    play = Draw(CONTROLLER) * 2
    discard = Draw(CONTROLLER) * 2


##
# Tokens


class WW_044t:
    """Barrel of Sludge"""

    # When this is played, discarded, or destroyed, deal 3 damage to the
    # lowest Health enemy.
    play = Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 3)
    discard = Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 3)


class WW_437t:
    """Tram Car"""

    # Rush. (vanilla — Rush lives in data)
