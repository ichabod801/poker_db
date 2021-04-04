This is the data dictionary for Ichabod's Poker Variant Database.

## Tables

* variants
	* variant_id
	* name
	* cards
	* players
	* rounds
	* max_seen
	* wilds
	* source_id
* variant_rules
	* variant_id
	* rule_id
	* order
* variant_tags
	* variant_id
	* tag_id
* rules
	* rule_id
	* type_id
	* short
	* full
* rule_types
	* type_id
	* name
* sources
	* source_id
	* name
	* link
* tags
	* tag_id
	* tag

## Variants

Standard Numbers
98: Undefined due to variability in cards or max seen.
99: Depends on the number of players
10N: N rounds plus Match Pot.
20N: N card plus more based on player choice
30N: N card plus more based on the deal.

Cards: The number of cards used to make the final hand.
	One issue is five down, five sets of two common cards. I used to say 7, now I say 17. How to code both?
		Go back to coding intuitively, and clarify with max-seen.
		And is that 5 ways to do 7, or 7 to 17. The first doesn't tell us the max number. The first is clearer.
			Really want 5 plus 5 ways to do 2.
			This shit gets complicated. There needs to be a limit on what I code.
		Could code 10717, 7 to 17.
			It would be better to split it into two numbers in the database.
			Note this would work for Three Five Seven, as 3 to 7.
	intuition doesn't work
Max Players: How many players can play without the deck running out of cards.
Betting Rounds: How many times you get to bet.
	We would want to add N plus player choice/deal, but 100s for match pot, that would not be consistent.
Max Seen: The maximum number of cards that go through your hand during the game.

## Tags

stud: up cards/down cards (dealt, flip games are not necessarily stud games)
draw: drawing. does not count instant rejects.
pass: passing
guts: in/out & match pot
common: common cards, including usable by multiple players but not all (love canal)
table: table cards
fee: involves extra fees, including forced bets and auctions.
wilds: has wilds
limited: has limited wilds
dead: has dead cards
odd-ranks: non-standard poker hands (not used if only split hand is odd ranks)
mod-ranks: standard poker hands with slight changes
odd-deal: not deal per player, doesn't include common cards (for things like dutch)
split-card: splits with a specific card
lowball
split-pot: splits to the pot beyond high/low and split-card
no-peek: includes other cards you do not see until showdown (deal one down right before showdown).
flip
must-fold
fee-fold
redeal: hands can be redealt, non-guts (make guts a search tag? no, want it for organizing)
jokers: there are jokers in the deck.
forced-bet: There are forced bets in the game.
qualifier: A restriction on hands, either on betting or winning.
straight: Cards dealt face down, no stud, draw, pass, guts, or common.
discard: Attrition through discarding.

### Have search tags, that group common searches. User editable?

plain: has only one tag
classic: stud or draw
poker-ranks: no (odd-ranks or mod-ranks)
fold: must-fold or fee-fold
hold-em: common and no (stud or draw)?

## Rules

standard card numbers
	108 is all available cards
	109 is the number of jokers in the game.
	110 is the number of cards initially dealt
	111 is the current number of cards in hand
	112 is the current number of up cards in hand
	113 is the current number of down cards in hand
	114 is the number of cards in the deck.
	115	is the number of cards in a layout feature
	116 is the number of cards until an event happens
	117 is the number of hands a player has
	118 is the number of each player's discarded cards
	119 is the number of remaining no peek cards
	200+ is cards per player (for typically absolute rules)
	300+ is absolute number of cards (for typically per player rules)
	400+ is cards per layout feature (row/column/whatever)
	500+ is cards per common card
	600+ is cards per table card
	for the hundreds, an even hundred is an odd value based on that value.
		200 is an odd value based on the number of players.

bet
	a round of payments into the pot.
	0 = changes to ante.
	1 = full betting round
	2 = multiple hands
common
	deal common cards
	use turn for flipping them over.
	n is total cards dealt
dead
	Cards with no value.
	number is absolute number of cards.
	standard text: foos do not count toward hand value.
deal
	deal cards from the deck, without corresponding discards
	includes redeals (cards = 110/cards initially dealt)
	number is the cards dealt to each player (expected/median)
deck
	add or remove cards from the deck
	number is the change in deck size.
declare
	hi/low declarations and similar.
	same card numbers as showdown
		0 = declare in/out
deprecated
	deprecated rules are no longer used.
discard
	remove cards from hand with out getting cards back.
	number is how many each player discards. (max if necc)
draw
	discard cards to get more cards from the deck (or somewhere)
	includes twisting (paying to draw).
	number is the max number of cards you can draw.
hand
	rules determining which cards you can use.
	number is the number of cards mentioned/manipulated.
flip
	flipping over cards from your hand.
	number is the max number each player can flip
fold
	Actions/events that cause a player to fold.
	-2 = paid reentry
	-1 = reentry
	0 = forced fold
	1 = pay or fold
	2 = other player can force fold
limited
	limited wild cards. Bugs, ambivalents, that sort of thing.
		also includes rank boosters. Note that one wild typically boosts more than one rank.
	cards same as wilds
match
	Matching the pot or other fees after a declare or showdown.
	Cards:
		0 = losers match
		1 = winners match
		2 = could have won match
		3 = all match
		4 = out match
		5 = in match
other
	everything else, review these at the end. [done]
	Cards
		1 = shifting games
		2 = dice
		3 = pot actions
		4 = odd fees
		5 = card actions
pass
	pass cards from one player to another
	number is max cards passed.
qualifier
	Something that must be beat to win/open.
		0 = no qualifier
		1 = set qualifier
		2 = deck qualifier
		3 = table qualifier
		4 = other
rank
	How hands are ranked against each other.
		1 = standard
		2 = modified standard
		3 = split cards
		4 = points
		5 = other
repeat
	repeat a number of actions for a number of rounds, or until a condition is met.
	number is number of actions repeated
	-1 for a condition related to repeating actions, independent of the repeat
showdown
	see who has the best hand and divide the pot.
	instant win goes under win
	Use a bit map:
		1 = low
		2 = high
		4 = both
		8 = card
		16 = other
		32 = other II
		64 = tba
		high/low = 3
		high/low/both = 7
		high/card = 10
		low/low = 17
		high/high = 18
shuffle
	(re)shuffle the deck somehow
	0 = conditional shuffle
	1 = reshuffle
stack
	put your cards into a stack.
	111 all cards
	otherwise number of cards stacked
table
	deal table cards
	use turn for flipping them over
	n is total cards dealt
	201+ for per player
turn
	flip over table or common cards.
variant
	play a specific variant. For things like HORSE, which would have a combined tag.
wild
	includes wilds, double wilds (double the cards), half wilds (halve the cards)
	number should be the number of wild cards (max) the rule introduces
		double wilds count as 2 cards
		0 is a rule that nefs wilds, or provides wilds to the table.
win
	instant win rule
	1 = specific cards
	2 = multiple wins
