from communities.list_wikis import update_wiki_list_pages
from communities.update_wiki_stats import update_all_wikibase_pages
from communities.wiki_db import update_local_db
from wiki_scanners.analyses import force_update_all_statistics


def main():
    update_local_db()
    force_update_all_statistics()
    update_all_wikibase_pages()
    update_wiki_list_pages()


if __name__ == '__main__':
    main()
