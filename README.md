# rekibots
Mastodon bots based on Ananas (https://github.com/chr-1x/ananas)

Prerequisites: python 3, ananas with prereqs (from pypi), pybooru with prereqs (from pypi), sqlite 3

## Setup
Clone, make sure rekibot.py is on your PYTHONPATH, setup a configuration file according to the instructions for Ananas and below and launch with ananas config.cfg -i. Proceed with the instructions. Next time run without the -i.

## Config entries

`class`: `rekibot.danboorubot` for image bot, or `rekibot.reminder` for alt text reminder bot

Apart from the default entires as covered in the readme for ananas, there are also custom entries:

### Danbooru bot

`tags`: [REQUIRED] comma-separated booru tags to use for search in the api ex. `"gun,handgun,rifle,shotgun,tactical_clothes"`

`blacklist_tags`: (default = `"spoilers,guro,bdsm,bondage,foot_worship,comic,naked_sheet,foot_licking,nude,nude_cover,randoseru,kindergarten_uniform,male_focus,1boy,2boys,3boys,4boys,5boys,6+boys,multiple_boys,horror,parody,no_humans,manly,banned_artist,swastika,nazi,ss_insignia,everyone,giantess"`) (adds to default, not replaces) comma-separated booru tags to be blacklisted ex. `"mecha_musume,xenosaga,kantai_collection"`

`mandatory_tags`: (default = `"1girl,2girls,3girls,4girls,5girls,6+girls,multiple_girls"`) (adds to default, not replaces) comma-separated booru tags. Any of them must appear in the post to be posted ex. `"1girl"`

`skip_tags`: (default = `"mahou_shoujo_madoka_magica,touhou"`) (adds to default, not replaces) comma-separated booru tags to have a chance to skip over when posting (eg. if a tag is overrepresented in the database) ex. `"bayonetta,samus_aran"`

`skip_chance`: (default = 75) percentage chance of skipping over a tag listed in `skip_tags`

`max_page`: (default = 300) how many pages to check on booru before stopping processing

`max_badpages`: (default = 10) how many pages with no new images to tolerate before stopping processing

`queue_length`: (default = 5) how many posts to draw from the db into memory at a time

`post_every`: (default = 30) how many minutes between each post from the bot (keep in mind they must fit within an hour, so any more than 30 will only post twice at most)

`offset`: (default = 0) offset posting time by this many minutes (eg. with a value of 2, instead of posting at 0 and 30 minutes past, post at 2 and 32 minutes past)

`log_file`: file to save logs in. If not present, will print to stdout

### Reminder bot

`log_file`: file to save logs in. If not present, will print to stdout
