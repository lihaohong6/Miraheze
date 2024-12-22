import pickle
import re
import signal
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import requests

from utils import headers

cache_path = Path("cache.pickle")

def file_size(size: int) -> str:
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{1}f} {unit}"


@dataclass
class MirahezeWiki:
    dbname: str
    sitename: str
    url: str
    file_count: int = -1
    file_size: int = -1
    unused_images_count: int = -1
    done: bool = False

    @property
    def api_url(self):
        return self.url + "/w/api.php"

    def __str__(self):
        return (f"{self.sitename} has {self.file_count} files and {self.unused_images_count} unused images. "
                f"Total size is {file_size(self.file_size)}. "
                f"URL: {self.url}")


def fetch_all_mh_wikis() -> list[MirahezeWiki]:
    # FIXME: how to use the paginated API?
    url = "https://meta.miraheze.org/w/api.php?action=wikidiscover&wdstate=active|public&format=json"
    wiki_list = requests.get(url, headers=headers).json()["wikidiscover"]
    results = []
    for wiki in wiki_list:
        results.append(MirahezeWiki(dbname=wiki["dbname"], sitename=wiki["sitename"], url=wiki["url"]))
    return results


def fetch_file_statistics(wiki: MirahezeWiki):
    api_url = wiki.api_url
    media_statistics = requests.get(api_url,
                                    params={"action": "query",
                                            "list": "querypage",
                                            "qppage": "MediaStatistics",
                                            "format": "json"},
                                    headers=headers)
    media_statistics = media_statistics.json()["query"]["querypage"]["results"]

    file_count = 0
    size_count = 0
    for row in media_statistics:
        string = row["title"]
        match = re.search(r";(\d+);(\d+)$", string)
        file_count += int(match.group(1))
        size_count += int(match.group(2))
    wiki.file_count = file_count
    wiki.file_size = size_count


def fetch_unused_images_count(wiki: MirahezeWiki):
    api_url = wiki.api_url
    count = 0
    offset = 0
    while True:
        unused_images = requests.get(api_url,
                                     params={"action": "query",
                                             "list": "querypage",
                                             "qppage": "Unusedimages",
                                             "qpoffset": offset,
                                             "qplimit": 500,
                                             "format": "json"},
                                     headers=headers)
        unused_images = unused_images.json()["query"]["querypage"]["results"]
        count += len(unused_images)
        if len(unused_images) < 500:
            break
        offset += len(unused_images)
    wiki.unused_images_count = count


def save_all_wikis(path: Path, wikis: list[MirahezeWiki]) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pickle.dump(wikis, open(path, "wb"))
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def get_all_wikis(path: Path) -> list[MirahezeWiki]:
    if not path.exists():
        wikis = fetch_all_mh_wikis()
        save_all_wikis(path, wikis)
    return pickle.load(open(path, "rb"))


def fetch_wiki_info(wikis: list[MirahezeWiki]):
    for index, wiki in enumerate(wikis):
        if index % 100 == 99:
            print(f"{index}/{len(wikis)}")
            save_all_wikis(cache_path, wikis)
        if wiki.done:
            continue
        wiki.done = True
        try:
            fetch_file_statistics(wiki)
            fetch_unused_images_count(wiki)
        except Exception as e:
            print(f"Failed to gather data for {wiki.sitename} due to {e}")
        sleep(0.5)
    save_all_wikis(cache_path, wikis)


def print_problematic_wikis(wikis: list[MirahezeWiki]):
    for wiki in wikis:
        if wiki.unused_images_count <= 0:
            continue
        if (wiki.unused_images_count > wiki.file_count / 2 and (wiki.file_count > 5000 or wiki.file_size > (1 << 30))) or wiki.unused_images_count >= 4999:
            print(str(wiki))


def main():
    wikis = get_all_wikis(cache_path)
    fetch_wiki_info(wikis)
    print_problematic_wikis(wikis)


if __name__ == "__main__":
    main()
