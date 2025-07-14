from pywikibot.pagegenerators import GeneratorFactory

from extension.extension_utils import beta


def main():
    gen = GeneratorFactory(beta())
    gen.handle_args(['-start:!', r'-grepnot:(Auto|Manual)Test', r'-titleregexnot:/'])
    gen = gen.getCombinedGenerator()
    print(list(p.title() for p in gen))

if __name__ == "__main__":
    main()