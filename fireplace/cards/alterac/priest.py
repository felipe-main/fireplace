from ..utils import *


##
# Minions


class AV_325:
    """Undying Disciple"""

    # [x]<b>Taunt</b> <b>Deathrattle:</b> Deal damage equal to this minion's
    # Attack to all enemy minions.
    deathrattle = Hit(ENEMY_MINIONS, ATK(SELF))


class AV_326:
    """Luminous Geode"""

    # After a friendly minion is healed, give it +2 Attack.
    events = Heal(FRIENDLY_MINIONS).after(Buff(Heal.TARGET, "AV_326e"))


AV_326e = buff(atk=2)


class AV_328:
    """Spirit Guide"""

    # [x]<b>Taunt</b> <b>Deathrattle:</b> Draw a Holy spell and a Shadow spell.
    deathrattle = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + HOLY_SPELL)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + SHADOW_SPELL)),
    )


class AV_331:
    """Najak Hexxen"""

    # [x]<b>Battlecry:</b> Take control of an enemy minion. <b>Deathrattle:</b>
    # Give the minion back. We remember the stolen target as instance state
    # on Najak so the deathrattle can hand it back to its original (now
    # enemy-from-Najak's-POV) owner.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }

    def play(self):
        target = self.target
        self._stolen_target = target
        yield Steal(target)

    def deathrattle(self):
        target = getattr(self, "_stolen_target", None)
        if target is None or target.dead:
            return
        # Hand the minion back to Najak's opponent (its original owner).
        yield Steal(target, OPPONENT)


##
# Spells


class AV_315:
    """Deliverance"""

    # Deal $3 damage to a minion. <b>Honorable Kill:</b> Summon a new 3/3 copy
    # of it.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 3)
    honorable_kill = Summon(CONTROLLER, Copy(HonorableKill.VICTIM)).then(
        Buff(Summon.CARD, "AV_315e2")
    )


class AV_315e2:
    # "Salvation" — Blizzard's real enchant id, sets the copy to 3/3 stats.
    tags = {GameTag.ATK: 3, GameTag.HEALTH: 3}


class AV_324:
    """Shadow Word: Devour"""

    # Choose a minion. It steals 1 Health from _ALL other minions.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(ALL_MINIONS - TARGET, 1), Buff(TARGET, "AV_324e2")


class AV_324e2:
    # "Superior" — Blizzard's real enchant id for the target's gain. The
    # gain should scale with the count of other minions; using a flat +1
    # health as a static approximation.
    tags = {GameTag.HEALTH: 1}


class AV_329:
    """Bless"""

    # [x]Give a minion +2 Health, then set its Attack to be equal to its
    # Health.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "AV_329e")


class AV_329e:
    tags = {GameTag.HEALTH: 2}
    # "Set attack = health" portion is best-effort; engine has no
    # set-attack-from-health primitive in the buff DSL.


class AV_330:
    """Gift of the Naaru"""

    # [x]Restore #3 Health to all characters. If any are still damaged, draw
    # a card.
    play = Heal(ALL_CHARACTERS, 3).then(
        Find(ALL_CHARACTERS + DAMAGED) & Draw(CONTROLLER)
    )


class AV_664:
    """Stormpike Aid Station"""

    # [x]At the end of your turn, give your minions +2 Health. Lasts 3 turns.
    events = OWN_TURN_END.on(Buff(FRIENDLY_MINIONS, "AV_664e2"))


class AV_664e2:
    # "Restored" — Blizzard's real enchant id for the Aid Station +2 Health.
    tags = {GameTag.HEALTH: 2}


##
# Heros


class AV_207:
    """Xyrella, the Devout"""

    # [x]<b>Battlecry:</b> Trigger the <b>Deathrattle</b> of every friendly
    # minion that died this game. Iterates the controller's graveyard
    # directly since game.entities doesn't include graveyard cards.
    def play(self):
        from hearthstone.enums import CardType as _CT
        for minion in list(self.controller.graveyard):
            if minion.type == _CT.MINION and minion.has_deathrattle:
                yield Deathrattle(minion)
