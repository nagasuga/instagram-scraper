Instagram Scraper
=================

## Usage

### Getting user info
```
from instagram_scraper import Scraper
username = 'davepimentel'
scraper = Scraper(username)
user = scraper.user()
print user.__dict__
```

### Iterating through all the medias (posts) by a user

```
from instagram_scraper import Scraper

username = 'davepimentel'
scraper = Scraper(username)
for item in scraper.medias():
    print item.__dict__
```

### Detail Calls

By instantiating the Scraper class with optional `client_id` and `client_secret` obtained from Instagram API, the scraper will perform a deeper call to obtain more information about the user (follows, followed by) and media (likes, comments) using the official Instagram API instead of what was found during scraping which is limited.

```
from instagram_scraper import Scraper
username = 'davepimentel'
client_id = '<client_id from Instagram>'
client_secret = '<client_secret from Instagram>'
scraper = Scraper(username, client_id=client_id, client_secret=client_secret)
user = scraper.user()
print user.__dict__
```
