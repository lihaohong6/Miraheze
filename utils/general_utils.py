import dataclasses
import enum
import json
import logging
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import requests
from pywikibot import Site, Page
from pywikibot.data.api import Request
from requests import Session

user_agent = 'MediaWiki bot by User:PetraMagna'
headers = {'User-Agent': user_agent, }
anonymous_headers = {'User-Agent': 'MediaWiki bot', }

cache_dir = Path('cache')
cache_dir.mkdir(parents=True, exist_ok=True)


def meta():
    return Site(code="meta")


@dataclass
class MirahezeWiki:
    db_name: str
    site_name: str
    url: str
    category: str
    language: str
    creation_date: str
    # one of active, inactive, closed, deleted
    state: str

    @property
    def api_url(self):
        return self.url + "/w/api.php"

    def to_sql_values(self) -> tuple[str, str, str, str, str, str, str]:
        return self.db_name, self.site_name, self.url, self.category, self.language, self.creation_date, self.state

    @classmethod
    def from_sql_row(cls, row: tuple[str, str, str, str, str, str, str]) -> 'MirahezeWiki':
        return cls(*row)

    def __str__(self):
        return f"{self.site_name} ({self.url})"


@cache
def fetch_all_mh_wikis_uncached(state: str = "public") -> list[MirahezeWiki]:
    results: list[MirahezeWiki] = []
    offset = 0
    while True:
        req = Request(meta(), parameters={
            "action": "query",
            "list": "wikidiscover",
            "wdprop": "sitename|url|languagecode|category|creationdate",
            "wdstate": state,
            "format": "json",
            "wdoffset": offset
        })
        response = req.submit()
        wikis: dict[str, dict] = response['query']['wikidiscover']['wikis']
        for db_name, wiki_stats in wikis.items():
            states = []
            for possible_state in ["active", "inactive", "closed", "deleted"]:
                if wiki_stats.get(possible_state, None) is not None:
                    states.append(possible_state)
            results.append(MirahezeWiki(
                db_name=db_name,
                site_name=wiki_stats["sitename"],
                url=wiki_stats["url"],
                category=wiki_stats["category"],
                language=wiki_stats["languagecode"],
                creation_date=wiki_stats["creationdate"],
                state="|".join(states))
            )
        if len(wikis) < 500:
            break
        offset += len(wikis)
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
    log_root = Path("logs")
    log_root.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler_debug = logging.FileHandler(log_root / f"{name}_log_debug.txt")
    file_handler_debug.setLevel(logging.DEBUG)
    file_handler_debug.setFormatter(formatter)

    file_handler_warning = logging.FileHandler(log_root / f"{name}_log_warning.txt")
    file_handler_warning.setLevel(logging.WARNING)
    file_handler_warning.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO,
                        filename=log_root / f"{name}_log.txt",
                        filemode="a",
                        encoding="utf-8")
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler_debug)
    logger.addHandler(file_handler_warning)
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


def site() -> Site:
    return Site()


def dump_json(o):
    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            if isinstance(o, enum.Enum):
                return o.value
            return super().default(o)

    return json.dumps(o, indent=4, cls=EnhancedJSONEncoder)


def save_json_page(page: Page | str, obj, summary: str = "update json page"):
    if isinstance(page, str):
        page = Page(site(), page)

    if page.text != "":
        original_json = json.loads(page.text)
        original = dump_json(original_json)
    else:
        original = ""
    modified = dump_json(obj)
    if original != modified:
        page.text = modified
        page.save(summary=summary)


def throttle(seconds: float):
    import time
    def get_current_time_milli():
        return round(time.time() * 1000)

    prev: float | None = getattr(throttle, "prev", None)
    if prev is not None:
        wakeup_time = prev + seconds * 1000
        sleep_seconds = (wakeup_time - get_current_time_milli()) / 1000
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    setattr(throttle, "prev", get_current_time_milli())