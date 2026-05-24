from ..utils import *


##
# Spells


class ONY_006:
    """Deep Breath"""

    # Deal $@ damage to a minion and its neighbors. (Improved by number of
    # other spells in your hand.) @ = 2 + (#spells in hand other than this).
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        controller = self.controller
        spells_in_hand = sum(
            1
            for c in controller.hand
            if c is not self and c.type == CardType.SPELL
        )
        amount = 2 + spells_in_hand
        target = self.target
        if target is None:
            return
        targets = [target]
        if target.zone == Zone.PLAY and target in controller.opponent.field + controller.field:
            field = target.controller.field
            idx = field.index(target)
            if idx > 0:
                targets.append(field[idx - 1])
            if idx < len(field) - 1:
                targets.append(field[idx + 1])
        for t in targets:
            yield Hit(t, amount)


class ONY_029:
    """Drakefire Amulet"""

    # <b>Tradeable</b>. <b>Discover</b> 2 Dragons. Summon them.
    play = (
        Discover(CONTROLLER, RandomMinion(race=Race.DRAGON)).then(
            Summon(CONTROLLER, Discover.CARD)
        ),
        Discover(CONTROLLER, RandomMinion(race=Race.DRAGON)).then(
            Summon(CONTROLLER, Discover.CARD)
        ),
    )


##
# Minions


class ONY_007:
    """Haleh, Matron Protectorate"""

    # After you cast a spell, deal 4 damage randomly split among all enemies.
    events = OWN_SPELL_PLAY.after(Hit(RANDOM_ENEMY_CHARACTER, 1) * 4)
