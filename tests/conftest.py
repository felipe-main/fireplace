import random
import zlib

import pytest

from fireplace import cards


@pytest.fixture(scope="session", autouse=True)
def _initialize_card_db():
	if not cards.db.initialized:
		cards.db.initialize()


@pytest.fixture(autouse=True)
def _seed_rng(request, monkeypatch):
	# Two RNG sources drive test behavior:
	#   1) tests/utils.py uses Python's global `random` for class picking
	#      and `random_draft()` deck construction.
	#   2) BaseGame.__init__ seeds its own `Random` from the OS when no
	#      seed is passed; that drives in-game rolls (Discover pools,
	#      random summons, Sneed's deathrattle, etc.).
	# Derive a stable seed from the test nodeid so each test is
	# reproducible across runs AND independent of test ordering.
	seed = zlib.crc32(request.node.nodeid.encode("utf-8"))
	random.seed(seed)

	from fireplace.game import BaseGame
	original_init = BaseGame.__init__

	def patched_init(self, players, seed=None):
		if seed is None:
			seed = zlib.crc32(request.node.nodeid.encode("utf-8"))
		original_init(self, players, seed=seed)

	monkeypatch.setattr(BaseGame, "__init__", patched_init)
