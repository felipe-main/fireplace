from ..utils import *


##
# Spells


class TSC_912:
    """Azsharan Vessel"""

    # Summon two 3/3 Pirates with Stealth. Put a 'Sunken Vessel' on the
    # bottom of your deck.
    play = (
        Summon(CONTROLLER, "TSC_912t2") * 2,
        PutOnBottom(CONTROLLER, "TSC_912t"),
    )


class TSC_912t:
    """Sunken Vessel"""

    # Casts When Drawn. Summon two 3/3 Pirates with Stealth.
    play = Summon(CONTROLLER, "TSC_912t2") * 2


class TSC_912t2:
    """Sunken Pirate"""


class TSC_916:
    """Gone Fishin'"""

    # Dredge. Combo: Draw a card.
    play = Dredge(CONTROLLER)
    combo = Dredge(CONTROLLER), Draw(CONTROLLER)


class TSC_932:
    """Blood in the Water"""

    # Deal $3 damage to an enemy. Summon a 5/5 Shark with Rush.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_ENEMY_TARGET: 0}
    play = Hit(TARGET, 3), Summon(CONTROLLER, "TSC_932t")


@custom_card
class TSC_932t:
    tags = {
        GameTag.CARDNAME: "Shark",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 5,
        GameTag.ATK: 5,
        GameTag.HEALTH: 5,
        GameTag.RUSH: True,
    }


##
# Minions


class TSC_085:
    """Cutlass Courier"""

    # After your hero attacks, draw a Pirate.
    events = Attack(FRIENDLY_HERO).after(
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + PIRATE))
    )


class _BootstrapToBottom(TargetedAction):
    """Atomic field → bottom-of-deck move. Bounce-then-PutOnBottom would
    visit Zone.HAND in the middle; this skips straight to the deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        owner = target.controller
        if len(owner.deck) >= owner.max_deck_size:
            source.game.queue_actions(source, [Destroy(target)])
            return
        # Let the zone setter handle the field → deck plumbing. The
        # setter appends to deck; we then pin to position 0.
        target.zone = Zone.DECK
        if target in owner.deck:
            owner.deck.remove(target)
        owner.deck.insert(0, target)


class TSC_933:
    """Bootstrap Sunkeneer"""

    # Combo: Put an enemy minion on the bottom of your opponent's deck.
    # Atomic move (field → deck-bottom), bypassing the hand zone that a
    # Bounce-then-PutOnBottom would visit.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_FOR_COMBO: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    combo = _BootstrapToBottom(TARGET)


class TSC_934:
    """Pirate Admiral Hooktusk"""

    # Battlecry: If you've summoned 8 other Pirates this game, plunder
    # the enemy! The three plunder options are real tokens in data:
    # TSC_934t (Take their Supplies — 5 cards from deck), TSC_934t2
    # (Take their Gold — 2 from hand), TSC_934t3 (Take their Ship —
    # steal highest-attack minion). We Discover one of the three.
    def play(self):
        controller = self.controller
        pirate_count = sum(
            1
            for c in controller.cards_played_this_game
            if c.type == CardType.MINION and Race.PIRATE in c.races
        )
        if pirate_count < 8:
            return
        yield GenericChoice(
            controller, ["TSC_934t", "TSC_934t2", "TSC_934t3"]
        )


class TSC_934t:
    """Take their Supplies!"""

    # Take 5 cards from your opponent's deck.
    def play(self):
        opponent = self.controller.opponent
        for _ in range(5):
            if not opponent.deck:
                break
            card = opponent.deck[-1]
            yield Give(CONTROLLER, card.id)
            card.discard()


class TSC_934t2:
    """Take their Gold!"""

    # Take 2 cards from your opponent's hand.
    def play(self):
        opponent = self.controller.opponent
        import random as _random

        candidates = [c for c in opponent.hand]
        for _ in range(2):
            if not candidates:
                break
            picked = _random.choice(candidates)
            candidates.remove(picked)
            yield Give(CONTROLLER, picked.id)
            picked.discard()


class TSC_934t3:
    """Take their Ship!"""

    # Take control of your opponent's highest-Attack minion.
    def play(self):
        opponent = self.controller.opponent
        if not opponent.field:
            return
        # Pick the highest-attack enemy minion.
        highest = max(opponent.field, key=lambda m: m.atk)
        yield Steal(highest)


class TSC_936:
    """Swiftscale Trickster"""

    # Battlecry: Your next spell this turn costs (0). Implemented as
    # Solar-Eclipse-style: an enchantment attached to the controller that
    # refreshes a Cost: -100 aura on every spell in hand, and destroys
    # itself the moment any spell is cast.
    play = Buff(CONTROLLER, "TSC_936e")


class TSC_936e:
    update = Refresh(FRIENDLY_HAND + SPELL, {GameTag.COST: -100})
    events = Play(CONTROLLER, SPELL).after(Destroy(SELF))


class TSC_937:
    """Crabatoa"""

    # Colossal +2. Your Crabatoa Claws have +2 Attack. Each Claw is
    # TSC_937t/t3 (3-attack Rush DR Equip 2/1 Claw). Engine summons the
    # claws around Crabatoa; we buff them via update.
    update = Refresh(
        FRIENDLY_MINIONS + (ID("TSC_937t") | ID("TSC_937t3")),
        buff="TSC_937e",
    )


TSC_937e = buff(atk=2)


class TSC_937t:
    """Crabatoa's Claw"""

    # Rush. Deathrattle: Equip a 2/1 Claw.
    deathrattle = Summon(CONTROLLER, "TSC_937t2")


class TSC_937t2:
    """Crabatoa Claw"""


class TSC_937t3(TSC_937t):
    pass


class TSC_086:
    """Swordfish"""

    # Weapon. Battlecry: Dredge. If it's a Pirate, give this weapon and
    # the Pirate +2 Attack.
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.PIRATE))
        & (
            Buff(SELF, "TSC_086e"),
            Buff(Dredge.CARD, "TSC_086e"),
        )
    )


TSC_086e = buff(atk=2)


class TSC_963:
    """Filletfighter"""

    # Battlecry: Deal 1 damage.
    requirements = {PlayReq.REQ_TARGET_IF_AVAILABLE: 0}
    play = Hit(TARGET, 1)
