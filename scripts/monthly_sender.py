from argparse import ArgumentParser

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator
from wikitextparser import parse

from utils.general_utils import meta


def parse_links(page: Page) -> list[str]:
    parsed = parse(page.text)
    for section in parsed.sections:
        if section.title and "talk" in section.title.lower():
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
    page = Page(meta(), args.page)
    talk_pages = [Page(meta(), title) for title in parse_links(page)]
    talk_pages = list(PreloadingGenerator(talk_pages))
    assert all(p.namespace().id == 3 for p in talk_pages)
    date = args.date
    text = f"""==Miraheze Monthly - [[User:Raidarr/Miraheze Monthly/{date}|{date} issue]]==
{{{{:User:Raidarr/Miraheze Monthly/{date}}}}}
<div style="text-align: right"><span style="display: none">[[User:%s]]</span>Delivered by ~~~~</div>"""
    for page in talk_pages:
        if page.text.strip() != "":
            page.text.rstrip() + "\n\n"
        username = page.title().split("/")[0].split(":")[1]
        user_message = text.replace("%s", username)
        page.text += user_message
        summary = args.summary
        page.save(summary=summary)


if __name__ == '__main__':
    main()
