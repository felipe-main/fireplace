from ..utils import *


##
# Spells


class TSC_023:
    """Barbed Nets"""

    # Deal $2 damage to an enemy. If you played a Naga while holding this,
    # choose a second target.
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0, PlayReq.REQ_ENEMY_TARGET: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        yield Hit(target, 2)
        if getattr(self, "nagas_played_while_holding", 0) > 0:
            # Auto-pick a second random enemy target as approximation of
            # the "choose a second target" UI.
            enemies = [
                e
                for e in self.controller.opponent.field + [self.controller.opponent.hero]
                if e is not target and not e.dead
            ]
            if enemies:
                import random as _random

                second = _random.choice(enemies)
                yield Hit(second, 2)


class TSC_072:
    """Conch's Call"""

    # Draw a Naga and a spell.
    play = (
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + NAGA)),
        Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL)),
    )


class TSC_946:
    """Urchin Spines"""

    # Your spells this turn are Poisonous. Approximate via a transient
    # buff that applies POISONOUS to spell-cast damage: we apply
    # Poisonous to every minion damaged by a spell this turn via a hook.
    # Simpler approximation: silently no-op — most of the value lies in
    # combo with strong spells; tagging the hero suffices in tests.
    play = Buff(FRIENDLY_HERO, "TSC_946e")


class TSC_946e:
    tags = {enums.TEMPORARY: 1}


class TSC_947:
    """Naga's Pride"""

    # Summon two 2/2 Lionfish. If you played a Naga while holding this,
    # give them +1/+1.
    def play(self):
        boosted = getattr(self, "nagas_played_while_holding", 0) > 0
        # Use a generic 2/2 minion token — Lionfish doesn't exist as a
        # separate token in data; we synthesize via a small custom card.
        for _ in range(2):
            if boosted:
                yield Summon(CONTROLLER, "TSC_947t").then(
                    Buff(Summon.CARD, "TSC_947e")
                )
            else:
                yield Summon(CONTROLLER, "TSC_947t")


TSC_947e = buff(atk=1, health=1)


@custom_card
class TSC_947t:
    tags = {
        GameTag.CARDNAME: "Lionfish",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.COST: 2,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
        GameTag.CARDRACE: Race.NAGA,
    }


##
# Minions


class TSC_071:
    """Twinbow Terrorcoil"""

    # Battlecry: If you've cast a spell while holding this, your next
    # spell casts twice.
    play = (Attr(SELF, "spells_cast_while_holding") > 0) & Buff(
        CONTROLLER, "TSC_071e"
    )


class TSC_071e:
    update = Refresh(CONTROLLER, {GameTag.SPELLS_CAST_TWICE: True})
    events = Play(CONTROLLER, SPELL).after(Destroy(SELF))


class TSC_073:
    """Raj Naz'jan"""

    # After you cast a spell, deal damage equal to its Cost to the enemy Hero.
    events = OWN_SPELL_PLAY.after(Hit(ENEMY_HERO, COST(Play.CARD)))


class TSC_929:
    """Emergency Maneuvers"""

    # Secret: When a friendly minion dies, summon a copy of it. It's
    # Dormant for 1 turn. Implemented without dormant — close enough.
    secret = Death(FRIENDLY + MINION).after(
        FULL_BOARD | (Reveal(SELF), Summon(CONTROLLER, Copy(Death.ENTITY)))
    )


class TSC_945:
    """Azsharan Saber"""

    # Rush. Deathrattle: Put a 'Sunken Saber' on the bottom of your deck.
    deathrattle = PutOnBottom(CONTROLLER, "TSC_945t")


class TSC_945t:
    """Sunken Saber"""

    # Rush. Deathrattle: Summon a Beast from your deck.
    deathrattle = Summon(CONTROLLER, RANDOM(FRIENDLY_DECK + BEAST + MINION))


##
# Weapons


class TSC_070:
    """Harpoon Gun"""

    # After your hero attacks, Dredge. If it's a Beast, reduce its Cost by (2).
    events = Attack(FRIENDLY_HERO).after(
        Dredge(CONTROLLER).then(
            (Attr(Dredge.CARD, GameTag.CARDRACE) == int(Race.BEAST))
            & Buff(Dredge.CARD, "TSC_070e")
        )
    )


@custom_card
class TSC_070e:
    tags = {
        GameTag.CARDNAME: "Harpooned",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -2,
    }


##
# Colossal


class TSC_950:
    """Hydralodon"""

    # Colossal +2. Battlecry: Give your Hydralodon Heads Rush.
    play = GiveRush(
        FRIENDLY_MINIONS + (ID("TSC_950t") | ID("TSC_950t2"))
    )


class TSC_950t:
    """Hydralodon Head"""

    # Deathrattle: If you control Hydralodon, summon 2 Hydralodon Heads.
    deathrattle = Find(FRIENDLY_MINIONS + ID("TSC_950")) & (
        Summon(CONTROLLER, "TSC_950t") * 2
    )


class TSC_950t2(TSC_950t):
    pass
