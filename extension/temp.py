import re
from dataclasses import dataclass
from pathlib import Path

from pywikibot.pagegenerators import GeneratorFactory

from extension.extension_utils import lower_to_upper, beta
from wiki_scanners.extension_statistics import get_extension_popularity_statistics, WikiExtensionStatistics, \
    get_wiki_extension_statistics


@dataclass
class ExtensionTestingStatus:
    name: str
    tested: bool
    marked_as_global: bool = False

def get_extension_testing_status() -> list[ExtensionTestingStatus]:
    data_file = Path("data/extension_testing.txt")
    if not data_file.exists():
        raise RuntimeError(f"No extension testing data found. Please put it in {data_file}")
    with open(data_file, "r", encoding="utf-8") as file:
        lines = file.readlines()
    result = []
    for line in lines:
        r = re.search(r"^\[(| |x)] ?(\w+)", line)
        if r is None:
            continue
        g1 = r.group(1)
        ext = r.group(2)
        marked_as_global = "global" in line
        result.append(ExtensionTestingStatus(ext, g1 == 'x', marked_as_global))
    return result


def mark_global_extensions():
    gen = GeneratorFactory(beta())
    gen.handle_args(['-cat:Default extensions'])
    gen = gen.getCombinedGenerator()
    global_extensions = set(p.title().lower().replace(' ', '') for p in gen)
    for extension in get_extension_testing_status():
        if extension.name.lower().replace(' ', '') not in global_extensions:
            continue
        if not extension.tested and not extension.marked_as_global:
            print(extension.name)
        elif not extension.tested and extension.marked_as_global:
            print(f"Already marked {extension.name}")


def get_ready_wikis():
    ready_extensions: set[str] = set(e.name.lower()
                                     for e in get_extension_testing_status()
                                     if e.tested)
    for wiki, statistics in get_wiki_extension_statistics().items():
        problematic_extensions = []
        for extension in statistics.extensions:
            extension = lower_to_upper(extension).lower()
            if extension not in ready_extensions:
                problematic_extensions.append(extension)
        if len(problematic_extensions) > 0:
            print(f"{wiki} has problematic extensions: {', '.join(problematic_extensions)}")
        else:
            print(f"Wiki {wiki} is ready")


def main():
    s: WikiExtensionStatistics
    testing_status: dict[str, bool] = dict((t.name, t.tested) for t in get_extension_testing_status())
    stats = get_extension_popularity_statistics()
    for ext, num in stats.items():
        ext = lower_to_upper(ext)
        if ext not in testing_status:
            print(f"Where is {ext}?")
            continue
        if not testing_status[ext]:
            print(f"{ext} is not tested")

if __name__ == "__main__":
    get_ready_wikis()
else:
    raise RuntimeError()