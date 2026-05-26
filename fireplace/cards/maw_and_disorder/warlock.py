from ..utils import *


##
# Spells


class _ArsonAccuse(TargetedAction):
    """Stamp the chosen minion both with an accused-side marker
    (MAW_001e2, silenceable) and arm the hero-side trigger (MAW_001e).
    The hero-side trigger scans for live MAW_001e2 marks at fire time
    — silencing the accused removes the mark and breaks the deathlink."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Accused-side mark.  Silence wipes the enchantment, breaking
        # the chain — the hero-side scan finds no marks for this
        # accused and the destroy skips it.
        source.buff(target, "MAW_001e2")
        if not getattr(ctrl, "_arson_armed", False):
            ctrl._arson_armed = True
            source.buff(ctrl.hero, "MAW_001e")


class _ArsonFire(TargetedAction):
    """Fire on the friendly hero taking damage: destroy every enemy
    minion still carrying the MAW_001e2 mark (= still under accusation).
    Silenced accused minions lost the mark and survive."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        from hearthstone.enums import Zone
        live = []
        for player in source.game.players:
            for m in player.field:
                if m.controller is ctrl:
                    continue  # printed text targets enemy minions only
                if any(b.id == "MAW_001e2" for b in m.buffs):
                    live.append(m)
        if live:
            source.game.cheat_action(source, [Destroy(live)])


class MAW_001:
    """Arson Accusation"""

    # Choose a minion. Destroy it after your hero takes damage.  Pair
    # of enchantments: MAW_001e2 on the accused (silence-removable);
    # MAW_001e on the caster's hero (one per controller).  At fire
    # time the hero-side enchantment scans for live MAW_001e2 marks.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _ArsonAccuse(TARGET)


@custom_card
class MAW_001e:
    tags = {
        GameTag.CARDNAME: "Arson Trial",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = Damage(OWNER).on(_ArsonFire(CONTROLLER))


class MAW_001e2:
    # Accused-side marker.  Empty body — silence wipes it via standard
    # enchantment removal.  The hero-side _ArsonFire scans for this id.
    tags = {GameTag.CARDNAME: "Accused of Arson"}


class _HabeasResurrectOnPick(TargetedAction):
    """Choose-callback for Habeas Corpses: resurrect the chosen
    friendly graveyard minion on the controller's side with Rush + an
    end-of-turn auto-destroy."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards, picked):
        if isinstance(picked, list):
            if not picked:
                return
            picked = picked[0]
        ctrl = source.controller
        source.game.cheat_action(source, [Summon(ctrl, picked.id)])
        for m in ctrl.field:
            if m.id == picked.id and not getattr(m, "_habeas_marked", False):
                m._habeas_marked = True
                source.game.cheat_action(
                    source, [GiveRush(m), Buff(m, "MAW_002e")]
                )
                break


class _HabeasOpenDiscover(TargetedAction):
    """Open a real 3-card Discover over the friendly graveyard's
    minions; the chosen card is resurrected (Rush + end-of-turn)."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType
        pool = [c for c in target.graveyard if c.type == CardType.MINION]
        if not pool:
            return
        n = min(3, len(pool))
        picks = source.game.random.sample(pool, n)
        offered = [target.card(p.id, source=source) for p in picks]
        choice = Choice(target, offered).then(
            _HabeasResurrectOnPick(Choice.PLAYER, Choice.CARDS, Choice.CARD)
        )
        source.game.queue_actions(source, [choice])


class MAW_002:
    """Habeas Corpses"""

    # Discover a friendly minion to resurrect and give it Rush. It dies
    # at the end of turn.  Opens a real 3-card Discover over the
    # friendly graveyard's minions.
    play = _HabeasOpenDiscover(CONTROLLER)


@custom_card
class MAW_002e:
    tags = {
        GameTag.CARDNAME: "Habeas Corpse",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(Destroy(OWNER))


##
# Minions


class _ImpOsterMorphOnPick(TargetedAction):
    """Choose-callback for Imp-oster: morph Imp-oster (stamped on the
    source) into a copy of the chosen friendly Imp."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards, picked):
        if isinstance(picked, list):
            if not picked:
                return
            picked = picked[0]
        # `source` is Imp-oster itself.  Morph it into a copy of the
        # picked card.  No-op if Imp-oster is no longer on the field
        # (somehow died mid-choice).
        from hearthstone.enums import Zone
        if source.zone != Zone.PLAY:
            return
        source.game.cheat_action(source, [Morph(source, picked.id)])


class _ImpOsterOpenChoice(TargetedAction):
    """Open a real Choose over the friendly Imps on the board
    (excluding Imp-oster itself).  No-op if no other Imps."""

    TARGET = ActionArg()

    def do(self, source, target):
        from fireplace.dsl.selector import IMP
        pool = IMP.eval(target.controller.field, source)
        pool = [m for m in pool if m is not target]
        if not pool:
            return
        ctrl = target.controller
        offered = [ctrl.card(m.id, source=source) for m in pool]
        choice = Choice(ctrl, offered).then(
            _ImpOsterMorphOnPick(Choice.PLAYER, Choice.CARDS, Choice.CARD)
        )
        source.game.queue_actions(source, [choice])


class MAW_000:
    """Imp-oster"""

    # Battlecry: Choose a friendly Imp. Transform into a copy of it.
    # Opens a real Choose-One over the friendly Imps on the board.
    play = _ImpOsterOpenChoice(SELF)
