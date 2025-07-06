from collections import defaultdict

from utils.general_utils import MirahezeWiki, save_json_page
from utils.wiki_scanner import fetch_all_mh_wikis
from wiki_scanners.extension_statistics import get_wiki_extension_statistics, sort_dict, WikiExtensionStatistics
from wiki_scanners.site_statistics import get_wiki_site_statistics, WikiSiteStatistics

wikis: dict[str, MirahezeWiki] = dict((w.db_name, w) for w in fetch_all_mh_wikis())


def get_wiki_active_editors() -> dict[str, int]:
    result: dict[str, int] = defaultdict(int)
    for k, v in get_wiki_site_statistics(read_only=True).items():
        v: WikiSiteStatistics
        if v is not None:
            result[k] = v.active_users
    return result


def get_wikis_with_most_and_least_extensions():
    s1 = get_wiki_extension_statistics(read_only=True)
    result: list[tuple[MirahezeWiki, list[str]]] = []
    for k, v in s1.items():
        v: WikiExtensionStatistics
        if v is not None:
            result.append((wikis[k], v.extensions))
    result.sort(key=lambda t: len(t[1]), reverse=True)
    result = result[0:2] + result[-10:]
    for r in result:
        print(r)


def get_most_popular_extensions_by_active_users() -> dict[str, int]:
    active_editors = get_wiki_active_editors()
    result: dict[str, int] = defaultdict(int)
    for wiki, v in get_wiki_extension_statistics(read_only=True).items():
        for ext in v.extensions:
            result[ext] += active_editors[wiki]
    return result


def save_statistics():
    result = get_most_popular_extensions_by_active_users()
    sort_dict(result)
    save_json_page("User:PetraMagnaBot/extensions_by_active_users.json", result)


def main():
    save_statistics()


if __name__ == '__main__':
    main()
