# README for poker_db

Back in 2006 I made a sort-of database of poker variants. I put that on my website with some rather outdated HTML. Then I switched my website to MediaWiki, and did a (not very careful) translation of the original HTML to MediaWiki. Then my webhost got bought out by GoDaddy, and decided they were incapable of migrating a MediaWiki installation to their new servers. So I made a simple WordPress site, but this did not include the poker variants.

However, some people had linked to my collection, and were sad to see it go bye-bye. The idea here is to turn that database into a git repository, maybe with a simple CLI interface written in Python. It's a work in progress, complicated by the lack of the original data files. Everything has to be scraped from the original HTML files.

## Using the Database

To use the database, just go to the all_web folder, and open up the all_web_toc.html file. That provides links to all of the sub-files with the poker variants in them, and you can just browse from there. Alternatively, you can look in the all_md folder for markdown versions of those files. The markdown files do not have links, so there is no table of contents file. Also, since there are no links, variants with multiple tags are duplicated in the files for the different tags.

To use the interface to the database, download the zip of the latest release or clone the current repo. Then open poker_var.py with Python. The interface has tools for loading subsets of the database into libraries and then exporting them in different formats. Type 'help' for an introduction to those tools.

## Contributions

I am not accepting unsolicited pull requests. Talk to me before doing a pull request.

If you find a problem or want a change, please add a issue to the project. Please use the appropriate tags. Use 'bug' for bugs with the python program, 'data' for problems with the data (including typos in rules or incorrect variant attributes), 'variant' for requests to add a new variant to the database (this is on hold pending adding that functionality to the interface), and 'feature' for new feature request. Please be clear in your description of the problem/request. I reserve the right to reject any issue I don't understand or that doesn't have proper tags.

## Changes

I reviewed all of the rules by hand. A part of the old database that was not visible from the HTML output was that rules had a type and card number. So, for example, a rule to deal five cards down to each player would have a rule type of 'deal' and a card number of 5. Some rule types (like showdown rules) don't deal with cards, but the card number was still used to differentiate different sub-types of those rule types. Since this was not visible from the HTML, I had to recreate this from scratch. It's different than it was, but I'm not entirely sure at this point what it was.

I split a lot of the rules apart, to expand general usability. Two places this happened a lot were wild cards and showdowns. The old rules had 'aces and twos are wild.' Now that's two rules, 'aces are wild' and 'twos are wild.' I also made different rule types for limited wild cards (like bugs) and dead cards. Showdowns had a lot of complicated stuff in them. I split that stuff into showdown rules (how the pot is won or split), rank rules (how the hands are judged against each other), qualifier rules (things you have to beat in order to win), and match rules (for match pot and leg games).

I reviewed all of the variants by hand. There were a lot of errors in the variant attributes, like the number of cards seen or the maximum number of players. I'm kind of ashamed at how many errors there were, and I'm pretty sure I didn't get them all. If you see any, please add a ticket with the problem variant/error.

I also changed how some of the numbers (mainly the number of cards in the variant) were calculated. I tried to come up with more rigorous definitions, but that didn't always work out.

I removed 70 variants from the database. I came into this planning to get rid of the racist and misogynist variants. Younger me was willing to record them for historical purposes, older me wants nothing to do with them. I did leave in one misogynist variant because it is so damn popular, but I changed the name. I also removed variants I could not make sense of, if the original source was no longer available for clarification.

The old database categorized variants by draw, stud, common, and so on. I changed that into a tag system, like the one at pagat.com. Now if a stud variant has a draw in it, it can be coded as both draw and stud. I also included other tags, to assist in searching the database.

## License

This project is licensed under the GPLv3 license. See the LICENSE.txt file for details.