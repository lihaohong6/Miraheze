from functools import cache

from pywikibot import Site
from pywikibot.pagegenerators import GeneratorFactory

from communities.wbi_helper import preload_items
from utils.db_utils import make_conn, db_dir
from utils.general_utils import MirahezeWiki
from utils.wiki_scanner import fetch_all_mh_wikis

communities_wiki_db = db_dir / "communities.sqlite"

@cache
def get_communities_db_conn():
    return make_conn(communities_wiki_db)

@cache
def db_init() -> None:
    conn = get_communities_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS communities (
        db_name TEXT PRIMARY KEY ,
        wiki_name TEXT NOT NULL,
        property TEXT NOT NULL
    )
    """)
    conn.commit()

@cache
def db_fetch() -> dict[str, str]:
    db_init()
    conn = get_communities_db_conn()
    cursor = conn.cursor()
    cursor.execute(
    """
    SELECT db_name, property FROM communities
    order by db_name desc 
    """
    )
    rows = cursor.fetchall()
    return dict(rows)


def get_item_id_from_wiki(wiki: MirahezeWiki) -> str | None:
    db_dict = db_fetch()
    if wiki.db_name in db_dict:
        return db_dict[wiki.db_name]
    return None

def insert_item_id_for_wiki(wiki: MirahezeWiki, item_id: str) -> None:
    db_init()
    conn = get_communities_db_conn()
    cursor = conn.cursor()
    cursor.execute(
    """
    INSERT OR REPLACE INTO communities (db_name, wiki_name, property) values (?, ?, ?)
    """,
    (wiki.db_name, wiki.site_name, item_id))
    conn.commit()

def replace_wiki_list(wikis: list[tuple[MirahezeWiki, str]]):
    db_init()
    conn = get_communities_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM communities WHERE true;
    """)
    params = ((w[0].db_name, w[0].site_name, w[1]) for w in wikis)
    cursor.executemany(
        """
        INSERT OR REPLACE INTO communities (db_name, wiki_name, property) values (?, ?, ?)
        """,
        params)
    conn.commit()


def get_wiki_dict() -> dict[str, MirahezeWiki]:
    return dict((w.db_name, w) for w in fetch_all_mh_wikis())


def update_local_db():
    mh_wikis = get_wiki_dict()
    s = Site("communities")
    gen = GeneratorFactory(s)
    gen.handle_args(['-start:Item:!'])
    gen = gen.getCombinedGenerator(preload=False)
    titles = [page.title().split(":")[-1] for page in gen]
    result: list[tuple[MirahezeWiki, str]] = []
    for prop, item in preload_items(titles):
        db_names = item.claims.get('P12')
        if len(db_names) == 0:
            continue
        if len(db_names) > 1:
            raise RuntimeError(f"Multiple DB names found for {prop}")
        db_name = db_names[0].mainsnak.datavalue['value']
        if 'wiki' not in db_name:
            db_names += 'wiki'
        if db_name not in mh_wikis:
            print(f"DB name {db_name} not found among list of MH wikis")
            continue
        result.append((mh_wikis[db_name], prop))
    replace_wiki_list(result)


def main():
    update_local_db()

if __name__ == '__main__':
    main()
