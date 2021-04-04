"""
poker_db.py

A command line interface for Ichabod's Poker Variant Database.

WARNING: This program uses eval in Viewer.do_shell. Before running this program
over a network or other insecure situations, you should nerf that method.

To Do:
* Restart git, with a remote on github.
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
import traceback

class Viewer(cmd.Cmd):
	"""
	A command line interface for Ichabod's Poker Variant Database. (cmd.Cmd)

	Class Attributes:
	aliases: Command aliases. (dict of str: str)

	Methods:
	do_quit: Quit the interface. (True)

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
		return True

	def do_shell(self, arguments):
		"""Handle raw Python code. (!)"""
		print(eval(arguments))

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
		self.load_data()
		self.current = self.variants['Five Card Draw']
		self.current_rule = self.rules[950]   # One-eyed jacks are wild.
		self.changed = set()
		self.count, self.match_index = 0, 0
		self.matches, self.rule_matches = [], []
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

if __name__ == '__main__':
	viewer = Viewer()
	viewer.cmdloop()
