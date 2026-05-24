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


class ONY_004:
    """Raid Boss Onyxia"""

    # <b>Rush</b>. <b>Immune</b> while you control a Whelp. <b>Battlecry:</b>
    # Summon six 2/1 Whelps with <b>Rush</b>.
    play = Summon(CONTROLLER, "ONY_001t") * 6
    update = Find(FRIENDLY_MINIONS + ID("ONY_001t")) & Refresh(
        SELF,
        {
            GameTag.CANT_BE_DAMAGED: True,
            GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
        },
    )


# Kazakusan — best-effort approximation. The real card replaces your deck
# with a hand-picked set of 30 Treasures via UI. We shuffle a fixed sample
# of treasures into the deck when the gating condition (all deck minions are
# Dragons) is met.
KAZAKUSAN_TREASURES = (
    "ONY_005ta1",   # Necrotic Poison
    "ONY_005ta2",   # Mutating Injection
    "ONY_005ta4",   # Pure Cold
    "ONY_005ta8",   # Looming Presence
    "ONY_005ta10",  # Spyglass
    "ONY_005tb2",   # Gnomish Army Knife
    "ONY_005tb4",   # Wand of Disintegration
    "ONY_005tb9",   # Banana Split
    "ONY_005tc1",   # Embers of Ragnaros
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
