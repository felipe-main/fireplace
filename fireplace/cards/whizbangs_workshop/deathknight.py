from ..utils import *


##
# Helpers


def _spellstone_progress(self):
    """Corpse-Spellstone progress: corpses GAINED while this card sits in
    hand (the printed text reads "Gain 4 Corpses to upgrade"). We freeze a
    baseline of `corpses_gained_this_game` whenever the card is anywhere
    but the hand, so once drawn the running delta starts at 0 and ticks up
    with every corpse gained. The engine's process_reward() loop polls
    `finished` after every action stack empties, so no explicit corpse
    event hook is required."""
    from hearthstone.enums import Zone

    if self.zone != Zone.HAND or self.controller is None:
        if self.controller is not None:
            self._corpse_baseline = self.controller.corpses_gained_this_game
        return 0
    base = getattr(self, "_corpse_baseline", self.controller.corpses_gained_this_game)
    return self.controller.corpses_gained_this_game - base


def _spellstone_clear(self):
    self._progress = 0
    if self.controller is not None:
        self._corpse_baseline = self.controller.corpses_gained_this_game


##
# Minions


# Rush. After you cast a Frost spell, gain Reborn.
class TOY_821:
    """Rambunctious Stuffy"""

    tags = {GameTag.RUSH: True}
    events = Play(CONTROLLER, SPELL + FROST_SPELL).after(GiveReborn(SELF))


# Battlecry: If your deck started with a Blood, Frost, or Unholy card,
# gain Lifesteal, Reborn, or Rush respectively.
class _RainbowSeamstress(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        started = list(getattr(ctrl, "starting_deck", []))

        def _has(tag):
            return any(c.data.tags.get(tag, 0) >= 1 for c in started)

        if _has(GameTag.COST_BLOOD):
            source.game.cheat_action(source, [GiveLifesteal(source)])
        if _has(GameTag.COST_FROST):
            source.game.cheat_action(source, [GiveReborn(source)])
        if _has(GameTag.COST_UNHOLY):
            source.game.cheat_action(source, [GiveRush(source)])


class TOY_823:
    """Rainbow Seamstress"""

    play = _RainbowSeamstress(SELF)


# At the end of your turn, deal this minion's Attack damage randomly split
# among enemies.
class TOY_824:
    """Darkthorn Quilter"""

    events = OWN_TURN_END.on(Hit(RANDOM_ENEMY_CHARACTER, 1) * ATK(SELF))


# Taunt. Battlecry: Spend 5 Corpses to summon a copy of this.
class TOY_827:
    """Shambling Zombietank"""

    tags = {GameTag.TAUNT: True}
    play = (CORPSES >= 5) & (
        SpendCorpses(CONTROLLER, 5),
        Summon(CONTROLLER, "TOY_827"),
    )


# Miniaturize, Taunt. Deathrattle: Give Undead in your hand +2/+2.
class TOY_828:
    """Amateur Puppeteer"""

    tags = {GameTag.TAUNT: True}
    deathrattle = Buff(FRIENDLY_HAND + UNDEAD, "TOY_828e4", atk=2, max_health=2)


# Mini, Taunt. Deathrattle: Give Undead in your hand +2/+2.
class TOY_828t:
    """Amateur Puppeteer"""

    tags = {GameTag.TAUNT: True}
    deathrattle = Buff(FRIENDLY_HAND + UNDEAD, "TOY_828e4", atk=2, max_health=2)


# Battlecry: Discover a 5, 3, and 1-Cost minion to stitch to this.
# Deathrattle: Summon the 5-Cost minion (which summons the 3-Cost, which
# summons the 1-Cost — the full stitch chain).
class _StitchensewStore(TargetedAction):
    """Record one stitched minion id and re-queue the next Discover in the
    descending-cost sequence (5 → 3 → 1). The 5-Cost pick (first) is also
    stamped onto the source minion for its deathrattle."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards, picked):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        costs = source._stitch_remaining
        cost, is_first = costs.pop(0)
        if picked is not None:
            if not hasattr(source, "_stitched"):
                source._stitched = []
            source._stitched.append(picked.id)
            if is_first:
                source._stitched_five = picked.id
        if costs:
            source.game.queue_actions(source, [_StitchensewOpen(SELF)])


class _StitchensewOpen(TargetedAction):
    """Open the Discover for the next pending stitched cost. The Discover
    is queued with the host minion (target) as its source so the
    _StitchensewStore callback reads the minion's pending-cost list."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = target.controller
        cost = target._stitch_remaining[0][0]
        picker = RandomMinion(
            custom_filter=lambda c, _cost=cost: c.cost == _cost
        )
        action = Discover(ctrl, picker).then(
            _StitchensewStore(Discover.TARGET, Discover.CARDS, Discover.CARD)
        )
        target.game.queue_actions(target, [action])


class _StitchensewDiscover(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        source._stitched = []
        source._stitched_five = None
        source._stitch_remaining = [(5, True), (3, False), (1, False)]
        source.game.queue_actions(source, [_StitchensewOpen(source)])


class _StitchensewSummon(TargetedAction):
    """Deathrattle: summon the stitched 5-Cost minion, which in turn summons
    the 3-Cost, which in turn summons the 1-Cost (the in-game stitch chain).
    We materialise the whole chain here in descending-cost order so the final
    board state matches live Hearthstone."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        stitched = list(getattr(source, "_stitched", []))
        if not stitched:
            five = getattr(source, "_stitched_five", None)
            stitched = [five] if five else []
        for cid in stitched:
            if cid:
                source.game.cheat_action(source, [Summon(ctrl, cid)])


class TOY_830:
    """Dr. Stitchensew"""

    play = _StitchensewDiscover(SELF)
    deathrattle = _StitchensewSummon(SELF)


##
# Spells


# Choose a friendly minion. Discover a spell that costs (4) or less for it
# to cast when it dies.
class _SilkStitchingStore(TargetedAction):
    """After the spell is Discovered, stamp the host minion with the spell
    id and a deathrattle enchant (TOY_822e) that casts it on death."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def __init__(self, target, cards, card, host):
        super().__init__(target, cards, card)
        self._host = host

    def do(self, source, player, cards, picked):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if picked is None or self._host is None:
            return
        host = self._host
        host._silk_spell = picked.id
        source.game.cheat_action(source, [Buff(host, "TOY_822e")])


class _SilkStitchingCast(TargetedAction):
    """Deathrattle granted by TOY_822e: cast the stored spell."""

    TARGET = ActionArg()

    def do(self, source, target):
        # target = OWNER = the host minion carrying the stored spell id.
        spell_id = getattr(target, "_silk_spell", None)
        if not spell_id:
            return
        source.game.cheat_action(target.controller, [CastSpell(spell_id)])


class _SilkStitchingDiscover(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # No card_class filter: the Discover machinery weights the pool by
        # the hero's class + Neutral automatically.
        picker = RandomSpell(custom_filter=lambda c: c.cost <= 4)
        action = Discover(ctrl, picker).then(
            _SilkStitchingStore(
                Discover.TARGET, Discover.CARDS, Discover.CARD, target
            )
        )
        source.game.queue_actions(source, [action])


class TOY_822:
    """Silk Stitching"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = _SilkStitchingDiscover(TARGET)


class TOY_822e:
    # "Darkness Within" — Cast the stored spell when the minion dies.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = _SilkStitchingCast(OWNER)


# Give Undead in your hand +1/+1. (Gain 4 Corpses to upgrade.)
class TOY_825:
    """Lesser Spinel Spellstone"""

    progress_total = 4
    play = Buff(FRIENDLY_HAND + UNDEAD, "TOY_825e", atk=1, max_health=1)
    reward = Morph(SELF, "TOY_825t")
    progress = _spellstone_progress
    clear_progress = _spellstone_clear


# Give Undead in your hand +2/+2. (Gain 4 Corpses to upgrade.)
class TOY_825t:
    """Spinel Spellstone"""

    progress_total = 4
    play = Buff(FRIENDLY_HAND + UNDEAD, "TOY_825e2", atk=2, max_health=2)
    reward = Morph(SELF, "TOY_825t2")
    progress = _spellstone_progress
    clear_progress = _spellstone_clear


# Give Undead in your hand +3/+3.
class TOY_825t2:
    """Greater Spinel Spellstone"""

    play = Buff(FRIENDLY_HAND + UNDEAD, "TOY_825e3", atk=3, max_health=3)


# Give all minions "Deathrattle: Deal 1 damage to all minions."
class TOY_826:
    """Threads of Despair"""

    play = Buff(ALL_MINIONS, "TOY_826e")


class TOY_826e:
    # "Threads of the Dead" — Deathrattle: Deal 1 damage to all minions.
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Hit(ALL_MINIONS, 1)


##
# Hero + tokens


# Battlecry: Destroy the enemy minion with the most Attack! Shuffle my Head
# into your deck.
class TOY_829:
    """The Headless Horseman"""

    play = (
        Destroy(HIGHEST_ATK(ENEMY_MINIONS)),
        Shuffle(CONTROLLER, "TOY_829t"),
    )


class TOY_829t2:
    """The Headless Horseman"""

    play = (
        Destroy(HIGHEST_ATK(ENEMY_MINIONS)),
        Shuffle(CONTROLLER, "TOY_829t"),
    )


# When Drawn, this Casts. Imbue the souls of Undead into your Hero Power!
class _HorsemanImbue(TargetedAction):
    """Replace the current hero power with the imbued Pulsing Pumpkins
    (Deal 3 + Discover an Undead)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.summon("TOY_829hp")


class TOY_829t:
    """Horseman's Head"""

    tags = {GameTag.CASTS_WHEN_DRAWN: True}
    play = _HorsemanImbue(CONTROLLER)


# Pulsing Pumpkins (base): Deal 3 damage.
class TOY_829hp3:
    """Pulsing Pumpkins"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 3)


# Pulsing Pumpkins (imbued): Deal 3 damage. Discover an Undead.
class TOY_829hp:
    """Pulsing Pumpkins"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 3), DISCOVER(RandomMinion(race=Race.UNDEAD))


##
# Whizbang's Workshop mini-set (Dr. Boom's Incredible Inventions)


# "Choose a minion in your hand" support — the engine's play-targets only
# range over in-play characters, so model the printed hand pick with an
# ENTITY_CHOICE over the friendly hand minions, then run a callback.
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
    ctrl = source.controller
    minions = [c for c in ctrl.hand if c.type == CardType.MINION]
    if not minions:
        return
    if len(minions) == 1:
        apply(source, minions[0])
        return
    ctrl.choice = _HandMinionChoice(source, ctrl, minions, apply)


@custom_card
class MIS_006e:
    # "Collection Bonus" battlecry discount — magnitude (this minion's
    # Attack) is supplied via the cost= kwarg at Buff time. Not in data.
    tags = {
        GameTag.CARDNAME: "Collection Bonus",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class MIS_006:
    """Toysnatching Geist"""

    # Gigantify (engine). Battlecry: Discover an Undead. Reduce its Cost by
    # this minion's Attack.
    play = Discover(CONTROLLER, RandomMinion(race=Race.UNDEAD)).then(
        Give(CONTROLLER, Discover.CARD).then(
            Buff(Give.CARD, "MIS_006e", cost=-ATK(SELF))
        )
    )


class MIS_006t(MIS_006):
    """Toysnatching Geist"""

    # Gigantic 8/8 form — same Discover battlecry (reduces by 8 Attack).


class _HelmHandBuff(TargetedAction):
    """Helm of Humiliation — give a CHOSEN minion in your hand +5/+5."""

    TARGET = ActionArg()

    def do(self, source, target):
        _choose_hand_minion(
            source,
            lambda s, m: s.game.cheat_action(s, [Buff(m, "MIS_100e1")]),
        )


class MIS_100:
    """Helm of Humiliation"""

    # Give a minion -5/-5. Give a minion in your hand +5/+5.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "MIS_100e"), _HelmHandBuff(SELF)


class MIS_100e:
    # Humiliated — -5/-5.
    tags = {GameTag.ATK: -5, GameTag.HEALTH: -5}


class MIS_100e1:
    # Discount Lich King — +5/+5.
    tags = {GameTag.ATK: 5, GameTag.HEALTH: 5}


class MIS_101:
    """Foamrender"""

    # Whenever your hero attacks, spend 3 Corpses to gain +1 Durability.
    events = Attack(FRIENDLY_HERO).after(
        (CORPSES >= 3) & SpendCorpses(CONTROLLER, 3).then(Buff(SELF, "MIS_101e"))
    )


class MIS_101e:
    # Some Assembly Required — +1 Durability.
    tags = {GameTag.HEALTH: 1}
