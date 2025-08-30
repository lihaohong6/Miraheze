from pywikibot.pagegenerators import GeneratorFactory


def main():
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


if __name__ == "__main__":
    main()
