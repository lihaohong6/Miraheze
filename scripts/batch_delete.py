from pywikibot import Site
from pywikibot.pagegenerators import GeneratorFactory


def delete_imports():
    gen = GeneratorFactory()
    gen.handle_args(['-start:Template:!'])
    gen = gen.getCombinedGenerator()
    for page in gen:
        contributors = page.contributors()
        # only list pages where rj is not the only contributor
        non_rj = False
        for contributor in contributors:
            if contributor == 'Rodejong':
                continue
            if contributor in {"FANDOM"}:
                non_rj = True
                continue
            if contributor.startswith("wikia:"):
                non_rj = True
                continue
            break
        else:
            if non_rj:
                print(page.full_url() + "?action=history")


def is_language_code(code: str):
    from langcodes import Language
    code = code.split('-')[0]
    try:
        lang = Language.make(language=code)
        return lang.is_valid()
    except:
        return False

def delete_translations():
    s = Site()
    s.login()
    prefixes = []
    while True:
        prefix = input("Prefix to remove translations from: ")
        if prefix.strip() == "":
            break
        prefixes.append(prefix)

    for prefix in prefixes:
        prefix += "/"
        prefix = prefix.replace(" ", "_")
        gen = GeneratorFactory()
        gen.handle_args([f'-prefixindex:{prefix}'])
        gen = gen.getCombinedGenerator()
        for page in gen:
            last_segment = page.title(underscore=True).replace(prefix, "")
            if not is_language_code(last_segment):
                print(page.title() + " is not a language page")
                continue
            print(f"Deleting {page.title()}")
            s.delete(page, reason="Delete orphan translation pages after the original is unmarked for translation")


if __name__ == "__main__":
    delete_translations()
