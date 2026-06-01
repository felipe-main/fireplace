from ..utils import *

from hearthstone.enums import CardClass, CardType, GameTag, Zone

from ._smolder import _SmolderTick, smolder_level


##
# Custom actions


class _QonzuKeepOrGive(TargetedAction):
    """Q'onzu — after Discovering a spell, offer a binary choice: keep the
    spell (it enters your hand) or put it on top of your opponent's deck.

    The engine's plain ``Discover`` only opens the three-card pick; it does
    not give the chosen card anywhere by itself (callers ``Give`` it). So we
    take the already-chosen spell here and re-open a two-option
    ``GenericChoice`` between the real spell card (= keep) and a marker token
    (= send to opponent). A small subclass of GenericChoice branches on which
    one was picked."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        if not isinstance(card, list):
            card = [card] if card else []
        if not card:
            return
        spell = card[0]
        marker = source.controller.card("EDR_517t", source=source)
        marker._qonzu_spell = spell
        choice = _QonzuChoice(source.controller, [spell, marker])
        source.game.queue_actions(source, [choice])


class _QonzuChoice(GenericChoice):
    def choose(self, card):
        spell = None
        marker = None
        for c in self.cards:
            if getattr(c, "_qonzu_spell", None) is not None:
                marker = c
                spell = c._qonzu_spell
        # Always discard the marker; it is never kept.
        if card is marker:
            # Send the discovered spell to the top of the opponent's deck.
            self.player.choice = None
            marker.discard()
            self.source.game.queue_actions(
                self.source, [PutOnTop(self.player.opponent, spell)]
            )
        else:
            # Keep the spell: standard GenericChoice behaviour (spell -> hand,
            # everything else discarded).
            super().choose(card)


##
# Minions


class EDR_430:
    """Aessina"""

    # [x]<b>Battlecry:</b> If 20 friendly minions have died this game,
    # deal 20 damage split among all enemies.
    play = (Attr(CONTROLLER, "friendly_minions_died_this_game") >= 20) & (
        Hit(RANDOM(ENEMY_CHARACTERS), 1) * 20
    )


class EDR_517:
    """Q'onzu"""

    # <b>Battlecry:</b> <b>Discover</b> a spell. Choose to keep it or
    # put it on top of your opponent's deck.
    play = Discover(CONTROLLER, RandomSpell()).then(
        _QonzuKeepOrGive(CONTROLLER, Discover.CARD)
    )


@custom_card
class EDR_517t:
    # Engine-internal marker for Q'onzu's "put on opponent's deck" option.
    tags = {
        GameTag.CARDNAME: "Put on Opponent's Deck",
        GameTag.CARDTYPE: CardType.SPELL,
    }


class EDR_519:
    """Wisprider"""

    # <b>Battlecry:</b> <b>Imbue</b> your Hero Power, then trigger it.
    # Mage's Imbued Hero Power (Blessing of the Wisp, EDR_851p) is
    # untargeted; its `activate` ignores the target, so we pass the friendly
    # hero as a harmless placeholder (PlayHeroPower requires a TARGET arg).
    play = Imbue(CONTROLLER).then(
        PlayHeroPower(FRIENDLY_HERO_POWER, FRIENDLY_HERO)
    )


class EDR_871:
    """Spirit Gatherer"""

    # <b>Battlecry:</b> Get a Wisp. <b>Imbue</b> your Hero Power.
    play = Give(CONTROLLER, "EDR_851t"), Imbue(CONTROLLER)


class EDR_940:
    """Merry Moonkin"""

    # [x]At the end of your turn, gain @ Armor. (Improved by Wisps you
    # control!)  Base 1 Armor, +1 for each Wisp you control.
    events = OWN_TURN_END.on(
        GainArmor(
            FRIENDLY_HERO,
            Count(FRIENDLY_MINIONS + ID("EDR_851t")) + 1,
        )
    )


##
# Spells


class EDR_804:
    """Divination"""

    # Destroy a friendly Wisp to draw 3 cards.
    #
    # "a friendly Wisp" is a card-NAME restriction: Wisp tokens span Undead
    # (EDR_851t) and raceless (CS2_231) variants, so no Race filter is faithful.
    # Uses the custom REQ_TARGET_WITH_CARD_NAME PlayReq (param = "Wisp").
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_CARD_NAME: "Wisp",
    }
    play = Destroy(TARGET), Draw(CONTROLLER) * 3


class EDR_872:
    """Spark of Life"""

    # <b>Choose One -</b> <b>Discover</b> a Mage spell; or <b>Discover</b>
    # a Druid spell.
    choose = ("EDR_872A", "EDR_872B")
    play = ChooseBoth(CONTROLLER) & (
        DISCOVER(RandomSpell(card_class=CardClass.MAGE)),
        DISCOVER(RandomSpell(card_class=CardClass.DRUID)),
    )


class EDR_872A:
    """Gift of Fire"""

    # <b>Discover</b> a Mage spell.
    play = DISCOVER(RandomSpell(card_class=CardClass.MAGE))


class EDR_872B:
    """Gift of Nature"""

    # <b>Discover</b> a Druid spell.
    play = DISCOVER(RandomSpell(card_class=CardClass.DRUID))


class EDR_874:
    """Stellar Balance"""

    # Get a Moonfire and a Starfire. Give them <b>Spell Damage +1</b>.
    # The +1 Spell Damage rider is the in-data enchant EDR_874e. As of the Lost
    # City engine pass, Player.get_spell_damage reads the cast spell's own
    # SPELLPOWER tag, so the rider now correctly adds +1 at cast time (Moonfire
    # deals 2, Starfire 6).
    play = (
        Give(CONTROLLER, "CS2_008").then(Buff(Give.CARD, "EDR_874e")),
        Give(CONTROLLER, "EX1_173").then(Buff(Give.CARD, "EDR_874e")),
    )


class EDR_874e:
    # In-data enchant "Stellar Balance" — Spell Damage +1. Data XML carries no
    # SPELLPOWER tag, so declare it here for fidelity.
    tags = {GameTag.SPELLPOWER: 1}


class EDR_941:
    """Starsurge"""

    # Deal $@ damage to a minion. (Improved by each friendly minion that died
    # this game.)  Base 1 damage, +1 per friendly minion that has died.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(
        TARGET,
        Attr(CONTROLLER, "friendly_minions_died_this_game") + 1,
    )


##
# Locations


class EDR_520:
    """Forbidden Shrine"""

    # [x]Spend all your Mana. Cast a random spell that costs that much.
    activate = SpendMana(CONTROLLER, CURRENT_MANA(CONTROLLER)).then(
        CastSpell(RandomSpell(cost=SpendMana.AMOUNT))
    )


##
# Firelands mini-set (FIR_)


class _ScorchingWindsDiscard(TargetedAction):
    """Scorching Winds (FIR_910) — discard a random Fire spell from the
    caster's hand; if one was actually discarded, deal 3 more damage to the
    spell's target.

    A plain ``Discard(RANDOM(FRIENDLY_HAND + SPELL + FIRE_SPELL))`` cannot gate
    the bonus damage on whether a Fire spell existed (the chained ``Hit`` would
    fire even when nothing was discarded). So we resolve the candidate here,
    discard it, and only then queue the extra 3 damage on the original target.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        # `target` is the original damage target, threaded through unchanged.
        candidates = (FRIENDLY_HAND + SPELL + FIRE_SPELL).eval(
            source.game, source
        )
        if not candidates:
            return
        spell = source.game.random.choice(candidates)
        source.game.queue_actions(source, [Discard(spell)])
        if target is not None and not getattr(target, "dead", False):
            source.game.queue_actions(source, [Hit(target, 3)])


class FIR_910:
    """Scorching Winds"""

    # Deal $3 damage. Discard a random Fire spell to deal $3 more.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
    }
    play = Hit(TARGET, 3), _ScorchingWindsDiscard(TARGET)


class FIR_911:
    """Smoldering Grove"""

    # Draw {0} card(s). (Upgrades each turn, but discards after {1}!)
    #
    # Smoldering: while held, {0} rises by 1 at the start of each of your
    # turns and the card is discarded after a few turns. The exact {0}/{1}
    # values are server-resolved (not in CardXML) — we use the package
    # default (base 1, +1 per turn, discard after 3). Flagged as an
    # approximation (same class as the other Smoldering cards).
    class Hand:
        events = OWN_TURN_BEGIN.on(_SmolderTick(SELF))

    def play(self):
        yield Draw(CONTROLLER) * smolder_level(self, base=1)


class FIR_913:
    """Inferno Herald"""

    # [x]After you cast a Fire spell, get a random Elemental and
    # reduce its Cost by (3).
    events = Play(CONTROLLER, SPELL + FIRE_SPELL).on(
        Give(CONTROLLER, RandomElemental()).then(Buff(Give.CARD, "FIR_913e"))
    )


@custom_card
class FIR_913e:
    # Inferno Herald's cost reducer (not in CardXML) — reduce the gifted
    # Elemental's Cost by 3.
    tags = {
        GameTag.CARDNAME: "Inferno Herald",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }
