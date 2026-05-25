from ..utils import *


##
# Spells


class TID_920:
    """Drown"""

    # Put an enemy minion on the bottom of your deck.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_ENEMY_TARGET: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        yield PutOnBottom(self.controller, target)


##
# Minions


class TID_085:
    """Herald of Light"""

    # Battlecry: If you've cast a Holy spell while holding this, restore 6
    # Health to all friendly characters.
    def play(self):
        schools = getattr(self, "spell_schools_cast_while_holding", set())
        if int(SpellSchool.HOLY) in schools:
            yield Heal(FRIENDLY_CHARACTERS, 6)


class TID_700:
    """Disarming Elemental"""

    # Battlecry: Dredge for your opponent. Set its Cost to (6). The Dredge
    # action already routes the choice to source.controller (the player
    # casting it); we simply target the opponent's deck.
    play = Dredge(OPPONENT).then(Buff(Dredge.CARD, "TID_700e"))


class TID_700e:
    cost = SET(6)
