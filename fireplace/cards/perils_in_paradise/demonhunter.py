from ..utils import *


##
# Custom actions


class _ArannaRedirect(TargetedAction):
    """Aranna, Thrill Seeker — redirect self-damage taken by your hero on
    your turn to a random enemy. Implemented reactively: after the hero
    takes damage on the controller's turn, restore that much Health and
    deal the same amount to a random enemy. This is a net-state
    approximation of a true pre-damage redirect (see review notes)."""

    TARGET = ActionArg()  # the friendly hero that took damage
    AMOUNT = IntArg()

    def do(self, source, target, amount):
        if amount <= 0:
            return
        game = source.game
        # Only on the controller's own turn.
        if game.current_player is not target.controller:
            return
        game.queue_actions(source, [Heal(target, amount)])
        game.queue_actions(source, [Hit(RANDOM_ENEMY_CHARACTER, amount)])


class _SkirtingDeathSteal(TargetedAction):
    """Skirting Death — your hero steals up to 4 Attack from the chosen
    minion this turn: the minion loses that Attack and your hero gains it
    (both effects last until end of turn)."""

    TARGET = ActionArg()  # the chosen minion

    def do(self, source, target):
        steal = min(4, max(0, target.atk))
        if steal <= 0:
            return
        game = source.game
        game.queue_actions(source, [Buff(target, "VAC_931e", atk=-steal)])
        game.queue_actions(
            source, [Buff(source.controller.hero, "VAC_931e1", atk=steal)]
        )


##
# Minions


class VAC_501:
    """Aranna, Thrill Seeker"""

    # [x]<b>Priest Tourist</b> Damage your hero takes on your turn is
    # redirected to a random enemy.
    # (Tourist is a deckbuilding keyword only — no in-game trigger.)
    events = Damage(FRIENDLY_HERO).on(
        _ArannaRedirect(Damage.TARGET, Damage.AMOUNT)
    )


class VAC_927:
    """Adrenaline Fiend"""

    # After a friendly Pirate attacks, give your hero +1 Attack this turn.
    events = Attack(FRIENDLY + PIRATE).after(Buff(FRIENDLY_HERO, "VAC_927e"))


class VAC_927e:
    """Adrenaline"""

    # Increased Attack this turn.
    tags = {GameTag.ATK: 1}
    events = OWN_TURN_END.on(Destroy(SELF))


class VAC_930:
    """All Terrain Voidhound"""

    # Whenever this attacks, give your hero +5 Attack this turn.
    events = Attack(SELF).on(Buff(FRIENDLY_HERO, "VAC_930e"))


class VAC_930e:
    """Off Road"""

    # Increased Attack this turn.
    tags = {GameTag.ATK: 5}
    events = OWN_TURN_END.on(Destroy(SELF))


class VAC_933:
    """Patches the Pilot"""

    # [x]<b>Battlecry:</b> Shuffle six Parachutes into your deck that summon
    # a 1/1 Pirate with <b>Charge</b> when drawn.
    play = Shuffle(CONTROLLER, "VAC_933t") * 6


class VAC_933t:
    """Parachute"""

    # <b>Casts When Drawn</b> Summon a 1/1 Pirate with <b>Charge</b>.
    play = Summon(CONTROLLER, "VAC_926t")


class VAC_932:
    """Climbing Hook"""

    # Doesn't lose Durability while you control a minion with 5 or more Attack.
    doesnt_lose_durability = lambda self, x: any(
        m.atk >= 5 for m in self.controller.field
    )


class VAC_932e:
    """Hooked"""

    # Doesn't lose Durability while you control a minion with 5 or more Attack.
    # (Cosmetic tracker enchant — the weapon class carries the real logic.)


##
# Spells


class VAC_925:
    """Sigil of Skydiving"""

    # At the start of your next turn, summon three 1/1 Pirates with <b>Charge</b>.
    events = OWN_TURN_BEGIN.on(Summon(CONTROLLER, "VAC_926t") * 3, Destroy(SELF))


class VAC_926:
    """Cliff Dive"""

    # [x]Summon 2 minions from your deck and give them <b>Rush</b>. They go
    # back at the end of your turn.
    play = (
        Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)).then(
            GiveRush(Summon.CARD), Buff(Summon.CARD, "VAC_926e")
        )
        * 2
    )


class VAC_926e:
    """Bungee Jumping"""

    # Returns to deck at end of turn.
    events = OWN_TURN_END.on(Shuffle(CONTROLLER, OWNER))


class VAC_926t:
    """Falling Illidari"""

    # <b>Charge</b> (1/1 Pirate — Charge supplied by data tags).
    tags = {GameTag.CHARGE: True}


class VAC_928:
    """Paraglide"""

    # [x]Both players draw 3 cards. <b>Outcast:</b> Only you do.
    play = Draw(ALL_PLAYERS) * 3
    outcast = Draw(CONTROLLER) * 3


class VAC_931:
    """Skirting Death"""

    # Choose a minion. This turn, your hero steals 4 Attack from it.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _SkirtingDeathSteal(TARGET)


class VAC_931e:
    """Skirting Death"""

    # -4 Attack this turn (amount supplied at buff time).
    events = OWN_TURN_END.on(Destroy(SELF))


class VAC_931e1:
    """Skirted"""

    # +@ Attack this turn (amount supplied at buff time).
    events = OWN_TURN_END.on(Destroy(SELF))


##
# Locations


class VAC_929:
    """Dangerous Cliffside"""

    # [x]Summon two 1/1 Pirates with <b>Charge</b>. After your hero attacks,
    # reopen this.
    activate = Summon(CONTROLLER, "VAC_926t") * 2
    events = Attack(FRIENDLY_HERO).after(ReopenLocation(SELF))
