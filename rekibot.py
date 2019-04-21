from textstat.textstat import textstat
import ananas
import random

import urllib.request, urllib.parse, urllib.error
from pybooru import Danbooru
import magic
import time
from random import randint
import re

import requests
from twitter import *
import threading
from html.parser import HTMLParser
import pprint

class reminder(ananas.PineappleBot):
    def start(self):
        self.me = self.mastodon.account_verify_credentials()
        self.last_checked_toot = self.mastodon.timeline_home()[0]
        self.h = HTMLParser()
        
    @ananas.schedule(second=0)
    def check_follows(self):
        self.me = self.mastodon.account_verify_credentials()
        my_id = self.me['id']
        followers_count = self.me['followers_count']
        followers = self.mastodon.account_followers(my_id)
        while len(followers)<followers_count:
            followers = followers + self.mastodon.account_followers(my_id,max_id=followers[-1]._pagination_next['max_id'])
        following_count = self.me['following_count']
        following = self.mastodon.account_following(my_id)
        while len(following)<following_count:
            following = following + self.mastodon.account_following(my_id,max_id=following[-1]._pagination_next['max_id'])
            
        followingids=[]
        for followed in following:
            followingids=followingids+[followed['id'],]
            
        followerids=[]
        for follower in followers:
            followerids=followerids+[follower['id'],]
        
        for follower in followerids:
            if follower not in followingids:
                time.sleep(1)
                if not self.mastodon.account_relationships(follower)[0]['requested']:
                    if "moved" in self.mastodon.account(follower):
                        self.mastodon.account_block(follower)
                        self.mastodon.account_unblock(follower)
                    else:
                        self.mastodon.account_follow(follower,reblogs=False)
                            
        for followed in followingids:
            if followed not in followerids:
                time.sleep(1)
                if not self.mastodon.account_relationships(followed)[0]['requested']:
                    self.mastodon.account_unfollow(followed) 
                
    @ananas.schedule(second=0)
    @ananas.schedule(second=30)
    def check_toots(self):
        toots = self.mastodon.timeline_home(since_id=self.last_checked_toot['id'])
        if len(toots)>0:
            for toot in toots:
                if len(toot['media_attachments'])>0 and toot['reblog'] is None and toot['in_reply_to_id'] is None:
                    marked = False
                    for attachment in toot['media_attachments']:
                        if attachment['description'] is None:
                            marked = True
                    if marked:
                        self.mastodon.status_post('@'+toot['account']['acct']+' hey, just so you know, this status includes an attachment with missing accessibility (alt) text.', in_reply_to_id=(toot['id']),visibility='direct')
            self.last_checked_toot = toots[0]
            
    @ananas.reply
    def delete_toot(self, status, user):
        if user['acct'] == 'pup_hime@bark.house':
            if '!deletethis' in status['content']:
                self.mastodon.status_delete(status['in_reply_to_id'])
            elif '!announce' in status['content']:
                text = re.sub('<[^<]+?>', '', status['content'])
                text = self.h.unescape(text)
                self.mastodon.status_post(text.split('!announce ')[-1], in_reply_to_id=None, media_ids=None, sensitive=False, visibility="unlisted", spoiler_text=None)
        
class x_an_y(ananas.PineappleBot):
    sighs = ["oh", "ugh", "sigh"]
    articles = ["a","the"]
    gos = ["go","just go"]
    maxsyllables = 1
    def start(self):
        self.h = HTMLParser()
        with open('/home/pi/rekibot/words/nouns.txt', 'r') as nouns:
            self.nouns = nouns.readlines()
        with open('/home/pi/rekibot/words/verbs.txt', 'r') as verbs:
            self.verbs = verbs.readlines()
    
    @ananas.hourly(minute=30)
    @ananas.hourly(minute=0)
    def post(self):
        sigh = random.choice(self.sighs)
        verb = random.choice(self.verbs)
        noun = random.choice(self.nouns)
        while textstat.syllable_count(verb)>self.maxsyllables:
            verb = random.choice(self.verbs)
        while textstat.syllable_count(noun)>self.maxsyllables:
            noun = random.choice(self.nouns)
        go = random.choice(self.gos)
        article = random.choice(self.articles)
        verb=verb.strip(' \t\n\r')
        noun=noun.strip(' \t\n\r')
        if article == "a":
            if noun[0] in ["a","e","i","o","u"]:
                article = "an"
        self.mastodon.status_post("{}, {} {} {} {}".format(sigh, go, verb, article, noun), visibility = "unlisted")
    
    @ananas.reply
    def delete_toot(self, status, user):
        if user['acct'] == 'pup_hime@bark.house':
            if '!deletethis' in status['content']:
                self.mastodon.status_delete(status['in_reply_to_id'])
            elif '!announce' in status['content']:
                text = re.sub('<[^<]+?>', '', status['content'])
                text = self.h.unescape(text)
                self.mastodon.status_post(text.split('!announce ')[-1], in_reply_to_id=None, media_ids=None, sensitive=False, visibility="unlisted", spoiler_text=None)
        
class danboorubot(ananas.PineappleBot):
    def start(self):
        self.mime = magic.Magic(mime=True)
        self.proxy = urllib.request.ProxyHandler({})
        self.opener = urllib.request.build_opener(self.proxy)
        self.opener.addheaders = [('User-Agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.1 Safari/603.1.30')]
        urllib.request.install_opener(self.opener)
        self.client = Danbooru('danbooru')
        self.h = HTMLParser()
        self.excluded_tags = ['female_pervert','groping','breast_grab','pervert','sexual_harassment','sexually_suggestive','underwear_only','breast_press','underwear','topless','dangerous_beast','bottomless','no_panties','spoilers','revealing_clothes','pet_play','eargasm','daijoubu?_oppai_momu?','guro','swimsuit','bdsm','bondage','foot_worship','comic','cameltoe','bikini_top','osomatsu-san','osomatsu-kun','naked_sheet','foot_licking','sweat','nude','nude_cover','bunnysuit','loli','randoseru','age_difference','younger','child','height_difference','futaba_anzu','incest','you_gonna_get_raped','sisters','kindergarten_uniform','male_focus']
    
    @ananas.hourly(minute=30)
    @ananas.hourly(minute=0)
    def post(self):
        while True:
            download_list=[]
            randompage = randint(1, 200)
            posts = None
            while posts==None:
                try:
                    posts = self.client.post_list(tags='rating:s '+self.config.tag, page=str(randompage), limit=200)
                except Exception as e:
                    posts = None
                    time.sleep(30)
            for post in posts:
                if 'drawfag' not in post['source'] and '.png' not in post['source'] and '.jpg' not in post['source'] and post['source'] != '' and post['is_deleted']==False and not any(tag in post['tag_string'] for tag in self.excluded_tags):
                    if 'file_url' in post:
                        download_list.append((post['file_url'],post['source'],post['id']))
                    elif 'large_file_url' in post:
                        download_list.append(('http://danbooru.donmai.us' + post['large_file_url'],post['source'],post['id']))
            if len(download_list) > 0:
                break
            
        while True:
            try:
                url,src,id = random.choice(download_list)
                url = urllib.request.urlretrieve(url)[0]
                with open(url,'rb') as file:
                    mediadict = self.mastodon.media_post(file.read(),self.mime.from_file(url))
                status_text = 'http://danbooru.donmai.us/posts/{0}\r\nsource: {1}'.format(id,src)
                self.mastodon.status_post(status_text, in_reply_to_id=None, media_ids=(mediadict['id'],), sensitive=True, visibility="unlisted", spoiler_text=None)
            except Exception as e:
                continue
            else:
                break
            
    @ananas.reply
    def delete_toot(self, status, user):
        if user['acct'] == 'pup_hime@bark.house':
            if '!deletethis' in status['content']:
                self.mastodon.status_delete(status['in_reply_to_id'])
            elif '!announce' in status['content']:
                text = re.sub('<[^<]+?>', '', status['content'])
                text = self.h.unescape(text)
                self.mastodon.status_post(text.split('!announce ')[-1], in_reply_to_id=None, media_ids=None, sensitive=False, visibility="unlisted", spoiler_text=None)

