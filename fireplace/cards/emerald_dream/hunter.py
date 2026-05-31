from ..utils import *


##
# Into the Emerald Dream — HUNTER collectible cards.


class EDR_014:
    """Verdant Dreamsaber"""

    # Battlecry: If this costs (3) or less, attack two random enemy minions.
    play = (COST(SELF) <= 3) & (
        Attack(SELF, RANDOM(ENEMY_MINIONS)),
        Attack(SELF, RANDOM(ENEMY_MINIONS)),
    )


class EDR_226:
    """Exotic Houndmaster"""

    # Battlecry: Draw a Beast. Imbue your Hero Power.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + BEAST)), Imbue(CONTROLLER)


class EDR_227:
    """Umbraclaw"""

    # Rush
    # Deathrattle: Imbue your Hero Power.
    deathrattle = Imbue(CONTROLLER)


class EDR_261:
    """Amphibian's Spirit"""

    # Give a minion +2/+2 and "Deathrattle: Give a friendly minion +2/+2
    # and this Deathrattle."
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Buff(TARGET, "EDR_261e")


class EDR_261e:
    """Amphibian's Spirit"""

    # +2/+2 and Deathrattle: Give a friendly minion +2/+2 and this Deathrattle.
    # The deathrattle re-applies this very enchant, so the granted Deathrattle
    # propagates to the next host (each new minion gains +2/+2 and the rattle).
    # DEATHRATTLE=True makes the host's has_deathrattle aggregate this enchant's
    # deathrattle script (data ships +2/+2 but not the DEATHRATTLE flag).
    tags = {GameTag.ATK: 2, GameTag.HEALTH: 2, GameTag.DEATHRATTLE: True}
    deathrattle = Buff(RANDOM(FRIENDLY_MINIONS), "EDR_261e")


class EDR_262:
    """Spirit Bond"""

    # Deal $3 damage to a minion. If that kills it, summon a 3/2 Wolf with Rush.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = Hit(TARGET, 3), Dead(TARGET) & Summon(CONTROLLER, "EDR_262t")


@custom_card
class EDR_262t:
    """Wolf"""

    # 3/2 with Rush. (Token summoned by Spirit Bond / Grace of the Greatwolf.)
    # Not present in CardXML for this build, so registered as a custom card.
    tags = {
        GameTag.CARDNAME: "Wolf",
        GameTag.CARDTYPE: CardType.MINION,
        GameTag.CARDRACE: Race.BEAST,
        GameTag.ATK: 3,
        GameTag.HEALTH: 2,
        GameTag.RUSH: True,
    }


class EDR_263:
    """Grace of the Greatwolf"""

    # Choose One - Deal $4 damage to the enemy hero; or Summon two 3/2 Wolves
    # with Rush.
    choose = ("EDR_263a", "EDR_263b")
    play = ChooseBoth(CONTROLLER) & (
        Hit(ENEMY_HERO, 4),
        Summon(CONTROLLER, "EDR_262t") * 2,
    )


class EDR_263a:
    """Greatwolf's Ferocity"""

    # Deal $4 damage to the enemy hero.
    play = Hit(ENEMY_HERO, 4)


class EDR_263b:
    """Greatwolf's Guidance"""

    # Summon two 3/2 Wolves with Rush.
    play = Summon(CONTROLLER, "EDR_262t") * 2


class EDR_416:
    """Shepherd's Crook"""

    # After your hero attacks, summon a 3/3 Sheep that's Dormant for 2 turns.
    events = Attack(FRIENDLY_HERO).after(
        Summon(CONTROLLER, "EDR_416t").then(Dormant(Summon.CARD, 2))
    )


class EDR_416t:
    """Sleepy Sheep"""

    # 3/3. Dormant for 2 turns. (Dormant applied by Shepherd's Crook.)


class EDR_480:
    """Goldrinn"""

    # Rush. Friendly Beasts deal double damage.
    # Modelled as an aura doubling friendly Beasts' Attack (the dominant
    # source of a Beast's damage); triggered-ability damage is not doubled
    # by this engine (no source-side damage hook is exposed to scripts).
    # The printed text reads "Friendly Beasts" with no "other", so Goldrinn
    # (itself a Beast) is included — its own Attack doubles too.
    update = Refresh(FRIENDLY_MINIONS + BEAST, buff="EDR_480e")


@custom_card
class EDR_480e:
    # Goldrinn — doubled Attack (aura from Goldrinn). Not in CardXML, so
    # registered as a custom enchantment carrying the atk-doubling script.
    tags = {
        GameTag.CARDNAME: "Goldrinn",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    atk = lambda self, i: i * 2


class EDR_481:
    """Mythical Runebear"""

    # Taunt. Battlecry: If this has 4 or more Attack, summon a copy of this.
    play = (Attr(SELF, GameTag.ATK) >= 4) & Summon(CONTROLLER, ExactCopy(SELF))


class EDR_853:
    """Broll Bearmantle"""

    # After you cast a spell, summon a random Animal Companion.
    entourage = ["NEW1_032", "NEW1_033", "NEW1_034"]
    events = OWN_SPELL_PLAY.after(Summon(CONTROLLER, RandomEntourage()))
