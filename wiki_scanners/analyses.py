from datetime import timedelta

from utils.wiki_scanner import fetch_all_mh_wikis
from wiki_scanners.extension_statistics import get_wiki_extension_statistics
from wiki_scanners.site_statistics import get_wiki_site_statistics


def force_update_all_statistics():
    exp = timedelta(days=1)
    fetch_all_mh_wikis(cache_expiry=exp)
    get_wiki_extension_statistics(cache_expiry=exp)
    get_wiki_site_statistics(cache_expiry=exp)


def main():
    force_update_all_statistics()


if __name__ == '__main__':
    main()
