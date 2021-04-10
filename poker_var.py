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
import math
import os
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
union, and xor commands. The library command allows for switching, renaming,
and sorting libraries.

The variant command allows for pulling out variants to view in full. You can
also use it to navigate the variant tree through a variant's parents and
children.

I'm still working on other functionality, including:
	* Filters.
		* Keep/Drop (one filter method, pass args through, replace/remove)
	* Libraries
		* Views (tag, summary, stats)
		* Copy (needed for filters)
	* Viewing the individual variants.
		* Navigation. (var parent, var child, step)
	* Exporting of libraries to files.
		* By tag (multiple?)
		* By cards (2-, 3, 4, ..., 8, 9, 10+)
	* The creation of new rules and variants.
	* The modification of current rules and variants (for data cleaning).
"""

WORDS = ['ace', 'bet', 'card', 'duece', 'edge', 'flush', 'guts', 'high-low', 'inside', 'joker', 'king',
	'lowball', 'maverick', 'nut', 'odds', 'pair', 'queen', 'royal', 'showdown', 'trips', 'up',
	'value', 'wheel']

class Variant(object):
	"""
	A poker variant from the SQL database. (object)

	Attributes:
	cards: How many cards are used to make the final hand. (int)
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

	Methods:
	display: Text representation for viewing in the CLI. (str)

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
		self.variant_id = row[0]
		self.name = row[1]
		self.cards = row[2]
		self.players = row[3]
		self.rounds = row[4]
		self.max_seen = row[5]
		self.wilds = row[6]
		self.parent_id = row[7]
		self.source_id = row[8]
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

	def __repr__(self):
		"""Debugging text representation. (str)"""
		return f'<Variant {self.variant_id}: {self.name}>'

	def __str__(self):
		"""Human readable representation. (str)"""
		tags = ', '.join(self.tags)
		return f'{self.name} (#{self.variant_id}): {tags}'

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

class Viewer(cmd.Cmd):
	"""
	A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)

	Attributes:
	conn: A connection to the poker variant database. (Connection)
	cursor: An SQL command executor. (Cursor)
	current_library: A key to the current library. (str)
	current_variant: The current variant. (Variant)
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

	Methods:
	do_intersection: Generate the intersection between two libraries. (None)
	do_library: Process library related commands. (None)
	do_load: Load variants into a library. (None)
	do_minus: Remove the values in the second libary from the first one. (None)
	do_page: Change the page being viewed. (None)
	do_quit: Quit the interface. (True)
	do_reset: Reset the SQL database based on the csv files. (None)
	do_sql: Handle raw SQL code. (None)
	do_union: Generate the union of two libraries. (None)
	do_xor: Generate the exclusive or of two libraries. (None)
	get_child: Get a child variant from the current variant. (None)
	get_libraries: Get libraries for binary set operations. (tuple of dict)
	library_list: Create a new library from a list of variants. (None)
	library_sql: Create a new library from the most recent query. (None)
	load_by_rules: Load variants into a library by rules. (None)
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
	do_help
	do_shell
	onecmd
	precmd
	preloop
	postcmd
	"""

	aliases = {'&': 'intersection', '-': 'minus', '|': 'union', 'lib': 'library', 'lbt': 'load by tag', 
		'lbr': 'load by rule', 'lbs': 'load by stats', 'p': 'page', 'q': 'quit', 'var': 'variant'}
	help_text = {'help': HELP_GENERAL}
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

	def do_library(self, arguments):
		"""
		Process library commands. (lib)

		Possible arguments include:
			* Nothing, to redisplay the current library.
			* The name of a library, to switch to that library.
			* 'rename' or 'rn' and a new name, to change the name of the current
				library.
			* 'sort' and a sort type to sort the current library. Valid sort types
				include: variant_id, name, cards, players, rounds, max_seen, wilds, 
				and tags. You can give a third argument of 'reverse' to reverse the
				sort order.
		"""
		# Parse arguments.
		words = arguments.split()
		command = words[0] if words else ''
		# Change libraries.
		if arguments in self.libraries:
			self.current_library = words[0]
		# Rename the current libraries.
		elif command in ('rename', 'rn'):
			new_name = ' '.join(words[1:])
			self.libraries[new_name] = self.libraries[self.current_library]
			del self.libraries[self.current_library]
			self.current_library = new_name
		# Show the current library.
		elif not arguments:
			pass  # it will be shown at the end of the method.
		# Sort the current library.
		elif command == 'sort':
			sorter = lambda variant: getattr(variant, words[1].lower())
			self.libraries[self.current_library].sort(key = sorter)
			if len(words) > 2 and words[3].lower() == 'reverse':
				self.libraries[self.current_library].reverse()
		# Error for invalid input.
		else:
			print('I do not understand.')
			return
		self.show_library()

	def do_load(self, arguments):
		"""
		Load variants into a library.

		Currently you can only load by rules, stats, or tags. The aliases for these
		are lbr, lbs, and lbt, respectively.

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
		words = arguments.split()
		if words[0].lower() == 'by':
			words.pop(0)
		search_type = words[0].lower()
		if search_type in ('rule', 'rules'):
			self.load_by_rules(words[1:])
		elif search_type == 'stats':
			self.load_by_stats(words[1:])
		elif search_type in ('tag', 'tags'):
			self.load_by_tags(words[1:])
		else:
			print('Invalid search type.')

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
		self.library_sql()

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
		self.library_sql()

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
		self.library_sql()

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
		# Set the variant tracking.
		self.current_variant = None
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
			print(variant)

if __name__ == '__main__':
	viewer = Viewer()
	viewer.cmdloop()
