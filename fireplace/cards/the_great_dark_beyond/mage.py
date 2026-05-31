from ..utils import *

from hearthstone.enums import CardType, SpellSchool


##
# Custom actions


class _ArmIngeniousArtificer(TargetedAction):
    """Ingenious Artificer — the next Draenei you play refreshes Mana Crystals
    equal to its Attack."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game

        def hook(played):
            game.cheat_action(
                played, [ManaThisTurn(played.controller, max(0, played.atk))]
            )

        source.controller.next_draenei_hooks.append(hook)


class _PocketDimension(TargetedAction):
    """Pocket Dimension — Discover a spell, repeating until a spell already
    taken is offered (seen for the second time)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if getattr(source, "_pocket_seen", None) is None:
            source._pocket_seen = set()
        source.game.queue_actions(
            source,
            [
                Discover(ctrl, RandomSpell()).then(
                    Give(CONTROLLER, Discover.CARD),
                    _PocketDimensionStep(source, Discover.CARD),
                )
            ],
        )


class _PocketDimensionStep(TargetedAction):
    TARGET = ActionArg()
    CARD = ActionArg()

    def do(self, source, target, card):
        if isinstance(card, (list, tuple)):
            card = card[0] if card else None
        if card is None:
            return
        seen = source._pocket_seen
        if card.id in seen:
            return
        seen.add(card.id)
        source.game.queue_actions(source, [_PocketDimension(source)])


class _FillHandFireSpells(TargetedAction):
    """Supernova — fill your hand with random Fire spells that cost (1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        while len(ctrl.hand) < ctrl.max_hand_size:
            before = len(ctrl.hand)
            source.game.cheat_action(
                source, [Give(ctrl, RandomSpell(spell_school=SpellSchool.FIRE))]
            )
            if len(ctrl.hand) <= before:
                break
            # "They cost (1)": set, not reduce — apply the per-card delta.
            card = ctrl.hand[-1]
            source.game.cheat_action(
                source, [Buff(card, "GDB_301e", cost=1 - card.cost)]
            )


class _BlazingAccretion(TargetedAction):
    """Blazing Accretion — destroy the top 3 cards of your deck; Fire spells
    and Elementals among them are drawn instead."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        top = list(ctrl.deck)[-3:]
        for card in reversed(top):
            is_fire = (
                card.type == CardType.SPELL
                and card.spell_school is not None
                and int(card.spell_school) == int(SpellSchool.FIRE)
            )
            is_elem = Race.ELEMENTAL in getattr(card, "races", [])
            if is_fire or is_elem:
                source.game.cheat_action(source, [Draw(ctrl, card)])
            else:
                card.zone = Zone.GRAVEYARD


class _ColossusBlast(TargetedAction):
    """Colossus — deal damage to all enemies, twice, where the amount equals
    the number of Protoss spells you've cast this game."""

    TARGET = ActionArg()

    def do(self, source, target):
        amount = source.controller.protoss_spells_cast_this_game
        if amount <= 0:
            return
        source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, amount)])
        source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, amount)])


class _ArmShieldBattery(TargetedAction):
    """Shield Battery — your next Protoss spell costs (2) less."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.next_protoss_spell_discount += 2


class _GiveRandomProtossSpell(TargetedAction):
    """Resonance Coil — get a random Protoss spell."""

    TARGET = ActionArg()

    def do(self, source, target):
        from .. import db as _db

        pool = [
            cid
            for cid, c in _db.items()
            if c.collectible
            and c.type == CardType.SPELL
            and c.tags.get(GameTag.PROTOSS, 0)
        ]
        if not pool:
            return
        source.game.cheat_action(
            source, [Give(source.controller, source.game.random.choice(pool))]
        )


##
# Minions


class GDB_134:
    """Arkwing Pilot"""

    # At the end of your turn, deal 3 damage to a random enemy. Spellburst:
    # Summon an Arkwing Pilot.
    events = OWN_TURN_END.on(Hit(RANDOM(ENEMY_CHARACTERS), 3))
    spellburst = Summon(CONTROLLER, "GDB_134")


class GDB_135:
    """Ingenious Artificer"""

    # Battlecry: The next Draenei you play refreshes Mana Crystals equal to
    # its Attack.
    play = _ArmIngeniousArtificer(SELF)


class _MarkHataaru(TargetedAction):
    """Tag the discovered spell so that playing it THIS turn repeats Exarch
    Hataaru's Discover (engine hook in Play.do re-runs the source's play)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        target._hataaru_source = source
        target._hataaru_turn = source.game.turn


class GDB_136:
    """Exarch Hataaru"""

    # Battlecry: Discover a spell and reduce its Cost by (1). If you play it
    # this turn, repeat this effect.
    play = Discover(CONTROLLER, RandomSpell()).then(
        Give(CONTROLLER, Discover.CARD),
        Buff(Discover.CARD, "GDB_136e2"),
        _MarkHataaru(Discover.CARD),
    )


class GDB_302:
    """Blazing Accretion"""

    # Battlecry: Destroy the top 3 cards of your deck. Any Fire spells or
    # Elementals are drawn instead.
    play = _BlazingAccretion(SELF)


class GDB_303:
    """Blasteroid"""

    # Battlecry: Shuffle 5 random Fire spells into your deck. They cost (2)
    # less.
    play = Shuffle(
        CONTROLLER, RandomSpell(spell_school=SpellSchool.FIRE)
    ).then(Buff(Shuffle.CARD, "GDB_303e")) * 5


class GDB_304:
    """Saruun"""

    # Battlecry: Give all Elementals in your deck Fire Spell Damage +1.
    play = Buff(FRIENDLY_DECK + ELEMENTAL, "GDB_304e")


##
# Spells


class GDB_133:
    """Pocket Dimension"""

    # Discover a spell. Repeat until you see one for the second time.
    play = _PocketDimension(SELF)


class GDB_301:
    """Supernova"""

    # Fill your hand with random Fire spells. They cost (1).
    play = _FillHandFireSpells(SELF)


class GDB_305:
    """Solar Flare"""

    # Deal $2 damage to all enemies. Costs (1) less for each Elemental you
    # control.
    cost_mod = -Count(FRIENDLY + ELEMENTAL + MINION + IN_PLAY)
    play = Hit(ENEMY_CHARACTERS, 2)


class GDB_456:
    """Spontaneous Combustion"""

    # Deal $4 damage to a random enemy. If you played an Elemental last turn,
    # choose the target. (Targeting requirement comes from data.)
    def play(self):
        if self.target is not None:
            yield Hit(self.target, 4)
        else:
            yield Hit(RANDOM(ENEMY_CHARACTERS), 4)


##
# Heroes of StarCraft — Protoss (Mage)


class SC_758:
    """Colossus"""

    # Battlecry: Deal @ damage to all enemies, twice. (@ = the number of
    # Protoss spells you've cast this game.)
    play = _ColossusBlast(SELF)


class SC_759:
    """Shield Battery"""

    # Gain 6 Armor. Your next Protoss spell costs (2) less.
    play = GainArmor(FRIENDLY_HERO, 6), _ArmShieldBattery(SELF)


class SC_760:
    """Resonance Coil"""

    # Deal $5 damage to a minion. Get a random Protoss spell.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 5), _GiveRandomProtossSpell(SELF)


##
# Enchantments


@custom_card
class GDB_301e:
    # Supernova — Fire spell costs (1). The COST delta is supplied per-card via
    # the `cost=` buff kwarg (1 - card.cost), so the base tag is a placeholder.
    tags = {
        GameTag.CARDNAME: "Supernova",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: 0,
    }


@custom_card
class GDB_303e:
    # Blasteroid — Fire spell costs (2) less.
    tags = {
        GameTag.CARDNAME: "Blasteroid",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


class GDB_304e:
    # Heat of Saruun — Fire Spell Damage +1.
    tags = {GameTag.SPELLPOWER_FIRE: 1}


@custom_card
class GDB_136e2:
    # Exarch Hataaru — discovered spell costs (1) less.
    tags = {
        GameTag.CARDNAME: "Exarch Hataaru",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }
