import dataclasses
import pickle
import signal
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from time import sleep
from typing import Any

import requests
from pywikibot import Site

from utils import MirahezeWiki, fetch_all_mh_wikis, cache_dir, headers


@dataclass
class WikiAdmin:
    username: str
    last_edit: datetime
    user_groups: list[str]


class WikiStatus(Enum):
    PENDING = 0
    DONE = 1
    FAILED = 2


@dataclass
class AdminStats:
    wiki: MirahezeWiki
    admins: list[WikiAdmin] = dataclasses.field(default_factory=list)
    status: WikiStatus = WikiStatus.PENDING


def get_last_edit_date(wiki: MirahezeWiki, users: list[WikiAdmin]) -> None:
    for u in users:
        response = requests.get(url=wiki.api_url, params={
            'action': 'query',
            'list': 'usercontribs',
            'ucuser': u.username,
            'uclimit': 1,
            'format': 'json',
        }, headers=headers).json()
        edits = response['query']['usercontribs']
        if len(edits) == 0:
            continue
        edit = edits[0]
        u.last_edit = datetime.fromisoformat(edit['timestamp'])


def get_wiki_admin_stats(stats: AdminStats) -> None:
    wiki = stats.wiki
    try:
        # FIXME: what if the wiki renamed privileged user groups?
        response = requests.get(wiki.api_url, params={
            'action': 'query',
            'list': 'allusers',
            'augroup': "bureaucrat|sysop",
            'auprop': 'groups',
            'aulimit': 50,
            'format': 'json',
        }, headers=headers).json()
        admins: list[WikiAdmin] = []
        for admin_info in response['query']['allusers']:
            admin_info: dict[str, Any]
            username = admin_info['name']
            groups = admin_info['groups']
            admins.append(WikiAdmin(username, datetime.fromtimestamp(0), groups))
        get_last_edit_date(wiki, admins)
        stats.admins = admins
        stats.status = WikiStatus.DONE
    except Exception as e:
        print(f"Failed for {wiki.dbname}: {e}")
        stats.status = WikiStatus.FAILED


def load_admin_stats(p: Path) -> list[AdminStats]:
    if p.exists():
        return pickle.load(open(p, "rb"))
    wikis = fetch_all_mh_wikis()
    return [AdminStats(wiki) for wiki in wikis]


def save_admin_stats(p: Path, stats: list[AdminStats]) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pickle.dump(stats, open(p, "wb"))
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def print_problematic_wikis(admin_stats):
    now = datetime.now()
    for stats in admin_stats:
        if stats.status != WikiStatus.DONE:
            continue
        last_edits = [admin.last_edit.replace(tzinfo=None) for admin in stats.admins]
        if len(last_edits) == 0:
            # print(f"{stats.wiki} does not appear to have an admin")
            continue
        last_edit = max(last_edits)
        delta = now - last_edit
        if delta > timedelta(days=10000):
            # print(f"{stats.wiki}'s admins have not made a single edit. Is this a new wiki?")
            continue
        if delta > timedelta(days=1000):
            wiki = stats.wiki
            row = (
                "{{/entry"
                f"|name={wiki.sitename}"
                f"|link={wiki.url}"
                f"|text={delta.days} days"
                "|status={{status}} "
                "}}"
            ).replace("|", " | ")
            print(row)


def fetch_admin_stats(admin_stats: list[AdminStats], cache_file: Path) -> None:
    for index, wiki in enumerate(admin_stats, 1):
        if wiki.status != WikiStatus.PENDING:
            continue
        get_wiki_admin_stats(wiki)
        sleep(1)
        if index % 10 == 0:
            print(f"{index}/{len(admin_stats)}")
            save_admin_stats(cache_file, admin_stats)


def main():
    cache_file = cache_dir / "no_admin_edit.pickle"
    admin_stats = load_admin_stats(cache_file)
    fetch_admin_stats(admin_stats, cache_file)
    print_problematic_wikis(admin_stats)


if __name__ == "__main__":
    main()
