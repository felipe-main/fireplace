from ..utils import *


##
# Minions


class ONY_020:
    """Stormwind Avenger"""

    # After you cast a spell on this minion, it gains +2 Attack.
    events = Play(CONTROLLER, SPELL, SELF).after(Buff(SELF, "ONY_020e"))


class ONY_020e:
    tags = {GameTag.ATK: 2}


class ONY_022:
    """Battle Vicar"""

    # <b>Battlecry:</b> <b>Discover</b> a Holy spell.
    play = DISCOVER(RandomSpell(spell_school=SpellSchool.HOLY))


##
# Spells


class ONY_027:
    """Ring of Courage"""

    # <b>Tradeable</b>. Give a minion +1/+1. Repeat for each enemy minion.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        enemy_count = len(self.controller.opponent.field)
        # +1/+1 plus +1/+1 per enemy minion → (1 + enemy_count) total stacks.
        for _ in range(1 + enemy_count):
            yield Buff(target, "ONY_027e")


ONY_027e = buff(atk=1, health=1)
