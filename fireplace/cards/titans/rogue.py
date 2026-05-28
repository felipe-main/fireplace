from ..utils import *


##
# Custom actions


class _ClearStealthAction(TargetedAction):
    """Remove stealth from TARGET (used for SP-3Y3-D3R 'Stealth for 1 turn')."""

    TARGET = ActionArg()

    def do(self, source, target):
        target.stealthed = False


class _GearShiftAction(TargetedAction):
    """Gear Shift (TTN_922) — Shuffle the two left-most cards in the
    controller's hand into their deck, then Draw 3.

    "Left-most" = hand[0] and hand[1] by engine list order.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        # Collect the two leftmost cards (may be fewer if hand is tiny)
        to_shuffle = list(ctrl.hand)[:2]
        for card in to_shuffle:
            source.game.cheat_action(source, [Shuffle(ctrl, card)])
        source.game.cheat_action(source, [Draw(ctrl)] * 3)


class _MimironGadgetGive(TargetedAction):
    """Mimiron, the Mastermind (TTN_920) — After you play a Mech, give a
    random one of Mimiron's Gadgets to the controller's hand.

    Gadget pool (all spells): TTN_920t10 (Blades), TTN_920t5 (Coolant),
    TTN_920t6 (Cloakfield), TTN_920t7 (Switch), TTN_920t8 (Horn),
    TTN_920t9 (Rewinder).
    """

    _GADGETS = (
        "TTN_920t10",  # Mimiron's Blades — Deal 3 damage
        "TTN_920t5",   # Mimiron's Coolant — next card costs (2) less this turn
        "TTN_920t6",   # Mimiron's Cloakfield — give minion +3 Atk + Stealth
        "TTN_920t7",   # Mimiron's Switch — two minions swap stats
        "TTN_920t8",   # Mimiron's Horn — give minion Taunt + Divine Shield
        "TTN_920t9",   # Mimiron's Rewinder — return a minion to owner's hand
    )

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        chosen = source.game.random.choice(self._GADGETS)
        source.game.cheat_action(source, [Give(ctrl, chosen)])


class _LabConstructorSummonCopy(TargetedAction):
    """Lab Constructor (TTN_730) end-of-turn trigger — summon a copy of
    SELF (the Lab Constructor) at end of turn.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(
            source, [Summon(source.controller, "TTN_730")]
        )


class _LabConstructorForgeSummonCopy(TargetedAction):
    """Lab Constructor Forged (TTN_730t) end-of-turn trigger — summon a
    copy of the Forged version.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.cheat_action(
            source, [Summon(source.controller, "TTN_730t")]
        )


class _KajamiteOtherClassSpell(RandomCardPicker):
    """Kaja'mite Creation — pick a random collectible spell from another
    class (not Rogue, not Neutral) that costs 3 or less.
    """

    def __init__(self):
        super().__init__(collectible=True, type=CardType.SPELL)

    def evaluate(self, source):
        from hearthstone.enums import CardClass
        from fireplace import cards as _cards
        ctrl_class = getattr(source.controller.hero, "card_class", CardClass.INVALID)
        candidates = []
        for cid in _cards.db.filter(collectible=True, type=CardType.SPELL):
            c = _cards.db[cid]
            if c.cost > 3:
                continue
            classes = getattr(c, "classes", None) or [c.card_class]
            if ctrl_class in classes:
                continue
            if classes == [CardClass.NEUTRAL]:
                continue
            candidates.append(cid)
        if not candidates:
            return []
        return [source.game.random.choice(candidates)]


class _VTR0NPrimeRepeatOnFriendly(TargetedAction):
    """V-07-TR-0N Prime (TTN_721) passive — after each ability use, repeat
    its stat-buff portion on a random OTHER friendly minion.

    Called from each ability sub-card's play tuple with the buff id to
    apply and an optional extra action (Hit / Draw) that targets the
    chosen friendly minion.
    """

    TARGET = ActionArg()
    BUFF = ActionArg()   # enchant id string to apply

    def do(self, source, target, buff_id):
        others = [m for m in source.controller.field if m is not source]
        if not others:
            return
        chosen = source.game.random.choice(others)
        source.game.cheat_action(source, [Buff(chosen, buff_id)])


##
# Minions


class TTN_721:
    """V-07-TR-0N Prime"""

    # T1T4N. This minion's abilities repeat on another random friendly minion.
    titan_ability_order = ["TTN_721t", "TTN_721t1", "TTN_721t2"]


class TTN_730:
    """Lab Constructor"""

    # At the end of your turn, summon a copy of this.
    # Forge: Gain Magnetic (forged card is TTN_730t).
    events = OWN_TURN_END.on(_LabConstructorSummonCopy(SELF))
    forge_card = "TTN_730t"


class TTN_730t:
    """Lab Constructor"""

    # Forged, Magnetic. At the end of your turn, summon a copy of this.
    events = OWN_TURN_END.on(_LabConstructorForgeSummonCopy(SELF))


class TTN_920:
    """Mimiron, the Mastermind"""

    # After you play a Mech, get a random one of Mimiron's Gadgets.
    events = Summon(CONTROLLER, MECH - SELF).on(_MimironGadgetGive(SELF))


class TTN_921:
    """Coppertail Snoop"""

    # Magnetic. Whenever this attacks, get a Coin.
    events = Attack(SELF).on(Give(CONTROLLER, THE_COIN))


class TTN_923:
    """SP-3Y3-D3R"""

    # Magnetic. Stealth for 1 turn.
    # Stealth is set in data; the "for 1 turn" part: remove stealth at
    # the start of the controller's next turn.
    events = OWN_TURN_BEGIN.on(_ClearStealthAction(SELF))

    # TTN_923e is in data — no script needed beyond the turn-begin removal.


class TTN_925:
    """Kaja'mite Creation"""

    # Battlecry: Discover a spell from another class that costs (3) or less.
    play = DISCOVER(_KajamiteOtherClassSpell())


##
# Spells


_SPARKBOT_IDS = [
    "TTN_719t", "TTN_719t1", "TTN_719t2", "TTN_719t3",
    "TTN_719t4", "TTN_719t5", "TTN_719t6", "TTN_719t7",
]


class TTN_719:
    """From the Scrapheap"""

    def play(self):
        ctrl = self.controller
        for cid in self.game.random.sample(_SPARKBOT_IDS, 3):
            yield Give(ctrl, cid)


class _TarSlickArm(TargetedAction):
    """Tar Slick — arm the both-player per-turn double-damage flag for minions.
    Must arm on both players so any source dealing minion damage this turn
    sees the multiplier (Predamage reads target.controller.minion_damage_doubled).
    """
    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.minion_damage_doubled_this_turn = True
        source.controller.opponent.minion_damage_doubled_this_turn = True


class TTN_726:
    """Tar Slick"""

    # Minions take double damage this turn. Deal 1 damage.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _TarSlickArm(CONTROLLER), Hit(TARGET, 1)


class TTN_728:
    """Pit Stop"""

    # Discover a Mech from your deck. Give it +2/+1.
    def play(self):
        ctrl = self.controller
        deck_mechs = [c for c in ctrl.deck
                      if c.type == CardType.MINION and Race.MECHANICAL in c.races]
        if not deck_mechs:
            return
        unique_ids = list({c.id for c in deck_mechs})
        yield GenericChoice(ctrl, RandomID(*unique_ids)).then(
            Buff(GenericChoice.CARD, "TTN_728e1")
        )


class TTN_922:
    """Gear Shift"""

    # Shuffle the two left-most cards in your hand into your deck. Draw 3 cards.
    play = _GearShiftAction(CONTROLLER)


##
# Titan ability sub-cards


class TTN_721t:
    """Attach the Cannons!"""

    # Gain +2/+1. Deal 4 damage to a random enemy.
    # T1T4N: also buff a random OTHER friendly minion with +2/+1.
    play = (
        Buff(SELF, "TTN_721te"),
        Hit(RANDOM(ENEMY_CHARACTERS), 4),
        _VTR0NPrimeRepeatOnFriendly(SELF, "TTN_721te"),
    )


class TTN_721t1:
    """Full Power!"""

    # Gain +1/+2. Draw a card.
    # T1T4N: also buff a random OTHER friendly minion with +1/+2.
    play = (
        Buff(SELF, "TTN_721t1e"),
        Draw(CONTROLLER),
        _VTR0NPrimeRepeatOnFriendly(SELF, "TTN_721t1e"),
    )


class TTN_721t2:
    """Maximize Defenses!"""

    # Gain +3 Health and "Can't be targeted by spells or Hero Powers."
    # T1T4N: also apply the same to a random OTHER friendly minion.
    play = (
        Buff(SELF, "TTN_721t2e2"),
        _VTR0NPrimeRepeatOnFriendly(SELF, "TTN_721t2e2"),
    )


##
# Enchantments (in-data — declare stat tags where missing)


class TTN_721te:
    """Cannons Armed!"""

    # +2/+1 — used by Attach the Cannons! ability
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}


class TTN_721t1e:
    """Plating Reinforced!"""

    # +1/+2 — used by Full Power! ability
    tags = {GameTag.ATK: 1, GameTag.HEALTH: 2}


class TTN_721t2e2:
    """Sneak Attack!"""

    # +3 Health and can't be targeted by spells or Hero Powers.
    tags = {
        GameTag.HEALTH: 3,
        GameTag.CANT_BE_TARGETED_BY_ABILITIES: True,
        GameTag.CANT_BE_TARGETED_BY_HERO_POWERS: True,
    }


class TTN_728e1:
    """Tuned Up"""

    # +2/+1 — used by Pit Stop
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 1}
