from ..utils import *


##
# Minions


class AV_114:
    """Shivering Sorceress"""

    # [x]<b>Battlecry:</b> Reduce the Cost of the highest Cost spell in your
    # hand by (1).
    play = Buff(HIGHEST_COST(FRIENDLY_HAND + SPELL), "AV_114e")


class AV_114e:
    tags = {GameTag.COST: -1}


class AV_115:
    """Amplified Snowflurry"""

    # <b>Battlecry:</b> Your next Hero Power costs (0) and <b>Freezes</b> the
    # target.
    play = (
        IncreaseAttr(CONTROLLER, "next_hero_power_costs_zero", 1),
        IncreaseAttr(CONTROLLER, "next_hero_power_freezes_target", 1),
    )


class AV_284:
    """Balinda Stonehearth"""

    # <b>Battlecry:</b> Draw 2 spells. Swap their Costs with this minion's
    # stats.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)) * 2


##
# Spells


class AV_212:
    """Siphon Mana"""

    # Deal $2 damage. <b>Honorable Kill</b>: Reduce the Cost of spells in your
    # hand by (1).
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2)
    honorable_kill = Buff(FRIENDLY_HAND + SPELL, "AV_212e")


class AV_212e:
    tags = {GameTag.COST: -1}


class AV_218:
    """Mass Polymorph"""

    # Transform all minions into 1/1 Sheep.
    play = Morph(ALL_MINIONS, "CS2_tk1")


class AV_116:
    """Arcane Brilliance"""

    # Add a copy of a 7, 8, 9, and 10-Cost spell in your deck to your hand.
    play = (
        Give(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST == 7))),
        Give(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST == 8))),
        Give(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST == 9))),
        Give(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST == 10))),
    )


class AV_282:
    """Build a Snowman"""

    # Summon a 3/3 Snowman that <b>Freezes</b>. Add "Build a Snowbrute" to
    # your hand.
    play = Summon(CONTROLLER, "AV_282t"), Give(CONTROLLER, "AV_282t2")


class AV_283:
    """Rune of the Archmage"""

    # [x]Cast 20 Mana worth of Mage spells at enemies. Repeatedly picks a
    # random Mage spell whose cost fits the remaining budget, casts it at
    # an enemy character (chosen by CastSpellTargetsEnemiesIfPossible).
    def play(self):
        budget = 20
        # Avoid drawing the same Rune again — would be infinite recursion.
        excluded_ids = {"AV_283"}
        for _ in range(20):  # safety bound — at most 20 casts (1-cost spells)
            if budget <= 0:
                return
            candidates = [
                cid for cid in db
                if (
                    cid not in excluded_ids
                    and db[cid].type == CardType.SPELL
                    and db[cid].card_class == CardClass.MAGE
                    and db[cid].collectible
                    and 0 < db[cid].cost <= budget
                )
            ]
            if not candidates:
                return
            pick = self.game.random.choice(candidates)
            budget -= db[pick].cost
            yield CastSpellTargetsEnemiesIfPossible(pick)


class AV_290:
    """Iceblood Tower"""

    # [x]At the end of your turn, cast another spell from your deck. Lasts 3
    # turns.
    events = OWN_TURN_END.on(CastSpell(RANDOM(FRIENDLY_DECK + SPELL)))


##
# Heros


class AV_200:
    """Magister Dawngrasp"""

    # [x]<b>Battlecry:</b> Recast a spell from each spell school you've cast
    # this game. Uses Player.spells_cast_by_school (populated by the Play
    # action) to recast one random spell per school.
    def play(self):
        history = self.controller.spells_cast_by_school
        for school, spell_ids in history.items():
            if spell_ids:
                pick = self.game.random.choice(spell_ids)
                yield CastSpellTargetsEnemiesIfPossible(pick)
