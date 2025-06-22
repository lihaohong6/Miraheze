import sqlite3
from pathlib import Path

db_dir = Path('databases')
db_dir.mkdir(parents=True, exist_ok=True)


def make_conn(db_name: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_name)


def get_conn(db_name: Path) -> sqlite3.Connection:
    if not hasattr(get_conn, "conn"):
        get_conn.conn = make_conn(db_name)
    return get_conn.conn


def get_cursor(db_name: Path) -> sqlite3.Cursor:
    return get_conn(db_name).cursor()
