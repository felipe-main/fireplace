from ..utils import *
from .utils import _RemixRotate, _RemixFireVariant


class _SpeakerStomperBuff(TargetedAction):
	"""Speaker Stomper — Battlecry: enemy spells cost (2) more next
	turn. Stamps a +2-cost enchant on each spell currently in the
	opponent's hand; the enchant auto-clears at the opponent's next
	OWN_TURN_END (just like Cold Feet)."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		spells = [c for c in opp.hand if c.type == CardType.SPELL]
		if not spells:
			return
		source.game.cheat_action(source, [Buff(spells, "JAM_034e")])


class _GrimtotemDiscardForDraw(TargetedAction):
	"""Grimtotem Buzzkill — Battlecry: Discard a weapon to draw 3
	cards. If no weapon in hand, no-op."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		weapons = [c for c in ctrl.hand if c.type == CardType.WEAPON]
		if not weapons:
			return
		pick = source.game.random.choice(weapons)
		source.game.cheat_action(
			source,
			[Discard(pick), Draw(ctrl) * 3],
		)


class _MagathaDrawAndShare(TargetedAction):
	"""Magatha, Bane of Music — Battlecry: Draw 5 cards. Give any
	spells drawn to your opponent. Track pre-hand-set, draw 5, then
	move any new spells to the opponent's hand."""

	TARGET = ActionArg()

	def do(self, source, target):
		ctrl = source.controller
		opp = ctrl.opponent
		pre_ids = {id(c) for c in ctrl.hand}
		source.game.cheat_action(source, [Draw(ctrl) * 5])
		drawn = [c for c in ctrl.hand if id(c) not in pre_ids]
		for card in drawn:
			if card.type != CardType.SPELL:
				continue
			# Move from controller's hand to opponent's hand. Cross-
			# controller hand transfer requires direct list munging:
			# the engine's zone setter only swaps within one player.
			# Handle opp-hand-full BEFORE detaching from ctrl.hand so
			# discard() runs through the normal HAND -> GRAVEYARD pipeline.
			if len(opp.hand) >= opp.max_hand_size:
				card.discard()
				continue
			ctrl.hand.remove(card)
			card.controller = opp
			opp.hand.append(card)


class _RockDuelTick(TargetedAction):
	"""Elite Tauren Champion's Rock Duel — at TURN_END, if the
	turn-ending player did NOT spend all their mana, deal 8 damage to
	them. The turn-ending player is game.current_player at the moment
	EndTurn fires (before begin_turn swaps it)."""

	TARGET = ActionArg()

	def do(self, source, target):
		turn_player = source.game.current_player
		if turn_player is None:
			return
		if turn_player.used_mana < turn_player.max_mana:
			source.game.cheat_action(source, [Hit(turn_player.hero, 8)])


##
# Minions

class JAM_033:
	"""Remixed Musician"""

	# Rush (data). Gains an extra effect in your hand that changes
	# each turn. Variants stamp a Rush minion with one extra keyword.
	class Hand:
		events = OWN_TURN_BEGIN.on(_RemixRotate(SELF))
	play = _RemixFireVariant(SELF)


class JAM_033t:
	"""Cathedral Musician"""
	# Rush + Divine Shield
	play = GiveDivineShield(SELF)


class JAM_033t2:
	"""Tropical Musician"""
	# Rush + Windfury
	play = GiveWindfury(SELF)


class JAM_033t3:
	"""Romantic Musician"""
	# Rush + Lifesteal
	play = GiveLifesteal(SELF)


class JAM_033t4:
	"""Noise Musician"""
	# Rush + Poisonous
	play = GivePoisonous(SELF)


class JAM_034:
	"""Speaker Stomper"""

	# Tradeable (data — handled by Card.use_tradeable). Battlecry:
	# Enemy spells cost (2) more next turn.
	play = _SpeakerStomperBuff(CONTROLLER)


class JAM_035:
	"""Grimtotem Buzzkill"""

	# Battlecry: Discard a weapon to draw 3 cards.
	play = _GrimtotemDiscardForDraw(CONTROLLER)


class JAM_036:
	"""Magatha, Bane of Music"""

	# Battlecry: Draw 5 cards. Give any spells drawn to your opponent.
	play = _MagathaDrawAndShare(CONTROLLER)


class JAM_037:
	"""Elite Tauren Champion"""

	# Finale: Start a ROCK DUEL! Players must spend all their Mana each
	# turn or else they take 8 damage. Stamp a SINGLE Rock-Duel enchant
	# on the controller; it listens for TURN_END (any player) and
	# damages whoever ended their turn with unspent mana.
	play = FINALE & Buff(CONTROLLER, "JAM_037e")


##
# Enchantments

@custom_card
class JAM_034e:
	# Speaker Stomper — +2 cost on enemy hand spells; auto-clears at
	# the next end of the controller's turn (i.e. the opponent's turn
	# from the spell-owner's perspective).
	tags = {
		GameTag.CARDNAME: "Loud",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
		GameTag.COST: 2,
	}
	events = OWN_TURN_END.on(Destroy(SELF))


@custom_card
class JAM_037e:
	# Elite Tauren Champion's Rock Duel — single enchant on the
	# original ETC controller. Fires on TURN_END (either player); the
	# turn-ending Player is the EndTurn target, and the action damages
	# that player's hero if they had leftover mana.
	tags = {
		GameTag.CARDNAME: "ROCK DUEL!",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = TURN_END.on(_RockDuelTick(SELF))
