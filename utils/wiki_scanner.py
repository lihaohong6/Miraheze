from datetime import timedelta, datetime
from typing import TypeVar, Callable

import jsonpickle

from utils.db_utils import db_dir, get_conn
from utils.general_utils import MirahezeWiki, fetch_all_mh_wikis_uncached

db_name = db_dir / "wiki_scanner.sqlite"

CACHE_EXPIRY_TABLE = "cache_expiry"

DEFAULT_CACHE_EXPIRY = timedelta(days=7)


def create_tables():
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS all_wikis (
    db_name VARCHAR(64) PRIMARY KEY NOT NULL,
    site_name VARCHAR(128) NOT NULL,
    url TEXT NOT NULL
    )
    """)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {CACHE_EXPIRY_TABLE} (
    table_name VARCHAR(64) PRIMARY KEY NOT NULL,
    expiration INTEGER NOT NULL
    )""")
    conn.commit()


def deserialize_miraheze_wikis(rows: list[tuple[str, str, str]]) -> list[MirahezeWiki]:
    return [MirahezeWiki.from_sql_row(row) for row in rows]


def fetch_all_mh_wikis(cache_expiry: timedelta = DEFAULT_CACHE_EXPIRY) -> list[MirahezeWiki]:
    create_tables()
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    SELECT expiration FROM {CACHE_EXPIRY_TABLE}
    WHERE table_name = ?
    """, ("all_wikis",))
    rows = cursor.fetchall()
    fetch_new_list = False
    if len(rows) == 0:
        fetch_new_list = True
    else:
        expiry_date = rows[0][0]
        if datetime.fromtimestamp(expiry_date) + cache_expiry < datetime.now():
            fetch_new_list = True
    if fetch_new_list:
        wikis = fetch_all_mh_wikis_uncached()
        data = [wiki.to_sql_values() for wiki in wikis]
        cursor.executemany(f"INSERT OR REPLACE INTO all_wikis VALUES (?, ?, ?)", data)
        cursor.execute(f"""
        INSERT OR REPLACE INTO {CACHE_EXPIRY_TABLE}
        VALUES (?, ?)
        """, ('all_wikis', int(datetime.now().timestamp())))
        conn.commit()
    cursor.execute(f"""
    SELECT db_name, site_name, url FROM all_wikis
    """)
    rows = cursor.fetchall()
    assert len(rows) >= 500
    return deserialize_miraheze_wikis(rows)


def chunk_list(lst: list, k: int) -> list[list]:
    return [lst[i:i + k] for i in range(0, len(lst), k)]


T = TypeVar("T")


def scan_wikis(mapper: Callable[[list[MirahezeWiki]], dict[str, T | None]],
               table_name: str,
               reset: bool = False,
               batch_size: int = 1) -> dict[str, T]:
    wikis = fetch_all_mh_wikis()
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
    db_name VARCHAR(64) PRIMARY KEY NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (db_name) REFERENCES all_wikis(db_name) ON DELETE CASCADE ON UPDATE CASCADE
    )""")
    conn.commit()
    if not reset:
        cursor.execute(f"""
        SELECT * FROM all_wikis
        WHERE db_name NOT IN (SELECT db_name FROM {table_name})
        """)
        wikis = deserialize_miraheze_wikis(cursor.fetchall())
    wiki_chunks = chunk_list(wikis, batch_size)
    for wiki_chunk in wiki_chunks:
        result = mapper(wiki_chunk)
        for wiki_db_name, extension_info in result.items():
            text = jsonpickle.encode(extension_info)
            cursor.execute(f"""
            INSERT OR REPLACE INTO {table_name} VALUES (?, ?)
            """, (wiki_db_name, text))
        conn.commit()
    cursor.execute(f"""
    SELECT db_name, data FROM {table_name}
    """)
    rows = cursor.fetchall()
    assert len(rows) >= 500
    return dict((row[0], jsonpickle.decode(row[1])) for row in rows)


def main():
    wikis = fetch_all_mh_wikis()
    print(wikis)


if __name__ == "__main__":
    main()
