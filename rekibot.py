# encoding: utf-8
import ananas
import random
import sqlite3
import urllib.request
from pybooru import Danbooru, Moebooru
import magic
import time
import re
import sys
from datetime import datetime
from html import unescape
import os
import mastodon


class AltTextReminder(ananas.PineappleBot):
    @ananas.schedule(minute='*/10')
    def reload_configs(self):
        function_name = 'reload_configs'
        self.init()
        self.load_config(global_config=True)
        self.load_config()
        if self.verbose:
            self.log(function_name, f'admin = {str(self.admin)}')
            self.log(function_name, f'verbose_logging = {str(self.verbose_logging)}')
            self.log(function_name, f'verbose = {str(self.verbose)}')
            self.log(function_name, f'log_file = {str(self.log_file)}')
            self.log(function_name, f'log_to_stderr = {str(self.log_to_stderr)}')

    def load_config(self, global_config=False):
        if global_config:
            config = ananas.PineappleBot.Config(self.config._bot, self.config._filename)
            config.load('global', silent=not self.verbose_logging)
        else:
            config = self.config
            config.load(self.config._name, silent=not self.verbose_logging)

        if 'admin' in config and len(config.admin) > 0: self.admin = config.admin
        if 'verbose' in config and (config.verbose.lower() in ['no', 'yes', 'very']):
            if config.verbose.lower() == 'yes':
                self.verbose_logging = True
                self.verbose = False
            elif config.verbose.lower() == 'very':
                self.verbose_logging = True
                self.verbose = True
            elif config.verbose.lower() == 'no':
                self.verbose_logging = False
                self.verbose = False
        if 'log_file' in config and len(config.log_file) > 0:
            self.log_file = open(config.log_file, 'a')
            self.log_to_stderr = False

    def log(self, bot_id, msg):
        if bot_id is None:
            bot_id = self.__class__.__name__
        print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {self.config._name}.{id}: {str(msg)}',
              file=self.log_file, flush=True)
    
    def init(self):
        self.me = None
        self.last_checked_post = None
        self.admin = 'pup_hime@slime.global'
        self.verbose_logging = False  # the bot's verbosity
        self.verbose = False  # ananas' own verbosity
        self.log_file = sys.stderr
        self.log_to_stderr = True

    def start(self):
        function_name = "start"
        self.reload_configs()
        self.mastodon = mastodon.Mastodon(client_id=self.config.client_id,
                                          client_secret=self.config.client_secret,
                                          access_token=self.config.access_token,
                                          api_base_url=f'https://{self.config.domain}',
                                          ratelimit_method='throw')
        self.me = self.mastodon.account_verify_credentials()
        self.last_checked_post = self.mastodon.timeline_home()[0]
        self.log(function_name, 'Bot started.')

    @ananas.schedule(minute='*')
    def check_follows(self):
        function_name = 'check_follows'
        try:
            self.log(function_name, 'starting follow check')
            self.me = self.mastodon.account_verify_credentials()
            my_id = self.me['id']
            followers_count = self.me['followers_count']
            followers = self.mastodon.account_followers(my_id, limit=80)
            while len(followers) < followers_count: followers = followers + self.mastodon.fetch_remaining(followers)
            following_count = self.me['following_count']
            following = self.mastodon.account_following(my_id, limit=80)
            while len(following) < following_count: following = following + self.mastodon.fetch_remaining(following)
            following_ids = []
            for followed in following: following_ids = following_ids + [followed['id'], ]
            follower_ids = []
            for follower in followers: follower_ids = follower_ids + [follower['id'], ]
            processed = 1
            for follower in follower_ids:
                if follower not in following_ids:
                    if not self.mastodon.account_relationships(follower)[0]['requested']:
                        if 'moved' in self.mastodon.account(follower):
                            self.mastodon.account_block(follower)
                            self.mastodon.account_unblock(follower)
                            if self.verbose_logging:
                                self.log(function_name, f'Softblocked user {str(follower)}.')
                            time.sleep(5)
                        else:
                            try:
                                self.mastodon.account_follow(follower, reblogs=False)
                                if self.verbose_logging:
                                    self.log(function_name, f'Attempted to follow user {str(follower)}.')
                                time.sleep(5)
                            except Exception as e:
                                if len(e.args) > 1 and e.args[1] == 403:
                                    if self.verbose_logging:
                                        self.log(function_name, f'Attempted to follow user {str(follower)} but got 403.')
                                    self.mastodon.account_block(follower)
                                    self.mastodon.account_unblock(follower)
                                    if self.verbose_logging:
                                        self.log(function_name, f'Softblocked user {str(follower)}.')
                                    time.sleep(5)
                                else: raise e
                    processed = processed + 1
                if not processed % 40: break
            processed = 1
            for followed in following_ids:
                if followed not in follower_ids:
                    if not self.mastodon.account_relationships(followed)[0]['requested']:
                        self.mastodon.account_unfollow(followed)
                        if self.verbose_logging: self.log(function_name, f'Unfollowed user {str(followed)}.')
                        time.sleep(5)
                        processed = processed + 1
                if not processed % 40: break
        except Exception as e:
            self.log(function_name, e)
            return

    @ananas.schedule(minute="*/2")
    def check_posts(self):
        function_name = "check_posts"
        try:
            posts = self.mastodon.timeline_home(since_id=self.last_checked_post['id'])
            if len(posts) > 0:
                for post in posts:
                    if len(post['media_attachments']) > 0 and post['reblog'] is None and post['in_reply_to_id'] is None:
                        flag = False
                        for attachment in post['media_attachments']:
                            if attachment['description'] is None and attachment['type'] == 'image': flag = True
                        if flag:
                            self.mastodon.status_post(
                                f'@{post["account"]["acct"]} hey, just so you know, this status includes an attachment with missing accessibility (alt) text.',
                                in_reply_to_id=(post['id']),
                                visibility='direct')
                            if self.verbose_logging: self.log(function_name, 'Posted reply.')
                            time.sleep(5)
                self.last_checked_post = posts[0]
        except Exception as e:
            self.log(function_name, e)
            return

    @ananas.reply
    def handle_reply(self, status, user):
        function_name = 'handle_reply'
        try:
            if user['acct'] == self.admin:
                if 'delete this!' in status['content']: self.mastodon.status_delete(status['in_reply_to_id'])
                elif 'announce! ' in status['content']:
                    text = re.sub('<[^<]+?>', '', status['content'])
                    text = unescape(text)
                    self.mastodon.status_post(text.split('announce! ')[-1],
                                              in_reply_to_id=None,
                                              media_ids=None,
                                              sensitive=False,
                                              visibility='unlisted',
                                              spoiler_text=None)
        except Exception as e:
            self.log(function_name, e)
            return


class ImageBot(ananas.PineappleBot):
    @ananas.schedule(minute="*/10")
    def reload_configs(self):
        function_name = "reload_configs"
        self.init()
        self.load_config(global_config=True)
        self.load_config()
        if self.verbose:
            self.log(function_name, f'booru_type = {str(self.booru_type)}')
            self.log(function_name, f'tags = {str(self.tags)}')
            self.log(function_name, f'log_file = {str(self.log_file)}')
            self.log(function_name, f'log_to_stderr = {str(self.log_to_stderr)}')
            self.log(function_name, f'verbose_logging = {str(self.verbose_logging)}')
            self.log(function_name, f'verbose = {str(self.verbose)}')
            self.log(function_name, f'admin = {str(self.admin)}')
            self.log(function_name, f'booru_url = {str(self.booru_url)}')
            self.log(function_name, f'db_file = {str(self.db_file)}')
            self.log(function_name, f'blacklist_tags = {str(self.blacklist_tags)}')
            self.log(function_name, f'mandatory_tags = {str(self.mandatory_tags)}')
            self.log(function_name, f'cw_tags = {str(self.cw_tags)}')
            self.log(function_name, f'ratings = {str(self.ratings)}')
            self.log(function_name, f'skip_tags = {str(self.skip_tags)}')
            self.log(function_name, f'skip_chance = {str(self.skip_chance)}')
            self.log(function_name, f'max_page = {str(self.max_page)}')
            self.log(function_name, f'max_bad_pages = {str(self.max_bad_pages)}')
            self.log(function_name, f'queue_length = {str(self.queue_length)}')
            self.log(function_name, f'post_every = {str(self.post_every)}')
            self.log(function_name, f'offset = {str(self.offset)}')
            self.log(function_name, f'rebuild_db = {str(self.rebuild_db)}')
            self.log(function_name, f'migrate_flags = {str(self.migrate_flags)}')

        if self.booru_type in ('danbooru', 'e621'): self.client = Danbooru(site_url=self.booru_url)
        elif self.booru_type == 'moebooru': self.client = Moebooru(site_url=self.booru_url)
        if self.rebuild_db: self.build_db()

    def load_config(self, global_config=False):
        if global_config:
            config = ananas.PineappleBot.Config(self.config._bot, self.config._filename)
            config.load('global', silent=not self.verbose_logging)
        else:
            config = self.config
            config.load(self.config._name, silent=not self.verbose_logging)

        if 'booru_type' in config and config.booru_type.lower() in ['e621', 'danbooru']: self.booru_type = config.booru_type
        if 'tags' in config and len(config.tags) > 0: self.tags = config.tags.split(',')
        if 'log_file' in config and len(config.log_file) > 0:
            self.log_file = open(config.log_file, "a")
            self.log_to_stderr = False
        if 'verbose' in config and config.verbose.lower() in ['no', 'yes', 'very']:
            if config.verbose.lower() == 'yes':
                self.verbose_logging = True
                self.verbose = False
            elif config.verbose.lower() == 'very':
                self.verbose_logging = True
                self.verbose = True
            elif config.verbose.lower() == 'no':
                self.verbose_logging = False
                self.verbose = False
        if 'admin' in config and len(config.admin) > 0: self.admin = config.admin
        if 'booru_url' in config and len(config.booru_url) > 0: self.booru_url = config.booru_url
        if 'db_file' in config and len(config.db_file) > 0: self.db_file = config.db_file
        if 'blacklist_tags' in config and len(config.blacklist_tags) > 0:
            self.blacklist_tags = f"{self.blacklist_tags},{config.blacklist_tags}".strip(",")
        if 'mandatory_tags' in config and len(config.mandatory_tags) > 0:
            self.mandatory_tags = f"{self.mandatory_tags},{config.mandatory_tags}".strip(",")
        if 'skip_tags' in config and len(config.skip_tags) > 0:
            self.skip_tags = f"{self.skip_tags},{config.skip_tags}".strip(",")
        if 'cw_tags' in config and len(config.cw_tags) > 0:
            self.cw_tags = f"{self.cw_tags},{config.cw_tags}".strip(",")
        if 'ratings' in config and len(config.ratings) > 0: self.ratings = config.ratings
        if 'skip_chance' in config and config.skip_chance.isdigit(): self.skip_chance = int(config.skip_chance)
        if 'max_page' in config and config.max_page.isdigit(): self.max_page = int(config.max_page)
        if 'max_bad_pages' in config and config.max_bad_pages.isdigit(): self.max_bad_pages = int(config.max_bad_pages)
        if 'queue_length' in config and config.queue_length.isdigit(): self.queue_length = int(config.queue_length)
        if 'post_every' in config and config.post_every.isdigit(): self.post_every = int(config.post_every)
        if 'offset' in config and config.offset.isdigit(): self.offset = int(config.offset)
        if 'rebuild_db' in config and config.rebuild_db in ['no', 'yes', 'no_migration']:
            if config.rebuild_db == 'no_migration':
                self.rebuild_db = True
                self.migrate_flags = False
            elif config.rebuild_db == 'yes':
                self.rebuild_db = True
                self.migrate_flags = True
            elif config.rebuild_db == 'no':
                self.rebuild_db = False
                self.migrate_flags = False

    def log(self, bot_id, msg):
        if bot_id is None:
            bot_id = self.__class__.__name__
        print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {self.config._name}.{bot_id}: {str(msg)}',
              file=self.log_file, flush=True)

    def init(self):
        self.client = None
        self.queue = []
        self.proxy = urllib.request.ProxyHandler({})
        self.opener = urllib.request.build_opener(self.proxy)
        self.mime = magic.Magic(mime=True)
        self.admin = 'pup_hime@slime.global'
        self.verbose_logging = False  # the bot's verbosity
        self.verbose = False  # ananas' own verbosity
        self.log_file = sys.stderr
        self.log_to_stderr = True

        self.blacklist_tags = ""
        self.mandatory_tags = ""
        self.cw_tags = ""
        self.skip_tags = ""

        self.skip_chance = 75
        self.max_page = 300
        self.max_bad_pages = 10
        self.queue_length = 5
        self.post_every = 30
        self.offset = 0
        self.tags = ['1girl', ]

        self.rebuild_db = False
        self.migrate_flags = False

        self.booru_url = 'https://danbooru.donmai.us'
        self.booru_type = 'danbooru'
        self.ratings = 'e,g,q,s'

        self.create_table_sql = 'create table if not exists images (danbooru_id integer primary key, url_danbooru ' \
                                'text, url_source text, tags text, posted integer default 0, blacklisted integer ' \
                                'default 0, UNIQUE(url_danbooru), UNIQUE(url_source)); '
        self.insert_sql = 'insert into images(danbooru_id, url_danbooru, url_source, tags) values(?, ?, ?, ?);'
        self.select_sql = 'select danbooru_id, url_danbooru, url_source, tags from images ' \
                          'where blacklisted = 0 and posted = 0 order by random() limit ?; '
        self.count_not_posted_sql = 'select count(*) from images where blacklisted = 0 and posted = 0;'
        self.count_posted_sql = 'select count(*) from images where blacklisted = 0 and posted = 1;'
        self.count_blacklisted_sql = 'select count(*) from images where blacklisted = 1'
        self.flag_blacklisted_sql = 'update images set blacklisted = 1 where danbooru_id = ?;'
        self.add_tags_sql = "update images set tags = tags || ' ' || ? where danbooru_id = ?;"
        self.remove_posted_flag_sql = 'update images set posted = 0;'
        self.flag_posted_sql = 'update images set posted = 1 where danbooru_id = ?;'
        self.migrate_db_sql1 = 'alter table images rename to images_old;'
        self.migrate_db_sql2 = 'update images set blacklisted = 1 ' \
                               'where danbooru_id in (select danbooru_id from images_old where blacklisted = 1); '
        self.migrate_db_sql3 = 'update images set posted = 1 ' \
                               'where danbooru_id in (select danbooru_id from images_old where posted = 1); '
        self.migrate_db_sql4 = 'drop table images_old;'

    def build_db(self):
        function_name = "build_db"
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()

        if self.rebuild_db:
            if self.migrate_flags:
                self.log(function_name, 'Database rebuild with migration starting...')
            else:
                self.log(function_name, 'Database rebuild starting...')
            try:
                if self.verbose_logging: self.log(function_name, self.migrate_db_sql1)
                cur.execute(self.migrate_db_sql1)
            except Exception as e:
                self.log(function_name, e)
                conn.rollback()
                conn.close()
                return

        if self.verbose_logging: self.log(function_name, self.create_table_sql)
        cur.execute(self.create_table_sql)
        conn.commit()
        conn.close()

        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()

        cur.execute(self.select_sql, (self.queue_length,))
        if len(cur.fetchall()) == 0: self.update_db()
        conn.close()

        if self.rebuild_db:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            try:
                if self.migrate_flags:
                    if self.verbose_logging: self.log(function_name, self.migrate_db_sql2)
                    cur.execute(self.migrate_db_sql2)
                    if self.verbose_logging: self.log(function_name, self.migrate_db_sql3)
                    cur.execute(self.migrate_db_sql3)
                if self.verbose_logging: self.log(function_name, self.migrate_db_sql4)
                cur.execute(self.migrate_db_sql4)
            except Exception as e:
                self.log(function_name, e)
                conn.rollback()
                conn.close()
                return

            conn.commit()
            conn.close()
            self.log(function_name, 'Database rebuild completed.')
            self.rebuild_db = False
            self.migrate_flags = False
            self.config.rebuild_db = 'no'
            self.config.save()

    def start(self):
        function_name = 'start'
        self.opener.addheaders = [('User-Agent',
                                   'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.1 Safari/603.1.30')]
        urllib.request.install_opener(self.opener)
        self.db_file = f'{self.config._name}.db'
        self.reload_configs()
        self.build_db()
        try:
            self.mastodon.account_update_credentials(note=f'Pic every 30 min. Report bad stuff to @{self.admin}')
        except Exception as e:
            self.log(function_name, e)
        self.log(function_name, 'Bot started.')

    @ananas.schedule(hour='*/6', minute=15)
    def update_db(self):
        function_name = 'update_db'
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        for tag in self.tags:
            if self.verbose_logging: self.log(function_name, f'Pulling from tag \'{tag}\'.')
            bad_pages = 0
            for page in range(1, self.max_page + 1):
                while True:
                    posts = None
                    try:
                        posts = self.client.post_list(tags=tag, page=str(page), limit=200)
                    except:
                        continue
                    else:
                        break
                if len(posts) == 0:
                    if self.verbose_logging: self.log(function_name, 'No more posts. Break processing.')
                    break
                counter = 0
                if self.booru_type == "e621":
                    for post in posts['posts']:
                        tag_string = (' '.join((' '.join(post['tags']['general']),
                                                ' '.join(post['tags']['species']),
                                                ' '.join(post['tags']['character']),
                                                ' '.join(post['tags']['copyright']),
                                                ' '.join(post['tags']['artist']),
                                                ' '.join(post['tags']['meta']),
                                                ' '.join(post['tags']['lore']))))
                        while '  ' in tag_string:
                            tag_string = tag_string.replace('  ', ' ')
                        if (len(post['sources']) > 0
                            and not any(x in post['sources'][0].lower() for x in ['drawfag', '.png', '.jpg', '.gif'])) \
                                and post['flags']['deleted'] is False \
                                and not self.check_tags(tag_string, self.blacklist_tags) \
                                and (self.check_tags(tag_string, self.mandatory_tags)
                                     or len(self.mandatory_tags) == 0) \
                                and post['rating'] in self.ratings.split(","):
                            source_url = post['sources'][0]
                            danbooru_url = post['file']['url']
                            try:
                                cur.execute(self.insert_sql, (int(post['id']), danbooru_url, source_url, tag_string))
                            except:
                                continue
                            else:
                                counter = counter + 1
                else:
                    for post in posts:
                        if ((not any(x in post['source'].lower() for x in ['drawfag', '.png', '.jpg', '.gif'])
                             and post['source'] != '')
                            or post['pixiv_id'] is not None) \
                                and post['is_deleted'] is False \
                                and not self.check_tags(post['tag_string'], self.blacklist_tags) \
                                and (self.check_tags(post['tag_string'], self.mandatory_tags)
                                     or len(self.mandatory_tags) == 0) \
                                and post['rating'] in self.ratings.split(","):
                            if post['pixiv_id'] is None:
                                source_url = post['source']
                            else:
                                source_url = f'https://www.pixiv.net/artworks/{post["pixiv_id"]}'
                            if 'file_url' in post:
                                danbooru_url = post['file_url']
                            elif 'large_file_url' in post:
                                danbooru_url = post['large_file_url']
                            else:
                                continue
                            try:
                                cur.execute(self.insert_sql, (int(post['id']), danbooru_url, source_url, post['tag_string']))
                            except:
                                continue
                            else:
                                counter = counter + 1
                if self.verbose_logging: self.log(function_name, f'Page {page} - inserted {counter} entries.')
                if counter == 0:
                    bad_pages = bad_pages + 1
                    if bad_pages == self.max_bad_pages:
                        if self.verbose_logging:
                            self.log(function_name, f'No new posts on {bad_pages} pages in a row. Break processing.')
                        break
                else:
                    bad_pages = 0
        conn.commit()
        conn.close()
        if self.verbose_logging: self.log(function_name, 'Completed.')

    def blacklist(self, post_id, reason):
        function_name = 'blacklist'
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(self.flag_blacklisted_sql, (post_id,))
        conn.commit()
        conn.close()
        self.log(function_name, f'Blacklisted {self.booru_url}/posts/{post_id} Reason: {reason}.')

    def add_tags(self, post_id, tags):
        function_name = 'add_tags'
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(self.add_tags_sql, (tags, post_id))
        conn.commit()
        conn.close()
        self.log(function_name, f'Added tags to post {post_id}: {tags}.')

    def check_tags(self, post_tag_string, tag_string, mode="or"):
        results = []
        if len(tag_string) == 0:
            return False
        if mode == "or":
            tag_list = tag_string.split(",")
        else:
            tag_list = tag_string.split(" ")
        post_tag_list = post_tag_string.split(" ")
        for tag in tag_list:
            if " " in tag:
                results.append(self.check_tags(post_tag_string, tag, 'and'))
            else:
                results.append(tag in post_tag_list)
        if mode == "or":
            return any(results)
        else:
            return all(results)

    @ananas.schedule(minute='*')
    def post(self):
        function_name = 'post'
        if not any(datetime.now().minute == x + self.offset for x in range(0, 60, self.post_every)): return
        while True:
            while len(self.queue) == 0:
                try:
                    conn = sqlite3.connect(self.db_file)
                    cur = conn.cursor()
                    cur.execute(self.select_sql, (self.queue_length,))
                    self.queue = cur.fetchall()
                    if len(self.queue) == 0:
                        self.log(function_name, 'No valid entries. Resetting db.')
                        cur.execute(self.remove_posted_flag_sql)
                        conn.commit()
                    else:
                        cur.executemany(self.flag_posted_sql, [(str(item[0]),) for item in self.queue])
                        conn.commit()
                    conn.close()
                    if self.verbose_logging: self.log(function_name, f'Refilled queue with {len(self.queue)} entries.')
                except:
                    continue
            post_id, url, src, tags = self.queue.pop()
            if self.check_tags(tags, self.blacklist_tags):
                intersect = list(set(tags.split(" ")).intersection(self.blacklist_tags.split(",")))
                and_tags = [i for i in self.blacklist_tags.split(",") if " " in i]
                for tag in and_tags:
                    found = [i for i in tags.split(" ") if i in tag.split(" ")]
                    if len(found) == len(tag.split(" ")):
                        intersect.append(found)
                self.blacklist(post_id, f'Found blacklist tags {str(intersect)}')
                continue
            if not self.check_tags(tags, self.mandatory_tags) and len(self.mandatory_tags) > 0:
                self.blacklist(post_id, 'Mandatory tags not found')
                continue
            if self.check_tags(tags, self.skip_tags) and random.randint(1, 100) <= self.skip_chance:
                intersect = list(set(tags.split(' ')).intersection(self.skip_tags.split(',')))
                and_tags = [i for i in self.skip_tags.split(',') if " " in i]
                for tag in and_tags:
                    found = [i for i in tags.split(' ') if i in tag.split(' ')]
                    if len(found) == len(tag.split(' ')):
                        intersect.append(found)
                if self.verbose_logging:
                    self.log(function_name, f'Skipped {post_id}. Reason: Found skip tags {str(intersect)}')
                continue
            spoiler_text = None
            if self.check_tags(tags, self.cw_tags):
                spoiler_text = list(set(tags.split(' ')).intersection(self.cw_tags.split(',')))
                and_tags = [i for i in self.cw_tags.split(",") if " " in i]
                for tag in and_tags:
                    found = [i for i in tags.split(' ') if i in tag.split(' ')]
                    if len(found) == len(tag.split(' ')):
                        spoiler_text.append(found)
                spoiler_text = f'CW: {", ".join(spoiler_text)}'
            saved_file_path = ''
            try:
                saved_file_path = urllib.request.urlretrieve(url)[0]
                with open(saved_file_path, 'rb') as file:
                    media_dict = self.mastodon.media_post(file.read(),
                                                          mime_type=self.mime.from_file(saved_file_path),
                                                          description=f'Image with the tags: {tags.replace(" ", ", ").replace("_", " ")[:1400].strip(",")}')
                status_text = f'{self.booru_url}/posts/{post_id}\r\nsource: {src}'
                self.mastodon.status_post(status_text,
                                          in_reply_to_id=None,
                                          media_ids=(media_dict['id'],),
                                          sensitive=True,
                                          visibility='unlisted',
                                          spoiler_text=spoiler_text)
            except Exception as e:
                if len(e.args) > 1 and e.args[1] == 422: self.blacklist(post_id, f'{e.args[2]}. {e.args[3]}')
                else: self.log(function_name, f'Post {self.booru_url}/posts/{post_id} threw exception: {e}')
                continue
            else:
                if self.verbose_logging: self.log(function_name, 'Posted.')
                break
            finally:
                if os.path.isfile(saved_file_path): os.remove(saved_file_path)

    @ananas.reply
    def handle_reply(self, status, user):
        function_name = 'handle_reply'
        try:
            if user['acct'] == self.admin:
                if 'delete this!' in status['content']:
                    status_in_question = self.mastodon.status(status['in_reply_to_id'])
                    try:
                        self.mastodon.status_delete(status['in_reply_to_id'])
                    except:
                        return
                    text = re.sub('<[^<]+?>', '', status_in_question['content'])
                    text = unescape(text)
                    post_id = re.search("posts/([0-9]+)source", text)
                    if post_id is not None and len(post_id.groups()) > 0:
                        post_id = post_id.groups()[0]
                        self.blacklist(post_id, "Admin request")
                if 'tag this!' in status['content']:
                    status_in_question = self.mastodon.status(status['in_reply_to_id'])
                    try:
                        self.mastodon.status_delete(status['in_reply_to_id'])
                    except:
                        return
                    new_tags = status['content']
                    new_tags = re.sub('<[^<]+?>', '', new_tags)
                    new_tags = unescape(new_tags)
                    new_tags = new_tags.split("tag this!")[-1].strip()
                    text = re.sub('<[^<]+?>', '', status_in_question['content'])
                    text = unescape(text)
                    post_id = re.search('posts/([0-9]+)source', text)
                    if post_id is not None and len(post_id.groups()) > 0:
                        post_id = post_id.groups()[0]
                        self.add_tags(post_id, new_tags)
                elif 'announce! ' in status['content']:
                    text = re.sub('<[^<]+?>', '', status['content'])
                    text = unescape(text)
                    self.mastodon.status_post(text.split('announce! ')[-1],
                                              in_reply_to_id=None,
                                              media_ids=None,
                                              sensitive=False,
                                              visibility='unlisted',
                                              spoiler_text=None)
                elif 'report!' in status['content']:
                    conn = sqlite3.connect(self.db_file)
                    cur = conn.cursor()
                    cur.execute(self.count_posted_sql)
                    posted = cur.fetchone()[0]
                    cur.execute(self.count_not_posted_sql)
                    not_posted = cur.fetchone()[0]
                    cur.execute(self.count_blacklisted_sql)
                    blacklisted = cur.fetchone()[0]
                    conn.close()
                    self.mastodon.status_post(
                        f'@{self.admin} DB: {self.db_file}\r\nnot posted: {not_posted}\r\nposted: {posted}\r\nblacklisted: {blacklisted}',
                        in_reply_to_id=status['id'],
                        media_ids=None,
                        sensitive=False,
                        visibility="unlisted",
                        spoiler_text=None)
        except Exception as e:
            self.log(function_name, e)
            return
