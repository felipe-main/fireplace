from ..utils import *

from hearthstone.enums import Zone, Race as _Race, Rarity as _Rarity, SpellSchool

from .utils import _TrailingProgressCardtextMixin, _MetrognomeCardtextMixin


##
# Custom actions / helpers


class _ETCBandManagerDiscover(TargetedAction):
    """E.T.C., Band Manager Battlecry — Discover one of the controller's
    stamped sideboard (3 cards) when populated by deck-time stamping
    (see PlayableCard.__init__ in fireplace/card.py). When the sideboard
    is empty (no deck-time stamp, e.g. test games or non-drafted games),
    fall back to 3 random Neutral collectible minions for THIS play
    only — do NOT write the random pool back to `_etc_sideboard`, so
    repeat plays / future games stay in the uninitialized state."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        sideboard = source._etc_sideboard
        if not sideboard:
            # On-demand fallback: 3 random Neutral collectibles. Do NOT
            # persist back onto source._etc_sideboard.
            from .. import db as _db
            pool = [
                cid for cid, c in _db.items()
                if c.collectible
                and c.card_class == CardClass.NEUTRAL
                and c.type == CardType.MINION
                and cid != source.id
            ]
            if not pool:
                return
            sideboard = source.game.random.sample(pool, min(3, len(pool)))
        # Materialise the 3 cards on the controller's side.
        cards = [ctrl.card(cid) for cid in sideboard]
        source.game.queue_actions(source, [GenericChoice(ctrl, cards)])


class _GhostWriterFinaleDiscover(TargetedAction):
    """Ghost Writer Finale — open a second Discover-a-spell after the
    initial battlecry resolves."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not source.play_finale:
            return
        ctrl = source.controller
        action = Discover(ctrl, RandomSpell()).then(
            Give(ctrl, Discover.CARD)
        )
        source.game.queue_actions(source, [action])


class _StaticWaveformTick(TargetedAction):
    """Static Waveform — at the start of EACH turn, lose 1 Attack or
    Health (randomly). Approximate via two enchants: ETC_089e (-1 atk)
    and ETC_089e2 (-1 health)."""

    TARGET = ActionArg()

    def do(self, source, target):
        pick = source.game.random.choice(["ETC_089e", "ETC_089e2"])
        source.game.cheat_action(source, [Buff(source, pick)])


class _InstrumentCaseDeathrattle(TargetedAction):
    """Instrument Case Deathrattle — add a random weapon to the
    controller's hand (i.e. the player who controls the Case, which is
    the opponent of the Worgen Roadie player)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        picker = RandomWeapon()
        cid = picker.evaluate(source)
        if not cid:
            return
        source.game.cheat_action(source, [Give(ctrl, cid)])


class _CowbellSoloistHit(TargetedAction):
    """Cowbell Soloist — if you control no other minions, deal 2 damage
    (to the target supplied at play time). SELF is in PLAY at battlecry
    time so we exclude it from the "no other minions" check."""

    TARGET = ActionArg()

    def do(self, source, target):
        others = [m for m in source.controller.field if m is not source]
        if others:
            return
        source.game.cheat_action(source, [Hit(target, 2)])


class _AirGuitaristBuff(TargetedAction):
    """Air Guitarist — give your weapon +1 Durability."""

    TARGET = ActionArg()

    def do(self, source, target):
        weapon = source.controller.weapon
        if weapon is None:
            return
        source.game.cheat_action(
            source, [Buff(weapon, "ETC_102e")]
        )


class _HipsterDiscover(TargetedAction):
    """Hipster — Discover a spell from your opponent's class that isn't
    in their deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = target.opponent
        # Also exclude what's in the opponent's hand — the printed text
        # ("isn't in their deck") in modern HS reads as "not currently
        # in the opponent's library" which includes the hand.
        held_ids = {c.id for c in opp.deck} | {c.id for c in opp.hand}
        opp_class = opp.hero.card_class
        from .. import db as _db
        pool = [
            cid for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.SPELL
            and c.card_class == opp_class
            and cid not in held_ids
        ]
        if not pool:
            # Printed text exclusion is strict — no widening fallback.
            return
        picks = source.game.random.sample(pool, min(3, len(pool)))
        cards = [target.card(cid) for cid in picks]
        source.game.queue_actions(source, [GenericChoice(target, cards)])


class _StereoTotemBuff(TargetedAction):
    """Stereo Totem — at end of turn, give a random minion in your hand
    +2/+2."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        minions = [c for c in ctrl.hand if c.type == CardType.MINION]
        if not minions:
            return
        pick = source.game.random.choice(minions)
        source.game.cheat_action(source, [Buff(pick, "ETC_105e")])


class _FrequencyOscillatorBuff(TargetedAction):
    """Frequency Oscillator — the next Mech you play costs (1) less.
    Implemented via an aura stamp on the controller."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._next_mech_cost_reduction = (
            getattr(target, "_next_mech_cost_reduction", 0) + 1
        )


class _RowdyFanBuff(TargetedAction):
    """Rowdy/Obsessive/Annoying Fan — target a minion and bind a
    while-alive effect to it. Implemented as a per-instance buff
    referencing the fan; when the fan dies, the buff is removed via
    Death(fan) listener on the buff (REMOVED_IN_PLAY-style)."""

    TARGET = ActionArg()
    BUFF_ID = ActionArg()

    def do(self, source, target, buff_id):
        if isinstance(buff_id, list):
            buff_id = buff_id[0] if buff_id else None
        source.game.cheat_action(source, [Buff(target, buff_id)])
        # Stash on the fan a back-pointer so Death(fan) can strip it.
        source._fan_buffed_target = target
        source._fan_buff_id = buff_id


class _StripFanBuff(TargetedAction):
    """When a fan minion dies, strip the matching buff from the buffed
    target."""

    TARGET = ActionArg()

    def do(self, source, target):
        victim = getattr(source, "_fan_buffed_target", None)
        buff_id = getattr(source, "_fan_buff_id", None)
        if victim is None or buff_id is None:
            return
        for b in list(victim.buffs):
            if b.id == buff_id:
                b.destroy()


class _AcousticCoverFinish(TargetedAction):
    """Cover Artist — once a discover pick has been made, morph SELF
    into that minion and then re-stamp 3/3 stats by setting the
    morphed entity's atk / max_health to 3 (the printed text forces
    3/3 regardless of the source minion's printed stats)."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, list):
            card = card[0] if card else None
        if card is None:
            return
        cid = card.id if hasattr(card, "id") else card
        # Morph the original Cover Artist body into the chosen minion.
        source.game.cheat_action(source, [Morph(target, cid)])
        # After Morph, `target` retains its identity but `.id` switches
        # to the morph target. Read the post-morph entity off the field.
        morphed = None
        for m in target.controller.field:
            if m is target or m.id == cid:
                morphed = m
                break
        if morphed is None:
            return
        # Stamp the printed 3/3 line by overwriting the base stats. We
        # apply a 3/3-set enchant: clamp atk & max_health to exactly 3.
        delta_atk = 3 - (morphed.atk or 0)
        delta_hp = 3 - (morphed.max_health or 0)
        if delta_atk != 0 or delta_hp != 0:
            source.game.cheat_action(
                source,
                [Buff(morphed, "ETC_110e", atk=delta_atk, max_health=delta_hp)],
            )


class _AcousticCoverMorph(TargetedAction):
    """Cover Artist — Battlecry: Discover a 3/3 copy of a minion. Opens
    a Discover over 3 random minions (cost-agnostic — printed text says
    "a minion", no cost restriction), morphs SELF into the picked card,
    then forces stats to 3/3."""

    TARGET = ActionArg()

    def do(self, source, target):
        picker = RandomMinion()
        source.game.cheat_action(
            source,
            [
                Discover(source.controller, picker).then(
                    _AcousticCoverFinish(target, Discover.CARD)
                ),
            ],
        )


class _CrowdSurferReborn(TargetedAction):
    """Crowd Surfer — give other friendly minions Reborn. (Note: this
    Festival neutral *minion* with the giant-reborn effect is ETC_104?
    No — ETC_104 is actually 'Crowd Surfer' the 1/1 with the chained
    deathrattle. We are scripting the 1/1 dr-chain version below; this
    helper is unused. Kept for future re-use.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for m in list(ctrl.field):
            if m is source:
                continue
            source.game.cheat_action(source, [GiveReborn(m)])


class _FizzleSnapshotStamp(TargetedAction):
    """Photographer Fizzle — snapshot the current hand. Stores
    ExactCopy entities of each card so atk/hp/cost-mod state is
    preserved through the shuffle-and-redraw cycle. The snapshot
    token (ETC_113t) is then shuffled into the controller's deck."""

    TARGET = ActionArg()

    def do(self, source, target):
        from ...dsl.copy import ExactCopy
        ctrl = source.controller
        snapshot = []
        for c in list(ctrl.hand):
            if c is source:
                continue
            try:
                copy = ExactCopy(c).copy(source, c)
                copy.controller = ctrl
                snapshot.append(copy)
            except Exception:
                # Fall back to id-only if ExactCopy doesn't apply (rare
                # for non-playable hand entities).
                snapshot.append(c.id)
        token = ctrl.card("ETC_113t")
        token._fizzle_snapshot = snapshot
        token.zone = Zone.DECK


class _FizzleSnapshotResolve(TargetedAction):
    """Fizzle's Snapshot — add the stamped cards back to the
    controller's hand. Entries that are Card entities (with preserved
    buffs/cost mods) are moved straight to HAND; legacy id-only
    entries fall back to Give(id)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        snapshot = getattr(source, "_fizzle_snapshot", None) or []
        for entry in snapshot:
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            if isinstance(entry, str):
                source.game.cheat_action(source, [Give(ctrl, entry)])
            else:
                entry.controller = ctrl
                entry.zone = Zone.HAND


class _FreebirdBuff(TargetedAction):
    """Freebird — Battlecry: Gain +1/+1 for each other Freebird you've
    played this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        prior = sum(
            1
            for c in ctrl.cards_played_this_game
            if c.id == "ETC_336" and c is not source
        )
        if prior <= 0:
            return
        source.game.cheat_action(
            source,
            [Buff(source, "ETC_336e", atk=prior, max_health=prior)],
        )


class _PartyAnimalBuff(TargetedAction):
    """Party Animal — give +1/+1 to a minion of each minion type in your
    hand (deterministic walk picks the first card of each new race seen)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen = set()
        chosen = []
        for c in list(ctrl.hand):
            if c.type != CardType.MINION or c is source:
                continue
            for race in getattr(c, "races", []):
                if race in seen or race == _Race.INVALID:
                    continue
                seen.add(race)
                chosen.append(c)
                break
        for c in chosen:
            source.game.cheat_action(source, [Buff(c, "ETC_350e")])


class _OneAmalgamBonus(TargetedAction):
    """The One-Amalgam Band — gain a random bonus effect for each minion
    type you've played this game. Approximation: stack +1/+1 buffs."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        seen = set()
        for c in ctrl.cards_played_this_game:
            if c.type != CardType.MINION:
                continue
            for race in getattr(c, "races", []):
                if race != _Race.INVALID:
                    seen.add(int(race))
        n = len(seen)
        if n <= 0:
            return
        source.game.cheat_action(
            source,
            [Buff(source, "ETC_409e", atk=n, max_health=n)],
        )


class _MetrognomeTick(TargetedAction):
    """Metrognome — after you play an N-cost card, draw an (N+1)-cost
    card; bump N each time. Stamp the counter on the minion itself
    (lives only while in play)."""

    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        # ActionArg wraps singletons in a list — unwrap.
        if isinstance(card, list):
            if not card:
                return
            card = card[0]
        n = getattr(source, "_metrognome_n", 0)
        if card.cost == n:
            # Draw any card with cost (n+1) from the deck.
            ctrl = source.controller
            pool = [c for c in list(ctrl.deck) if c.cost == n + 1]
            if pool:
                pick = source.game.random.choice(pool)
                if len(ctrl.hand) < ctrl.max_hand_size:
                    pick.zone = Zone.HAND
                else:
                    pick.discard()
            source._metrognome_n = n + 1


class _MishMashMosher(TargetedAction):
    """Mish-Mash Mosher — after this attacks, gain +1 Attack and attack
    a random enemy minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        # Refuse re-entry to avoid infinite chain.
        if getattr(source, "_mishmash_attacking", False):
            return
        if source.zone != Zone.PLAY:
            return
        source.game.cheat_action(source, [Buff(source, "ETC_419e")])
        enemies = [m for m in source.controller.opponent.field if m is not None]
        if not enemies:
            return
        victim = source.game.random.choice(enemies)
        source._mishmash_attacking = True
        try:
            source.game.cheat_action(source, [Attack(source, victim)])
        finally:
            source._mishmash_attacking = False


class _OutfitTailorBuff(TargetedAction):
    """Outfit Tailor — give a friendly minion +(self.atk)/+(self.health)."""

    TARGET = ActionArg()

    def do(self, source, target):
        atk = source.atk
        health = source.health
        source.game.cheat_action(
            source,
            [Buff(target, "ETC_420e", atk=atk, max_health=health)],
        )


class _PozzikBattlecry(TargetedAction):
    """Pozzik — Battlecry: Add two 3/3 Audio Bots to your opponent's
    hand. Deathrattle: Summon them for yourself."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        for _ in range(2):
            source.game.cheat_action(source, [Give(opp, "ETC_425t")])


class _PozzikDeathrattle(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(2):
            source.game.cheat_action(source, [Summon(ctrl, "ETC_425t")])


class _PyrotechnicianAddFireSpell(TargetedAction):
    """Pyrotechnician — after a spell is cast, add a random Fire spell
    to controller's hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db
        ctrl = source.controller
        pool = [
            cid for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.SPELL
            and getattr(c, "spell_school", None) == SpellSchool.FIRE
        ]
        if not pool:
            return
        cid = source.game.random.choice(pool)
        if len(ctrl.hand) >= ctrl.max_hand_size:
            return
        source.game.cheat_action(source, [Give(ctrl, cid)])


class _TonySwap(TargetedAction):
    """Tony, King of Piracy — Battlecry: Swap both decks. Hands the
    existing card entities across (controllers re-pointed) so in-deck
    enchants / per-card state survive the swap. Uses the engine's
    SwapDecks GameAction primitive."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [SwapDecks()])


class _FestivalSecurityForceAttack(TargetedAction):
    """Festival Security Finale — make every enemy minion attack SELF."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not source.play_finale:
            return
        for m in list(source.controller.opponent.field):
            if m.zone != Zone.PLAY:
                continue
            if source.zone != Zone.PLAY or getattr(source, "dead", False):
                break
            source.game.cheat_action(source, [Attack(m, source)])


class _CandleraiserAdjDS(TargetedAction):
    """Candleraiser Finale — give adjacent minions Divine Shield."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not source.play_finale:
            return
        field = source.controller.field
        if source not in field:
            return
        idx = field.index(source)
        for i in (idx - 1, idx + 1):
            if 0 <= i < len(field):
                source.game.cheat_action(source, [GiveDivineShield(field[i])])


class _RollingStoneCheck(TargetedAction):
    """Rolling Stone — if the last card you played costs (1), gain +1/+1."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # The played card sequence already includes SELF (Rolling Stone),
        # so look at the second-to-last entry.
        played = [c for c in ctrl.cards_played_this_game if c is not source]
        if not played:
            return
        last = played[-1]
        if max(0, last.cost) != 1:
            return
        source.game.cheat_action(
            source,
            [Buff(source, "ETC_742e", atk=1, max_health=1)],
        )


class _MerchSellerPutSpellOnTop(TargetedAction):
    """Merch Seller — at end of your turn, put a random spell on top of
    your opponent's deck. We use a fresh random collectible spell card."""

    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        picker = RandomSpell()
        cid = picker.evaluate(source)
        # RandomCardPicker.evaluate returns a list of card ids.
        if isinstance(cid, list):
            if not cid:
                return
            cid = cid[0]
        if not cid:
            return
        card = opp.card(cid)
        card.zone = Zone.DECK
        # Move to top of deck — fireplace's draw pulls from the end, so
        # appending puts it on top.
        if card in opp.deck:
            opp.deck.remove(card)
        opp.deck.append(card)


class _UnpopularHasBeenSummon(TargetedAction):
    """Unpopular Has-Been Deathrattle — summon a random 5-cost minion
    "from the past" (i.e. Wild-rotated cards). Filters to collectible
    5-cost minions whose card set is NOT in the modern Standard
    rotation. The Standard set list is read from `is_standard` on the
    data card so the pool tracks future-patch rotations automatically."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db
        pool = [
            cid for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.MINION
            and (c.cost or 0) == 5
            and not getattr(c, "is_standard", False)
        ]
        if not pool:
            # Fallback: any 5-cost collectible (avoids no-op if the
            # data parser doesn't carry is_standard on this patch).
            pool = [
                cid for cid, c in _db.items()
                if c.collectible
                and c.type == CardType.MINION
                and (c.cost or 0) == 5
            ]
        if not pool:
            return
        cid = source.game.random.choice(pool)
        source.game.cheat_action(source, [Summon(source.controller, cid)])


class _BoomWrenchDraw(TargetedAction):
    """Boom Wrench — whenever you summon a Mech, draw a card."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(source, [Draw(source.controller)])


class _SoundwaveTrainerCopy(TargetedAction):
    """Soundwave Trainer — get a copy of the highest-Cost minion in
    your hand. (Not part of the printed dump but kept as a private
    helper for ETC_096 if it appears.)"""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        minions = [c for c in ctrl.hand if c.type == CardType.MINION and c is not source]
        if not minions:
            return
        best = max(minions, key=lambda c: c.cost)
        if len(ctrl.hand) >= ctrl.max_hand_size:
            return
        source.game.cheat_action(source, [Give(ctrl, ExactCopy(best))])


##
# Minions


# While building your deck, assemble a band of 3 cards.
# Battlecry: Discover one!
class ETC_080:
    """E.T.C., Band Manager"""

    play = _ETCBandManagerDiscover(SELF)


# Taunt. Deathrattle: Deal 3 damage to all enemy minions.
class ETC_086:
    """Amplified Elekk"""

    deathrattle = Hit(ENEMY_MINIONS, 3)


# Battlecry: Set your maximum Mana and hand size to 11.
class _SetMaxManaAndHand(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        target.max_resources = 11
        target.max_mana = max(target.max_mana, 11)
        target.max_hand_size = 11


class ETC_087:
    """Audio Amplifier"""

    play = _SetMaxManaAndHand(CONTROLLER)


# Battlecry: Discover a spell. Finale: Discover another.
class ETC_088:
    """Ghost Writer"""

    # First Discover; once the chosen card is given, a Finale-gated second
    # Discover queues. Both branches chained via .then() so the second
    # discover only opens *after* the first choice resolves.
    # Two nested .then() steps so the second Discover queues *after* the
    # first GenericChoice resolves; otherwise both choices fight for the
    # single player.choice slot (only the last one survives — see CLAUDE.md
    # "Choice sequencing").
    play = Discover(CONTROLLER, RandomSpell()).then(
        Give(CONTROLLER, Discover.CARD).then(
            _GhostWriterFinaleDiscover(SELF),
        ),
    )


# At the start of EACH turn, lose 1 Attack or Health (chosen randomly).
class ETC_089:
    """Static Waveform"""

    events = TURN_BEGIN.on(_StaticWaveformTick(SELF))


# Battlecry: Summon a 0/3 Instrument Case for your opponent.
class ETC_098:
    """Worgen Roadie"""

    play = Summon(OPPONENT, "ETC_098t")


class ETC_098t:
    """Instrument Case"""

    deathrattle = _InstrumentCaseDeathrattle(SELF)


# Tradeable. Finale: Destroy an enemy minion.
class ETC_099:
    """Concert Promo-Drake"""

    play = FINALE & Destroy(RANDOM(ENEMY_MINIONS))


# Battlecry: If you control no other minions, deal 2 damage.
class ETC_101:
    """Cowbell Soloist"""

    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _CowbellSoloistHit(TARGET)


# Battlecry: Give your weapon +1 Durability.
class ETC_102:
    """Air Guitarist"""

    play = _AirGuitaristBuff(SELF)


# Battlecry: Discover a spell from your opponent's class that isn't in their deck.
class ETC_103:
    """Hipster"""

    play = _HipsterDiscover(CONTROLLER)


# Deathrattle: Give ANY other minion +1/+1 and this Deathrattle.
class _CrowdSurferChain(TargetedAction):
    """Pick a random other minion (any side), give it +1/+1 and append
    THIS deathrattle as an additional_deathrattle so the chain keeps
    going when the recipient dies."""

    TARGET = ActionArg()

    def do(self, source, target):
        candidates = [
            m for m in source.game.player1.field + source.game.player2.field
            if m is not source
        ]
        if not candidates:
            return
        pick = source.game.random.choice(candidates)
        source.game.cheat_action(source, [Buff(pick, "ETC_104e")])
        # Append this same chained action as an additional_deathrattle
        # on the recipient (so the chain propagates on next death).
        pick.additional_deathrattles.append((_CrowdSurferChain(SELF),))
        if not pick.has_deathrattle:
            pick.has_deathrattle = True


class ETC_104:
    """Crowd Surfer"""

    deathrattle = _CrowdSurferChain(SELF)


class ETC_104e:
    """Crowd Surfing"""

    # In-data enchant — stat tags (+1/+1) aren't parsed; declare here.
    # The chained deathrattle behaviour is wired via
    # _CrowdSurferChain.additional_deathrattles, not via this enchant.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


# At the end of your turn, give a random minion in your hand +2/+2.
class ETC_105:
    """Stereo Totem"""

    events = OWN_TURN_END.on(_StereoTotemBuff(SELF))


# Battlecry: The next Mech you play costs (1) less.
class ETC_106:
    """Frequency Oscillator"""

    play = _FrequencyOscillatorBuff(CONTROLLER)


# Battlecry: Choose a minion. It has +4 Attack while this is alive.
class ETC_107:
    """Rowdy Fan"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _RowdyFanBuff(TARGET, "ETC_107e")
    events = Death(SELF).on(_StripFanBuff(SELF))


# Battlecry: Choose a minion. It has Stealth while this is alive.
class ETC_108:
    """Obsessive Fan"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _RowdyFanBuff(TARGET, "ETC_108e")
    events = Death(SELF).on(_StripFanBuff(SELF))


# Battlecry: Choose a minion. It can't attack while this is alive.
class ETC_109:
    """Annoying Fan"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = _RowdyFanBuff(TARGET, "ETC_109e")
    events = Death(SELF).on(_StripFanBuff(SELF))


# Battlecry: Transform into a 3/3 copy of a minion.
class ETC_110:
    """Cover Artist"""

    play = _AcousticCoverMorph(SELF)


# At the end of your turn, put a random spell on top of your opponent's deck.
class ETC_111:
    """Merch Seller"""

    events = OWN_TURN_END.on(_MerchSellerPutSpellOnTop(SELF))


# Battlecry: Take a Snapshot of your current hand and shuffle it into your deck.
class ETC_113:
    """Photographer Fizzle"""

    play = _FizzleSnapshotStamp(SELF)


class ETC_113t:
    """Fizzle's Snapshot"""

    play = _FizzleSnapshotResolve(SELF)


# Rush. Finale: Gain Lifesteal.
class ETC_325:
    """Audio Medic"""

    play = FINALE & GiveLifesteal(SELF)


# Battlecry: Discover a Legendary minion.
class ETC_326:
    """Paparazzi"""

    play = DISCOVER(RandomMinion(rarity=_Rarity.LEGENDARY))


# Charge. Battlecry: Gain +1/+1 for each other Freebird you've played this game.
class ETC_336(_TrailingProgressCardtextMixin):
    """Freebird"""

    play = _FreebirdBuff(SELF)

    def cardtext_entity_0(self):
        ctrl = getattr(self, "controller", None)
        if ctrl is None:
            return "0"
        return str(sum(
            1 for c in ctrl.cards_played_this_game
            if c.id == "ETC_336" and c is not self
        ))

    tags = {
        **_TrailingProgressCardtextMixin.tags,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


# Deathrattle: Summon a random 5-Cost minion from the past.
class ETC_349:
    """Unpopular Has-Been"""

    deathrattle = _UnpopularHasBeenSummon(SELF)


# Battlecry: Give +1/+1 to a minion of each type in your hand.
class ETC_350:
    """Party Animal"""

    play = _PartyAnimalBuff(SELF)


# Battlecry: Gain a random bonus effect for each minion type you've played this game.
class ETC_409(_TrailingProgressCardtextMixin):
    """The One-Amalgam Band"""

    play = _OneAmalgamBonus(SELF)

    def cardtext_entity_0(self):
        ctrl = getattr(self, "controller", None)
        if ctrl is None:
            return "0"
        seen = set()
        for c in ctrl.cards_played_this_game:
            if c.type != CardType.MINION:
                continue
            for race in getattr(c, "races", []):
                if race != _Race.INVALID:
                    seen.add(int(race))
        return str(len(seen))

    tags = {
        **_TrailingProgressCardtextMixin.tags,
        GameTag.CARDTEXT_ENTITY_0: cardtext_entity_0,
    }


# Battlecry: Draw a weapon.
class _DrawWeapon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        weapons = [c for c in list(target.deck) if c.type == CardType.WEAPON]
        if not weapons:
            return
        pick = source.game.random.choice(weapons)
        if len(target.hand) >= target.max_hand_size:
            pick.discard()
            return
        pick.zone = Zone.HAND


class ETC_418:
    """Instrument Tech"""

    play = _DrawWeapon(CONTROLLER)


# Rush. After this attacks, gain +1 Attack and attack a random enemy minion.
class ETC_419:
    """Mish-Mash Mosher"""

    events = Attack(SELF).after(_MishMashMosher(SELF))


# Battlecry: Give a friendly minion Attack and Health equal to this minion's.
class ETC_420:
    """Outfit Tailor"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = _OutfitTailorBuff(TARGET)


# After you play a {0}-Cost card, draw a {1}-Cost card. (Then increase!)
class ETC_422(_MetrognomeCardtextMixin):
    """Metrognome"""

    events = Play(CONTROLLER).after(_MetrognomeTick(SELF, Play.CARD))


# Battlecry: Add two 3/3 Bots to your opponent's hand.
# Deathrattle: Summon them for yourself.
class ETC_425:
    """Pozzik, Audio Engineer"""

    play = _PozzikBattlecry(SELF)
    deathrattle = _PozzikDeathrattle(SELF)


class ETC_425t:
    """Audio Bot"""

    # 3/3 vanilla; stats from data.


# After you cast a spell, add a random Fire spell to your hand.
class ETC_540:
    """Pyrotechnician"""

    events = OWN_SPELL_PLAY.after(_PyrotechnicianAddFireSpell(SELF))


# Both players' decks are swapped. Finale: Draw a card.
class ETC_541:
    """Tony, King of Piracy"""

    play = (
        _TonySwap(SELF),
        FINALE & Draw(CONTROLLER),
    )


# Taunt. Finale: Force all enemy minions to attack this.
class ETC_542:
    """Festival Security"""

    play = _FestivalSecurityForceAttack(SELF)


# Divine Shield. Finale: Give adjacent minions Divine Shield.
class ETC_543:
    """Candleraiser"""

    play = _CandleraiserAdjDS(SELF)


# Rush. Battlecry: If the last card you played costs (1), gain +1/+1.
class ETC_742:
    """Rolling Stone"""

    play = _RollingStoneCheck(SELF)


##
# Engine-internal enchantments


@custom_card
class ETC_522te_fallback:
    # Stub never referenced; the deathknight module owns the real one.
    tags = {
        GameTag.CARDNAME: "_unused",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ETC_336e:
    tags = {
        GameTag.CARDNAME: "Avian Freedom",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ETC_409e:
    tags = {
        GameTag.CARDNAME: "Do Re Malgam",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ETC_419e:
    tags = {
        GameTag.CARDNAME: "Moshing",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
    }


@custom_card
class ETC_742e:
    tags = {
        GameTag.CARDNAME: "Rockin' and Rollin'",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ETC_543e:
    tags = {
        GameTag.CARDNAME: "Candleraiser",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


# In-data enchantments with missing stat tags — supply them here.
class ETC_350e:
    # +1/+1.
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 1}


class ETC_105e:
    # +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class ETC_102e:
    # +1 weapon durability. Weapons read durability via _getattr("max_health"),
    # so the buff carries HEALTH not DURABILITY.
    tags = {GameTag.HEALTH: 1}


class ETC_106e:
    # "Next Mech costs (1) less" — script-side reduction lives on the
    # controller. Enchant is marker only.
    pass


class ETC_107e:
    # "+4 Attack" while the fan is alive.
    tags = {GameTag.ATK: 4}


class ETC_108e:
    tags = {GameTag.STEALTH: True}


class ETC_109e:
    tags = {GameTag.CANT_ATTACK: True}


@custom_card
class ETC_110e:
    # Cover Artist — runtime-stamped delta-buff used to force the
    # morphed minion's atk/max_health to exactly 3. Stats come from
    # Buff() kwargs each cast.
    tags = {
        GameTag.CARDNAME: "Cover Artist",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class ETC_089e:
    # -1 Attack.
    tags = {GameTag.ATK: -1}


class ETC_089e2:
    # -1 Health.
    tags = {GameTag.HEALTH: -1}


class ETC_420e:
    # Stats supplied at Buff() time via atk/max_health kwargs.
    pass
