from ..utils import *


##
# "Choose a minion in your hand" support
#
# The engine's play-targets only range over in-play characters, so a hand
# minion cannot be a normal play-target. Model the printed player choice with
# an ENTITY_CHOICE over the friendly hand minions (mirrors Chillin' Vol'jin's
# pick), then run a callback on the chosen minion.

class _HandMinionChoice:
    type = "ENTITY_CHOICE"
    min_count = 1
    max_count = 1

    def __init__(self, source, player, cards, apply):
        self.source = source
        self.player = player
        self.cards = list(cards)
        self._apply = apply

    def choose(self, card):
        if card not in self.cards:
            raise ValueError("not a valid pick")
        self.player.choice = None
        self._apply(self.source, card)


def _choose_hand_minion(source, apply):
    """Let the controller choose a friendly hand minion, then run
    apply(source, chosen). Auto-resolves when there is exactly one; no-op when
    there are none."""
    ctrl = source.controller
    minions = [c for c in ctrl.hand if c.type == CardType.MINION]
    if not minions:
        return
    if len(minions) == 1:
        apply(source, minions[0])
        return
    ctrl.choice = _HandMinionChoice(source, ctrl, minions, apply)


class _CupOMuscleBuff(TargetedAction):
    """Cup o' Muscle — give a CHOSEN minion in your hand +2/+1."""

    TARGET = ActionArg()

    def do(self, source, target):
        _choose_hand_minion(
            source,
            lambda s, m: s.game.cheat_action(s, [Buff(m, "VAC_338e")]),
        )


##
# Minions


class VAC_337:
    """Line Cook"""

    # [x]<b>Tradeable</b> <b>Taunt</b>. When you draw this, get a copy of it.
    # Tradeable + Taunt live in data. The draw trigger gives an exact copy.
    draw = Give(CONTROLLER, ExactCopy(SELF))


class _SummonCheese(TargetedAction):
    """Muensterosity — at end of turn summon a Cheese Elemental whose stats
    *equal* Muensterosity's current Attack and Health. The token's printed
    stats (1/1) are a placeholder; we summon it then set its base atk /
    max_health to match the source, so the result is exactly N/N (not 1+N)."""

    TARGET = ActionArg()

    def do(self, source, target):
        # target is Muensterosity (SELF). Snapshot its live stats, summon the
        # token onto the same controller's board, then set base stats to match.
        atk = target.atk
        health = target.health
        cheese = target.controller.summon("VAC_339t")
        cheese.atk = atk
        cheese.max_health = health
        cheese.damage = 0


class VAC_339:
    """Muensterosity"""

    # [x]<b>Taunt</b>. At the end of your turn, summon an Elemental with stats
    # equal to this minion's.
    # Taunt lives in data.
    events = OWN_TURN_END.on(_SummonCheese(SELF))


class VAC_339t:
    """Cheese Elemental"""


class VAC_340:
    """Hamm, the Hungry"""

    # [x]<b>Druid Tourist</b> <b>Taunt</b>. At the end of your turn, eat a
    # minion in the enemy's deck to gain +2/+2.
    # Tourist is deckbuilding-only (no in-game trigger). Taunt lives in data.
    # At end of turn, if the enemy deck has a minion, remove one and buff +2/+2.
    events = OWN_TURN_END.on(
        Find(ENEMY_DECK + MINION)
        & (
            Discard(RANDOM(ENEMY_DECK + MINION)),
            Buff(SELF, "VAC_340e"),
        )
    )


VAC_340e = buff(+2, +2)


class VAC_341:
    """Undercooked Calamari"""

    # [x]<b>Battlecry:</b> Destroy an enemy minion with Attack less than or
    # equal to this minion's.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_MAX_ATTACK: 4,
    }
    # The data card carries REQ_TARGET_MAX_ATTACK = (this minion's printed
    # Attack, 4). Destroy is gated again at resolution on the live Attack so a
    # buffed Calamari can also clear a bigger minion.
    play = (ATK(TARGET) <= ATK(SELF)) & Destroy(TARGET)


class VAC_527:
    """Draconic Delicacy"""

    # <b>Rush</b>, <b>Elusive</b> Can only take 1 damage at a time.
    # Rush + Elusive (CANT_BE_TARGETED_BY_SPELLS) live in data. The
    # "1 damage at a time" cap is the incoming_damage_max engine primitive.
    update = Refresh(SELF, {enums.INCOMING_DAMAGE_MAX: 1})


##
# Weapons


class VAC_525:
    """The Ryecleaver"""

    # [x]<b>Battlecry and Deathrattle:</b> Get a Slice of Bread.
    # (Get 2 to Sandwich any minions in between!)
    play = Give(CONTROLLER, "VAC_525t1")
    deathrattle = Give(CONTROLLER, "VAC_525t1")


class VAC_525e:
    """Sandwich Tracker"""

    # Engine-internal tracker enchant (lives in data). No behavior of its own;
    # _SliceOfBread reads the board range between the two slices directly.


class _SandwichSlices(TargetedAction):
    """The Ryecleaver — playing a Slice of Bread.

    The printed combo: the first Slice "marks" the board; playing a second
    Slice stuffs every minion summoned *between* the two slices into a
    2-Cost Minion Sandwich. We model the marker with a per-player attribute
    `_ryecleaver_slice` snapshotting the friendly board size when the first
    Slice resolves. When the second Slice resolves, every friendly minion at
    a board index at/after the snapshot is removed and packed into a fresh
    Minion Sandwich token (VAC_525t2) given to hand; its stored ids are read
    back on play to re-summon them."""

    PLAYER = ActionArg()

    def do(self, source, player):
        marker = getattr(player, "_ryecleaver_slice", None)
        if marker is None:
            # First slice: snapshot current board width.
            player._ryecleaver_slice = len(player.field)
            return
        # Second slice: capture minions summoned since the marker.
        start = min(marker, len(player.field))
        stuffed = list(player.field[start:])
        player._ryecleaver_slice = None
        sandwich = player.card("VAC_525t2", source=source)
        sandwich._sandwich_ids = [m.id for m in stuffed]
        for m in stuffed:
            m.zone = Zone.REMOVEDFROMGAME
        sandwich.zone = Zone.HAND


class VAC_525t1:
    """Slice of Bread"""

    # Get another Slice of Bread to stuff all minions in between into a
    # 2-Cost Sandwich!
    play = _SandwichSlices(CONTROLLER)


class _SummonSandwich(TargetedAction):
    """Minion Sandwich — re-summon every minion stuffed into this Sandwich."""

    PLAYER = ActionArg()

    def do(self, source, player):
        ids = getattr(source, "_sandwich_ids", [])
        for cid in ids:
            source.game.cheat_action(source, [Summon(player, cid)])


class VAC_525t2:
    """Minion Sandwich"""

    # [x]Summon the minions stuffed in this Sandwich.
    play = _SummonSandwich(CONTROLLER)


##
# Spells


class VAC_338:
    """Cup o' Muscle"""

    # [x]Give a minion in your hand +2/+1. (3 Drinks left!)
    # Drink chain: give the next copy first, then open the hand-minion choice
    # (so the choice is the last thing pending when the play resolves).
    play = (
        Give(CONTROLLER, "VAC_338t"),
        _CupOMuscleBuff(SELF),
    )


VAC_338e = buff(+2, +1)


class VAC_338t:
    """Cup o' Muscle"""

    # [x]Give a minion in your hand +2/+1. (2 Drinks left!)
    play = (
        Give(CONTROLLER, "VAC_338t2"),
        _CupOMuscleBuff(SELF),
    )


class VAC_338t2:
    """Cup o' Muscle"""

    # [x]Give a minion in your hand +2/+1. (Last Drink!)
    play = _CupOMuscleBuff(SELF)


class _CharExcessBuff(TargetedAction):
    """Char — deal 7 to the target minion; the *excess* damage (amount beyond
    the target's current Health) becomes +X/+X on a random minion in your
    hand. Spell Damage scales the 7 via get_damage. We snapshot the target's
    health before the hit so the overflow is exact even though the target dies
    mid-resolution."""

    TARGET = ActionArg()

    def do(self, source, target):
        amount = source.get_damage(7, target)
        excess = max(0, amount - target.health)
        source.game.cheat_action(source, [Hit(target, amount)])
        if excess <= 0:
            return
        # Player chooses which hand minion gets +excess/+excess.
        _choose_hand_minion(
            source,
            lambda s, m: s.game.cheat_action(
                s, [Buff(m, "VAC_526e", atk=excess, max_health=excess)]
            ),
        )


class VAC_526:
    """Char"""

    # Deal $7 damage to a minion. Give a minion in your hand stats equal to the
    # excess damage.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _CharExcessBuff(TARGET)


class VAC_526e:
    """Toasty"""

    # Increased Stats — runtime-stamped (atk / max_health supplied at Buff time).


class _DrawDistinctTypes(TargetedAction):
    """All You Can Eat — draw three minions of *different* minion types from
    your deck. We greedily pick minions whose race-set is disjoint from the
    types already chosen, so each draw introduces a new type. Falls back to
    fewer draws if the deck can't supply three distinct-typed minions."""

    PLAYER = ActionArg()

    def do(self, source, player):
        deck_minions = [c for c in player.deck if c.type == CardType.MINION]
        chosen = []
        used_types = set()
        # Shuffle for randomness among equally-valid candidates.
        candidates = list(deck_minions)
        source.game.random.shuffle(candidates)
        for card in candidates:
            if len(chosen) >= 3:
                break
            races = set(getattr(card, "races", []) or [])
            # A minion with no race can still count as a distinct "type".
            key = frozenset(races) if races else frozenset()
            if races and races & used_types:
                continue
            chosen.append(card)
            used_types |= races if races else {None}
        for card in chosen:
            source.game.cheat_action(source, [ForceDraw(card)])


class VAC_528:
    """All You Can Eat"""

    # Draw three minions of different minion types.
    play = _DrawDistinctTypes(CONTROLLER)


class VAC_533:
    """Food Fight"""

    # Summon a 0/6 Entrée for your opponent. When it dies, summon a minion
    # from your deck.
    play = Summon(OPPONENT, "VAC_533t")


class VAC_533t:
    """Entrée"""

    # <b>Deathrattle:</b> Your opponent summons a minion from their deck.
    # "Your opponent" (from the Entrée's controller's view) is the original
    # caster of Food Fight, i.e. this token's controller's opponent.
    deathrattle = Summon(OPPONENT, RANDOM(ENEMY_DECK + MINION))
