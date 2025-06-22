import re
import shutil
from argparse import ArgumentParser
from dataclasses import dataclass
from enum import Enum
from json import JSONDecodeError
from pathlib import Path

from utils.general_utils import cache_dir, get_logger, SessionInfo, get_csrf_token, login, headers

# Use 200MB for Special:RequestImport. Use 2MB for Special:Import.
# Files absolutely cannot be larger than this.
# Leave a bit of room for header
LENGTH_HARD_LIMIT = 200 * 1024 * 1000
# Files should target this length to leave extra room for miscellaneous stuff.
LENGTH_TARGET_LIMIT = 200 * 1000 * 1000

xml_cache_dir = cache_dir / "xml"
xml_cache_dir.mkdir(parents=True, exist_ok=True)

logger = get_logger("import_sharder")


def str_size(string: str | list[str]) -> int:
    if isinstance(string, list):
        return sum((str_size(s) for s in string), 0)

    return len(string.encode("utf-8"))


@dataclass
class Revision:
    lines: list[str]

    def __str__(self):
        return "".join(self.lines)

    @property
    def size(self):
        return str_size(self.lines)


@dataclass
class ParsedPage:
    start_tag: str
    revisions: list[Revision]
    end_tag: str

    @property
    def size(self):
        return str_size(self.start_tag) + str_size(self.end_tag) + sum(r.size for r in self.revisions)

    def __str__(self):
        return "".join([self.start_tag,
                          ''.join(str(r) for r in self.revisions),
                          self.end_tag])


@dataclass
class ParsedFile:
    template_start: str
    pages: list[ParsedPage]
    template_end: str

    def __str__(self):
        return "".join([self.template_start,
                          ''.join(str(p) for p in self.pages),
                          self.template_end])


def parse_page(lines: list[str]) -> ParsedPage:
    revisions = []
    current_revision = []
    revision_start = 0
    while revision_start < len(lines):
        if re.search("<.*revision.*>", lines[revision_start]):
            break
        revision_start += 1
    else:
        logger.error("Cannot find start of revision for this page. Aborting.")
        exit(1)
    for line in lines[revision_start:-1]:
        current_revision.append(line)
        if re.search(r"</(ns\d+:)?revision.*>", line) is not None:
            revisions.append(Revision(current_revision))
            current_revision = []
    return ParsedPage("".join(lines[:revision_start]), revisions, lines[-1])


def parse_lines(lines: list[str]) -> ParsedFile:
    class ParserState(Enum):
        START = 1
        PAGES = 2

    state = ParserState.START
    template_start = []
    cur_page = []
    pages: list[ParsedPage] = []
    template_end = None

    for line in lines:
        if state == ParserState.START:
            template_start.append(line)
            if "</siteinfo>" in line:
                state = ParserState.PAGES
        elif state == ParserState.PAGES:
            if "</mediawiki>" in line:
                template_end = line
                continue
            cur_page.append(line)
            if re.search(r"</(ns\d+:)?page.*>", line) is not None:
                pages.append(parse_page(cur_page))
                cur_page = []
    if state == ParserState.START:
        logger.error(f"No </siteinfo> tag found in xml file. Aborting.")
        exit(1)
    if template_end is None:
        logger.error("No </mediawiki> tag found in xml file. Aborting.")
        exit(1)
    return ParsedFile("".join(template_start), pages, template_end)


T = ParsedPage | Revision
def partition_by_size(original: list[T], max_size: int) -> list[list[T]]:
    result = []
    current_parts = []
    current_size = 0

    for part in original:
        if part.size > max_size:
            if isinstance(part, Revision):
                logger.error(f"A page has size {part.size}, greater than the max allowed size. Aborting.")
                exit(1)
            else:
                remaining_size = max_size - str_size(part.start_tag) - str_size(part.end_tag)
                assert remaining_size > 0
                split_revisions = partition_by_size(part.revisions, max_size)
                for revision_group in split_revisions:
                    result.append([ParsedPage(part.start_tag, revision_group, part.end_tag)])
                continue
        if current_size + part.size > max_size:
            result.append(current_parts)
            current_parts = []
            current_size = 0
        current_parts.append(part)
        current_size += part.size
    if current_size > 0:
        result.append(current_parts)
    return result


def parse_file(file: Path) -> ParsedFile:
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    logger.info(f"File {file.name} loaded.")
    return parse_lines(lines)


def shard_file(original_file: Path) -> list[Path]:
    parsed_file = parse_file(original_file)
    logger.info(f"File {original_file.name} parsed.")

    files = []
    pages = parsed_file.pages

    remaining_size = LENGTH_TARGET_LIMIT - str_size(parsed_file.template_start) - str_size(parsed_file.template_end)
    page_groups = partition_by_size(pages, remaining_size)

    logger.info(f"File partitioned into {len(page_groups)} groups. Writing them to disk...")

    for file_number, page_group in enumerate(page_groups):
        xml_str = parsed_file.template_start + "".join(str(p) for p in page_group) + parsed_file.template_end
        assert str_size(xml_str) <= LENGTH_HARD_LIMIT, f"File {file_number} has size {str_size(xml_str)}, greater than the configured maximum."
        file_path = xml_cache_dir / f"{original_file.stem}_{file_number}.xml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logger.info(f"File {file_path.name} is created. It has {len(page_group)} pages in it.")
        files.append(file_path)

    return files


def import_xml(file: Path, prefix: str, summary: str, session_info: SessionInfo) -> bool:

    with open(file, "rb") as f:
        files = {
            "xml": ("dump.xml", f, "application/xml")
        }
        data = {
            "action": "import",
            "format": "json",
            "token": get_csrf_token(session_info.session, session_info.url),
            "interwikiprefix": prefix,  # optional
            "summary": summary,  # optional
        }
        response = session_info.session.post(session_info.url, data=data, files=files, headers=headers)

    if response.status_code != 200:
        logger.error(f"Failed to import {file.name}: {response}")
        return False
    try:
        response = response.json()
    except JSONDecodeError:
        logger.error(f"Failed to decode json for {file.name}: {response.text}")
        return False
    if 'error' in response or 'import' not in response:
        logger.error(f"Failed to import {file.name}: {response}")
        return False
    entries = response['import']
    logger.info(f"Imported {len(entries)} pages and {sum(entry['revisions'] for entry in entries)} revisions.")
    return True


def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands",
                                       dest="command",
                                       required=True,
                                       description="valid commands",
                                       help='subcommand help')

    # create the parser for the "a" command
    shard_parser = subparsers.add_parser('shard',
                                         help='Shard a single xml file into multiple xml files and store them in the cache.')
    shard_parser.add_argument('-f', '--file', required=True, type=str)

    import_parser = subparsers.add_parser('import',
                                          help='Import xml files in the cache, which are assumed to be sharded. '
                                               'Files that are successfully imported will be deleted from the cache.')
    import_parser.add_argument('--url', required=True, type=str,
                               help='Api entry point of the wiki (found on [[Special:Version]])')
    import_parser.add_argument('--username', required=True, type=str)
    import_parser.add_argument('--password', required=True, type=str)
    import_parser.add_argument('--prefix', required=True, type=str, help="Interwiki prefix")
    import_parser.add_argument('--summary', default="Import xml dump", type=str,
                               help="Summary of this import")

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
        session = login(args.url, args.username, args.password)
        for file in files:
            logger.info(f"Processing {file.name}")
            result = import_xml(file, args.prefix, args.summary, session)
            if result:
                logger.info(f"Successfully imported {file.name}, deleting it from the cache")
                file.unlink()
            else:
                logger.error(f"Failed to import {file.name}. Skpping...")
                continue

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
