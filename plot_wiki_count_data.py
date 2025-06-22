import json
from datetime import datetime
from functools import cache
from pathlib import Path

from pywikibot import Page

from utils.general_utils import site

@cache
def get_json_data():
    file_cache_path = Path("cache/wiki_count.json")
    data: dict[str, int]
    if file_cache_path.exists():
        data = json.load(open(file_cache_path, "r"))
    else:
        file_cache_path.parent.mkdir(parents=True, exist_ok=True)
        page = Page(site(), "User:PetraMagnaBot/number_of_wikis.json")
        data = json.loads(page.text)
        json.dump(data, open(file_cache_path, "w"))
    pairs = [(datetime.strptime(k, "%Y-%m-%d"), v)
             for k, v in data.items()]
    pairs.sort(key=lambda x: x[0])
    return pairs


def plot():
    import matplotlib.pyplot as plt
    data = get_json_data()
    dates = [t[0] for t in data]
    values = [t[1] for t in data]

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(dates, values)
    plt.title("Number of wikis over time")
    plt.xlabel("Date")
    plt.ylabel("Number of wikis")
    plt.ylim(bottom=0)
    plt.grid(True)
    plt.show()

def show_month_on_month_changes():
    pairs = get_json_data()
    month_dict: dict[int, set[int]] = {}
    result: list[tuple[datetime, int]] = []

    for date, wikis in pairs:
        year = date.year
        month = date.month
        if year not in month_dict:
            month_dict[year] = set()
        if month in month_dict[year]:
            continue
        month_dict[year].add(month)
        result.append((date, wikis))

    prev = 1
    print("<table>")
    for date, wikis in result:
        change = (wikis - prev) / prev * 100
        positive = change > 0
        print(f"<tr>"
              f"<td>{date.strftime('%Y-%m-%d')}</td>"
              f"<td>{wikis}</td>"
              f"<td style=\"color: {'green' if positive else 'red'}\">{'+' if positive else ''}{change:.2f}%</td>"
              f"</tr>")
        prev = wikis
    print("</table>")


def main():
    plot()

if __name__ == "__main__":
    main()
