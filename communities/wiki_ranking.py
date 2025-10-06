from dataclasses import dataclass
from typing import DefaultDict

from pywikibot import Site, Page

from communities.wiki_db import get_wiki_dict
from utils.general_utils import WikiState, save_json_page
from wiki_scanners.site_statistics import get_wiki_site_statistics


@dataclass
class StatisticsTotal:
    total: int
    articles: dict[int, int]
    pages: dict[int, int]
    edits: dict[int, int]
    files: dict[int, int]
    users: dict[int, int]
    active_users: dict[int, int]


def rank_wikis():
    all_wikis = get_wiki_dict()
    stats = get_wiki_site_statistics(read_only=True)
    result: dict[str, dict[int, int]] = {
        'articles': DefaultDict(int),
        'pages': DefaultDict(int),
        'edits': DefaultDict(int),
        'files': DefaultDict(int),
        'users': DefaultDict(int),
        'active_users': DefaultDict(int)
    }
    total = 0
    for k, v in stats.items():
        if k not in all_wikis:
            continue
        if v is None:
            continue
        wiki = all_wikis[k]
        if wiki.state not in {WikiState.ACTIVE.value, WikiState.EXEMPT.value}:
            continue
        total += 1
        for stat in result.keys():
            num = getattr(v, stat, None)
            # temporary
            if num is None and stat == 'files':
                num = getattr(v, 'images', None)
            assert num is not None
            result[stat][num] += 1
    t = StatisticsTotal(total=total, **result)
    s = Site("communities")
    save_json_page(Page(s, "Module:Wiki_rank/data.json"), t)


def main():
    rank_wikis()


if __name__ == '__main__':
    main()
