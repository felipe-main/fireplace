from ..utils import *


##
# Spells


class TID_708:
    """Polymorph: Jellyfish"""

    # Transform a minion into a 4/1 Jellyfish with Spell Damage +2.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Morph(TARGET, "TID_708t")


class TID_708t:
    """Jellyfish"""

    # 3-cost 4/1 with Spell Damage +2.
    tags = {GameTag.SPELLPOWER: 2}


##
# Minions


class TID_707:
    """Submerged Spacerock"""

    # Deathrattle: Add two Arcane Mage spells to your hand. At the end of
    # your turn, discard them. (Two random Arcane Mage spells joined with
    # the "discards at end of owner turn" marker.)
    def deathrattle(self):
        for _ in range(2):
            yield _SpacerockGive(self.controller)


class _SpacerockGive(TargetedAction):
    """Give the player a random Arcane Mage spell and stamp it with the
    end-of-turn-discard marker so end_turn_cleanup removes it."""

    TARGET = ActionArg()

    def do(self, source, target):
        picker = RandomCardPicker(
            card_class=CardClass.MAGE,
            type=CardType.SPELL,
            spell_school=SpellSchool.ARCANE,
        )
        result = picker.evaluate(source)
        if not result:
            return
        if isinstance(result, (list, tuple)):
            if not result:
                return
            card_id = result[0]
        else:
            card_id = result
        card = target.card(card_id, source=source)
        card.zone = Zone.HAND
        card.discards_at_end_of_owner_turn = True


def _naz_jar_transform_target(spell, source):
    """Pick the Naz'jar transform variant matching the just-cast school.
    Fire → TID_709t2, Frost → TID_709t3, Arcane → TID_709t. Anything else
    returns None to suppress the morph."""
    school = getattr(spell, "spell_school", None)
    if school is None:
        return None
    s = int(school)
    if s == int(SpellSchool.ARCANE):
        return "TID_709t"
    if s == int(SpellSchool.FIRE):
        return "TID_709t2"
    if s == int(SpellSchool.FROST):
        return "TID_709t3"
    return None


class _NazjarTransformInHand(TargetedAction):
    """Hand-side morph for Lady Naz'jar.

    When the controller casts a Fire/Frost/Arcane spell while Naz'jar is in
    hand, replace her with the matching transform variant. The spell that
    just resolved is the second element of the broadcast event_args.
    """

    TARGET = ActionArg()

    def do(self, source, target):
        args = source.event_args or []
        spell = args[1] if len(args) >= 2 else None
        if spell is None:
            return
        new_id = _naz_jar_transform_target(spell, target)
        if new_id is None:
            return
        source.game.queue_actions(target, [Morph(target, new_id)])


class TID_709:
    """Lady Naz'jar"""

    # While in your hand, this transforms after you cast a Fire, Frost, or
    # Arcane spell.
    class Hand:
        events = OWN_SPELL_PLAY.on(_NazjarTransformInHand(SELF))


class TID_709t:
    """Lady Naz'jar"""

    # Battlecry: Reduce the Cost of spells in your hand by (2).
    play = Buff(FRIENDLY_HAND + SPELL, "TID_709e")


class TID_709e:
    tags = {GameTag.COST: -2}


class TID_709t2:
    """Lady Naz'jar"""

    # Battlecry: Deal 5 damage to an enemy minion and 2 to all others.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        yield Hit(self.target, 5)
        yield Hit(ENEMY_MINIONS - TARGET, 2)


class TID_709t3:
    """Lady Naz'jar"""

    # Battlecry: Gain 8 Armor.
    play = GainArmor(FRIENDLY_HERO, 8)
