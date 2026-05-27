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
			# controller hand transfer requires direct list muniging:
			# the engine's zone setter only swaps within one player.
			ctrl.hand.remove(card)
			if len(opp.hand) >= opp.max_hand_size:
				card.discard()
				continue
			card.controller = opp
			opp.hand.append(card)


class _RockDuelTick(TargetedAction):
	"""Elite Tauren Champion's Rock Duel — at each OWN_TURN_END, if
	the turn-ending player did NOT spend all their mana, deal 8 damage
	to them. SOURCE = the per-player Rock-Duel enchant; TARGET = the
	player whose turn just ended."""

	TARGET = ActionArg()

	def do(self, source, target):
		if target.used_mana < target.max_mana:
			source.game.cheat_action(source, [Hit(target.hero, 8)])


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
	# turn or else they take 8 damage. Implemented by stamping the
	# Rock-Duel enchant on both players (JAM_037e) — its events fire on
	# EndTurn for either player and apply the 8-damage penalty.
	play = FINALE & (
		Buff(CONTROLLER, "JAM_037e"),
		Buff(OPPONENT, "JAM_037e"),
	)


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
	# Elite Tauren Champion's Rock Duel — at OWN_TURN_END, the player
	# this enchant rides on takes 8 damage if they ended their turn
	# with unspent mana. Persists for the rest of the game.
	tags = {
		GameTag.CARDNAME: "ROCK DUEL!",
		GameTag.CARDTYPE: CardType.ENCHANTMENT,
	}
	events = OWN_TURN_END.on(_RockDuelTick(CONTROLLER))
