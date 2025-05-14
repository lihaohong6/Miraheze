import shutil
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup, PageElement, Tag
from requests import Session

from utils import cache_dir, get_logger

LENGTH_LIMIT = 0.2 * 1024 * 1024

xml_cache_dir = cache_dir / "xml"
xml_cache_dir.mkdir(parents=True, exist_ok=True)

logger = get_logger("import_sharder")

def make_new_soup(old_root: BeautifulSoup, siteinfo: PageElement, pages: list[Tag] = []) -> tuple[BeautifulSoup, Tag]:
    new_soup = BeautifulSoup(features="lxml-xml")
    new_root = new_soup.new_tag("mediawiki", attrs=old_root.attrs)
    new_soup.append(new_root)
    new_root.append(siteinfo)
    for p in pages:
        new_root.append(p)
    return new_soup, new_root


def soup_to_string(soup: BeautifulSoup) -> str:
    result = soup.prettify()
    return "\n".join(result.split("\n")[1:])


def shard_file(original_file: Path) -> list[Path]:
    soup = BeautifulSoup(open(original_file, mode="rb").read(), features="lxml")
    root = soup.find("mediawiki")
    siteinfo = root.find("siteinfo")

    def find_subpages() -> list[Tag]:
        children = [c for c in root.children if isinstance(c, Tag)]
        assert children[0].name == siteinfo.name
        result = children[1:]
        logger.info(f"{len(result)} pages found in {original_file.name}")
        for p in result:
            page_name = p.name
            if "page" in page_name:
                continue
            logger.error(f"It seems that a non-page element is found. The tag is {page_name}. Aborting.")
            exit(1)
        return result
    pages = find_subpages()

    i = 0
    partition_number = 0
    files = []
    while i < len(pages):
        new_soup, new_root = make_new_soup(root, siteinfo)

        current_pages = []
        while i < len(pages):
            page = pages[i]
            new_root.append(page)
            xml_str = soup_to_string(new_soup)
            length = len(xml_str.encode("utf-8"))
            if length < LENGTH_LIMIT:
                i += 1
                current_pages.append(page)
                continue
            new_soup, new_root = make_new_soup(root, siteinfo, current_pages)
            break

        partition_number += 1
        file_path = xml_cache_dir / f"{original_file.stem}_{partition_number}.xml"
        xml_str = soup_to_string(new_soup)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logger.info(f"Written to {file_path.name}, which has {len(current_pages)} pages in it.")
        files.append(file_path)

    return files


@dataclass
class SessionInfo:
    url: str
    session: Session
    csrf_token: str


def get_session_and_token(url: str, username: str, password: str) -> SessionInfo:
    # 1. Start a session
    session = requests.Session()

    # 2. Get login token
    params = {
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    }
    r = session.get(url, params=params)
    login_token = r.json()["query"]["tokens"]["logintoken"]

    # 3. Log in
    login_params = {
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "lgtoken": login_token,
        "format": "json"
    }
    r = session.post(url, data=login_params)

    # 4. Get CSRF token
    params = {
        "action": "query",
        "meta": "tokens",
        "format": "json"
    }
    r = session.get(url, params=params)
    csrf_token = r.json()["query"]["tokens"]["csrftoken"]
    return SessionInfo(url, session, csrf_token)


def import_xml(file: Path, prefix: str, summary: str, session_info: SessionInfo) -> bool:
    # 5. Upload the XML file using multipart/form-data
    with open(file, "rb") as f:
        files = {
            "xml": ("dump.xml", f, "application/xml")
        }
        data = {
            "action": "import",
            "format": "json",
            "token": session_info.csrf_token,
            "interwikiprefix": prefix,  # optional
            "summary": summary,  # optional
        }
        response = session_info.session.post(session_info.url, data=data, files=files)

    if response.status_code != 200:
        logger.error(f"Failed to import {file.name}: {response}")
        return False
    response = response.json()
    if 'error' in response:
        logger.error(f"Failed to import {file.name}: {response}")
        return False
    return True


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands",
                                       dest="command",
                                       required=True,
                                       description="valid commands",
                                       help='subcommand help')

    # create the parser for the "a" command
    shard_parser = subparsers.add_parser('shard', help='Shard a single xml file into multiple xml files.')
    shard_parser.add_argument('-f', '--file', required=True, type=str)

    import_parser = subparsers.add_parser('import',
                                          help='Import xml files in the cache, which is assumed to be sharded.')
    import_parser.add_argument('--url', required=True, type=str,
                               help='Api entry point of the wiki (found on [[Special:Version]])')
    import_parser.add_argument('--username', required=True, type=str)
    import_parser.add_argument('--password', required=True, type=str)
    import_parser.add_argument('--prefix', required=True, type=str, help="Interwiki prefix")
    import_parser.add_argument('--summary', default="Import xml dump", type=str)

    clean_parser = subparsers.add_parser('clean', help='Clean xml files in the cache.')
    args = parser.parse_args()

    def shard_wrapper():
        file = Path(args.file)
        results = shard_file(file)
        logger.info(f"Sharded the original into {len(results)} files")
        logger.info(f"These filse are: {', '.join(r.name for r in results)}")

    def import_xml_wrapper():
        files = list(xml_cache_dir.glob("*.xml"))
        logger.info(f"Found {len(files)} xml files in the cache")
        session = get_session_and_token(args.url, args.username, args.password)
        for file in files:
            logger.info(f"Processing {file.name}")
            result = import_xml(file, args.prefix, args.summary, session)
            if result:
                logger.info(f"Successfully imported {file.name}, deleting it from the cache")
                file.unlink()
            else:
                logger.error(f"Failed to import {file.name}. Aborting...")
                exit(1)


    def clean():
        shutil.rmtree(xml_cache_dir, ignore_errors=True)
        logger.info("Removed xml cache.")

    dispatcher = {
        "shard": shard_wrapper,
        "import": import_xml_wrapper,
        "clean": clean
    }
    dispatcher[args.command]()

if __name__ == '__main__':
    main()
