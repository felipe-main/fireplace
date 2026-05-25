from ..utils import *


##
# Spells


class REV_825:
    """Double Cross"""

    # Secret: When your opponent spends all their Mana, draw two cards.
    # Approximated to fire on opponent's turn end.
    secret = OWN_TURN_END.on(
        Reveal(SELF),
        Draw(CONTROLLER) * 2,
    )


class REV_827:
    """Sticky Situation"""

    # Secret: After your opponent casts a spell, summon a 3/4 Spider
    # with Stealth.
    secret = Play(OPPONENT, SPELL).after(
        Reveal(SELF), Summon(CONTROLLER, "REV_827t")
    )


class REV_827t:
    """Tomb Crawler"""

    tags = {GameTag.STEALTH: True}


class REV_828:
    """Kidnap"""

    # Secret: After your opponent plays a minion, stuff it in a 0/4 Sack.
    secret = Play(OPPONENT, MINION).after(
        Reveal(SELF), Morph(Play.CARD, "REV_828t")
    )


class REV_828t:
    """Kidnapper's Sack"""


class REV_938:
    """Door of Shadows"""

    # Draw a spell. (Infused: Add a temporary copy of it to your hand.)
    play = ForceDraw(FRIENDLY_DECK + SPELL)


class REV_938t:
    """Door of Shadows"""

    # Infused — Draw a spell + add a temporary copy to hand.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + SPELL)).then(
        Give(CONTROLLER, Copy(ForceDraw.TARGET)).then(GiveTemporary(Give.CARD))
    )


class REV_939:
    """Serrated Bone Spike"""

    # Deal 3 damage to a minion. If it dies, your next card this turn
    # costs (2) less. Approximation: pure damage; cost-discount window
    # not modeled.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3)


##
# Minions


class REV_826:
    """Private Eye"""

    # Battlecry: Cast a Secret from your deck. Combo: Cast 2 instead.
    play = CastSpell(RANDOM(FRIENDLY_DECK + SECRET))
    combo = CastSpell(RANDOM(FRIENDLY_DECK + SECRET)) * 2


class REV_829:
    """Halkias"""

    # Deathrattle: If you control a Secret, store Halkias' soul inside
    # of it. It resummons Halkias when triggered. Approximation: if a
    # secret is controlled, just resurrect Halkias immediately.
    deathrattle = (Count(FRIENDLY + SECRET) >= 1) & Summon(CONTROLLER, "REV_829")


class REV_940:
    """Necrolord Draka"""

    # Battlecry: Equip an X/3 Dagger, where X = 1 + the number of other
    # cards played this turn. Approximate: equip a 3/3 Dagger.
    play = Summon(CONTROLLER, "REV_940t")


class REV_940t:
    """Maldraxxus Dagger"""


class REV_959:
    """Ghastly Gravedigger"""

    # Battlecry: If you control a Secret, choose a card in your
    # opponent's hand to shuffle into their deck. Approximation: random
    # opponent hand card → opponent deck.
    play = (Count(FRIENDLY + SECRET) >= 1) & Shuffle(
        OPPONENT, RANDOM(ENEMY_HAND)
    )


##
# Locations


class REV_750:
    """Sinstone Graveyard"""

    # Summon a 1/1 Stealthed Ghost. Has +1/+1 for each other card you
    # played this turn. Approximation: just summon a 1/1 stealthed Ghost
    # token.
    activate = Summon(CONTROLLER, "REV_750t2")
