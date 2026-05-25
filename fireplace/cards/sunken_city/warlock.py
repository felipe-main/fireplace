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


class TSC_753:
    """Bloodscent Vilefin"""

    # Battlecry: Dredge. If it's a Murloc, change its Cost to Health
    # instead of Mana. Approximation: set its cost to 0.
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.MURLOC))
        & Buff(Dredge.CARD, "TSC_753e")
    )


class TSC_753e:
    tags = {GameTag.COST: -100}


class TSC_955:
    """Sira'kess Cultist"""

    # Battlecry: Give your opponent an Abyssal Curse.
    play = Shuffle(OPPONENT, "TSC_955t")


class TSC_955t:
    """Abyssal Curse"""

    # Casts When Drawn: At the start of your turn, take @ damage. Each
    # Curse is worse than the last. Simplified: deal scaling damage based
    # on number of Curses drawn this game.
    def play(self):
        # Count past curses to scale damage. Use the controller's draw count
        # heuristic of "abyssal_curses_drawn".
        controller = self.controller
        controller.abyssal_curses_drawn = (
            getattr(controller, "abyssal_curses_drawn", 0) + 1
        )
        yield Hit(FRIENDLY_HERO, controller.abyssal_curses_drawn)


class TSC_959:
    """Za'qul"""

    # Your Abyssal Curses heal you for the damage they deal. Battlecry:
    # Give your opponent an Abyssal Curse. Heal-side approximated by a
    # generic heal-on-curse-fire hook (would require Za'qul tracking).
    # We just do the Battlecry portion correctly; the healing side is a
    # near-no-op until further engine work.
    play = Shuffle(OPPONENT, "TSC_955t")


class TSC_962:
    """Gigafin"""

    # Colossal +1. Battlecry: Devour all enemy minions. Deathrattle: Spit
    # them back out. Implemented as: BC bounces enemy minions to a shadow
    # zone (we use Destroy + remember on a parent attribute), DR resummons
    # them on the opponent's side.
    def play(self):
        target = self.controller.opponent.field[:]
        self._devoured_ids = [m.id for m in target]
        for m in target:
            yield Destroy(m)

    def deathrattle(self):
        for cid in getattr(self, "_devoured_ids", []):
            yield Summon(OPPONENT, cid)


class TSC_962t:
    """Gigafin's Maw"""

    # Taunt. Deathrattle: Permanently destroy all minions inside Gigafin.
    # Approximation: clear the parent's devoured list (so they don't come
    # back when the parent dies).
    def deathrattle(self):
        parent = next(
            (m for m in self.controller.field if m.id == "TSC_962"),
            None,
        )
        if parent is not None:
            parent._devoured_ids = []
        return ()
