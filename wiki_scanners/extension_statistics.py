from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import TypeVar, Any

import requests

from utils.general_utils import MirahezeWiki, headers, meta, save_json_page
from utils.wiki_scanner import scan_wikis


@dataclass
class WikiExtensionStatistics:
    settings: dict[str, Any]
    extensions: list[str]


def fetch_wiki_extension_statistics(wikis: list[MirahezeWiki]) -> dict[str, WikiExtensionStatistics]:
    db_names = "|".join(w.db_name for w in wikis)
    response = requests.get("https://meta.miraheze.org/w/api.php", params={
        'action': 'query',
        'list': 'wikiconfig',
        'wcfwikis': db_names,
        'wcfprop': 'settings|extensions',
        'format': 'json',
        'formatversion': 2,
    }, headers=headers)
    response = response.json()['query']['wikiconfig']
    result: dict[str, WikiExtensionStatistics] = {}
    for row in response:
        extensions = row['extensions']
        settings = row['settings']
        if len(settings) == 0:
            settings = {}
        result[row['name']] = WikiExtensionStatistics(
            extensions=extensions,
            settings=settings,
        )
    return result


K = TypeVar('K')
V = TypeVar('V')


def sort_dict(d: dict[K, V]) -> None:
    result: dict[K, V] = {}
    for k in sorted(d, key=d.get, reverse=True):
        result[k] = d[k]
    d.clear()
    d.update(result)


def get_wiki_extension_statistics(cache_expiry: timedelta | None = None) -> dict[str, WikiExtensionStatistics]:
    res = scan_wikis(fetch_wiki_extension_statistics,
                     "wiki_extensions",
                     batch_size=50,
                     cache_expiry=cache_expiry)
    for k, v in res.items():
        if isinstance(v, dict):
            v.pop('py/object', '')
            res[k] = WikiExtensionStatistics(**v)
    return res


def analyze_extension_statistics():
    result = get_wiki_extension_statistics()
    extension_counter: dict[str, int] = defaultdict(int)
    default_skin_counter: dict[str, int] = defaultdict(int)
    skip_skin_counter: dict[str, int] = defaultdict(int)
    for db_name, stats in result.items():
        for extension in stats.extensions:
            extension_counter[extension] += 1
        default_skin_counter[stats.settings['default_skin']] += 1
        for skin in stats.settings['skip_skins']:
            skip_skin_counter[skin] += 1
    sort_dict(extension_counter)
    sort_dict(default_skin_counter)
    sort_dict(skip_skin_counter)
    return extension_counter, default_skin_counter, skip_skin_counter


def get_extension_popularity_statistics() -> dict[str, int]:
    return analyze_extension_statistics()[0]


def main():
    get_wiki_extension_statistics(timedelta(days=1))


if __name__ == "__main__":
    main()
