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
* Create the user interface.
	* Filters
	* SQL searches
	* Output formats (markdown, html, json?)
	* New variant command.
	* Random poker game? Random 1st rule, random 2nd rule based on 1st, ...
* Add new games.
	* Dealer's Choice, book by James Ernest, Phil Foglio, & Mike Selinker. (fair use?)
	* poker.fandom.com/wiki
	* Hurricane (one down, bet, one up, bet, showdown)
	* HORSE (need tag, rule type)
		* Wikipedia calls them mixed games.
		* 3-6-9/2-4-10
		* Redo Jack the Switch
	* Kuhn Poker
* Release
	* the pagat guy
	* r/poker (or is there a variants sub? looks like not)
	* that facebook guy
* Future improvements (cool, but not necessary)
	* Consider splitting deal into up and down, for better structure analysis.
		* Could even have no-peek rules.
		* This would change distance calculations. Perhaps have a structure code on rules table.
	* Figure out 3-5-7 and multiple set common card games.
		* I'm really leaning to a second variable.
	* Look at distance analysis again.
		* Currently I like the idea of a tree starting with Showdown Straight.

Constants:
WORDS: Poker terms for defualt names of libraries. (list of str)

Classes:
Variant: A poker variant from the SQL database. (object)
Viewer: A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)
"""

import cmd
import csv
import os
import sqlite3 as sql
import traceback

WORDS = ['Ace', 'Bet', 'Card', 'Deal', 'Edge', 'Flush', 'Guts', 'High-Low', 'Inside', 'Joker', 'Kicker',
	'Lowball', 'Maverick', 'Nut', 'Odds', 'Pair', 'Qualifier', 'Royal', 'Showdown', 'Trips', 'Up',
	'Value', 'Wheel']

class Variant(object):
	"""
	A poker variant from the SQL database. (object)

	Attributes:
	cards: How many cards are used to make the final hand. (int)
	children: The database rows for this variant's children. (list of tuple)
	name: The name of the variant. (str)
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

	Overridden Methods:
	__init__
	__repr__
	__str__
	"""

	base_tags = ('common', 'discard', 'draw', 'flip', 'guts', 'pass', 'straight', 'stud')

	def __init__(self, row, cursor):
		"""
		Pull the other data needed to fill out the database. (None)

		Parameters:
		row: A row from the variants table of the database. (tuple)
		cursor: A cursor for executing SQL commands. (Cursor)
		"""
		# Save the base attributes
		self.variant_id = row['variant_id']
		self.name = row['name']
		self.cards = row['cards']
		self.players = row['players']
		self.rounds = row['rounds']
		self.max_seen = row['max_seen']
		self.wilds = row['wilds']
		self.parent_id = row['parent_id']
		self.source_id = row['source_id']
		# Get the tags for the game.
		code = 'select tag from tags, variant_tags where tags.tag_id = variant_tags.tag_id'
		code = f'{code} and variant_tags.variant_id = ?'
		cursor.execute(code, (self.variant_id,))
		tags = [row[0] for row in cursor.fetchall()]
		tags.sort()
		self.tags = [tag for tag in tags if tag in self.base_tags]
		self.tags += [tag for tag in tags if tag not in self.base_tags]
		# Get the rules for the game.
		code = 'select rules.* from rules, variant_rules where rules.rule_id = variant_rules.rule_id'
		code = f'{code} and variant_rules.variant_id = ? order by variant_rules.rule_order'
		cursor.execute(code, (self.variant_id,))
		self.rules = [row for row in cursor.fetchall()]
		# Get the source for the game.
		code = 'select name, link from sources where source_id = ?'
		cursor.execute(code, (self.source_id,))
		self.source, self.source_link = cursor.fetchone()
		# Get the children of the game.
		code = 'select * from variants where parent_id = ? order by variant_id'
		cursor.execute(code, (self.variant_id,))
		self.children = list(cursor.fetchall())

	def __repr__(self):
		"""Debugging text representation. (str)"""
		return f'<Variant {self.variant_id}: {self.name}>'

	def __str__(self):
		"""Human readable representation. (str)"""
		tags = ', '.join(self.tags)
		return f'{self.name} (#{self.variant_id}): {tags}'

class Viewer(cmd.Cmd):
	"""
	A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)

	Attributes:
	conn: A connection to the poker variant database. (Connection)
	cursor: An SQL command executor. (Cursor)
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

	Methods:
	do_load: Load variants into a library. (None)
	do_quit: Quit the interface. (True)
	do_reset: Reset the SQL database based on the csv files. (None)
	do_sql: Handle raw SQL code. (None)
	load_by_tags: Load variants into a library by tags. (None)
	load_csv_data: Load csv data from the old database. (dict of str: tuple)
	load_lookups: Load the lookups tables that are used internally. (None)
	next_library: Create and auto-name a new library. (None)
	reset_rule_types: Load the old rule type data into the database. (None)
	reset_rules: Load the old rule data into the database. (None)
	reset_sources: Load the old source data into the database. (None)
	reset_tags: Load the old tag data into the database. (None)
	reset_variant_rules: Load the old variant rules data into the database. (None)
	reset_variant_tags: Load the old variant tag data into the database. (None)
	reset_variants: Load the old variant data into the database. (None)
	show_library: Print out a library. (None)

	Overridden Methods:
	default
	do_shell
	onecmd
	precmd
	preloop
	postcmd
	"""

	aliases = {'q': 'quit'}
	prompt = 'IPVDB >> '

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

	def do_load(self, arguments):
		"""Load variants into a library."""
		words = arguments.split()
		if words[0].lower() == 'by':
			words.pop(0)
		if words[0].lower() in ('tag', 'tags'):
			self.load_by_tags(words[1:])

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
			self.reset_variant_rules(data)
			self.reset_variant_tags(data)
		else:
			# Note that the reset was aborted.
			print('Reset aborted.')

	def do_shell(self, arguments):
		"""Handle raw Python code. (!)"""
		print(eval(arguments))

	def do_sql(self, arguments):
		"""Handle raw SQL code."""
		self.cursor.execute(arguments)
		for row in self.cursor:
			print(row)
		self.conn.commit()

	def load_by_tags(self, tags):
		"""
		Load variants into a library by tags.

		Parameters:
		tags: A list of tags to load by. (list of str)
		"""
		# Parse out the tags.
		positive, negative = [], []
		for tag in tags:
			if tag.startswith('-'):
				negative.append(self.tag_ids[tag[1:].lower()])
			else:
				positive.append(self.tag_ids[tag.lower()])
		# Build the SQL code.
		code = 'select distinct variants.* from variants, variant_tags'
		code = f'{code} where variants.variant_id = variant_tags.variant_id'
		if positive:
			qmarks = ', '.join(['?'] * len(positive))
			code = f'{code} and variant_tags.tag_id in ({qmarks})'
		if negative:
			qmarks = ', '.join(['?'] * len(negative))
			code = f'{code} and variant_tags.tag_id not in ({qmarks})'
		# Pull the values.
		self.cursor.execute(code, positive + negative)
		key = self.next_library()
		for row in self.cursor.fetchall():
			if row[0] not in self.variants:
				self.variants[row[0]] = Variant(row, self.cursor)
			self.libraries[key].append(self.variants[row[0]])
		self.show_library()

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
		with open('rule_data.csv') as tag_file:
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

	def next_library(self):
		"""Create and auto-name a new library. (None)"""
		# Get the new library name.
		self.library_count += 1
		library_number = self.library_count
		words = []
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
		self.conn = sql.connect('poker_db.db')
		self.conn.row_factory = sql.Row
		self.cursor = self.conn.cursor()
		self.load_lookups()
		self.libraries = {}
		self.current_library = ''
		self.library_count = 0
		self.variants = {}
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
				raise ValueError(f'Rule ID mismatch for old rule #{rule[0]}, new rule #{rule_id}')
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
		tags = list(set(row[1] for row in data['tags']))
		tags.sort()
		new_tag_order = ['common', 'discard', 'draw', 'flip' 'guts', 'pass', 'straight', 'stud']
		new_tag_order.extend(tag for tag in tags if tag not in new_tag_order)
		self.tag_lookup = {}
		self.tag_ids = {}
		code = 'insert into tags(tag) values(?)'
		for tag in new_tag_order:
			self.cursor.execute(code, (tag,))
			tag_id = self.cursor.lastrowid
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
		print(f'The {key} library has {len(library)} variants in it.')
		for variant in library:
			print(variant)

if __name__ == '__main__':
	viewer = Viewer()
	viewer.cmdloop()
