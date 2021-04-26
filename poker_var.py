"""
poker_db.py

A command line interface for Ichabod's Poker Variant Database.

WARNING: This program uses eval in Viewer.do_shell. Before running this program
over a network or in other insecure situations, you should nerf that method.

Copyright (C) 2021 by Craig O'Brien and any IPVDB contributers.

This program and the attached database are free software: you can redistribute 
it and/or modify it under the terms of the GNU General Public License as 
published by the Free Software Foundation, either version 3 of the License, or 
(at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
details.

See <http://www.gnu.org/licenses/> for details on this license (GPLv3).

To Do:
* User interface.
	* New variant command. This will require editing.
		* Edit command, similar to the one in Fiddler.
		* Edit mode (rule or variant).
		* Changing out requires commit decision.
			* Step, parent/child, variant, new.
			* Commit/discard commands.
			* Committing requires updating the database.
				* Rule mode is easy.
				* Track changes by database table for variants. Update those tables.
		* Summary of changes:
			* New Viewer attributes: edit_mode*, current_rule*, rule_changes*.
			* New Viewer commands: commit*, discard*, edit, new, rules
			* New Variant attribute: changes*
			* New Variant methods: commit', discard (reload)
			* Changed Viewer commands: step, variant
			* foo* = foo is implemented, foo' = foo is partially implemented.
* Add new games.
	* poker.fandom.com/wiki
	* Hurricane (one down, bet, one up, bet, showdown)
	* HORSE (need tag, rule type, tag must be base tag)
		* Wikipedia calls them mixed games.
		* 3-6-9/2-4-10
		* Redo Jack the Switch
	* Kuhn Poker
* Release
	* the pagat guy
	* r/poker (or is there a variants sub? looks like not)
	* that facebook guy
* Future improvements (cool, but not necessary)
	* Export argument child-stag, which shows serial number and tags.
		* Switch children to a table. Allows easier scanning for differences.
	* Consider splitting deal into up and down, for better structure analysis.
		* Could even have no-peek rules.
		* This would change distance calculations. Perhaps have a structure code on rules table.
	* Figure out 3-5-7 and multiple set common card games.
		* I'm really leaning to a second variable.
	* Look at distance analysis again.
		* Currently I like the idea of a tree starting with Showdown Straight.
	* Random poker game? Random 1st rule, random 2nd rule based on 1st, ...

Constants:
HELP_GENERAL: General help text for the interface. (str)
HELP_SERIAL: A description of serial numbers for variants. (str)
HELP_TAGS: A list of tags and their meaning. (str)
WORDS: Poker terms for default names of libraries. (list of str)

Classes:
Variant: A poker variant from the SQL database. (object)
Viewer: A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)
"""

import cmd
import csv
import math
import os
import shutil
import sqlite3 as sql
import textwrap
import traceback

HELP_GENERAL = """
This is an interface to Ichabod's Poker Variant Database, which is a database
of different ways to play poker. The idea is that poker variants are largely a
series of actions that you take, and those actions are often common across 
several variants. So the actions are stored separately, and the variants are
stored as a list of references to those actions. Plus some bells and whistles.

Sets of variants can be loaded into libraries using the load command, or by
certain calls to the sql command. You can look through the libraries using the
page command. You can join libraries together with the intersection, minus, 
union, and xor commands. The library command allows for copying, switching, 
renaming, and sorting libraries. It also allows you to change how the variants
are displayed in the libraries.

The variant command allows for pulling out variants to view in full. You can
also use it to navigate the variant tree through a variant's parents and
children. To navigate to the next (or previous) varaint in the library, use 
the step command.

The export command allows for exporting the current library into one or more
files. You can export to HTML, markdown, or plain text, with or without child
and parent variants listed (and you can control how the children are listed).

I'm still working on other functionality, including:
   * The creation of new rules and variants.
   * The modification of current rules and variants (for data cleaning).
"""

HELP_SERIAL = """
Serial numbers are a sequence of numbers giving statistics for the variant.
The are the numbers given in the table at the variant description. The five
numbers in the serial number are:

* The number of cards in the variant (5-card draw, 7-card stud). This is meant
   to be the number of cards available to make your hand at the showdown.
* The maximum number of players in the variant.
* The number of betting rounds in the variant.
* The maximum number of cards a player could possibly see in one round of the
   variant.
* The number of wild cards in the variant.

Some of the numbers are special codes. For example, a variant with 100 for the
number of betting rounds is actually a match pot variant. See the data 
dictionary for details on the special numbers.
"""

HELP_TAGS = """
Each poker variant has one or more tags describing features of that variant.
The tags are split into primary tags and secondary tags. The primary tags are
the categories that are traditionally used to classify poker variants, such
and draw, stud, and common. However, many games have features from more than
one of these categories, so a tag system is used instead. The primary tags
include:

* common: The variant has common cards, including those usable by multiple 
   players but not all.
* discard: Variants using attrition through discarding.
* draw: Players discarding cards to get new ones. Does not count instant 
   rejection of cards.
* flip: The variant involves flipping down cards face up.
* guts: The variant involves declaring in or out, losers matching the pot, 
   until one person goes in. This includes games with legs.
* pass: The variant involves cards being passed from one player to another.
* straight: The cards in this variant are dealt face down, with no stud, draw,
   pass, guts, or common.
* stud: The variant has cards dealt face up. Does not count flipping down cards 
   up (see 'flip').

The seconary tags cover other features common to many poker varints across the
standard categories. They include:

* dead: The variant has dead cards, which do not contribute to the value of 
   hands.
* fee: The variant involves extra fees, including auctions.
* fee-fold: The variant has conditions which force players pay a fee or fold 
   their hand.
* forced-bet: There are forced bets in the variant.
* jokers: There are jokers in the deck.
* limited: The variant has limited wild cards, which have limits on what they 
   can represent.
* lowball: The low hand wins the variant.
* mod-ranks: The variant uses standard poker hands with slight changes.
* must-fold: The variant has conditions which force players to fold with no 
   recourse.
* no-peek: The variant includes cards you do not see until showdown, excluding
   those dealt just before the showdown.
* odd-deal: The variant are not deal to the players on a per player basis.
* odd-deck: The variant uses something besides a standard 52 card deck.
* odd-ranks: The variant uses non-standard hand ranks. This is not used if only 
   split hand is odd ranks.
* qualifier: There is a restriction on hands, either on which hands can bet or
   which hands can win.
* redeal: Hands can be redealt, non-guts.
* split-card: The pot is split with whoever has a specified card.
* split-pot: The pot is split in some way besides high/low or split-card
* table: The variant has table cards.
* wilds: The variant has full wild cards. See also 'limited' and 'dead'.
"""

WORDS = ['ace', 'bet', 'card', 'duece', 'edge', 'flush', 'guts', 'high-low', 'inside', 'joker', 'king',
	'lowball', 'maverick', 'nut', 'odds', 'pair', 'queen', 'royal', 'showdown', 'trips', 'up',
	'value', 'wheel']

class Variant(object):
	"""
	A poker variant from the SQL database. (object)

	Attributes:
	cards: How many cards are used to make the final hand. (int)
	changes: What parts of the variant have been changed. (list of tuple)
	children: The database rows for this variant's children. (list of tuple)
	name: The name of the variant. (str)
	parent: The database row for the parent of this variant. (tuple)
	parent_id: The variant ID of this variant's parent. (int)
	players: The maximum number of possible players. (int)
	rounds: The number of betting rounds. (int)
	rules: The rules for the game. (list of tuple)
	source: The name of this variant's source. (str)
	source_id: The numeric ID of this variant's source. (int)
	source_link: The link to this variant's source, if any. (str)
	tags: The tags for the game. (list of str)
	variant_id: A unique numeric ID. (int)
	wilds: The maximum possible wild cards. (int)

	Class Attributes:
	primary_tags: The tags usually used to categorize variants. (tuple of str)

	Methods:
	commit: Commit any modifications made to the variant. (None)
	display: Text representation for viewing in the CLI. (str)
	export_html: Export the variant to a file as HTML. (None)
	export_markdown: Export the variant to a file as markdown. (None)
	export_text: Export the variant to a file as text. (None)
	load_data: Load attributes from the database. (None)
	load_row: Load the attributes from the row on the variants table. (None)
	relative_path: Get a relative path to another variant. (str)
	reset: Reset the variant from the database. (None)
	serial_number: Give a serial number of the stats of the variant. (str)
	summary: Give a summary of the rules of the variant. (str)
	view: Give a simplified view of the variant. (str)

	Overridden Methods:
	__init__
	__repr__
	__str__
	"""

	primary_tags = ('common', 'discard', 'draw', 'flip', 'guts', 'pass', 'straight', 'stud')

	def __init__(self, row, cursor):
		"""
		Pull the other data needed to fill out the database. (None)

		Parameters:
		row: A row from the variants table of the database. (tuple)
		cursor: A cursor for executing SQL commands. (Cursor)
		"""
		# Save the base attributes
		self.load_row(row)
		# Set the edit tracking.
		self.changes = []
		# Load the attributes from the database.
		self.load_data(cursor)

	def __repr__(self):
		"""Debugging text representation. (str)"""
		return f'<Variant {self.variant_id}: {self.name}>'

	def __str__(self):
		"""Human readable representation. (str)"""
		tags = ', '.join(self.tags)
		return f'{self.name} (#{self.variant_id}): {tags}'

	def commit(self, conn, cursor):
		"""
		Commit any modifications made to the variant. (None)

		Parameters:
		conn: A database connection. (Connection)
		cursor: A cursor to execute database commands. (Cursor)
		"""
		for variable, action, value in self.changes:
			if (variable, action) == ('alias', 'add'):
				code = 'insert into aliases(variant_id, alias) values (?, ?)'
				cursor.execute(code, (self.variant_id, self.alias))
			elif (variable, action) == ('alias', 'remove'):
				code = 'delete from aliases where variant_id = ? and alias = ?'
				cursor.execute(code, (self.variant_id, self.alias))
			print(f'Change: {variable}/{action}')
		conn.commit()
		self.changes = []

	def display(self):
		"""Text representation for viewing in the CLI. (str)"""
		# Set up the title.
		lines = [f'{self.name} (#{self.variant_id})']
		lines.append('-' * len(lines[0]))
		# Set up the stats.
		lines.append(f'Cards:          {self.cards}')
		lines.append(f'Players:        {self.players}')
		lines.append(f'Betting Rounds: {self.rounds}')
		lines.append(f'Max Cards Seen: {self.max_seen}')
		lines.append(f'Wilds:          {self.wilds}')
		lines.append(f'Source:         {self.source}')
		tag_text = ', '.join(self.tags)
		lines.append(f'Tags:           {tag_text}')
		lines.append('-' * len(lines[-1]))
		# Set up the rules
		lines.append('Rules:')
		for rule_index, rule in enumerate(self.rules, start = 1):
			lines.append(f'{rule_index}: {rule[4]} (#{rule[0]})')
		# Set up the variant tree information.
		parent_text = f'Parent: {self.parent[1]} (#{self.parent[0]})'
		lines.append('-' * len(parent_text))
		lines.append(parent_text)
		if self.children:
			lines.append('Children:')
			for child in self.children[:9]:
				lines.append(f'{child[1]} (#{child[0]})')
			if len(self.children) > 9:
				lines.append('...')
		# Combine and return.
		return '\n'.join(lines)

	def export_html(self, arguments, known_variants, cursor, variant_paths):
		"""
		Export the variant to a file as HTML. (None)

		Parameters:
		arguments: The options chosen for the export. (set of str)
		known_variants: The variants pulled from the database so far. (dict)
		cursor: A connection for executing SQL code. (Cursor)
		variant_paths: The path to the HTML file for each variant. (dict of int: str)
		"""
		# Set up the title.
		lines = [f'<h2 class="name" id="variant-{self.variant_id}">']
		lines.append(f'{self.name} <span class="variant-id">(#{self.variant_id})</span>')
		lines.append(f'</h2>')
		if self.aliases:
			alias_text = ', '.join(self.aliases)
			lines.append(f'<p class="aliases">Also known as: <span class="aliases">{alias_text}</span>.</p>')
		# Set up the stats.
		lines.append('<table class="statistics">')
		lines.append(f'<tr><td class="cards">Cards</td><td>{self.cards}</td></tr>')
		lines.append(f'<tr><td class="players">Players</td><td>{self.players}</td></tr>')
		lines.append(f'<tr><td class="rounds">Betting Rounds</td><td>{self.rounds}</td></tr>')
		lines.append(f'<tr><td class="max-seen">Max Cards Seen</td><td>{self.max_seen}</td></tr>')
		lines.append(f'<tr><td class="wilds">Wilds</td><td>{self.wilds}</td></tr>')
		lines.append(f'<tr><td class="source">Source</td><td>{self.source}</td></tr>')
		lines.append('</table>')
		tag_text = ', '.join(self.tags)
		lines.append(f'<p class="tags">Tags: <span class="tags">{tag_text}</span></p>')
		# Set up the rules
		lines.append('<h3 class="rules">Rules:</h3>')
		lines.append('<ol class="rule-list">')
		for rule_index, rule in enumerate(self.rules, start = 1):
			lines.append(f'<li class="rule-line">{rule[4]}</li>')
		lines.append('</ol>')
		# Set up the variant tree information.
		# Check for a child mode.
		try:
			child_mode = [arg for arg in arguments if arg.startswith('child')][0]
		except IndexError:
			child_mode = ''
		if child_mode:
			# Find this variant.
			my_path = variant_paths[self.variant_id].split('/')
			# Set up the parent.
			try:
				parent_path = self.relative_path(my_path, variant_paths[self.parent[0]], self.parent[0])
			except KeyError:
				parent_text = '<p class="parent">Parent: {1} <span class="variant-id">(#{0})</span></p>'
				lines.append(parent_text.format(*self.parent))
			else:
				lines.append(f'<p class="parent">Parent: <a href="{parent_path}">{self.parent[1]}</a>')
				lines.append(f'<span class="variant-id">(#{self.parent[0]})</span>')
				lines.append('</p>')
			# Set up the children, if any.
			if self.children:
				lines.append('<h3 class="children">Children:</h3>')
				if child_mode in ('child-name', 'child-summary'):
					lines.append('<ul class="child-list">')
				else:
					lines.append('<table class="child-table">')
				for child in self.children:
					try:
						child_path = self.relative_path(my_path, variant_paths[child[0]], child[0])
					except KeyError:
						child_name = child[1]
					else:
						child_name = f'<a href="{child_path}">{child[1]}</a>'
					# Get the text by child mode.
					if child_mode == 'child-name':
						child_text = '<li class="child">{} <span class="variant-id">(#{})</span></li>'
						lines.append(child_text.format(child_name, child[0]))
					elif child_mode == 'child-summary':
						child = known_variants.get(child[0], Variant(child, cursor))
						lines.append(f'<li class="child">{child_name}')
						lines.append(f'<span class="variant_id">(#{child.variant_id})</span>')
						if child_mode == 'child-summary':
							summary = child.summary()
							lines.append(f'<span class="summary">{summary}</span></li>')
					else:
						child_obj = known_variants.get(child[0], Variant(child, cursor))
						lines.append('<tr>')
						child_text = '<td class="name">{} <span class="variant-id">(#{})</span></td>'
						lines.append(child_text.format(child_name, child_obj.variant_id))
						if child_mode in ('child-serial', 'child-stags'):
							serial_text = '<td><span class="serial-number">{2}-{3}-{4}-{5}-{6}</span></td>'
							lines.append(serial_text.format(*child))
						if child_mode in ('child-tags', 'child-stags'):
							tag_text = ', '.join(child_obj.tags)
							lines.append(f'<td><span class="tags">{tag_text}</span></td>')
						lines.append('</tr>')
				if child_mode in ('child-name', 'child-summary'):
					lines.append('</ul>')
				else:
					lines.append('</table>')
		# Export the variant.
		lines.extend(('', '', ''))
		return '\n'.join(lines)

	def export_markdown(self, arguments, known_variants, cursor):
		"""
		Export the variant to a file as markdown. (None)

		Parameters:
		arguments: The options chosen for the export. (set of str)
		cursor: A connection for executing SQL code. (Cursor)
		"""
		# Set up the title.
		lines = [f'## {self.name} (#{self.variant_id})']
		if self.aliases:
			lines.append('Also known as: *{}*.'.format(', '.join(self.aliases)))
		# Set up the stats.
		lines.append('')
		lines.append('|Statistic|Value|')
		lines.append('|---------|-----|')
		lines.append(f'|Cards|{self.cards}|')
		lines.append(f'|Players|{self.players}|')
		lines.append(f'|Betting Rounds|{self.rounds}|')
		lines.append(f'|Max Cards Seen|{self.max_seen}|')
		lines.append(f'|Wilds|{self.wilds}|')
		lines.append(f'|Source|{self.source}|')
		tag_text = ', '.join(self.tags)
		lines.append(f'Tags: *{tag_text}*')
		# Set up the rules
		lines.append('### Rules:')
		for rule_index, rule in enumerate(self.rules, start = 1):
			lines.append(f'{rule_index}. {rule[4]}')
		# Set up the variant tree information.
		# Check for a child mode.
		try:
			child_mode = [arg for arg in arguments if arg.startswith('child')][0]
		except IndexError:
			child_mode = ''
		if child_mode:
			# Set up the parent.
			lines.append('')
			lines.append(f'Parent: {self.parent[1]} (#{self.parent[0]})')
			# Set up the children, if any.
			if self.children:
				lines.append('### Children:')
				if child_mode == 'child-tags':
					lines.append('')
					lines.append('|Name|Tags|')
					lines.append('|----|----|')
				elif child_mode == 'child-serial':
					lines.append('')
					lines.append('|Name|Serial #|')
					lines.append('|----|--------|')
				elif child_mode == 'child-stags':
					lines.append('')
					lines.append('|Name|Serial #|Tags|')
					lines.append('|----|--------|----|')
				for child in self.children:
					# Get the text by child mode.
					if child_mode == 'child-name':
						lines.append(f'* {child[1]} (#{child[0]})')
					elif child_mode == 'child-serial':
						serial_text = '{2}-{3}-{4}-{5}-{6}'.format(*child)
						lines.append(f'|{child[1]} (#{child[0]})|*{serial_text}*|')
					else:
						child_obj = known_variants.get(child[0], Variant(child, cursor))
						child_name = f'{child_obj.name} (#{child_obj.variant_id})'
						if child_mode == 'child-stags':
							tag_text = ', '.join(child_obj.tags)
							serial_text = '{2}-{3}-{4}-{5}-{6}'.format(*child)
							lines.append(f'|{child_name}|{serial_text}|{tag_text}')
						elif child_mode == 'child-summary':
							summary = child_obj.summary()
							lines.append(f'* {child_name}: *{summary}*')
						elif child_mode == 'child-tags':
							tag_text = ', '.join(child_obj.tags)
							lines.append(f'|{child_name}|*{tag_text}*|')
		# Export the variant.
		lines.extend(('', '', ''))
		return '\n'.join(lines)

	def export_text(self, arguments, known_variants, cursor):
		"""
		Export the variant to a file as text. (None)

		Parameters:
		arguments: The options chosen for the export. (set of str)
		known_variants: The variants pulled from the database so far. (dict)
		cursor: A connection for executing SQL code. (Cursor)
		"""
		# Set up the title.
		lines = [f'{self.name} (#{self.variant_id})']
		if self.aliases:
			lines.append('Also known as: {}.'.format(', '.join(self.aliases)))
		lines.append('-' * len(lines[0]))
		# Set up the stats.
		lines.append(f'Cards:          {self.cards}')
		lines.append(f'Players:        {self.players}')
		lines.append(f'Betting Rounds: {self.rounds}')
		lines.append(f'Max Cards Seen: {self.max_seen}')
		lines.append(f'Wilds:          {self.wilds}')
		lines.append(f'Source:         {self.source}')
		tag_text = ', '.join(self.tags)
		lines.append(f'Tags:           {tag_text}')
		lines.append('-' * len(lines[-1]))
		# Set up the rules
		lines.append('Rules:')
		for rule_index, rule in enumerate(self.rules, start = 1):
			lines.append(f'{rule_index}: {rule[4]}')
		# Set up the variant tree information.
		# Check for a child mode.
		try:
			child_mode = [arg for arg in arguments if arg.startswith('child')][0]
		except IndexError:
			child_mode = ''
		if child_mode:
			# Set up the parent.
			parent_text = f'Parent: {self.parent[1]} (#{self.parent[0]})'
			lines.append('-' * len(parent_text))
			lines.append(parent_text)
			# Set up the children, if any.
			if self.children:
				lines.append('Children:')
				for child in self.children:
					# Get the text by child mode.
					if child_mode == 'child-name':
						lines.append(f'{child[1]} (#{child[0]})')
					elif child_mode == 'child-serial':
						serial_text = '{2}-{3}-{4}-{5}-{6}'.format(*child)
						lines.append(f'{child[1]} (#{child[0]}): {serial_text}')
					else:
						child_obj = known_variants.get(child[0], Variant(child, cursor))
						child_name = f'{child_obj.name} (#{child_obj.variant_id})'
						if child_mode == 'child-stags':
							tag_text = ', '.join(child_obj.tags)
							serial_text = '{2}-{3}-{4}-{5}-{6}'.format(*child)
							lines.append(f'{child_name}: {serial_text} | {tag_text}')
						elif child_mode == 'child-summary':
							summary = child_obj.summary()
							lines.append(f'   {child_name}: {summary}')
						elif child_mode == 'child-tags':
							tag_text = ', '.join(child_obj.tags)
							lines.append(f'{child_name}: {tag_text}')
		# Export the variant.
		lines.extend(('', '', ''))
		return '\n'.join(lines)

	def load_data(self, cursor):
		"""
		Load attributes from the database. (None)

		Parameters:
		cursor: A cursor to execute SQL commands. (Cursor)
		"""
		# Get the aliases of the game.
		code = 'select alias from aliases where aliases.variant_id = ? order by alias'
		cursor.execute(code, (self.variant_id,))
		self.aliases = [row[0] for row in cursor.fetchall()]
		# Get the tags for the game.
		code = 'select tag from tags, variant_tags where tags.tag_id = variant_tags.tag_id'
		code = f'{code} and variant_tags.variant_id = ?'
		cursor.execute(code, (self.variant_id,))
		tags = [row[0] for row in cursor.fetchall()]
		tags.sort()
		self.tags = [tag for tag in tags if tag in self.primary_tags]
		self.tags += [tag for tag in tags if tag not in self.primary_tags]
		# Get the rules for the game.
		code = 'select rules.* from rules, variant_rules where rules.rule_id = variant_rules.rule_id'
		code = f'{code} and variant_rules.variant_id = ? order by variant_rules.rule_order'
		cursor.execute(code, (self.variant_id,))
		self.rules = [row for row in cursor.fetchall()]
		# Get the source for the game.
		code = 'select name, link from sources where source_id = ?'
		cursor.execute(code, (self.source_id,))
		self.source, self.source_link = cursor.fetchone()
		# Get the parent of the game.
		if self.parent_id:
			code = 'select * from variants where variant_id = ?'
			cursor.execute(code, (self.parent_id,))
			self.parent = cursor.fetchone()
		else:
			self.parent = (0, 'Root Game')
		# Get the children of the game.
		code = 'select * from variants where parent_id = ? order by variant_id'
		cursor.execute(code, (self.variant_id,))
		self.children = list(cursor.fetchall())

	def load_row(self, row):
		"""
		Load the attributes from the row on the variants table. (None)

		Parameters:
		row: A row from the variants table. (tuple)
		"""
		self.variant_id = row[0]
		self.name = row[1]
		self.cards = row[2]
		self.players = row[3]
		self.rounds = row[4]
		self.max_seen = row[5]
		self.wilds = row[6]
		self.parent_id = row[7]
		self.source_id = row[8]

	def relative_path(self, my_path, target_path, target_id):
		"""
		Get a relative path to another variant. (str)

		Parameters:
		my_path: The path to the file with this variant. (list of str)
		target_path: The path to the file with the target variant. (str)
		target_id: The ID for the target variant. (int)
		"""
		target_path = target_path.split('/')
		if my_path == target_path:
			return f'#variant-{target_id}'
		elif my_path[-2] != target_path[-2]:
			return f'../{target_path[1]}/{target_path[2]}.html#variant-{target_id}'
		else:
			return f'{target_path[-1]}.html#variant-{target_id}'

	def reset(self, cursor):
		"""
		Reset the variant from the database. (None)

		Parameters:
		cursor: A cursor for executing SQL commands. (Cursor)
		"""
		# Save the base attributes
		code = 'select * from variants where variant_id = ?'
		cursor.execute(code, (self.variant_id,))
		self.load_row(cursor.fetchone())
		# Set the edit tracking.
		self.changes = []
		# Load the attributes from the database.
		self.load_data(cursor)

	def serial_number(self):
		"""Give a serial number of the stats of the variant. (str)"""
		return f'{self.cards}-{self.players}-{self.rounds}-{self.max_seen}-{self.wilds}'

	def summary(self):
		"""Give a summary of the rules of the variant. (str)"""
		return '; '.join(rule[3] for rule in self.rules)

	def view(self, mode = 'tags'):
		"""
		Give a simplified view of the variant. (str)

		Parameters:
		mode: The type of view to give. (str)
		"""
		if mode == 'stats':
			serial_num = self.serial_number()
			return f'{self.name} (#{self.variant_id}): {serial_num}'
		elif mode == 'summary':
			summary = self.summary()
			text = f'{self.name} (#{self.variant_id}): {summary}'
			lines = textwrap.wrap(text, width = 79, subsequent_indent = '   ')
			return '\n'.join(lines)
		elif mode == 'tags':
			return str(self)

class Viewer(cmd.Cmd):
	"""
	A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)

	Attributes:
	changes: A flag for there being uncommitted changes. (bool)
	conn: A connection to the poker variant database. (Connection)
	cursor: An SQL command executor. (Cursor)
	current_library: A key to the current library. (str)
	current_rule: The current rule. (tuple)
	current_variant: The current variant. (Variant)
	edit_mode: What type of object is currently being edited. (str)
	libraries: Sets of variants. (dict of str: list)
	rule_lookup: A lookup table for rules. (dict of int: str)
	rule_type_ids: A lookup table for rule type IDs. (dict of str: int)
	rule_type_lookup: A lookup table for rule types. (dict of int: str)
	source_ids: A lookup table for source IDs. (dict of str: int)
	source_lookup: A lookup table for sources. (dict of int: tuple)
	tag_ids: A lookup table for tag IDs. (dict of str: int)
	tag_lookup: A lookup table for tag. (dict of int: str)
	variants: Variants that have been loaded, keyed by ID (dict of int: Variant)

	Class Attributes:
	aliases: Command aliases. (dict of str: str)
	help_text: Help for non-command topics. (None)
	valid_export: The valid arguments to the export command. (set of str)

	Methods:
	do_commit: Commit the latest changes to the database. (None)
	do_discard: Discard any changes made to the database. (None)
	do_drop: Specify which variants to remove from the current library. (None)
	do_export: Export a library to one or more files. (None)
	do_intersection: Generate the intersection between two libraries. (None)
	do_keep: Specify which variants to keep in the current library. (None)
	do_library: Process library related commands. (None)
	do_load: Load variants into a library. (None)
	do_minus: Remove the values in the second libary from the first one. (None)
	do_page: Change the page being viewed. (None)
	do_quit: Quit the interface. (True)
	do_reset: Reset the SQL database based on the csv files. (None)
	do_sql: Handle raw SQL code. (None)
	do_union: Generate the union of two libraries. (None)
	do_xor: Generate the exclusive or of two libraries. (None)
	export_files: Export data to external files. (int)
	get_child: Get a child variant from the current variant. (None)
	get_libraries: Get libraries for binary set operations. (tuple of dict)
	library_list: Create a new library from a list of variants. (None)
	library_sql: Create a new library from the most recent query. (None)
	load_by_rules: Load variants into a library by rules. (None)
	load_by_tags: Load variants into a library by tags. (None)
	load_csv_data: Load csv data from the old database. (dict of str: tuple)
	load_lookups: Load the lookups tables that are used internally. (None)
	load_variants: Load variants from the database. (None)
	next_library: Create and auto-name a new library. (None)
	reset_rule_types: Load the old rule type data into the database. (None)
	reset_rules: Load the old rule data into the database. (None)
	reset_sources: Load the old source data into the database. (None)
	reset_tags: Load the old tag data into the database. (None)
	reset_variant_rules: Load the old variant rules data into the database. (None)
	reset_variant_tags: Load the old variant tag data into the database. (None)
	reset_variants: Load the old variant data into the database. (None)
	show_library: Print out a library. (None)
	split_libraries: Split a library based on export arguments. (list of tuple)

	Overridden Methods:
	default
	do_help
	do_shell
	onecmd
	precmd
	preloop
	postcmd
	"""

	aliases = {'&': 'intersection', '-': 'minus', '|': 'union', 'dbr': 'drop by rule', 'drs': 'drop by stats',
		'drt': 'drop by tag', 'kbr': 'keep by rule', 'kbs': 'keep by stats', 'kbt': 'keep by tag',
		'lib': 'library', 'lbr': 'load by rule', 'lbs': 'load by stats', 'lbt': 'load by tag', 'p': 'page', 
		'q': 'quit', 's': 'step', 'var': 'variant'}
	help_text = {'help': HELP_GENERAL, 'serial numbers': HELP_SERIAL, 'tags': HELP_TAGS}
	prompt = 'IPVDB >> '
	valid_export = set(('by-cards', 'by-tag', 'child-name', 'child-serial', 'child-summary', 'child-stags', 
		'child-tags', 'html', 'markdown', 'multi-all', 'multi-alpha', 'mutli-freq', 'text'))

	def default(self, line):
		"""
		Handle unrecognized input. (bool)

		Parameters:
		line: The command entered by the user. (str)
		"""
		words = line.split()
		if words[0] in self.aliases:
			words[0] = self.aliases[words[0]]
			return self.onecmd(' '.join(words))
		else:
			return super(Viewer, self).default(line)

	def do_commit(self, arguments):
		"""
		Commit the latest changes to the database.
		"""
		if self.edit_mode == 'variant':
			if self.current_variant is None or not self.current_variant.changes:
				print('There are no changes to commit.')
			else:
				self.current_variant.commit(self.conn, self.cursor)
		else:
			if self.rule_changes:
				code = 'update rules set type_id = ?, cards = ?, short = ?, full = ?'
				code = f'{code} where rule_id = ?'
				values = (self.rule_type_ids[self.current_rule[1]],)
				values += self.current_rule[2:] + self.current_rule[:1]
				self.cursor.execute(code, values)
				self.conn.commit()
				self.rule_changes = False
				print('Note that rule changes do no propogate to variants already loaded.')
				print('You must reload your libraries to change the rules loaded for them.')
			else:
				print('There are no changes to commit.')

	def do_discard(self, arguments):
		"""
		Discard any changes made to the database.
		"""
		if self.edit_mod == 'variant':
			if self.current_variant is None or not self.current_variant.changes:
				print('There are no changes to commit.')
			else:
				self.current_variant.reset(self.conn, self.cursor)
		else:
			if self.rule_changes:
				self.current_rule = None
				self.rule_changes = False
			else:
				print('There are no changes to commit.')

	def do_drop(self, arguments):
		"""
		Specify which variants to remove from the current library.

		Currently you can drop by rules, stats, or tags. The 'by' is optional, so 
		you can use 'drop by tags' or 'drop stats', followed by the search
		specification as detailed in 'help load'. The aliases for these ways to drop 
		are kbr, kbs, and kbt, respectively.
		"""
		try:
			self.load_variants(arguments)
		except ValueError:
			pass
		else:
			drop_ids = set(row[0] for row in self.cursor.fetchall())
			library = self.libraries[self.current_library]
			kept = [var for var in library if var.variant_id not in drop_ids]
			self.libraries[self.current_library] = kept
			self.show_library()

	def do_edit(self, arguments):
		"""
		Edit the current rule or variant.

		The arguments for the edit command are a sub-command and the arguments for the
		sub-command. Possible sub-commands include:
			* alias: Add the alias given as an argument, or remove it if it's already
				listed for the current variant.
			* mode: Switch what is being edited, to either variant or rule.
		"""
		# Parse the arguments.
		command, space, sub_args = arguments.partition(' ')
		command = command.lower()
		sub_args = sub_args.strip()
		# Handle adding or removing aliases.
		if command == 'alias':
			if sub_args in self.current_variant.aliases:
				self.current_variant.aliases.remove(sub_args)
				self.current_variant.changes.append(('alias', 'remove', sub_args))
			else:
				self.current_variant.aliases.append(sub_args)
				self.current_variant.changes.append(('alias', 'add', sub_args))
		# Handle changing the edit mode.
		elif command == 'mode':
			new_mode = sub_args.lower()
			if new_mode in ('variant', 'rule'):
				if new_mode != self.edit_mode and self.changes:
					print('There are uncommitted changes. Please commit or discard.')
				else:
					self.edit_mode = new_mode
					# !! need way to get a rule if there isn't one selected.
			else:
				print("Invalid edit mode. Please use 'variant' or 'rule'.")

	def do_export(self, arguments):
		"""
		Export a library to one or more files.

		Variants will be exported in the order they are in the library, so sort the
		library as desired with the library command before exporting.

		Arguments for the export command include:
		   * by-cards: Break into files by number of cards in the game.
		   * by-tag: Break into files by primary tags.
		      * mutli-all: Put variants with mutliple primary tags with all of
		        the tags they have.
		      * multi-alpha: Put variants with multiple primary tags with the 
		        first tag alpahbetically.
		      * multi-freq: Put variants with multiple primary tags with the most 
		        common tag.
	       * child-name: Children are listed by name and ID only.
	       * child-serial: Children are listed with serial numbers.
	       * child-stags: Children are listed with serial numbers and tags.
	       * child-summary: Children are listed with summaries.
	       * child-tags: Children are listed with tags.
		   * html: Export as HTML.
		   * markdown: Export as a Markdown file.
		   * text: Export as a text file (this is the default).

		If the by-cards and by-tag arguments are both given, the files will be split
		into folders by primary tag, and then into files by cards within those those
		folders. If none of the child-foo arguments are given, neither children nor
		parents are listed.
		"""
		# Validate exporting.
		if not self.libraries or not self.libraries[self.current_library]:
			print('There is no data loaded to export.')
			return
		# Validate the export arguments.
		args = set(arguments.lower().split())
		invalid_args = args - self.valid_export
		if invalid_args:
			invalid_text = ', '.join(invalid_args)
			print(f'Invalid arguments detected: {invalid_text}.')
			print('Export aborted.')
			return
		# Set the defaults
		if 'multi-all' not in args and 'multi-alpha' not in args:
			args.add('multi-freq')
		if 'html' not in args and 'markdown' not in args:
			args.add('text')
		# Get the overall name.
		name = input('Enter the name for the file or folder: ')
		# Split the library based on by-foo commands.
		files = self.split_libraries([(name, self.libraries[self.current_library][:])], args)
		# Export the files.
		file_count = self.export_files(files, args)
		# Update the user.
		print('\n{} file(s) exported.'.format(file_count))

	def do_help(self, arguments):
		"""
		Handle help requests. (bool)

		Parameters:
		arguments: What to provide help for. (str)
		"""
		topic = arguments.lower()
		# check for aliases
		topic = self.aliases.get(topic, topic)
		# The help_text dictionary takes priority.
		if topic in self.help_text:
			print(self.help_text[topic].strip())
		# General help is given with no arguments.
		elif not topic:
			# Show the base help text.
			print(self.help_text['help'].strip())
			# Get the names of other help topics.
			names = [name[3:] for name in dir(self.__class__) if name.startswith('do_')]
			names.extend([name[5:] for name in dir(self.__class__) if name.startswith('help_')])
			names.extend(self.help_text.keys())
			# Clean up the names.
			names = list(set(names) - set(('debug', 'help', 'text')))
			names.sort()
			# Convert the names to cleanly wrapped text and output.
			name_lines = textwrap.wrap(', '.join(names), width = 79)
			if name_lines:
				print()
				print("Additional help topics available with 'help <topic>':")
				print('\n'.join(name_lines))
		# help_foo methods take priority over do_foo docstrings.
		elif hasattr(self, 'help_' + topic):
			help_method = getattr(self, 'help_' + topic)
			# Exit without pausing if requested by the help_foo method.
			if help_method():
				return True
		# Method docstrings are given for recognized commands.
		elif hasattr(self, 'do_' + topic):
			help_text = getattr(self, 'do_' + topic).__doc__
			help_text = textwrap.dedent(help_text).strip()
			print(help_text)
		# Display default text for unknown arguments.
		else:
			print("I can't help you with that.")

	def do_intersection(self, arguments):
		"""
		Generate the intersection between two libraries. (&)
		"""
		left, right = self.get_libraries(*arguments.split())
		if left is not None:
			self.library_list([variant for variant in left if variant in right])

	def do_keep(self, arguments):
		"""
		Specify which variants to keep in the current library.

		Currently you can keep by rules, stats, or tags. The 'by' is optional, so 
		you can use 'keep by tags' or 'keep stats', followed by the search
		specification as detailed in 'help load'. The aliases for these ways to keep 
		are kbr, kbs, and kbt, respectively.
		"""
		try:
			self.load_variants(arguments)
		except ValueError:
			pass
		else:
			keep_ids = set(row[0] for row in self.cursor.fetchall())
			library = self.libraries[self.current_library]
			kept = [var for var in library if var.variant_id in keep_ids]
			self.libraries[self.current_library] = kept
			self.show_library()

	def do_library(self, arguments):
		"""
		Process library commands. (lib)

		Possible arguments include:
			* Nothing, to redisplay the current library.
			* The name of a library, to switch to that library.
			* 'copy' to make a copy of the library.
			* 'rename' or 'rn' and a new name, to change the name of the current
				library.
			* 'sort' and a sort type to sort the current library. Valid sort types
				include: variant_id, name, cards, players, rounds, max_seen, wilds, 
				and tags. You can give a third argument of 'reverse' to reverse the
				sort order.
			* 'view' and a view mode (stats, summary, or tags) to use to display the
				variants.
		"""
		# Parse arguments.
		words = arguments.split()
		command = words[0] if words else ''
		# Change libraries.
		if arguments in self.libraries:
			self.current_library = words[0]
		# Show the current library.
		elif not arguments:
			pass  # it will be shown at the end of the method.
		# Copy the current library.
		elif command == 'copy':
			self.library_list(self.libraries[self.current_library][:])
			return # library list will show the library.
		# Rename the current libraries.
		elif command in ('rename', 'rn'):
			new_name = ' '.join(words[1:])
			self.libraries[new_name] = self.libraries[self.current_library]
			del self.libraries[self.current_library]
			self.current_library = new_name
		# Sort the current library.
		elif command == 'sort':
			sorter = lambda variant: getattr(variant, words[1].lower())
			self.libraries[self.current_library].sort(key = sorter)
			if len(words) > 2 and words[3].lower() == 'reverse':
				self.libraries[self.current_library].reverse()
		# Set the view mode.
		elif command == 'view':
			view_mode = words[1].lower()
			if view_mode in ('stats', 'summary', 'tags'):
				self.view_mode = view_mode
			else:
				print('Invalid view mode.')
				return
		# Error for invalid input.
		else:
			print('I do not understand.')
			return
		self.show_library()

	def do_load(self, arguments):
		"""
		Load variants into a library.

		Currently you can load by rules, stats, or tags. The 'by' is optional, so 
		you can use 'load by tags' or 'load stats', followed by the search
		specification as detailed below. The aliases for these ways to load are 
		lbr, lbs, and lbt, respectively. You can also use 'load all' to load the
		entire database into one library.

		Loading by rules can be done three ways. If you just pass a number, it will
		search for games with that rule ID. If you pass the word 'type' and a rule 
		type it will search for games with that rule type. When you search by type,
		you can also pass a card number to search by rule type and card number. 
		Anything else will be interpretted as a search of the rule's full text. Use
		SQL wildcards when doing this search: % for any sequence of zero or more
		characters and _ for any single character.

		Loading by stats can be done using three part search terms. The first part 
		of a search term can be any variable on the variants table: variant_id, name, 
		cards, players, rounds, max_seen, wilds, parent_id, or source_id. The second
		part is an operator, one of '=', '>', '<', or '~' (like). The third part is
		the value to search for. Multiple search terms can be used, but resulting
		variants must match all search terms.

		Loading by tags takes a list of tags as an argument. Tags can be listed plain
		or with a preceding -. Matching variants will have one of the plain tags, and 
		none of the -tags.
		"""
		try:
			self.load_variants(arguments)
		except ValueError:
			pass
		else:
			self.library_sql()

	def do_minus(self, arguments):
		"""
		Remove the values in the second libary from the first library. (-)
		"""
		left, right = self.get_libraries(*arguments.split())
		if left is not None:
			self.library_list([variant for variant in left if variant not in right])

	def do_page(self, arguments):
		"""
		Switch pages in the library view. (p)

		Without arguments, this command will move one page forward. You can give b or
		back as an argument to move one page back. You can also give an integer
		argument to move to a specific page. Finally, you can use 'size N' as an
		argument to change the number of variants showed at a time to N.
		"""
		# Pre-processing.
		arguments = arguments.lower()
		library = self.libraries[self.current_library]
		# Go back.
		if arguments in ('b', 'back'):
			self.page = max(1, self.page - 1)
		# Go to a specific page.
		elif arguments.isdigit():
			self.page = min(math.ceil(len(library) / self.page_size), int(arguments))
		# Go forward.
		elif not arguments:
			self.page = min(math.ceil(len(library) / self.page_size), self.page + 1)
		# Change the page size.
		elif arguments.startswith('size'):
			words = arguments.split()
			if words[1].isdigit():
				self.page_size = int(words[1])
			else:
				print(f'Invalid page size: {words[1]!r}.')
		# Say what?
		else:
			print(f'Invalid arguments: {arguments!r}')
		self.show_library()

	def do_quit(self, arguments):
		"""Quit the IPVDB interface. (q)"""
		self.cursor.close()
		self.conn.close()
		return True

	def do_reset(self, arguments):
		"""Reset the SQL database based on the csv files."""
		# Confirm resetting the database.
		print('+--------------------------------------------------------------+')
		print('| WARNING: This will DESTROY any changes made to the database! |')
		print('+--------------------------------------------------------------+')
		print()
		confirm = input('Are you sure you want to do this? ')
		if confirm.lower() in ('y', 'yes'):
			# Delete the database.
			self.cursor.close()
			self.conn.close()
			try:
				os.remove('poker_db.db')
			except IOError:
				pass
			# Restart the database.
			self.conn = sql.connect('poker_db.db')
			self.cursor = self.conn.cursor()
			# Reset the table definitions.
			with open('poker_var.sql') as code_file:
				db_code = code_file.read()
				self.cursor.executescript(db_code)
				self.conn.commit()
			# Load the old data.
			data = self.load_csv_data()
			self.reset_rule_types(data)
			self.reset_sources(data)
			self.reset_tags(data)
			self.reset_rules(data)
			self.reset_variants(data)
			self.reset_aliases(data)
			self.reset_variant_rules(data)
			self.reset_variant_tags(data)
		else:
			# Note that the reset was aborted.
			print('Reset aborted.')

	def do_shell(self, arguments):
		"""Handle raw Python code. (!)"""
		print(eval(arguments))

	def do_sql(self, arguments):
		"""
		Handle raw SQL code.

		If the SQL code starrts with 'select variants.*' or 'select distinct 
		variants.*', the code will try to convert the returned rows into a 
		library. Otherwise, it will just display the row tuples.
		"""
		self.cursor.execute(arguments)
		# Check for library vs. displaying raw rows.
		args = arguments[:26].lower()
		if args.startswith('select variants.*') or args.startswith('select distinct variants.*'):
			self.library_sql()
		else:
			for row in self.cursor:
				print(row)
		self.conn.commit()

	def do_step(self, arguments):
		"""
		Step to the next variant in the library. (s)

		You can use 'b' or 'back' as an argument to see the previous variant in the
		library.
		"""
		try:
			variant_index = self.libraries[self.current_library].index(self.current_variant)
		except IndexError:
			print('The current variant is not in the current library, so step cannot be used.')
			return
		if arguments.lower() in ('b', 'back'):
			variant_index = max(0, variant_index - 1)
		else:
			variant_index = min(len(self.libraries[self.current_library]) - 1, variant_index + 1)
		self.current_variant = self.libraries[self.current_library][variant_index]
		print(self.current_variant.display())

	def do_union(self, arguments):
		"""
		Generate the union of two libraries. (|)
		"""
		left, right = self.get_libraries(*arguments.split())
		if left is not None:
			union = list(set(left + right))
			union.sort(key = lambda variant: variant.variant_id)
			self.library_list(union)

	def do_variant(self, arguments):
		"""
		Process variant commands. (var)

		You can pass a variant ID or name (case sensitive) as an argument to show 
		that variant, but only if it has been loaded fromm the database. You may give
		no arguments to view the current variant.
		"""
		# Parse the arguments.
		words = arguments.split()
		command = words[0] if words else ''
		# Get a variant's child
		if command == 'child':
			if not self.get_child():
				return
		# Get a variant by ID.
		elif command.isdigit():
			variant_id = int(command)
			if variant_id in self.variants:
				self.current_variant = self.variants[variant_id]
			else:
				print('That variant has not been loaded from the database.')
				return
		# Get a variant by name.
		elif arguments in self.variants:
			self.current_variant = self.variants[arguments]
		# Get a variant's parent.
		elif command in ('parent', 'rent'):
			if self.current_variant.parent_id:
				try:
					self.current_variant = self.variants[self.current_variant.parent_id]
				except KeyError:
					parent = Variant(self.current_variant.parent, self.cursor)
					self.variants[parent.variant_id] = parent
					self.variants[parent.name] = parent
					self.current_variant = parent
			else:
				print('The current variant is a root game, it has no parent.')
				return
		# Show the current variant
		elif not arguments:
			pass
		# Warn user of invalid input.
		else:
			print('That is an invalid command or a variant that has not been loaded from the database.')
		# Show the current variant.
		print(self.current_variant.display())

	def do_xor(self, arguments):
		"""
		Generate the exclusive or of two libraries.

		That is, generate a new library with variants that are in one of the two 
		libraries, but not both of the libraries.
		"""
		left, right = self.get_libraries(*arguments.split())
		if left is not None:
			xor = [variant for variant in left if variant not in right]
			xor += [variant for variant in right if variant not in left]
			xor.sort(key = lambda variant: variant.variant_id)
			self.library_list(xor)

	def export_files(self, files, args):
		"""
		Export data to external files. (int)

		The return value is the number of files exported.

		Parameters:
		files: The path and variants for each file. (list of tuple)
		args: The arguments to the export command. (set of str)
		"""
		# Get the proper extension.
		if 'text' in args:
			ext = 'txt'
		elif 'html' in args:
			ext = 'html'
		elif 'markdown' in args:
			ext = 'md'
		# Export to the files.
		if 'html' in args:
			variant_paths = {}
			for path, variants in files:
				for variant in variants:
					variant_paths[variant.variant_id] = path
			parts = path.split('/')
			if len(parts) > 1:
				os.mkdir(parts[0])
				shutil.copyfile('poker_style.css', f'{parts[0]}/poker_style.css')
				self.html_contents(files)
		file_count = 0
		for path, variants in files:
			if variants:
				# Open the file, creating new directories as needed.
				try:
					variant_file = open(f'{path}.{ext}', 'w')
				except FileNotFoundError:
					folder = path[:path.rindex('/')]
					os.makedirs(folder)
					variant_file = open(f'{path}.{ext}', 'w')
				# Generate a header for HTML files.
				if 'html' in args:
					file_words = [word.strip('0').title() for word in path.split('/')]
					file_words.reverse()
					title = '{} Poker Variants'.format(' '.join(file_words))
					variant_file.write('<html>\n')
					variant_file.write('<head>\n')
					variant_file.write(f'<title>{title}</title>\n')
					if len(file_words) == 3:
						variant_file.write(f'<link rel="stylesheet" href="../poker_style.css">')
					else:
						variant_file.write(f'<link rel="stylesheet" href="poker_style.css">')
					variant_file.write('</head>\n')
					variant_file.write('<body>\n')
				# Export the text for the individual variants.
				for variant in variants:
					if 'html' in args:
						variant_text = variant.export_html(args, self.variants, self.cursor, variant_paths)
						variant_file.write(variant_text)
					elif 'markdown' in args:
						variant_text = variant.export_markdown(args, self.variants, self.cursor)
						variant_file.write(variant_text)
					elif 'text' in args:
						variant_text = variant.export_text(args, self.variants, self.cursor)
						variant_file.write(variant_text)
				# Generate a footer for HTML files.
				if 'html' in args:
					variant_file.write('</body>\n')
					variant_file.write('</html>\n')
				file_count += 1
		return file_count

	def get_child(self):
		"""
		Get a child variant from the current variant. (None or Variant)

		The return value can be used as a condition to check if a child was 
		successfully chosen.
		"""
		# Determine which child to change to.
		children = self.current_variant.children
		if not children:
			print('There are no children of the current variant.')
			return
		elif len(children) == 1:
			child = children[0]
		else:
			for child_index, child in enumerate(children):
				print(f'{child_index}: {child[1]}')
			choice = input('\nWhich child (by number) would you like to view? ')
			print()
			try:
				child = children[int(choice)]
			except (IndexError, ValueError):
				print('That is not a valid choice.')
				return
		# Set the child from a data row.
		if child[0] in self.variants:
			self.current_variant = self.variants[child[0]]
		else:
			child = Variant(child, self.cursor)
			self.variants[child.variant_id] = child
			self.variants[child.name] = child
			self.current_variant = child
		return child

	def get_libraries(self, left, right):
		"""
		Get libraries for binary set operations. (tuple of dict)

		Returns None, None if either library key is invalid.

		Parameters:
		left: The key for the left hand library. (str)
		right: The key for the right hand library. (str)
		"""
		if left not in self.libraries:
			print(f'Invalid library name: {left!r}. Library names are case sensitive.')
		elif right not in self.libraries:
			print(f'Invalid library name: {right!r}. Library names are case sensitive.')
		else:
			return self.libraries[left], self.libraries[right]
		return None, None

	def html_contents(self, files):
		"""
		Create a table of contents for HTML exports. (None)

		Parameters:
		files: The path and variants for the exported files. (list of tuple)
		"""
		# Calculate basic info.
		depth = len(files[0][0].split('/')) - 1
		base = files[0][0].split('/')[0]
		# Set up the header.
		lines = ['<html>', '<head>']
		lines.append(f'<title>{base.title()} Table of Contents</title>')
		lines.append('<link rel="stylesheet" href="poker_style.css">')
		lines.append('</head>')
		# Set up the body
		lines.append('<body>')
		lines.append(f'<h2>{base.title()} Table of Contents</h2>')
		lines.append('<ul>')
		# Loop through the files to be created.
		last_tag = ''
		for path, variants in files:
			# Parse out the path.
			file_words = path.split('/')
			relative_path = '/'.join(file_words[1:])
			word = file_words[1].strip('0').title()
			if depth == 1:
				# Handle single by-foo break down.
				lines.append(f'<li><a href="{relative_path}.html">{word} Games</a></li>')
			elif depth == 2:
				# Handle by-cards and by-tag break down.
				if file_words[1] != last_tag:
					# Check for ending last sub-list.
					if last_tag:
						lines.append('</ul>')
					# Create a new sub-list as needed.
					lines.append(f'<li>{word} Games</li>')
					lines.append('<ul>')
					last_tag = file_words[1]
				# Output the file link.
				sub_word = file_words[2].strip('0').title()
				lines.append(f'<li><a href="{relative_path}.html">{sub_word} {word} Games</a></li>')
		# Close off the last sub-list as needed.
		if depth == 2:
			lines.append('</ul>')
		# Close of and export the HTML.
		lines.extend(('</ul>', '</body>', '</html>'))
		with open(f'{base}/{base}_toc.html', 'w') as toc_file:
			toc_file.write('\n'.join(lines))

	def library_list(self, variants):
		"""
		Create a new library from a list of variants. (None)

		Parameters:
		variants: The variants to put in the library. (list of Variant)
		"""
		key = self.next_library()
		self.libraries[key] = variants
		self.show_library()

	def library_sql(self):
		"""Create a new library from the most recent query. (None)"""
		key = self.next_library()
		for row in self.cursor.fetchall():
			if row[0] not in self.variants:
				self.variants[row[0]] = Variant(row, self.cursor)
				self.variants[row[1]] = self.variants[row[0]]
			self.libraries[key].append(self.variants[row[0]])
		self.show_library()

	def load_by_rules(self, words):
		"""
		Load variants into a library by rules. (None)

		See the documentation for do_load for details on the words parameter.

		Parameters:
		words: The words specifying what rules to search for. (list of str)
		"""
		# Set up the base code.
		code = 'select distinct variants.* from variants'
		code = f'{code} inner join variant_rules on variants.variant_id = variant_rules.variant_id'
		code = f'{code} inner join rules on variant_rules.rule_id = rules.rule_id'
		# Finish the code based on search type.
		if words[0].isdigit():
			# Rule ID searches.
			code = f'{code} and variant_rules.rule_id = ?'
			params = (int(words[0]),)
		elif words[0].lower() == 'type':
			# Rule type searches.
			type_id = self.rule_type_ids[words[1].lower()]
			if len(words) > 2:
				code = f'{code} and rules.type_id = ? and rules.cards = ?'
				params = (type_id, int(words[2]))
			else:
				code = f'{code} and rules.type_id = ?'
				params = (type_id,)
		else:
			# Rule text searches.
			code = f'{code} and rules.full like ?'
			params = (' '.join(words),)
		# Pull the values.
		self.cursor.execute(code, params)

	def load_by_stats(self, words):
		"""
		Load variants into a library by statistics. (None)

		Parameters:
		words: The words specifying what variants to load. (list of str)
		"""
		# Parse out the individual search terms.
		operators = tuple('=><~')
		chunks = []
		this_chunk = []
		for word in words:
			if not this_chunk:
				# Handle the first word.
				if word[-1] in operators:
					# With a terminal operator.
					this_chunk = [word[:-1], word[-1]]
				else:
					for operator in operators:
						if operator in word:
							# With an internal operator.
							this_chunk = word.partition(operator)
							break
					else:
						# With no operator
						this_chunk = [word]
			elif len(this_chunk) == 1:
				# Handle the second word.
				if word in operators:
					# As a lone operator.
					this_chunk.append(word)
				elif word[0] in operators:
					# With an initial operator.
					this_chunk.extend([word[0], word[1:]])
				else:
					# With no operator.
					print(f'Invalid second word in stat specs: {word!r}.')
					return
			elif len(this_chunk) == 2:
				# Handle the third word.
				this_chunk.append(word)
			# Check for completed search term.
			if len(this_chunk) == 3:
				chunks.append(this_chunk)
				this_chunk = []
		# Create the code.
		clauses, params = [], []
		for variable, operator, parameter in chunks:
			if operator == '~':
				operator = 'like'
			clauses.append(f'{variable} {operator} ?')
			if variable != 'name':
				parameter = int(parameter)
			params.append(parameter)
		clause_text = ' and '.join(clauses)
		code = f'select * from variants where {clause_text}'
		# Pull the values.
		self.cursor.execute(code, params)

	def load_by_tags(self, tags):
		"""
		Load variants into a library by tags. (None)

		Parameters:
		tags: A list of tags to load by. (list of str)
		"""
		# Parse out the tags.
		negative, neutral = [], []
		for tag in tags:
			if tag.startswith('-'):
				negative.append(self.tag_ids[tag[1:].lower()])
			else:
				neutral.append(self.tag_ids[tag.lower()])
		# Build the SQL code.
		code = 'select distinct variants.* from variants'
		code = f'{code} inner join variant_tags on variants.variant_id = variant_tags.variant_id'
		if neutral:
			qmarks = ', '.join(['?'] * len(neutral))
			code = f'{code} and variant_tags.tag_id in ({qmarks})'
		if negative:
			qmarks = ', '.join(['?'] * len(negative))
			code = f'{code} except select var2.* from variants var2'
			code = f'{code} inner join variant_tags var_tag2 on var2.variant_id = var_tag2.variant_id'
			code = f'{code} and var_tag2.tag_id in ({qmarks})'
		# Pull the values.
		self.cursor.execute(code, neutral + negative)

	def load_csv_data(self):
		"""
		Load the csv data from the old database. (dict of str: tuple)

		Each table in the old data is given a key in the returned dictionary. Note
		that the tables in the old database do not correspond exactly to the tables in
		the new database. Some things that should have been lookup tables weren't.
		"""
		data = {}
		with open('alias_data.csv') as alias_file:
			alias_reader = csv.reader(alias_file)
			data['aliases'] = tuple(alias_reader)
		with open('game_data.csv') as game_file:
			game_reader = csv.reader(game_file)
			data['variants'] = tuple(game_reader)
		with open('game_rules.csv') as game_rules_file:
			game_rules_reader = csv.reader(game_rules_file)
			data['variant-rules'] = tuple(game_rules_reader)
		with open('game_tags.csv') as game_tags_file:
			game_tags_reader = csv.reader(game_tags_file)
			data['variant-tags'] = tuple(game_tags_reader)
		with open('rule_data.csv') as rule_file:
			rule_reader = csv.reader(rule_file)
			data['rules'] = tuple(rule_reader)
		with open('tag_data.csv') as tag_file:
			tags_reader = csv.reader(tag_file)
			data['tags'] = tuple(tags_reader)
		return data

	def load_lookups(self):
		"""Load the lookups tables that are used internally. (None)"""
		# Load rule type lookups.
		self.rule_type_ids, self.rule_type_lookup = {}, {}
		code = 'select * from rule_types'
		self.cursor.execute(code)
		for type_id, rule_type in self.cursor.fetchall():
			self.rule_type_ids[rule_type] = type_id
			self.rule_type_lookup[type_id] = rule_type
		# Load the source lookups.
		self.source_ids, self.source_lookup = {}, {}
		code = 'select * from sources'
		self.cursor.execute(code)
		for source_id, name, link in self.cursor.fetchall():
			self.source_ids[name] = source_id
			self.source_lookup[source_id] = (name, link)
		# Load the tag lookups.
		self.tag_ids, self.tag_lookup = {}, {}
		code = 'select * from tags'
		self.cursor.execute(code)
		for tag_id, tag in self.cursor.fetchall():
			self.tag_ids[tag] = tag_id
			self.tag_lookup[tag_id] = tag

	def load_variants(self, arguments):
		"""
		Load variants from the database. (None)

		Parameters:
		arguments: The user's specification of what variants to load. (str)
		"""
		# Get the search type.
		words = arguments.split()
		if words[0].lower() == 'by':
			words.pop(0)
		search_type = words[0].lower()
		# Process the search.
		if search_type == 'all':
			self.cursor.execute('select * from variants')
		elif search_type in ('rule', 'rules'):
			self.load_by_rules(words[1:])
		elif search_type == 'stats':
			self.load_by_stats(words[1:])
		elif search_type in ('tag', 'tags'):
			self.load_by_tags(words[1:])
		else:
			raise ValueError('Invalid search type.')

	def next_library(self):
		"""Create and auto-name a new library. (None)"""
		# Get the new library name.
		self.library_count += 1
		library_number = self.library_count - 1
		words = []
		if library_number == 0:
			words = [WORDS[0]]
		while library_number:
			words.append(WORDS[library_number % len(WORDS)])
			library_number //= len(WORDS)
		key = ' '.join(reversed(words))
		# Add the library.
		self.libraries[key] = []
		self.current_library = key
		return key

	def onecmd(self, line):
		"""
		Interpret the argument. (str)

		Parameters:
		line: The line with the user's command. (str)
		"""
		# Catch errors and print the traceback.
		try:
			return super(Viewer, self).onecmd(line)
		except:
			traceback.print_exc()

	def precmd(self, line):
		"""
		Pre-command processing. (str)

		Parameters:
		line: The line with the user's command. (str)
		"""
		print()
		return line

	def preloop(self):
		"""Set up the interface. (None)"""
		# Set the database connection.
		self.conn = sql.connect('poker_db.db')
		self.cursor = self.conn.cursor()
		# Set the lookup tables.
		self.load_lookups()
		self.variants = {}
		# Set the library tracking.
		self.libraries = {}
		self.current_library = ''
		self.library_count = 0
		self.page_size = 23
		self.page = 1
		self.view_mode = 'tags'
		# Set the variant tracking.
		self.current_variant = None
		# Set up the edit tracking.
		self.edit_mode = 'variant'
		self.current_rule = None
		self.rule_changes = False
		# Formatting.
		print()

	def postcmd(self, stop, line):
		"""
		Post-command processing. (str)

		Parameters:
		stop: A flag for quitting the interface. (bool)
		line: The line with the user's command. (str)
		"""
		if not stop:
			print()
		return stop

	def reset_aliases(self, data):
		"""
		Load the old alias data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		code = 'insert into aliases(variant_id, alias) values (?, ?)'
		for variant_id, alias in data['aliases']:
			self.cursor.execute(code, (variant_id, alias))
		self.conn.commit()

	def reset_rule_types(self, data):
		"""
		Load the old rule type data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		rule_types = list(set(row[1] for row in data['rules']))
		rule_types.extend(['deprecated', 'variant'])
		rule_types.sort()
		self.rule_type_lookup = {}
		self.rule_type_ids = {}
		code = 'insert into rule_types(type) values(?)'
		for rule_type in rule_types:
			self.cursor.execute(code, (rule_type,))
			type_id = self.cursor.lastrowid
			self.rule_type_ids[rule_type] = type_id
			self.rule_type_lookup[type_id] = rule_type
		self.conn.commit()

	def reset_rules(self, data):
		"""
		Load the old rule data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		code = 'insert into rules(type_id, cards, short, full) values(?, ?, ?, ?)'
		for rule in data['rules']:
			row = (self.rule_type_ids[rule[1]], int(rule[2]), rule[3], rule[4])
			self.cursor.execute(code, row)
			rule_id = self.cursor.lastrowid
			if rule_id != int(rule[0]):
				raise ValueError(f'Rule ID mismatch for old rule #{rule[0]}, new rule #{rule_id}.')
		self.conn.commit()

	def reset_sources(self, data):
		"""
		Load the old source data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		sources = list(set(tuple(row[-2:]) for row in data['variants']))
		sources.sort()
		self.source_lookup = {}
		self.source_ids = {}
		code = 'insert into sources(name, link) values(?, ?)'
		for name, link in sources:
			if link == 'N/A' or 'amazon' in link:
				link = None
			self.cursor.execute(code, (name, link))
			source_id = self.cursor.lastrowid
			self.source_ids[name] = source_id
			self.source_lookup[source_id] = (name, link)
		self.conn.commit()

	def reset_tags(self, data):
		"""
		Load the old tag data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		self.tag_lookup = {}
		self.tag_ids = {}
		code = 'insert into tags(tag) values(?)'
		for old_id, tag in data['tags']:
			self.cursor.execute(code, (tag,))
			tag_id = self.cursor.lastrowid
			if tag_id != int(old_id):
				raise ValueError(f'Tag ID mismatch for old tag #{old_id}, new tag #{tag_id}.')
			self.tag_ids[tag] = tag_id
			self.tag_lookup[tag_id] = tag
		self.conn.commit()

	def reset_variant_rules(self, data):
		"""
		Load the old variant rules data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		code = 'insert into variant_rules(variant_id, rule_id, rule_order) values(?, ?, ?)'
		for old_row in data['variant-rules']:
			row = tuple(int(x) for x in old_row)
			self.cursor.execute(code, row)
		self.conn.commit()

	def reset_variant_tags(self, data):
		"""
		Load the old variant tag data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		code = 'insert into variant_tags(variant_id, tag_id) values(?, ?)'
		for variant_id, tag_id in data['variant-tags']:
			row = (int(variant_id), int(tag_id))
			self.cursor.execute(code, row)
		self.conn.commit()

	def reset_variants(self, data):
		"""
		Load the old variant data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		code = 'insert into variants(name, cards, players, rounds, max_seen, wilds, parent_id, source_id)'
		code = f'{code} values(?, ?, ?, ?, ?, ?, ?, ?)'
		for variant in data['variants']:
			row = (variant[1], int(variant[3]), int(variant[6]), int(variant[4]), int(variant[7]))
			row += (int(variant[5]), int(variant[8]), self.source_ids[variant[9]])
			self.cursor.execute(code, row)
			variant_id = self.cursor.lastrowid
			if variant_id != int(variant[0]):
				text = f'Variant ID mismatch for old variant #{variant[0]}, new variant #{variant_id}'
				raise ValueError(text)
		self.conn.commit()

	def show_library(self, key = None):
		"""
		Print out a library. (None)

		Parameters:
		key: The name of the library. (str)
		"""
		if key is None:
			key = self.current_library
			if key == '':
				print('There are no libraries at the moment. Use the load command to create one.')
				return
		if key not in self.libraries:
			print('I do not know that library. Library names are case sensitive.')
			return
		library = self.libraries[key]
		max_pages = math.ceil(len(library) / self.page_size)
		header = f'The {key} library has {len(library)} variants in it. Page {self.page}/{max_pages}'
		print(header)
		print('-' * len(header))
		for variant in library[((self.page - 1) * self.page_size):(self.page * self.page_size)]:
			print(variant.view(self.view_mode))

	def split_libraries(self, files, args):
		"""
		Split the current library based on the export arguments. (list of tuple)

		There are two possible splits: by cards, and by tag. Each is done by creating
		a list of tuples, the tuples being a file name and a list of variants in that
		file. The second split (by cards) is done on a list of such tuples, so it can
		create a two-level split if both split methods are in the arguments.

		Parameters:
		files: The initial file name and variant list. (tuple of str, list)
		args: The user provided arguments to the export command. (str)
		"""
		# Split by tag
		if 'by-tag' in args:
			name, variants = files[0]
			# Set the tag list
			if 'multi-freq' in args:
				# Calculate the tag frequencies if necessary.
				counts = {tag: 0 for tag in Variant.primary_tags}
				for variant in variants:
					for tag in variant.tags:
						if tag in counts:
							counts[tag] += 1
						else:
							break
				counts = [(count, tag) for tag, count in counts.items()]
				counts.sort(reverse = True)
				tags = tuple(tag for count, tag in counts)
			else:
				tags = Variant.primary_tags
			# Set the dupe handling.
			drop_dupes = 'multi-all' not in args
			# Split the file data.
			files = []
			for tag in tags:
				files.append((f'{name}/{tag}', [var for var in variants if tag in var.tags]))
				if drop_dupes:
					variants = [var for var in variants if var not in files[-1][1]]
		# Split by cards
		if 'by-cards' in args:
			split_files = []
			for name, variants in files:
				# Split out the low end.
				split_variants = [var for var in variants if var.cards < 3]
				if split_variants:
					split_files.append((f'{name}/02-card-', split_variants))
				# Split the middle range by individual card number.
				for cards in range(3, 10):
					split_variants = [var for var in variants if var.cards == cards]
					if split_variants:
						split_files.append((f'{name}/0{cards}-card', split_variants))
				# Split out the high end.
				split_variants = [var for var in variants if var.cards > 9]
				if split_variants:
					split_files.append((f'{name}/10-card+', split_variants))
			files = split_files
		return files

if __name__ == '__main__':
	viewer = Viewer()
	viewer.cmdloop()
