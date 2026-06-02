from ..utils import *


##
# "While in hand, play a Dragon to become …" transform helper
#
# Stonetalon Striker / Ebonscale Scout / Ebyssian all upgrade into a beefier
# Dragon token the first time their controller plays a Dragon while they sit in
# hand. Engine precedent: wonders/hunter.py Imposter cards (Hand.events on a
# trigger -> Morph the in-hand card). We morph into the card's `_dragon_form`
# token; the token's own battlecry/keywords ride along on play.


class _DragonAwaken(TargetedAction):
    """Morph the in-hand source into its Dragon form (per-card `_dragon_form`
    token id). No-op once already transformed or if it has left hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target.zone != Zone.HAND:
            return
        form = getattr(target.data.scripts, "_dragon_form", None)
        if not form:
            return
        source.game.cheat_action(source, [Morph(target, form)])


##
# Minions


class CATA_551:
    """Stonetalon Striker"""

    # Taunt. While in hand, play a Dragon to become a 6/6 Dragon.
    _dragon_form = "CATA_551t"
    tags = {GameTag.TAUNT: True}

    class Hand:
        events = Play(CONTROLLER, DRAGON).on(_DragonAwaken(SELF))


class CATA_551t:
    """Stonetalon Striker"""

    # 6/6 Dragon with Taunt (transformed form).
    tags = {GameTag.TAUNT: True}


class CATA_552:
    """Ebonscale Scout"""

    # Battlecry: Deal damage equal to this minion's Attack.
    # While in hand, play a Dragon to become an 8/8 Dragon.
    _dragon_form = "CATA_552t"
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}

    play = Hit(TARGET, ATK(SELF))

    class Hand:
        events = Play(CONTROLLER, DRAGON).on(_DragonAwaken(SELF))


class CATA_552t:
    """Ebonscale Scout"""

    # 8/8 Dragon. Battlecry: Deal damage equal to this minion's Attack.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, ATK(SELF))


class CATA_553:
    """Ebyssian"""

    # Battlecry: Your Dragons have Rush this game.
    # While in hand, play a Dragon to become a 12/12 Dragon.
    _dragon_form = "CATA_553t"

    play = Buff(CONTROLLER, "CATA_553e")

    class Hand:
        events = Play(CONTROLLER, DRAGON).on(_DragonAwaken(SELF))


class CATA_553t:
    """Ebyssian"""

    # 12/12 Dragon. Battlecry: Your Dragons have Rush this game.
    play = Buff(CONTROLLER, "CATA_553e")


class CATA_553e:
    """Ebyssian's Blessing"""

    # Controller-attached aura: friendly Dragons have Rush for the rest of the
    # game. (Persists — never destroyed.)
    update = Refresh(FRIENDLY_MINIONS + DRAGON, {GameTag.RUSH: True})


class CATA_558:
    """Reinforcement Rallier"""

    # Elusive (Can't be targeted by spells or Hero Powers). Carried in the
    # rendered text only, so apply the tags here.
    # ELUSIVE (consolidated GameTag 1211) means "can't be targeted by spells
    # OR hero powers" — the engine honors it directly in targeting.py. The
    # CATA_558 data omits the keyword entirely, so set it here.
    tags = {GameTag.ELUSIVE: True}


class _TolvirCarver(TargetedAction):
    """Battlecry: Choose a card in your hand; reduce its Cost by (1) each turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        choose_hand_card(
            source,
            lambda s, c: s.game.cheat_action(s, [Buff(c, "CATA_566e")]),
        )


class CATA_566:
    """Tol'vir Carver"""

    # Battlecry: Choose a card in your hand. At the start of your turns, reduce
    # its Cost by (1).
    play = _TolvirCarver(SELF)


class _CarvingTick(TargetedAction):
    """Carving enchant — at the start of each of the controller's turns, deepen
    the held card's cost reduction by 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        for buff in list(target.buffs):
            if buff.id == "CATA_566e":
                buff._carving_reduction = getattr(buff, "_carving_reduction", 0) + 1


class CATA_566e:
    """Carving"""

    # Reduces Cost each turn.
    cost = lambda self, i: i - getattr(self, "_carving_reduction", 0)

    class Hand:
        events = OWN_TURN_BEGIN.on(_CarvingTick(OWNER))


##
# Spells


class _EarthenRoarSecond(TargetedAction):
    """Earthen Roar second pick — if the controller is holding a Dragon, let the
    player pick a second (different) enemy minion to set to 1 Health. Modelled
    with the board-target ENTITY_CHOICE primitive (auto-resolves when only one
    other enemy minion is on the board; no-op when none); the soak's automatic
    chooser picks at random, matching the previous approximation."""

    TARGET = ActionArg()

    def do(self, source, first):
        ctrl = source.controller
        holding_dragon = any(
            c.type == CardType.MINION and Race.DRAGON in c.races
            for c in ctrl.hand
            if c is not source
        )
        if not holding_dragon:
            return
        others = [m for m in ctrl.opponent.field if m is not first]
        choose_card(
            source,
            others,
            lambda s, c: s.game.cheat_action(s, [Buff(c, "CATA_554e")]),
        )


class CATA_554:
    """Earthen Roar"""

    # Set an enemy minion's Health to 1. If you're holding a Dragon, pick
    # another.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }

    play = Buff(TARGET, "CATA_554e"), _EarthenRoarSecond(TARGET)


class CATA_554e:
    """Intimidated"""

    # This minion has 1 Health.
    max_health = SET(1)


class _SylvanasTriumph(TargetedAction):
    """Sylvanas's Triumph — deal 3 damage to a target; if another copy of this
    card has already been played this game, hit ALL enemies for 3 instead."""

    TARGET = ActionArg()

    def do(self, source, target):
        played = [c.id for c in source.controller.cards_played_this_game]
        # The battlecry fires BEFORE Play.do appends this very card to
        # cards_played_this_game, so any count >= 1 here means a *prior* copy
        # was already played this game.
        if played.count("CATA_557") >= 1:
            source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 3)])
        elif target is not None:
            source.game.cheat_action(source, [Hit(target, 3)])


class CATA_557:
    """Sylvanas's Triumph"""

    # Deal 3 damage. If you've played another copy of this, hit all enemies
    # instead.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = _SylvanasTriumph(TARGET)


class _ConfrontReplay(TargetedAction):
    """Confront the Tol'vir — replay each 1-Cost card the controller has played
    this game. Spells are recast (targeting enemies if possible); minions are
    summoned. Fresh copies so the originals in the graveyard are untouched."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        originals = [
            c for c in list(ctrl.cards_played_this_game)
            if (c.data.cost or 0) == 1 and c.id != "CATA_560"
        ]
        for original in originals:
            copy = ctrl.card(original.id, source=source)
            copy.controller = ctrl
            if copy.type == CardType.SPELL:
                source.game.cheat_action(
                    source, [CastSpellTargetsEnemiesIfPossible(copy)]
                )
            elif copy.type == CardType.MINION:
                if len(ctrl.field) >= 7:
                    continue
                source.game.cheat_action(source, [Summon(ctrl, copy)])


class CATA_560:
    """Confront the Tol'vir"""

    # Replay each 1-Cost card you've played this game (targeting enemies if
    # possible).
    play = _ConfrontReplay(SELF)


##
# Shatter — Supply Run (CATA_820)
#
# The engine splits a Shatter card into its two half-tokens on DRAW. The
# collectible parent (CATA_820) never resolves directly — it only needs a valid
# docstring + tags. Implement the two halves.


class CATA_820:
    """Supply Run"""

    # Shatter. Draw 3 minions. Give minions in your hand +2/+2.
    pass


class CATA_820t:
    """Supply Run"""

    # Shattered: Draw 3 minions.
    play = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION)) * 3


class CATA_820t2:
    """Supply Run"""

    # Shattered: Give minions in your hand +2/+2.
    play = Buff(FRIENDLY_HAND + MINION, "CATA_820e")


class CATA_820e:
    """Brick by Brick"""

    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


##
# Colossal — Magmaw (CATA_550)
#
# Colossal limb-summoning is engine-handled: limbs are tokens named
# {parent}t/t2/… carrying COLOSSAL_LIMB=1 (CATA_550t..t6, all in data). The
# parent only needs a docstring; each limb body carries the same deathrattle.


class _MagmawRefill(TargetedAction):
    """Magmaw — "Summon any leftover appendages when there is room." At the
    start of your turn, summon banked appendages (those that didn't fit when
    Magmaw was played, tracked on `_colossal_leftover`) into any empty board
    slots, up to the 7-minion cap."""

    TARGET = ActionArg()

    def do(self, source, target):
        leftover = getattr(source, "_colossal_leftover", None)
        if not leftover:
            return
        while leftover and source.controller.minion_slots > 0:
            limb_id = leftover.pop(0)
            source.game.cheat_action(source, [Summon(source.controller, limb_id)])


class CATA_550:
    """Magmaw"""

    # Colossal +99. Summon any leftover appendages when there is room.
    # The Colossal hook caps limb-summoning at the 7-minion board and banks the
    # rest on `_colossal_leftover`; at the start of each of your turns Magmaw
    # refills empty slots from that bank.
    events = OWN_TURN_BEGIN.on(_MagmawRefill(SELF))


class CATA_550t:
    """Magmaw's Body"""

    # Deathrattle: Give a random friendly minion +2 Attack.
    deathrattle = Buff(RANDOM_FRIENDLY_MINION, "CATA_550e1")


class CATA_550t2(CATA_550t):
    """Magmaw's Body"""


class CATA_550t3(CATA_550t):
    """Magmaw's Body"""


class CATA_550t4(CATA_550t):
    """Magmaw's Body"""


class CATA_550t5(CATA_550t):
    """Magmaw's Body"""


class CATA_550t6(CATA_550t):
    """Magmaw's Body"""


class CATA_550e1:
    """Stampede"""

    # +2 Attack.
    tags = {GameTag.ATK: 2}
