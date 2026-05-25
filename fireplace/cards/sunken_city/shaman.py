from ..utils import *


##
# Spells


class TSC_631:
    """Schooling"""

    # Add three 1/1 Piranha Swarmers to your hand.
    play = Give(CONTROLLER, "TSC_638") * 3


class TSC_637:
    """Scalding Geyser"""

    # Deal $2 damage. Dredge.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 2), Dredge(CONTROLLER)


class TSC_772:
    """Azsharan Scroll"""

    # Discover a Fire, Frost or Nature spell. Put a 'Sunken Scroll' on the
    # bottom of your deck.
    play = (
        DISCOVER(
            RandomSpell(card_class=CardClass.SHAMAN)
        ),  # approximation — engine class default
        PutOnBottom(CONTROLLER, "TSC_772t"),
    )


class TSC_772t:
    """Sunken Scroll"""

    # Add a Fire, Frost, and Nature spell from your class to your hand.
    play = (
        Give(CONTROLLER, RandomSpell(card_class=CardClass.SHAMAN, spell_school=SpellSchool.FIRE)),
        Give(CONTROLLER, RandomSpell(card_class=CardClass.SHAMAN, spell_school=SpellSchool.FROST)),
        Give(CONTROLLER, RandomSpell(card_class=CardClass.SHAMAN, spell_school=SpellSchool.NATURE)),
    )


class TSC_923:
    """Bioluminescence"""

    # Give your minions Spell Damage +1.
    play = Buff(FRIENDLY_MINIONS, "TSC_923e")


class TSC_923e:
    tags = {GameTag.SPELLPOWER: 1}


##
# Minions


class TSC_630:
    """Wrathspine Enchanter"""

    # Battlecry: Cast a copy of a Fire, Frost, and Nature spell in your
    # hand (targets chosen randomly).
    def play(self):
        controller = self.controller
        for school in (SpellSchool.FIRE, SpellSchool.FROST, SpellSchool.NATURE):
            matches = [
                c
                for c in controller.hand
                if c.type == CardType.SPELL and c.spell_school == school and c is not self
            ]
            if matches:
                import random as _random

                pick = _random.choice(matches)
                yield CastSpell(pick.id)


class TSC_633:
    """Piranha Poacher"""

    # At the end of your turn, add a 1/1 Piranha Swarmer to your hand.
    events = OWN_TURN_END.on(Give(CONTROLLER, "TSC_638"))


class TSC_635:
    """Radiance of Azshara"""

    # Fire Spell Damage +2. Your Nature spells cost (1) less. After you
    # cast a Frost spell, gain 3 Armor. The engine already aggregates
    # per-school spellpower (player.get_spell_damage), so we set
    # SPELLPOWER_FIRE on the friendly hero — no over-buff on other
    # schools.
    update = (
        Refresh(FRIENDLY_HERO, {GameTag.SPELLPOWER_FIRE: 2}),
        Refresh(FRIENDLY_HAND + SPELL + NATURE_SPELL, buff="TSC_635e"),
    )
    events = Play(CONTROLLER, SPELL + FROST_SPELL).after(GainArmor(FRIENDLY_HERO, 3))


class TSC_635e:
    tags = {GameTag.COST: -1}


class TSC_639:
    """Glugg the Gulper"""

    # Colossal +3. After a friendly minion dies, gain its original stats.
    def events(self):
        return ()


class TSC_639:  # noqa: F811
    """Glugg the Gulper"""

    events = Death(FRIENDLY_MINIONS - SELF).on(
        Buff(SELF, "TSC_639e", atk=ATK(Death.ENTITY), max_health=Attr(Death.ENTITY, GameTag.HEALTH))
    )


TSC_639e = buff()


class TSC_639t:
    """Glugg's Tail"""


class TSC_639t2(TSC_639t):
    pass


class TSC_639t3(TSC_639t):
    pass


class TSC_648:
    """Coral Keeper"""

    # Battlecry: Summon a 3/3 Elemental for each spell school you've cast
    # this game.
    def play(self):
        n = len(self.controller.spells_cast_by_school)
        for _ in range(n):
            yield Summon(CONTROLLER, "TSC_648t")


@custom_card
class TSC_648t:
    tags = {
        GameTag.CARDNAME: "Coral Elemental",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 3,
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
        GameTag.CARDRACE: Race.ELEMENTAL,
    }


class TSC_922:
    """Anchored Totem"""

    # After you summon a 1-Cost minion, give it +2/+1.
    events = Summon(CONTROLLER, MINION + (COST == 1)).after(
        Buff(Summon.CARD, "TSC_922e")
    )


TSC_922e = buff(atk=2, health=1)
