from functools import cache

from airium import Airium

from communities.wiki_list import get_item_id_from_wiki
from utils.general_utils import MirahezeWiki
from utils.wiki_scanner import fetch_all_mh_wikis, run_wiki_scanner_query

@cache
def get_wiki_dict() -> dict[str, MirahezeWiki]:
    return dict((w.db_name, w) for w in fetch_all_mh_wikis())

def get_wiki_name_column(db: str) -> str:
    wiki = get_wiki_dict()[db]
    item_id = get_item_id_from_wiki(wiki)
    if item_id is None:
        item = ""
    else:
        item = f" ([[Item:{item_id}|{item_id}]])"
    return f"[[mh:{db[:-4]}|{wiki.site_name}]]{item}"

def list_wikis_by_article_count():
    a = Airium(base_indent="")
    with a.table(klass="wikitable sortable"):
        with a.tr():
            a.th(_t="Name")
            a.th(_t="Article count")
            a.th(_t="Page count")

        for wiki in run_wiki_scanner_query("most_articles")[:500]:
            db, name, articles, pages = wiki
            with a.tr():
                a.td(_t=get_wiki_name_column(db))
                a.td(_t=str(articles))
                a.td(_t=str(pages))
    print(str(a))

def list_wikis_by_active_users():
    a = Airium(base_indent="")
    with a.table(klass="wikitable sortable"):
        with a.tr():
            a.th(_t="Name")
            a.th(_t="Active users")
            a.th(_t="wgActiveUserDays", style="word-break: break-word")

        for wiki in run_wiki_scanner_query("most_active_users")[:800]:
            db, name, au_days, active_users = wiki
            if active_users < 4:
                continue
            with a.tr():
                a.td(_t=get_wiki_name_column(db))
                style = 'background-color: var(--background-color-disabled, #dadde3)'
                au_days = int(au_days)
                if au_days != 30:
                    a.td(_t=str(active_users), style=style)
                else:
                    a.td(_t=str(active_users))
                a.td(_t=str('-' if au_days == 30 else au_days))
    print(str(a))

def list_wikis_by_creation_date():
    a = Airium(base_indent="")
    with a.table(klass="wikitable sortable"):
        with a.tr():
            a.th(_t="Name")
            a.th(_t="Creation date")
            a.th(_t="Active users")

        for wiki in run_wiki_scanner_query("sort_by_creation_date"):
            db, name, creation, au = wiki
            with a.tr():
                a.td(_t=get_wiki_name_column(db))
                a.td(_t=creation)
                a.td(_t=au)
    print(str(a))

if __name__ == '__main__':
    list_wikis_by_creation_date()
