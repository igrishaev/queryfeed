
from flask import Flask
from flask import request
from flask import redirect
from flask import url_for
from flask import abort
from flask import make_response
from flask import render_template

import urllib
from time import sleep
from functools import wraps


try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except ImportError:
            raise ImportError("JSON library not found.")


import google.appengine.ext.db as db


class CONFIG:

    # Update this:
    BASE_URL =  "http://example.com"               # Base URL of service.
    WEBMASTER = "webmaster@example.com"            # Email in feed header.
    PLUS_KEY = "_________________________________" # Google plus API key.
    #

    DEBUG = False
    TWITTER_TTL = 5
    FACEBOOK_TTL = 10
    GOOGLE_TTL = 10



def fetch(url):
    for i in range(4):
        try:
            return urllib.urlopen(url).read()
        except Exception, e:
            sleep(1)
    raise e


class Feed(db.Model):
    q = db.StringProperty()
    source = db.StringProperty()
    times = db.IntegerProperty(default=0)
    date_create = db.DateTimeProperty(auto_now_add=True)
    date_update = db.DateTimeProperty(auto_now=True)


TWITTER_SEARCH_URL  = "http://search.twitter.com/search.json"
FACEBOOK_SEARCH_URL = "https://graph.facebook.com/search"
GOOGLE_SEARCH_URl   = "https://www.googleapis.com/plus/v1/activities"


ENCODING = "ISO-8859-1"
LIMITS = 15

app = Flask(__name__)
app.config.from_object(CONFIG)


@app.route("/")
def frontpage():
    recents = Feed.all().order("-date_create").run(limit=LIMITS)
    populars = Feed.all().order("-times").run(limit=LIMITS)
    return render_template("frontpage.html", populars=populars, recents=recents)


def update_counter(source, q):
    key_name = u"%s_%s" % (source, q)
    f = Feed.get_by_key_name(key_name)
    if not f:
        f = Feed(key_name=key_name, source=source, q=q)
    f.times += 1
    try:
        f.put() # Quotas may be riched.
    except:
        pass


def as_rss(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        body = f(*args, **kwargs)
        response = make_response(body)
        response.headers["Content-Type"] = "application/rss+xml; charset=utf-8"
        return response
    return decorated_function


@app.route("/twitter")
@as_rss
def twitter():
    q = request.args.get("q")
    if not q:
        abort(400)

    params=dict(q=q.encode("utf8"), include_entities=1, rpp=100, result_type="recent")

    qs = urllib.urlencode(params)
    url = TWITTER_SEARCH_URL + "?" + qs
    out = fetch(url)
    feed = json.loads(out)

    if feed.get("error"):
        abort(500)

    s = render_template("twitter.xml", feed=feed, q=q)

    update_counter(u"twitter", q)

    return s


@app.route("/facebook")
@as_rss
def facebook():
    q = request.args.get("q")
    if not q:
        abort(400)

    params=dict(q=q.encode("utf8"))

    qs = urllib.urlencode(params)
    url = FACEBOOK_SEARCH_URL + "?" + qs

    out = fetch(url)

    feed = json.loads(out)

    if feed.get("error"):
        abort(500)

    s = render_template("facebook.xml", feed=feed, q=q)

    update_counter(u"facebook", q)

    return s


@app.route("/plus")
@as_rss
def plus():
    q = request.args.get("q")
    if not q:
        abort(400)

    params = dict(query=q.encode("utf8"), maxResults=20, orderBy="recent", key=CONFIG.PLUS_KEY)
    qs = urllib.urlencode(params)
    url = GOOGLE_SEARCH_URl + "?" + qs

    out = fetch(url)
    feed = json.loads(out)

    if feed.get("error"):
        abort(500)

    s = render_template("plus.xml", feed=feed, q=q)

    update_counter(u"plus", q)

    return s

