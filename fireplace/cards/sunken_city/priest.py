from ..utils import *


##
# Spells


class TSC_209:
    """Whirlpool"""

    # Destroy all minions and all copies of them (wherever they are).
    # Approximation: destroy all minions on the field, and also discard
    # any copies in hands/decks (silenced + destroyed).
    def play(self):
        all_field = list(self.game.player1.field) + list(self.game.player2.field)
        ids = {m.id for m in all_field}
        for m in all_field:
            yield Destroy(m)
        for player in (self.game.player1, self.game.player2):
            for zone_list in (player.hand, player.deck):
                for c in list(zone_list):
                    if c.id in ids:
                        c.discard()


class TSC_210:
    """Illuminate"""

    # Dredge. If it's a spell, reduce its Cost by (3).
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDTYPE) == int(CardType.SPELL))
        & Buff(Dredge.CARD, "TSC_210e")
    )


@custom_card
class TSC_210e:
    tags = {
        GameTag.CARDNAME: "Illuminated",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


class TSC_211:
    """Whispers of the Deep"""

    # Silence a friendly minion, then deal damage equal to its Attack
    # randomly split among all enemy minions.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }

    def play(self):
        target = self.target
        if target is None:
            return
        atk = target.atk
        yield Silence(target)
        if atk > 0:
            yield Hit(RANDOM(ENEMY_MINIONS), 1) * atk


class TSC_215:
    """Serpent Wig"""

    # Give a minion +1/+1. If you played a Naga while holding this, add a
    # Serpent Wig to your hand.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        Buff(TARGET, "TSC_215e"),
        (Attr(SELF, "nagas_played_while_holding") > 0) & Give(CONTROLLER, "TSC_215"),
    )


TSC_215e = buff(atk=1, health=1)


class TSC_702:
    """Switcheroo"""

    # Draw 2 minions. Swap their stats.
    def play(self):
        controller = self.controller
        before = len(controller.hand)
        yield Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION))
        yield Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MINION))
        drawn = [c for c in controller.hand[before:]]
        if len(drawn) == 2:
            a, b = drawn
            a_atk, a_hp = a.atk, a.max_health
            b_atk, b_hp = b.atk, b.max_health
            yield Buff(a, "TSC_702e", atk=b_atk - a_atk, max_health=b_hp - a_hp)
            yield Buff(b, "TSC_702e", atk=a_atk - b_atk, max_health=a_hp - b_hp)


TSC_702e = buff()


class TSC_775:
    """Azsharan Ritual"""

    # Silence a minion and summon a copy of it. Put a 'Sunken Ritual' on
    # the bottom of your deck.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        Silence(TARGET),
        Summon(CONTROLLER, Copy(TARGET)),
        PutOnBottom(CONTROLLER, "TSC_775t"),
    )


class TSC_775t:
    """Sunken Ritual"""

    # Silence a minion and summon 2 copies of it.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        Silence(TARGET),
        Summon(CONTROLLER, Copy(TARGET)) * 2,
    )


##
# Minions


class TSC_212:
    """Handmaiden"""

    # Battlecry: If you've cast three spells while holding this, draw 3 cards.
    play = (Attr(SELF, "spells_cast_while_holding") >= 3) & (Draw(CONTROLLER) * 3)


class TSC_213:
    """Queensguard"""

    # Battlecry: Gain +1/+1 for each spell you've cast this turn.
    play = Buff(
        SELF,
        "TSC_213e",
        atk=Count(CARDS_PLAYED_THIS_TURN + SPELL),
        max_health=Count(CARDS_PLAYED_THIS_TURN + SPELL),
    )


TSC_213e = buff()


class TSC_216:
    """Blackwater Behemoth"""

    # Colossal +1. Lifesteal.
    pass


class TSC_216t:
    """Behemoth's Lure"""

    # At the end of your turn, force a random enemy minion to attack
    # the Blackwater Behemoth. Approximation: at end of turn, queue an
    # attack from a random enemy minion against the parent if alive.
    events = OWN_TURN_END.on(
        Find(FRIENDLY_MINIONS + ID("TSC_216"))
        & Find(ENEMY_MINIONS)
        & Attack(
            RANDOM(ENEMY_MINIONS),
            FRIENDLY_MINIONS + ID("TSC_216"),
        )
    )


class TSC_828:
    """Priestess Valishj"""

    # Battlecry: Refresh an empty Mana Crystal for each spell you've cast
    # this turn.
    play = GainEmptyMana(CONTROLLER, Count(CARDS_PLAYED_THIS_TURN + SPELL))
