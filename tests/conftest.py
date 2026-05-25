import pytest

from fireplace import cards


@pytest.fixture(scope="session", autouse=True)
def _initialize_card_db():
	if not cards.db.initialized:
		cards.db.initialize()
