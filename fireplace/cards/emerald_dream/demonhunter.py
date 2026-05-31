from ..utils import *


# Random picker over the three Dormant Dreadseed tokens (defined at the
# bottom of this file).
RandomDreadseed = lambda **kw: RandomCardPicker(
    card_id=["EDR_840t", "EDR_840t1", "EDR_840t2"], is_standard=None, **kw
)


##
# Minions


class _OmenAttacked(TargetedAction):
    """Omen — bump the per-minion strike counter each time it attacks."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._omen_strikes = getattr(target, "_omen_strikes", 0) + 1


class _OmenDeathrattle(TargetedAction):
    """Omen — deal (1 + strikes) damage to all enemies on death."""

    TARGET = ActionArg()

    def do(self, source, target):
        amount = 1 + getattr(source, "_omen_strikes", 0)
        enemies = (ENEMY_CHARACTERS - DEAD).eval(source.game, source)
        if enemies:
            source.game.cheat_action(source, [Hit(enemies, amount)])


class EDR_421:
    """Omen"""

    # Rush, Windfury. Deathrattle: Deal @ damage to all enemies.
    # (Improves after this attacks!) Base 1, +1 per attack.
    events = Attack(SELF).on(_OmenAttacked(SELF))
    deathrattle = _OmenDeathrattle(SELF)


class EDR_493:
    """Alara'shi"""

    # Battlecry: Transform minions in your hand into random Demons.
    # (They keep their original stats and Cost.)
    def play(self):
        for minion in (FRIENDLY_HAND + MINION).eval(self.game, self):
            yield Morph(minion, RandomDemon()).then(
                SetStateBuff(Morph.CARD, Morph.TARGET, "EDR_493e"),
                SetStateBuff(Morph.CARD, Morph.TARGET, "EDR_493e2"),
            )


class EDR_493e:
    # Demon Cost — restore the pre-transform Cost.
    events = REMOVED_IN_PLAY
    cost = lambda self, _: self._xcost


class EDR_493e2:
    # Demon Form — restore the pre-transform Attack/Health.
    atk = lambda self, _: self._xatk
    max_health = lambda self, _: self._xhealth


class EDR_841:
    """Dreadsoul Corrupter"""

    # Battlecry and Deathrattle: Summon a random Dormant Dreadseed.
    play = Summon(CONTROLLER, RandomDreadseed())
    deathrattle = Summon(CONTROLLER, RandomDreadseed())


class EDR_890:
    """Nightmare Dragonkin"""

    # Deathrattle: Reduce the Cost of the right-most card in your hand by (2).
    deathrattle = Buff(RIGHTMOST(FRIENDLY_HAND), "EDR_890e")


@custom_card
class EDR_890e:
    # Reduce Cost by (2).
    tags = {
        GameTag.CARDNAME: "Nightmarish",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class _ResurrectAndCopy(TargetedAction):
    """Resurrect one eligible friendly dead Deathrattle minion (the actual
    dead card) and summon a copy of it. ``CARDS`` selects the candidate
    pool; one is chosen at random and both the original and a clone are
    summoned."""

    TARGET = ActionArg()
    CARDS = CardArg()

    def get_target_args(self, source, target):
        selector = self._args[1]
        pool = selector.eval(source.game, source)
        if not pool:
            return [None]
        return [source.game.random.choice(pool)]

    def do(self, source, target, card):
        if card is None:
            return
        player = source.controller
        # Resurrect the actual dead card, then summon a fresh copy (base
        # stats) of the same minion alongside it.
        clone = player.card(card.id, source=source)
        clone.controller = player
        source.game.cheat_action(
            source, [Summon(player, card), Summon(player, clone)]
        )


class EDR_891:
    """Ravenous Felhunter"""

    # Deathrattle: Resurrect a friendly Deathrattle minion that costs (4) or
    # less. Summon a copy of it.
    deathrattle = _ResurrectAndCopy(
        CONTROLLER, FRIENDLY + KILLED + MINION + DEATHRATTLE + (COST <= 4)
    )


class EDR_892:
    """Ferocious Felbat"""

    # Deathrattle: Resurrect a different friendly Deathrattle minion that costs
    # (5) or more. Summon a copy of it.
    deathrattle = _ResurrectAndCopy(
        CONTROLLER, FRIENDLY + KILLED + MINION + DEATHRATTLE + (COST >= 5) - SELF
    )


##
# Weapons


class _DefiledSpearStrike(TargetedAction):
    """Defiled Spear — after the hero attacks an enemy, deal the hero's
    Attack to another random enemy (not the one just attacked)."""

    TARGET = ActionArg()  # the defender just attacked

    def do(self, source, target):
        hero = source.controller.hero
        amount = hero.atk
        if amount <= 0:
            return
        others = (ENEMY_CHARACTERS - DEAD).eval(source.game, source)
        others = [c for c in others if c is not target]
        if not others:
            return
        victim = source.game.random.choice(others)
        source.game.cheat_action(source, [Hit(victim, amount)])


class EDR_842:
    """Defiled Spear"""

    # After your hero attacks an enemy, deal your hero's Attack damage to
    # another random enemy.
    events = Attack(FRIENDLY_HERO).after(_DefiledSpearStrike(SELF, Attack.DEFENDER))


##
# Spells


class EDR_820:
    """Wyvern's Slumber"""

    # Choose One - Summon two Dormant Dreadseeds; or Deal $2 damage to all
    # minions.
    choose = ("EDR_820a", "EDR_820b")
    play = ChooseBoth(CONTROLLER) & (
        Summon(CONTROLLER, RandomDreadseed()) * 2,
        Hit(ALL_MINIONS, 2),
    )


class EDR_820a:
    """Encroaching Fear"""

    # Summon two random Dormant Dreadseeds.
    play = Summon(CONTROLLER, RandomDreadseed()) * 2


class EDR_820b:
    """Awoken Darkness"""

    # Deal $2 damage to all minions.
    play = Hit(ALL_MINIONS, 2)


class EDR_840:
    """Grim Harvest"""

    # Draw a card. Summon a random Dormant Dreadseed.
    play = (Draw(CONTROLLER), Summon(CONTROLLER, RandomDreadseed()))


class _JumpscareDiscover(Discover):
    """Jumpscare! — Discover a Demon costing (5)+; the two un-chosen cards
    are shuffled into the controller's deck instead of being discarded."""

    def choose(self, card):
        leftovers = [c for c in self.cards if c is not card]
        super().choose(card)
        if leftovers:
            self.source.game.cheat_action(
                self.source, [Shuffle(self.player, leftovers)]
            )


class EDR_882:
    """Jumpscare!"""

    # Discover a Demon that costs (5) or more with a Dark Gift. Shuffle the
    # other two into your deck.
    # Note: the "Dark Gift" attachment is a cross-class mechanic handled
    # elsewhere; this script performs the Discover (Demon, Cost 5+) and the
    # shuffle-the-rest behaviour.
    play = _JumpscareDiscover(
        CONTROLLER, RandomDemon(custom_filter=lambda c: (c.cost or 0) >= 5)
    ).then(Give(CONTROLLER, Discover.CARD))


##
# Tokens — Dormant Dreadseeds


class EDR_840t:
    """Hound Dreadseed"""

    # Dormant for 2 turns. When this awakens, give your hero +3 Attack this
    # turn.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 2
    awaken = Buff(FRIENDLY_HERO, "EDR_840te")


class EDR_840te:
    # Hound's Fangs — +3 Attack this turn.
    tags = {GameTag.ATK: 3, GameTag.TAG_ONE_TURN_EFFECT: True}


class EDR_840t1:
    """Crow Dreadseed"""

    # Elusive. Dormant for 1 turn.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 1


class EDR_840t2:
    """Serpent Dreadseed"""

    # Taunt, Lifesteal. Dormant for 3 turns.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 3
