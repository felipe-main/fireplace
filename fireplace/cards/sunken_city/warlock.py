from ..utils import *


##
# Spells


class TSC_924:
    """Abyssal Wave"""

    # Deal $4 damage to all minions. Give your opponent an Abyssal Curse.
    play = Hit(ALL_MINIONS, 4), Shuffle(OPPONENT, "TSC_955t")


class TSC_925:
    """Rock Bottom"""

    # Summon a 1/1 Murloc, then Dredge. If it's also a Murloc, summon
    # one more.
    play = (
        Summon(CONTROLLER, "TSC_925t"),
        Dredge(CONTROLLER).then(
            (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.MURLOC))
            & Summon(CONTROLLER, "TSC_925t")
        ),
    )


@custom_card
class TSC_925t:
    tags = {
        GameTag.CARDNAME: "Sea Giant Murloc",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 1,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
        GameTag.CARDRACE: Race.MURLOC,
    }


class TSC_956:
    """Dragged Below"""

    # Deal $4 damage to a minion. Give your opponent an Abyssal Curse.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 4), Shuffle(OPPONENT, "TSC_955t")


class TSC_957:
    """Chum Bucket"""

    # Give all Murlocs in your hand +1/+1. Repeat for each Murloc you control.
    def play(self):
        n = 1 + sum(1 for m in self.controller.field if Race.MURLOC in m.races)
        for _ in range(n):
            yield Buff(FRIENDLY_HAND + MURLOC, "TSC_957e")


TSC_957e = buff(atk=1, health=1)


##
# Minions


class TSC_039:
    """Azsharan Scavenger"""

    # Battlecry: Put a 'Sunken Scavenger' on the bottom of your deck.
    play = PutOnBottom(CONTROLLER, "TSC_039t")


class TSC_039t:
    """Sunken Scavenger"""

    # Battlecry: Give your other Murlocs +1/+1 (wherever they are).
    play = (
        Buff(FRIENDLY_HAND + MURLOC - SELF, "TSC_039te"),
        Buff(FRIENDLY_DECK + MURLOC - SELF, "TSC_039te"),
        Buff(FRIENDLY_MINIONS + MURLOC - SELF, "TSC_039te"),
    )


TSC_039te = buff(atk=1, health=1)


class TSC_614:
    """Voidgill"""

    # Deathrattle: Give all Murlocs in your hand +1/+1.
    deathrattle = Buff(FRIENDLY_HAND + MURLOC, "TSC_614e")


TSC_614e = buff(atk=1, health=1)


class _BloodscentMark(TargetedAction):
    """Snapshot the target's printed cost onto a per-card attribute and
    buff its cost to 0. When the card is played, the controller pays
    the snapshot HP instead of mana — handled by a Play hook on the
    Bloodscent Vilefin card class via the engine's own_card_play
    listener (registered on the *controller* so it survives the card
    leaving hand)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._bloodscent_hp_cost = max(0, target.cost)
        target._bloodscent_marked = True
        source.game.queue_actions(source, [Buff(target, "TSC_753e")])


class _BloodscentPayHP(TargetedAction):
    """Damage hook fired when any minion is played: if the played card
    was previously marked by a Bloodscent Vilefin Dredge, pay its
    snapshot HP cost to the controller's hero."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not getattr(target, "_bloodscent_marked", False):
            return
        cost = getattr(target, "_bloodscent_hp_cost", 0)
        if cost <= 0:
            return
        # Clear the mark so the hit doesn't repeat (e.g. on resummon).
        target._bloodscent_marked = False
        source.game.queue_actions(
            source, [Hit(target.controller.hero, cost)]
        )


class TSC_753:
    """Bloodscent Vilefin"""

    # Battlecry: Dredge. If it's a Murloc, change its Cost to Health
    # instead of Mana.
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.MURLOC))
        & _BloodscentMark(Dredge.CARD)
    )

    # Whenever any minion is played by the controller, the HP-cost hook
    # checks if it was a Bloodscent-marked Murloc and pays the HP.
    events = Play(CONTROLLER, MINION).after(_BloodscentPayHP(Play.CARD))


class TSC_753e:
    tags = {GameTag.COST: -100}


class TSC_955:
    """Sira'kess Cultist"""

    # Battlecry: Give your opponent an Abyssal Curse.
    play = Shuffle(OPPONENT, "TSC_955t")


class _AbyssalCurseTick(TargetedAction):
    """A single Abyssal Curse tick: bumps the controller's curse counter,
    deals damage equal to the new total, heals an opposing Za'qul for
    the same amount, then destroys SELF. Implemented as a custom action
    so the side-effects on the controller happen exactly once per fire —
    the engine's trigger_event calls callable lambdas twice (the body
    runs once, then runs again to gather iterable actions), so a plain
    Python helper would over-count."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = target.controller
        controller.abyssal_curses_drawn = (
            getattr(controller, "abyssal_curses_drawn", 0) + 1
        )
        amount = controller.abyssal_curses_drawn
        source.game.queue_actions(target, [Hit(controller.hero, amount)])
        caster = controller.opponent
        if any(m.id == "TSC_959" for m in caster.field):
            source.game.queue_actions(target, [Heal(caster.hero, amount)])
        source.game.queue_actions(target, [Destroy(target)])


class TSC_955t:
    """Abyssal Curse"""

    # At the start of your turn, take @ damage. Each Curse is worse than
    # the last. The card sits in deck/hand and ticks once per own turn.
    class Hand:
        events = OWN_TURN_BEGIN.on(_AbyssalCurseTick(SELF))

    class Deck:
        events = OWN_TURN_BEGIN.on(_AbyssalCurseTick(SELF))


class TSC_959:
    """Za'qul"""

    # Your Abyssal Curses heal you for the damage they deal. Battlecry:
    # Give your opponent an Abyssal Curse. (The healing side lives on
    # the Curse itself — see TSC_955t's play action above.)
    play = Shuffle(OPPONENT, "TSC_955t")


class TSC_962:
    """Gigafin"""

    # Colossal +1. Battlecry: Devour all enemy minions. Deathrattle: Spit
    # them back out. We move the devoured minions to SETASIDE (preserving
    # their full state — buffs, deathrattles, current health, summon
    # order) and resummon those exact entities on death, so they come
    # back with everything intact.
    def play(self):
        targets = self.controller.opponent.field[:]
        self._devoured = targets
        for m in targets:
            m.zone = Zone.SETASIDE

    def deathrattle(self):
        devoured = getattr(self, "_devoured", None) or []
        for m in devoured:
            if m.zone == Zone.SETASIDE:
                yield Summon(OPPONENT, m)
        self._devoured = []


class TSC_962t:
    """Gigafin's Maw"""

    # Taunt. Deathrattle: Permanently destroy all minions inside Gigafin.
    # When the Maw dies first, the devoured minions are sent to the
    # graveyard rather than being returned by the parent's deathrattle.
    def deathrattle(self):
        # The Maw belongs to Gigafin's owner; find the parent on the
        # same side of the field (it may already be in graveyard, in
        # which case the devoured set will still be cleared correctly).
        parent = next(
            (
                m
                for m in self.controller.field
                + list(self.controller.graveyard)
                if m.id == "TSC_962"
            ),
            None,
        )
        if parent is None:
            return ()
        devoured = getattr(parent, "_devoured", None) or []
        actions = []
        for m in devoured:
            if m.zone == Zone.SETASIDE:
                # Send to graveyard directly so they never resurrect.
                m.zone = Zone.GRAVEYARD
        parent._devoured = []
        return actions
