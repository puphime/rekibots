# rekibots
Mastodon bots based on Ananas (https://github.com/chr-1x/ananas)

Prerequisites: python 3, ananas with prereqs (requires most recent version from github!), pybooru with prereqs (from pypi), sqlite 3

## General information

### Image bot
Builds a local database and posts images from any Danbooru compatible image board on a schedule, based on tag searches, with tag filters.

### Alt text reminder bot
Reminds followers gently that they forgot to add alt text to their media.

## Setup
Clone, make sure rekibot.py is on your PYTHONPATH, setup a configuration file according to the instructions for Ananas and below and launch with ananas config.cfg -i. Proceed with the instructions. Next time run without the -i.

For an example config see https://github.com/puphime/rekibots/blob/master/debug.cfg

## Config entries

`class`: `rekibot.ImageBot` for image bot, `rekibot.AltTextReminder` for alt text reminder bot

Apart from the default entires as covered in the readme for ananas, there are also custom entries:

### Image bot

`tags`: (default = "1girl") comma-separated search terms for the booru, ex. `"rifle,2girls gun"`

`blacklist_tags`: (default = "") comma-separated tags to be blacklisted. Allows for rudimentary logic ie. Spaces are AND and commas are OR. ANDs are resolved first. ex. `"loli,monster_girl_encyclopedia character_profile"`

`skip_tags`: (default = "") comma-separated tags that enable a post to be skipped based on `skip_chance`. Allows for rudimentary logic ie. Spaces are AND and commas are OR. ANDs are resolved first.

`skip_chance`: (default = 75) percentage chance of skipping over a post containing a tag listed in `skip_tags`.

`mandatory_tags`: (default = "") comma-separated tags that must be present in the post. Allows for rudimentary logic ie. Spaces are AND and commas are OR. ANDs are resolved first.

`booru_url`: (default = "https://danbooru.donmai.us") The URL for the booru the bot should pull images from. (for e621 the URL is currently hard coded into the library, so this will only change displayed URLs in posts)

`booru_type`: (default = "danbooru") (available values = `danbooru, moebooru, e621`) The type of booru the url points at.

`max_badpages`: (default = 10) how many 200-item pages with no new images to tolerate before stopping processing.

`max_page`: (default = 300) how many 200-item pages to check on booru before stopping processing.

`db_file`: sqlite database file. If not present, will default to `[bot name].db` in the working directory.

`queue_length`: (default = 5) how many posts to draw from the db into memory at a time.

`ratings`: (default = "s,q,e") what ratings to accept posts with, ex. `"s,q"`

`rebuild_db`: (default = no) (available values = `yes, no, no_migration`) trigger database rebuild. `no_migration` causes the blacklisted and posted flags to be discarded. After rebuild is done, automatically set to `no`.

`post_every`: (default = 30) how many minutes between each post from the bot (keep in mind they must fit within an hour, so any more than 30 will only post once at most).

`offset`: (default = 0) offset posting time by this many minutes (eg. with a value of 2, instead of posting at 0 and 30 minutes past, post at 2 and 32 minutes past).

`log_file`: file to save logs in. If not present, will print to stderr.

`verbose`: (default = no) (available values = `yes, no, very`) increase the amount of information produced by rekibots.

### Reminder bot

`log_file`: file to save logs in. If not present, will print to stderr.

`verbose`: (default = no) (available values = `yes, no, very`) increase the amount of information produced by rekibots.

### Global section

Additionally, by adding a [global] section in your config file you can set nearly every configuration parameter (except `class`, `domain`, `client_id`, `client_secret`, `access_token`) globally for all bots. **In this case, tag parameters (except `tags`) will be combined, not overwritten.**
