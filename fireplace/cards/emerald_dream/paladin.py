from ..utils import *


##
# Custom actions


class _DragonscaleDraw(TargetedAction):
    """Dragonscale Armaments — draw a spell that started in your deck and one
    that didn't. ``_started_in_deck`` is stamped at game setup (True for cards
    that began in the deck/opening hand, False for everything generated later),
    so the two buckets are exactly "started here" vs "didn't"."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spells = [
            c
            for c in ctrl.deck
            if c.type == CardType.SPELL
        ]
        started = [c for c in spells if getattr(c, "_started_in_deck", False)]
        not_started = [c for c in spells if not getattr(c, "_started_in_deck", False)]
        rng = source.game.random
        picks = []
        if started:
            picks.append(rng.choice(started))
        if not_started:
            picks.append(rng.choice(not_started))
        for card in picks:
            source.game.cheat_action(source, [ForceDraw(card)])


class _DreamwardenDraw(TargetedAction):
    """Dreamwarden — if there is a card in your deck that didn't start there,
    draw it and gain +2/+2. A deck card with ``_started_in_deck`` False is one
    that was shuffled in after game start."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        candidates = [
            c
            for c in ctrl.deck
            if not getattr(c, "_started_in_deck", False)
        ]
        if not candidates:
            return
        card = source.game.random.choice(candidates)
        source.game.cheat_action(
            source, [ForceDraw(card), Buff(source, "EDR_256e")]
        )


class _TorethReinforce(TargetedAction):
    """Toreth the Unbreaking — "Your Divine Shields take three hits to break."
    The engine strips a Divine Shield on the first hit (LosesDivineShield). We
    re-grant it up to two more times per minion so it survives a total of three
    hits. Per-minion hit count lives on ``_toreth_shield_hits``."""

    TARGET = ActionArg()

    def do(self, source, target):
        hits = getattr(target, "_toreth_shield_hits", 0) + 1
        target._toreth_shield_hits = hits
        if hits < 3:
            # Re-apply the shield: this hit didn't break it for good.
            source.game.cheat_action(source, [SetTag(target, GameTag.DIVINE_SHIELD)])


def _ursol_cast(source, ctrl, spell_id):
    """Cast a fresh copy of Ursol's stored spell at a random valid target."""
    card = ctrl.card(spell_id, source=source)
    card.zone = Zone.PLAY
    if card.targets:
        spell_target = source.game.random.choice(card.targets)
        source.game.cheat_action(source, [CastSpell(card, spell_target)])
    else:
        source.game.cheat_action(source, [CastSpell(card)])


class _UrsolAura(TargetedAction):
    """Ursol — cast the highest Cost spell from your hand as an Aura that lasts
    3 turns: at the end of each of your next 3 turns, re-cast that spell. We
    capture the spell id at battlecry time and attach a self-ticking host
    enchant to the hero that recasts a fresh copy each end of turn."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spells = [c for c in ctrl.hand if c.type == CardType.SPELL]
        if not spells:
            return
        spell = max(spells, key=lambda c: c.cost)
        spell_id = spell.id
        # The spell is consumed from hand — the aura recasts fresh copies.
        spell.zone = Zone.GRAVEYARD
        host = ctrl.hero
        buff = source.buff(host, "EDR_259host")
        buff._ursol_spell_id = spell_id
        # The aura casts the stored spell at the end of each of your next 3
        # turns ("lasts 3 turns").
        buff._ursol_turns_left = 3


class _UrsolTick(TargetedAction):
    """End-of-turn tick for Ursol's Aura host: re-cast the stored spell and
    decrement the remaining-turns counter, removing the host when spent."""

    TARGET = ActionArg()

    def do(self, source, target):
        spell_id = getattr(target, "_ursol_spell_id", None)
        if spell_id is None:
            return
        _ursol_cast(source, target.controller, spell_id)
        target._ursol_turns_left -= 1
        if target._ursol_turns_left <= 0:
            target.remove()


##
# Minions


class EDR_256:
    """Dreamwarden"""

    # Taunt. Battlecry: If there is a card in your deck that didn't start there,
    # draw it and gain +2/+2.
    play = _DreamwardenDraw(SELF)


class EDR_257:
    """Lightmender"""

    # Taunt. Choose One - +3 Attack and Divine Shield; or +3 Health and
    # Lifesteal.
    choose = ("EDR_257a", "EDR_257b")
    play = ChooseBoth(CONTROLLER) & (
        (Buff(SELF, "EDR_257ae"), SetTag(SELF, GameTag.DIVINE_SHIELD)),
        Buff(SELF, "EDR_257be"),
    )


class EDR_257a:
    """Holy Bond"""

    # +3 Attack and Divine Shield. Choose-One sub-card: buffs Lightmender itself.
    play = Buff(SELF, "EDR_257ae"), SetTag(SELF, GameTag.DIVINE_SHIELD)


class EDR_257b:
    """Embrace of the Light"""

    # +3 Health and Lifesteal. Choose-One sub-card: buffs Lightmender itself.
    play = Buff(SELF, "EDR_257be")


class EDR_258:
    """Toreth the Unbreaking"""

    # Divine Shield, Taunt. Your Divine Shields take three hits to break.
    # When a friendly minion loses its Divine Shield, re-grant it until it has
    # taken three hits.
    events = LosesDivineShield(FRIENDLY_MINIONS).after(
        _TorethReinforce(LosesDivineShield.TARGET)
    )


class EDR_259:
    """Ursol"""

    # Battlecry: Cast the highest Cost spell from your hand as an Aura that
    # lasts 3 turns.
    play = _UrsolAura(SELF)


class EDR_451:
    """Goldpetal Drake"""

    # Battlecry and Deathrattle: Imbue your Hero Power.
    play = Imbue(CONTROLLER)
    deathrattle = Imbue(CONTROLLER)


##
# Weapons


class EDR_253:
    """Ursine Maul"""

    # After your hero attacks, draw your highest Cost card.
    events = Attack(FRIENDLY_HERO).after(
        ForceDraw(RANDOM(HIGHEST_COST(FRIENDLY_DECK)))
    )


##
# Spells


class EDR_251:
    """Dragonscale Armaments"""

    # Draw a spell that started in your deck and one that didn't.
    play = _DragonscaleDraw(CONTROLLER)


class EDR_252:
    """Mark of Ursol"""

    # Choose a minion. If it's an enemy, set its stats to 1/1. If it's
    # friendly, set its stats to 3/3 instead.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (
        Buff(TARGET + ENEMY, "EDR_252e"),
        Buff(TARGET + FRIENDLY, "EDR_252e1"),
    )


class EDR_255:
    """Renewing Flames"""

    # Lifesteal. Deal $5 damage to the lowest Health enemy, twice.
    play = Hit(LOWEST_HEALTH(ENEMY_CHARACTERS), 5) * 2


class EDR_264:
    """Aegis of Light"""

    # Summon a random 1-Cost minion and give it Taunt. Imbue your Hero Power.
    play = (
        Summon(CONTROLLER, RandomMinion(cost=1)).then(
            SetTags(Summon.CARD, {GameTag.TAUNT: True})
        ),
        Imbue(CONTROLLER),
    )


##
# Enchantments


class EDR_256e:
    # Portalmancy — +2/+2.
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2}


class EDR_257ae:
    # Holy Bonded — +3 Attack and Divine Shield.
    tags = {GameTag.ATK: 3, GameTag.DIVINE_SHIELD: True}


class EDR_257be:
    # Light's Embrace — +3 Health and Lifesteal.
    tags = {GameTag.HEALTH: 3, GameTag.LIFESTEAL: True}


class EDR_252e:
    # Mark of Ursol — stats set to 1/1.
    atk = SET(1)
    max_health = SET(1)


class EDR_252e1:
    # Might of Ursol — stats set to 3/3.
    atk = SET(3)
    max_health = SET(3)


@custom_card
class EDR_259host:
    # Engine-internal host for Ursol's Aura. Lives on the caster's hero and
    # re-casts the stored spell at the end of each of the next 3 turns.
    tags = {
        GameTag.CARDNAME: "Ursol's Aura",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(_UrsolTick(SELF))
