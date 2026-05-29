"""Showdown in the Badlands — Neutral Legendary cards (WILD_WEST)."""

from ..utils import *


##
# Custom actions


class _RenoEmptyEnemyBoard(TargetedAction):
    """Reno, Lone Ranger — "empty the enemy board": destroy every enemy
    minion (dormant ones included — the jail-style dormant guard in
    Destroy.do is bypassed because the printed card clears the entire
    board). Resolves all at once, mirroring the in-game wipe."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        victims = list(opp.field)
        for minion in victims:
            minion.dormant = False
            source.game.cheat_action(source, [Destroy(minion)])


class _KingpinResurrectOgreGang(TargetedAction):
    """Kingpin Pud — resurrect every friendly minion that died this game
    whose printed name starts with "Ogre-Gang" (Outlaw / Rider / Ace),
    then give each summoned copy Windfury. No de-duplication: a minion
    that died twice this game comes back twice, matching "Resurrect your
    Ogre-Gang". Summons stop once the board fills (engine drops the rest)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        pool = [
            c
            for c in ctrl.graveyard
            if c.type == CardType.MINION and c.data.name.startswith("Ogre-Gang")
        ]
        for dead in pool:
            source.game.cheat_action(
                source,
                [Summon(ctrl, dead.id).then(SetTag(Summon.CARD, GameTag.WINDFURY))],
            )


class _FlintFirearmGiveQuickdraw(TargetedAction):
    """Flint Firearm — add a random Quickdraw card to the controller's
    hand and stamp the WW_379e marker on it. WW_379e listens for that
    card's Play this turn and re-runs this action (the "repeat this"
    chain). The marker is a one-turn-effect, so if the card is not played
    this turn the chain ends on its own."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        picker = RandomCard(
            collectible=True,
            custom_filter=lambda c: bool(c.tags.get(GameTag.QUICKDRAW)),
        )
        source.game.cheat_action(
            source,
            [Give(ctrl, picker).then(
                Buff(Give.CARD, "WW_379e"), _FlintMarkCard(Give.CARD)
            )],
        )


class _FlintMarkCard(TargetedAction):
    """Tag the granted Quickdraw card so the player-level watcher
    (WW_379t) knows to repeat Flint's battlecry when it is played. A
    plain Python marker is used (not the WW_379e enchant's own events)
    because a SPELL's enchantments are cleaned up the instant it is cast,
    before a card-attached Play listener would fire — the marker survives
    on the card object regardless of card type."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._flint_marked = True


class _FlintRepeatIfMarked(TargetedAction):
    """Player-level: fired by WW_379t whenever the controller plays a
    card. If the played card carries the Flint marker, consume it and
    repeat Flint's battlecry (grant + mark another Quickdraw card). The
    fresh card is marked too, so the chain continues for as long as the
    player keeps playing the granted cards this turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not getattr(target, "_flint_marked", False):
            return
        target._flint_marked = False
        source.game.cheat_action(
            source, [_FlintFirearmGiveQuickdraw(source.controller)]
        )


class _OpenBadlandsJail(TargetedAction):
    """Sheriff Barrelbrim — "open the Badlands Jail": put the WW_359t
    location onto the board and immediately trigger it, making a random
    enemy minion go Dormant for 3 turns (jail catches an outlaw). If the
    opponent has no minion, the jail is still summoned, ready to be used
    on a future turn — matching the printed location behaviour."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(source, [Summon(ctrl, "WW_359t")])
        candidates = [m for m in ctrl.opponent.field if not m.dormant]
        if candidates:
            victim = source.game.random.choice(candidates)
            source.game.cheat_action(source, [Dormant(victim, 3)])


##
# Heroes


class WW_0700:
    """Reno, Lone Ranger"""

    # [x]<b>Battlecry:</b> If your deck has no duplicates, empty the enemy
    # board and limit it to 1 minion for a turn. <i>It's high noon!</i>
    powered_up = -FindDuplicates(FRIENDLY_DECK)
    play = powered_up & (
        _RenoEmptyEnemyBoard(CONTROLLER),
        Buff(OPPONENT, "WW_0700e1"),
        Summon(CONTROLLER, RandomEntourage()),
    )
    entourage = [
        "WW_0700p1",
        "WW_0700p2",
        "WW_0700p3",
        "WW_0700p4",
        "WW_0700p5",
        "WW_0700p6",
        "WW_0700p7",
    ]


class WW_0700e1:
    """Alone Ranger"""

    # Your board size is 1 for a turn. (Engine has no per-player board-size
    # cap primitive; this marker is a one-turn effect placeholder.)
    tags = {GameTag.TAG_ONE_TURN_EFFECT: True}


# The installed hero power (Reno's Handcannon) swaps into a random bullet
# each turn. Each bullet's activate fires its effect, then at end of turn it
# morphs into another random bullet (Dr. Boom, Mad Genius pattern).
_BULLETS = [
    "WW_0700p1",
    "WW_0700p2",
    "WW_0700p3",
    "WW_0700p4",
    "WW_0700p5",
    "WW_0700p6",
    "WW_0700p7",
]


class WW_0700p:
    """Reno's Handcannon"""

    # Shoot this turn's magic bullet! (Loads a random bullet on install.)
    entourage = _BULLETS
    events = OWN_TURN_BEGIN.on(Summon(CONTROLLER, RandomEntourage()))


class WW_0700p1:
    """Arcane Bullet"""

    # Deal $2 damage. Refresh 2 Mana Crystals. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), FillMana(CONTROLLER, 2)
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


class WW_0700p2:
    """Frost Bullet"""

    # Deal $2 damage. Gain $d4 Armor. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), GainArmor(FRIENDLY_HERO, 4)
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


class WW_0700p3:
    """Fire Bullet"""

    # Deal $2 damage, then deal $1 damage to all enemy minions. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), Hit(ENEMY_MINIONS, 1)
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


class WW_0700p4:
    """Holy Bullet"""

    # Deal $2 damage. Give a random friendly minion +2/+2. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), Buff(RANDOM_FRIENDLY_MINION, "WW_0700p4e1")
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


WW_0700p4e1 = buff(+2, +2)


class WW_0700p5:
    """Nature Bullet"""

    # Deal $2 damage. Discover a spell. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), DISCOVER(RandomSpell())
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


class WW_0700p6:
    """Shadow Bullet"""

    # Deal $2 damage. Summon a random 3-Cost minion. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), Summon(CONTROLLER, RandomMinion(cost=3))
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


class WW_0700p7:
    """Fel Bullet"""

    # Deal $2 damage. Draw a card. Swaps each turn.
    entourage = _BULLETS
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 2), Draw(CONTROLLER)
    events = OWN_TURN_END.on(Summon(CONTROLLER, RandomEntourage(exclude=SELF)))


##
# Minions


class WW_359:
    """Sheriff Barrelbrim"""

    # <b>Battlecry:</b> If you have 20 or less Health, open the Badlands Jail.
    powered_up = CURRENT_HEALTH(FRIENDLY_HERO) <= 20
    play = powered_up & _OpenBadlandsJail(CONTROLLER)


class WW_359t:
    """Badlands Jail"""

    # Make a minion go <b>Dormant</b> for 3 turns.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    activate = Dormant(TARGET, 3)


class WW_379:
    """Flint Firearm"""

    # [x]<b>Battlecry:</b> Get a random <b>Quickdraw</b> card. If you play
    # it this turn, repeat this.
    # Install the one-turn player-level watcher (WW_379t) that repeats the
    # battlecry whenever a Flint-marked card is played, then grant + mark the
    # first Quickdraw card.
    play = Buff(CONTROLLER, "WW_379t"), _FlintFirearmGiveQuickdraw(CONTROLLER)


class WW_379e:
    """Flint Firearm"""

    # Visual marker buff on the granted Quickdraw card. The repeat is driven
    # by the player-level watcher (WW_379t) keyed on the _flint_marked Python
    # attribute, so this enchant carries no events.


@custom_card
class WW_379t:
    # Player-level watcher: for the rest of the turn, every card the
    # controller plays is checked for the Flint marker; a marked card
    # repeats Flint's battlecry. Works for spells (a card-attached Play
    # listener would miss them — spell enchants are cleared on cast).
    tags = {
        GameTag.CARDNAME: "Flint Firearm",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.TAG_ONE_TURN_EFFECT: True,
    }
    events = Play(CONTROLLER).after(_FlintRepeatIfMarked(Play.CARD))


class WW_421:
    """Kingpin Pud"""

    # <b>Battlecry:</b> Resurrect your Ogre-Gang. Give them <b>Windfury</b>.
    play = _KingpinResurrectOgreGang(CONTROLLER)


class WW_440:
    """Thunderbringer"""

    # <b>Taunt</b> <b>Deathrattle:</b> Summon an Elemental and Beast from
    # your deck.
    deathrattle = (
        Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + ELEMENTAL)),
        Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + BEAST)),
    )
