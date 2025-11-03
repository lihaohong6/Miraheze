from communities.list_wikis import update_wiki_list_pages
from communities.update_wiki_stats import update_all_wikibase_pages
from communities.wiki_db import update_local_db
from communities.wiki_ranking import rank_wikis
from wiki_scanners.analyses import force_update_all_statistics


def main():
    print("All stats.")
    force_update_all_statistics()
    print("Local db.")
    update_local_db()
    print("Wikibase")
    update_all_wikibase_pages()
    print("Wiki list")
    update_wiki_list_pages()
    print("Wiki rank")
    rank_wikis()


if __name__ == '__main__':
    main()
