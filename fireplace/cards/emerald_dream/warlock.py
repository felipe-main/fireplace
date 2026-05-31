from ..utils import *

from hearthstone.enums import CardType, GameTag, Race

from .neutral import _GiveDarkGift


##
# Custom actions


class _FractureTick(TargetedAction):
    """Rotten Apple — at the end of each of your next 2 turns, deal 3 damage
    to your hero, then tear the countdown enchant down once it has fired
    twice."""

    TARGET = ActionArg()

    def do(self, source, target):
        ticks = getattr(source, "_fracture_ticks", 0) + 1
        source._fracture_ticks = ticks
        ctrl = source.controller
        source.game.cheat_action(source, [Hit(ctrl.hero, 3)])
        if ticks >= 2:
            source.game.cheat_action(source, [Destroy(source)])


class _DelayedManaTick(TargetedAction):
    """Fractured Power — count down two of the controller's turn-begins, then
    gain two Mana crystals and remove the countdown enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        ticks = getattr(source, "_delayed_mana_ticks", 0) + 1
        source._delayed_mana_ticks = ticks
        if ticks >= 2:
            ctrl = source.controller
            source.game.cheat_action(source, [GainMana(ctrl, 2), Destroy(source)])


class _GainDeathrattlesDiedThisTurn(TargetedAction):
    """Archdruid of Thorns — gain the Deathrattles of your minions that died
    this turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for dead in list(ctrl.graveyard):
            if dead.type != CardType.MINION:
                continue
            if not dead.killed_this_turn:
                continue
            if not dead.has_deathrattle:
                continue
            source.game.cheat_action(
                source, [CopyDeathrattleBuff(dead, "EDR_491e")]
            )


class _HungeringEat(TargetedAction):
    """Hungering Ancient — eat a random minion in your deck, gain its stats,
    and remember it so the Deathrattle can hand it back."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        deck_minions = [c for c in ctrl.deck if c.type == CardType.MINION]
        if not deck_minions:
            return
        eaten = source.game.random.choice(deck_minions)
        atk = eaten.atk
        hp = eaten.health
        eaten_id = eaten.id
        source._hungering_eaten = getattr(source, "_hungering_eaten", []) + [eaten_id]
        source.game.cheat_action(
            source,
            [
                Buff(source, "EDR_494e", atk=atk, max_health=hp),
                Destroy(eaten),
            ],
        )


class _HungeringDeathrattle(TargetedAction):
    """Hungering Ancient — add every minion it ate back to your hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for cid in getattr(source, "_hungering_eaten", []):
            source.game.cheat_action(source, [Give(ctrl, cid)])


class _WallowAbsorb(TargetedAction):
    """Wallow, the Wretched — while in hand or deck, copy every Dark Gift
    given to your minions that it has not already absorbed."""

    TARGET = ActionArg()

    def do(self, source, target):
        absorbed = getattr(source, "_wallow_absorbed", set())
        absorbed = set(absorbed)
        for minion in source.controller.field:
            for gift_id in getattr(minion, "_dark_gifts", []):
                key = (id(minion), gift_id)
                if key in absorbed:
                    continue
                absorbed.add(key)
                source.game.cheat_action(source, [Buff(source, gift_id)])
        source._wallow_absorbed = absorbed


class _AgamagganMark(TargetedAction):
    """Agamaggan — the next card you play costs your opponent's Health instead
    of Mana (up to 10). Arms the cost-substituting aura on the hero."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Buff(source.controller.hero, "EDR_489e")])


class _AgamagganPay(TargetedAction):
    """Agamaggan — when the next card is played, deal its (capped) Cost to the
    enemy hero and consume the aura. TARGET is the played card (Play.CARD)."""

    TARGET = ActionArg()

    def do(self, source, target):
        # `target` is the card that was just played. Its printed Cost is the
        # amount of opponent Health to spend, capped at 10.
        cost = min(10, target.data.cost or 0)
        enemy = source.controller.opponent.hero
        if cost > 0:
            source.game.cheat_action(source, [Hit(enemy, cost)])
        source.game.cheat_action(source, [Destroy(source)])


##
# Spells


class EDR_482:
    """Rotten Apple"""

    # Restore #12 Health to your hero. For the next 2 turns, deal $3 damage to
    # your hero.
    play = Heal(FRIENDLY_HERO, 12), Buff(FRIENDLY_HERO, "EDR_482e")


class EDR_482e:
    # Fracture — at the end of your turn, deal 3 damage to your hero (twice).
    events = OWN_TURN_END.on(_FractureTick(SELF))


class EDR_483:
    """Fractured Power"""

    # Destroy one of your Mana Crystals. In 2 turns, gain two.
    play = GainMana(CONTROLLER, -1), Buff(FRIENDLY_HERO, "EDR_483e")


class EDR_483e:
    # Delayed Mana — gain 2 mana in 2 turns.
    events = OWN_TURN_BEGIN.on(_DelayedManaTick(SELF))


class EDR_488:
    """Avant-Gardening"""

    # Discover a Deathrattle minion with a Dark Gift.
    # The discovered minion is given a random Dark Gift (shared EDR keyword
    # mechanic — modelled by `_GiveDarkGift` as a random Nightmare Bonus
    # Effect, the same approximation every sibling Dark-Gift card uses).
    play = Discover(
        CONTROLLER,
        RandomMinion(deathrattle=True),
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))


class EDR_490:
    """Sleep Paralysis"""

    # Choose One - Summon two 3/6 Demons with Taunt that can't attack; or
    # Destroy an enemy minion.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    choose = ("EDR_490a", "EDR_490b")
    # Under a Choose-Both effect the destroy half hits the player-chosen TARGET
    # (the parent's REQ_TARGET_IF_AVAILABLE carries the selection through), so a
    # combined cast destroys the chosen enemy minion rather than a random one.
    play = ChooseBoth(CONTROLLER) & (
        Summon(CONTROLLER, "EDR_490t") * 2,
        Destroy(TARGET),
    )


class EDR_490a:
    """Figure in the Dark"""

    # Summon two 3/6 Demons with Taunt that can't attack.
    play = Summon(CONTROLLER, "EDR_490t") * 2


class EDR_490b:
    """Wit's End"""

    # Destroy an enemy minion.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Destroy(TARGET)


class EDR_490t:
    """Night Terror"""

    # Taunt. Can't attack.  (Taunt + CANT_ATTACK supplied by data.)


##
# Minions


class EDR_485:
    """Rotheart Dryad"""

    # Deathrattle: Draw a minion that costs (7) or more.
    deathrattle = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION + (COST >= 7)))


class EDR_487:
    """Wallow, the Wretched"""

    # While this is in your hand or deck, it gains a copy of every Dark Gift
    # given to your minions.
    # NOTE: Dark Gifts are granted by cards outside this file and the engine
    # has no Dark Gift broadcast yet, so this scan keys off the shared
    # convention that a granted Dark Gift enchant is appended to the recipient
    # minion's `_dark_gifts` list. Each turn Wallow copies any Dark Gift it has
    # not yet absorbed onto itself while it sits in hand or deck.
    class Hand:
        events = OWN_TURN_BEGIN.on(_WallowAbsorb(SELF))

    class Deck:
        events = OWN_TURN_BEGIN.on(_WallowAbsorb(SELF))


class EDR_489:
    """Agamaggan"""

    # Battlecry: The next card you play costs your OPPONENT'S Health instead of
    # Mana (up to 10).
    # NOTE: there is no engine flag for paying the OPPONENT's Health, so this
    # approximation makes the next card free (mana-wise, via the aura) and
    # deals its Cost (capped at 10) to the enemy hero on play.
    play = _AgamagganMark(SELF)


@custom_card
class EDR_489e:
    # Agamaggan — next card you play is free; on play, deal its Cost (up to
    # 10) to the enemy hero. The Refresh zeroes hand-card cost; _AgamagganPay
    # bills the opponent and tears the aura down.
    tags = {
        GameTag.CARDNAME: "Agamaggan",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    update = Refresh(FRIENDLY_HAND, {GameTag.COST: -100})
    events = OWN_CARD_PLAY.on(_AgamagganPay(Play.CARD))


class EDR_491:
    """Archdruid of Thorns"""

    # Battlecry: Gain the Deathrattles of your minions that died this turn.
    play = _GainDeathrattlesDiedThisTurn(SELF)


class EDR_494:
    """Hungering Ancient"""

    # At the end of your turn, eat a minion in your deck and gain its stats.
    # Deathrattle: Add them to your hand.
    events = OWN_TURN_END.on(_HungeringEat(SELF))
    deathrattle = _HungeringDeathrattle(SELF)


class EDR_654:
    """Overgrown Horror"""

    # Taunt. Battlecry: Reduce the Cost of minions in your hand with Dark Gifts
    # by (2).
    # NOTE: "with Dark Gifts" filters on the shared `_dark_gifts` marker that
    # gift-granting cards append to a minion. Minions carrying a Dark Gift get
    # a -2 cost enchant.
    def play(self):
        for card in self.controller.hand:
            if card.type != CardType.MINION:
                continue
            if getattr(card, "_dark_gifts", None):
                yield Buff(card, "EDR_654e")


class EDR_654e:
    # Overgrown Horror — Dark Gift minion costs (2) less.
    tags = {GameTag.COST: -2}
