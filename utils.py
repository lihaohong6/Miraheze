import pickle
from dataclasses import dataclass
from pathlib import Path

from pywikibot import Site
from pywikibot.data.api import QueryGenerator

headers = {'User-Agent': 'MediaWiki bot by User:PetraMagna', }

cache_dir = Path('cache')

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


def fetch_all_mh_wikis(state: str = "active|public") -> list[MirahezeWiki]:
    wiki_cache_dir = cache_dir / "wiki_list"
    wiki_cache_dir.mkdir(parents=True, exist_ok=True)
    wiki_cache_file = wiki_cache_dir / f"{state.replace('|', '-')}-wiki-list.pickle"
    if not wiki_cache_file.exists():
        # FIXME: how to use the paginated API?
        gen = QueryGenerator(site=meta(), parameters={
            "list": "wikidiscover",
            "wdstate": state,
            "format": "json",
        })
        results: list[MirahezeWiki] = []
        for wiki in gen:
            results.append(MirahezeWiki(dbname=wiki["dbname"], sitename=wiki["sitename"], url=wiki["url"]))
        pickle.dump(results, open(wiki_cache_file, "wb"))
    else:
        results = pickle.load(open(wiki_cache_file, "rb"))
    return results
