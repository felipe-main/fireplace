from ..utils import *


##
# Helpers — Death Knight rune-card Discover and corpse-spending utilities.


def _rune_discover_picker(rune_tag):
    """Build a RandomCardPicker that yields DK cards with at least one
    rune of the requested type (COST_BLOOD / COST_FROST / COST_UNHOLY).
    Used by Hematurge + Necrotic Mortician.  Implemented via the
    `custom_filter` hook on the card-pool filter."""

    return RandomCollectible(
        card_class=CardClass.DEATHKNIGHT,
        custom_filter=lambda c: c.tags.get(rune_tag, 0) >= 1,
    )


class _DiscoverRuneCard(TargetedAction):
    """Open a 3-card Discover over DK cards of the requested rune type."""

    TARGET = ActionArg()

    def __init__(self, target, rune_tag):
        super().__init__(target)
        self._rune_tag = rune_tag

    def do(self, source, target):
        picker = _rune_discover_picker(self._rune_tag)
        action = Discover(target, picker).then(Give(target, Discover.CARD))
        source.game.queue_actions(source, [action])


##
# Spells


# Deal $3 damage to an enemy and Freeze it. Deal $1 damage to all other enemies.
class RLK_015:
    """Howling Blast"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = (
        Hit(TARGET, 3),
        Freeze(TARGET),
        Hit(ENEMY_CHARACTERS - TARGET, 1),
    )


# Deal $3 damage to a minion. If that kills it, summon a 2/2 Zombie with Rush.
class _PlagueStrikeHit(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        from hearthstone.enums import Zone

        source.game.cheat_action(source, [Hit(target, 3)])
        if target.zone == Zone.GRAVEYARD or getattr(target, "dead", False):
            source.game.cheat_action(source, [Summon(controller, "RLK_018t")])


class RLK_018:
    """Plague Strike"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _PlagueStrikeHit(TARGET)


# Detonate a Corpse to deal $1 damage to all minions.
# If any are still alive, repeat this.
class _CorpseExplosionTick(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        if controller.corpses <= 0:
            return
        controller.corpses -= 1
        controller.corpses_spent_this_game += 1
        source.game.cheat_action(source, [Hit(ALL_MINIONS, 1)])
        # If any minions still alive, repeat.
        alive = [
            m
            for p in source.game.players
            for m in p.field
            if not getattr(m, "dead", False)
        ]
        if alive and controller.corpses > 0:
            source.game.queue_actions(source, [_CorpseExplosionTick(CONTROLLER)])


class RLK_035:
    """Corpse Explosion"""

    play = _CorpseExplosionTick(CONTROLLER)


# Deal $2 damage to an enemy and Freeze it.
class RLK_038:
    """Icy Touch"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Hit(TARGET, 2), Freeze(TARGET)


# Refresh 2 Mana Crystals.
class RLK_042:
    """Horn of Winter"""

    # "Refresh" = refill — give back up to 2 used crystals this turn.
    play = ManaThisTurn(CONTROLLER, 2)


# Give your hero +5 Health. Spend 3 Corpses to gain 5 more and draw a card.
class RLK_051:
    """Vampiric Blood"""

    play = (
        GainArmor(FRIENDLY_HERO, 5),
        (CORPSES >= 3)
        & (SpendCorpses(CONTROLLER, 3), GainArmor(FRIENDLY_HERO, 5), Draw(CONTROLLER)),
    )


# Choose an enemy minion. Your minions attack it.
# Resummon any that die.
class _UnholyFrenzy(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        from hearthstone.enums import Zone

        attackers = list(controller.field)
        for atk in attackers:
            if atk.zone != Zone.PLAY:
                continue
            if target.zone != Zone.PLAY or getattr(target, "dead", False):
                break
            atk_id = atk.id
            source.game.cheat_action(source, [Attack(atk, target)])
            # Refresh death state.
            if atk.zone == Zone.GRAVEYARD or getattr(atk, "dead", False):
                source.game.cheat_action(source, [Summon(controller, atk_id)])


class RLK_056:
    """Unholy Frenzy"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = _UnholyFrenzy(TARGET)


# Transform an Undead into a 4/5 Undead Monstrosity with Rush.
class RLK_057:
    """Dark Transformation"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
    }
    play = Morph(TARGET, "RLK_057t")


# Deal $5 damage. Freeze all enemy minions. Summon a 5/5 Frostwyrm.
class RLK_063:
    """Frostwyrm's Fury"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = (
        Hit(TARGET, 5),
        Freeze(ENEMY_MINIONS),
        Summon(CONTROLLER, "RLK_063t"),
    )


# Destroy the highest Attack enemy minion.
class RLK_087:
    """Asphyxiate"""

    play = Destroy(HIGHEST_ATK(ENEMY_MINIONS))


# Summon two 2/2 Zombies with Taunt. Spend 4 Corpses to give them Reborn.
class _TombGuardiansSummon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        summons = []
        for _ in range(2):
            source.game.cheat_action(source, [Summon(controller, "RLK_118t3")])
        new = [m for m in controller.field if m.id == "RLK_118t3"]
        # Pick the two most-recent.
        new = new[-2:]
        spend_reborn = controller.corpses >= 4
        if spend_reborn:
            controller.corpses -= 4
            controller.corpses_spent_this_game += 4
            for m in new:
                source.game.cheat_action(source, [GiveReborn(m)])


class RLK_118:
    """Tomb Guardians"""

    play = _TombGuardiansSummon(CONTROLLER)


# Fill your board with random Undead.
class _FillBoardWithUndead(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        controller = source.controller
        from hearthstone.enums import Race

        # is_standard=True restricts the pool to the current standard year
        # — Wild-only UNDEAD minions (rare, but possible once UNDEAD
        # retro-tribing spreads to legacy sets) are excluded.
        picker = RandomMinion(race=Race.UNDEAD, is_standard=True)
        while len(controller.field) < 7:
            card_id = picker.evaluate(source)
            if not card_id:
                break
            source.game.cheat_action(source, [Summon(controller, card_id)])


class RLK_122:
    """The Scourge"""

    play = _FillBoardWithUndead(CONTROLLER)


class _ArmGlacialAdvance(TargetedAction):
    """Glacial Advance — "Your next spell this turn costs (2) less."
    Stamps the controller's `_next_spell_cost_reduction`; pay_cost
    (player.py) consumes it on the next spell played and clears it.
    Also auto-clears at OWN_TURN_END (game.py end_turn_cleanup)."""

    TARGET = ActionArg()

    def do(self, source, target):
        target._next_spell_cost_reduction = 2


# Deal $4 damage. Your next spell this turn costs (2) less.
class RLK_512:
    """Glacial Advance"""

    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = Hit(TARGET, 4), _ArmGlacialAdvance(CONTROLLER)


@custom_card
class RLK_025e:
    # Vestigial marker enchant (kept so any saved-state reference to the
    # id resolves). Cost reduction is now owned by pay_cost +
    # controller._next_spell_cost_reduction.
    tags = {
        GameTag.CARDNAME: "Glacial Advance",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


# Give all minions in your hand +1/+1.
# Spend 3 Corpses to give them +1/+1 more.
class RLK_712:
    """Blood Tap"""

    play = (
        Buff(FRIENDLY_HAND + MINION, "RLK_712e"),
        (CORPSES >= 3)
        & (SpendCorpses(CONTROLLER, 3), Buff(FRIENDLY_HAND + MINION, "RLK_712e")),
    )


# Lifesteal. Infect all enemy minions. At the end of your turns, they
# take 2 damage.
class RLK_730:
    """Blood Boil"""

    play = Buff(ENEMY_MINIONS, "RLK_730e")
    tags = {GameTag.LIFESTEAL: True}


##
# Minions


# Taunt. Battlecry: Summon two copies of this minion.
class RLK_062:
    """Nerubian Swarmguard"""

    play = Summon(CONTROLLER, "RLK_062") * 2


# Battlecry: Spend a Corpse to Discover a Blood Rune card.
class _DiscoverBloodRune(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        if target.corpses <= 0:
            return
        target.corpses -= 1
        target.corpses_spent_this_game += 1
        picker = _rune_discover_picker(GameTag.COST_BLOOD)
        action = Discover(target, picker).then(Give(target, Discover.CARD))
        source.game.queue_actions(source, [action])


class RLK_066:
    """Hematurge"""

    play = _DiscoverBloodRune(CONTROLLER)


# After you cast a spell, deal 1 damage to two random enemies.
class RLK_083:
    """Deathchiller"""

    events = OWN_SPELL_PLAY.on(Hit(RANDOM(ENEMY_CHARACTERS) * 2, 1))


# Battlecry: Gain +1 Attack for each Frost spell in your hand.
class RLK_110:
    """Ymirjar Frostbreaker"""

    play = Buff(SELF, "RLK_110e") * Count(FRIENDLY_HAND + FROST_SPELL)


# Battlecry: If a friendly Undead died after your last turn,
# Discover an Unholy Rune card.
class _NecroticMortician(TargetedAction):
    """Reads the engine-managed `_undead_deaths_in_window` for the
    precise "died after your last turn" check (Death.do appends,
    OWN_TURN_END resets)."""

    TARGET = ActionArg()

    def do(self, source, target):
        if not target._undead_deaths_in_window:
            return
        picker = _rune_discover_picker(GameTag.COST_UNHOLY)
        action = Discover(target, picker).then(Give(target, Discover.CARD))
        source.game.queue_actions(source, [action])


class RLK_116:
    """Necrotic Mortician"""

    play = _NecroticMortician(CONTROLLER)


# Battlecry: Shred a random minion in your deck to gain 3 Corpses.
class _MeatGrinderShred(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        from hearthstone.enums import CardType, Zone

        minions = [c for c in ctrl.deck if c.type == CardType.MINION]
        if not minions:
            return
        victim = source.game.random.choice(minions)
        # Move to GRAVEYARD (not REMOVEDFROMGAME) so resurrect pools and
        # "destroyed minions" trackers see the body. Deck-destroyed minions
        # in HS don't fire their deathrattle (only in-play destroys do),
        # so we skip the Deathrattle pipeline by setting the zone directly.
        victim.zone = Zone.GRAVEYARD
        ctrl.corpses += 3
        ctrl.corpses_gained_this_game += 3


class RLK_120:
    """Meat Grinder"""

    play = _MeatGrinderShred(CONTROLLER)


# After a friendly Undead dies, draw a card.
class RLK_121:
    """Acolyte of Death"""

    events = Death(FRIENDLY + MINION + UNDEAD).on(Draw(CONTROLLER))


# Battlecry: Infect all enemy minions. When they die, you summon a 2/2
# Zombie with Taunt.
class RLK_225:
    """Blightfang"""

    play = Buff(ENEMY_MINIONS, "RLK_225e")


# Battlecry: Spend up to 8 Corpses.
# Summon a Risen Groom with stats equal to the amount spent.
class _CorpseBrideSummon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spend = min(8, ctrl.corpses)
        if spend <= 0:
            return
        ctrl.corpses -= spend
        ctrl.corpses_spent_this_game += spend
        source.game.cheat_action(source, [Summon(ctrl, "RLK_506t")])
        groom = [m for m in ctrl.field if m.id == "RLK_506t"]
        if not groom:
            return
        groom = groom[-1]
        # Buff Risen Groom: it's a 1/1, the printed effect summons one
        # with stats == amount spent.  We approximate by stacking
        # +(spend-1)/+(spend-1) so it lands at spend/spend.
        delta = spend - 1
        if delta > 0:
            source.game.cheat_action(
                source,
                [Buff(groom, "RLK_504e", atk=delta, max_health=delta)],
            )


class RLK_504:
    """Corpse Bride"""

    play = _CorpseBrideSummon(CONTROLLER)


# Battlecry: Spend up to 5 Corpses. Deal 2 damage to a random enemy
# for each.
class _MarrowManipulator(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spend = min(5, ctrl.corpses)
        if spend <= 0:
            return
        ctrl.corpses -= spend
        ctrl.corpses_spent_this_game += spend
        for _ in range(spend):
            source.game.cheat_action(source, [Hit(RANDOM_ENEMY_CHARACTER, 2)])


class RLK_505:
    """Marrow Manipulator"""

    play = _MarrowManipulator(CONTROLLER)


# Taunt. Battlecry: Raise up to 6 Corpses as 1/2 Risen Footmen with Taunt.
class _BoneguardSummon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spend = min(6, ctrl.corpses)
        if spend <= 0:
            return
        ctrl.corpses -= spend
        ctrl.corpses_spent_this_game += spend
        for _ in range(spend):
            source.game.cheat_action(source, [Summon(ctrl, "RLK_061t")])


class RLK_506:
    """Boneguard Commander"""

    play = _BoneguardSummon(CONTROLLER)


# Battlecry: For the rest of the game, deal 3 damage to your opponent
# at the end of your turns.
class _AlexandrosArm(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        target._alexandros_armed = True
        target._alexandros_source = source


@custom_card
class RLK_706e:
    tags = {
        GameTag.CARDNAME: "Ashbringer's Light",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }
    events = OWN_TURN_END.on(Hit(ENEMY_HERO, 3))


class RLK_706:
    """Alexandros Mograine"""

    # Stamp a permanent enchantment on the friendly hero that fires
    # 3 damage to the enemy hero at every OWN_TURN_END.
    play = Buff(FRIENDLY_HERO, "RLK_706e")


# Battlecry: Give a minion in your hand Attack equal to this minion's
# Attack.
class _ViciousBloodwormApplyBuff(TargetedAction):
    """Apply the +N Attack buff after the player Choice resolves."""

    PLAYER = ActionArg()
    CARDS = ActionArg()
    CARD = ActionArg()
    AMOUNT = ActionArg()

    def do(self, source, player, cards, picked, amount):
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if picked is None:
            return
        if isinstance(amount, list):
            amount = amount[0] if amount else 0
        source.game.cheat_action(
            source, [Buff(picked, "RLK_711e", atk=int(amount))]
        )


class _ViciousBloodwormBuff(TargetedAction):
    """Open a player Choice over the controller's hand minions; the
    chosen card receives a +N Attack buff where N is this minion's
    current attack (snapshotted at trigger time)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        from hearthstone.enums import CardType

        minions = [c for c in ctrl.hand if c.type == CardType.MINION]
        if not minions:
            return
        atk = source.atk
        choice = Choice(ctrl, minions).then(
            _ViciousBloodwormApplyBuff(
                Choice.PLAYER, Choice.CARDS, Choice.CARD, atk
            )
        )
        source.game.queue_actions(source, [choice])


class RLK_711:
    """Vicious Bloodworm"""

    play = _ViciousBloodwormBuff(SELF)


# Deathrattle: Copy all Frost spells in your hand.
class _LadyDeathwhisperCopy(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        from hearthstone.enums import CardType, SpellSchool

        def _is_frost(c):
            # Match either a single-school Frost spell or a multi-school
            # spell whose schools include Frost. Data exposes
            # `spell_schools` (list[SpellSchool]) for multi-school spells
            # and `spell_school` (single value) otherwise.
            schools = getattr(c.data, "spell_schools", None)
            if schools:
                return SpellSchool.FROST in schools
            return getattr(c.data, "spell_school", None) == SpellSchool.FROST

        frost_spells = [
            c
            for c in list(ctrl.hand)
            if c.type == CardType.SPELL and _is_frost(c)
        ]
        for spell in frost_spells:
            if len(ctrl.hand) >= ctrl.max_hand_size:
                break
            source.game.cheat_action(source, [Give(ctrl, spell.id)])


class RLK_713:
    """Lady Deathwhisper"""

    deathrattle = _LadyDeathwhisperCopy(CONTROLLER)


# Battlecry: Spend 2 Corpses to give all minions in your hand +2 Attack.
class RLK_731:
    """Darkfallen Neophyte"""

    play = (CORPSES >= 2) & (
        SpendCorpses(CONTROLLER, 2),
        Buff(FRIENDLY_HAND + MINION, "RLK_731e"),
    )


class RLK_731e:
    # In-data buff "Fallen to Dark" — +2 Attack on hand minions. The data
    # card carries no ATK tag so the buff is a no-op until declared here.
    tags = {GameTag.ATK: 2}


# Battlecry: Destroy all other minions. Gain 1 Corpse for each enemy
# destroyed.
class _SoulstealerDestroy(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        enemies = [m for m in source.game.board if m.controller is not ctrl and m is not source]
        friendlies = [m for m in source.game.board if m.controller is ctrl and m is not source]
        all_others = enemies + friendlies
        if all_others:
            source.game.cheat_action(source, [Destroy(all_others)])
        ctrl.corpses += len(enemies)
        ctrl.corpses_gained_this_game += len(enemies)


class RLK_741:
    """Soulstealer"""

    play = _SoulstealerDestroy(SELF)


# Reborn. At the end of your turn, spend 5 Corpses to summon a copy of
# this minion.
class _MalignantHorrorTick(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.corpses < 5:
            return
        ctrl.corpses -= 5
        ctrl.corpses_spent_this_game += 5
        source.game.cheat_action(source, [Summon(ctrl, "RLK_745")])


class RLK_745:
    """Malignant Horror"""

    events = OWN_TURN_END.on(_MalignantHorrorTick(SELF))


##
# Weapons


# After your hero attacks and kills a minion, gain 2 Corpses.
class _SoulbreakerKill(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        # Defender of the just-resolved hero attack — if it's a minion
        # in the graveyard, +2 corpses to controller.
        ctrl = source.controller
        from hearthstone.enums import CardType, Zone

        if (
            target.type == CardType.MINION
            and (target.zone == Zone.GRAVEYARD or getattr(target, "dead", False))
        ):
            ctrl.corpses += 2
            ctrl.corpses_gained_this_game += 2


class RLK_012:
    """Soulbreaker"""

    events = Attack(FRIENDLY_HERO).after(_SoulbreakerKill(Attack.DEFENDER))


# Deathrattle: Summon every minion killed by this weapon.
class _FrostmourneRecord(TargetedAction):
    """Listener on the wielding weapon: every hero-attack against a
    minion records the defender's id; if it dies, summon on deathrattle."""

    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType, Zone

        weapon = source.controller.weapon
        if weapon is None or weapon.id != "RLK_086":
            return
        if target.type != CardType.MINION:
            return
        if not hasattr(weapon, "_frostmourne_kills"):
            weapon._frostmourne_kills = []
        if target.zone == Zone.GRAVEYARD or getattr(target, "dead", False):
            weapon._frostmourne_kills.append(target.id)


class _FrostmourneSummonAll(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        kills = getattr(source, "_frostmourne_kills", [])
        for cid in kills:
            source.game.cheat_action(source, [Summon(ctrl, cid)])


class RLK_086:
    """Frostmourne"""

    events = Attack(FRIENDLY_HERO).after(_FrostmourneRecord(Attack.DEFENDER))
    deathrattle = _FrostmourneSummonAll(SELF)


# After your hero attacks a minion, deal 2 damage to the enemy hero.
class RLK_516:
    """Bone Breaker"""

    events = Attack(FRIENDLY_HERO, MINION).after(Hit(ENEMY_HERO, 2))


# Battlecry: Spend up to 3 Corpses. Freeze that many enemy minions.
class _MightOfMenethilFreeze(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spend = min(3, ctrl.corpses)
        if spend <= 0:
            return
        ctrl.corpses -= spend
        ctrl.corpses_spent_this_game += spend
        enemies = list(ctrl.opponent.field)
        if not enemies:
            return
        n = min(spend, len(enemies))
        picks = source.game.random.sample(enemies, n)
        for m in picks:
            source.game.cheat_action(source, [Freeze(m)])


class RLK_740:
    """Might of Menethil"""

    play = _MightOfMenethilFreeze(CONTROLLER)


##
# Engine-internal enchantments — register the ones the data XML doesn't
# already carry.


@custom_card
class RLK_057e:
    tags = {
        GameTag.CARDNAME: "Dark Transformation",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class RLK_086e:
    tags = {
        GameTag.CARDNAME: "Frostmourne",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class RLK_118e:
    tags = {
        GameTag.CARDNAME: "Tomb Guardians",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class RLK_504e:
    tags = {
        GameTag.CARDNAME: "Risen Groom",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class RLK_741e:
    tags = {
        GameTag.CARDNAME: "Soulstealer",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


@custom_card
class RLK_745e:
    tags = {
        GameTag.CARDNAME: "Malignant Horror",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


##
# Core / starter Death Knight cards (CORE set companions to MotLK).


# Battlecry: Destroy a random minion in your opponent's hand, deck, and battlefield.
class _PatchwerkDestroy(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        opp = source.controller.opponent
        from hearthstone.enums import CardType, Zone

        # Hand: random minion card in opponent hand. Move to GRAVEYARD
        # so resurrect pools/destroyed-from-hand trackers see it.
        hand_minions = [c for c in list(opp.hand) if c.type == CardType.MINION]
        if hand_minions:
            victim = source.game.random.choice(hand_minions)
            victim.zone = Zone.GRAVEYARD
        # Deck: random minion card in opponent deck.
        deck_minions = [c for c in list(opp.deck) if c.type == CardType.MINION]
        if deck_minions:
            victim = source.game.random.choice(deck_minions)
            victim.zone = Zone.GRAVEYARD
        # Battlefield: random enemy minion in play (full destroy pipeline
        # — deathrattle, friendly_minions_died_this_game, etc.).
        field = [m for m in list(opp.field) if not getattr(m, "dead", False)]
        if field:
            victim = source.game.random.choice(field)
            source.game.cheat_action(source, [Destroy(victim)])


class RLK_071:
    """Patchwerk"""

    play = _PatchwerkDestroy(CONTROLLER)


# Battlecry: Summon two 1/1 Fighters with Rush and Reborn.
class _PossessifierSummon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(2):
            source.game.cheat_action(source, [Summon(ctrl, "RLK_077t")])
        # Pick the two most-recently-summoned Possessed Fighters.
        fighters = [m for m in ctrl.field if m.id == "RLK_077t"][-2:]
        for m in fighters:
            source.game.cheat_action(source, [GiveRush(m), GiveReborn(m)])


class RLK_077:
    """Possessifier"""

    play = _PossessifierSummon(CONTROLLER)


# Battlecry: Deal 2 damage to an enemy and your hero.
class RLK_079:
    """Noxious Cadaver"""

    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_ENEMY_TARGET: 0,
    }
    play = Hit(TARGET, 2), Hit(FRIENDLY_HERO, 2)


# Taunt. Deathrattle: Return this to your hand. It costs Health instead of Mana.
# (Approximation: the "costs Health instead of Mana" effect requires engine
# support for an alternative cost mechanic; we just bounce the card back to
# hand on death and leave a TODO for the cost-swap.)
class _SaurfangBounce(TargetedAction):
    """Saurfang deathrattle: return a fresh Saurfang to hand and arm the
    "next Paladin minion costs Health" flag. Saurfang is itself a DK
    minion (not Paladin), so we use a per-card flag `_costs_health`
    that pay_cost (player.py) honours regardless of class."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        source.game.cheat_action(source, [Give(ctrl, "RLK_082")])
        # Find the just-given copy and stamp it as costing Health.
        for c in reversed(ctrl.hand):
            if c.id == "RLK_082":
                c.card_costs_health = True
                break


class RLK_082:
    """Deathbringer Saurfang"""

    tags = {GameTag.TAUNT: True}
    deathrattle = _SaurfangBounce(CONTROLLER)


# Battlecry: Raise ALL of your Corpses as 1/1 Risen Golems with Rush.
# For each that can't fit, give one +2/+2.
class _MarrowgarRaise(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        spend = ctrl.corpses
        if spend <= 0:
            return
        ctrl.corpses -= spend
        ctrl.corpses_spent_this_game += spend
        slots = max(0, 7 - len(ctrl.field))
        summon_count = min(spend, slots)
        overflow = spend - summon_count
        summoned = []
        for _ in range(summon_count):
            source.game.cheat_action(source, [Summon(ctrl, "RLK_085t")])
            golems = [m for m in ctrl.field if m.id == "RLK_085t"]
            if golems:
                m = golems[-1]
                source.game.cheat_action(source, [GiveRush(m)])
                summoned.append(m)
        # Distribute +2/+2 to summoned golems for each overflow corpse.
        if summoned:
            for i in range(overflow):
                target_m = summoned[i % len(summoned)]
                source.game.cheat_action(
                    source,
                    [Buff(target_m, "RLK_085e", atk=2, max_health=2)],
                )


class RLK_085:
    """Lord Marrowgar"""

    play = _MarrowgarRaise(CONTROLLER)


# Battlecry and Deathrattle: Draw a card.
class RLK_708:
    """Chillfallen Baron"""

    play = Draw(CONTROLLER)
    deathrattle = Draw(CONTROLLER)


# Battlecry: Gain a Corpse.
class _BodyBaggerGainCorpse(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ctrl.corpses += 1
        ctrl.corpses_gained_this_game += 1


class RLK_503:
    """Body Bagger"""

    play = _BodyBaggerGainCorpse(CONTROLLER)


# Deathrattle: Draw a Frost spell.
# Custom action: draw is top-of-deck only; we pull a random Frost spell
# directly from the deck into hand.
class _DrawFrostSpell(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType, SpellSchool, Zone

        deck = [
            c
            for c in list(target.deck)
            if c.type == CardType.SPELL
            and getattr(c.data, "spell_school", None) == SpellSchool.FROST
        ]
        if not deck:
            return
        pick = source.game.random.choice(deck)
        if len(target.hand) >= target.max_hand_size:
            pick.discard()
            return
        pick.zone = Zone.HAND


class RLK_511:
    """Harbinger of Winter"""

    deathrattle = _DrawFrostSpell(CONTROLLER)


# Battlecry: Summon two 2/1 Rime Elementals with "Deathrattle: Deal 2 damage
# to a random enemy."
class RLK_752:
    """Rime Sculptor"""

    play = Summon(CONTROLLER, "RLK_907t") * 2


# The Rime Elemental token (RLK_907t) needs its deathrattle scripted.
class RLK_907t:
    """Rime Elemental"""

    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 2)


# Battlecry: Spend a Corpse to gain +1/+2.
class RLK_753:
    """Bonedigger Geist"""

    play = (CORPSES >= 1) & (
        SpendCorpses(CONTROLLER, 1),
        Buff(SELF, "RLK_753e", atk=1, max_health=2),
    )


# Battlecry: Give a friendly Undead +2 Attack.
class RLK_958:
    """Skeletal Sidekick"""

    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_FRIENDLY_TARGET: 0,
        PlayReq.REQ_TARGET_WITH_RACE: int(Race.UNDEAD),
    }
    play = Buff(TARGET, "RLK_958e", atk=2)


# Reborn. Battlecry and Deathrattle: Deal 2 damage to a random enemy.
class RLK_223:
    """Thassarian"""

    tags = {GameTag.REBORN: True}
    play = Hit(RANDOM_ENEMY_CHARACTER, 2)
    deathrattle = Hit(RANDOM_ENEMY_CHARACTER, 2)


# Battlecry: Draw 2 spells. If they're both Frost spells, deal 2 damage to
# all enemies.
class _FrigidaraDraw(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        from hearthstone.enums import CardType, SpellSchool, Zone

        drawn = []
        for _ in range(2):
            spells = [c for c in list(target.deck) if c.type == CardType.SPELL]
            if not spells:
                break
            pick = source.game.random.choice(spells)
            if len(target.hand) >= target.max_hand_size:
                pick.discard()
            else:
                pick.zone = Zone.HAND
            drawn.append(pick)
        if (
            len(drawn) == 2
            and all(
                getattr(c.data, "spell_school", None) == SpellSchool.FROST
                for c in drawn
            )
        ):
            source.game.cheat_action(source, [Hit(ENEMY_CHARACTERS, 2)])


class RLK_224:
    """Overseer Frigidara"""

    play = _FrigidaraDraw(CONTROLLER)


# Taunt. Deathrattle: Spend 3 Corpses to summon a 3/3 Risen Ymirjar with Taunt.
class _YmirjarSummon(TargetedAction):
    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        if ctrl.corpses < 3:
            return
        ctrl.corpses -= 3
        ctrl.corpses_spent_this_game += 3
        source.game.cheat_action(source, [Summon(ctrl, "RLK_226t")])


class RLK_226:
    """Ymirjar Deathbringer"""

    tags = {GameTag.TAUNT: True}
    deathrattle = _YmirjarSummon(CONTROLLER)


