from ..utils import *


##
# Spells


class MAW_006:
    """Objection!"""

    # Secret: When your opponent plays a minion, Counter it.  Engine
    # approximation: bounce the minion back to hand and mark it
    # uncastable (Counter alone leaves a minion on the board because
    # `cant_play` only gates future plays).
    secret = Play(OPPONENT, MINION).on(
        Reveal(SELF), Counter(Play.CARD), Bounce(Play.CARD)
    )


class MAW_013:
    """Life Sentence"""

    # Remove a minion from the game.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Remove(TARGET)


##
# Minions


class MAW_101:
    """Contract Conjurer"""

    # Costs (3) less for each Secret you control.
    # FRIENDLY_SECRETS (= IN_SECRET + SECRET + FRIENDLY) counts only Secrets
    # active in the Secret zone. A bare `FRIENDLY + SECRET` also matches Secret
    # cards sitting in the deck/hand, which over-discounts the card.
    cost_mod = -(Count(FRIENDLY_SECRETS) * 3)
