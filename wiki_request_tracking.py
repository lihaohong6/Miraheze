import re
from datetime import datetime, timedelta
from time import sleep

import requests
from bs4 import BeautifulSoup

from utils.general_utils import headers, save_json_page
from utils.db_utils import get_conn, db_dir

db_name = db_dir / "wiki_request.sqlite"


def create_tables():
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS requests (
            wiki_name VARCHAR(256) PRIMARY KEY NOT NULL,
            request_date TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id int PRIMARY KEY NOT NULL,
            query_offset VARCHAR(30) NOT NULL
        )
    """)
    conn.commit()


def get_wikis(offset: str):
    response = requests.get("https://meta.miraheze.org/wiki/Special:RequestWikiQueue",
                            params={'status': '*',
                                    'language': '*',
                                    'offset': offset},
                            headers=headers)
    if response.status_code != 200:
        raise Exception(response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', attrs={'class': 'mw-datatable'})
    body = table.find('tbody')
    rows = body.find_all('tr')
    result: list[tuple[datetime, str]] = []
    for row in rows:
        timestamp = row.find('td', attrs={'class': 'TablePager_col_cw_timestamp'}).text
        timestamp = timestamp.split(",")[1].strip()
        parsed_date = datetime.strptime(timestamp, "%d %B %Y")
        site_name = row.find('td', attrs={'class': 'TablePager_col_cw_dbname'}).text
        site_name += row.find('td', attrs={'class': 'TablePager_col_cw_sitename'}).text
        result.append((parsed_date, site_name))
    nav = soup.find('span', attrs={'class': 'TablePager_nav'})
    next_page_link = nav.find_all('a', attrs={'role': 'button'})
    for link in next_page_link:
        if "Next" in link.text:
            href: str = link.attrs.get('href', None)
            if href is None:
                continue
            next_offset = re.search(r"offset=(\d+)", href).group(1)
            break
    else:
        next_offset = None
    return result, next_offset


def get_progress() -> str:
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    select query_offset from progress;
    """)
    rows = cursor.fetchall()
    if len(rows) == 0:
        return ""
    assert len(rows) == 1
    return rows[0][0]

def save_progress(wikis: list[tuple[datetime, str]], offset: str | None):
    conn = get_conn(db_name)
    cursor = conn.cursor()
    for wiki in wikis:
        timestamp, site_name = wiki
        site_name = "".join(c for c in site_name if c.isalnum())
        time_string = timestamp.isoformat().split("T")[0]
        cursor.execute(f"""
        insert or ignore into requests (wiki_name, request_date) values ('{site_name}', '{time_string}')
        """)
    if offset is not None:
        cursor.execute(f"""
        insert or replace into progress (id, query_offset) values (1, {offset})
        """)
    conn.commit()

def fetch_wiki_requests():
    offset = get_progress()
    while offset is not None:
        print("Fetching wikis from MH")
        wikis, new_offset = get_wikis(offset)
        save_progress(wikis, new_offset)
        offset = new_offset
        sleep(1)

def collect_data():
    conn = get_conn(db_name)
    cursor = conn.cursor()
    cursor.execute(f"""
    select request_date, count(*)  as c from requests group by request_date order by request_date asc;
    """)
    rows = cursor.fetchall()

    def parse_date(s: str) -> datetime:
        return datetime.strptime(s, "%Y-%m-%d")

    start_date = parse_date(rows[0][0])
    end_date = parse_date(rows[-1][0])
    cur = start_date
    result: dict[str, int] = {}
    while cur <= end_date:
        result[cur.isoformat().split('T')[0]] = 0
        cur = cur + timedelta(days=1)
    for row in rows:
        date, count = row
        result[date] = count
    return result

def main():
    create_tables()
    fetch_wiki_requests()
    data = collect_data()
    save_json_page("User:PetraMagnaBot/number_of_requests.json", data)

if __name__ == '__main__':
    main()
