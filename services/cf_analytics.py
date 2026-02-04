from datetime import date, timedelta
from pathlib import Path

import requests

from services.json_page import JsonPage


def get_token() -> str:
    p = Path("tokens/cf.txt")
    assert p.exists()
    return open(p, "r").read().strip()

def get_zone() -> str:
    p = Path("tokens/cf_zone.txt")
    assert p.exists()
    return open(p, "r").read().strip()


def update_cf_analytics():
    end = date.today()
    start = end - timedelta(days=30)

    json_pages: dict[str, JsonPage] = {
        'uniques': JsonPage("User:PetraMagnaBot/cf_unique_visitors.json"),
        'pageViews': JsonPage("User:PetraMagnaBot/cf_page_views.json"),
        'requests': JsonPage("User:PetraMagnaBot/cf_requests.json"),
    }

    # The minimal GraphQL query for just 'Total Requests'
    query = {
        "query": f"""
        {{
          viewer {{
            zones(filter: {{zoneTag: "{get_zone()}"}}) {{
              httpRequests1dGroups(orderBy: [date_ASC], limit: 100, filter: {{date_geq: "{start}", date_leq: "{end}"}}) {{
                dimensions {{ date }}
                sum {{
                  requests
                  pageViews
                }}
                uniq {{
					uniques
				}}
              }}
            }}
          }}
        }}
        """
    }

    response = requests.post("https://api.cloudflare.com/client/v4/graphql",
                             headers={"Authorization": f"Bearer {get_token()}"},
                             json=query).json()

    rows = response['data']['viewer']['zones'][0]['httpRequests1dGroups']
    # Last day's data is not up-to-date
    rows = rows[:-1]

    for index, row in enumerate(rows):
        date_key = row['dimensions']['date']
        data = row['sum'] | row['uniq']
        for attribute, v in data.items():
            # Only override if data is recent in case it is corrupted somehow
            json_pages[attribute].set(date_key, v, override=len(rows) - index <= 7)

    for p in json_pages.values():
        p.save()


if __name__ == "__main__":
    update_cf_analytics()