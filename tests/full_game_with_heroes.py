#!/usr/bin/env python
"""
Variant of tests/full_game.py focused on exercising the hero-replacement path.

Each player's deck is GUARANTEED at least one cost-bearing hero card (chosen
at random from HERO_CARDS for the rolled class). The random draft pool also
keeps all other cost-bearing hero cards eligible, so extra hero swaps can
appear naturally. Cosmetic cost-0 skins remain excluded.
"""
import random
import sys

from hearthstone.enums import CardClass, CardType

from fireplace import cards
from fireplace.deck import Deck
from fireplace.exceptions import GameOver
from fireplace.game import Game
from fireplace.logging import log
from fireplace.player import Player
from fireplace.utils import play_turn, random_class

sys.path.append("..")


HERO_CARDS = {
	CardClass.DRUID:       ["ICC_832", "AV_205"],
	CardClass.HUNTER:      ["TRL_065", "ICC_828", "AV_113"],
	CardClass.MAGE:        ["ICC_833", "YOD_009", "AV_200"],
	CardClass.PALADIN:     ["ICC_829", "AV_206"],
	CardClass.PRIEST:      ["ICC_830", "DRG_660", "AV_207"],
	CardClass.ROGUE:       ["ICC_827", "DRG_610", "AV_203"],
	CardClass.SHAMAN:      ["GIL_504", "ICC_481", "DRG_620", "AV_258"],
	CardClass.WARLOCK:     ["VAN_EX1_323", "ICC_831", "DRG_600", "AV_316"],
	CardClass.WARRIOR:     ["BOT_238", "DRG_650", "ICC_834", "AV_202"],
	CardClass.DEMONHUNTER: ["AV_204"],
}


def random_draft_with_heroes(card_class: CardClass, exclude=(), include=()):
	"""
	Same as fireplace.utils.random_draft but keeps cost-bearing HERO cards
	in the candidate pool. Cosmetic cost-0 skins are still excluded.
	"""
	deck = list(include)
	collection = []
	for card_id in cards.db.keys():
		if card_id in exclude:
			continue
		cls = cards.db[card_id]
		if not cls.collectible:
			continue
		if cls.type == CardType.HERO and cls.cost == 0:
			continue
		if cls.card_class and cls.card_class not in [card_class, CardClass.NEUTRAL]:
			continue
		collection.append(cls)

	while len(deck) < Deck.MAX_CARDS:
		card = random.choice(collection)
		if deck.count(card.id) < card.max_count_in_deck:
			deck.append(card.id)
	return deck


def setup_game():
	class1 = random_class()
	class2 = random_class()
	hero1 = random.choice(HERO_CARDS[class1])
	hero2 = random.choice(HERO_CARDS[class2])
	deck1 = random_draft_with_heroes(class1, include=[hero1])
	deck2 = random_draft_with_heroes(class2, include=[hero2])
	log.info("Player1 (%s) seeded with %s", class1.name, hero1)
	log.info("Player2 (%s) seeded with %s", class2.name, hero2)
	player1 = Player("Player1", deck1, class1.default_hero)
	player2 = Player("Player2", deck2, class2.default_hero)
	game = Game(players=(player1, player2))
	game.start()
	return game


def play_full_game():
	game = setup_game()

	for player in game.players:
		log.info("Can mulligan %r" % (player.choice.cards))
		mull_count = game.random.randint(0, len(player.choice.cards))
		cards_to_mulligan = game.random.sample(player.choice.cards, mull_count)
		player.choice.choose(*cards_to_mulligan)

	while True:
		play_turn(game)

	return game


def test_full_game_with_heroes():
	try:
		play_full_game()
	except GameOver:
		log.info("Game completed normally.")


def main():
	cards.db.initialize()
	if len(sys.argv) > 1:
		numgames = sys.argv[1]
		if not numgames.isdigit():
			sys.stderr.write("Usage: %s [NUMGAMES]\n" % (sys.argv[0]))
			exit(1)
		for i in range(int(numgames)):
			log.info(f"test full game with heroes: {i+1}/{int(numgames)}")
			test_full_game_with_heroes()
	else:
		test_full_game_with_heroes()


if __name__ == "__main__":
	main()
