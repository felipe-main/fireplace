from ..utils import *


##
# Custom actions


class _CardGraderForceDrawChosen(TargetedAction):
    """Card Grader — after the Discover window picks a card-id from the deck,
    pull the actual deck card with that id into hand (ForceDraw) so the real
    card leaves the deck. The other deck cards are untouched."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        ctrl = source.controller
        real = next((c for c in ctrl.deck if c.id == card.id), None)
        if real is not None:
            source.game.cheat_action(source, [ForceDraw(real)])


class _CardGraderDiscoverFromDeck(TargetedAction):
    """Card Grader — Discover a card from your deck. Builds a Discover window
    scoped to the distinct card-ids currently in the controller's deck; the
    chosen card is then drawn out of the deck for real (the other cards stay
    in the deck, matching the printed effect)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        ids = list({c.id for c in ctrl.deck})
        if not ids:
            return
        source.game.cheat_action(
            source,
            [
                Discover(CONTROLLER, RandomID(*ids)).then(
                    _CardGraderForceDrawChosen(SELF, Discover.CARD)
                )
            ],
        )


class _NostalgicInitiateFirstSpell(TargetedAction):
    """Nostalgic Initiate — the first time you cast a spell, gain +2/+2.
    Guarded by a per-minion flag so it only fires once."""

    TARGET = ActionArg()

    def do(self, source, target):
        if getattr(source, "_initiate_buffed", False):
            return
        source._initiate_buffed = True
        source.game.cheat_action(source, [Buff(source, "TOY_340t")])


class _WindUpMusicianBattlecry(TargetedAction):
    """Wind-Up Musician — deal N damage to all enemy minions, where N is the
    card's current upgrade level (starts at 1, +1 per Trade)."""

    TARGET = ActionArg()

    def do(self, source, target):
        amount = getattr(source, "_windup_damage", 1)
        enemies = list(source.controller.opponent.field)
        if enemies:
            source.game.cheat_action(source, [Hit(enemies, amount)])


class _WindUpMusicianUpgrade(TargetedAction):
    """Wind-Up Musician — Trade to upgrade: bump the stored damage by 1."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._windup_damage = getattr(source, "_windup_damage", 1) + 1


class _TrackHigherCostPlayed(TargetedAction):
    """Nostalgic Clown — while in hand, mark a flag the first time the
    controller plays a card whose Cost is higher than the Clown's own Cost.
    The Clown's battlecry reads `_higher_cost_played` to decide whether to
    deal 4 damage."""

    TARGET = ActionArg()
    CARD = CardArg()

    def do(self, source, target, card):
        if card is source:
            return
        if card.cost > source.cost:
            source._higher_cost_played = 1


class _NostalgicClownBattlecry(TargetedAction):
    """Nostalgic Clown — if a higher-Cost card was played while holding this,
    deal 4 damage to the chosen target."""

    TARGET = ActionArg()

    def do(self, source, target):
        if isinstance(target, list):
            target = target[0] if target else None
        if not getattr(source, "_higher_cost_played", 0):
            return
        if target is not None:
            source.game.cheat_action(source, [Hit(target, 4)])


##
# Minions


class TOY_000:
    """Tar Slime"""

    # <b>Taunt</b> Has +2 Attack during your opponent's turn.
    # Taunt lives in data. The +2 Attack is a conditional aura on SELF that
    # is active only while the opponent is the current player.
    update = CurrentPlayer(OPPONENT) & Refresh(SELF, {GameTag.ATK: 2})


class TOY_006:
    """Scarab Keychain"""

    # <b>Battlecry:</b> <b>Discover</b> a 2-Cost card.
    play = DISCOVER(RandomCollectible(cost=2))


class TOY_054:
    """Card Grader"""

    # <b>Battlecry:</b> If you've cast a spell while holding this,
    # <b>Discover</b> a card from your deck.
    play = (Attr(SELF, "spells_cast_while_holding") > 0) & _CardGraderDiscoverFromDeck(
        SELF
    )


class TOY_307:
    """Sweetened Snowflurry"""

    # [x]<b>Miniaturize</b> <b>Battlecry:</b> Get 2 random temporary Frost
    # spells. (Engine auto-adds the paired Mini token on play.)
    play = (
        Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.FROST)).then(
            GiveTemporary(Give.CARD)
        )
        * 2
    )


class TOY_307t:
    """Sweetened Snowflurry"""

    # [x]<b>Mini</b> <b>Battlecry:</b> Get 2 random temporary Frost spells.
    play = (
        Give(CONTROLLER, RandomSpell(spell_school=SpellSchool.FROST)).then(
            GiveTemporary(Give.CARD)
        )
        * 2
    )


class TOY_312:
    """Nostalgic Gnome"""

    # [x]<b>Miniaturize</b> <b>Rush</b>. After this minion deals exact lethal
    # damage on your turn, draw a card. (Rush in data; "exact lethal on your
    # turn" is the Honorable Kill trigger.)
    tags = {GameTag.HONORABLE_KILL: True}
    honorable_kill = Draw(CONTROLLER)


class TOY_312t:
    """Nostalgic Gnome"""

    # [x]<b>Mini</b> <b>Rush</b>. After this minion deals exact lethal damage
    # on your turn, draw a card.
    tags = {GameTag.HONORABLE_KILL: True}
    honorable_kill = Draw(CONTROLLER)


class TOY_340:
    """Nostalgic Initiate"""

    # <b>Miniaturize</b> The first time you cast a spell, gain +2/+2.
    events = OWN_SPELL_PLAY.on(_NostalgicInitiateFirstSpell(SELF))


class TOY_340t1:
    """Nostalgic Initiate"""

    # <b>Mini</b> The first time you cast a spell, gain +2/+2.
    events = OWN_SPELL_PLAY.on(_NostalgicInitiateFirstSpell(SELF))


# Intrepid — +2/+2.
TOY_340t = buff(+2, +2)


class TOY_341:
    """Nostalgic Clown"""

    # [x]<b>Miniaturize</b> <b>Battlecry:</b> If you've played a higher Cost
    # card while holding this, deal 4 damage.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _NostalgicClownBattlecry(TARGET)

    class Hand:
        events = Play(CONTROLLER).after(_TrackHigherCostPlayed(SELF, Play.CARD))


class TOY_341t:
    """Nostalgic Clown"""

    # [x]<b>Mini</b> <b>Battlecry:</b> If you've played a higher Cost card
    # while holding this, deal 4 damage.
    requirements = {
        PlayReq.REQ_TARGET_IF_AVAILABLE: 0,
    }
    play = _NostalgicClownBattlecry(TARGET)

    class Hand:
        events = Play(CONTROLLER).after(_TrackHigherCostPlayed(SELF, Play.CARD))


class TOY_386:
    """Giftwrapped Whelp"""

    # <b>Battlecry:</b> If you're holding a Dragon, give it and this minion
    # +1/+1.
    play = HOLDING_DRAGON & (
        Buff(RANDOM(FRIENDLY_HAND + DRAGON), "TOY_386e"),
        Buff(SELF, "TOY_386e"),
    )


# Draconic Gift — +1/+1.
TOY_386e = buff(+1, +1)


class TOY_390:
    """Clearance Promoter"""

    # <b>Deathrattle:</b> Reduce the Cost of two spells in your hand by (1).
    deathrattle = Buff(RANDOM(FRIENDLY_HAND + SPELL) * 2, "TOY_390e")


# Discount Toy — Cost reduced (by 1).
TOY_390e = buff(cost=-1)


class TOY_391:
    """Caricature Artist"""

    # <b>Battlecry:</b> Draw a minion that costs (5) or more. Give it a funny
    # mustache!
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION + (COST >= 5))).then(
        Buff(ForceDraw.TARGET, "TOY_391e")
    )


# Caricature — Has a funny mustache (cosmetic enchant, no stats).
class TOY_391e:
    tags = {}


class TOY_509:
    """Wind-Up Musician"""

    # [x]<b>Tradeable</b> <b>Battlecry:</b> Deal @ damage to all enemy
    # minions. <i>(<b>Trade</b> to upgrade!)</i>
    # Tradeable handled by the engine. The @ damage starts at 1 (data
    # TAG_SCRIPT_DATA_NUM_1) and increments by 1 each time the card is Traded.
    play = _WindUpMusicianBattlecry(SELF)
    trade = _WindUpMusicianUpgrade(SELF)


##
# Whizbang's Workshop mini-set


class MIS_025:
    """The Replicator-inator"""

    # Miniaturize, Gigantify (engine). After you play a minion with the same
    # Attack as this, summon a copy of it.
    events = Play(CONTROLLER, MINION).after(
        (ATK(Play.CARD) == ATK(SELF)) & Summon(CONTROLLER, Copy(Play.CARD))
    )


class MIS_025t(MIS_025):
    """The Replicator-inator"""

    # Mini 1/1 form — same trigger (matches Attack 1).


class MIS_025t1(MIS_025):
    """The Replicator-inator"""

    # Gigantic 8/8 form — same trigger (matches Attack 8).


class MIS_026:
    """Puppetmaster Dorian"""

    # After you draw a minion, get a 1/1 copy of it that costs (1).
    # (Draw broadcasts on the ON listener, not AFTER.)
    events = Draw(CONTROLLER).on(
        Find(Draw.CARD + MINION)
        & Give(CONTROLLER, Copy(Draw.CARD)).then(Buff(Give.CARD, "MIS_026e"))
    )


class MIS_026e:
    # Creepy Puppet — stats set to 1/1, cost (1).
    atk = lambda self, i: 1
    max_health = lambda self, i: 1
    cost = SET(1)


class MIS_308:
    """Explodineer"""

    # At the end of your turn, shuffle a Bomb into your opponent's deck. When
    # drawn, it explodes for 5 damage (BOT_511t — Casts When Drawn).
    events = OWN_TURN_END.on(Shuffle(OPPONENT, "BOT_511t"))


class MIS_314:
    """Building-Block Golem"""

    # Rush (data). Deathrattle: Summon three random 1-Cost minions.
    deathrattle = Summon(CONTROLLER, RandomMinion(cost=1)) * 3


class _ProGamerResolve(TargetedAction):
    """Resolve Rock-Paper-Scissors: compare the chosen throw against the
    opponent's random throw; the winner draws 2. Ties draw nothing."""

    TARGET = ActionArg()
    # Each throw beats the one it maps to: Rock>Scissors, Paper>Rock,
    # Scissors>Paper.
    _BEATS = {"MIS_916a": "MIS_916c", "MIS_916b": "MIS_916a", "MIS_916c": "MIS_916b"}

    def do(self, source, target):
        ctrl = source.controller
        opp = ctrl.opponent
        my_throw = target.id
        opp_throw = source.game.random.choice(
            ["MIS_916a", "MIS_916b", "MIS_916c"]
        )
        if self._BEATS.get(my_throw) == opp_throw:
            source.game.cheat_action(source, [Draw(ctrl), Draw(ctrl)])
        elif self._BEATS.get(opp_throw) == my_throw:
            source.game.cheat_action(source, [Draw(opp), Draw(opp)])


class MIS_916:
    """Pro Gamer"""

    # Battlecry: Challenge your opponent to a game of Rock-Paper-Scissors!
    # The winner draws 2 cards. (You pick your throw; the opponent's is
    # random.) Plain Choice keeps the throw token out of hand — it just picks.
    play = Choice(CONTROLLER, ["MIS_916a", "MIS_916b", "MIS_916c"]).then(
        _ProGamerResolve(Choice.CARD)
    )
