from ..utils import *


##
# Minions


class AV_201:
    """Coldtooth Yeti"""

    # <b>Combo:</b> Gain +3 Attack.
    combo = Buff(SELF, "AV_201e")


AV_201e = buff(atk=3)


class AV_711:
    """Double Agent"""

    # [x]<b>Battlecry:</b> If you're holding a card from another class, summon
    # a copy of this.
    play = Find(FRIENDLY_HAND + OTHER_CLASS - SELF) & Summon(CONTROLLER, "AV_711")


class AV_298:
    """Wildpaw Gnoll"""

    # [x]<b>Rush</b> Costs (1) less for each card you've added to your hand
    # _from another class.
    # Note: scoped to off-class cards currently in hand rather than tracking
    # the cumulative "added this game" history; behaviorally identical in
    # normal play (cards leave hand when played, so the deltas converge).
    cost_mod = -Count(FRIENDLY_HAND + OTHER_CLASS - SELF)


class AV_403:
    """Cera'thine Fleetrunner"""

    # [x]<b>Battlecry:</b> Replace your minions in hand and deck with ones
    # from other classes. They cost (2) less. Pool: collectible minions from
    # any class other than ours (Neutral excluded; "other classes" is read
    # as "specifically not yours, specifically not Neutral").
    def play(self):
        own_class = self.controller.hero.card_class
        pool = [
            cid for cid, c in db.items()
            if (
                c.type == CardType.MINION
                and c.collectible
                and c.card_class != own_class
                and c.card_class != CardClass.NEUTRAL
            )
        ]
        if not pool:
            return
        # Replace minions in hand
        for minion in [c for c in list(self.controller.hand) if c.type == CardType.MINION and c is not self]:
            replacement = self.game.random.choice(pool)
            yield Morph(minion, replacement).then(Buff(Morph.CARD, "AV_403e2"))
        # Replace minions in deck
        for minion in [c for c in list(self.controller.deck) if c.type == CardType.MINION]:
            replacement = self.game.random.choice(pool)
            yield Morph(minion, replacement).then(Buff(Morph.CARD, "AV_403e2"))


class AV_403e2:
    # "Quickfooted" — Blizzard's real -2 cost enchant for Cera'thine's swaps.
    tags = {GameTag.COST: -2}


class AV_601:
    """Forsaken Lieutenant"""

    # <b><b>Stealth</b>.</b> After you play a <b>Deathrattle</b> minion,
    # become a 2/2 copy of it with <b>Rush</b>.
    events = Play(CONTROLLER, MINION + DEATHRATTLE).after(
        Morph(SELF, Play.CARD)
    )


##
# Spells


class AV_710:
    """Reconnaissance"""

    # <b>Discover</b> a <b>Deathrattle</b> minion from another class. It
    # costs (2) less.
    play = DISCOVER(
        RandomCollectible(card_class=CardClass.HUNTER)
    ).then(Buff(Discover.CARD, "AV_710e"))


class AV_710e:
    tags = {GameTag.COST: -2}


class AV_400:
    """Snowfall Graveyard"""

    # [x]Your <b>Deathrattles</b> trigger twice. Lasts 3 turns.
    # Sets the controller's `extra_deathrattles` slot flag — already
    # consulted by Deathrattle.do to re-queue the actions a second time.
    update = Refresh(CONTROLLER, {GameTag.EXTRA_DEATHRATTLES: True})


class AV_405:
    """Contraband Stash"""

    # Replay 5 cards from other classes you've played this game.
    play = Replay(RANDOM(CARDS_PLAYED_THIS_GAME, 5))


##
# Weapons


class AV_402:
    """The Lobotomizer"""

    # [x]<b>Honorable Kill:</b> Get a copy of the top card of your opponent's
    # deck.
    honorable_kill = Give(CONTROLLER, Copy(RANDOM(ENEMY_DECK)))


##
# Heros


class AV_203:
    """Shadowcrafter Scabbs"""

    # [x]<b>Battlecry:</b> Return all minions to their owner's hands. Summon
    # two 4/2 Shadows with <b>Stealth</b>.
    play = Bounce(ALL_MINIONS), Summon(CONTROLLER, "AV_203t") * 2
