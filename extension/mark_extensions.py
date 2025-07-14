from functools import cache

from pywikibot import Site, Page
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory

from extension.extension_utils import lower_to_upper

GLOBAL_EXTENSIONS = [
    'AbuseFilter',
    'AntiSpoof',
    'BetaFeatures',
    'CentralNotice',
    'CheckUser',
    'CreateWiki',
    'CookieWarning',
    'ConfirmEdit',
    'DataDump',
    'DiscordNotifications',
    'DismissableSiteNotice',
    'Echo',
    'EventBus',
    'EventLogging',
    'EventStreamConfig',
    'GlobalCssJs',
    'GlobalNewFiles',
    'ImportDump',
    'InterwikiDispatcher',
    'IPInfo',
    'LoginNotify',
    'ManageWiki',
    'MatomoAnalytics',
    'MirahezeMagic',
    'MobileDetect',
    'Nuke',
    'OATHAuth',
    'OAuth',
    'ParserFunctions',
    'ParserMigration',
    'QuickInstantCommons',
    'RottenLinks',
    'Scribunto',
    'SpamBlacklist',
    'TitleBlacklist',
    'TorBlock',
    'WebAuthn',
    'WikiDiscover',
    'WikiEditor',
    'CLDR', ]

DEFAULT_EXTENSIONS = [
    'categorytree',
    'cite',
    'citethispage',
    'codeeditor',
    'codemirror',
    'darkmode',
    'globaluserpage',
    'minervaneue',
    'mobilefrontend',
    'purge',
    'syntaxhighlight_geshi',
    'templatestyles',
    'textextracts',
    'urlshortener',
    'wikiseo',
]

@cache
def get_default_extensions() -> set[str]:
    return set(GLOBAL_EXTENSIONS).union(set(lower_to_upper(e) for e in DEFAULT_EXTENSIONS))


def main():
    s = Site('beta')
    s.login()
    gen = GeneratorFactory(s)
    gen.handle_args(['-cat:Automatic tests', '-cat:Manual tests', '-ns:0'])
    gen = gen.getCombinedGenerator(preload=True)
    pages: dict[str, Page] = dict((p.title(), p) for p in gen)
    default_extensions = get_default_extensions()
    for title, page in pages.items():
        setattr(page, "_bot_may_edit", True)
        edited = False
        extension_template = "{{DefaultExtension}}"
        if title in get_default_extensions():
            if extension_template not in page.text:
                page.text = extension_template + page.text
                edited = True
            default_extensions.remove(title)
        else:
            if extension_template in page.text:
                page.text = page.text.replace(extension_template, "")
                edited = True
        if edited:
            page.save(summary="batch mark extensions as default")
    if len(default_extensions) > 0:
        print("Some extensions were not covered")
        print("\n".join(default_extensions))


if __name__ == "__main__":
    main()
