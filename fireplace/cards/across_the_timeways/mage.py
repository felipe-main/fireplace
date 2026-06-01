from ..utils import *


##
# Spells


class TIME_000:
    "Semi-Stable Portal"
    # Rewind Battlecry (spell): Add a random minion to your hand. It costs (3)
    # less. (Rewind keep/rewind choice is engine-handled via GameTag.REWIND.)
    play = Give(CONTROLLER, RandomMinion()).then(Buff(Give.CARD, "TIME_000e"))


@custom_card
class TIME_000e:
    tags = {
        GameTag.CARDNAME: "Semi-Stable Portal Buff",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }
    events = REMOVED_IN_PLAY


# Rewind-timeline helper tokens (engine-offered choice). Effect-less, but the
# Keep/Rewind tokens exist in data so we just declare them with docstrings.
class TIME_000ta:
    "Keep Timeline"


class TIME_000tb:
    "Rewind Timeline"


class TIME_006:
    "Mirror Dimension"
    # Summon a 0/4 minion with Taunt. If you are holding a Dragon, summon another.
    play = (
        Summon(CONTROLLER, "TIME_006t1"),
        HOLDING_DRAGON & Summon(CONTROLLER, "TIME_006t1"),
    )


class TIME_006t1:
    "Mirrored Mage"
    # Vanilla Taunt token.


class _ArcaneBarrage(TargetedAction):
    """Deal 3 damage to the chosen enemy, then 2 damage to up to two OTHER
    distinct random enemy characters."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Hit(target, source.get_damage(3, target))])
        others = [
            c
            for c in (source.controller.opponent.characters)
            if c is not target and not c.dead
        ]
        source.game.random.shuffle(others)
        for c in others[:2]:
            source.game.cheat_action(source, [Hit(c, source.get_damage(2, c))])


class TIME_855:
    "Arcane Barrage"
    # Deal $3 damage to an enemy and $2 damage to two other random ones.
    play = _ArcaneBarrage(TARGET)
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }


_ALTER_TIME_DISCOVER = Discover(
    CONTROLLER, RandomSpell(spell_school=SpellSchool.ARCANE)
).then(Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "TIME_857e")))


class _AlterTime(TargetedAction):
    """Discover two Arcane spells (each costs (2) less). Run as two sequential
    Discovers via re-queue so each opens its own choice in turn — a flat tuple
    of Discovers would all set player.choice at once and only the last would
    survive."""

    TARGET = ActionArg()

    def do(self, source, target):
        for _ in range(2):
            source.game.cheat_action(source, [_ALTER_TIME_DISCOVER])


class TIME_857:
    "Alter Time"
    # Discover two Arcane spells from the past. They cost (2) less.
    play = _AlterTime(CONTROLLER)


@custom_card
class TIME_857e:
    tags = {
        GameTag.CARDNAME: "Alter Time Buff",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }
    events = REMOVED_IN_PLAY


class _Anomalize(TargetedAction):
    """Summon a random 10-Cost and a random 1-Cost minion, then swap (scramble)
    their Attack/Health via the TIME_859e enchant."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        before = set(ctrl.field)
        source.game.cheat_action(
            source,
            [
                Summon(ctrl, RandomMinion(cost=10)),
                Summon(ctrl, RandomMinion(cost=1)),
            ],
        )
        summoned = [m for m in ctrl.field if m not in before]
        if len(summoned) >= 2:
            a, b = summoned[-2], summoned[-1]
            source.game.cheat_action(source, [SwapStateBuff(a, b, "TIME_859e")])


class TIME_859:
    "Anomalize"
    # Summon a random 10 and 1-Cost minion. Scramble their stats.
    play = _Anomalize(CONTROLLER)


class TIME_859e:
    "Anomalized"
    # Attack and Health scrambled — applied by SwapStateBuff, reads runtime
    # _xatk / _xhealth stamped from the other minion's stats.
    atk = lambda self, i: self._xatk
    max_health = lambda self, i: self._xhealth


##
# Minions


class TIME_852:
    "Azure Queen Sindragosa"
    # Fabled: If you control another Dragon, your Arcane spells cost (2) less.
    update = Find(FRIENDLY_MINIONS + DRAGON - SELF) & Refresh(
        FRIENDLY_HAND + SPELL + ARCANE_SPELL, {GameTag.COST: -2}
    )


class _MalygosArcaneEcho(TargetedAction):
    """Azure King Malygos — cast a fresh copy of the Arcane spell the controller
    just played (so it casts twice), aimed at the original target. Guarded
    against recursion so the recast's own OWN_SPELL_PLAY hook doesn't re-fire
    infinitely."""

    TARGET = ActionArg()
    SPELL = ActionArg()
    SPELL_TARGET = ActionArg()

    def do(self, source, target, spell, spell_target):
        if isinstance(spell, list):
            spell = spell[0] if spell else None
        if isinstance(spell_target, list):
            spell_target = spell_target[0] if spell_target else None
        if spell is None:
            return
        ctrl = source.controller
        if getattr(ctrl, "_malygos_recasting", False):
            return
        ctrl._malygos_recasting = True
        try:
            source.game.cheat_action(source, [CastSpell(spell.id, spell_target)])
        finally:
            ctrl._malygos_recasting = False


class TIME_852t1:
    "Azure King Malygos"
    # If you control another Dragon, your Arcane spells cast twice.
    events = Play(CONTROLLER, SPELL + ARCANE_SPELL).after(
        Find(FRIENDLY_MINIONS + DRAGON - SELF)
        & _MalygosArcaneEcho(CONTROLLER, Play.CARD, Play.TARGET)
    )


class _AzureOathstone(TargetedAction):
    """Summon every Dragon the controller has had die this game (now in the
    graveyard, whether it was played or summoned)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        dragons = [
            c.id
            for c in ctrl.graveyard
            if c.type == CardType.MINION and Race.DRAGON in c.races
        ]
        for cid in dragons:
            source.game.cheat_action(source, [Summon(ctrl, cid)])


class TIME_852t3:
    "Azure Oathstone"
    # Summon your Dragons that died this game.
    play = _AzureOathstone(CONTROLLER)


class TIME_856:
    "Algeth'ar Instructor"
    # Spell Damage +2 (vanilla — SPELLPOWER tag carried by data).


class _TemporalConstruct(TargetedAction):
    """Deal 5 damage to an enemy minion. Draw cards equal to the excess damage
    (damage beyond the target's current Health). Snapshot health before the hit
    so overkill is exact even though the target dies mid-resolution."""

    TARGET = ActionArg()

    def do(self, source, target):
        amount = source.get_damage(5, target)
        excess = max(0, amount - target.health)
        source.game.cheat_action(source, [Hit(target, amount)])
        for _ in range(excess):
            source.game.cheat_action(source, [Draw(source.controller)])


class TIME_858:
    "Temporal Construct"
    # Battlecry: Deal 5 damage to an enemy minion. Draw cards equal to the
    # excess damage.
    play = _TemporalConstruct(TARGET)
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }


class _FacelessEnigmaChoice(Choice):
    """Look at 2 random Secrets. The chosen one casts for the controller, the
    other casts for the opponent."""

    def choose(self, card):
        super().choose(card)
        ctrl = self.player
        opp = ctrl.opponent
        for _card in self.cards:
            caster = ctrl if _card == card else opp
            secret = caster.card(_card.id, source=self.source)
            secret.zone = Zone.HAND
            self.source.game.cheat_action(self.source, [CastSpell(secret)])


class _FacelessEnigma(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        picker = RandomSpell(secret=True) * 2
        ids = picker.evaluate(source)
        offered = [ctrl.card(cid, source=source) for cid in ids]
        if len(offered) < 2:
            return
        source.game.queue_actions(source, [_FacelessEnigmaChoice(ctrl, offered)])


class TIME_860:
    "Faceless Enigma"
    # Battlecry: Look at 2 random Secrets. Pick one to cast for yourself. The
    # other casts for your opponent.
    play = _FacelessEnigma(CONTROLLER)


class _TokiGetSpells(TargetedAction):
    """Get 4 random spells from the past, marked (per-Toki group) so that when
    all 4 of a group are played, the controller gets another Timelooper Toki.

    The tracking lives on a persistent CONTROLLER enchant (TIME_861e1) whose
    Play(CONTROLLER, SPELL) listener stays alive even after the marked spells
    leave the hand for the graveyard. A spell enchant could NOT do this — spells
    discard on play, taking their enchants (and listeners) with them."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if not hasattr(ctrl, "_toki_groups"):
            ctrl._toki_groups = {}
        gid = getattr(ctrl, "_toki_next_group", 0)
        ctrl._toki_next_group = gid + 1
        marked = []
        for _ in range(4):
            picker = RandomSpell()
            pick = picker.evaluate(source)
            cid = pick[0] if isinstance(pick, list) else pick
            if not cid:
                continue
            source.game.cheat_action(source, [Give(ctrl, cid)])
            given = ctrl.hand[-1]
            given._toki_group = gid
            marked.append(given)
        ctrl._toki_groups[gid] = len(marked)
        # One persistent listener on the controller drives all groups.
        if not getattr(ctrl, "_toki_watching", False):
            ctrl._toki_watching = True
            source.game.cheat_action(source, [Buff(ctrl, "TIME_861e1")])


class _TokiTick(TargetedAction):
    """A spell was played: if it was one of Toki's marked spells, decrement its
    group counter, and if that group is now exhausted, give another Timelooper
    Toki."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        ctrl = source.controller
        gid = getattr(card, "_toki_group", None)
        groups = getattr(ctrl, "_toki_groups", None)
        if groups is None or gid is None or gid not in groups:
            return
        groups[gid] -= 1
        if groups[gid] <= 0:
            del groups[gid]
            source.game.cheat_action(source, [Give(ctrl, "TIME_861")])


class TIME_861:
    "Timelooper Toki"
    # Battlecry: Get 4 random spells from the past. When you play ALL 4, get
    # another Timelooper Toki.
    play = _TokiGetSpells(CONTROLLER)


class TIME_861e1:
    "Looping Time"
    # Persistent controller enchant (exists in data): watches every spell the
    # controller plays and routes it through _TokiTick (which only acts on
    # Toki-marked spells).
    events = Play(CONTROLLER, SPELL).after(_TokiTick(CONTROLLER, Play.CARD))
