import pickle
import re
import subprocess
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path

import requests
from pywikibot import Site, FilePage
from pywikibot.data.api import ListGenerator
from pywikibot.pagegenerators import GeneratorFactory, PreloadingGenerator

from utils.general_utils import cache_dir, get_logger

local_files_directory: Path | None = None

logger = get_logger("importer")

def get_files_on_wiki(site: Site) -> set[str]:
    gen = GeneratorFactory(site)
    gen.handle_args(['-start:File:!'])
    gen = gen.getCombinedGenerator()
    result: set[str] = set()
    for p in gen:
        p: FilePage
        result.add(p.title(with_ns=True, underscore=True))
        if len(result) % 500 == 0:
            logger.info(f"{len(result)} pages processed")
    return result


def load_cache_or_fetch(cache_file: Path, fetch_function: Callable):
    if not cache_file.exists():
        result = fetch_function()
        with open(cache_file, "wb") as f:
            pickle.dump(result, f)
    else:
        result = pickle.load(open(cache_file, "rb"))
    return result


def get_original_wiki_files(original_wiki: Site) -> set[str]:
    """
    Retrieve a set of file page titles from the original wiki.
    Results are cached on disk so that later tries do not request
    the full list of files.
    :return:
    """
    cache_file = cache_dir / "original_images.pickle"
    return load_cache_or_fetch(cache_file, lambda: get_files_on_wiki(original_wiki))


def get_miraheze_wiki_files(new_wiki: Site) -> set[str]:
    logger.info("Retrieving miraheze wiki files...")
    cache_file = cache_dir / "mh_wiki_files.pickle"
    return load_cache_or_fetch(cache_file, lambda: get_files_on_wiki(new_wiki))


def download_file(url: str, local_file: Path):
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def get_upload_source(old_page: FilePage) -> Path | None:
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
            return local_file
    local_file_dir = cache_dir / "images"
    local_file_dir.mkdir(parents=True, exist_ok=True)
    local_file = local_file_dir / file_name
    try:
        download_file(old_page.get_file_url(), local_file)
        return local_file
    except Exception as e:
        logger.error(f"Error downloading {file_name}: {e}")
        return None

def upload_file(f: Path,
                new_wiki: Site,
                text: str = "",
                comment: str = "Batch image upload",
                mime_retry: bool = False,
                exists_normalized_retry: bool = False,
                redirect_duplicate: bool = False,
                ignore_filename_prefix: bool = False) -> bool:
    file_title = f"File:{f.name}"
    ignore_warnings = False
    while True:
        try:
            new_page = FilePage(new_wiki, file_title)
        except Exception as e:
            logger.error(f"Failed to create file page {file_title} due to {e}")
            return False
        if new_page.exists():
            return False
        try:
            new_page.upload(str(f.absolute()), comment=comment, text=text, ignore_warnings=ignore_warnings)
            f.unlink()
            return True
        except Exception as e:
            if "MIME" in str(e) and mime_retry:
                logger.warning(f"Mime type mismatch for {file_title}, converting to perform a try")
                temp_file = cache_dir / f"temp{f.suffix}"
                temp_file.unlink(missing_ok=True)
                p = subprocess.run(["magick", f, temp_file],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                if p.returncode == 0:
                    f = temp_file
                    mime_retry = False
                    continue
            if "exists-normalized" in str(e) and exists_normalized_retry:
                exists_normalized_retry = False
                ignore_warnings = True
                continue
            if "duplicate" in str(e) and redirect_duplicate:
                match = re.search(r"a duplicate of \['([^']+)'[,\]]", str(e))
                assert match is not None, f"Failed to match error {e}"
                redirect_target = FilePage(new_wiki, match.group(1))
                new_page.set_redirect_target(redirect_target,
                                             summary="Redirect duplicate file page",
                                             create=True)
                f.unlink()
                return True
            if ("thumb-name" in str(e) or "bad-prefix" in str(e) in str(e)) and ignore_filename_prefix:
                ignore_filename_prefix = False
                ignore_warnings = True
                continue
            logger.error(f"Failed to upload {file_title}: {e}")
            return False


def has_valid_extension(wiki: Site, file_name: str) -> bool:
    try:
        fp = FilePage(wiki, file_name)
        return True
    except Exception:
        return False


def upload_files(files: list[str], original_wiki: Site, new_wiki: Site, comment: str = "Batch import file") -> None:
    logger.info(f"Beginning to upload {len(files)} files.")
    gen = PreloadingGenerator(FilePage(original_wiki, f)
                              for f in files
                              if has_valid_extension(original_wiki, f))
    counter = 0
    for old_page in gen:
        old_page: FilePage
        if not old_page.exists():
            logger.warning(f"{old_page} does not exist on the original wiki")
            continue
        upload_source = get_upload_source(old_page)
        if upload_source is None:
            continue
        res = upload_file(upload_source, new_wiki, comment=comment, text=old_page.text,
                          exists_normalized_retry=True,
                          mime_retry=True,
                          redirect_duplicate=True,
                          ignore_filename_prefix=True)
        if res:
            counter += 1
            if counter > 0 and counter % 100 == 0:
                logger.info(f"Uploaded {counter + 1}/{len(files)} files.")

def confirm(question: str) -> None:
    input(question + " Press enter to continue...")

def upload_local_files(new_wiki: Site, comment: str = "batch file upload"):
    confirm(f"Will flood {new_wiki.base_url('')} with image imports.")
    existing_files = get_miraheze_wiki_files(new_wiki)
    files = [f
             for f in local_files_directory.iterdir()
             if f.is_file() and "File:" + f.name.replace(" ", "_") not in existing_files]
    failed_dir = local_files_directory / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    confirm(f"{len(files)} files will be uploaded.")
    for f in files:
        res = upload_file(f, new_wiki, comment=comment, exists_normalized_retry=True, mime_retry=True)
        if not res:
            f.rename(failed_dir / f.name)


def get_wanted_files(new_wiki: Site) -> set[str]:
    def generate_page_set():
        gen = GeneratorFactory(new_wiki)
        gen.handle_args(['-querypage:Wantedfiles', '-ns:File'])
        gen = gen.getCombinedGenerator(preload=False)
        result: set[str] = set()
        for page in gen:
            print(page.title())
            result.add(page.title(with_ns=True, underscore=True))
        return result

    cache_file = cache_dir / "wanted_files.pickle"
    return load_cache_or_fetch(cache_file, generate_page_set)


def generate_all_used_files(new_wiki: Site) -> set[str]:
    gen = ListGenerator(listaction="allfileusages",
                        site=new_wiki,
                        afunique=True,
                        afprop="title")
    result: set[str] = set()
    for row in gen:
        title: str = row['title']
        result.add(title.replace(' ', '_'))
        if len(result) % 500 == 0:
            logger.info(f"{len(result)} file usages found")
    return result


def get_all_file_usage(new_wiki: Site) -> set[str]:
    cache_file = cache_dir / "all_file_usage.pickle"
    return load_cache_or_fetch(cache_file, lambda: generate_all_used_files(new_wiki))


def main():
    parser = ArgumentParser()
    parser.add_argument("--original", type=str, default=None, help="Url of original wiki.")
    parser.add_argument("--new", type=str, default=None, help="Url of new wiki.")
    parser.add_argument("-i", "--images", dest="images", type=str, default=None,
                        help="Local images directory. The program can use images from this directory instead of"
                             "the original wiki, which helps reduce requests made to the original wiki.")
    parser.add_argument("-m", "--mode", type=str, required=True,
                        choices=["local", "wanted", "allfileusage", "all"],
                        help="local: only upload images in the local repository"
                             "wanted: only import images that are on Special:WantedFiles\n"
                             "allfileusage: use query api's allfileusage to look up all wanted files\n"
                             "all: all files on the fandom wiki")
    parser.add_argument("-s", "--summary", type=str, default="Batch file import")

    args = parser.parse_args()
    if args.new is not None:
        if "http" in args.new:
            new_wiki = Site(url=args.new)
        else:
            new_wiki = Site(code=args.new)
    else:
        new_wiki = Site(code="new")
    new_wiki.login()
    global local_files_directory
    if args.images:
        local_files_directory = Path(args.images)
        assert local_files_directory.exists(), f"{local_files_directory} does not exist"
    mode = args.mode
    local_only = mode == "local"
    if local_only:
        assert local_files_directory is not None
        print("Uploading local files only")
        upload_local_files(new_wiki, comment=args.summary)
        return
    if args.original:
        original_wiki = Site(url=args.original)
    else:
        original_wiki = Site(code="original")
    if mode == "wanted":
        all_files = get_wanted_files(new_wiki)
    elif mode == "allfileusage":
        all_files = get_all_file_usage(new_wiki)
    elif mode == "all":
        all_files = get_original_wiki_files(original_wiki)
    else:
        raise Exception(f"Unknown mode {mode}")
    miraheze_files = get_miraheze_wiki_files(new_wiki)
    files_needing_upload = all_files.difference(miraheze_files)
    upload_files(list(files_needing_upload), original_wiki, new_wiki, comment=args.summary)


if __name__ == "__main__":
    main()
