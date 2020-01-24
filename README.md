# rekibots
Mastodon bots based on Ananas (https://github.com/chr-1x/ananas)

Prerequisites: python 3, ananas with prereqs (from pypi), pybooru with prereqs (from pypi), sqlite 3

## Setup
Clone, make sure rekibot.py is on your PYTHONPATH, setup a configuration file according to the instructions for Ananas and launch with ananas config.cfg -i. Proceed with the instructions. Next time run without the -i.

## Config entries

`class`: `rekibot.danboorubot` for image bot, or `rekibot.reminder` for alt text reminder bot

### Danbooru bot

`tags`: [REQUIRED] comma-separated booru tags to use for search in the api ex. `"gun,handgun,rifle,shotgun,tactical_clothes"`

`blacklist_tags`: (default = `"female_pervert,groping,breast_grab,pervert,sexual_harassment,sexually_suggestive,underwear_only,breast_press,topless,dangerous_beast,bottomless,no_panties,spoilers,revealing_clothes,pet_play,eargasm,daijoubu?_oppai_momu?,guro,bdsm,bondage,foot_worship,comic,cameltoe,osomatsu-san,osomatsu-kun,naked_sheet,foot_licking,nude,nude_cover,bunnysuit,randoseru,age_difference,younger,child,incest,you_gonna_get_raped,sisters,kindergarten_uniform,male_focus,1boy,multiple_boys,violence,horror,parody,no_humans,calne_ca,predator,goron,ichigo_mashimaro,manly,upskirt,banned_artist,santa_costume,injury,damaged,swastika,nazi,ss_insignia,everyone"`) (adds to default, not replaces) comma-separated booru tags to be blacklisted (bot-specific) ex. `"mecha_musume,xenosaga,kantai_collection"`

`mandatory_tags`: (default = `"girl"`) (adds to default, not replaces) comma-separated booru tags that must appear in the post to be posted ex. `"girl"`

`skip_tags`: (default = `"madoka_magica,touhou"`) (adds to default, not replaces) comma-separated booru tags to have a chance to skip over when posting (eg. if a tag is overrepresented in the database) ex. `"bayonetta,samus"`

`skip_chance`: (default = 75) percentage chance of skipping over a tag listed in `skip_tags`

`max_page`: (default = 300) how many pages to check on booru before stopping processing

`max_badpages`: (default = 10) how many pages with no new images to tolerate before stopping processing

`queue_length`: (default = 5) how many posts to draw from the db into memory at a time

`post_every`: (default = 30) how many minutes between each post from the bot (keep in mind they must fit within an hour, so any more than 30 will only post twice at most)

`offset`: (default = 0) offset posting time by this many minutes (eg. with a value of 2, instead of posting at 0 and 30 minutes past, post at 2 and 32 minutes past)

### Reminder bot

No custom entries
