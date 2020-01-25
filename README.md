# rekibots
Mastodon bots based on Ananas (https://github.com/chr-1x/ananas)

Prerequisites: python 3, ananas with prereqs (from pypi), pybooru with prereqs (from pypi), sqlite 3

## Setup
Clone, make sure rekibot.py is on your PYTHONPATH, setup a configuration file according to the instructions for Ananas and below and launch with ananas config.cfg -i. Proceed with the instructions. Next time run without the -i.

For an example config see https://github.com/puphime/rekibots/blob/master/debug.cfg

## Config entries

`class`: `rekibot.danboorubot` for image bot, or `rekibot.reminder` for alt text reminder bot

Apart from the default entires as covered in the readme for ananas, there are also custom entries:

### Danbooru bot

`tags`: [REQUIRED] comma-separated booru tags to use for search in the api ex. `"gun,handgun,rifle,shotgun,tactical_clothes"`

`blacklist_tags`: (default = "") comma-separated booru tags to be blacklisted.

`mandatory_tags`: (default = "") comma-separated booru tags. Any of them must appear in the post to be posted.

`skip_tags`: (default = "") comma-separated booru tags to have a chance to skip over when posting (eg. if a tag is overrepresented in the database, or you just don't like it).

`mandatory_tag_mode`: (default = any) require any or all mandatory tags (only accepts any|all)

`skip_chance`: (default = 75) percentage chance of skipping over a post containing a tag listed in `skip_tags`.

`max_page`: (default = 300) how many pages to check on booru before stopping processing.

`max_badpages`: (default = 10) how many pages with no new images to tolerate before stopping processing.

`queue_length`: (default = 5) how many posts to draw from the db into memory at a time.

`post_every`: (default = 30) how many minutes between each post from the bot (keep in mind they must fit within an hour, so any more than 30 will only post twice at most).

`offset`: (default = 0) offset posting time by this many minutes (eg. with a value of 2, instead of posting at 0 and 30 minutes past, post at 2 and 32 minutes past).

`log_file`: file to save logs in. If not present, will print to stdout.

### Reminder bot

`log_file`: file to save logs in. If not present, will print to stdout.
