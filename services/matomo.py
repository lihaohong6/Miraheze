from datetime import date, timedelta
from pathlib import Path

import requests

from services.json_page import JsonPage
from utils.general_utils import headers


def get_matomo_token() -> str:
    p = Path("tokens/matomo.txt")
    assert p.exists()
    return open(p, "r").read()


def update_matomo_analytics():
    json_pages: dict[str, JsonPage] = {
        'nb_uniq_visitors': JsonPage("User:PetraMagnaBot/matomo_unique_visitors.json"),
        'nb_pageviews': JsonPage("User:PetraMagnaBot/matomo_page_views.json")
    }

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=29)
    response = requests.post("https://analytics.wikitide.net/index.php?"
                             "module=API&format=JSON&idSite=1&period=day"
                             f"&date={start},{end}"
                             "&method=API.get&filter_limit=100&format_metrics=1&fetch_archive_state=1&expanded=1&showMetadata=0",
                             data={"token_auth": get_matomo_token(), },
                             headers=headers)
    data = response.json()
    for index, day in enumerate(data):
        v = data[day]
        for k, page in json_pages.items():
            page.set(day, v[k], override=len(data) - index <= 3)
    for p in json_pages.values():
        p.save()


if __name__ == "__main__":
    update_matomo_analytics()
