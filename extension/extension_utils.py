import re
from functools import cache

import requests
from pywikibot import Site


def beta():
    return Site('beta')


@cache
def get_table():
    response = requests.get(
        "https://raw.githubusercontent.com/miraheze/mw-config/refs/heads/main/ManageWikiExtensions.php")
    text = response.text
    result: dict[str, str] = {}
    for group in re.findall(r"'([^']+)' =>.*\n.*'name' => '([^']+)'", text):
        result[group[0]] = group[1].replace(' ', '')
    return result

def lower_to_upper(lower: str) -> str:
    table = get_table()
    if lower not in table:
        raise RuntimeError()
    return table[lower]

def main():
    print(get_table())

if __name__ == '__main__':
    main()