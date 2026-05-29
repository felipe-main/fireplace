from ..utils import *


##
# Custom actions


class _AnimatronicDestroy(TargetedAction):
    """Forgotten Animatronic — at end of your turn, destroy a random minion
    (either side) whose Attack is strictly less than this minion's Attack."""

    TARGET = ActionArg()

    def do(self, source, target):
        candidates = [
            m
            for m in source.game.board
            if m.type == CardType.MINION
            and m is not source
            and not m.dead
            and m.atk < source.atk
        ]
        if not candidates:
            return
        pick = source.game.random.choice(candidates)
        source.game.cheat_action(source, [Destroy(pick)])


class _CosplayTransform(TargetedAction):
    """Cosplay Contestant — after your opponent plays a minion, transform
    into a copy of it whose stats are set to 3/4."""

    TARGET = ActionArg()
    OTHER = CardArg()

    def do(self, source, target, other):
        if isinstance(other, list):
            other = other[0] if other else None
        if other is None or other.type != CardType.MINION:
            return
        # Morph returns the freshly-created copy that now sits in play.
        new_card = source.controller.card(other.id, source=source)
        results = source.game.cheat_action(source, [Morph(target, new_card)])
        # The morphed-into card is the live entity now; stamp the 3/4 set.
        source.game.cheat_action(source, [Buff(new_card, "TOY_878e")])


class _OrigamiSwap(TargetedAction):
    """Origami swap helper — swap Attack only, Health only, or both stats
    between SELF and the targeted minion, via TOY_894e/895e/896e."""

    TARGET = ActionArg()
    OTHER = CardArg()

    def __init__(self, *args, swap_atk=True, swap_health=True, buff_id=None):
        super().__init__(*args)
        self._swap_atk = swap_atk
        self._swap_health = swap_health
        self._buff_id = buff_id

    def do(self, source, target, other):
        if isinstance(other, list):
            other = other[0] if other else None
        if other is None or other.type != CardType.MINION:
            return
        # Snapshot both minions' stats before stamping either enchant.
        s_atk, s_health = source.atk, source.health
        o_atk, o_health = other.atk, other.health
        buff_s = source.controller.card(self._buff_id, source=source)
        buff_s.source = source
        buff_s._swap_atk = self._swap_atk
        buff_s._swap_health = self._swap_health
        buff_s._xatk = o_atk
        buff_s._xhealth = o_health
        buff_o = source.controller.card(self._buff_id, source=source)
        buff_o.source = source
        buff_o._swap_atk = self._swap_atk
        buff_o._swap_health = self._swap_health
        buff_o._xatk = s_atk
        buff_o._xhealth = s_health
        buff_s.apply(source)
        buff_o.apply(other)
        source.game.manager.targeted_action(self, source, target, other)


class _FloppyHydraShuffle(TargetedAction):
    """Floppy Hydra — shuffle a copy of this into your deck with permanently
    doubled Attack and Health. The doubling snapshots the dying minion's
    current stats, so repeated cycles stack."""

    TARGET = ActionArg()

    def do(self, source, target):
        copy = source.controller.card("TOY_897", source=source)
        buff = source.controller.card("TOY_897e", source=source)
        buff.source = source
        buff._xatk = max(0, source.atk) * 2
        buff._xhealth = max(1, source.health) * 2
        buff.apply(copy)
        source.game.cheat_action(source, [Shuffle(source.controller, copy)])


class _JoymancerCopies(TargetedAction):
    """Joymancer Jepetto — add to hand a copy of every minion you've played
    this game whose printed Attack or Health is 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for c in list(ctrl.cards_played_this_game):
            if c.type != CardType.MINION:
                continue
            data = c.data
            atk = getattr(data, "atk", None)
            health = getattr(data, "health", None)
            if atk == 1 or health == 1:
                source.game.cheat_action(source, [Give(ctrl, c.id)])


##
# Minions


class TOY_820:
    """Forgotten Animatronic"""

    # At the end of your turn, destroy a minion with less Attack than this.
    events = OWN_TURN_END.on(_AnimatronicDestroy(SELF))


class TOY_866:
    """Corridor Sleeper"""

    # Starts Dormant. After 7 minions die, awaken.
    tags = {GameTag.DORMANT: True}
    progress_total = 7
    dormant_events = Death(MINION).on(AddProgress(SELF, Death.ENTITY))
    reward = Awaken(SELF)


class TOY_878:
    """Cosplay Contestant"""

    # After your opponent plays a minion, transform into a 3/4 copy of it.
    events = Play(OPPONENT, MINION).after(_CosplayTransform(SELF, Play.CARD))


class TOY_878e:
    # Cool Costume — Stats set to 3/4.
    atk = lambda self, i: 3
    max_health = lambda self, i: 4


class TOY_891:
    """Workshop Janitor"""

    # Battlecry: If you control a location, draw 2 cards.
    play = (Count(IN_PLAY + FRIENDLY + LOCATION_CARD) >= 1) & Draw(CONTROLLER) * 2


class TOY_893:
    """Nesting Golem"""

    # Deathrattle: Resummon this with -1/-1.
    deathrattle = SummonCustomMinion(
        CONTROLLER, "TOY_893", 4, ATK(SELF) - 1, MAX_HEALTH(SELF) - 1
    )


class TOY_894:
    """Origami Frog"""

    # Rush. Battlecry: Swap Attack with another minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _OrigamiSwap(
        SELF, TARGET, swap_atk=True, swap_health=False, buff_id="TOY_894e"
    )


class TOY_894e:
    # Folding Paper — Swapped stats. Attack-only override.
    atk = lambda self, i: self._xatk if getattr(self, "_swap_atk", True) else i
    max_health = (
        lambda self, i: self._xhealth if getattr(self, "_swap_health", True) else i
    )


class TOY_895:
    """Origami Crane"""

    # Taunt. Battlecry: Swap Health with another minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _OrigamiSwap(
        SELF, TARGET, swap_atk=False, swap_health=True, buff_id="TOY_895e"
    )


class TOY_895e:
    # Crane Paper — Swapped Health.
    atk = lambda self, i: self._xatk if getattr(self, "_swap_atk", True) else i
    max_health = (
        lambda self, i: self._xhealth if getattr(self, "_swap_health", True) else i
    )


class TOY_896:
    """Origami Dragon"""

    # Divine Shield, Lifesteal. Battlecry: Swap stats with another minion.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _OrigamiSwap(
        SELF, TARGET, swap_atk=True, swap_health=True, buff_id="TOY_896e"
    )


class TOY_896e:
    # Frog Paper — Swapped stats.
    atk = lambda self, i: self._xatk if getattr(self, "_swap_atk", True) else i
    max_health = (
        lambda self, i: self._xhealth if getattr(self, "_swap_health", True) else i
    )


class TOY_897:
    """Floppy Hydra"""

    # Deathrattle: Shuffle a copy of this into your deck with permanently
    # doubled Attack and Health.
    deathrattle = _FloppyHydraShuffle(SELF)


@custom_card
class TOY_897e:
    # Floppy Hydra — permanently doubled Attack and Health (snapshot).
    tags = {
        GameTag.CARDNAME: "Doubled",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: self._xatk
    max_health = lambda self, i: self._xhealth


class TOY_943:
    """Rumble Enthusiast"""

    # After you play the left- or right-most card in your hand, deal 1
    # damage to a random enemy.
    events = Play(CONTROLLER, PLAY_OUTCAST).after(Hit(RANDOM_ENEMY_CHARACTER, 1))


class TOY_960:
    """Joymancer Jepetto"""

    # Battlecry: Get copies of every 1-Attack or 1-Health minion you've
    # played this game.
    play = _JoymancerCopies(SELF)


##
# Whizbang's Workshop cards classified under the LEGACY set in the data
# (TOY_100-103). Collectible, so they need scripts.


class TOY_100:
    """Gnomelia, S.A.F.E. Pilot"""

    # Rush. Also damages minions next to whomever this attacks.
    # Deathrattle: Deal 2 damage to all enemies. (Rush is a data tag.)
    events = Attack(SELF).on(CLEAVE)
    deathrattle = Hit(ENEMY_CHARACTERS, 2)


class TOY_101:
    """Night Elf Huntress"""

    # Battlecry: Deal 3 damage to three different enemies. (You pick the targets!)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_NONSELF_TARGET: 0,
    }
    play = (
        Hit(TARGET, 3),
        ChoiceTarget(CONTROLLER, ENEMY_CHARACTERS - TARGET).then(
            Hit(ChoiceTarget.CARD, 3),
            ChoiceTarget(
                CONTROLLER, ENEMY_CHARACTERS - TARGET - ChoiceTarget.CARD
            ).then(Hit(ChoiceTarget.CARD, 3)),
        ),
    )


class TOY_102:
    """Footman"""

    # Taunt. Adjacent minions are Immune while attacking. (Taunt is a data tag.)
    update = Refresh(SELF_ADJACENT, {GameTag.IMMUNE_WHILE_ATTACKING: True})


class TOY_103:
    """Warsong Grunt"""

    # Rush. After this attacks and kills a minion, it may attack again.
    # (Rush is a data tag.)
    events = Attack(SELF, ALL_MINIONS).after(Dead(Attack.DEFENDER) & ExtraAttack(SELF))
