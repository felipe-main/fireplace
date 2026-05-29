from ..utils import *


# "From another class" / "non-your-class" selectors used by several Rogue
# cards. OTHER_CLASS (in utils via dsl) already means "neither Neutral nor
# the controller's hero class". For Sea Shill ("non-Rogue class") we also
# want to include Neutral cards, so we use a dedicated selector that only
# excludes the controller's own hero class.
NON_OWN_CLASS = FuncSelector(
    lambda entities, source: [
        e
        for e in entities
        if getattr(e, "card_class", CardClass.INVALID)
        != getattr(source.controller.hero, "card_class", CardClass.INVALID)
    ]
)

# Playable classes excluding the controller's, for "from another class"
# Discover/random pools.
_PLAYABLE_CLASSES = [
    CardClass.DEATHKNIGHT,
    CardClass.DEMONHUNTER,
    CardClass.DRUID,
    CardClass.HUNTER,
    CardClass.MAGE,
    CardClass.PALADIN,
    CardClass.PRIEST,
    CardClass.ROGUE,
    CardClass.SHAMAN,
    CardClass.WARLOCK,
    CardClass.WARRIOR,
]
FOREIGN_CLASS = FuncSelector(
    lambda entities, source: [
        cc
        for cc in _PLAYABLE_CLASSES
        if cc != getattr(source.controller.hero, "card_class", CardClass.INVALID)
    ]
)


##
# Custom actions


class _KnickknackDraw(TargetedAction):
    """Knickknack Shack activate — draw a card and remember it on the
    location so that, if the controller plays that exact card this turn,
    the location reopens (cooldown cleared)."""

    TARGET = ActionArg()

    def do(self, source, target):
        before = set(id(c) for c in target.hand)
        target.draw()
        drawn = [c for c in target.hand if id(c) not in before]
        source._knickknack_card = drawn[0] if drawn else None
        source.game.manager.targeted_action(self, source, target)


class _KnickknackCheck(TargetedAction):
    """If the played card is the one Knickknack Shack just drew, reopen the
    location (clear its cooldown) and forget the tracked card."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        if card is not None and card is getattr(target, "_knickknack_card", None):
            target._knickknack_card = None
            source.game.queue_actions(source, [ReopenLocation(target)])
        source.game.manager.targeted_action(self, source, target, card)


class _BubbaSummon(TargetedAction):
    """Bubba — summon six 1/1 Bloodhounds with Rush, each attacking an enemy
    minion (GILA_400t is a 1/1 Bloodhound with Rush)."""

    TARGET = ActionArg()

    def do(self, source, target):
        for _ in range(6):
            if len(target.field) >= source.game.MAX_MINIONS_ON_FIELD:
                break
            source.game.cheat_action(source, [Summon(target, "GILA_400t")])
            hound = target.field[-1]
            enemies = [m for m in target.opponent.field if not m.dead]
            if enemies:
                victim = source.game.random.choice(enemies)
                source.game.cheat_action(source, [Attack(hound, victim)])


class _AncientReflections(TargetedAction):
    """Ancient Reflections — fill the board with 1/1 copies of the chosen
    minion."""

    TARGET = ActionArg()

    def do(self, source, target):
        if target is None:
            return
        controller = source.controller
        while len(controller.field) < source.game.MAX_MINIONS_ON_FIELD:
            source.game.cheat_action(source, [Summon(controller, target.id)])
            copy = controller.field[-1]
            copy.atk = 1
            copy.max_health = 1
            copy.damage = 0
        source.game.manager.targeted_action(self, source, target)


class _FillAnnoying(TargetedAction):
    """Annoy-o Horn — fill the board with annoying minions (1/2 Annoy-o-Tron
    copies stand in for the 'annoying minions' pool)."""

    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        while len(controller.field) < source.game.MAX_MINIONS_ON_FIELD:
            source.game.cheat_action(source, [Summon(controller, "GVG_085")])
            source.game.manager.targeted_action(self, source, target)


##
# Weapons


# After your hero attacks and kills a minion, get a Coin.
class VAC_330:
    """Metal Detector"""

    events = Attack(FRIENDLY_HERO, MINION).after(
        Dead(Attack.DEFENDER) & Give(CONTROLLER, "GAME_005")
    )


##
# Minions


# Battlecry: The next card you play from a non-Rogue class costs (2) less.
class VAC_332:
    """Sea Shill"""

    play = Buff(CONTROLLER, "VAC_332e")


# The next card you play from a non-Rogue class costs (2) less. Carrier aura
# on the player; reduces the next non-Rogue-class hand card by 2, and is
# consumed the moment such a card is played.
class VAC_332e:
    update = Refresh(FRIENDLY_HAND + NON_OWN_CLASS, {GameTag.COST: -2})
    events = Play(CONTROLLER, NON_OWN_CLASS).on(Destroy(SELF))


# Battlecry: Replay the last card you've played from another class.
class VAC_333:
    """Conniving Conman"""

    play = Replay(
        Copy(
            FuncSelector(
                lambda entities, source: [
                    c
                    for c in source.controller.cards_played_this_game
                    if getattr(c, "card_class", CardClass.INVALID)
                    not in (
                        CardClass.NEUTRAL,
                        getattr(
                            source.controller.hero, "card_class", CardClass.INVALID
                        ),
                    )
                ][-1:]
            )
        )
    )


# Draw a card. If you play it this turn, reopen this.
class VAC_334:
    """Knickknack Shack"""

    activate = _KnickknackDraw(CONTROLLER)
    events = Play(CONTROLLER).after(_KnickknackCheck(SELF, Play.CARD))


# Get two random 1-Cost spells from other classes.
class VAC_335:
    """Petty Theft"""

    play = (
        Give(CONTROLLER, RandomSpell(cost=1, card_class=FOREIGN_CLASS)),
        Give(CONTROLLER, RandomSpell(cost=1, card_class=FOREIGN_CLASS)),
    )


# Warlock Tourist. Battlecry: Discover a Hero card from the past (from
# another class). (Tourist is deckbuilding-only; we implement the Battlecry.)
class VAC_336:
    """Maestra, Mask Merchant"""

    play = DISCOVER(
        RandomCard(
            type=CardType.HERO,
            collectible=True,
            card_class=FOREIGN_CLASS,
        )
    )


##
# Spells


# Deal $2 damage. Combo: Get a coin.
class VAC_460:
    """Oh, Manager!"""

    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Hit(TARGET, 2)
    combo = Hit(TARGET, 2), Give(CONTROLLER, "GAME_005")


# Battlecry: Go on a Sidequest to Discover amazing loot! Play 3 cards from
# other classes to complete it.
class VAC_464:
    """Treasure Hunter Eudora"""

    play = Summon(CONTROLLER, "VAC_464t")


# Eudora's loot pool — the "amazing pieces of loot" Discovered as the
# sidequest reward. Excludes the helper sub-tokens (t27t / t31t) which are
# only reachable via transformation/forging, not the reward pool.
_EUDORA_LOOT = [
    "VAC_464t2",
    "VAC_464t3",
    "VAC_464t4",
    "VAC_464t5",
    "VAC_464t6",
    "VAC_464t7",
    "VAC_464t8",
    "VAC_464t9",
    "VAC_464t10",
    "VAC_464t11",
    "VAC_464t12",
    "VAC_464t14",
    "VAC_464t15",
    "VAC_464t16",
    "VAC_464t17",
    "VAC_464t18",
    "VAC_464t19",
    "VAC_464t20",
    "VAC_464t21",
    "VAC_464t22",
    "VAC_464t23",
    "VAC_464t24",
    "VAC_464t25",
    "VAC_464t26",
    "VAC_464t27",
    "VAC_464t28",
    "VAC_464t29",
    "VAC_464t30",
    "VAC_464t31",
]


# Sidequest: Play 3 cards from other classes. Reward: Discover two amazing
# pieces of loot!
class VAC_464t:
    """Eudora's Treasure Hunt"""

    progress_total = 3
    sidequest = Play(CONTROLLER, OTHER_CLASS_CHARACTER).after(
        AddProgress(SELF, Play.CARD)
    )
    reward = Discover(CONTROLLER, RandomID(*_EUDORA_LOOT)).then(
        Give(CONTROLLER, Discover.CARD).then(
            Discover(CONTROLLER, RandomID(*_EUDORA_LOOT)).then(
                Give(CONTROLLER, Discover.CARD)
            )
        )
    )


# Destroy two random enemy minions. Costs (1) less for each card you've
# played from another class.
class VAC_700:
    """Snatch and Grab"""

    cost_mod = -Count(CARDS_PLAYED_THIS_GAME + OTHER_CLASS_CHARACTER)
    play = Destroy(RANDOM(ENEMY_MINIONS) * 2)


# Battlecry: Set the Attack and Durability of your weapon to 3.
class VAC_701:
    """Swarthy Swordshiner"""

    play = Find(FRIENDLY_WEAPON) & Buff(FRIENDLY_WEAPON, "VAC_701e")


# Polished Sheen — Set the weapon's Attack and Durability to 3. The data
# enchant carries no stat tags, so we compute the delta against the weapon's
# base stats at apply time (atk/max_health contributions add onto the base,
# so a raw "+3" would not "set to 3"). The buff stamps the deltas needed to
# land exactly on 3/3.
def _PolishedSheen():
    cls = buff()

    def apply(self, target):
        self._delta_atk = 3 - target.atk
        self._delta_dur = 3 - target.max_durability

    cls.apply = apply
    cls.atk = lambda self, i: i + getattr(self, "_delta_atk", 0)
    cls.max_health = lambda self, i: i + getattr(self, "_delta_dur", 0)
    return cls


VAC_701e = _PolishedSheen()
VAC_701e.__name__ = "VAC_701e"
VAC_701e.__qualname__ = "VAC_701e"
VAC_701e.__doc__ = "Polished Sheen"


##
# Eudora's Treasure (the loot pool). These recreate the Onyxia's Lair "amazing
# loot" cards; implementations mirror the proven ONY_005t* scripts.


# Destroy a minion.
class VAC_464t2:
    """Necrotic Poison"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Destroy(TARGET)


# Give a minion +4/+4 and Taunt.
class VAC_464t3:
    """Mutating Injection"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "VAC_464t3e")


@custom_card
class VAC_464t3e:
    tags = {
        GameTag.CARDNAME: "Mutating Injection",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 4,
        GameTag.HEALTH: 4,
        GameTag.TAUNT: 1,
    }


# The Exorcisor — 1/3/3 weapon. Silence any minion attacked by this weapon.
class VAC_464t4:
    """The Exorcisor"""

    events = Attack(FRIENDLY_HERO, MINION).on(Silence(Attack.DEFENDER))


# Deal $8 damage to the enemy hero, and Freeze it.
class VAC_464t5:
    """Pure Cold"""

    play = Hit(ENEMY_HERO, 8), Freeze(ENEMY_HERO)


# Bubba — 5/8/8 Beast. Battlecry: Summon six 1/1 Bloodhounds with Rush to
# attack an enemy minion.
class VAC_464t6:
    """Bubba"""

    play = _BubbaSummon(CONTROLLER)


# Silence and destroy a minion. Summon a 10/10 copy of it.
class VAC_464t7:
    """Holy Book"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        target_id = target.id
        yield Silence(target)
        yield Destroy(target)
        yield Summon(CONTROLLER, target_id).then(Buff(Summon.CARD, "VAC_464t7e"))


# Set the summoned copy's stats to 10/10 (delta against the copy's base).
@custom_card
class VAC_464t7e:
    tags = {
        GameTag.CARDNAME: "Holy Book",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }

    def apply(self, target):
        self._d_atk = 10 - target.atk
        self._d_health = 10 - target.max_health

    atk = lambda self, i: i + getattr(self, "_d_atk", 0)
    max_health = lambda self, i: i + getattr(self, "_d_health", 0)


# Crusty the Crustacean — 3/3/3 Beast. Battlecry: Destroy a minion. Gain its
# Attack and Health.
class VAC_464t8:
    """Crusty the Crustacean"""

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
        yield Buff(SELF, "VAC_464t8e", atk=atk, max_health=hp)


# Runtime-stamped stat buff (Crusty gains the devoured minion's stats); the
# atk / max_health values are supplied by the Buff call's kwargs.
@custom_card
class VAC_464t8e:
    tags = {
        GameTag.CARDNAME: "Crusty the Crustacean",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


# Draw 2 cards. Gain 4 Armor.
class VAC_464t9:
    """Looming Presence"""

    play = Draw(CONTROLLER) * 2, GainArmor(FRIENDLY_HERO, 4)


# Put a copy of a random card in your opponent's hand into yours. It costs
# (3) less.
class VAC_464t10:
    """Spyglass"""

    play = Give(CONTROLLER, Copy(RANDOM(ENEMY_HAND))).then(
        Buff(Give.CARD, "VAC_464t10e")
    )


@custom_card
class VAC_464t10e:
    tags = {
        GameTag.CARDNAME: "Spyglass",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.COST: -3,
    }


# Clockwork Assistant — 3/1/1. Has +1/+1 for each spell you've cast this game.
class VAC_464t11:
    """Clockwork Assistant"""

    play = Buff(
        SELF,
        "VAC_464t11e",
        atk=Count(CARDS_PLAYED_THIS_GAME + SPELL),
        max_health=Count(CARDS_PLAYED_THIS_GAME + SPELL),
    )
    events = OWN_SPELL_PLAY.after(Buff(SELF, "VAC_464t11e2"))


@custom_card
class VAC_464t11e:
    tags = {
        GameTag.CARDNAME: "Clockwork Assistant Tally",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class VAC_464t11e2:
    tags = {
        GameTag.CARDNAME: "Clockwork Assistant Boost",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 1,
        GameTag.HEALTH: 1,
    }


# Transform all minions into random ones that cost (3) more.
class _PuzzleBoxMorph(TargetedAction):
    """Puzzle Box — transform ALL minions into random ones that cost (3) more,
    each picked independently from its own current cost. If a cost bucket is
    empty, that minion is left unchanged."""

    TARGET = ActionArg()

    def do(self, source, target):
        # Morph each minion into a random one costing its cost + 3. Mark the
        # morph result so a minion is never re-morphed: this play can re-fire
        # off the board change the Morph triggers, and without the guard the
        # already-upgraded minion would morph again (cost+3 a second time).
        for p in source.game.players:
            for minion in list(p.field):
                if minion.zone != Zone.PLAY:
                    continue
                if getattr(minion, "_puzzle_morphed", False):
                    continue
                pick = RandomMinion(cost=(minion.cost or 0) + 3).evaluate(source)
                if isinstance(pick, list):
                    pick = pick[0] if pick else None
                if not pick:
                    continue
                new_card = source.controller.card(pick.id, source=source)
                new_card._puzzle_morphed = True
                source.game.cheat_action(source, [Morph(minion, new_card)])


class VAC_464t12:
    """Puzzle Box"""

    play = _PuzzleBoxMorph(SELF)


# Hyperblaster — 3/1/4 weapon. Poisonous. Your hero is Immune while attacking.
# Poisonous is in the weapon's data tags; the immune-while-attacking is granted
# to the hero via an aura that lasts while the weapon is equipped.
class VAC_464t14:
    """Hyperblaster"""

    update = Refresh(FRIENDLY_HERO, {GameTag.IMMUNE_WHILE_ATTACKING: True})


# Give a minion Rush, Windfury, Divine Shield, Lifesteal, Poisonous, Taunt,
# and Stealth.
class VAC_464t15:
    """Gnomish Army Knife"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = (
        GiveRush(TARGET),
        GiveWindfury(TARGET),
        GiveDivineShield(TARGET),
        GiveLifesteal(TARGET),
        GivePoisonous(TARGET),
        Taunt(TARGET),
        Stealth(TARGET),
    )


# Silence and destroy all enemy minions.
class VAC_464t16:
    """Wand of Disintegration"""

    play = Silence(ENEMY_MINIONS), Destroy(ENEMY_MINIONS)


# Summon three 1/1 Snakes with Rush, Poisonous and Reborn.
class VAC_464t17:
    """Staff of Scales"""

    play = (
        Summon(CONTROLLER, "EX1_554t").then(
            GiveRush(Summon.CARD),
            GivePoisonous(Summon.CARD),
            GiveReborn(Summon.CARD),
        )
        * 3
    )


# Give your minions "Deathrattle: Summon a random Legendary minion."
class VAC_464t18:
    """Canopic Jars"""

    play = Buff(FRIENDLY_MINIONS, "VAC_464t18e")


@custom_card
class VAC_464t18e:
    tags = {
        GameTag.CARDNAME: "Canopic Jars",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.DEATHRATTLE: True,
    }
    deathrattle = Summon(CONTROLLER, RandomLegendaryMinion())


# Choose a minion. Fill your board with 1/1 copies of it.
class VAC_464t19:
    """Ancient Reflections"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = _AncientReflections(TARGET)


# Give a friendly minion +2/+2. Summon two copies of it.
class VAC_464t20:
    """Banana Split"""

    requirements = {
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = (
        Buff(TARGET, "VAC_464t20e"),
        Summon(CONTROLLER, ExactCopy(TARGET)) * 2,
    )


@custom_card
class VAC_464t20e:
    tags = {
        GameTag.CARDNAME: "Banana Split",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 2,
        GameTag.HEALTH: 2,
    }


# Summon 7 'Boom Bots'.
class VAC_464t21:
    """Dr. Boom's Boombox"""

    play = Summon(CONTROLLER, "GVG_110t") * 7


# Wax Rager — 3/5/1 Elemental. Deathrattle: Resummon this minion.
class VAC_464t22:
    """Wax Rager"""

    deathrattle = Summon(CONTROLLER, "VAC_464t22")


# Shoot three fireballs at random enemies that deal $8 damage each.
class VAC_464t23:
    """Embers of Ragnaros"""

    play = Hit(RANDOM_ENEMY_CHARACTER, 8) * 3


# Deal $7 damage to all enemies. Costs (1) less for each minion that's died
# this game.
class VAC_464t24:
    """Book of the Dead"""

    cost_mod = -Count(KILLED + MINION)
    play = Hit(ENEMY_CHARACTERS, 7)


# Fill your board with annoying minions.
class VAC_464t25:
    """Annoy-o Horn"""

    play = _FillAnnoying(CONTROLLER)


# Grimmer Patron — 3/3/3. At the end of your turn, summon a copy of this
# minion.
class VAC_464t26:
    """Grimmer Patron"""

    events = OWN_TURN_END.on(Summon(CONTROLLER, "VAC_464t26"))


# Beastly Beauty — 3/2/6. Rush. After this attacks a minion and survives,
# transform this into an 8/8.
class VAC_464t27:
    """Beastly Beauty"""

    tags = {GameTag.RUSH: 1}
    # "survives" = the attacker is NOT dead after the attack — use the
    # `Dead(SELF) | <action>` idiom (the else-branch fires when alive).
    events = Attack(SELF, MINION).after(Dead(SELF) | Morph(SELF, "VAC_464t27t"))


# Beautiful Beast — 5/8/8 (the transformed Beastly Beauty).
class VAC_464t27t:
    """Beautiful Beast"""


# Destroy a minion. Restore its Health to your hero.
class VAC_464t28:
    """Vampiric Fangs"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}

    def play(self):
        target = self.target
        if target is None:
            return
        heal_amount = target.max_health
        yield Destroy(target)
        yield Heal(FRIENDLY_HERO, heal_amount)


# Blade of Quel'Delar — 1/2/2 weapon (vanilla half of the Quel'Delar forge).
class VAC_464t29:
    """Blade of Quel'Delar"""


# Hilt of Quel'Delar — give a minion +3/+3 (vanilla half of the forge).
class VAC_464t30:
    """Hilt of Quel'Delar"""

    requirements = {PlayReq.REQ_MINION_TARGET: 0, PlayReq.REQ_TARGET_TO_PLAY: 0}
    play = Buff(TARGET, "VAC_464t30e")


@custom_card
class VAC_464t30e:
    tags = {
        GameTag.CARDNAME: "Hilt of Quel'Delar",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
        GameTag.ATK: 3,
        GameTag.HEALTH: 3,
    }


# Quel'Delar — 6/4/4 weapon. After your hero attacks, deal 4 damage to all
# enemies.
class VAC_464t31:
    """Quel'Delar"""

    events = Attack(FRIENDLY_HERO).after(Hit(ENEMY_CHARACTERS, 4))


# Forging Quel'Delar — 0-cost helper spell (the combine step).
class VAC_464t31t:
    """Forging Quel'Delar"""
