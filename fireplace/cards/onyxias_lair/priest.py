from ..utils import *


##
# Spells


class ONY_017:
    """Horn of Wrathion"""

    # Draw a minion. If it's a Dragon, summon two 2/1 Whelps with <b>Rush</b>.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)).then(
        (Attr(Draw.CARD, GameTag.CARDRACE) == int(Race.DRAGON))
        & (Summon(CONTROLLER, "ONY_001t") * 2)
    )


##
# Minions


class ONY_026:
    """Lightmaw Netherdrake"""

    # <b>Battlecry:</b> If you're holding a Holy and a Shadow spell, deal 3
    # damage to all other minions.
    play = (
        Find(FRIENDLY_HAND + SPELL + HOLY_SPELL)
        & Find(FRIENDLY_HAND + SPELL + SHADOW_SPELL)
        & Hit(ALL_MINIONS - SELF, 3)
    )


class ONY_028:
    """Mi'da, Pure Light"""

    # <b>Divine Shield</b>, <b>Lifesteal</b>. <b>Deathrattle:</b> Shuffle a
    # Fragment into your deck that resummons Mi'da when drawn.
    deathrattle = Shuffle(CONTROLLER, "ONY_028t")


class ONY_028t:
    """Fragment of Mi'da"""

    # Casts When Drawn: summon Mi'da. If the board is full the summon
    # silently no-ops and the Fragment is still consumed — matches the
    # engine's normal summon-from-deck behaviour.
    def play(self):
        if len(self.controller.field) < 7:
            yield Summon(CONTROLLER, "ONY_028")
