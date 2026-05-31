from ..utils import *

from hearthstone.enums import CardClass, GameTag, Race


##
# Custom actions


class _PaleomancyKeepAll(TargetedAction):
    """Paleomancy - Discover an Undead. If the controller has at least 5
    Corpses, spend them and add all 3 of the Discover options to hand
    instead of choosing one."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.corpses >= 5:
            picker = RandomMinion(race=Race.UNDEAD) * 3
            cards = picker.evaluate(source)
            ctrl.game.cheat_action(source, [SpendCorpses(ctrl, 5)])
            for cid in cards:
                ctrl.game.cheat_action(source, [Give(ctrl, cid)])
        else:
            ctrl.game.queue_actions(
                source,
                [Discover(ctrl, RandomMinion(race=Race.UNDEAD)).then(
                    Give(ctrl, Discover.CARD)
                )],
            )


class _SummonTwoDeathrattleFight(TargetedAction):
    """High Cultist Herenn - summon two Deathrattle minions from your deck,
    then they attack each other."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        pool = [
            c for c in ctrl.deck
            if c.type == CardType.MINION and c.has_deathrattle
        ]
        ctrl.game.random.shuffle(pool)
        summoned = []
        for card in pool[:2]:
            ctrl.game.cheat_action(source, [Summon(ctrl, card)])
            if card.zone == Zone.PLAY:
                summoned.append(card)
        if len(summoned) == 2:
            a, b = summoned
            if a.zone == Zone.PLAY and b.zone == Zone.PLAY:
                ctrl.game.cheat_action(source, [Attack(a, b)])
            if a.zone == Zone.PLAY and b.zone == Zone.PLAY:
                ctrl.game.cheat_action(source, [Attack(b, a)])


class _StampCorpseBaseline(TargetedAction):
    """Reanimate the Terror - capture the controller's lifetime corpses-spent
    count when the Quest is played, so progress = corpses spent SINCE then."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._corpse_base = target.controller.corpses_spent_this_game


##
# Minions


class TLC_401:
    """Bonechill Stegodon"""

    # Deathrattle: Deal 6 damage to three random enemies.
    deathrattle = Hit(RANDOM(ENEMY_CHARACTERS), 6) * 3


class TLC_432:
    """Dread Raptor"""

    # Battlecry: Draw a Deathrattle minion that costs (3) or less.
    # Kindred: It costs (0).
    play = Draw(
        CONTROLLER,
        RANDOM(FRIENDLY_DECK + MINION + DEATHRATTLE + (COST <= 3)),
    ).then(Kindred() & Buff(Draw.CARD, "TLC_432e"))


class TLC_436:
    """Reanimated Pterrordax"""

    # Rush, Lifesteal (data). Costs Corpses instead of Mana. Approximation:
    # zero the mana cost and spend its Corpse cost on play. The Corpse cost is
    # the CARD_ALTERNATE_COST tag (3), NOT the mana COST tag (5).
    cost = SET(0)
    play = SpendCorpses(CONTROLLER, 3)


class TLC_443:
    """Reluctant Wrangler"""

    # Reborn (data). Deathrattle: Summon a 2/2 Undead Beast with Taunt.
    deathrattle = Summon(CONTROLLER, "TLC_443t")


class TLC_810:
    """High Cultist Herenn"""

    # Battlecry: Summon two Deathrattle minions from your deck. They fight!
    play = _SummonTwoDeathrattleFight(CONTROLLER)


##
# Spells


class TLC_433:
    """Reanimate the Terror"""

    # Quest: Spend 18 Corpses. Reward: Tyrax, Bone Terror. SpendCorpses does
    # not broadcast an event, so we track progress by polling the lifetime
    # corpses-spent counter against a baseline captured when the Quest is
    # played. process_reward() (run after every action block) fires the
    # reward once progress reaches 18.
    progress_total = 18
    play = _StampCorpseBaseline(SELF)
    reward = Summon(CONTROLLER, "TLC_433t")

    def progress(self):
        base = getattr(self, "_corpse_base", 0)
        return max(0, self.controller.corpses_spent_this_game - base)

    def clear_progress(self):
        # After the reward fires, re-baseline so the Quest is "finished" and
        # won't re-trigger off later corpse spending.
        self._corpse_base = self.controller.corpses_spent_this_game


class TLC_434:
    """Paleomancy"""

    # Discover an Undead. Spend 5 Corpses to keep all 3 instead.
    play = _PaleomancyKeepAll(CONTROLLER)


class TLC_435:
    """Crypt Map"""

    # Discover a Frost Rune card. (The "play it this turn -> pick another"
    # follow-up is a noted approximation; we Discover one Frost Rune DK card.)
    play = Discover(
        CONTROLLER,
        RandomCollectible(
            card_class=CardClass.DEATHKNIGHT,
            custom_filter=lambda c: c.tags.get(GameTag.COST_FROST, 0) >= 1,
        ),
    ).then(Give(CONTROLLER, Discover.CARD))


class TLC_439:
    """Wave of Tar"""

    # Deal 2 damage to all enemy minions. Enemy minions cost (2) more next turn.
    play = (
        Hit(ENEMY_MINIONS, 2),
        Buff(ENEMY_HAND + MINION, "TLC_439e"),
    )


class TLC_440:
    """Cryosleep"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    # Deal 4 damage and draw a card. Kindred: Draw another.
    play = (
        Hit(TARGET, 4),
        Draw(CONTROLLER),
        Kindred() & Draw(CONTROLLER),
    )


##
# Reward token chain (Tyrax / Terror's Grave)


class TLC_433t:
    """Tyrax, Bone Terror"""

    # Deathrattle: Open Terror's Grave. It has "Deathrattle: Resummon Tyrax."
    deathrattle = Summon(CONTROLLER, "TLC_433t2")


class TLC_433t2:
    """Terror's Grave"""

    # Location. Deal 4 damage. Deathrattle: Resummon Tyrax, Bone Terror.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    activate = Hit(TARGET, 4)
    deathrattle = Summon(CONTROLLER, "TLC_433t")


##
# Tokens


class TLC_443t:
    """Reanimated Ossodon"""

    # 2/2 Undead Beast with Taunt - stats, races and Taunt live in data.


##
# Enchantments


@custom_card
class TLC_432e:
    # Dread Raptor - Kindred: the drawn Deathrattle minion costs (0). Not in
    # data: register name + COST tag (engine clamps the cost floor to 0).
    tags = {
        GameTag.CARDNAME: "Reanimated",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -100,
    }


@custom_card
class TLC_439e:
    # Wave of Tar - +2 cost on an enemy hand minion until that player's next
    # turn ends. Not in data: register a name + COST tag + expiry trigger.
    tags = {
        GameTag.CARDNAME: "Tar-Covered",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: 2,
    }
    events = OWN_TURN_END.on(Destroy(SELF))
