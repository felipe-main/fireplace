from ..utils import *


##
# Remixed — every Remixed base card rotates each turn while in hand
# through a fixed pool of "variant" tokens. The base card has no play
# effect of its own; on play it fires the currently-rotated variant's
# play script. Variant ids are JAM_XXXt / t2 / t3 / t4 in data.


REMIX_POOLS = {
	"JAM_000": ["JAM_000t", "JAM_000t2", "JAM_000t3", "JAM_000t4"],
	"JAM_012": ["JAM_012t", "JAM_012t2", "JAM_012t3", "JAM_012t4"],
	"JAM_015": ["JAM_015t", "JAM_015t2", "JAM_015t3", "JAM_015t4"],
	"JAM_018": ["JAM_018t", "JAM_018t2", "JAM_018t3", "JAM_018t4"],
	"JAM_033": ["JAM_033t", "JAM_033t2", "JAM_033t3", "JAM_033t4"],
}


def _pick_remix_initial(card):
	"""Stamp an initial variant id when the Remixed card first enters
	hand if one isn't already set. Random pick from its pool."""
	if getattr(card, "_remix_variant_id", None):
		return
	pool = REMIX_POOLS.get(card.id)
	if not pool:
		return
	card._remix_variant_id = card.game.random.choice(pool)


class _RemixRotate(TargetedAction):
	"""At OWN_TURN_BEGIN while in hand, pick a different variant from
	this Remixed card's pool. Source = the Remixed card (SELF)."""

	TARGET = ActionArg()

	def do(self, source, target):
		pool = REMIX_POOLS.get(source.id)
		if not pool:
			return
		cur = getattr(source, "_remix_variant_id", None)
		candidates = [v for v in pool if v != cur] or pool
		source._remix_variant_id = source.game.random.choice(candidates)


class _RemixFireVariant(TargetedAction):
	"""On play, fire the currently-rotated variant's play script via
	cheat_action. SELF in the variant resolves to the Remixed card."""

	TARGET = ActionArg()

	def do(self, source, target):
		vid = getattr(source, "_remix_variant_id", None)
		if not vid:
			# Defensive: pick on the fly if the rotation never ran (e.g.
			# card was added & played the same turn).
			pool = REMIX_POOLS.get(source.id)
			if not pool:
				return
			vid = source.game.random.choice(pool)
		# Read the variant's play actions directly from its scripts
		# definition — we don't want to instantiate the variant card or
		# fire its battlecry pipeline, just run its play side-effects.
		from .. import db as _db
		from .. import get_script_definition
		scripts = get_script_definition(vid)
		if scripts is None:
			return
		play_attr = getattr(scripts, "play", None)
		if play_attr is None:
			return
		actions = play_attr if isinstance(play_attr, (tuple, list)) else (play_attr,)
		for a in actions:
			source.game.cheat_action(source, [a])
