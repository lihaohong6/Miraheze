from datetime import datetime
import json
import re
from pathlib import Path

import requests
from pywikibot import Page

from utils.general_utils import headers, site, save_json_page


def main():
    response = requests.get("https://meta.miraheze.org/w/api.php", params={
        'action': 'parse',
        'text': '<p id="numofwikis">{{NUMBEROFWIKIS}}</p><p id="activewikis">{{NUMBEROFACTIVEWIKIS}}</p>',
        'contentmodel': 'wikitext',
        'prop': 'text',
        'format': 'json',
    }, headers=headers)
    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        return
    text = response.json()['parse']['text']['*']

    def get_num(element_id: str) -> int:
        num = re.search(rf'<p id="{element_id}">(\d+)(\n)?</p>', text).group(1)
        return int(num)

    current_date = datetime.now()
    date_format = current_date.strftime("%Y-%m-%d")

    add_data_to_page(date_format,
                     get_num("numofwikis"),
                     Page(site(), "User:PetraMagnaBot/number_of_wikis.json"))
    add_data_to_page(date_format,
                     get_num("activewikis"),
                     Page(site(), "User:PetraMagnaBot/number_of_active_wikis.json"))


def add_data_to_page(date_format: str, num: int, page: Page):
    if page.text != "":
        obj = json.loads(page.text)
    else:
        obj = dict()
    # Don't override existing values
    if date_format in obj:
        return
    obj[date_format] = num
    save_json_page(page, obj)


def import_from_wayback_dump():
    cache_dir = Path('cache')
    result: dict[str, int] = {}
    prev_count = 0
    for sub_dir in cache_dir.iterdir():
        if sub_dir.is_file():
            continue
        date_string = sub_dir.name[:8]
        date_string = date_string[:4] + "-" + date_string[4:6] + "-" + date_string[6:]
        cur = sub_dir
        while cur.is_dir():
            cur = list(cur.iterdir())[0]
        assert "Miraheze" in cur.name
        num = 0
        with open(cur, "r", encoding="utf-8") as f:
            text = f.read()
            if text.strip() == "":
                continue
            for regex in [r"Currently hosting (\d+) Wikis", r"<b>([\d,]+)</b>"]:
                search_result = re.search(regex, text)
                if search_result:
                    num = int(search_result.group(1).replace(",", ""))
                    break
        if num == 0:
            print(f"Cannot determine number of Wikis for {date_string}")
            continue
        if num == prev_count:
            continue
        prev_count = num
        result[date_string] = num
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    # import_from_wayback_dump()
    main()