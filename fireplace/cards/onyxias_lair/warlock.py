from ..utils import *


##
# Spells


class ONY_033:
    """Impfestation"""

    # Summon a 3/3 Dread Imp to attack each enemy minion.
    # Dread Imp = AV_316t (3/3) from Alterac. Each imp summoned individually
    # and attacks the corresponding enemy.
    def play(self):
        controller = self.controller
        enemy_minions = list(controller.opponent.field)
        for enemy in enemy_minions:
            if enemy.dead or enemy.zone != Zone.PLAY:
                continue
            yield Summon(CONTROLLER, "AV_316t").then(
                GiveRush(Summon.CARD),
                Attack(Summon.CARD, enemy),
            )


class ONY_034:
    """Curse of Agony"""

    # Shuffle three Agonies into the opponent's deck. They deal Fatigue
    # damage when drawn.
    play = Shuffle(OPPONENT, "ONY_034t") * 3


class ONY_034t:
    """Agony"""

    play = Fatigue(CONTROLLER)


##
# Minions


class ONY_035:
    """Spawn of Deathwing"""

    # <b>Battlecry:</b> Destroy a random enemy minion. Discard a random card.
    play = (
        Find(ENEMY_MINIONS) & Destroy(RANDOM(ENEMY_MINIONS)),
        Find(FRIENDLY_HAND - SELF) & Discard(RANDOM(FRIENDLY_HAND - SELF)),
    )
