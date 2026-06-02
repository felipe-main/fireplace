from ..utils import *


# "When summoned" trigger. The engine provides OWN_SUMMON — a self-observing
# Summon event that (unlike the base Summon event, whose _broadcast self-blocks)
# DOES fire for the minion's own summon. Fall back to a plain
# Summon(CONTROLLER, SELF) if an older engine lacks the name so the module still
# imports. (Same guard the Cataclysm Rogue tentacle tokens use.)
try:
    OWN_SUMMON
except NameError:
    OWN_SUMMON = Summon(CONTROLLER, SELF)


# Tichondrius — only the CORE reprint (CORE_CATA_001) exists in this data; its
# script resolves to the bare CATA_001 id (get_script_definition strips CORE_).
class _TichondriusNextDemonFree(TargetedAction):
    """Battlecry: arm "your next Demon this turn costs (0)" — a per-player
    one-shot flag consumed by the next Demon's cost (card.py + Play.do), reset
    at OWN_TURN_END."""

    TARGET = ActionArg()

    def do(self, source, target):
        source.controller.next_demon_free_this_turn = True


class CATA_001:
    """Tichondrius"""

    # Your hero is Immune. Battlecry: Your next Demon this turn costs (0).
    update = Refresh(FRIENDLY_HERO, {GameTag.IMMUNE: 1})
    play = _TichondriusNextDemonFree(SELF)


# ---------------------------------------------------------------------------
# Custom LazyNums / actions
# ---------------------------------------------------------------------------


class _HeraldAttack(LazyNum):
    """Azshara's Tentacle / Soldier of Azshara — the +Attack value the token
    gives the hero scales with Heralds: base 1, +1 per Herald up to twice
    (i.e. 1/2/3 at 0/1/2+ Heralds). Mirrors the card's
    "Herald twice/once to upgrade" wording."""

    def evaluate(self, source):
        player = source.controller
        return self.num(1 + min(getattr(player, "heralds_this_game", 0), 2))


class _FelSpellsCastThisGame(LazyNum):
    """Count of Fel spells the controller has cast this game (for Ravenous
    Felfisher's cost reduction). Reads Player.spells_cast_by_school which the
    Play action populates by SpellSchool."""

    def evaluate(self, source):
        history = source.controller.spells_cast_by_school
        return self.num(len(history.get(int(SpellSchool.FEL), [])))


class _BroxigarLastStand(TargetedAction):
    """Broxigar's Last Stand — deal 1 damage to all minions, then draw a card
    for each minion that died as a result. Snapshot the board, hit each for 1,
    let deaths process, then count how many of the snapshot left PLAY and draw
    that many."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        before = list(game.board)
        for minion in before:
            game.cheat_action(source, [Hit(minion, 1)])
        # Deaths are only moved to the graveyard once the action stack drains;
        # force it now so the post-AoE board reflects the kills before we count.
        game.process_deaths()
        died = sum(1 for m in before if m.zone != Zone.PLAY)
        if died:
            game.cheat_action(source, [Draw(source.controller) * died])


class _DreadLeviathanSteal(TargetedAction):
    """Dread Leviathan — steal 3 Health from the chosen enemy minion, three
    times: each tick reduces the victim's Health by 3 (CATA_699e) and gives
    Dread Leviathan +3 Health (CATA_699e2)."""

    TARGET = ActionArg()

    def do(self, source, target):
        game = source.game
        for _ in range(3):
            if target is None or target.zone != Zone.PLAY:
                break
            game.cheat_action(source, [Buff(target, "CATA_699e")])
            game.cheat_action(source, [Buff(source, "CATA_699e2")])


# ---------------------------------------------------------------------------
# Azshara, Ocean Lord (Colossal +2) + tentacle limbs + tokens
# ---------------------------------------------------------------------------


class CATA_151:
    """Azshara, Ocean Lord"""

    # Colossal +2. Your hero has Windfury. (Limbs CATA_151t / CATA_151t1 are
    # summoned automatically by the engine's Colossal hook.) The Windfury is a
    # while-in-play aura on the hero.
    update = Refresh(FRIENDLY_HERO, {GameTag.WINDFURY: True})


class CATA_151e:
    """Azshara Windfury"""

    tags = {GameTag.WINDFURY: True}


class CATA_151t(HeraldAttackTierCardtext):
    """Azshara's Tentacle"""

    # When summoned, give your hero +N Attack this turn (N scales with Heralds).
    summoned = Buff(FRIENDLY_HERO, "CATA_151te", atk=_HeraldAttack())


class CATA_151t1(CATA_151t):
    """Azshara's Tentacle"""


class CATA_151te:
    """Hero Blood of the Fel"""

    # +N Attack on your turn — one-turn effect (TAG_ONE_TURN_EFFECT in data),
    # value supplied dynamically by the summoning tentacle.
    tags = {GameTag.TAG_ONE_TURN_EFFECT: True}


# ---------------------------------------------------------------------------
# Armored Bloodletter + Soldier of Azshara token
# ---------------------------------------------------------------------------


class CATA_525(HeraldCountCardtext):
    """Armored Bloodletter"""

    # Rush (data). Battlecry: Herald.
    play = Herald(CONTROLLER)


class CATA_525t(HeraldAttackTierCardtext):
    """Soldier of Azshara"""

    # When summoned, give your hero +N Attack this turn (N scales with Heralds).
    # Uses the `summoned` script (fires on this token's own summon, which the
    # summon-event broadcast excludes).
    summoned = Buff(FRIENDLY_HERO, "CATA_151te", atk=_HeraldAttack())


# ---------------------------------------------------------------------------
# Broxigar's Last Stand
# ---------------------------------------------------------------------------


class CATA_526:
    """Broxigar's Last Stand"""

    # Deal 1 damage to all minions. Draw a card for each that died.
    play = _BroxigarLastStand(CONTROLLER)


# ---------------------------------------------------------------------------
# Nespirah, Enthralled (Location) + Nespirah, Unshackled
# ---------------------------------------------------------------------------


class CATA_527:
    """Nespirah, Enthralled"""

    # Deal 1 damage. After you cast a Fel spell, reopen. Deathrattle: Summon
    # Nespirah, Unshackled. (Data omits the DEATHRATTLE tag, so flag it so the
    # engine fires the deathrattle script.)
    tags = {GameTag.DEATHRATTLE: True}
    requirements = {PlayReq.REQ_TARGET_TO_PLAY: 0}
    activate = Hit(TARGET, 1)
    events = OWN_SPELL_PLAY.after(
        Find(Play.CARD + FEL_SPELL) & ReopenLocation(SELF)
    )
    deathrattle = Summon(CONTROLLER, "CATA_527t2")


class _NespirahFelNaga(TargetedAction):
    """Nespirah, Unshackled — after you cast a Fel spell, add a random Naga to
    your hand that costs (1)."""

    TARGET = ActionArg()

    def do(self, source, target):
        player = source.controller
        pick = RandomMinion(race=Race.NAGA).evaluate(source)
        if not pick:
            return
        before = len(player.hand)
        source.game.cheat_action(source, [Give(player, pick)])
        if len(player.hand) > before:
            given = player.hand[-1]
            # "It costs (1)": apply an additive COST buff equal to (1 - cost).
            base = given.data.cost or 0
            delta = 1 - base
            source.game.cheat_action(
                source, [Buff(given, "CATA_527t2e", cost=delta)]
            )


class CATA_527t2:
    """Nespirah, Unshackled"""

    # After you cast a Fel spell, get a random Naga. It costs (1).
    events = OWN_SPELL_PLAY.after(
        Find(Play.CARD + FEL_SPELL) & _NespirahFelNaga(CONTROLLER)
    )


@custom_card
class CATA_527t2e:
    tags = {
        GameTag.CARDNAME: "Nespirah's Gift",
        GameTag.CARDTYPE: CardType.ENCHANTMENT,
    }


# ---------------------------------------------------------------------------
# Sigil of the Seas + Naga Monstrosity
# ---------------------------------------------------------------------------


class CATA_528:
    """Sigil of the Seas"""

    # Sigil — at the start of your next turn, summon a 3/3 Naga with Taunt.
    events = OWN_TURN_BEGIN.on(Summon(CONTROLLER, "CATA_528t"), Destroy(SELF))


class CATA_528t:
    """Naga Monstrosity"""

    # Taunt (from data).


# ---------------------------------------------------------------------------
# Ravenous Felfisher
# ---------------------------------------------------------------------------


class CATA_529:
    """Ravenous Felfisher"""

    # Costs (1) less for each Fel spell you've cast this game.
    cost_mod = -_FelSpellsCastThisGame()


# ---------------------------------------------------------------------------
# Fel Infusion
# ---------------------------------------------------------------------------


class CATA_530(HeraldCountCardtext):
    """Fel Infusion"""

    # Herald. Your hero has Lifesteal this turn.
    play = Herald(CONTROLLER), Buff(FRIENDLY_HERO, "CATA_530e")


class CATA_530e:
    """Lifesteal this turn"""

    # One-turn Lifesteal on the hero. (Data carries no LIFESTEAL/one-turn tag,
    # so declare both: LIFESTEAL grants the heal, TAG_ONE_TURN_EFFECT clears it
    # at end of turn.)
    tags = {GameTag.LIFESTEAL: True, GameTag.TAG_ONE_TURN_EFFECT: True}


# ---------------------------------------------------------------------------
# Flash Flood
# ---------------------------------------------------------------------------


class CATA_533:
    """Flash Flood"""

    # Deal 5 damage to your opponent's left and right-most minions.
    # Outcast: Do it again. (Outcast REPLACES play in the engine, so the
    # Outcast branch performs the hit twice to net the "do it again" total.)
    play = Hit(OUTERMOST(ENEMY_MINIONS), 5)
    outcast = Hit(OUTERMOST(ENEMY_MINIONS), 5), Hit(OUTERMOST(ENEMY_MINIONS), 5)


# ---------------------------------------------------------------------------
# Malevolent Mutant
# ---------------------------------------------------------------------------


class _MalevolentMutant(TargetedAction):
    """Battlecry: Choose a Fel spell in your hand. Get a copy of it."""

    TARGET = ActionArg()

    def do(self, source, target):
        choose_hand_card(
            source,
            lambda s, c: s.game.cheat_action(s, [Give(s.controller, c.id)]),
            filter=lambda c: c.type == CardType.SPELL
            and getattr(c, "spell_school", SpellSchool.NONE) == SpellSchool.FEL,
        )


class CATA_697:
    """Malevolent Mutant"""

    # Battlecry: Choose a Fel spell in your hand. Get a copy of it.
    play = _MalevolentMutant(SELF)


# ---------------------------------------------------------------------------
# Dread Leviathan
# ---------------------------------------------------------------------------


class CATA_699:
    """Dread Leviathan"""

    # Taunt (data). Battlecry: Choose an enemy minion to steal 3 Health from,
    # three times.
    requirements = {
        PlayReq.REQ_ENEMY_TARGET: 0,
        PlayReq.REQ_MINION_TARGET: 0,
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _DreadLeviathanSteal(TARGET)


class CATA_699e:
    """Drained"""

    # Victim loses 3 Health.
    tags = {GameTag.HEALTH: -3}


class CATA_699e2:
    """Crackin'"""

    # Dread Leviathan gains 3 Health.
    tags = {GameTag.HEALTH: 3}
