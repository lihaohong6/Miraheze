from functools import cache
from typing import Generator

from wikibaseintegrator import WikibaseIntegrator, wbi_login
from wikibaseintegrator.entities import BaseEntity, ItemEntity
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_helpers import generate_entity_instances

from communities.bot_oauth import bot_passwords
from utils.general_utils import user_agent


@cache
def get_wbi():
    wbi_config['MEDIAWIKI_API_URL'] = 'https://communities.miraheze.org/w/api.php'
    wbi_config['MEDIAWIKI_REST_URL'] = 'https://communities.miraheze.org/w/api.php'
    wbi_config['WIKIBASE_URL'] = ''
    wbi_config['USER_AGENT'] = user_agent
    login_instance = wbi_login.Login(
        user=bot_passwords[0],
        password=bot_passwords[1],
        user_agent=user_agent)
    wbi = WikibaseIntegrator(login=login_instance)
    return wbi


def preload_items(titles: list[str],
                  wbi: WikibaseIntegrator = get_wbi()) -> Generator[tuple[str, ItemEntity], None, None]:
    size = 50
    chunked = [titles[i:i + size] for i in range(0, len(titles), size)]
    for chunk in chunked:
        results = generate_entity_instances(
            chunk,
            allow_anonymous=False,
            login=wbi.login,
            user_agent=user_agent)
        for r in results:
            r: tuple[str, ItemEntity]
            yield r
