from datetime import timedelta, datetime
from pathlib import Path
from sqlite3 import Connection
from typing import TypeVar, Callable

import jsonpickle

from utils.db_utils import db_dir, get_conn
from utils.general_utils import MirahezeWiki, fetch_all_mh_wikis_uncached

db_name = db_dir / "wiki_scanner.sqlite"

DEFAULT_CACHE_EXPIRY = timedelta(days=7)

def get_wiki_scanner_database() -> Connection:
    return get_conn(db_name)

def create_tables():
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS all_wikis (
    db_name VARCHAR(64) PRIMARY KEY NOT NULL,
    site_name VARCHAR(128) NOT NULL,
    url TEXT NOT NULL,
    category TEXT,
    language TEXT,
    creation_date TEXT,
    state TEXT,
    last_update INTEGER NOT NULL DEFAULT(unixepoch())
    )
    """)
    cursor.execute(f"""
    CREATE TRIGGER IF NOT EXISTS all_wikis_last_update
        AFTER UPDATE
        ON all_wikis
        FOR EACH ROW
        WHEN NEW.last_update = OLD.last_update
    BEGIN
        UPDATE all_wikis SET last_update=CURRENT_TIMESTAMP WHERE db_name=OLD.db_name;
    END;
    """)
    conn.commit()


def deserialize_miraheze_wikis(rows: list[tuple]) -> list[MirahezeWiki]:
    return [MirahezeWiki.from_sql_row(row[:-1]) for row in rows]


def fetch_all_mh_wikis(cache_expiry: timedelta = DEFAULT_CACHE_EXPIRY) -> list[MirahezeWiki]:
    create_tables()
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    SELECT max(last_update) from all_wikis;
    """)
    rows = cursor.fetchall()
    fetch_new_list = False
    if len(rows) == 0:
        fetch_new_list = True
    else:
        expiry_date = rows[0][0]
        if expiry_date is None or datetime.fromtimestamp(expiry_date) + cache_expiry < datetime.now():
            fetch_new_list = True
    if fetch_new_list:
        print("Fetching list of all wikis again due to cache expiry.")
        wikis = fetch_all_mh_wikis_uncached()
        data = [wiki.to_sql_values() for wiki in wikis]
        cursor.executemany(f"INSERT OR REPLACE INTO all_wikis VALUES (?, ?, ?, ?, ?, ?, ?, UNIXEPOCH())", data)
        conn.commit()
    cursor.execute(f"""
    SELECT * FROM all_wikis
    """)
    rows = cursor.fetchall()
    assert len(rows) >= 500
    return deserialize_miraheze_wikis(rows)


def chunk_list(lst: list, k: int) -> list[list]:
    return [lst[i:i + k] for i in range(0, len(lst), k)]


T = TypeVar("T")


def run_wiki_scanner_query(file_name: str, descriptions: list[str] = None) -> list[tuple]:
    sql_files_root = Path("wiki_scanners/sql")
    file = sql_files_root / (file_name + ".sql")
    assert file.exists() and file.is_file()
    with open(file, "r", encoding="utf-8") as f:
        sql = f.read()
    cursor = get_conn(db_name).execute(sql)
    if descriptions is not None:
        descriptions.extend(d[0] for d in cursor.description)
    return cursor.fetchall()


def scan_wikis(mapper: Callable[[list[MirahezeWiki]], dict[str, T | None]],
               table_name: str,
               batch_size: int = 1,
               cache_expiry: timedelta | None = None) -> dict[str, T]:
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
    db_name VARCHAR(64) PRIMARY KEY NOT NULL,
    data TEXT NOT NULL,
    last_update INTEGER NOT NULL DEFAULT(unixepoch()),
    FOREIGN KEY (db_name) REFERENCES all_wikis(db_name) ON DELETE CASCADE ON UPDATE CASCADE
    )
    """)
    cursor.execute(f"""
    CREATE TRIGGER IF NOT EXISTS {table_name}_last_update
        AFTER UPDATE
        ON {table_name}
        FOR EACH ROW
        WHEN NEW.last_update = OLD.last_update
    BEGIN
        UPDATE {table_name} SET last_update=CURRENT_TIMESTAMP WHERE db_name=OLD.db_name;
    END
    """)
    conn.commit()
    if cache_expiry:
        cursor.execute(f"""
        WITH need_update AS (
            SELECT db_name FROM all_wikis
            WHERE db_name NOT IN (SELECT {table_name}.db_name FROM {table_name})
            UNION
            SELECT db_name FROM {table_name}
            WHERE unixepoch() - last_update > {cache_expiry.total_seconds()}
        )
        SELECT * FROM all_wikis
        WHERE db_name in need_update;
        """)
        wikis = deserialize_miraheze_wikis(cursor.fetchall())
        # These wikis won't see any stat changes
        wikis = [w for w in wikis if w.state not in {"closed", "deleted"}]
        wiki_chunks = chunk_list(wikis, batch_size)
        for wiki_chunk in wiki_chunks:
            result = mapper(wiki_chunk)
            for wiki_db_name, extension_info in result.items():
                text = jsonpickle.encode(extension_info)
                cursor.execute(f"""
                INSERT OR REPLACE INTO {table_name} (db_name, data) VALUES (?, ?)
                """, (wiki_db_name, text))
            conn.commit()
    cursor.execute(f"""
    SELECT db_name, data FROM {table_name}
    """)
    rows = cursor.fetchall()
    assert len(rows) >= 50
    return dict((row[0], jsonpickle.decode(row[1])) for row in rows)


def main():
    fetch_all_mh_wikis(cache_expiry=timedelta(days=0))


if __name__ == "__main__":
    main()
