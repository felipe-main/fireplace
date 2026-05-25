from ..utils import *

from ..castle_nathria.utils import InfuseCardtextMixin


##
# Minions


class _SoulSeekerSwap(TargetedAction):
    """Soul Seeker: true cross-zone swap.  Pick a random minion from
    the opponent's deck, remove it from the deck, summon it on the
    caster's side, then shuffle Soul Seeker (this entity) into the
    opponent's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType, Zone
        opp = target.controller.opponent
        pool = [c for c in opp.deck if c.type == CardType.MINION]
        if not pool:
            return
        pick = source.game.random.choice(pool)
        # Pull the picked card out of opponent's deck and onto our side.
        # Summon by id mirrors a true resurrect — original card object
        # still in opp's deck is removed by hand.
        opp.deck.remove(pick)
        pick._zone = Zone.SETASIDE
        source.game.cheat_action(source, [Summon(target.controller, pick.id)])
        # Soul Seeker leaves the board and joins opp's deck.
        target.zone = Zone.SETASIDE
        target.controller = opp
        target.zone = Zone.DECK


class MAW_004:
    """Soul Seeker"""

    # Battlecry: Swap this with a random minion from your opponent's
    # deck. Approximation: morph SELF into the pick and shuffle a
    # fresh Soul Seeker into the opponent's deck.
    play = _SoulSeekerSwap(SELF)


class MAW_031:
    """Afterlife Attendant"""

    # Your Infuse cards also Infuse while in your deck. The engine
    # hook in Death.do checks for any friendly Afterlife Attendant on
    # board and, when present, also iterates the controller's deck
    # alongside the hand for Infuse-progress bumps.  No script body
    # needed — the engine reads the board for the marker.
    pass


class MAW_032:
    """Tight-Lipped Witness"""

    # Secrets can't be revealed. Approximation: not enforced. The
    # engine's Reveal action would need a per-game gate; we leave the
    # behaviour as a no-op and flag it in the audit. Vanilla 3/2/5
    # body still applies.
    pass


class MAW_033(InfuseCardtextMixin):
    """Sylvanas, the Accused"""

    # Battlecry: Destroy an enemy minion. (Infuse (7): Take control of
    # it instead.)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Destroy(TARGET)


class MAW_033t:
    """Sylvanas, the Accused"""

    # Infused — Take control of the enemy minion instead.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Steal(TARGET)


class _TheJailerDestroyDeckAndImmune(TargetedAction):
    """The Jailer: empty the controller's deck and stamp a per-game
    immune-friendly-minions aura via Buff(MAW_034e)."""

    TARGET = ActionArg()

    def do(self, source, target):
        for card in list(target.deck):
            source.game.cheat_action(source, [Remove(card)])
        source.buff(target.hero, "MAW_034e")


class MAW_034:
    """The Jailer"""

    # Battlecry: Destroy your deck. For the rest of the game, your
    # minions are Immune.
    play = _TheJailerDestroyDeckAndImmune(CONTROLLER)


@custom_card
class MAW_034e:
    tags = {
        GameTag.CARDNAME: "Mawsworn",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = Refresh(FRIENDLY_MINIONS, {GameTag.CANT_BE_DAMAGED: True})
