from ..utils import *

##
# Minions


class AV_100:
    """Drek'Thar"""

    # [x]<b>Battlecry</b>: If this costs more than every minion in your deck,
    # summon 2 of them.
    powered_up = -Find(FRIENDLY_DECK + MINION + (COST <= COST(SELF)))
    play = powered_up & Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION, 2))


class AV_223:
    """Vanndar Stormpike"""

    # [x]<b>Battlecry</b>: If this costs less than every minion in your deck,
    # reduce their Cost by (3).
    powered_up = -Find(FRIENDLY_DECK + MINION + (COST >= COST(SELF)))
    play = powered_up & Buff(FRIENDLY_DECK + MINION, "AV_223e")


class AV_223e:
    tags = {GameTag.COST: -3}
    events = REMOVED_IN_PLAY


class AV_141t:
    """Lokholar the Ice Lord"""

    # <b>Rush</b>, <b>Windfury</b> Costs (5) less if you have 15 Health or less.
    cost_mod = (Attr(FRIENDLY_HERO, GameTag.HEALTH) <= 15) & -5


class AV_142t:
    """Ivus, the Forest Lord"""

    # [x]<b>Battlecry:</b> Spend the rest of your Mana and gain +2/+2,
    # <b>Rush</b>, <b>Divine Shield</b>, or <b>Taunt</b> at random for each.
    # The four Blizzard enchantments are AV_142e/e2/e3/e4.
    def play(self):
        remaining = self.controller.mana
        if remaining <= 0:
            return
        yield SpendMana(self.controller, remaining)
        for _ in range(remaining):
            choice = self.game.random.randint(0, 3)
            if choice == 0:
                yield Buff(self, "AV_142e4")  # +2/+2 (Imposing)
            elif choice == 1:
                yield GiveRush(self)  # AV_142e2 Uprooted
            elif choice == 2:
                yield GiveDivineShield(self)  # AV_142e Crystalskin
            else:
                yield Taunt(self)  # AV_142e3 Forestguard


class AV_142e4:
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class AV_143:
    """Korrak the Bloodrager"""

    # [x]<b>Deathrattle:</b> If this wasn't <b>Honorably Killed</b>, resummon
    # Korrak. The `honorably_killed` flag is set by the Damage flow when the
    # killing blow's source has Honorable Kill and dealt exact damage.
    deathrattle = (Attr(SELF, "honorably_killed") == 0) & Summon(
        CONTROLLER, "AV_143"
    )
