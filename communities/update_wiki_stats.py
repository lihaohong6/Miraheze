import json
from dataclasses import dataclass
from functools import cache

from wikibaseintegrator import wbi_login, WikibaseIntegrator, datatypes
from wikibaseintegrator.entities import ItemEntity
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_helpers import search_entities

from communities.bot_oauth import bot_passwords
from communities.wiki_db import insert_item_id_for_wiki, db_fetch, preload_items
from utils.general_utils import user_agent, MirahezeWiki, throttle
from utils.wiki_scanner import fetch_all_mh_wikis, run_wiki_scanner_query
from wiki_scanners.extension_statistics import get_wiki_extension_statistics, WikiExtensionStatistics
from wiki_scanners.site_statistics import get_wiki_site_statistics, WikiSiteStatistics


@dataclass
class MirahezeWikiStats:
    wiki: MirahezeWiki
    extensions: WikiExtensionStatistics | None
    statistics: WikiSiteStatistics | None


@cache
def find_entity_by_exact_label(label: str, entity_type: str = 'item') -> str | None:
    # Search for entities with the given label
    results = search_entities(
        search_string=label,
        search_type=entity_type,
        max_results=5,
        dict_result=True,
        allow_anonymous=True
    )

    # Filter for exact label matches
    exact_matches = []
    for result in results:
        label_candidates: list[str] = [result['label'].lower()]
        aliases = result.get('aliases', [])
        if aliases:
            label_candidates.extend(alias.lower() for alias in aliases)
        if any(candidate == label.lower() for candidate in label_candidates):
            exact_matches.append(result)

    # Return the first exact match if found
    if len(exact_matches) == 1:
        return exact_matches[0]['id']
    elif len(exact_matches) > 1:
        raise RuntimeError("More than one match found")
    else:
        return None


def get_all_stats() -> dict[str, MirahezeWikiStats]:
    result: dict[str, MirahezeWikiStats] = {}
    wikis = fetch_all_mh_wikis()
    ext_statistics = get_wiki_extension_statistics(read_only=True)
    site_statistics = get_wiki_site_statistics(read_only=True)
    for wiki in wikis:
        db = wiki.db_name
        result[db] = MirahezeWikiStats(
            wiki=wiki,
            extensions=ext_statistics.get(db, None),
            statistics=site_statistics.get(db, None)
        )
    return result


def update_item_with_wiki_stats(wbi: WikibaseIntegrator,
                                item: ItemEntity,
                                wiki_stats: MirahezeWikiStats):
    if wiki_stats.wiki is None or wiki_stats.extensions is None or wiki_stats.statistics is None:
        return
    original_item = item.get_json()
    wiki = wiki_stats.wiki
    db_name = wiki.db_name
    name = wiki.site_name
    url = wiki.url
    item.labels.set('en', name)
    aliases = item.aliases.get('en')
    if aliases is not None:
        aliases = [a.value for a in aliases if "https://" not in a]
    else:
        aliases = []
    if db_name not in aliases:
        aliases.append(db_name)
    item.aliases.set('en', aliases, action_if_exists=ActionIfExists.REPLACE_ALL)

    if wiki.creation_date is not None:
        claim = datatypes.Time(prop_nr='P19', time="+" + wiki.creation_date.split('T')[0] + "T00:00:00Z")
        item.claims.add(claim)

    string_claims = {
        'P12': db_name,
        'P15': wiki.language
    }

    for k, v in string_claims.items():
        claim = datatypes.String(prop_nr=k, value=v)
        item.claims.add(claim)

    claim_url = datatypes.URL(prop_nr='P11', value=url)
    item.claims.add(claim_url)

    item_claims: dict[str, str | int] = {
        # always of type wiki
        'P13': 25
    }
    if wiki.category:
        category_id = find_entity_by_exact_label(wiki.category)
        if category_id:
            item_claims['P17'] = category_id
        else:
            print(f"Category {wiki.category} cannot be found on the site")
    for k, v in item_claims.items():
        claim = datatypes.Item(prop_nr=k, value=v)
        item.claims.add(claim)

    statistics = wiki_stats.statistics
    quantity_claims = {
        'P3': statistics.pages,
        'P4': statistics.articles,
        'P5': statistics.edits,
        'P6': statistics.images,
        'P7': statistics.users,
        'P8': statistics.active_users,
    }

    for k, v in quantity_claims.items():
        claim = datatypes.Quantity(prop_nr=k, amount=v)
        item.claims.add(claim)

    # No modifications are made
    if json.dumps(item.get_json(), sort_keys=True) == json.dumps(original_item, sort_keys=True):
        return

    try:
        throttle(0.5)
        item.write(is_bot=True)
    except Exception as e:
        print(e)
        print(f"Failed to update for {wiki.db_name} ({wiki.site_name})")


def update_site_statistics(wbi: WikibaseIntegrator):
    stats = get_all_stats()
    most_active_wikis = [r[0] for r in run_wiki_scanner_query("most_active_users")][:1000]
    existing_wikis = db_fetch()
    item_id_to_db = dict((v, k) for k, v in existing_wikis.items())
    for prop, item in preload_items(list(item_id_to_db.keys()), wbi=wbi):
        item: ItemEntity
        db_name = item_id_to_db[prop]
        update_item_with_wiki_stats(wbi, item, stats[db_name])
    for db_name in most_active_wikis:
        if db_name in existing_wikis:
            continue
        stat = stats[db_name]
        if stat.statistics.active_users < 10 or stat.statistics.articles < 100:
            continue
        item = wbi.item.new()
        update_item_with_wiki_stats(wbi, item, stat)
        if item.id is not None:
            insert_item_id_for_wiki(stat.wiki, item.id)


def main():
    wbi_config['MEDIAWIKI_API_URL'] = 'https://communities.miraheze.org/w/api.php'
    wbi_config['MEDIAWIKI_REST_URL'] = 'https://communities.miraheze.org/w/api.php'
    wbi_config['WIKIBASE_URL'] = ''
    wbi_config['USER_AGENT'] = user_agent
    login_instance = wbi_login.Login(
        user=bot_passwords[0],
        password=bot_passwords[1],
        user_agent=user_agent)
    wbi = WikibaseIntegrator(login=login_instance)
    update_site_statistics(wbi=wbi)


if __name__ == '__main__':
    main()
