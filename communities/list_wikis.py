from typing import Callable

from airium import Airium
from pywikibot import Page, Site
from wikitextparser import parse

from communities.wiki_db import get_item_id_from_wiki, get_wiki_dict
from utils.wiki_scanner import run_wiki_scanner_query


wiki_dict = get_wiki_dict()


def get_wiki_name_column(db: str) -> str:
    wiki = wiki_dict[db]
    item_id = get_item_id_from_wiki(wiki)
    if item_id is None:
        item = ""
    else:
        item = f" ([[Item:{item_id}|{item_id}]])"
    return f"[[mh:{db[:-4]}|{wiki.site_name}]]{item}"


def list_wikis_by_article_count() -> str:
    return generate_table('most_articles', ['ac', 'pc'], limit=500)


def list_wikis_by_active_users() -> str:
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
    return str(a)


def list_wikis_by_creation_date() -> str:
    return generate_table("sort_by_creation_date", ['cd', 'au'])


def generate_table(sql_query: str, fields: list[str], limit: int = None) -> str:
    mapping = {
        'cd': 'Creation date',
        'ac': 'Article count',
        'pc': 'Page count',
        'au': 'Active users',
        'status': 'Status'
    }
    a = Airium(base_indent="")
    with a.table(klass="wikitable sortable"):
        with a.tr():
            a.th(_t="Name")
            for f in fields:
                a.th(_t=mapping.get(f, ""))

        wikis = run_wiki_scanner_query(sql_query)
        if limit:
            wikis = wikis[:limit]
        for wiki in wikis:
            db = wiki[0]
            lst = wiki[2:]
            with a.tr():
                a.td(_t=get_wiki_name_column(db))
                for value in lst:
                    a.td(_t=str(value))
    return str(a)


def list_inactive_wikis():
    return generate_table("inactive_wikis", ['ac', 'pc'])


def list_exempt_wikis():
    return generate_table("exempt_wikis", ['au', 'ac', 'pc'])


def update_wiki_list_pages():
    pages: dict[str, Callable[[], str]] = {
        'List_of_wikis_by_active_users': list_wikis_by_active_users,
        'List_of_wikis_by_article_count': list_wikis_by_article_count,
        'List_of_wikis_by_creation_date': list_wikis_by_creation_date,
        'List_of_inactive_wikis': list_inactive_wikis,
        'List_of_exempt_wikis': list_exempt_wikis,
    }
    site = Site("communities")
    for title, func in pages.items():
        p = Page(site, title)
        parsed = parse(p.text)
        tables = parsed.get_tags('table')
        assert len(tables) == 1, f"Found {len(tables)} tables in {title}"
        table = tables[0]
        table.string = func()
        p.text = str(parsed)
        p.save(summary="update wiki list")


if __name__ == '__main__':
    update_wiki_list_pages()
