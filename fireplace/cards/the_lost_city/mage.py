from ..utils import *


##
# Minions


class TLC_220:
    """Windswept Pageturner"""

    # After you summon an Elemental, deal 3 damage to a random enemy.
    events = Summon(CONTROLLER, MINION + ELEMENTAL - SELF).after(
        Hit(RANDOM_ENEMY_CHARACTER, 3)
    )


class TLC_226:
    """Conjured Bookkeeper"""

    # Deathrattle: Draw a spell. Kindred: Summon a copy of this.
    deathrattle = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)),
        Kindred() & Summon(CONTROLLER, "TLC_226"),
    )


class TLC_452:
    """Titanographer Osk"""

    # Gains a random Titan ability in your hand that changes each turn.
    #
    # APPROXIMATION: the printed card grafts one of 35 unscripted 7/7/7
    # "Titan ability" battlecry tokens (TLC_452t1..t35) onto Osk while it is
    # in hand, re-rolling the choice every turn, and fires that battlecry when
    # Osk is played. Those tokens' battlecries are not scripted, so we ship
    # Osk as a vanilla 7/7/7 body. Tracked in review.csv.
    pass


class TLC_461:
    """Scrappy Scavenger"""

    # Battlecry: Discover a card with Cost equal to your remaining Mana
    # Crystals.
    play = DISCOVER(RandomCollectible(cost=CURRENT_MANA(CONTROLLER)))


class TLC_483:
    """Vault Breaker"""

    # After you Discover a card, reduce its Cost by (1).
    events = Discovered(CONTROLLER).on(Buff(Discovered.CARD, "TLC_483e"))


@custom_card
class TLC_483e:
    # Vault Breaker — discovered card costs (1) less.
    tags = {
        GameTag.CARDNAME: "Vault Breaker",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


##
# Spells


class TLC_334:
    """Relic of Kings"""

    # Discover a spell from any class that costs (8) or more. It costs (1).
    play = Discover(
        CONTROLLER,
        RandomSpell(custom_filter=lambda c: (c.cost or 0) >= 8, card_class=None),
    ).then(Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "TLC_334e")))


@custom_card
class TLC_334e:
    # Relic of Kings — set the discovered spell's Cost to (1).
    tags = {
        GameTag.CARDNAME: "Relic of Kings",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    cost = SET(1)


class TLC_364:
    """Story of the Waygate"""

    # Reduce the Cost of cards in your hand that didn't start in your deck
    # by (1).
    play = Buff(FRIENDLY_HAND - STARTING_DECK - SELF, "TLC_364e")


@custom_card
class TLC_364e:
    # Story of the Waygate — costs (1) less.
    tags = {
        GameTag.CARDNAME: "Story of the Waygate",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class TLC_365:
    """Storage Scuffle"""

    # Deal 3 damage to a minion. Costs (0) if you've Discovered this turn.
    # COST: -100 delta clamps to 0 (engine floors cost at 0).
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3)
    cost_mod = (Attr(CONTROLLER, "discovers_this_turn") >= 1) & -100


class TLC_462:
    """Unearthed Artifacts"""

    # Summon a random 2-Cost minion. If you've Discovered this turn, summon a
    # random 4-Cost minion instead.
    play = (Attr(CONTROLLER, "discovers_this_turn") >= 1) & Summon(
        CONTROLLER, RandomMinion(cost=4)
    ) | Summon(CONTROLLER, RandomMinion(cost=2))


##
# Quest


class TLC_460:
    """The Forbidden Sequence"""

    # Quest: Discover cards (total from QUEST_PROGRESS_TOTAL data tag, 7 at
    # build 226928). Reward: The Origin Stone.
    quest = Discovered(CONTROLLER).on(AddProgress(SELF, Discovered.CARD))
    reward = Give(CONTROLLER, "TLC_460t")


class TLC_460t:
    """The Origin Stone"""

    # After you Discover a card, this plays the other options. Lose 1
    # Durability.
    #
    # APPROXIMATION: the printed weapon replays the two un-chosen Discover
    # options and loses durability each time you Discover. Replaying arbitrary
    # un-chosen options is not modelled; we ship the 0/8/3 weapon body so the
    # quest reward still resolves. Tracked in review.csv.
    pass


##
# The Lost City of Un'Goro mini-set (Dinosaurs, DINO_)


class DINO_409:
    """Techysaurus"""

    # Taunt. Costs (1) less for each card you played this game that didn't
    # start in your deck.
    # cards_played_this_game records hand-plays; subtract the starting deck so
    # only "didn't start in your deck" cards count.
    cost_mod = -Count(CARDS_PLAYED_THIS_GAME - STARTING_DECK)


class _TributeDanceMorph(TargetedAction):
    """Tribute Dance — transform the first chosen minion (TARGET) into a copy
    of a second, different minion (FORM)."""

    TARGET = ActionArg()
    FORM = CardArg()

    def get_target_args(self, source, target):
        from ...actions import _eval_card

        form = _eval_card(source, self._args[1])
        form = form[0] if isinstance(form, list) and form else form
        return [form]

    def do(self, source, target, form):
        if target is None or form is None:
            return
        source.game.queue_actions(source, [Morph(target, form.id)])


class DINO_414:
    """Tribute Dance"""

    # Choose a minion. Choose a different minion to transform it into.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }

    def play(self):
        target = self.target
        if target is None:
            return
        # Second pick: any minion other than the one being transformed.
        target_eid = target.entity_id
        others = FuncSelector(
            lambda entities, source: [
                m
                for m in ALL_MINIONS.eval(source.game, source)
                if m.entity_id != target_eid
            ]
        )
        yield Find(others) & ChoiceTarget(CONTROLLER, others).then(
            _TributeDanceMorph(target, ChoiceTarget.CARD)
        )


class DINO_429:
    """Sheep Mask"""

    # Set a minion's stats to 1/1 and give it "Deathrattle: Deal 2 damage to
    # all minions."
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "DINO_429e")


class DINO_429e:
    # Sheep Mask — stats set to 1/1, plus the Deathrattle.
    tags = {GameTag.DEATHRATTLE: True}
    atk = lambda self, i: 1
    max_health = lambda self, i: 1
    deathrattle = Hit(ALL_MINIONS, 2)
