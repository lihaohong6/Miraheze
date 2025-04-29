import logging
import pickle
import sys
from argparse import ArgumentParser
from pathlib import Path

from pywikibot import Site, FilePage
from pywikibot.pagegenerators import GeneratorFactory, PreloadingGenerator

from utils import cache_dir

local_files_directory: Path | None = None

logging.basicConfig(level=logging.INFO,
                    filename="importer_log.txt",
                    filemode="a",
                    encoding="utf-8")
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger("importer")
logger.addHandler(handler)

def get_files_on_wiki(site: Site) -> set[str]:
    gen = GeneratorFactory(site)
    gen.handle_args(['-start:File:!'])
    gen = gen.getCombinedGenerator()
    result: set[str] = set()
    for p in gen:
        p: FilePage
        result.add(p.title(with_ns=True, underscore=True))
    return result


def get_original_wiki_files(original_wiki: Site) -> set[str]:
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


def get_miraheze_wiki_files(new_wiki: Site) -> set[str]:
    """
    Cannot cache because we might have uploaded more files last time.
    :return:
    """
    logger.info("Retrieving miraheze wiki files...")
    return get_files_on_wiki(new_wiki)


def get_upload_source(old_page: FilePage) -> str | None:
    """
    Figure out how to upload a file from a FilePage.
    The file might be available locally already, or it must be downloaded
    from the url of the old page (possibly generating more network requests)
    :param old_page:
    :return:
    """
    file_name = old_page.title(with_ns=False, underscore=True)
    if local_files_directory is not None:
        local_file = local_files_directory / file_name
        if local_file.exists():
            logger.info(f"File {file_name} found locally. Using that version instead.")
            return str(local_file)
    return old_page.get_file_url()


def upload_files(files: list[str], original_wiki: Site, new_wiki: Site) -> None:
    logger.info(f"Beginning to upload {len(files)} files.")
    gen = PreloadingGenerator(FilePage(original_wiki, f) for f in files)
    counter = 0
    for old_page in gen:
        old_page: FilePage
        file_title = old_page.title(with_ns=True, underscore=True)
        new_page = FilePage(new_wiki, file_title)
        upload_source = get_upload_source(old_page)
        if upload_source is None:
            continue
        res = new_page.upload(upload_source,
                              text=old_page.text,
                              summary=f"Imported from {old_page.full_url()}")
        if res:
            counter += 1
            if counter > 0 and counter % 100 == 0:
                logger.info(f"Uploaded {counter + 1}/{len(files)} files.")
        else:
            logger.error(f"Failed to upload {file_title}.")


def upload_local_files(new_wiki: Site):
    files = [f for f in local_files_directory.iterdir() if f.is_file()]
    for f in files:
        file_title = f"File:{f.name}"
        try:
            new_page = FilePage(new_wiki, file_title)
            new_page.upload(str(f.absolute()), comment=f"Uploaded as a part of T13584", ignore_warnings=False)
        except Exception as e:
            logger.error(f"Failed to upload {file_title}: {e}")


def main():
    parser = ArgumentParser()
    parser.add_argument("--original", type=str, default=None, help="Url of original wiki.")
    parser.add_argument("--new", type=str, default=None, help="Url of new wiki.")
    parser.add_argument("-i", "--images", dest="images", type=str, default=None,
                        help="Local images directory. The program can use images from this directory instead of"
                             "the original wiki, which helps reduce requests made to the original wiki.")
    parser.add_argument("-l", "--local", action="store_true",
                        help="Only import images that exist locally.")

    args = parser.parse_args()
    if args.new is not None:
        new_wiki = Site(url=args.new)
    else:
        new_wiki = Site(code="new")
    new_wiki.login()
    global local_files_directory
    if args.images:
        local_files_directory = Path(args.images)
        assert local_files_directory.exists(), f"{local_files_directory} does not exist"
    local_only = args.local
    if local_only:
        assert local_files_directory is not None
        upload_local_files(new_wiki)
        return
    if args.original:
        original_wiki = Site(url=args.original)
    else:
        original_wiki = Site(code="original")
    all_files = get_original_wiki_files(original_wiki)
    miraheze_files = get_miraheze_wiki_files(new_wiki)
    files_needing_upload = all_files.difference(miraheze_files)
    upload_files(list(files_needing_upload), original_wiki, new_wiki)


if __name__ == "__main__":
    main()
