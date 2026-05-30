from ..utils import *


##
# Custom actions


class _GormEatRight(TargetedAction):
    """Gorm the Worldeater — at the end of your turn, destroy the minion to
    the right of this to awaken 1 turn sooner."""

    TARGET = ActionArg()

    def do(self, source, target):
        field = list(source.controller.field)
        if source not in field:
            return
        i = field.index(source)
        if i + 1 < len(field):
            victim = field[i + 1]
            source.game.cheat_action(source, [Destroy(victim)])
            source.dormant_turns = max(0, source.dormant_turns - 1)


class _LaserBarrage(TargetedAction):
    """Laser Barrage — deal 3 to a minion; if building a Starship, also deal 3
    to its board neighbors."""

    TARGET = ActionArg()

    def do(self, source, target):
        board = list(target.controller.field)
        neighbors = []
        if target in board:
            i = board.index(target)
            if i > 0:
                neighbors.append(board[i - 1])
            if i < len(board) - 1:
                neighbors.append(board[i + 1])
        amount = source.controller.get_spell_damage(source, 3)
        source.game.cheat_action(source, [Hit(target, amount)])
        if source.controller.is_building_starship:
            for nb in neighbors:
                source.game.cheat_action(source, [Hit(nb, amount)])


##
# Minions


class GDB_107:
    """Specimen Claw"""

    # After your opponent plays a minion, attack it. Starship Piece.
    events = Play(OPPONENT, MINION).after(Attack(SELF, Play.CARD))


class GDB_111:
    """Biopod"""

    # Deathrattle: Deal damage equal to this minion's Attack to a random
    # enemy. Starship Piece.
    deathrattle = Hit(RANDOM(ENEMY_CHARACTERS), ATK(SELF))


class GDB_840:
    """Extraterrestrial Egg"""

    # Deathrattle: Summon a 3/5 Beast that attacks the lowest Health enemy.
    deathrattle = Summon(CONTROLLER, "GDB_840t").then(
        Attack(Summon.CARD, LOWEST_HEALTH(ENEMY_CHARACTERS))
    )


class GDB_841:
    """Rangari Scout"""

    # After you Discover a card, get a copy of it.
    events = Discovered(CONTROLLER).on(Give(CONTROLLER, Copy(Discovered.CARD)))


class GDB_842:
    """Gorm the Worldeater"""

    # Dormant for 5 turns. At the end of your turn, destroy the minion to the
    # right of this to awaken 1 turn sooner.
    dormant_events = OWN_TURN_END.on(_GormEatRight(SELF))


class GDB_846:
    """Exarch Naielle"""

    # Battlecry: Replace your Hero Power with Tracking (Discover a card from
    # your deck).
    play = Summon(CONTROLLER, "GDB_846hp")


##
# Weapons


class GDB_843:
    """Parallax Cannon"""

    # Has +2 Attack if you've Discovered this turn. Spellburst: Your hero is
    # Immune this turn.
    update = (Attr(CONTROLLER, "discovers_this_turn") >= 1) & Refresh(
        SELF, {GameTag.ATK: 2}
    )
    spellburst = Buff(FRIENDLY_HERO, "GDB_843e2")


##
# Spells


class GDB_237:
    """Alien Encounters"""

    # Summon two 2/5 Beasts with Taunt. Costs (1) less for each card you
    # Discovered this game.
    cost_mod = -Attr(CONTROLLER, "discovers_this_game")
    play = Summon(CONTROLLER, "GDB_237t") * 2


class GDB_844:
    """Detailed Notes"""

    # Discover a Beast that costs (5) or more. Reduce its Cost by (2).
    play = Discover(CONTROLLER, RandomBeast(cost=range(5, 100))).then(
        Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "GDB_844e"))
    )


class GDB_845:
    """Laser Barrage"""

    # Deal $3 damage to a minion. If you're building a Starship, also damage
    # its neighbors.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _LaserBarrage(TARGET)


##
# Tokens


class GDB_237t:
    """Snacking Scrunguk"""

    # 2/5 Beast with Taunt. Stats + Taunt live in data.


class GDB_840t:
    """Eggburster"""

    # 3/5 Beast. Stats live in data; the attack is driven by the Egg's
    # deathrattle.


##
# Enchantments


@custom_card
class GDB_844e:
    # Detailed Notes — the Beast costs (2) less.
    tags = {
        GameTag.CARDNAME: "Detailed Notes",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class GDB_843e2:
    # Angular Immunity — your hero is Immune this turn.
    tags = {GameTag.CANT_BE_DAMAGED: True}
