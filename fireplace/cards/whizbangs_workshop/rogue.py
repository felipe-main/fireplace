from ..utils import *


# After you summon a Pirate, draw a card.
class TOY_505:
    """Toy Boat"""

    events = Summon(CONTROLLER, PIRATE).after(Draw(CONTROLLER))


# Draw a minion. If it's a Pirate, get a Coin.
class TOY_510:
    """Dig for Treasure"""

    play = ForceDraw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)).then(
        Find(ForceDraw.TARGET + PIRATE) & Give(CONTROLLER, "GAME_005")
    )


# [x]After you summon a Pirate, summon a copy of it that attacks a random
# enemy, then dies.
class TOY_511:
    """Shoplifter Goldbeard"""

    # Exclude SELF as the summon source so the copies Goldbeard makes don't
    # re-trigger it (infinite loop), while still reacting to Pirates summoned
    # by anything else.
    events = Summon(CONTROLLER, PIRATE, source=FRIENDLY - SELF).after(
        Summon(CONTROLLER, ExactCopy(Summon.CARD)).then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER), Destroy(Summon.CARD)
        )
    )


# [x]The next minion you summon this turn has its stats set to 4/4.
class TOY_512:
    """The Crystal Cove"""

    activate = Buff(CONTROLLER, "TOY_512e1")


# Treasures Below — carrier on the player. The next minion summoned this turn
# gets its stats set to 4/4, then the carrier expires. TAG_ONE_TURN_EFFECT in
# data already clears it at end of turn if no minion is summoned.
class TOY_512e1:
    events = Summon(CONTROLLER, MINION).on(
        Buff(Summon.CARD, "TOY_512e"), Destroy(SELF)
    )


# Coveted Crystals — set the minion's stats to 4/4.
class TOY_512e:
    atk = SET(4)
    max_health = SET(4)


# <b>Discover</b> a spell from another class. Get a copy of it.
class _ThistleTeaOtherClassSpell(RandomCardPicker):
    """Thistle Tea Set — Discover a collectible spell from a class other than
    the controller's (and not Neutral)."""

    def __init__(self):
        super().__init__(collectible=True, type=CardType.SPELL)

    def evaluate(self, source):
        from hearthstone.enums import CardClass
        from fireplace import cards as _cards

        ctrl_class = getattr(source.controller.hero, "card_class", CardClass.INVALID)
        candidates = []
        for cid in _cards.db.filter(collectible=True, type=CardType.SPELL):
            c = _cards.db[cid]
            classes = getattr(c, "classes", None) or [c.card_class]
            if ctrl_class in classes:
                continue
            if classes == [CardClass.NEUTRAL]:
                continue
            candidates.append(cid)
        return candidates


class TOY_514:
    """Thistle Tea Set"""

    play = DISCOVER(_ThistleTeaOtherClassSpell())


# After you play a 1-Cost card, get a copy of it that costs (0).
class TOY_515:
    """Sonya Waterdancer"""

    events = Play(CONTROLLER, COST == 1).after(
        Give(CONTROLLER, Copy(Play.CARD)).then(Buff(Give.CARD, "TOY_515e3"))
    )


# Fancy Footwork — Costs (0).
class TOY_515e3:
    tags = {GameTag.COST: -100}


# <b>Rush</b> <b>Combo:</b> Summon a copy of this.
class TOY_516:
    """Bargain Bin Buccaneer"""

    combo = Summon(CONTROLLER, ExactCopy(SELF))


# Summon two random 4-Cost minions. Costs (1) less for each card you've drawn
# this turn.
class TOY_519:
    """Everything Must Go!"""

    cost_mod = -Attr(CONTROLLER, "cards_drawn_this_turn")
    play = Summon(CONTROLLER, RandomMinion(cost=4)) * 2


# [x]<b>Miniaturize</b> <b>Battlecry:</b> Your next card this turn costs (3)
# less.
class TOY_521:
    """Sandbox Scoundrel"""

    play = Buff(CONTROLLER, "TOY_521e1")


# [x]<b>Mini</b> <b>Battlecry:</b> Your next card this turn costs (3) less.
class TOY_521t1:
    """Sandbox Scoundrel"""

    play = Buff(CONTROLLER, "TOY_521e1")


# On Sale reduction! — carrier on the player. The next card played this turn
# costs (3) less; consumed when the controller plays a card, and expires at
# end of turn (TAG_ONE_TURN_EFFECT in data).
class TOY_521e1:
    update = Refresh(FRIENDLY_HAND, {GameTag.COST: -3})
    events = Play(CONTROLLER).on(Destroy(SELF))


# After your hero attacks, summon a 1/1 Pirate that attacks a random enemy.
class TOY_522:
    """Watercannon"""

    events = Attack(FRIENDLY_HERO).after(
        Summon(CONTROLLER, "TOY_522t").then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
        )
    )


# Waterslider — 1/1 Pirate token.
class TOY_522t:
    """Waterslider"""
