import json

from pywikibot import Page

from utils.general_utils import meta, save_json_page


class JsonPage:
    page: Page
    data: dict

    def __init__(self, title: str):
        self.page = Page(meta(), title)
        if self.page.exists():
            self.data = json.loads(self.page.text)
        else:
            self.data = {}

    def set(self, key, value, override: bool = True):
        if key not in self.data or override:
            self.data[key] = value

    def save(self):
        save_json_page(self.page, self.data)