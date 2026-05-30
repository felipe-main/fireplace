from ..utils import *


##
# Custom actions


class _NemsyDrawDemon(TargetedAction):
	"""Game Master Nemsy battlecry — draw a Demon from your deck and
	remember which card was drawn so the deathrattle can swap with it."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		demons = [c for c in ctrl.deck if Race.DEMON in getattr(c, "races", [])]
		if not demons:
			return
		import random
		pick = random.choice(demons)
		source.game.cheat_action(source, [Draw(ctrl, pick)])
		# Remember the drawn demon entity for the deathrattle swap.
		source._nemsy_demon = pick


class _NemsySwap(TargetedAction):
	"""Game Master Nemsy deathrattle — swap places with the Demon drawn
	by the battlecry. The drawn Demon (still in hand) is summoned into
	Nemsy's board slot, and the ACTUAL Nemsy entity is returned to hand via
	Bounce (the same card, not a fresh copy). Bounce also handles the
	full-hand case by destroying instead, matching live Hearthstone."""

	TARGET = ActionArg()

	def do(self, source, target):
		demon = getattr(source, "_nemsy_demon", None)
		ctrl = source.controller
		if demon is None:
			return
		# The drawn demon must still be in the player's hand to swap.
		if demon.zone != Zone.HAND:
			return
		# Summon the demon into play (Nemsy's slot — it died, so append).
		source.game.cheat_action(source, [Summon(ctrl, demon)])
		# Return the actual Nemsy entity to hand (swap places). Bounce moves
		# this very card, so any tracking that identifies "the same Nemsy"
		# is preserved; on hand-entry it resets to base like every bounce.
		source.game.cheat_action(source, [Bounce(source)])


class _CursedCampaignDeathrattle(TargetedAction):
	"""Final Session (TOY_527e) — when the enchanted minion dies, summon
	two copies of it that are Dormant for 2 turns."""

	TARGET = ActionArg()

	def do(self, source, target):
		# `source` is the enchantment; its owner is the dying minion.
		host = getattr(source, "owner", None)
		if host is None:
			return
		ctrl = host.controller
		base_id = host.id
		for _ in range(2):
			if len(ctrl.field) >= 7:
				break
			source.game.cheat_action(source, [Summon(ctrl, base_id)])
			if ctrl.field and ctrl.field[-1].id == base_id:
				source.game.cheat_action(
					source, [Dormant(ctrl.field[-1], 2)]
				)


class _WheelOfDeathTick(TargetedAction):
	"""Wheel of Death Counter (TOY_529e1) — counts down at the start of
	each of your turns. When the counter reaches 0, destroy the enemy
	hero."""

	TARGET = ActionArg()

	def do(self, source, target):
		ticks = getattr(source, "_wheel_ticks", 0) + 1
		source._wheel_ticks = ticks
		if ticks >= 5:
			source.game.cheat_action(
				source, [Destroy(source.controller.opponent.hero)]
			)
			source.game.cheat_action(source, [Destroy(source)])


class _CraneGameSummon(TargetedAction):
	"""Crane Game — "Summon copies of two Demons in your deck." Two independent
	random picks WITH replacement (matching live HS), so a deck with a single
	Demon yields two copies of it rather than just one. Each pick rolls over
	the full demon pool, so the same Demon can legitimately be chosen twice."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		demons = [c for c in ctrl.deck if Race.DEMON in getattr(c, "races", [])]
		if not demons:
			return
		import random
		copier = ExactCopy(None)
		for _ in range(2):
			if len(ctrl.field) >= 7:
				break
			demon = random.choice(demons)
			copy = copier.copy(source, demon)
			source.game.cheat_action(source, [Summon(ctrl, copy)])


class _EndgameResurrect(TargetedAction):
	"""Endgame — resurrect your last Demon that died (the most recently
	deceased friendly Demon)."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		demons = [
			c for c in ctrl.graveyard
			if c.type == CardType.MINION
			and Race.DEMON in getattr(c, "races", [])
		]
		if not demons:
			return
		# Graveyard preserves death order; the last entry died most recently.
		last = demons[-1]
		source.game.cheat_action(source, [Summon(ctrl, last.id)])


##
# Minions


class TOY_524:
	"""Game Master Nemsy"""

	# Battlecry: Draw a Demon. Deathrattle: Swap places with it.
	play = _NemsyDrawDemon(SELF)
	deathrattle = _NemsySwap(SELF)


class TOY_526:
	"""Malefic Rook"""

	# Battlecry: Attack YOUR hero.
	play = Attack(SELF, FRIENDLY_HERO)


class TOY_914:
	"""Wretched Queen"""

	# Taunt. Deathrattle: Summon two 4/6 Knights with Taunt.
	deathrattle = Summon(CONTROLLER, "TOY_914t") * 2


class TOY_914t:
	"""Ignoble Knight"""

	# Taunt. (Taunt lives in data.)


class TOY_915:
	"""Tabletop Roleplayer"""

	# Miniaturize. Battlecry: Give a friendly Demon +2 Attack and Immune
	# this turn. (Engine adds the paired Mini token automatically.)
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_TARGET_WITH_RACE: Race.DEMON,
	}
	play = Buff(TARGET, "TOY_915e")


class TOY_915t:
	"""Tabletop Roleplayer"""

	# Mini. Battlecry: Give a friendly Demon +2 Attack and Immune this turn.
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
		PlayReq.REQ_TARGET_WITH_RACE: Race.DEMON,
	}
	play = Buff(TARGET, "TOY_915e")


class TOY_915e:
	# In Character — +2 Attack and Immune this turn. TAG_ONE_TURN_EFFECT in
	# data auto-clears at end of turn; the immune tags aren't parsed from
	# data so declare them here.
	tags = {
		GameTag.ATK: 2,
		GameTag.CANT_BE_DAMAGED: True,
		GameTag.CANT_BE_TARGETED_BY_OPPONENTS: True,
	}


class TOY_916:
	"""Sketch Artist"""

	# Battlecry: Draw a Shadow spell. Get a temporary copy of it.
	play = (Find(FRIENDLY_DECK + SPELL + SHADOW_SPELL)) & ForceDraw(
		RANDOM(FRIENDLY_DECK + SPELL + SHADOW_SPELL)
	).then(
		Give(CONTROLLER, Copy(ForceDraw.TARGET)).then(GiveTemporary(Give.CARD))
	)


##
# Spells


class TOY_527:
	"""Cursed Campaign"""

	# Give a friendly minion "Deathrattle: Summon two copies of this minion
	# that are Dormant for 2 turns."
	requirements = {
		PlayReq.REQ_TARGET_TO_PLAY: 0,
		PlayReq.REQ_MINION_TARGET: 0,
		PlayReq.REQ_FRIENDLY_TARGET: 0,
	}
	play = Buff(TARGET, "TOY_527e")


class TOY_527e:
	# Final Session — grants a deathrattle that summons two Dormant copies.
	tags = {GameTag.DEATHRATTLE: True}
	deathrattle = _CursedCampaignDeathrattle(SELF)


class TOY_529:
	"""Wheel of DEATH!!!"""

	# Destroy your deck. In 5 turns, destroy the enemy hero.
	play = Destroy(FRIENDLY_DECK), Buff(FRIENDLY_HERO, "TOY_529e1")


class TOY_529e1:
	# Wheel of Death Counter — ticks down at the start of each of your
	# turns; destroys the enemy hero on the 5th tick.
	events = OWN_TURN_BEGIN.on(_WheelOfDeathTick(SELF))


class TOY_883:
	"""Table Flip"""

	# Deal $3 damage to all enemy minions. Costs (1) less for each other
	# card in your hand.
	cost_mod = -Count(FRIENDLY_HAND - SELF)
	play = Hit(ENEMY_MINIONS, 3)


class TOY_884:
	"""Crane Game"""

	# Summon copies of two Demons in your deck.
	play = _CraneGameSummon(SELF)


class TOY_886:
	"""Endgame"""

	# Resurrect your last Demon that died.
	play = _EndgameResurrect(SELF)


##
# Whizbang's Workshop mini-set


class _DominoEffect(TargetedAction):
    """Deal 2 to the target minion, then topple along one direction (toward
    whichever side has more minions; ties go right), dealing 1 more each hop.
    The chain is snapshotted before any damage so deaths don't shift it."""

    TARGET = ActionArg()

    def do(self, source, target):
        board = list(target.controller.field)
        if target not in board:
            return
        idx = board.index(target)
        left = idx
        right = len(board) - idx - 1
        step = 1 if right >= left else -1
        chain = []
        i = idx
        while 0 <= i < len(board):
            chain.append(board[i])
            i += step
        dmg = 2
        for minion in chain:
            amt = source.controller.get_spell_damage(source, dmg)
            source.game.cheat_action(source, [Hit(minion, amt)])
            dmg += 1


class MIS_027:
    """Domino Effect"""

    # Deal 2 damage to a minion. Repeat to the left or right, dealing 1 more
    # damage each time.
    requirements = {
        PlayReq.REQ_TARGET_TO_PLAY: 0,
        PlayReq.REQ_MINION_TARGET: 0,
    }
    play = _DominoEffect(TARGET)


class MIS_703:
    """INFERNAL!"""

    # Taunt (data). Battlecry: Set your hero's remaining Health to 15.
    play = SetCurrentHealth(FRIENDLY_HERO, 15)


class MIS_707:
    """Mass Production"""

    # Draw 2 cards. Deal 3 damage to your hero. Shuffle 2 copies of this
    # into your deck.
    play = (
        Draw(CONTROLLER) * 2,
        Hit(FRIENDLY_HERO, 3),
        Shuffle(CONTROLLER, "MIS_707") * 2,
    )
