from ..utils import *


##
# Custom actions / helpers


class _FeyaKeeperDuplicateHand(TargetedAction):
    """Freya, Keeper of Nature — Guardians of Life branch:
    Add a copy of each card currently in hand to the controller's hand."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = target
        # Snapshot the hand first so newly added copies aren't included.
        originals = list(ctrl.hand)
        for card in originals:
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            source.game.cheat_action(source, [Give(ctrl, card.id)])


class _FreyaSummonCopies(TargetedAction):
    """Freya, Keeper of Nature — Seeds of the Future branch:
    Summon copies of all other friendly minions on the board."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = target
        # Snapshot field, excluding Freya herself (source is the card that played
        # the sub-ability; the titan is accessed via source.controller.field).
        originals = [m for m in list(ctrl.field) if m is not source]
        for minion in originals:
            if len(ctrl.field) >= 7:
                break
            source.game.cheat_action(source, [Summon(ctrl, minion.id)])


class _ConservatorNymphTransform(TargetedAction):
    """Conservator Nymph — Battlecry: Transform a friendly Treant into
    a 5/5 Timeless Ancient with Taunt (TTN_903t4)."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.game.queue_actions(source, [Morph(target, "TTN_903t4")])


class _DrawUntilFull(TargetedAction):
    """Eonar — Spontaneous Growth: Draw cards until your hand is full."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = target
        while len(ctrl.hand) < ctrl.max_hand_size and ctrl.deck:
            source.game.cheat_action(source, [Draw(ctrl)])


##
# Minions


class TTN_503:
    """Disciple of Eonar"""

    # Battlecry: Your next Choose One card has both effects combined.
    play = IncreaseAttr(CONTROLLER, "next_choose_one_combined", 1)


class TTN_903:
    """Eonar, the Life-Binder"""

    # Titan. After this uses an ability, summon a 5/5 Timeless Ancient with
    # Taunt. Implemented by appending Summon to each ability sub-card.
    titan_ability_order = ["TTN_903t", "TTN_903t2", "TTN_903t3"]


class TTN_903t:
    """Spontaneous Growth"""

    # Draw cards until your hand is full. Then summon a 5/5 Ancient.
    play = _DrawUntilFull(CONTROLLER), Summon(CONTROLLER, "TTN_903t4")


class TTN_903t2:
    """Bountiful Harvest"""

    # Restore your hero to full health. Then summon a 5/5 Ancient.
    play = FullHeal(FRIENDLY_HERO), Summon(CONTROLLER, "TTN_903t4")


class TTN_903t3:
    """Flourish"""

    # Refresh your Mana Crystals. Then summon a 5/5 Ancient.
    play = FillMana(CONTROLLER, USED_MANA(CONTROLLER)), Summon(CONTROLLER, "TTN_903t4")


class TTN_903t4:
    """Timeless Ancient"""

    # 5/5 with Taunt — stats and Taunt are in data.


class TTN_926:
    """Ancient of Growth"""

    # Choose One — Summon three 2/2 Treants; or Transform your Treants into
    # 5/5 Timeless Ancients with Taunt.
    choose = ("TTN_926a", "TTN_926b")


class TTN_926a:
    """Treant Growth"""

    # Summon three 2/2 Treants.
    play = Summon(CONTROLLER, "ETC_373t") * 3


class TTN_926b:
    """Ancient Growth"""

    # Transform your Treants into 5/5 Timeless Ancients with Taunt.
    play = Morph(FRIENDLY_MINIONS + TREANT, "TTN_903t4")


class TTN_927:
    """Conservator Nymph"""

    # Battlecry: Transform a friendly Treant into a 5/5 Ancient with Taunt.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _ConservatorNymphTransform(TARGET)


##
# Spells


class TTN_930:
    """Frost Lotus Seedling"""

    # Draw 1 card. Gain 4 Armor. (Blossoms in 4 turns.)
    # Shuffle the Blossom into your deck; it draws 2 cards and gives 8 Armor
    # when eventually drawn (the "blooms in 4 turns" is approximated as
    # shuffle-to-deck so it arrives in 4+ draws on average).
    play = (
        Draw(CONTROLLER),
        GainArmor(FRIENDLY_HERO, 4),
        Shuffle(CONTROLLER, "TTN_930t"),
    )


class TTN_930t:
    """Frost Lotus Blossom"""

    # Draw 2 cards. Gain 8 Armor.
    play = Draw(CONTROLLER) * 2, GainArmor(FRIENDLY_HERO, 8)


class TTN_940:
    """Freya, Keeper of Nature"""

    # Choose One — Duplicate your hand; or Summon copies of all other
    # friendly minions.
    choose = ("TTN_940a", "TTN_940b")


class TTN_940a:
    """Guardians of Life"""

    # Duplicate your hand (add a copy of each card in hand).
    play = _FeyaKeeperDuplicateHand(CONTROLLER)


class TTN_940b:
    """Seeds of the Future"""

    # Summon copies of all other friendly minions.
    play = _FreyaSummonCopies(CONTROLLER)


class TTN_950:
    """Forest Seedlings"""

    # Summon two 1/1 Saplings. (Blossoms in 4 turns.)
    # TTN_950t is the 1/1 Sapling token; TTN_950t3 (Forest Blossoms) is
    # shuffled into the deck to bloom when drawn later.
    play = (
        Summon(CONTROLLER, "TTN_950t") * 2,
        Shuffle(CONTROLLER, "TTN_950t3"),
    )


class TTN_950t:
    """Sapling"""

    # 1/1 vanilla — stats in data.


class TTN_950t2:
    """Treant"""

    # 2/2 vanilla — stats in data.


class TTN_950t3:
    """Forest Blossoms"""

    # Summon two 2/2 Treants.
    play = Summon(CONTROLLER, "TTN_950t2") * 2


class TTN_951:
    """Embrace of Nature"""

    # Draw a Choose One card. Forge: It has both effects combined.
    forge_card = "TTN_951t"
    play = ForceDraw(RANDOM(FRIENDLY_DECK + CHOOSE_ONE))


class TTN_951t:
    """Embrace of Nature"""

    # Forged — Draw a Choose One card. It has both effects combined.
    # After drawing, set next_choose_one_combined so the drawn card has
    # both effects when played.
    play = (
        ForceDraw(RANDOM(FRIENDLY_DECK + CHOOSE_ONE)),
        IncreaseAttr(CONTROLLER, "next_choose_one_combined", 1),
    )


class TTN_954:
    """Cultivation"""

    # Give your minions +2/+2. Costs (1) less for each Treant you've
    # summoned this game.
    cost_mod = -Attr(CONTROLLER, "treants_summoned_this_game")
    play = Buff(FRIENDLY_MINIONS, "TTN_954e")


TTN_954e = buff(+2, +2)


class TTN_955:
    """Lifebinder's Gift"""

    # Choose One — Get 2 random Nature spells; or Reduce the Cost of spells
    # in your hand by (1).
    choose = ("TTN_955A", "TTN_955B")


class TTN_955A:
    """Lifebinder's Bloom"""

    # Get 2 random Nature spells.
    play = Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.NATURE)) * 2


class TTN_955B:
    """Lifebinder's Growth"""

    # Reduce the Cost of spells in your hand by (1).
    play = Buff(FRIENDLY_HAND + SPELL, "TTN_955Be")


class TTN_955Be:
    # In-data enchantment "Lifebinder's Growth" — costs (1) less.
    tags = {GameTag.COST: -1}
