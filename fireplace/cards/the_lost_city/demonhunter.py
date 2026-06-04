from ..utils import *


##
# Custom actions


class _GorishiColossusBonus(TargetedAction):
    """Gorishi Colossus permanent enchant tick: when the controller deals
    exactly 2 damage to an enemy, deal 2 more — guarded against re-triggering
    on its own bonus hit."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        if getattr(player, "_gorishi_colossus_bonus_active", False):
            return
        if target is None or target.dead:
            return
        if target.controller is player:
            return
        player._gorishi_colossus_bonus_active = True
        try:
            source.game.queue_actions(source, [Hit(target, 2)])
        finally:
            player._gorishi_colossus_bonus_active = False


class _EntomologistJar(TargetedAction):
    """Entomologist Toru battlecry: replace each minion in the controller's
    hand with a 0/1 Specimen Jar that costs (1) and whose deathrattle releases
    the original minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        minions = [c for c in list(player.hand) if c.type == CardType.MINION]
        for original in minions:
            jar = player.card("TLC_841t", source=source)
            jar.controller = player
            jar._summon_index = original.zone_position
            jar.zone = Zone.HAND
            original.zone = Zone.SETASIDE
            jar._jarred_minion = original
        source.game.manager.targeted_action(self, source, target)


class _ReleaseJarredMinion(TargetedAction):
    """Specimen Jar deathrattle: summon the minion stored inside the jar."""

    TARGET = ActionArg()

    def do(self, source, target):
        original = getattr(source, "_jarred_minion", None)
        if original is None:
            return
        player = source.controller
        original.controller = player
        source.game.queue_actions(player, [Summon(player, original)])
        source._jarred_minion = None


##
# Minions


class TLC_630:
    """Gorishi Wasp"""

    # Whenever this takes damage, get a 1-Cost Gorishi Stinger.
    events = SELF_DAMAGE.on(Give(CONTROLLER, "TLC_630t"))


class TLC_633:
    """Bugsquasher"""

    # <b>Battlecry:</b> Deal 6 damage to an enemy minion with a minion type.
    # REQ_TARGET_WITH_ANY_RACE enforces "with a minion type": only enemy minions
    # that have at least one race are valid targets (a raceless Yeti is not).
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_ANY_RACE: 0,
    }
    play = Hit(TARGET, 6)


class TLC_840:
    """Gorishi Tunneler"""

    # <b>Stealth</b> After this attacks, deal 2 damage to the enemy hero.
    events = Attack(SELF).after(Hit(ENEMY_HERO, 2))


class TLC_841:
    """Entomologist Toru"""

    # <b>Battlecry:</b> Put each minion in your hand into 0/1 Jars that cost
    # (1). Break them to release the minions!
    play = _EntomologistJar(CONTROLLER)


class TLC_903:
    """Silithid Queen"""

    # <b>Rush</b> <b>Kindred</b>: Give your hero +5 Attack this turn.
    play = Kindred() & Buff(FRIENDLY_HERO, "TLC_903e")


##
# Tokens


def _specimen_jar_cardtext(self):
    # Data text: "<empty-jar variant>@<b>Deathrattle:</b> Release {5}!" — two
    # `@`-delimited segments. Render the filled variant with the stored
    # minion's name substituted for {5}; if the jar is empty, the empty variant.
    segments = self.data.description.split("@")
    stored = getattr(self, "_jarred_minion", None)
    if stored is None or len(segments) < 2:
        return segments[0]
    name = getattr(getattr(stored, "data", None), "name", None) or stored.id
    return segments[1].replace("{5}", name)


class TLC_841t:
    """Specimen Jar"""

    # <b>Deathrattle:</b> Release the stored minion. The printed deathrattle
    # text is conditional — "Release <stored minion>!" when a minion is jarred,
    # or "Release nothing. (It's just an empty jar.)" when empty — rendered via
    # custom_cardtext from the {5} = stored minion's name.
    tags = {
        GameTag.DEATHRATTLE: True,
        enums.CUSTOM_CARDTEXT: _specimen_jar_cardtext,
    }
    deathrattle = _ReleaseJarredMinion(SELF)


class TLC_903t:
    """Silithid Grub"""

    # <b>Rush</b> (vanilla 2/1 token; keywords come from data)


class TLC_630t:
    """Gorishi Stinger"""

    # Deal $2 damage. Summon a 2/1 Grub with <b>Rush</b>.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 2), Summon(CONTROLLER, "TLC_903t")


class TLC_631t:
    """Gorishi Colossus"""

    # <b>Battlecry:</b> For the rest of the game, whenever you deal exactly 2
    # damage to an enemy, deal 2 more.
    play = Buff(CONTROLLER, "TLC_631e")


class TLC_631e:
    # Gorishi's Favor — permanent controller enchant powering the Colossus.
    events = Damage(ENEMY_CHARACTERS, source=FRIENDLY).after(
        (Damage.AMOUNT == 2) & _GorishiColossusBonus(Damage.TARGET)
    )


##
# Weapons


class TLC_833:
    """Insect Claw"""

    # After your hero attacks, summon a 2/1 Grub with <b>Rush</b>.
    events = Attack(FRIENDLY_HERO).after(Summon(CONTROLLER, "TLC_903t"))


##
# Spells


class TLC_631:
    """Unleash the Colossus"""

    # <b>Quest:</b> Deal exactly 2 damage to an enemy on your turn, 15 times.
    # <b>Reward:</b> Gorishi Colossus.
    quest = Damage(ENEMY_CHARACTERS, source=FRIENDLY).after(
        (Damage.AMOUNT == 2)
        & (Find(CURRENT_PLAYER + CONTROLLER) & AddProgress(SELF, 1))
    )
    reward = Summon(CONTROLLER, "TLC_631t")


class TLC_900:
    """Hive Map"""

    # <b>Discover</b> a Fel spell. If you play it this turn, also pick one of
    # the others — the two un-chosen Fel spells, via the shared
    # DiscoverPickOther machinery.
    play = Discover(CONTROLLER, RandomSpell(spell_school=SpellSchool.FEL)).then(
        DiscoverPickOther(SELF, Discover.CARDS, Discover.CARD)
    )


class TLC_901:
    """Fumigate"""

    # Deal $3 damage to a minion and all others of the same minion type.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Hit(ALL_MINIONS + SAME_RACE_TARGET - TARGET, 3)


class TLC_902:
    """Infestation"""

    # Get two 1-Cost Gorishi Stingers. Each one deals $2 damage and summons a
    # 2/1 Grub with <b>Rush</b>.
    play = Give(CONTROLLER, "TLC_630t") * 2


##
# Enchantments


class TLC_903e:
    """Queen's Stinger"""

    # +5 Attack this turn.
    tags = {GameTag.ATK: 5, GameTag.TAG_ONE_TURN_EFFECT: True}


##
# The Lost City of Un'Goro — Dinosaurs mini-set (DINO_)


class _SaucierDiscount(TargetedAction):
    """Skittish Saucier battlecry: reduce the Cost of its two physical hand
    neighbours by (1).

    The battlecry fires *after* the Saucier has left the hand (``Play.do`` set
    ``card.zone = PLAY`` before invoking the battlecry). But ``Play.do`` first
    snapshots the Saucier's exact hand position into ``_play_hand_index`` (its
    0-based slot) and ``_play_hand_size`` (the hand size *including* the
    Saucier). We use that snapshot to identify the true left/right neighbours:

      - The left neighbour sat at original index ``idx - 1``. Cards *before*
        the gap don't shift when the Saucier is removed, so it is still at
        index ``idx - 1`` in the now-shorter hand.
      - The right neighbour sat at original index ``idx + 1``. Removing the
        Saucier shifts everything after the gap down by one, so it is now at
        index ``idx`` in the current hand.

    Edge plays (left-most / right-most) simply have only one neighbour."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        hand = list(player.hand)
        idx = getattr(source, "_play_hand_index", -1)
        if idx < 0:
            return
        # Current-hand positions of the two original physical neighbours.
        neighbor_positions = []
        if idx - 1 >= 0:
            neighbor_positions.append(idx - 1)        # left neighbour, unshifted
        if idx <= len(hand) - 1:
            neighbor_positions.append(idx)            # right neighbour, shifted down 1
        for pos in neighbor_positions:
            source.game.queue_actions(source, [Buff(hand[pos], "DINO_137e")])


class _HornOfFeasting(TargetedAction):
    """Horn of Feasting: summon three 2/1 Rush Raptors. When played as an
    Outcast (``immune=True``), also give each freshly-summoned Raptor Immune
    while attacking this turn (a one-turn enchant)."""

    TARGET = ActionArg()

    def __init__(self, *args, immune=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._immune = immune

    def do(self, source, target):
        player = source.controller
        for _ in range(3):
            before = set(player.field)
            source.game.queue_actions(player, [Summon(player, "DINO_136t")])
            if self._immune:
                for raptor in [m for m in player.field if m not in before]:
                    source.game.queue_actions(source, [Buff(raptor, "DINO_136e")])


class DINO_136:
    """Horn of Feasting"""

    # Summon three 2/1 Raptors with <b>Rush</b>.
    # <b>Outcast:</b> Give them <b>Immune</b> while attacking this turn.
    # This data build encodes Outcast as tag 1824 (not GameTag.OUTCAST=1333,
    # which the engine maps to has_outcast), so the engine's Outcast dispatch
    # never fires. Re-stamp the recognised OUTCAST tag so the edge-play check
    # in Play/Battlecry routes to the `outcast` script.
    tags = {GameTag.OUTCAST: True}
    play = _HornOfFeasting(CONTROLLER)
    outcast = _HornOfFeasting(CONTROLLER, immune=True)


class DINO_137:
    """Skittish Saucier"""

    # <b>Battlecry:</b> Reduce the Cost of adjacent cards in your hand by (1).
    play = _SaucierDiscount(SELF)


class DINO_138:
    """Diabolus Rex"""

    # <b>Kindred:</b> Deal 6 damage to your opponent's left and right-most
    # minions.
    play = Kindred() & Hit(OUTERMOST(ENEMY_MINIONS), 6)


##
# DINO tokens


class DINO_136t:
    """Ravenous Raptor"""

    # <b>Rush</b> (vanilla 2/1 token; Rush comes from data)


##
# DINO enchantments


class DINO_136e:
    """Feasting"""

    # <b>Immune</b> while attacking this turn (data enchant carries only the
    # one-turn-effect marker, so we supply the Immune-while-attacking tag).
    tags = {
        GameTag.IMMUNE_WHILE_ATTACKING: True,
        GameTag.TAG_ONE_TURN_EFFECT: True,
    }


@custom_card
class DINO_137e:
    # Skittish Saucier — adjacent card costs (1) less.
    tags = {
        GameTag.CARDNAME: "Skittish Saucier",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }
