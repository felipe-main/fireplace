from ..utils import *


##
# Spells


class TSC_055:
    """Seafloor Gateway"""

    # Draw a Mech. Reduce the Cost of Mechs in your hand by (1).
    play = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + MECH)),
        Buff(FRIENDLY_HAND + MECH, "TSC_055e"),
    )


class TSC_055e:
    tags = {GameTag.COST: -1}


class TSC_056:
    """Volcanomancy"""

    # Choose a minion. When it dies, deal 3 damage to all other minions.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "TSC_056e")


class TSC_056e:
    tags = {GameTag.DEATHRATTLE: True}
    deathrattle = Hit(ALL_MINIONS - SELF, 3)


class TSC_948:
    """Gifts of Azshara"""

    # Draw a card. If you played a Naga while holding this, do it again.
    def play(self):
        yield Draw(CONTROLLER)
        if getattr(self, "nagas_played_while_holding", 0) > 0:
            yield Draw(CONTROLLER)


##
# Minions


class TSC_029:
    """Gaia, the Techtonic"""

    # Colossal +2. After a friendly Mech attacks, deal 1 damage to all enemies.
    events = Attack(FRIENDLY_MINIONS + MECH).after(Hit(ENEMY_CHARACTERS, 1))


class TSC_054:
    """Mecha-Shark"""

    # After you summon a Mech, deal 3 damage randomly split among all enemies.
    events = Summon(CONTROLLER, MECH).after(Hit(RANDOM_ENEMY_CHARACTER, 1) * 3)


class TSC_087(ThreeSpellsProgressUtils):
    """Commander Sivara"""

    # Battlecry: If you've cast three spells while holding this, add
    # those spells back to your hand.
    def play(self):
        history = getattr(self, "spells_history_while_holding", [])
        if len(history) < 3:
            return
        for card_id, _cost in history[:3]:
            yield Give(CONTROLLER, card_id)


def _siren_naga_fires(entities, source):
    """Naga-mode listener gate: fires when the Siren's current mode is
    'naga'. Also flips the mode to 'spell' for the next trigger."""
    if getattr(source, "siren_mode", "naga") != "naga":
        return []
    source.siren_mode = "spell"
    return [source]


def _siren_spell_fires(entities, source):
    """Spell-mode listener gate: mirror of _siren_naga_fires."""
    if getattr(source, "siren_mode", "naga") != "spell":
        return []
    source.siren_mode = "naga"
    return [source]


class TSC_620:
    """Spitelash Siren"""

    # After you play a Naga, refresh two Mana Crystals. (Then switch to spell!)
    # After you cast a spell, refresh two Mana Crystals. (Then switch to Naga!)
    # The Siren starts in "naga" mode — the first Naga play triggers, then
    # the mode flips to "spell"; the first spell after that triggers, etc.
    events = [
        Play(CONTROLLER, MINION + NAGA).after(
            Find(FuncSelector(_siren_naga_fires))
            & ManaThisTurn(CONTROLLER, 2)
        ),
        OWN_SPELL_PLAY.after(
            Find(FuncSelector(_siren_spell_fires))
            & ManaThisTurn(CONTROLLER, 2)
        ),
    ]


class TSC_642:
    """Trench Surveyor"""

    # Battlecry: Dredge. If it's a Mech, draw it.
    play = Dredge(CONTROLLER).then(
        (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.MECHANICAL))
        & ForceDraw(Dredge.CARD)
    )


class TSC_643:
    """Spellcoiler"""

    # Battlecry: If you've cast a spell while holding this, Discover a spell.
    play = (Attr(SELF, "spells_cast_while_holding") > 0) & DISCOVER(RandomSpell())


class TSC_776:
    """Azsharan Sweeper"""

    # Battlecry: Put a 'Sunken Sweeper' on the bottom of your deck.
    play = PutOnBottom(CONTROLLER, "TSC_776t")


class TSC_776t:
    """Sunken Sweeper"""

    # Battlecry: Add 3 random Mechs to your hand.
    play = Give(CONTROLLER, RandomMinion(race=Race.MECHANICAL)) * 3
