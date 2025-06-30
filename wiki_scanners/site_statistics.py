from dataclasses import dataclass

import requests

from utils.general_utils import MirahezeWiki, headers
from utils.wiki_scanner import scan_wikis


@dataclass
class WikiSiteStatistics:
    pages: int
    articles: int
    edits: int
    images: int
    active_users: int


def fetch_wiki_site_statistics(wikis: list[MirahezeWiki]) -> dict[str, WikiSiteStatistics | None]:
    wiki = wikis[0]
    try:
        response = requests.get(wiki.api_url, params={
            'action': 'query',
            'meta': 'siteinfo',
            'siprop': 'statistics',
            'format': 'json',
        }, headers=headers)
        r = response.json()['query']['statistics']
        result = WikiSiteStatistics(
            pages=r['pages'],
            articles=r['articles'],
            edits=r['edits'],
            images=r['images'],
            active_users=r['activeusers'],
        )
    except Exception as e:
        print(e)
        result = None
    return {
        wiki.db_name: result
    }


def get_wiki_site_statistics() -> dict[str, WikiSiteStatistics | None]:
    return scan_wikis(fetch_wiki_site_statistics,
                      "wiki_statistics",
                      reset=False,
                      batch_size=1)


def main():
    print(get_wiki_site_statistics())


if __name__ == "__main__":
    main()
