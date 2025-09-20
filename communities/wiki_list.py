from functools import cache

from utils.db_utils import make_conn, db_dir
from utils.general_utils import MirahezeWiki

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


def main():
    db_fetch()
    print(wiki_mapper)

if __name__ == '__main__':
    main()