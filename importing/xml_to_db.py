import sqlite3
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from bs4 import BeautifulSoup

from importing.import_sharder import parse_lines, ParsedPage, Revision
from utils.db_utils import db_dir


@cache
def get_db():
    conn = sqlite3.connect(db_dir / "xml.sqlite")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        title TEXT NOT NULL,
        page_id INTEGER PRIMARY KEY,
        latest_revision INTEGER REFERENCES revisions(revision_id) DEFERRABLE INITIALLY DEFERRED
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS revisions (
        revision_id INTEGER PRIMARY KEY,
        page_id INTEGER REFERENCES pages(page_id) DEFERRABLE INITIALLY DEFERRED,
        text TEXT NOT NULL,
        contributor TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    conn.commit()


@dataclass
class XmlRevision:
    revision_id: int
    text: str
    contributor: str
    timestamp: str


@dataclass
class XmlPage:
    title: str
    page_id: int
    revisions: list[XmlRevision]


def parse_page_revision(revision: Revision) -> XmlRevision:
    xml = "\n".join(revision.lines)
    soup = BeautifulSoup(xml, "lxml")
    revision_id = int(soup.find("id").text)
    text = soup.find("text").text
    username = soup.find("username")
    if username is not None:
        contributor = username.text
    else:
        ip = soup.find("ip")
        if ip is not None:
            contributor = ip
        else:
            contributor = "unknown"
    timestamp = soup.find("timestamp").text
    return XmlRevision(revision_id, text, contributor, timestamp)


def parse_page_xml(page: ParsedPage) -> XmlPage:
    from bs4 import BeautifulSoup
    xml = page.start_tag + page.end_tag
    soup = BeautifulSoup(xml, "lxml")
    title = soup.find('title').text
    page_id = int(soup.find('id').text)
    revisions = [parse_page_revision(r) for r in page.revisions]
    return XmlPage(title, page_id, revisions)


def add_page(original_page: ParsedPage) -> None:
    conn = get_db()
    cursor = conn.cursor()
    page = parse_page_xml(original_page)
    cursor.execute("""
    INSERT INTO pages (title, page_id, latest_revision) VALUES (?, ?, ?) 
    """, (page.title, page.page_id, page.revisions[-1].revision_id))
    args = []
    for r in page.revisions:
        args.append((r.revision_id, page.page_id, r.text, r.contributor, r.timestamp))
    cursor.executemany("""
    INSERT INTO revisions (revision_id, page_id, text, contributor, timestamp) VALUES (?, ?, ?, ?, ?)
    """, args)
    conn.commit()


def main():
    init_db()
    file_name = Path(sys.argv[1])
    assert file_name.exists()
    with open(file_name, "r") as f:
        lines = f.readlines()
    dump_file = parse_lines(lines)
    for page in dump_file.pages:
        add_page(page)

if __name__ == "__main__":
    main()