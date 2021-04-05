"""
poker_db.py

A command line interface for Ichabod's Poker Variant Database.

WARNING: This program uses eval in Viewer.do_shell. Before running this program
over a network or other insecure situations, you should nerf that method.

To Do:
* Convert to sqlite.
* Create the user interface.
	* Filters
	* SQL searches
	* Output formats
	* New variant command.
	* Random poker game? Random 1st rule, random 2nd rule based on 1st, ...
* Create output formats (markdown, html, json?)
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

Classes:
Viewer: A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)
"""

import cmd
import csv
import sqlite3 as sql
import traceback

class Viewer(cmd.Cmd):
	"""
	A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)

	Attributes:
	conn: A connection to the poker variant database. (Connection)
	cursor: An SQL command executor. (Cursor)
	rule_type_lookup: A lookup table for rule types. (dict of int: str) 
	rule_type_ids: A lookup tabe for rule type IDs. (dict of str: int)

	Class Attributes:
	aliases: Command aliases. (dict of str: str)

	Methods:
	do_quit: Quit the interface. (True)
	do_reset: Reset the SQL database based on the csv files. (None)
	load_csv_data: Load csv data from the old database. (dict of str: tuple)
	reset_rule_types: Load the old rule type data into the database. (None)

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
			# Reset the table definitions.
			with open('poker_var.sql') as code_file:
				db_code = code_file.read()
				self.cursor.execute('drop tables;')
				self.cursor.execute(db_code)
				self.conn.commit()
			# Load the old data.
			data = self.load_csv_data()
			self.reset_rule_types(data)
			self.reset_sources(data)
		else:
			# Note that the reset was aborted.
			print('Reset aborted.')

	def do_shell(self, arguments):
		"""Handle raw Python code. (!)"""
		print(eval(arguments))

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
			data['game-rules'] = tuple(game_rules_reader)
		with open('game_tags.csv') as game_tags_file:
			game_tags_reader = csv.reader(game_tags_file)
			data['game-tags'] = tuple(game_tags_reader)
		with open('rule_data.csv') as rule_file:
			rule_reader = csv.reader(rule_file)
			data['rules'] = tuple(rule_reader)
		with open('rule_data.csv') as tag_file:
			tags_reader = csv.reader(tag_file)
			data['tags'] = tuple(tags_reader)

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
		self.cursor = self.conn.cursor()
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
		rule_types.append('variant')
		rule_types.sort()
		self.rule_type_lookup = {}
		self.rule_type_ids = {}
		code = 'insert into rule_types(text) values(?)'
		for rule_type in rule_types:
			self.cursor.execute(code, (rule_type,))
			type_id = self.cursor.lastrowid
			self.rule_type_ids[rule_type] = type_id
			self.rule_type_lookup[type_id] = rule_type

	def reset_source(self, data):
		"""
		Load the old source data into the database. (None)

		Parameters:
		data: The data loaded from the csv files. (dict of str: tuple)
		"""
		pass

if __name__ == '__main__':
	viewer = Viewer()
	viewer.cmdloop()
