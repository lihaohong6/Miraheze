from argparse import ArgumentParser

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator
from wikitextparser import parse

from utils.general_utils import meta


def parse_links(page: Page, section_title: str) -> list[str]:
    parsed = parse(page.text)
    for section in parsed.sections:
        if section.title and section_title in section.title.lower():
            break
    else:
        return []
    text = "\n".join(line
                     for line in str(section).splitlines()
                     if line.startswith("#"))
    parsed = parse(text)
    return [link.title for link in parsed.wikilinks]


def main():
    parser = ArgumentParser()
    parser.add_argument("-p", "--page",
                        type=str,
                        help="Subscription page",
                        default="User:Raidarr/Miraheze_Monthly/subscriptions")
    parser.add_argument("-d", "--date",
                        type=str,
                        required=True,
                        help="Format: January 2025")
    parser.add_argument("-s", "--summary",
                        type=str,
                        default="Automated delivery of [[User:Raidarr/Miraheze Monthly|Miraheze Monthly]]")
    args = parser.parse_args()
    subscribers_page = Page(meta(), args.page)
    deliver_to_talk_page(subscribers_page, date=args.date, summary=args.summary)
    print_pings(subscribers_page)


def print_pings(page: Page) -> None:
    user_pages = [Page(meta(), title)
                  for title in parse_links(page, section_title="notification subscriptions")]
    user_pages = list(PreloadingGenerator(user_pages))
    for p in user_pages:
        if p.namespace().id != 2:
            print(f"Error: {p.title()} is not in user NS.")
            continue
    print("{{ping|" + "|".join(p.title(with_ns=False) for p in user_pages) + "}}")


def deliver_to_talk_page(page: Page, date: str, summary: str) -> None:
    talk_pages = [Page(meta(), title) for title in parse_links(page, "talk")]
    talk_pages = list(PreloadingGenerator(talk_pages))
    for p in talk_pages:
        if p.namespace().id != 3:
            print(f"Warning: {p.title()} is not in user talk NS.")
    text = f"""==Miraheze Monthly - [[User:Raidarr/Miraheze Monthly/{date}|{date} issue]]==
{{{{:User:Raidarr/Miraheze Monthly/{date}}}}}
<div style="text-align: right"><span style="display: none">[[User:%s]]</span>Delivered by ~~~~</div>"""
    for page in talk_pages:
        if page.text.strip() != "":
            page.text = page.text.rstrip() + "\n\n"
        if text.split("\n")[0] in page.text:
            print(f"Warning: {page.title()} already contains the current MH Monthly issue.")
            continue
        username = page.title().split("/")[0].split(":")[1]
        user_message = text.replace("%s", username)
        page.text += user_message
        page.save(summary=summary)


if __name__ == '__main__':
    main()
