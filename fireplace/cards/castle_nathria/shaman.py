from ..utils import *


##
# Spells


class REV_517:
    """Criminal Lineup"""

    # Choose a friendly minion. Summon 3 copies of it. Overload: (2)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Summon(CONTROLLER, Copy(TARGET)) * 3


class REV_920:
    """Convincing Disguise"""

    # Transform a friendly minion into one that costs (2) more.
    # Approximation: morph into any random minion (cost filter omitted
    # because empty cost buckets crash Morph's strict single-card
    # assertion).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Morph(TARGET, RandomMinion())


class REV_920t:
    """Convincing Disguise"""

    # Infused — Transform all friendly minions. Approximation: a single
    # random morph applied to the chosen target (engine Morph assertion
    # can't iterate over a multi-target selector).
    play = Morph(RANDOM(FRIENDLY_MINIONS), RandomMinion())


class REV_924:
    """Primordial Wave"""

    # Transform enemy minions into ones that cost (1) less and friendly
    # minions into ones that cost (1) more. Approximation: morph a
    # single random minion on each side without cost filter (Morph
    # asserts a single replacement card per call).
    play = (
        Morph(RANDOM_ENEMY_MINION, RandomMinion()),
        Morph(RANDOM(FRIENDLY_MINIONS), RandomMinion()),
    )


##
# Weapons


class REV_917:
    """Carving Chisel"""

    # After your hero attacks, summon a random basic Totem.
    events = Attack(FRIENDLY_HERO).after(
        Summon(CONTROLLER, RandomMinion(card_class=CardClass.SHAMAN, race=Race.TOTEM))
    )


##
# Minions


class REV_838:
    """Gigantotem"""

    # Costs (1) less for each Totem you've summoned this game.
    cost_mod = -Attr(CONTROLLER, "times_totem_summoned_this_game")


class REV_921:
    """The Stonewright"""

    # Battlecry: For the rest of the game, your Totems have +2 Attack.
    play = Buff(CONTROLLER, "REV_921e")


class REV_921e:
    update = Refresh(FRIENDLY_MINIONS + TOTEM, buff="REV_921ee")


@custom_card
class REV_921ee:
    tags = {
        GameTag.CARDNAME: "Stonewright Totem Buff",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
    }


class REV_925:
    """Baroness Vashj"""

    # If this would transform into a minion, summon that minion instead.
    # Engine doesn't support transform-redirect; left as a vanilla 4/3/6
    # Naga. Watch in soak.
    pass


class REV_935:
    """Party Favor Totem"""

    # At the end of your turn, summon a random basic Totem. (Infused:
    # Summon two instead.)
    events = OWN_TURN_END.on(
        Summon(CONTROLLER, RandomMinion(card_class=CardClass.SHAMAN, race=Race.TOTEM))
    )


class REV_935t:
    """Party Favor Totem"""

    # Infused — summon two instead.
    events = OWN_TURN_END.on(
        Summon(
            CONTROLLER, RandomMinion(card_class=CardClass.SHAMAN, race=Race.TOTEM)
        ) * 2
    )


class REV_936:
    """Crud Caretaker"""

    # Battlecry: Summon a 3/5 Elemental with Taunt.
    play = Summon(CONTROLLER, "REV_936t")


class REV_936t:
    """Untreated Filth"""

    tags = {GameTag.TAUNT: True}


##
# Locations


class REV_923:
    """Muck Pools"""

    # Transform a friendly minion into one that costs (1) more.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Morph(TARGET, RandomMinion())
