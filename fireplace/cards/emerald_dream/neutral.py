from ..utils import *

from hearthstone.enums import CardType, SpellSchool, Rarity, Race

from ..delve_into_deepholm._bonus import roll_bonus_effects


##
# Into the Emerald Dream — neutral collectibles.
#
# Two recurring custom mechanics handled here:
#
#   * "Dark Gift" — the printed cards grant a minion a random "Dark Gift"
#     (a Nightmare bonus). The data ships a single `EDR_102t` "Dark Gift"
#     spell that "executes nightmare bonus" entirely script-side; the per-gift
#     enchant pool is not enumerated as discrete card ids. We model a Dark Gift
#     as a random keyword Bonus Effect (the eight-keyword pool used by the
#     Delve into Deepholm "Bonus Effect" minions). This is a faithful-shape
#     approximation: a Dark Gift is always granted, it is random, and it is a
#     strict upgrade. See `_GiveDarkGift`.
#
#   * "Imbue your Hero Power" — provided by the engine stage as the
#     `Imbue(CONTROLLER)` action plus the per-game `imbues_this_game` counter.
#     Payoffs gate on that counter.


class _GiveDarkGift(TargetedAction):
    """Give the target minion a random Dark Gift (modelled as a random
    keyword Bonus Effect from the eight-keyword Nightmare pool)."""

    TARGET = ActionArg()

    def do(self, source, target):
        targets = target if isinstance(target, (list, tuple)) else [target]
        for t in targets:
            tags = roll_bonus_effects(source.game.random, 1)
            source.game.cheat_action(source, [SetTags(t, tags)])
            # Record each granted gift on the recipient so cards that read a
            # minion's accumulated Dark Gifts (Wallow EDR_487, Overgrown Horror
            # EDR_654) can observe them. Stored as a list of the tag-dicts.
            t._dark_gifts = getattr(t, "_dark_gifts", []) + [tags]


##
# Minions


class EDR_000:
    """Ysera, Emerald Aspect"""

    # Start of Game: Increase both players' maximum Mana by 5.
    # Battlecry: Gain 3 Mana Crystals.
    def start_of_game(self):
        yield GainMana(CONTROLLER, 5)
        yield GainMana(OPPONENT, 5)

    play = GainMana(CONTROLLER, 3)


class EDR_001:
    """Hopeful Dryad"""

    # Battlecry: Get a random Dream card.
    # The five Dream cards (DREAM_01..05) are non-collectible & non-standard,
    # so disable both default filters when rolling the pool.
    play = Give(CONTROLLER, RandomCard(
        is_standard=None,
        custom_filter=lambda c: c.id in (
            "DREAM_01", "DREAM_02", "DREAM_03", "DREAM_04", "DREAM_05",
        )
    ))


class EDR_102:
    """Treacherous Tormentor"""

    # Battlecry: Discover a Legendary minion with a Dark Gift.
    play = Discover(
        CONTROLLER,
        RandomMinion(rarity=Rarity.LEGENDARY),
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))


class EDR_105:
    """Creature of Madness"""

    # Battlecry: Discover a 3-Cost minion with a Dark Gift.
    play = Discover(
        CONTROLLER,
        RandomMinion(cost=3),
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))


class EDR_110:
    """Sporegnasher"""

    # Poisonous. Deathrattle: Deal 1 damage to a random enemy minion.
    deathrattle = Hit(RANDOM(ENEMY_MINIONS), 1)


class EDR_254:
    """Animated Moonwell"""

    # After you cast a spell, gain Attack equal to its Cost.
    events = OWN_SPELL_PLAY.on(
        Buff(SELF, "EDR_254e1", atk=COST(Play.CARD))
    )


class EDR_260:
    """Illusory Greenwing"""

    # Taunt. Deathrattle: Shuffle two 4/5 Dragons with Taunt into your deck.
    # They're Summoned When Drawn.
    deathrattle = Shuffle(CONTROLLER, "EDR_260t") * 2


class EDR_260t:
    """Illusion"""

    # Summoned When Drawn. Taunt. (4/5 Dragon — stats in data.)
    # Summon SELF straight onto the board: Summon moves this card's zone from
    # HAND to PLAY, so exactly one 4/5 Taunt Dragon enters play and no leftover
    # copy stays in hand (matches Frost Tyrant TTN_083t's idiom).
    draw = Summon(CONTROLLER, SELF)


class EDR_453:
    """Briarspawn Drake"""

    # At the end of your turn, attack a random enemy minion
    # (excess damage hits the enemy hero).
    events = OWN_TURN_END.on(Attack(SELF, RANDOM(ENEMY_MINIONS)))


class EDR_469:
    """Slumbering Sprite"""

    # Starts Dormant. After you use your Hero Power, this awakens.
    # No fixed turn count: it stays Dormant until a Hero Power awakens it, so
    # we mark it Dormant via the data tag (read by Card._set_zone on entering
    # PLAY) rather than `dormant_turns` (which would auto-awaken on a timer).
    tags = {GameTag.DORMANT: True}
    dormant_events = Activate(FRIENDLY_HERO_POWER).after(Awaken(SELF))


class EDR_470:
    """Barkshield Sentinel"""

    # Taunt. After you use your Hero Power, gain +2 Health.
    # EDR_470e ("Alert") carries no stat tags in data — supply +2 Health.
    events = Activate(FRIENDLY_HERO_POWER).after(
        Buff(SELF, "EDR_470e", max_health=2)
    )


class EDR_484:
    """Scavenging Flytrap"""

    # After a minion dies, gain its Attack.
    events = Death(MINION).on(
        lambda self, target: Buff(self, "EDR_484e", atk=target.atk)
    )


class EDR_486:
    """Scorching Observer"""

    # Rush, Lifesteal — keywords are in data; nothing to script.


class EDR_492:
    """Mother Duck"""

    # Battlecry: Summon three 1/1 Ducklings with Rush.
    play = Summon(CONTROLLER, "EDR_492t") * 3


class EDR_492t:
    """Duckling"""

    # 1/1 with Rush (in data).


class EDR_495:
    """Twisted Treant"""

    # Deathrattle: Give a random minion in each player's hand -2 Attack.
    # EDR_495e ("Twisted") carries no stat tags in data — supply -2 Attack.
    deathrattle = (
        Buff(RANDOM(FRIENDLY_HAND + MINION), "EDR_495e", atk=-2),
        Buff(RANDOM(ENEMY_HAND + MINION), "EDR_495e", atk=-2),
    )


class EDR_530:
    """Daydreaming Pixie"""

    # At the end of your turn, get a random Nature spell.
    events = OWN_TURN_END.on(
        Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.NATURE))
    )


class EDR_571:
    """Fae Trickster"""

    # Deathrattle: Draw a spell that costs (5) or more.
    deathrattle = Draw(CONTROLLER, RANDOM(FRIENDLY_DECK + SPELL + (COST >= 5)))


class EDR_572:
    """Tormented Dreadwing"""

    # Deathrattle: Draw 2 Dragons. Reduce their Costs by (1).
    deathrattle = Draw(
        CONTROLLER, RANDOM(FRIENDLY_DECK + DRAGON)
    ).then(Buff(Draw.CARD, "EDR_572e")) * 2


@custom_card
class EDR_572e:
    # Tormented Dreadwing — drawn Dragon costs (1) less.
    tags = {
        GameTag.CARDNAME: "Tormented Dreadwing",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -1,
    }


class EDR_598:
    """Dream Rager"""

    # Elusive — can't be targeted by spells or Hero Powers. The data ships the
    # consolidated GameTag.ELUSIVE (1211), which the engine's targeting check
    # honors directly, so no scripting is required.


class EDR_780:
    """Bloodthistle Illusionist"""

    # Battlecry: Summon a copy of this. One secretly dies when it takes damage.
    # We model "summon a copy of this"; the secret-death twin is cosmetic in
    # this engine (both copies are real minions).
    play = Summon(CONTROLLER, ExactCopy(SELF))


class EDR_800:
    """Flutterwing Guardian"""

    # Taunt, Divine Shield. Battlecry: Imbue your Hero Power.
    play = Imbue(CONTROLLER)


class EDR_844:
    """Naralex, Herald of the Flights"""

    # Your Dragons cost (1).
    update = Refresh(FRIENDLY_HAND + DRAGON, {GameTag.COST: SET(1)})


class _ShaladrassilWatch(TargetedAction):
    """Shaladrassil — mark that a higher-Cost card was played while holding."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._played_higher_cost = True


class EDR_846:
    """Shaladrassil"""

    # Get all 5 Dream cards. If you've played a higher Cost card while holding
    # this, corrupt them!
    def play(self):
        if getattr(self, "_played_higher_cost", False):
            ids = (
                "EDR_846t1", "EDR_846t2", "EDR_846t3", "EDR_846t4", "EDR_846t5",
            )
        else:
            ids = ("DREAM_01", "DREAM_02", "DREAM_03", "DREAM_04", "DREAM_05")
        for cid in ids:
            yield Give(CONTROLLER, cid)

    class Hand:
        # Play broadcast args are (player, card, target, index, choose); the
        # played card is args[1]. Mark when a higher-Cost card is played while
        # Shaladrassil sits in hand.
        events = OWN_CARD_PLAY.on(
            lambda self, player, card, *rest: _ShaladrassilWatch(SELF)
            if card is not self and (card.cost or 0) > (self.cost or 0)
            else None
        )


class EDR_849:
    """Dreambound Raptor"""

    # After you play a minion, give it a random Bonus Effect.
    events = OWN_MINION_PLAY.on(_GiveDarkGift(Play.CARD))


class EDR_852:
    """Bitterbloom Knight"""

    # Battlecry: Imbue your Hero Power.
    play = Imbue(CONTROLLER)


class EDR_856:
    """Nightmare Lord Xavius"""

    # Battlecry: Discover a minion from your deck. Give it a Dark Gift.
    # Deck-Discover: offer up to three DISTINCT deck minions as preview copies
    # (Barrens "Discover from your deck" idiom). The chosen copy enters hand;
    # apply the Dark Gift to it.
    play = GenericChoice(
        CONTROLLER, RANDOM(DeDuplicate(FRIENDLY_DECK + MINION)) * 3
    ).then(_GiveDarkGift(GenericChoice.CARD))


class EDR_860:
    """Resplendent Dreamweaver"""

    # Lifesteal. Battlecry: If you've Imbued your Hero Power twice, deal 4
    # damage to a minion.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = (Attr(CONTROLLER, "imbues_this_game") >= 2) & Hit(TARGET, 4)


class EDR_861:
    """Tranquil Treant"""

    # Deathrattle: Both players gain an empty Mana Crystal.
    deathrattle = (
        GainEmptyMana(CONTROLLER, 1),
        GainEmptyMana(OPPONENT, 1),
    )


class EDR_873:
    """Envoy of the Glade"""

    # Battlecry: Transform all Neutral cards in your deck into random Druid ones.
    # "Druid ones" means random COLLECTIBLE Druid cards — RandomCollectible
    # injects collectible=True so the pool can't roll non-collectible Druid
    # tokens / hero powers / enchants.
    play = Morph(
        FRIENDLY_DECK + NEUTRAL,
        RandomCollectible(card_class=CardClass.DRUID),
    )


class EDR_888:
    """Malorne the Waywatcher"""

    # Battlecry: Discover a Legendary Wild God. If you've Imbued your Hero
    # Power 4 times, set its Cost to (1).
    def play(self):
        picker = RandomMinion(
            is_standard=None,
            custom_filter=lambda c: bool(c.tags.get(4065)),
        )
        if self.controller.imbues_this_game >= 4:
            yield Discover(CONTROLLER, picker).then(
                Give(CONTROLLER, Discover.CARD).then(Buff(Give.CARD, "EDR_888e"))
            )
        else:
            yield Discover(CONTROLLER, picker).then(
                Give(CONTROLLER, Discover.CARD)
            )


@custom_card
class EDR_888e:
    # Malorne — set discovered Wild God's Cost to (1).
    cost = SET(1)
    tags = {
        GameTag.CARDNAME: "Malorne the Waywatcher",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class EDR_889:
    """Petal Peddler"""

    # At the end of your turn, give another random friendly Dragon +1/+1.
    # EDR_889e ("Flowery") carries no stat tags in data — supply +1/+1.
    events = OWN_TURN_END.on(
        Buff(RANDOM((FRIENDLY_MINIONS - SELF) + DRAGON), "EDR_889e",
             atk=1, max_health=1)
    )


class EDR_942:
    """Curious Cumulus"""

    # At the end of your turn, give your hero Divine Shield.
    events = OWN_TURN_END.on(
        SetTags(FRIENDLY_HERO, {GameTag.DIVINE_SHIELD: True})
    )


class EDR_971:
    """Critter Caretaker"""

    # At the end of your turn, restore 3 Health to both heroes.
    events = OWN_TURN_END.on(Heal(FRIENDLY_HERO, 3), Heal(ENEMY_HERO, 3))


class EDR_978:
    """Meadowstrider"""

    # Taunt. Deathrattle: Put a Meadowstrider on the bottom of your deck.
    # It costs (1).
    def deathrattle(self):
        copy = self.controller.card("EDR_978", source=self)
        yield PutOnBottom(CONTROLLER, copy).then(Buff(copy, "EDR_978e"))


@custom_card
class EDR_978e:
    # Meadowstrider — the deck copy costs (1).
    cost = SET(1)
    tags = {
        GameTag.CARDNAME: "Meadowstrider",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


class EDR_979:
    """Ancient of Yore"""

    # Dormant for 2 turns. While Dormant, gain 5 Armor and draw a card at the
    # end of your turn.
    # EDR_979's data omits the DORMANT tag, so declare it here (like Gorm) —
    # otherwise _set_zone leaves it awake and the dormant_events never fire.
    tags = {GameTag.DORMANT: True}
    dormant_turns = 2
    dormant_events = OWN_TURN_END.on(GainArmor(FRIENDLY_HERO, 5), Draw(CONTROLLER))


class EDR_999:
    """Gnawing Greenfin"""

    # Battlecry: Get a random Murloc.
    play = Give(CONTROLLER, RandomMurloc())


class EDR_004:
    """Raptor Herald"""

    # Battlecry: Discover a Beast with a Dark Gift.
    play = Discover(
        CONTROLLER,
        RandomMinion(race=Race.BEAST),
    ).then(Give(CONTROLLER, Discover.CARD).then(_GiveDarkGift(Give.CARD)))
