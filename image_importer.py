import logging
import pickle
from pathlib import Path

from pywikibot import Site, FilePage
from pywikibot.pagegenerators import GeneratorFactory, PreloadingGenerator

from utils import cache_dir


original_wiki = Site(code="original")
new_wiki = Site(code="miraheze")
local_files_directory = Path("~/Downloads/vocaloid-lyrics-wiki-image-dump").expanduser()
assert local_files_directory.exists()

logger = logging.getLogger("importer")
logging.basicConfig(level=logging.INFO,
                    filename="importer_log.txt",
                    filemode="w",
                    encoding="utf-8")

def get_files_on_wiki(site: Site) -> set[str]:
    gen = GeneratorFactory(site)
    gen.handle_args(['-start:File:!'])
    gen = gen.getCombinedGenerator()
    result: set[str] = set()
    for p in gen:
        p: FilePage
        result.add(p.title(with_ns=True, underscore=True))
    return result


def get_original_wiki_files() -> set[str]:
    """
    Retrieve a set of file page titles from the original wiki.
    Results are cached on disk so that later tries do not request
    the full list of files.
    :return:
    """
    cache_file = cache_dir / "original_images.pickle"
    if not cache_file.exists():
        files = get_files_on_wiki(original_wiki)
        with open(cache_file, "wb") as f:
            pickle.dump(files, f)
    else:
        files = pickle.load(open(cache_file, "rb"))
    return files


def get_miraheze_wiki_files() -> set[str]:
    """
    Cannot cache because we might have uploaded more files last time.
    :return:
    """
    return get_files_on_wiki(new_wiki)


def get_upload_source(old_page: FilePage) -> str:
    """
    Figure out how to upload a file from a FilePage.
    The file might be available locally already, or it must be downloaded
    from the url of the old page (possibly generating more network requests)
    :param old_page:
    :return:
    """
    file_name = old_page.title(with_ns=False, underscore=True)
    local_file = local_files_directory / file_name
    if local_file.exists():
        return str(local_file)
    return old_page.get_file_url()


def upload_files(files: list[str]) -> None:
    logger.info(f"Beginning to upload {len(files)} files.")
    gen = PreloadingGenerator(FilePage(original_wiki, f) for f in files)
    counter = 0
    for old_page in gen:
        old_page: FilePage
        file_title = old_page.title(with_ns=True, underscore=True)
        new_page = FilePage(new_wiki, file_title)
        res = new_page.upload(get_upload_source(old_page),
                              text=old_page.text,
                              summary=f"Imported from {old_page.full_url()}")
        if res:
            counter += 1
            if counter > 0 and counter % 100 == 0:
                logger.info(f"Uploaded {counter + 1}/{len(files)} files.")
        else:
            logger.error(f"Failed to upload {file_title}.")


def main():
    all_files = get_original_wiki_files()
    files_needing_upload = all_files.difference(get_miraheze_wiki_files())
    upload_files(list(files_needing_upload))


if __name__ == "__main__":
    main()
