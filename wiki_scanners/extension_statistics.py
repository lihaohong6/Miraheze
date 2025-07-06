from collections import defaultdict
from dataclasses import dataclass
from typing import TypeVar

import requests

from utils.general_utils import MirahezeWiki, headers, meta, save_json_page
from utils.wiki_scanner import scan_wikis


@dataclass
class WikiExtensionStatistics:
    default_skin: str
    skip_skins: list[str]
    extensions: list[str]


def fetch_wiki_extension_statistics(wikis: list[MirahezeWiki]) -> dict[str, WikiExtensionStatistics]:
    db_names = "|".join(w.db_name for w in wikis)
    response = requests.get("https://meta.miraheze.org/w/api.php", params={
        'action': 'query',
        'list': 'wikiconfig',
        'wcfwikis': db_names,
        'wcfprop': 'settings|extensions',
        'format': 'json',
    }, headers=headers)
    response = response.json()['query']['wikiconfig']
    result: dict[str, WikiExtensionStatistics] = {}
    for row in response:
        extensions = row['extensions']
        settings = row['settings']
        if len(settings) == 0:
            settings = {}
        default_skin = settings.get('wgDefaultSkin', '')
        skip_skins = settings.get('wgSkipSkins', [])
        result[row['name']] = WikiExtensionStatistics(
            extensions=extensions,
            default_skin=default_skin,
            skip_skins=skip_skins
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


def get_wiki_extension_statistics(read_only: bool = False) -> dict[str, WikiExtensionStatistics]:
    return scan_wikis(fetch_wiki_extension_statistics,
                      "wiki_extensions",
                      reset=False,
                      batch_size=50,
                      read_only=read_only)


def main():
    result = get_wiki_extension_statistics()
    extension_counter: dict[str, int] = defaultdict(int)
    default_skin_counter: dict[str, int] = defaultdict(int)
    skip_skin_counter: dict[str, int] = defaultdict(int)
    for db_name, stats in result.items():
        for extension in stats.extensions:
            extension_counter[extension] += 1
        default_skin_counter[stats.default_skin] += 1
        for skin in stats.skip_skins:
            skip_skin_counter[skin] += 1
    sort_dict(extension_counter)
    sort_dict(default_skin_counter)
    sort_dict(skip_skin_counter)
    save_json_page("User:PetraMagnaBot/extension_statistics.json", extension_counter)
    save_json_page("User:PetraMagnaBot/default_skins.json", default_skin_counter)


if __name__ == "__main__":
    main()
