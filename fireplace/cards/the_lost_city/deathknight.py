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
                # "They fight!" is a single SIMULTANEOUS strike — each deals its
                # Attack to the other at once (not two sequential Attack()s,
                # which would let the first kill the second before it retaliates
                # and would fire attack triggers / exhaust them).
                a_atk, b_atk = a.atk, b.atk
                ctrl.game.cheat_action(source, [Hit(a, b_atk), Hit(b, a_atk)])


class _StampCorpseBaseline(TargetedAction):
    """Reanimate the Terror - capture the controller's lifetime corpses-spent
    count when the Quest is played, so progress = corpses spent SINCE then."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._corpse_base = target.controller.corpses_spent_this_game


class _DirehornSpendForReborn(TargetedAction):
    """Hollow Direhorn (DINO_416) - after a friendly minion dies, if the
    controller has at least 3 Corpses, spend them and grant Reborn to the
    Direhorn. `source` is the Direhorn. If it already has Reborn or there
    aren't enough Corpses, nothing happens."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if source.zone != Zone.PLAY:
            return
        if source.reborn:
            return
        if ctrl.corpses < 3:
            return
        ctrl.game.cheat_action(source, [SpendCorpses(ctrl, 3)])
        source.game.cheat_action(source, [SetTags(source, {GameTag.REBORN: True})])


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

    # Rush, Lifesteal (data). Costs Corpses instead of Mana. The Corpse cost is
    # the CARD_ALTERNATE_COST tag (3), NOT the mana COST tag (5): zero the mana
    # cost, gate playability on having >= 3 Corpses, and spend exactly 3 on play.
    cost = SET(0)
    requirements = {PlayReq.REQ_MINIMUM_CORPSES: 3}
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

    # Quest: Spend Corpses (count from the QUEST_PROGRESS_TOTAL data tag, 15 at
    # build 226928). Reward: Tyrax, Bone Terror. SpendCorpses does not broadcast
    # an event, so we track progress by polling the lifetime corpses-spent
    # counter against a baseline captured when the Quest is played.
    # process_reward() (run after every action block) fires the reward once
    # progress reaches the total. progress_total falls back to the data tag.
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
    # The enchant's CONTROLLER is the caster (the Wave of Tar player), but the
    # tax must persist through the *taxed minion's* controller's turn — so the
    # expiry triggers on OWNER_CONTROLLER's EndTurn (the enemy), not the
    # caster's OWN_TURN_END (which would lift the tax before the enemy's turn
    # even began).
    tags = {
        GameTag.CARDNAME: "Tar-Covered",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: 2,
    }
    events = EndTurn(OWNER_CONTROLLER).on(Destroy(SELF))


##
# The Lost City of Un'Goro mini-set (Dinosaurs, DINO_) — Death Knight


class DINO_416:
    """Hollow Direhorn"""

    # Rush (data). After a friendly minion dies, spend 3 Corpses to gain
    # Reborn. FRIENDLY + MINION (without IN_PLAY) still matches the dying
    # minion that has already moved to the graveyard by AFTER-time. SELF is
    # excluded so the Direhorn's own death never tries to revive it.
    events = Death(FRIENDLY + MINION - SELF).on(
        _DirehornSpendForReborn(SELF)
    )


class DINO_415:
    """Story of Umbra"""

    # Discover a Deathrattle minion that costs (5) or more. Summon it and
    # trigger its Deathrattle.
    play = Discover(
        CONTROLLER,
        RandomMinion(
            deathrattle=True,
            custom_filter=lambda c: (c.cost or 0) >= 5,
        ),
    ).then(
        Summon(CONTROLLER, Discover.CARD).then(
            Deathrattle(Summon.CARD)
        )
    )


class DINO_417:
    """Soulrest Ceremony"""

    # Give your minions +1 Attack and Rush. They die at the end of your turn.
    play = Buff(FRIENDLY_MINIONS, "DINO_417e")


class DINO_417e:
    # Soulrest - +1 Attack and Rush. At the end of your turn, this minion dies.
    # The enchant exists in data (no stat/keyword tags there); we supply the
    # +1 Attack, Rush, and the end-of-turn self-destroy trigger.
    tags = {
        GameTag.ATK: 1,
        GameTag.RUSH: True,
    }
    events = OWN_TURN_END.on(Destroy(OWNER))
