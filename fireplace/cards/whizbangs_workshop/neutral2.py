from ..utils import *


##
# Helper actions


class _ObserverCastSecrets(TargetedAction):
    """Observer of Mysteries — cast 2 random Secrets (any class). Each cast
    Secret is flagged `_disco_temp` and the controller's `_disco_active` flag
    is armed so game._begin_turn destroys them at the start of the caster's
    next turn ("At the start of your turn, destroy them"). This reuses the
    exact same cleanup machinery as Disco at the End of Time."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(2):
            picker = RandomSpell(secret=True)
            pick = picker.evaluate(source)
            cid = pick[0] if isinstance(pick, list) else pick
            if not cid:
                continue
            card = ctrl.card(cid)
            card.zone = Zone.HAND
            card._disco_temp = True
            source.game.cheat_action(source, [CastSpell(card)])
        ctrl._disco_active = True


class _PlayhouseCardsDrawn(LazyNum):
    """Count of cards the controller has drawn this game, tracked on Playhouse
    Giant via `_cards_drawn_this_game` (bumped by its Deck/Hand draw listeners
    so the count is correct from game start through the moment it is played).
    Defaults to 0 before any draw."""

    def evaluate(self, source):
        return self.num(getattr(source, "_cards_drawn_this_game", 0))


class _PlayhouseBumpDrawn(TargetedAction):
    """Bump Playhouse Giant's per-card `_cards_drawn_this_game` counter each
    time the controller draws a card."""

    TARGET = ActionArg()

    def do(self, source, target):
        source._cards_drawn_this_game = getattr(
            source, "_cards_drawn_this_game", 0
        ) + 1


class _LiNaFillBoard(TargetedAction):
    """Li'Na, Shop Manager — fill the controller's board with random minions
    whose Cost equals the just-cast spell's Cost. The TARGET is the spell
    that was cast (Play.CARD)."""

    TARGET = ActionArg()

    def do(self, source, target):
        ctrl = source.controller
        cost = target.cost
        picker = RandomMinion(cost=cost)
        while len(ctrl.field) < ctrl.game.MAX_MINIONS_ON_FIELD:
            cid = picker.evaluate(source)
            if isinstance(cid, list):
                cid = cid[0] if cid else None
            if not cid:
                break
            source.game.cheat_action(source, [Summon(ctrl, cid)])


class _ColiferoTransform(TargetedAction):
    """Colifero the Artist — transform all OTHER friendly minions into copies
    of the drawn minion. The TARGET is the drawn card (still in hand);
    `source` is Colifero itself, excluded from the transform."""

    TARGET = ActionArg()

    def do(self, source, target):
        copier = ExactCopy(None)
        for minion in list(source.controller.field):
            if minion is source:
                continue
            copy = copier.copy(source, target)
            source.game.queue_actions(source, [Morph(minion, copy)])


class _BucketSummonSoldiers(TargetedAction):
    """Bucket of Soldiers — summon five 1/1 Toy Soldiers, each independently
    rolled from the eight bonus-effect variants."""

    TARGET = ActionArg()

    SOLDIERS = [
        "TOY_814t",   # Divine Shield
        "TOY_814t2",  # Taunt
        "TOY_814t3",  # Rush
        "TOY_814t4",  # Windfury
        "TOY_814t5",  # Stealth
        "TOY_814t6",  # Poisonous
        "TOY_814t7",  # Lifesteal
        "TOY_814t8",  # Reborn
    ]

    def do(self, source, target):
        ctrl = source.controller
        for _ in range(5):
            if len(ctrl.field) >= ctrl.game.MAX_MINIONS_ON_FIELD:
                break
            cid = source.game.random.choice(self.SOLDIERS)
            source.game.cheat_action(source, [Summon(ctrl, cid)])


##
# Minions


class TOY_517:
    """Plucky Paintfin"""

    # <b>Poisonous</b> <b>Battlecry:</b> Draw a <b>Rush</b> minion.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION + RUSH))


class TOY_518:
    """Treasure Distributor"""

    # After you summon a Pirate, give it +1 Attack.
    events = Summon(CONTROLLER, PIRATE).after(Buff(Summon.CARD, "TOY_518e"))


class TOY_518e:
    # Equal Earnings — +1 Attack (the data card carries no stat tags).
    tags = {GameTag.ATK: 1}


class TOY_520:
    """Observer of Mysteries"""

    # <b>Battlecry:</b> Cast 2 random <b>Secrets</b>. At the start of your
    # turn, destroy them.
    play = _ObserverCastSecrets(CONTROLLER)


class TOY_528:
    """Sing-Along Buddy"""

    # Your Hero Power triggers twice. Re-run the activated power's actions a
    # second time after each use (no extra cost — PlayHeroPower.do only runs
    # the activate actions). Activate.CARD is the actual power (or its chosen
    # subcard); Activate.TARGET is the original target.
    events = Activate(FRIENDLY_HERO_POWER).after(
        PlayHeroPower(Activate.CARD, Activate.TARGET)
    )


class TOY_530:
    """Playhouse Giant"""

    # Costs (1) less for each card you've drawn this game. Tracked via a
    # per-card counter bumped on every controller draw (Deck + Hand events),
    # mirroring Fye, the Setting Sun.
    cost_mod = -_PlayhouseCardsDrawn()

    class Deck:
        events = Draw(CONTROLLER).on(_PlayhouseBumpDrawn(SELF))

    class Hand:
        events = Draw(CONTROLLER).on(_PlayhouseBumpDrawn(SELF))


class TOY_531:
    """Li'Na, Shop Manager"""

    # Whenever you cast a spell, fill your board with random minions of that
    # Cost.
    events = OWN_SPELL_PLAY.after(_LiNaFillBoard(Play.CARD))


class TOY_601:
    """Factory Assemblybot"""

    # <b>Miniaturize</b> At the end of your turn, summon a 6/7 Bot that
    # attacks a random enemy.
    events = OWN_TURN_END.on(
        Summon(CONTROLLER, "TOY_601t2").then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
        )
    )


class TOY_601t:
    """Factory Assemblybot"""

    # <b>Mini</b> At the end of your turn, summon a 6/7 Bot that attacks a
    # random enemy.
    events = OWN_TURN_END.on(
        Summon(CONTROLLER, "TOY_601t2").then(
            Attack(Summon.CARD, RANDOM_ENEMY_CHARACTER)
        )
    )


class TOY_601t2:
    """Copybot"""

    # 6/6/7 vanilla Bot summoned by Factory Assemblybot.


class TOY_646:
    """Messmaker"""

    # <b>Lifesteal</b>, <b>Taunt</b> <b>Deathrattle:</b> Deal 1 damage to all
    # enemies.
    deathrattle = Hit(ENEMY_CHARACTERS, 1)


class TOY_670:
    """Giggling Toymaker"""

    # <b>Deathrattle:</b> Summon two 1/2 Mechs with <b>Taunt</b> and
    # <b>Divine Shield</b>. (Annoy-o-Tron — BOT_270t — is the exact 1/2
    # Mech with Taunt + Divine Shield.)
    deathrattle = Summon(CONTROLLER, "BOT_270t") * 2


class TOY_703:
    """Colifero the Artist"""

    # <b>Battlecry:</b> Draw a minion. Transform all other friendly minions
    # into copies of it.
    play = ForceDraw(RANDOM(FRIENDLY_DECK + MINION)).then(
        _ColiferoTransform(ForceDraw.TARGET)
    )


class TOY_814:
    """Bucket of Soldiers"""

    # <b>Deathrattle:</b> Summon five 1/1 Soldiers with random
    # <b>bonus effects</b>.
    deathrattle = _BucketSummonSoldiers(CONTROLLER)
