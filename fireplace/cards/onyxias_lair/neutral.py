from ..utils import *


##
# Minions


class ONY_001:
    """Onyxian Warder"""

    # <b>Battlecry:</b> If you're holding a Dragon, summon two 2/1 Whelps
    # with <b>Rush</b>.
    play = HOLDING_DRAGON & (Summon(CONTROLLER, "ONY_001t") * 2)


class ONY_002:
    """Gear Grubber"""

    # <b>Taunt</b>. If you end your turn with any unspent mana, reduce this
    # card's Cost by (1). Trigger lives on the in-hand zone so the cost
    # reduction sticks before the card is played.
    class Hand:
        events = OWN_TURN_END.on(
            (
                Attr(CONTROLLER, GameTag.RESOURCES_USED)
                < Attr(CONTROLLER, GameTag.RESOURCES)
            )
            & Buff(SELF, "ONY_002e")
        )


class ONY_002e:
    tags = {GameTag.COST: -1}


class ONY_003:
    """Whelp Bonker"""

    # <b>Frenzy</b> and <b>Honorable Kill:</b> Draw a card.
    frenzy = Draw(CONTROLLER)
    honorable_kill = Draw(CONTROLLER)


def _is_whelp(entity, source):
    """A Whelp is any minion whose printed name contains 'Whelp'. This
    matches Hearthstone's canonical interpretation for Raid Boss Onyxia's
    immunity check."""
    data = getattr(entity, "data", None)
    if data is None:
        return False
    name = getattr(data, "name", "") or ""
    return "Whelp" in name


_FRIENDLY_WHELPS = FuncSelector(
    lambda entities, source: [
        e
        for e in entities
        if getattr(e, "controller", None) is source.controller
        and getattr(e, "zone", None) == Zone.PLAY
        and getattr(e, "type", None) == CardType.MINION
        and _is_whelp(e, source)
    ]
)


class ONY_004:
    """Raid Boss Onyxia"""

    # <b>Rush</b>. <b>Immune</b> while you control a Whelp. <b>Battlecry:</b>
    # Summon six 2/1 Whelps with <b>Rush</b>.
    play = Summon(CONTROLLER, "ONY_001t") * 6
    update = Find(_FRIENDLY_WHELPS) & Refresh(
        SELF,
        {
            GameTag.CANT_BE_DAMAGED: True,
            GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
        },
    )


# Kazakusan — best-effort approximation. The real card replaces your deck
# with a hand-picked set of 30 Treasures chosen through a UI; we shuffle a
# fixed sample of fully-scripted treasures into the deck when the gating
# condition (all deck minions are Dragons) is met.
KAZAKUSAN_TREASURES = (
    "ONY_005ta1",   # Necrotic Poison
    "ONY_005ta2",   # Mutating Injection
    "ONY_005ta4",   # Pure Cold
    "ONY_005ta6",   # Holy Book
    "ONY_005ta7",   # Crusty the Crustacean
    "ONY_005ta8",   # Looming Presence
    "ONY_005ta10",  # Spyglass
    "ONY_005ta11",  # Clockwork Assistant
    "ONY_005tb2",   # Gnomish Army Knife
    "ONY_005tb4",   # Wand of Disintegration
    "ONY_005tb5",   # Staff of Scales
    "ONY_005tb9",   # Banana Split
    "ONY_005tb14",  # Vampiric Fangs
    "ONY_005tc1",   # Embers of Ragnaros
    "ONY_005tc6",   # Hilt of Quel'Delar
)


class ONY_005:
    """Kazakusan"""

    # <b>Battlecry:</b> If all minions in your deck are Dragons, craft a
    # custom deck of Treasures.
    def play(self):
        controller = self.controller
        deck_minions = [c for c in controller.deck if c.type == CardType.MINION]
        if deck_minions and all(Race.DRAGON in c.races for c in deck_minions):
            for treasure_id in KAZAKUSAN_TREASURES:
                yield Shuffle(CONTROLLER, treasure_id)


# Treasures — only the few we actually shuffle in have scripts. The rest
# remain unscripted (vanilla/cosmetic) and will simply do nothing if drawn
# via some other path.


class ONY_005ta1:
    """Necrotic Poison"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Destroy(TARGET)


class ONY_005ta2:
    """Mutating Injection"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "ONY_005ta2e")


ONY_005ta2e = buff(atk=4, health=4, taunt=True)


class ONY_005ta4:
    """Pure Cold"""

    play = Hit(ENEMY_HERO, 8), Freeze(ENEMY_HERO)


class ONY_005ta8:
    """Looming Presence"""

    play = Draw(CONTROLLER) * 2, GainArmor(FRIENDLY_HERO, 4)


class ONY_005ta10:
    """Spyglass"""

    play = Give(CONTROLLER, Copy(RANDOM(ENEMY_HAND))).then(
        Buff(Give.CARD, "ONY_005ta10e")
    )


class ONY_005ta10e:
    tags = {GameTag.COST: -3}


class ONY_005tb2:
    """Gnomish Army Knife"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        GiveRush(TARGET),
        GiveWindfury(TARGET),
        GiveDivineShield(TARGET),
        GiveLifesteal(TARGET),
        GivePoisonous(TARGET),
        Taunt(TARGET),
    )


class ONY_005tb4:
    """Wand of Disintegration"""

    play = Silence(ENEMY_MINIONS), Destroy(ENEMY_MINIONS)


class ONY_005tb9:
    """Banana Split"""

    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = (
        Buff(TARGET, "ONY_005tb9e"),
        Summon(CONTROLLER, Copy(TARGET)) * 2,
    )


ONY_005tb9e = buff(atk=2, health=2)


class ONY_005tc1:
    """Embers of Ragnaros"""

    play = Hit(RANDOM_ENEMY_CHARACTER, 8) * 3


class ONY_005ta6:
    """Holy Book"""

    # Silence and destroy a minion. Summon a 10/10 copy of it.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        target_id = target.id
        yield Silence(target)
        yield Destroy(target)
        yield Summon(CONTROLLER, target_id).then(Buff(Summon.CARD, "ONY_005ta6e"))


ONY_005ta6e = buff(atk=10, health=10)


class ONY_005ta7:
    """Crusty the Crustacean"""

    # Battlecry: Destroy a minion. Gain its Attack and Health.
    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }

    def play(self):
        target = self.target
        if target is None:
            return
        atk = target.atk
        hp = target.health
        yield Destroy(target)
        yield Buff(SELF, "ONY_005ta7e", atk=atk, max_health=hp)


ONY_005ta7e = buff()


class ONY_005ta11:
    """Clockwork Assistant"""

    # Has +1/+1 for each spell you've cast this game.
    # On play: apply the back-buff for every spell already cast.
    # While on board: stack +1/+1 per future spell cast.
    play = Buff(
        SELF,
        "ONY_005ta11e",
        atk=Count(CARDS_PLAYED_THIS_GAME + SPELL),
        max_health=Count(CARDS_PLAYED_THIS_GAME + SPELL),
    )
    events = OWN_SPELL_PLAY.after(Buff(SELF, "ONY_005ta11e2"))


# Patch 23.4 removed both `ONY_005ta11e` and `ONY_005ta11e2` from
# hearthstone_data, but Clockwork Assistant still references them at runtime
# (Buff(SELF, "ONY_005ta11e", ...) + the on-spell-cast +1/+1). Register
# both as custom cards so the lookup succeeds.


@custom_card
class ONY_005ta11e:
    tags = {
        GameTag.CARDNAME: "Clockwork Assistant Tally",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class ONY_005ta11e2:
    tags = {
        GameTag.CARDNAME: "Clockwork Assistant Boost",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
    }


class ONY_005tb5:
    """Staff of Scales"""

    # Summon three 1/1 Snakes with Rush, Poisonous and Reborn.
    play = Summon(CONTROLLER, "ONY_005tb5t") * 3


class ONY_005tb5t:
    """Ancient Snake"""


class ONY_005tb14:
    """Vampiric Fangs"""

    # Destroy a minion. Restore its Health to your hero.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        heal_amount = target.max_health
        yield Destroy(target)
        yield Heal(FRIENDLY_HERO, heal_amount)


class ONY_005tc6:
    """Hilt of Quel'Delar"""

    # Give a minion +3/+3.
    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "ONY_005tc6e")


ONY_005tc6e = buff(atk=3, health=3)
