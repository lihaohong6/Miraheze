import logging
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from pywikibot import Site
from pywikibot.data.api import ListGenerator, Request
from requests import Session

headers = {'User-Agent': 'MediaWiki bot by User:PetraMagna', }

cache_dir = Path('cache')
cache_dir.mkdir(parents=True, exist_ok=True)

def meta():
    return Site(code="meta")


@dataclass
class MirahezeWiki:
    dbname: str
    sitename: str
    url: str

    @property
    def api_url(self):
        return self.url + "/w/api.php"


    def __str__(self):
        return f"{self.sitename} ({self.url})"


def fetch_all_mh_wikis(state: str = "active|public") -> list[MirahezeWiki]:
    wiki_cache_dir = cache_dir / "wiki_list"
    wiki_cache_dir.mkdir(parents=True, exist_ok=True)
    wiki_cache_file = wiki_cache_dir / f"{state.replace('|', '-')}-wiki-list.pickle"
    if not wiki_cache_file.exists():
        results: list[MirahezeWiki] = []

        # FIXME: how to use the paginated API?
        offset = 0
        while True:
            req = Request(meta(), parameters={
                "action": "query",
                "list": "wikidiscover",
                "wdprop": "sitename|url",
                "wdstate": state,
                "format": "json",
                "wdoffset": offset
            })
            response = req.submit()
            wikis: dict[str, dict] = response['query']['wikidiscover']['wikis']
            for db_name, wiki_stats in wikis.items():
                results.append(MirahezeWiki(dbname=db_name, sitename=wiki_stats["sitename"], url=wiki_stats["url"]))
            if len(wikis) < 500:
                break
            offset += len(wikis)

        pickle.dump(results, open(wiki_cache_file, "wb"))
    else:
        results = pickle.load(open(wiki_cache_file, "rb"))
    return results


def get_num_of_recent_changes(wiki: MirahezeWiki) -> int:
    result = requests.get(wiki.api_url, {
        'action': 'query',
        'list': 'recentchanges',
        'rcnamespace': '*',
        'rcprop': 'user',
        'rclimit': 100,
        'format': 'json'
    }, headers=headers).json()['query']['recentchanges']
    return len(result)


def get_logger(name: str = "logger") -> logging.Logger:
    logging.basicConfig(level=logging.INFO,
                        filename=f"{name}_log.txt",
                        filemode="a",
                        encoding="utf-8")
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger


@dataclass
class SessionInfo:
    url: str
    session: Session


def get_csrf_token(session: Session, url: str) -> str:
    params = {
        "action": "query",
        "meta": "tokens",
        "format": "json"
    }
    r = session.get(url, params=params, headers=headers)
    return r.json()["query"]["tokens"]["csrftoken"]


def login(url: str, username: str, password: str) -> SessionInfo:
    # 1. Start a session
    session = requests.Session()

    # 2. Get login token
    params = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    }
    r = session.get(url, params=params, headers=headers)
    login_token = r.json()["query"]["tokens"]["logintoken"]

    # 3. Log in
    login_params = {
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "lgtoken": login_token,
        "format": "json"
    }
    r = session.post(url, data=login_params, headers=headers)
    return SessionInfo(url, session)
