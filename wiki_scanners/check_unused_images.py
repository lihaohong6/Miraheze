import pickle
import re
import signal
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import requests

from utils.general_utils import headers, MirahezeWiki
from utils.wiki_scanner import fetch_all_mh_wikis

cache_path = Path("cache.pickle")

def file_size(size: int) -> str:
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{1}f} {unit}"


@dataclass
class FileStats:
    wiki: MirahezeWiki
    file_count: int = -1
    file_size: int = -1
    unused_images_count: int = -1
    done: bool = False

    def __str__(self):
        return (f"{self.wiki.site_name} has {self.file_count} files and {self.unused_images_count} unused images. "
                f"Total size is {file_size(self.file_size)}. "
                f"URL: {self.wiki.url}")


def fetch_file_statistics(wiki: FileStats):
    api_url = wiki.wiki.api_url
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


def fetch_unused_images_count(wiki: FileStats):
    api_url = wiki.wiki.api_url
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


def save_all_wikis(path: Path, wikis: list[FileStats]) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pickle.dump(wikis, open(path, "wb"))
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def fetch_file_stat(file_stats: list[FileStats]):
    for index, wiki in enumerate(file_stats):
        if index % 100 == 99:
            print(f"{index}/{len(file_stats)}")
            save_all_wikis(cache_path, file_stats)
        if wiki.done:
            continue
        wiki.done = True
        try:
            fetch_file_statistics(wiki)
            fetch_unused_images_count(wiki)
        except Exception as e:
            print(f"Failed to gather data for {wiki.wiki.site_name} due to {e}")
        sleep(0.5)
    save_all_wikis(cache_path, file_stats)


def print_problematic_wikis(wikis: list[FileStats]):
    for wiki in wikis:
        if wiki.unused_images_count <= 0:
            continue
        if (wiki.unused_images_count > wiki.file_count / 2 and (wiki.file_count > 5000 or wiki.file_size > (1 << 30))) or wiki.unused_images_count >= 4999:
            print(str(wiki))


def main():
    wikis = fetch_all_mh_wikis()
    file_stats = [FileStats(w) for w in wikis]
    fetch_file_stat(file_stats)
    print_problematic_wikis(file_stats)


if __name__ == "__main__":
    main()
