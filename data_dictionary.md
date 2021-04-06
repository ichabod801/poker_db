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
	* rule_order
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

### Standard Numbers

* 98: Undefined due to variability in cards or max seen.
* 99: Depends on the number of players
* 10N: N rounds plus Match Pot.
* 20N: N card plus more based on player choice
* 30N: N card plus more based on the deal.

### Data Fields

* Variant ID: The unique numerica ID for the variant.
	* It was originally it's place in the variant tree, in depth first order. 
	* That is not necessarily true any more.
* Name: Names (and aliases) in the database are unique. 
	* This is not true in the real world.
	* Multiple variants with the same name are distinguished by roman numerals.
* Cards: The number of cards used to make the final hand.
* Max Players: How many players can play without the deck running out of cards.
* Betting Rounds: How many times you get to bet.
* Max Seen: The maximum number of cards that go through your hand during the game.
* Wilds: The (maximum) number of wild cards in the game.
* Source ID: The ID for the source of the variant.
	* The source is not necessarily the creator, but the place where I found the game.

## Tags

### Primary Tags

These are tags commonly used to classify poker games by type.

* common: The game has common cards, including those usable by multiple players but not all.
* discard: Games using attrition through discarding.
* draw: Players discarding cards to get new ones. Does not count instant rejects.
* flip: The game involves flipping down cards face up.
* guts: The game involves declaring in or out, losers matching the pot, until one person goes in.
	* Includes games with legs.
* pass: Cards being passed from one player to another.
* straight: Cards dealt face down, no stud, draw, pass, guts, or common.
* stud: The game has cards dealt face up. Does not count flipping down cards up (see 'flip').

### Secondary Tags

These tags involve other features common to many poker games.

* dead: The game has dead cards, which do not contribute to the value of hands.
* fee: The game involves extra fees, including auctions.
* fee-fold: The game has conditions which force players pay a fee or fold their hand.
* forced-bet: There are forced bets in the game.
* jokers: There are jokers in the deck.
* limited: The game has limited wild cards, which have limits on what they can represent.
* lowball: The low hand wins the game.
* mod-ranks: The game uses standard poker hands with slight changes.
* must-fold: The game has conditions which force players to fold with no recourse.
* no-peek: The game includes cards you do not see until showdown, excluding those dealt just before the showdown.
* odd-deal: The cards are not deal to the players on a per player basis.
* odd-deck: The game uses something besides a standard 52 card deck.
* odd-ranks: The game uses non-standard hand ranks. This is not used if only split hand is odd ranks.
* qualifier: There is a restriction on hands, either on betting or winning.
* redeal: Hands can be redealt, non-guts.
* split-card: The pot is split with whoever has a specified card.
* split-pot: The pot is split in some way besides high/low or split-card
* table: The game has table cards.
* wilds: The game has full wild cards. See also 'limited' and 'dead'.

### Search Tags

These are tags that can be used in the interface, but that are not stored in the database. That is, they are calculated from other tags.

* classic: stud or draw
* fold: must-fold or fee-fold
* plain: has only one tag
* poker-ranks: no (odd-ranks or mod-ranks)

## Rules

Special card numbers used in rules are listed below. Note the 200 and 300 ranges especially. Some rule types (like deal) have card numbers on a per player basis. Cards = 2 means two cards are dealt per player. Other rules (like table) have an absolute card number. Cards = 2 means two cards are dealt total. The 200 and 300 ranges allow for switching that around, and dealing one card to one player, or one table card per player.
	
* 108 is all available cards
* 109 is the number of jokers in the game.
* 110 is the number of cards initially dealt
* 111 is the current number of cards in hand
* 112 is the current number of up cards in hand
* 113 is the current number of down cards in hand
* 114 is the number of cards in the deck.
* 115 is the number of cards in a layout feature
* 116 is the number of cards until an event happens
* 117 is the number of hands a player has
* 118 is the number of each player's discarded cards
* 119 is the number of remaining no peek cards
* 200+ is cards per player (for typically absolute rules)
* 300+ is absolute number of cards (for typically per player rules)
* 400+ is cards per layout feature (row/column/whatever)
* 500+ is cards per common card
* 600+ is cards per table card

Not all card numbers refer to actual cards. Some rule types just use the card number to differentiate different sub-types of the rule type. The specific rule types with definitions of their card numbers are below.

All rules have a short text and a full text. The full text is the text that should be used when playing the game. The short text is there for short summaries of how the game plays, as in a list of games. Note that the short text never ends in a period (it is expected to be joined by semi-colons) while the full text always ends in a period.

### bet

Rules for rounds of payments into the pot.

* 0 = changes to ante.
* 1 = full betting round
* 2 = multiple hands

### common

Rules for dealing common cards. Use turn for flipping face-down commons over. The card number is the number of cards dealt.

### dead
	
Rules specifying cards with that do not contribute to hand value. The card number is absolute number of dead cards.

### deal

Rules for dealing cards to players from the deck. This includes If players discard cards to get cards from the deck, that is a draw rule instead. The card number is the number of cards dealt to each player.

### deck

Rules for adding or removing cards from the deck. The card number is the change to the size of the deck. So cards = 2 means two cards are added to the deck, and cards = -4 means four cards are removed from the deck.

### declare
	
Rules for player declarations, such as declaring whether they are going for the high or low hand, or if they are staying in or going out in a guts game. Cards are the same as for showdown rules, but cards = 0 is for in/out declarations.

### deprecated

Deprecated rules are no longer used. These should have all been removed from the database at this point, but the rule type was left in as a possibility in case more rules get deprecated in the future. All deprecated rules should have a card number of -108.

### discard

Rules for removing cards from a player's hand with out getting cards back. The card number is how many cards each player discards. If necessary, the maximum possible number of discarded cards is used.

### draw
	
Rules for discarding cards to get more cards from the deck (or somewhere). This includes 'twisting,' which is paying money to the pot in order to draw cards. The card number is the maximum number of cards each player can draw.

### hand
	
Rules determining which cards you can use in your hand. The card number is the number of cards mentioned/manipulated.

### flip
	
Rules for flipping down cards face up, from a player's hand. The card number is the maximum number of cards a player can flip.

### fold

Rules for actions or events that can cause a player to fold. Cards numbers are:

* -2 = You may pay to reenter the game after folding.
* -1 = You may reenter the game for free after folding.
* 0 = You are forced to fold with no recourse.
* 1 = You must pay a fee to the pot or forld.
* 2 = Other players can force you to fold.

### limited

Rules for limited wild cards. This includes bugs, which can count as an ace or be used to complete a straight or a flush; ambivalent cards, which can change their rank one step up or down; or rank boosters, which can change a hand's value up or down a rank. Rank boosters are considered limited wild cards because full wilds typically boost a hand by more than one rank. For example, a wild boosts a pair over two pair to three of a kind, and boosts two pair all the way to full house. The card numbers are the same as for wilds.

### match
	
Rules for matching the pot or other fees after a declare or showdown. The card number specifies who has to match:

* 0 = losers match
* 1 = winners match
* 2 = could have won match
* 3 = all match
* 4 = out match
* 5 = in match

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
