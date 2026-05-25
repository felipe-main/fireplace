from ..utils import *


##
# Spells


class REV_506:
    """Sinful Brand"""

    # Brand an enemy minion. Whenever it takes damage, deal 2 damage to the
    # enemy hero. Modeled as an enchantment on the target whose event fires
    # when the target is damaged.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Buff(TARGET, "REV_506e")


class REV_506e:
    events = Damage(OWNER).on(Hit(ENEMY_HERO, 2))


class REV_507:
    """Dispose of Evidence"""

    # Give your hero +3 Attack this turn. Choose a card in your hand to
    # shuffle into your deck. Approximated as the hero buff + shuffle a
    # random hand card into the deck (no UI choice in our engine).
    play = Buff(FRIENDLY_HERO, "REV_507e"), Shuffle(
        CONTROLLER, RANDOM(FRIENDLY_HAND - SELF)
    )


class REV_507e:
    tags = {GameTag.ATK: 3, enums.TEMPORARY: 1}


class REV_508:
    """Relic of Dimensions"""

    # Draw two cards and reduce their Cost by the Relic counter. We don't
    # track the cumulative Relic counter; approximate by reducing the cost
    # of two drawn cards by 2.
    play = Draw(CONTROLLER).then(Buff(Draw.CARD, "REV_508e")) * 2


class REV_508e:
    tags = {GameTag.COST: -2}


class REV_834:
    """Relic of Extinction"""

    # Deal X damage to a random enemy minion, twice. Approximate with X=2.
    play = Hit(RANDOM_ENEMY_MINION, 2) * 2


class REV_943:
    """Relic of Phantasms"""

    # Summon two N/N Spirits. Approximate with N=2 via the dedicated token.
    play = Summon(CONTROLLER, "REV_943t") * 2


class REV_943t:
    """Fleeting Spirit"""


##
# Weapons


class REV_509:
    """Magnifying Glaive"""

    # After your hero attacks, draw until you have 3 cards.
    events = Attack(FRIENDLY_HERO).after(DrawUntil(CONTROLLER, 3))


##
# Minions


class REV_510:
    """Kryxis the Voracious"""

    # Battlecry: Discard your hand. Deathrattle: Draw 3 cards.
    play = Discard(FRIENDLY_HAND - SELF)
    deathrattle = Draw(CONTROLLER) * 3


class REV_511:
    """Bibliomite"""

    # Battlecry: Choose a card in your hand to shuffle into your deck.
    # Approximated as shuffling a random hand card.
    play = Shuffle(CONTROLLER, RANDOM(FRIENDLY_HAND))


class REV_937:
    """Artificer Xy'mox"""

    # Battlecry: Discover and cast a Relic. Infuse (5): Cast all three
    # instead. No Relic pool exists in MaCN base set beyond the three
    # demon-hunter Relic spells (REV_508/834/943); cast one of them at
    # random as an approximation.
    play = CastSpell(RandomSpell(card_class=CardClass.DEMONHUNTER))


class REV_937t:
    """Artificer Xy'mox"""

    # Infused: cast all three Relics. Approximation.
    play = (
        CastSpell("REV_508"),
        CastSpell("REV_834"),
        CastSpell("REV_943"),
    )


##
# Locations


class REV_942:
    """Relic Vault"""

    # The next Relic you play this turn casts twice. Approximated as a
    # spells-cast-twice marker for the rest of the turn.
    activate = Buff(CONTROLLER, "REV_942e")


class REV_942e:
    tags = {GameTag.SPELLS_CAST_TWICE: True}
    events = OWN_TURN_END.on(Destroy(SELF))
