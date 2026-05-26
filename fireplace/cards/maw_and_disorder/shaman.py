from ..utils import *

from ..castle_nathria.utils import InfuseCardtextMixin


##
# Spells


class _TotemicEvidenceSummonOnPick(TargetedAction):
    """Choose-callback for Totemic Evidence: summon the chosen Totem
    on the controller's side."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()

    def do(self, source, player, cards, picked):
        if isinstance(picked, list):
            if not picked:
                return
            picked = picked[0]
        source.game.cheat_action(source, [Summon(source.controller, picked.id)])


class _TotemicEvidenceOpenChoice(TargetedAction):
    """Open a real Choose-One over the (up to 4) basic Totems the
    controller doesn't already have on the board."""

    TARGET = ActionArg()

    def do(self, source, target):
        on_board = {m.id for m in target.field}
        avail = [tid for tid in BASIC_TOTEMS if tid not in on_board]
        if not avail:
            return
        offered = [target.card(tid, source=source) for tid in avail]
        choice = Choice(target, offered).then(
            _TotemicEvidenceSummonOnPick(Choice.PLAYER, Choice.CARDS, Choice.CARD)
        )
        source.game.queue_actions(source, [choice])


class MAW_003(InfuseCardtextMixin):
    """Totemic Evidence"""

    # Choose a basic Totem and summon it. (Infuse (3 Totems): Summon
    # all 4 instead.)  Opens a real Choose-One over the available
    # basic Totems.
    play = _TotemicEvidenceOpenChoice(CONTROLLER)


class MAW_003t:
    """Totemic Evidence"""

    # Infused — summon all 4 basic totems (excluding any duplicates).
    play = [Summon(CONTROLLER, tid) for tid in BASIC_TOTEMS]


class MAW_005:
    """Framester"""

    # Battlecry: Shuffle 3 'Framed' cards into the opponent's deck.
    # When drawn, they Overload for (2). MAW_005t has CASTS_WHEN_DRAWN
    # + OVERLOAD=2 in data, so the engine handles both auto-cast and
    # the overload tick on the opponent's side.
    play = Shuffle(OPPONENT, "MAW_005t") * 3


class MAW_005t:
    """Framed"""

    # Empty body — engine reads CASTS_WHEN_DRAWN and OVERLOAD tags
    # from data and fires both on draw automatically.
    pass


##
# Minions


class _TorghastRandomKeyword(TargetedAction):
    """For each enemy minion, randomly buff Torghast with Rush, Divine
    Shield, or Windfury (each enemy = one independent roll)."""

    TARGET = ActionArg()

    def do(self, source, target):
        enemies = list(target.controller.opponent.field)
        for _ in enemies:
            roll = source.game.random.randint(0, 2)
            buff_id = ("MAW_030e2", "MAW_030e3", "MAW_030e4")[roll]
            source.game.cheat_action(source, [Buff(target, buff_id)])


class MAW_030:
    """Torghast Custodian"""

    # Battlecry: For each enemy minion, randomly gain Rush, Divine
    # Shield, or Windfury. Enchantments live in data (MAW_030e2/3/4)
    # but data ships them as bare-name enchantments — the script
    # below adds the actual keyword tags.
    play = _TorghastRandomKeyword(SELF)


class MAW_030e2:
    # Crawling — Rush
    tags = {GameTag.RUSH: True}


class MAW_030e3:
    # Sweeping — Divine Shield
    tags = {GameTag.DIVINE_SHIELD: True}


class MAW_030e4:
    # Formidable — Windfury
    tags = {GameTag.WINDFURY: True}
