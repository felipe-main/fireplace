from ..utils import *


class _HollowHoundAdjacent(TargetedAction):
	"""Hollow Hound — after this attacks, also damage minions adjacent
	to the defender. DEFENDER comes in via Attack.DEFENDER (as a list
	since DEFENDER is a CardArg targeting form). Hero attacks have no
	neighbours; no-op."""

	TARGET = ActionArg()
	DEFENDER = ActionArg()

	def do(self, source, target, defender):
		# Defender arrives as a list (CardArg semantics).
		if isinstance(defender, (list, tuple)):
			defender = defender[0] if defender else None
		if defender is None or defender.zone != Zone.PLAY:
			return
		if defender.type != CardType.MINION:
			return
		field = defender.controller.field
		if defender not in field:
			return
		idx = field.index(defender)
		neighbours = []
		if idx > 0:
			neighbours.append(field[idx - 1])
		if idx + 1 < len(field):
			neighbours.append(field[idx + 1])
		if not neighbours:
			return
		# Hollow Hound deals its own current Attack to each neighbour.
		dmg = target.atk
		source.game.cheat_action(source, [Hit(neighbours, dmg)])


class _HiddenMeaningTrigger(TargetedAction):
	"""Hidden Meaning — at the end of the opponent's turn, if they have
	no Mana left, summon a random 3-cost minion. Self-reveals after
	firing (consumed Secret)."""

	TARGET = ActionArg()

	def do(self, source, target):
		opp = source.controller.opponent
		if opp.max_mana <= 0:
			return
		if opp.max_mana - opp.used_mana > 0:
			return
		picker = RandomMinion(cost=3)
		pick = picker.evaluate(source)
		cid = pick[0] if isinstance(pick, list) else pick
		if not cid:
			return
		source.game.cheat_action(
			source,
			[Reveal(source), Summon(source.controller, cid)],
		)


##
# Minions

class JAM_004:
	"""Hollow Hound"""

	# Lifesteal, Rush (both in data). Also damages minions next to
	# whomever this attacks. Listener fires on this card's own Attack;
	# DEFENDER is read from Attack.DEFENDER.
	events = Attack(SELF).on(_HollowHoundAdjacent(SELF, Attack.DEFENDER))


##
# Spells

class JAM_003:
	"""Hidden Meaning"""

	# Secret: When your opponent ends their turn with no Mana, summon
	# a random 3-Cost minion. EndTurn(OPPONENT) is the standard secret
	# pattern for "opponent ends their turn" triggers.
	secret = EndTurn(OPPONENT).on(_HiddenMeaningTrigger(SELF))
