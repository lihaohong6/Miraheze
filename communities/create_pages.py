from pywikibot import Site, Page
from wikibaseintegrator import datatypes
from communities.wbi_helper import get_wbi, preload_items
from communities.wiki_db import db_fetch
from utils.wiki_scanner import run_wiki_scanner_query
from utils.general_utils import throttle

TEMPLATE_TEXT = """{{Wiki top}}
{{InfoboxWiki}}
'''{{subst:PAGENAME}}''' is a Miraheze wiki.
{{Wiki bottom}}"""


def create_missing_main_pages():
    """
    Retrieves the top 100 wikis by active users.
    For each, ensures it has a main-namespace page connected via sitelink.
    If the page does not exist, create it and connect it.
    """
    site = Site("communities")
    wbi = get_wbi()

    # get top 100 by active users
    top_wikis = [r[0] for r in run_wiki_scanner_query("most_active_users")[:20]]
    db_to_item = db_fetch()
    item_to_db = {v: k for k, v in db_to_item.items()}

    # preload all corresponding items
    for item_id, item in preload_items(list(item_to_db.keys()), wbi=wbi):
        db = item_to_db[item_id]
        if db not in top_wikis:
            continue

        label = item.labels.get("en")
        if not label:
            print(f"ERROR: No label for {db}")
            continue
        label = label.value

        sitelinks = item.sitelinks.get_json()
        has_main = any(link["site"] == "communitieswiki" for link in sitelinks.values())

        if has_main:
            continue

        page = Page(site, label)
        if not page.exists():
            print(f"Will create {page.title()}")
            page.text = TEMPLATE_TEXT
            page.save(summary="Create wiki page from Wikibase item", bot=False)

        # connect the new page as sitelink
        item.sitelinks.set("communitieswiki", label)
        try:
            throttle(2)
            item.write(summary="Add sitelink", is_bot=True)
            print(f"Linked {label}")
        except Exception as e:
            print(f"Failed to add sitelink for {label}: {e}")


if __name__ == "__main__":
    create_missing_main_pages()
