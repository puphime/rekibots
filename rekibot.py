# encoding: utf-8
import yippi
import ananas
import random
import sqlite3
import urllib.request
from pybooru import Danbooru
import magic
import time
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
import os

class reminder(ananas.PineappleBot):
    @ananas.schedule(minute = "*/10")
    def reload_config(self):
        self.config.load(self.config._name, silent = not self.verbose_logging)
        self.log_file = sys.stderr
        self.load_global_config()
        if "log_file" in self.config and len(self.config.log_file) > 0:
            self.log_file = open(self.config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in self.config and (self.config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif self.config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
            elif self.config.verbose.lower() == "no":
                self.verbose_logging = False
                self.verbose = False
        if "admin" in self.config and len(self.config.admin) > 0: self.admin = self.config.admin

    def log(self, id, msg):
        if id is None:
            id = self.__class__.__name__
        print("[{0:%Y-%m-%d %H:%M:%S}] {1}.{2}: {3}".format(datetime.now(), self.config._name, id, str(msg)), file = self.log_file, flush = True)
        
    def init(self):
        self.admin = "pup_hime@slime.global"
        self.verbose_logging = False #the bot's verbosity
        self.verbose = False #ananas' own verbosity
        self.log_file = sys.stderr
        self.log_to_stderr = True
        
    def load_global_config(self):
        global_config = ananas.PineappleBot.Config(self.config._bot, self.config._filename)
        global_config.load("global", silent = not self.verbose_logging)
        if "log_file" in global_config and len(global_config.log_file) > 0:
            self.log_file = open(global_config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in global_config and (global_config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif global_config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
        if "admin" in global_config and len(global_config.admin) > 0: self.admin = global_config.admin
    
    def start(self):
        fname = "start"
        self.reload_config()
        self.me = self.mastodon.account_verify_credentials()
        self.last_checked_post = self.mastodon.timeline_home()[0]
        self.h = HTMLParser()
        self.log(fname, "Bot started.")
        
    @ananas.schedule(minute = "*", second = 30)
    def check_follows(self):
        fname = "check_follows"
        try:
            self.me = self.mastodon.account_verify_credentials()
            my_id = self.me['id']
            followers_count = self.me['followers_count']
            followers = self.mastodon.account_followers(my_id, limit = 80)
            if len(followers) < followers_count: followers = self.mastodon.fetch_remaining(followers)
            following_count = self.me['following_count']
            following = self.mastodon.account_following(my_id, limit = 80)
            if len(following) < following_count: following = self.mastodon.fetch_remaining(following)
            followingids = []
            for followed in following: followingids = followingids + [followed['id'], ]
            followerids = []
            for follower in followers: followerids = followerids + [follower['id'], ]
            for follower in followerids:
                if follower not in followingids:
                    time.sleep(1)
                    if not self.mastodon.account_relationships(follower)[0]['requested']:
                        if "moved" in self.mastodon.account(follower):
                            self.mastodon.account_block(follower)
                            self.mastodon.account_unblock(follower)
                            if self.verbose_logging: self.log(fname, "Softblocked user {}.".format(str(follower)))
                        else:
                            ret = self.mastodon.account_follow(follower, reblogs = False)
                            if self.verbose_logging: self.log(fname, "Attempted to follow user {}.".format(str(follower)))
            for followed in followingids:
                if followed not in followerids:
                    time.sleep(1)
                    if not self.mastodon.account_relationships(followed)[0]['requested']:
                        self.mastodon.account_unfollow(followed) 
                        if self.verbose_logging: self.log(fname, "Unfollowed user {}.".format(str(followed)))
        except Exception as e:
            self.log(fname, e)
            return
   
    @ananas.schedule(minute = "*", second = 0)
    def check_posts(self):
        fname = "check_posts"
        try:
            posts = self.mastodon.timeline_home(since_id = self.last_checked_post['id'])
            if len(posts) > 0:
                for post in posts:
                    if len(post['media_attachments']) > 0 and post['reblog'] is None and post['in_reply_to_id'] is None and post['account']['acct'] != self.admin:
                        flag = False
                        for attachment in post['media_attachments']: 
                            if attachment['description'] is None: flag = True
                        if flag:
                            self.mastodon.status_post('@' + post['account']['acct'] + ' hey, just so you know, this status includes an attachment with missing accessibility (alt) text.', in_reply_to_id = (post['id']), visibility = 'direct')
                            if self.verbose_logging: self.log(fname, "Posted reply.")
                self.last_checked_post = posts[0]
        except Exception as e:
            self.log(fname, e)
            return
            
    @ananas.reply
    def handle_reply(self, status, user):
        fname = "handle_reply"
        try:
            if user['acct'] == self.admin:
                if 'delete this!' in status['content']: self.mastodon.status_delete(status['in_reply_to_id'])
                elif '!announce' in status['content']:
                    text = re.sub('<[^<]+?>', '', status['content'])
                    text = self.h.unescape(text)
                    self.mastodon.status_post(text.split('announce! ')[-1], in_reply_to_id = None, media_ids = None, sensitive = False, visibility = "unlisted", spoiler_text = None)
        except Exception as e:
            self.log(fname, e)
            return
        
class danboorubot(ananas.PineappleBot):
    @ananas.schedule(minute = "*/10")
    def reload_config(self):
        self.config.load(self.config._name, silent = not self.verbose_logging)
        self.tags = self.config.tags.split(',')
        self.db_file = "{0}.db".format(self.config._name)
        self.log_file = sys.stderr
        self.log_to_stderr = True
        self.load_global_config()
        if "log_file" in self.config and len(self.config.log_file) > 0:
            self.log_file = open(self.config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in self.config and (self.config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif self.config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
            elif self.config.verbose.lower() == "no":
                self.verbose_logging = False
                self.verbose = False
        if "admin" in self.config and len(self.config.admin) > 0: self.admin = self.config.admin
        if "booru_url" in self.config and len(self.config.booru_url) > 0: self.booru_url = self.config.booru_url
        if 'db_file' in self.config and len(self.config.db_file) > 0: self.db_file = self.config.db_file
        if 'blacklist_tags' in self.config and len(self.config.blacklist_tags) > 0: self.blacklist_tags = (self.blacklist_tags + "," + self.config.blacklist_tags).strip(",")
        if 'mandatory_tags' in self.config and len(self.config.mandatory_tags) > 0: self.mandatory_tags = (self.mandatory_tags + "," + self.config.mandatory_tags).strip(",")
        if 'skip_tags' in self.config and len(self.config.skip_tags) > 0: self.skip_tags = (self.skip_tags + "," + self.config.skip_tags).strip(",")
        if 'skip_chance' in self.config and self.config.skip_chance.isdigit(): self.skip_chance = int(self.config.skip_chance)
        if 'max_page' in self.config and self.config.max_page.isdigit(): self.max_page = int(self.config.max_page)
        if 'max_badpages' in self.config and self.config.max_badpages.isdigit(): self.max_badpages = int(self.config.max_badpages)
        if 'queue_length' in self.config and self.config.queue_length.isdigit(): self.queue_length = int(self.config.queue_length)
        if 'post_every' in self.config and self.config.post_every.isdigit(): self.post_every = int(self.config.post_every)
        if 'offset' in self.config and self.config.offset.isdigit(): self.offset = int(self.config.offset)
        if 'rebuild_db' in self.config and self.config.rebuild_db in ['no', 'yes', 'with_migration']:
            if self.config.rebuild_db == "yes": self.rebuild_db = True
            elif self.config.rebuild_db == "with_migration":
                self.rebuild_db = True
                self.migrate_flags = True
            elif self.config.rebuild_db == "no":
                self.rebuild_db = False
                self.migrate_flags = False

    def log(self, id, msg):
        if id is None:
            id = self.__class__.__name__
        print("[{0:%Y-%m-%d %H:%M:%S}] {1}.{2}: {3}".format(datetime.now(), self.config._name, id, str(msg)), file = self.log_file, flush = True)
       
    def init(self):
        self.mime = magic.Magic(mime = True)
        self.proxy = urllib.request.ProxyHandler({})
        self.opener = urllib.request.build_opener(self.proxy)
        self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.1 Safari/603.1.30')]
        urllib.request.install_opener(self.opener)
        self.h = HTMLParser()
        
        self.admin = "pup_hime@slime.global"
        self.verbose_logging = False #the bot's verbosity
        self.verbose = False #ananas' own verbosity
        self.log_file = sys.stderr
        self.log_to_stderr = True
        
        self.queue = []
        self.blacklist_tags = ""
        self.mandatory_tags = ""
        self.skip_tags = ""
        
        self.skip_chance = 75
        self.max_page = 300
        self.max_badpages = 10    
        self.queue_length = 5
        self.post_every = 30
        self.offset = 0
        self.tags = []
        self.db_file = ""
        
        self.rebuild_db = False
        self.migrate_flags = False
        
        self.booru_url = 'https://danbooru.donmai.us'
        
        self.create_table_sql = "create table if not exists images (danbooru_id integer primary key, url_danbooru text, url_source text, tags text, posted integer default 0, blacklisted integer default 0, UNIQUE(url_danbooru), UNIQUE(url_source));"
        self.insert_sql = "insert into images(danbooru_id, url_danbooru, url_source, tags) values(?, ?, ?, ?);"
        self.select_sql = "select danbooru_id, url_danbooru, url_source, tags from images where blacklisted = 0 and posted = 0 order by random() limit ?;"
        self.flag_blacklisted_sql = "update images set blacklisted = 1 where danbooru_id = ?;"
        self.remove_posted_flag_sql = "update images set posted = 0;"
        self.flag_posted_sql = "update images set posted = 1 where danbooru_id = ?;"
        self.migrate_db_sql1 = "alter table images rename to images_old;"
        self.migrate_db_sql2 = "update images set blacklisted = 1 where danbooru_id in (select danbooru_id from images_old where blacklisted = 1);"
        self.migrate_db_sql3 = "update images set posted = 1 where danbooru_id in (select danbooru_id from images_old where posted = 1);"
        self.migrate_db_sql4 = "drop table images_old;"
    
    def load_global_config(self):
        global_config = ananas.PineappleBot.Config(self.config._bot, self.config._filename)
        global_config.load("global", silent = not self.verbose_logging)
        if "log_file" in global_config and len(global_config.log_file) > 0:
            self.log_file = open(global_config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in global_config and (global_config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif global_config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
        if "admin" in global_config and len(global_config.admin) > 0: self.admin = global_config.admin
        if "booru_url" in global_config and len(global_config.booru_url) > 0: self.booru_url = global_config.booru_url
        if 'blacklist_tags' in global_config and len(global_config.blacklist_tags) > 0: self.blacklist_tags = global_config.blacklist_tags
        if 'mandatory_tags' in global_config and len(global_config.mandatory_tags) > 0: self.mandatory_tags = global_config.mandatory_tags
        if 'skip_tags' in global_config and len(global_config.skip_tags) > 0: self.skip_tags = global_config.skip_tags
        if 'skip_chance' in global_config and global_config.skip_chance.isdigit(): self.skip_chance = int(global_config.skip_chance)
        if 'max_page' in global_config and global_config.max_page.isdigit(): self.max_page = int(global_config.max_page)
        if 'max_badpages' in global_config and global_config.max_badpages.isdigit(): self.max_badpages = int(global_config.max_badpages)
        if 'queue_length' in global_config and global_config.queue_length.isdigit(): self.queue_length = int(global_config.queue_length)
        if 'post_every' in global_config and global_config.post_every.isdigit(): self.post_every = int(global_config.post_every)
        if 'offset' in global_config and global_config.offset.isdigit(): self.offset = int(global_config.offset)
        if 'rebuild_db' in global_config and global_config.rebuild_db in ['no', 'yes', 'with_migration']:
            if global_config.rebuild_db == "yes": self.rebuild_db = True
            elif global_config.rebuild_db == "with_migration":
                self.rebuild_db = True
                self.migrate_flags = True
                
    def start(self):   
        fname = "start"
        self.reload_config()
        
        self.client = Danbooru(site_url = self.booru_url)
        
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        
        if self.rebuild_db:
            if self.migrate_flags: self.log(fname, "Database rebuild with migration starting...")
            else: self.log(fname, "Database rebuild starting...")
            try:
                if self.verbose_logging: self.log(fname, "ALTER TABLE images RENAME TO images_old;")
                cur.execute(self.migrate_db_sql1)
            except Exception as e:
                self.log(fname, e)
                conn.rollback()
                conn.close()
                return
        
        if self.verbose_logging: self.log(fname, "CREATE TABLE IF NOT EXISTS images (danbooru_id INTEGER PRIMARY KEY, url_danbooru TEXT, url_source TEXT, tags TEXT, posted INTEGER DEFAULT 0, blacklisted INTEGER DEFAULT 0, UNIQUE(url_danbooru), UNIQUE(url_source));")
        cur.execute(self.create_table_sql)
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        
        cur.execute(self.select_sql, (self.queue_length, ))
        if len(cur.fetchall()) == 0: self.update_db()
        conn.close()
        
        if self.rebuild_db:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            try:
                if self.migrate_flags:
                    if self.verbose_logging: self.log(fname, "UPDATE images SET blacklisted = 1 WHERE danbooru_id IN (SELECT danbooru_id FROM images_old WHERE blacklisted = 1);")
                    cur.execute(self.migrate_db_sql2)
                    if self.verbose_logging: self.log(fname, "UPDATE images SET posted = 1 WHERE danbooru_id IN (SELECT danbooru_id FROM images_old WHERE posted = 1);")
                    cur.execute(self.migrate_db_sql3)
                if self.verbose_logging: self.log(fname, "DROP TABLE images_old;")
                cur.execute(self.migrate_db_sql4)
            except Exception as e:
                self.log(fname, e)
                conn.rollback()
                conn.close()
                return
                
            conn.commit()
            conn.close()
            self.log(fname, "Database rebuild completed.")
            self.config.rebuild_db = "no"
        self.log(fname, "Bot started.")
        
    @ananas.schedule(hour = "*/6", minute = 15)
    def update_db(self):
        fname = "update_db"
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        for t in self.tags:
            if self.verbose_logging: self.log(fname, "Pulling from tag '{}'.".format(t))
            badpages = 0
            for page in range(1, self.max_page + 1):
                while True:
                    try: posts = self.client.post_list(tags = t, page = str(page), limit = 200)
                    except: continue
                    else: break
                if len(posts) == 0:
                    if self.verbose_logging: self.log(fname, "No more posts. Break processing.")
                    break
                counter = 0
                for post in posts:
                    if ((not any(x in post['source'].lower() for x in ['drawfag', '.png', '.jpg', '.gif']) and post['source'] != '') or post['pixiv_id'] is not None) and post['is_deleted'] == False and not self.check_tags(post['tag_string'], self.blacklist_tags) and (self.check_tags(post['tag_string'], self.mandatory_tags) or len(self.mandatory_tags) == 0):
                        if post['pixiv_id'] is not None: source_url = 'https://www.pixiv.net/artworks/{0}'.format(post['pixiv_id'])
                        else: source_url = post['source']
                        if 'file_url' in post: danbooru_url = post['file_url']
                        elif 'large_file_url' in post: danbooru_url = post['large_file_url']
                        else: continue
                        try: cur.execute(self.insert_sql, (int(post['id']), danbooru_url, source_url, post['tag_string']))
                        except: continue
                        else: counter = counter + 1
                if self.verbose_logging: self.log(fname, "Page {} - inserted {} entries.".format(page, counter))
                if counter == 0:
                    badpages = badpages + 1
                    if badpages == self.max_badpages:
                        if self.verbose_logging: self.log(fname, "No new posts on {} pages in a row. Break processing.".format(badpages))
                        break
                else: badpages = 0
        conn.commit()
        conn.close()
        if self.verbose_logging: self.log(fname, "Completed.")
        
    def blacklist(self, id, reason):
        fname = "blacklist"
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(self.flag_blacklisted_sql, (id, ))
        conn.commit()
        conn.close()
        self.log(fname, "Blacklisted {}/posts/{} Reason: {}.".format(self.booru_url, id, reason))
        
    def check_tags(self, post_tag_string, tag_string, mode = "or"):
        results = []
        if len(tag_string) == 0: return False
        if mode == "or": tag_list = tag_string.split(",")
        else: tag_list = tag_string.split(" ")
        post_tag_list = post_tag_string.split(" ")
        for tag in tag_list:
            if " " in tag: results.append(self.check_tags(post_tag_string, tag, "and"))
            else: results.append(tag in post_tag_list)
        if mode == "or": return any(results)
        else: return all(results)
        
    @ananas.schedule(minute = "*")
    def post(self):
        fname = "post"
        if not any(datetime.now().minute == x + self.offset for x in range(0, 60, self.post_every)): return
        while True:
            while len(self.queue) == 0:
                try:
                    conn = sqlite3.connect(self.db_file)
                    cur = conn.cursor()
                    cur.execute(self.select_sql, (self.queue_length, ))
                    self.queue = cur.fetchall()
                    if len(self.queue) == 0:
                        self.log(fname, "No valid entries. Resetting db.")
                        cur.execute(self.remove_posted_flag_sql)
                        conn.commit()
                    else:
                        cur.executemany(self.flag_posted_sql, [(str(item[0]), ) for item in self.queue])
                        conn.commit()
                    conn.close()
                    if self.verbose_logging: self.log(fname, "Refilled queue with {} entries.".format(len(self.queue)))
                except: continue
            id, url, src, tags = self.queue.pop()
            if self.check_tags(tags, self.blacklist_tags):
                intersect = list(set(tags.split(" ")).intersection(self.blacklist_tags.split(",")))
                andtags = [i for i in self.blacklist_tags.split(",") if " " in i]
                for tag in andtags:
                    found = [i for i in tags.split(" ") if i in tag.split(" ")]
                    if len(found) == len(tag.split(" ")):
                        intersect.append(found)
                self.blacklist(id, "Found blacklist tags {}".format(str(intersect)))
                continue
            if not self.check_tags(tags, self.mandatory_tags) and len(self.mandatory_tags) > 0:
                self.blacklist(id, "Mandatory tags not found")
                continue
            if self.check_tags(tags, self.skip_tags):
                if random.randint(1, 100) <= self.skip_chance:
                    intersect = list(set(tags.split(" ")).intersection(self.skip_tags.split(",")))
                    andtags = [i for i in self.skip_tags.split(",") if " " in i]
                    for tag in andtags:
                        found = [i for i in tags.split(" ") if i in tag.split(" ")]
                        if len(found) == len(tag.split(" ")):
                            intersect.append(found)
                    if self.verbose_logging: self.log(fname, "Skipped {}. Reason: Found skip tags {}".format(id, str(intersect)))
                    continue
            saved_file_path = ""
            try:
                saved_file_path = urllib.request.urlretrieve(url)[0]
                with open(saved_file_path, 'rb') as file: mediadict = self.mastodon.media_post(file.read(), self.mime.from_file(saved_file_path))
                status_text = '{0}/posts/{1}\r\nsource: {2}'.format(self.booru_url, id, src)
                self.mastodon.status_post(status_text, in_reply_to_id = None, media_ids = (mediadict['id'], ), sensitive = True, visibility = "unlisted", spoiler_text = None)
            except Exception as e:
                if e.args[1] == 422: self.blacklist(id, "{0}. {1}".format(e.args[2], e.args[3]))
                else: self.log(fname, "Post {}/posts/{} threw exception: {}".format(self.booru_url, id, e))
                continue
            else:
                if self.verbose_logging: self.log(fname, "Posted.")
                break
            finally: 
                if os.path.isfile(saved_file_path): os.remove(saved_file_path)

    @ananas.reply
    def handle_reply(self, status, user):
        fname = "handle_reply"
        try:
            if user['acct'] == self.admin:
                if 'delete this!' in status['content']:
                    status_in_question = self.mastodon.status(status['in_reply_to_id'])
                    self.mastodon.status_delete(status['in_reply_to_id'])
                    text = re.sub('<[^<]+?>', '', status_in_question['content'])
                    text = self.h.unescape(text)
                    id = re.search("posts\/([0-9]+)source", text)
                    id = id.groups()[0]
                    self.blacklist(id, "Admin request")
                elif 'announce! ' in status['content']:
                    text = re.sub('<[^<]+?>', '', status['content'])
                    text = self.h.unescape(text)
                    self.mastodon.status_post(text.split('announce! ')[-1], in_reply_to_id = None, media_ids = None, sensitive = False, visibility = "unlisted", spoiler_text = None)
        except Exception as e:
            self.log(fname, e)
            return

class e621bot(ananas.PineappleBot):
    @ananas.schedule(minute = "*/10")
    def reload_config(self):
        self.config.load(self.config._name, silent = not self.verbose_logging)
        self.tags = self.config.tags.split(',')
        self.db_file = "{0}.db".format(self.config._name)
        self.log_file = sys.stderr
        self.log_to_stderr = True
        self.load_global_config()
        if "log_file" in self.config and len(self.config.log_file) > 0:
            self.log_file = open(self.config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in self.config and (self.config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif self.config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
            elif self.config.verbose.lower() == "no":
                self.verbose_logging = False
                self.verbose = False
        if "admin" in self.config and len(self.config.admin) > 0: self.admin = self.config.admin
        if 'db_file' in self.config and len(self.config.db_file) > 0: self.db_file = self.config.db_file
        if 'blacklist_tags' in self.config and len(self.config.blacklist_tags) > 0: self.blacklist_tags = (self.blacklist_tags + "," + self.config.blacklist_tags).strip(",")
        if 'mandatory_tags' in self.config and len(self.config.mandatory_tags) > 0: self.mandatory_tags = (self.mandatory_tags + "," + self.config.mandatory_tags).strip(",")
        if 'skip_tags' in self.config and len(self.config.skip_tags) > 0: self.skip_tags = (self.skip_tags + "," + self.config.skip_tags).strip(",")
        if 'rating' in self.config and len(self.config.rating) > 0: self.rating = self.config.rating
        if 'skip_chance' in self.config and self.config.skip_chance.isdigit(): self.skip_chance = int(self.config.skip_chance)
        if 'max_page' in self.config and self.config.max_page.isdigit(): self.max_page = int(self.config.max_page)
        if 'max_badpages' in self.config and self.config.max_badpages.isdigit(): self.max_badpages = int(self.config.max_badpages)
        if 'queue_length' in self.config and self.config.queue_length.isdigit(): self.queue_length = int(self.config.queue_length)
        if 'post_every' in self.config and self.config.post_every.isdigit(): self.post_every = int(self.config.post_every)
        if 'offset' in self.config and self.config.offset.isdigit(): self.offset = int(self.config.offset)
        if 'rebuild_db' in self.config and self.config.rebuild_db in ['no', 'yes', 'with_migration']:
            if self.config.rebuild_db == "yes": self.rebuild_db = True
            elif self.config.rebuild_db == "with_migration":
                self.rebuild_db = True
                self.migrate_flags = True
            elif self.config.rebuild_db == "no":
                self.rebuild_db = False
                self.migrate_flags = False

    def log(self, id, msg):
        if id is None:
            id = self.__class__.__name__
        print("[{0:%Y-%m-%d %H:%M:%S}] {1}.{2}: {3}".format(datetime.now(), self.config._name, id, str(msg)), file = self.log_file, flush = True)
       
    def init(self):
        self.mime = magic.Magic(mime = True)
        self.proxy = urllib.request.ProxyHandler({})
        self.opener = urllib.request.build_opener(self.proxy)
        self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.1 Safari/603.1.30')]
        urllib.request.install_opener(self.opener)
        self.h = HTMLParser()
        
        self.admin = "pup_hime@slime.global"
        self.verbose_logging = False #the bot's verbosity
        self.verbose = False #ananas' own verbosity
        self.log_file = sys.stderr
        self.log_to_stderr = True
        
        self.queue = []
        self.blacklist_tags = ""
        self.mandatory_tags = ""
        self.skip_tags = ""
        
        self.skip_chance = 75
        self.max_page = 300
        self.max_badpages = 10    
        self.queue_length = 5
        self.post_every = 30
        self.offset = 0
        self.tags = []
        self.db_file = ""
        
        self.rebuild_db = False
        self.migrate_flags = False
        
        self.booru_url = "https://e621.net"
        self.rating = "s"
        
        self.create_table_sql = "create table if not exists images (danbooru_id integer primary key, url_danbooru text, url_source text, tags text, posted integer default 0, blacklisted integer default 0, UNIQUE(url_danbooru), UNIQUE(url_source));"
        self.insert_sql = "insert into images(danbooru_id, url_danbooru, url_source, tags) values(?, ?, ?, ?);"
        self.select_sql = "select danbooru_id, url_danbooru, url_source, tags from images where blacklisted = 0 and posted = 0 order by random() limit ?;"
        self.flag_blacklisted_sql = "update images set blacklisted = 1 where danbooru_id = ?;"
        self.remove_posted_flag_sql = "update images set posted = 0;"
        self.flag_posted_sql = "update images set posted = 1 where danbooru_id = ?;"
        self.migrate_db_sql1 = "alter table images rename to images_old;"
        self.migrate_db_sql2 = "update images set blacklisted = 1 where danbooru_id in (select danbooru_id from images_old where blacklisted = 1);"
        self.migrate_db_sql3 = "update images set posted = 1 where danbooru_id in (select danbooru_id from images_old where posted = 1);"
        self.migrate_db_sql4 = "drop table images_old;"
    
    def load_global_config(self):
        global_config = ananas.PineappleBot.Config(self.config._bot, self.config._filename)
        global_config.load("global", silent = not self.verbose_logging)
        if "log_file" in global_config and len(global_config.log_file) > 0:
            self.log_file = open(global_config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in global_config and (global_config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif global_config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
            else:
                self.verbose_logging = False
                self.verbose = False
        if "admin" in global_config and len(global_config.admin) > 0: self.admin = global_config.admin
        if 'blacklist_tags' in global_config and len(global_config.blacklist_tags) > 0: self.blacklist_tags = global_config.blacklist_tags
        if 'mandatory_tags' in global_config and len(global_config.mandatory_tags) > 0: self.mandatory_tags = global_config.mandatory_tags
        if 'skip_tags' in global_config and len(global_config.skip_tags) > 0: self.skip_tags = global_config.skip_tags
        if 'skip_chance' in global_config and global_config.skip_chance.isdigit(): self.skip_chance = int(global_config.skip_chance)
        if 'rating' in global_config and len(global_config.rating) > 0: self.rating = global_config.rating
        if 'max_page' in global_config and global_config.max_page.isdigit(): self.max_page = int(global_config.max_page)
        if 'max_badpages' in global_config and global_config.max_badpages.isdigit(): self.max_badpages = int(global_config.max_badpages)
        if 'queue_length' in global_config and global_config.queue_length.isdigit(): self.queue_length = int(global_config.queue_length)
        if 'post_every' in global_config and global_config.post_every.isdigit(): self.post_every = int(global_config.post_every)
        if 'offset' in global_config and global_config.offset.isdigit(): self.offset = int(global_config.offset)
        if 'rebuild_db' in global_config and global_config.rebuild_db in ['no', 'yes', 'with_migration']:
            if global_config.rebuild_db == "yes": self.rebuild_db = True
            elif global_config.rebuild_db == "with_migration":
                self.rebuild_db = True
                self.migrate_flags = True
               
    def start(self):   
        fname = "start"
        self.reload_config()
        
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        
        if self.rebuild_db:
            if self.migrate_flags: self.log(fname, "Database rebuild with migration starting...")
            else: self.log(fname, "Database rebuild starting...")
            try:
                if self.verbose_logging: self.log(fname, "ALTER TABLE images RENAME TO images_old;")
                cur.execute(self.migrate_db_sql1)
            except Exception as e:
                self.log(fname, e)
                conn.rollback()
                conn.close()
                return
        
        if self.verbose_logging: self.log(fname, "CREATE TABLE IF NOT EXISTS images (danbooru_id INTEGER PRIMARY KEY, url_danbooru TEXT, url_source TEXT, tags TEXT, posted INTEGER DEFAULT 0, blacklisted INTEGER DEFAULT 0, UNIQUE(url_danbooru), UNIQUE(url_source));")
        cur.execute(self.create_table_sql)
        conn.commit()
        conn.close()
        
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        
        cur.execute(self.select_sql, (self.queue_length, ))
        if len(cur.fetchall()) == 0: self.update_db()
        conn.close()
        
        if self.rebuild_db:
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            try:
                if self.migrate_flags:
                    if self.verbose_logging: self.log(fname, "UPDATE images SET blacklisted = 1 WHERE danbooru_id IN (SELECT danbooru_id FROM images_old WHERE blacklisted = 1);")
                    cur.execute(self.migrate_db_sql2)
                    if self.verbose_logging: self.log(fname, "UPDATE images SET posted = 1 WHERE danbooru_id IN (SELECT danbooru_id FROM images_old WHERE posted = 1);")
                    cur.execute(self.migrate_db_sql3)
                if self.verbose_logging: self.log(fname, "DROP TABLE images_old;")
                cur.execute(self.migrate_db_sql4)
            except Exception as e:
                self.log(fname, e)
                conn.rollback()
                conn.close()
                return
                
            conn.commit()
            conn.close()
            self.log(fname, "Database rebuild completed.")
            self.config.rebuild_db = "no"
        self.log(fname, "Bot started.")
        
    @ananas.schedule(hour = "*/6", minute = 15)
    def update_db(self):
        fname = "update_db"
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        for t in self.tags:
            if self.verbose_logging: self.log(fname, "Pulling from tag '{}'.".format(t))
            badpages = 0
            for page in range(1, self.max_page + 1):
                while True:
                    try: posts = yippi.search().post(tags = [t,], page = str(page), limit = 200, rating = self.rating)
                    except: continue
                    else: break
                if len(posts) == 0:
                    if self.verbose_logging: self.log(fname, "No more posts. Break processing.")
                    break
                counter = 0
                for post in posts:
                    if (post.source is not None and not any(x in post.source.lower() for x in ['drawfag', '.png', '.jpg', '.gif']) and post.source != '') and not self.check_tags(" ".join(post.tags), self.blacklist_tags) and (self.check_tags(" ".join(post.tags), self.mandatory_tags) or len(self.mandatory_tags) == 0):
                        source_url = post.source
                        danbooru_url = post.file_url
                        try: cur.execute(self.insert_sql, (int(post.id), danbooru_url, source_url, " ".join(post.tags)))
                        except: continue
                        else: counter = counter + 1
                if self.verbose_logging: self.log(fname, "Page {} - inserted {} entries.".format(page, counter))
                if counter == 0:
                    badpages = badpages + 1
                    if badpages == self.max_badpages:
                        if self.verbose_logging: self.log(fname, "No new posts on {} pages in a row. Break processing.".format(badpages))
                        break
                else: badpages = 0
        conn.commit()
        conn.close()
        if self.verbose_logging: self.log(fname, "Completed.")
        
    def blacklist(self, id, reason):
        fname = "blacklist"
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(self.flag_blacklisted_sql, (id, ))
        conn.commit()
        conn.close()
        self.log(fname, "Blacklisted {}/post/show/{} Reason: {}.".format(self.booru_url, id, reason))
        
    def check_tags(self, post_tag_string, tag_string, mode = "or"):
        results = []
        if len(tag_string) == 0: return False
        if mode == "or": tag_list = tag_string.split(",")
        else: tag_list = tag_string.split(" ")
        post_tag_list = post_tag_string.split(" ")
        for tag in tag_list:
            if " " in tag: results.append(self.check_tags(post_tag_string, tag, "and"))
            else: results.append(tag in post_tag_list)
        if mode == "or": return any(results)
        else: return all(results)
        
    @ananas.schedule(minute = "*")
    def post(self):
        fname = "post"
        if not any(datetime.now().minute == x + self.offset for x in range(0, 60, self.post_every)): return
        while True:
            while len(self.queue) == 0:
                try:
                    conn = sqlite3.connect(self.db_file)
                    cur = conn.cursor()
                    cur.execute(self.select_sql, (self.queue_length, ))
                    self.queue = cur.fetchall()
                    if len(self.queue) == 0:
                        self.log(fname, "No valid entries. Resetting db.")
                        cur.execute(self.remove_posted_flag_sql)
                        conn.commit()
                    else:
                        cur.executemany(self.flag_posted_sql, [(str(item[0]), ) for item in self.queue])
                        conn.commit()
                    conn.close()
                    if self.verbose_logging: self.log(fname, "Refilled queue with {} entries.".format(len(self.queue)))
                except: continue
            id, url, src, tags = self.queue.pop()
            if self.check_tags(tags, self.blacklist_tags):
                intersect = list(set(tags.split(" ")).intersection(self.blacklist_tags.split(",")))
                andtags = [i for i in self.blacklist_tags.split(",") if " " in i]
                for tag in andtags:
                    found = [i for i in tags.split(" ") if i in tag.split(" ")]
                    if len(found) == len(tag.split(" ")):
                        intersect.append(found)
                self.blacklist(id, "Found blacklist tags {}".format(str(intersect)))
                continue
            if not self.check_tags(tags, self.mandatory_tags) and len(self.mandatory_tags) > 0:
                self.blacklist(id, "Mandatory tags not found")
                continue
            if self.check_tags(tags, self.skip_tags):
                if random.randint(1, 100) <= self.skip_chance:
                    intersect = list(set(tags.split(" ")).intersection(self.skip_tags.split(",")))
                    andtags = [i for i in self.skip_tags.split(",") if " " in i]
                    for tag in andtags:
                        found = [i for i in tags.split(" ") if i in tag.split(" ")]
                        if len(found) == len(tag.split(" ")):
                            intersect.append(found)
                    if self.verbose_logging: self.log(fname, "Skipped {}. Reason: Found skip tags {}".format(id, str(intersect)))
                    continue
            try:
                saved_file_path = urllib.request.urlretrieve(url)[0]
                with open(saved_file_path, 'rb') as file: mediadict = self.mastodon.media_post(file.read(), self.mime.from_file(saved_file_path))
                status_text = '{0}/post/show/{1}\r\nsource: {2}'.format(self.booru_url, id, src)
                self.mastodon.status_post(status_text, in_reply_to_id = None, media_ids = (mediadict['id'], ), sensitive = True, visibility = "unlisted", spoiler_text = None)
            except Exception as e:
                if e.args[1] == 422: self.blacklist(id, "{0}. {1}".format(e.args[2], e.args[3]))
                else: self.log(fname, "Post {}/post/show/{} threw exception: {}".format(self.booru_url, id, e))
                continue
            else:
                if self.verbose_logging: self.log(fname, "Posted.")
                break
            finally: 
                if os.path.isfile(saved_file_path): os.remove(saved_file_path)

    @ananas.reply
    def handle_reply(self, status, user):
        fname = "handle_reply"
        try:
            if user['acct'] == self.admin:
                if 'delete this!' in status['content']:
                    status_in_question = self.mastodon.status(status['in_reply_to_id'])
                    self.mastodon.status_delete(status['in_reply_to_id'])
                    text = re.sub('<[^<]+?>', '', status_in_question['content'])
                    text = self.h.unescape(text)
                    id = re.search("post\/show\/([0-9]+)source", text)
                    id = id.groups()[0]
                    self.blacklist(id, "Admin request")
                elif 'announce! ' in status['content']:
                    text = re.sub('<[^<]+?>', '', status['content'])
                    text = self.h.unescape(text)
                    self.mastodon.status_post(text.split('announce! ')[-1], in_reply_to_id = None, media_ids = None, sensitive = False, visibility = "unlisted", spoiler_text = None)
        except Exception as e:
            self.log(fname, e)
            return

class admin_cleaner(ananas.PineappleBot):
    @ananas.schedule(minute = "*/10")
    def reload_config(self):
        self.config.load(self.config._name, silent = not self.verbose_logging)
        self.load_global_config()
        if "log_file" in self.config and len(self.config.log_file) > 0:
            self.log_file = open(self.config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in self.config and (self.config.verbose.lower() in ['no', 'yes', 'very']):
            if self.config.verbose.lower() == "yes": self.verbose_logging = True
            elif self.config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
            elif self.config.verbose.lower() == "no":
                self.verbose_logging = False
                self.verbose = False
                
    def log(self, id, msg):
        if id is None:
            id = self.__class__.__name__
        print("[{0:%Y-%m-%d %H:%M:%S}] {1}.{2}: {3}".format(datetime.now(), self.config._name, id, str(msg)), file = self.log_file, flush = True)
        
    def init(self):
        self.admin = "pup_hime@slime.global"
        self.verbose_logging = False #the bot's verbosity
        self.verbose = False #ananas' own verbosity  
        self.log_file = sys.stderr
        self.log_to_stderr = True
        
    def load_global_config(self):
        global_config = ananas.PineappleBot.Config(self.config._bot, self.config._filename)
        global_config.load("global", silent = not self.verbose_logging)
        if "log_file" in global_config and len(global_config.log_file) > 0:
            self.log_file = open(global_config.log_file, "a")
            self.log_to_stderr = False
        if "verbose" in global_config and (global_config.verbose.lower() in ['no', 'yes', 'very']):
            if global_config.verbose.lower() == "yes": 
                self.verbose_logging = True
                self.verbose = False
            elif global_config.verbose.lower() == "very": 
                self.verbose_logging = True
                self.verbose = True
                
    def start(self):
        fname = "start"
        self.reload_config()
        self.me = self.mastodon.account_verify_credentials()
        self.last_checked_post = self.mastodon.timeline_home()[0]
        self.log(fname, "Bot started.")

    @ananas.schedule(minute = 0)
    def check_posts(self):
        fname = "check_posts"
        try:
            posts = self.mastodon.account_statuses(self.me['id'], since_id = self.last_checked_post)
            if len(posts) > 0:
                for post in posts:
                    if "delete this!" in post['content']:
                        self.mastodon.status_delete(post['id'])
                        if self.verbose_logging: self.log(fname, "Found deleter post id {}.".format(post['id']))
                    if "announce! " in post['content']:
                        self.mastodon.status_delete(post['id'])
                        if self.verbose_logging: self.log(fname, "Found announcer post id {}.".format(post['id']))
                self.last_checked_post = posts[0]
        except Exception as e:
            self.log(fname, e)
            return
