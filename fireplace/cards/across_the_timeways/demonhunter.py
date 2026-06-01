from ..utils import *


##
# Collectibles


class TIME_020:
    """Broxigar"""

    # Fabled, Charge
    # Start of Game: Disappear. Kill all 4 Demons from Argus to reappear in
    # hand.
    #
    # At the start of the game Broxigar removes himself from the deck, equips
    # the Axe of Cenarius, and shuffles the First Portal to Argus into the
    # deck. The Axe (after your hero attacks and kills a minion) draws a
    # Portal; each Portal summons an escalating Demon for your opponent whose
    # deathrattle draws them a card and shuffles in the next Portal. When the
    # 4th (Final) Demon dies, Broxigar reappears in hand.
    class Deck:
        events = GameStart().on(
            Remove(SELF),
            Summon(CONTROLLER, "TIME_020t1"),
            Shuffle(CONTROLLER, "TIME_020t2"),
        )


class _DrawPortal(TargetedAction):
    """Axe of Cenarius — after your hero attacks and kills a minion, draw a
    Portal to Argus. Only fires when the just-attacked defender was a minion
    that is now dead / off the board."""

    TARGET = ActionArg()

    def do(self, source, target):
        hero = source.controller.hero
        defender = getattr(hero, "attack_target", None)
        if defender is None or defender.type != CardType.MINION:
            return
        if defender.zone == Zone.PLAY and not getattr(defender, "dead", False):
            return
        portals = [
            c
            for c in source.controller.deck
            if c.id.startswith("TIME_020t") and c.type == CardType.SPELL
        ]
        if portals:
            source.game.cheat_action(source, [Draw(source.controller, portals[0])])


class TIME_020t1:
    """Axe of Cenarius"""

    # Lifesteal
    # After your hero attacks and kills a minion, draw a Portal to Argus.
    events = Attack(FRIENDLY_HERO).after(_DrawPortal(CONTROLLER))


class TIME_020t2:
    """First Portal to Argus"""

    # Summon a 1/1 Demon for your opponent. When it dies, draw a card and
    # shuffle the next Portal into your deck.
    play = Summon(OPPONENT, "TIME_020t2t")


class TIME_020t2t:
    """Fleeing Ur'zul"""

    # Deathrattle: Your opponent draws a card. Shuffle the Second Portal to
    # Argus into their deck.
    # (Token data lacks the DEATHRATTLE tag, so declare it for the engine.)
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = (Draw(OPPONENT), Shuffle(OPPONENT, "TIME_020t3"))


class TIME_020t3:
    """Second Portal to Argus"""

    # Summon a 2/1 Demon for your opponent. When it dies, draw a card and
    # shuffle the next Portal into your deck.
    play = Summon(OPPONENT, "TIME_020t3t")


class TIME_020t3t:
    """Fleeing Incubus"""

    # Deathrattle: Your opponent draws a card. Shuffle the Third Portal to
    # Argus into their deck.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = (Draw(OPPONENT), Shuffle(OPPONENT, "TIME_020t4"))


class TIME_020t4:
    """Third Portal to Argus"""

    # Summon a 3/1 Demon for your opponent. When it dies, draw a card and
    # shuffle the next Portal into your deck.
    play = Summon(OPPONENT, "TIME_020t4t")


class TIME_020t4t:
    """Fleeing Wrathguard"""

    # Deathrattle: Your opponent draws a card. Shuffle the Final Portal to
    # Argus into their deck.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = (Draw(OPPONENT), Shuffle(OPPONENT, "TIME_020t5"))


class TIME_020t5:
    """Final Portal to Argus"""

    # Summon a 4/1 Demon for your opponent. When it dies, Broxigar reappears
    # in your hand.
    play = Summon(OPPONENT, "TIME_020t5t")


class TIME_020t5t:
    """Fleeing Terrorguard"""

    # Deathrattle: Broxigar reappears in your opponent's hand.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Give(OPPONENT, "TIME_020")


class TIME_021:
    """Doomsday Prepper"""

    # Outcast: Your hero is Immune until your next turn.
    outcast = Buff(FRIENDLY_HERO, "TIME_021e")


@custom_card
class TIME_021e:
    # Doomsday — hero Immune until your next turn. Not a one-turn effect (it
    # must survive the opponent's turn), so it self-destroys at the start of
    # your next turn instead.
    tags = {
        GameTag.CARDNAME: "Doomsday Prepper",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.CANT_BE_DAMAGED: 1,
        GameTag.CANT_BE_TARGETED_BY_OPPONENTS: 1,
    }
    events = OWN_TURN_BEGIN.on(Destroy(SELF))


class TIME_022:
    """Perennial Serpent"""

    # Rush
    # Costs (4) less if a minion is Dormant.
    cost_mod = (Count(IN_PLAY + MINION + DORMANT) >= 1) & -4


class TIME_441:
    """Aeon Rend"""

    # Rewind
    # Deal $4 damage to two random enemies.
    # (Rewind is engine-handled — only the base effect lives here.)
    play = Hit(RANDOM_ENEMY_CHARACTER, 4) * 2


class _Imprison(TargetedAction):
    """Timeway Warden — imprison an enemy minion: it goes Dormant for 10,000
    turns. Remember it on the Warden so the deathrattle can awaken it."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._imprisoned = target
        source.game.cheat_action(
            source,
            [Dormant(target, 10000), Buff(target, "TIME_442e")],
        )


class _AwakenImprisoned(TargetedAction):
    """Timeway Warden deathrattle — awaken the minion it imprisoned."""

    TARGET = ActionArg()

    def do(self, source, target):
        prisoner = getattr(source, "_imprisoned", None)
        if prisoner is not None and prisoner.zone == Zone.PLAY:
            source.game.cheat_action(source, [Awaken(prisoner)])


class TIME_442:
    """Timeway Warden"""

    # Battlecry: Imprison an enemy minion. It goes Dormant for 10,000 turns.
    # Deathrattle: Awaken it.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = _Imprison(TARGET)
    deathrattle = _AwakenImprisoned(SELF)


class TIME_442e:
    """Eternal Imprisonment"""

    # Dormant. Awaken in 10,000 turns. (Cosmetic marker enchant — the actual
    # dormancy is applied by the _Imprison action.)
    tags = {}


class _HoundsOfFury(TargetedAction):
    """Hounds of Fury — summon two 3/3 Demons. If your deck has no minions,
    they immediately attack the lowest-Health enemy."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        before = set(player.field)
        source.game.cheat_action(
            source,
            [Summon(player, "TIME_443t"), Summon(player, "TIME_443t2")],
        )
        summoned = [m for m in player.field if m not in before]
        deck_has_minion = any(c.type == CardType.MINION for c in player.deck)
        if deck_has_minion:
            return
        for hound in summoned:
            if hound.zone != Zone.PLAY or getattr(hound, "dead", False):
                continue
            enemies = [
                m
                for m in player.opponent.characters
                if m.zone == Zone.PLAY and not getattr(m, "dead", False)
            ]
            if not enemies:
                break
            victim = min(enemies, key=lambda m: m.health)
            source.game.cheat_action(source, [Attack(hound, victim)])


class TIME_443:
    """Hounds of Fury"""

    # Summon two 3/3 Demons. If your deck has no minions, they attack the
    # lowest Health enemy.
    play = _HoundsOfFury(CONTROLLER)


class TIME_443t:
    """Sargeran Felhound"""


class TIME_443t2:
    """Sargeran Felhound"""


class TIME_444:
    """Time-Lost Glaive"""

    # Deathrattle: Get a random Demon from the past.
    deathrattle = Give(CONTROLLER, RandomDemon())


class _EternalHold(TargetedAction):
    """The Eternal Hold — get a Demon that costs (5) or more. If your deck has
    no minions, your next one costs (0) (modelled by zeroing the cost of the
    Demon you just got)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        demon = RandomDemon(custom_filter=lambda c: (c.cost or 0) >= 5)
        before = set(player.hand)
        source.game.cheat_action(source, [Give(player, demon)])
        deck_has_minion = any(c.type == CardType.MINION for c in player.deck)
        if deck_has_minion:
            return
        given = [c for c in player.hand if c not in before]
        for c in given:
            source.game.cheat_action(source, [Buff(c, "TIME_446e")])


class TIME_446:
    """The Eternal Hold"""

    # Get a Demon that costs (5) or more. If your deck has no minions, your
    # next one costs (0).
    activate = _EternalHold(CONTROLLER)


class TIME_446e:
    """Jailbreak"""

    # Your next minion costs (0). (Modelled as a cost-0 buff on the Demon you
    # got from The Eternal Hold.)
    tags = {GameTag.COST: -100}


class _Solitude(TargetedAction):
    """Solitude — if your deck has no minions, reduce the Cost of minions in
    your hand by (2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        deck_has_minion = any(c.type == CardType.MINION for c in player.deck)
        if deck_has_minion:
            return
        for c in list(player.hand):
            if c.type == CardType.MINION:
                source.game.cheat_action(source, [Buff(c, "TIME_448e")])


class TIME_448:
    """Solitude"""

    # Discover a minion. If your deck has no minions, reduce the Cost of any
    # in your hand by (2).
    play = DISCOVER(RandomMinion()).then(_Solitude(CONTROLLER))


@custom_card
class TIME_448e:
    # Solitude — minion in hand costs (2) less.
    tags = {
        GameTag.CARDNAME: "Solitude",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class _LastingLegacy(TargetedAction):
    """Lasting Legacy — give your hero +4 Attack this turn. If your deck has
    no minions, also give minions in your hand +4 Attack (permanent)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        source.game.cheat_action(source, [Buff(player.hero, "TIME_449e1")])
        deck_has_minion = any(c.type == CardType.MINION for c in player.deck)
        if deck_has_minion:
            return
        for c in list(player.hand):
            if c.type == CardType.MINION:
                source.game.cheat_action(source, [Buff(c, "TIME_449e2")])


class TIME_449:
    """Lasting Legacy"""

    # Give your hero +4 Attack this turn. If your deck has no minions, give
    # any in hand +4 Attack.
    play = _LastingLegacy(CONTROLLER)


class TIME_449e1:
    """Broxigar's Honor"""

    # +4 Attack this turn. (Data carries TAG_ONE_TURN_EFFECT — auto-expires.)
    tags = {GameTag.ATK: 4}


class TIME_449e2:
    """Broxigar's Legacy"""

    # +4 Attack.
    tags = {GameTag.ATK: 4}
