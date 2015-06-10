import httplib
import json
import logging
import re
import urllib
import urllib2

from bs4 import BeautifulSoup

from instagram.client import InstagramAPI
from instagram.models import User, Media



class PageScraper(object):
    def __init__(self):
        self.raw_html = None

    def call(self, username):
        domain = 'instagram.com'
        conn = httplib.HTTPSConnection(domain)
        conn.request('GET', '/' + username)
        resp = conn.getresponse()

        msg = 'PageScraper: ' + 'https://instagram.com/' + username
        logging.info(msg)

        self.raw_html = resp.read()
        return self

    @staticmethod
    def _extract_tags(text):
        return re.compile('#([^\s-]*)').findall(text)

    def _extract_user(self, raw_html):
        pattern = re.compile('window._sharedData = (.*?);[\s]*$')

        soup = BeautifulSoup(raw_html, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if(pattern.match(str(script.string))):
                data = pattern.match(script.string)
                shared_data = json.loads(data.groups()[0])
                return shared_data['entry_data']['UserProfile'][0]['user']
        return None

    def _extract_medias(self, raw_html):
        pattern = re.compile('window._sharedData = (.*?);[\s]*$')

        soup = BeautifulSoup(raw_html, 'html.parser')
        scripts = soup.find_all('script')
        for script in scripts:
            if(pattern.match(str(script.string))):
                data = pattern.match(script.string)
                shared_data = json.loads(data.groups()[0])
                return shared_data['entry_data']['UserProfile'][0]['userMedia']
        return None

    @property
    def user(self):
        raw_user = self._extract_user(self.raw_html)
        return User(id=raw_user['id'],
                    username=raw_user['username'],
                    full_name=raw_user['full_name'],
                    image=raw_user['profile_picture'])

    @property
    def medias(self):
        raw_medias = self._extract_medias(self.raw_html)
        for idx, raw_media in enumerate(raw_medias):
            user = User(**raw_media['user'])
            location = None
            if raw_media['location']:
                location = (raw_media['location']['latitude'],
                            raw_media['location']['longitude'])
            raw_caption = raw_media.get('caption') or {}
            caption = raw_caption.get('text', '')
            tags = self._extract_tags(caption)
            video = None
            if 'videos' in raw_media:
                video = raw_media['videos']['standard_resolution']['url']
            media = Media(id=raw_media['id'],
                          type=raw_media['type'],
                          tags=tags,
                          comments=raw_media['comments'],
                          likes=raw_media['likes'],
                          caption=caption,
                          link=raw_media['link'],
                          user=user,
                          create_time=raw_media['created_time'],
                          image=raw_media['images']['standard_resolution']['url'],
                          location=location,
                          video=video)
            raw_medias[idx] = media
        return raw_medias


class MediaScraper(object):
    def __init__(self, username):
        self.username = username
        self.raw = {}
        self.idx = 0

    def __iter__(self):
        self.raw = self._call()
        return self

    def next(self): # Python 3: def __next__(self)
        if self.idx >= len(self.raw['items']):
            if not self.raw['more_available']:
                raise StopIteration
            last_media = self.raw['items'][self.idx - 1]
            self.raw = self._call(params={'max_id': last_media['id']})
            self.idx = 0

        self.idx += 1

        raw_item = self.raw['items'][self.idx - 1]
        raw_caption = raw_item.get('caption') or {}
        raw_item['tags'] = self._extract_tags(raw_caption.get('text', ''))
        return Media.object_from_dictionary(raw_item)

    def _call(self, params=None):
        url = 'https://instagram.com/{}/media'.format(self.username)
        if params:
            url += '?' + urllib.urlencode(params)

        msg = 'MediaScraper: ' + url
        logging.info(msg)

        resp = urllib2.urlopen(url)
        return json.loads(resp.read())

    @staticmethod
    def _extract_tags(text):
        return re.compile('#([^\s-]*)').findall(text)


class Scraper(object):
    def __init__(self, username, client_id=None, client_secret=None):
        self.username = username
        self.api = None
        if client_id and client_secret:
            self.api= InstagramAPI(client_id=client_id,
                                   client_secret=client_secret)

    def user(self):
        for item in MediaScraper(self.username):
            user = item.user
            break

        if self.api:
            # Follows
            follows, next_url = self.api.user_follows(user.id)
            while next_url:
                more_follows, next_url = self.api.user_follows(
                    with_next_url=next_url)
                follows += more_follows
            user.follows = follows

            # Followed_by
            followed_by, next_url = self.api.user_followed_by(user.id)
            while next_url:
                more_followed_by, next_url = self.api.user_followed_by(
                    with_next_url=next_url)
                followed_by += more_followed_by
            user.followed_by = followed_by

        return user

    def medias(self):
        for item in MediaScraper(self.username):
            if self.api:
                item.comments = self.api.media_comments(item.id)
                item.likes = self.api.media_likes(item.id)
            yield item
