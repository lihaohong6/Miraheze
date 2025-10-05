import re
from itertools import dropwhile
from time import sleep

import requests

from utils.general_utils import headers, get_logger

logger = get_logger("ssl")

def main():
    r = requests.get("https://raw.githubusercontent.com/miraheze/ssl/refs/heads/main/wikidiscover_output.yaml")
    r.raise_for_status()
    text = r.text
    urls = []
    for line in text.splitlines():
        line = line.strip()
        if line == "":
            continue
        re_match = re.search(r"(https://.*)$", line)
        if re_match is None:
            print(f"ERROR: {line} does not seem to contain a custom domain")
            continue
        url = re_match.group(1)
        urls.append(url)
    # Uncomment to resume
    # urls = list(dropwhile(lambda x: "gimkit" not in x, urls))
    for url in urls:
        test_custom_domain(url)
        sleep(0.5)


def test_custom_domain(url, retry_cloudflare: int = 2) -> None:
    try:
        response = requests.get(url, headers=headers)
        response= response.text
    except Exception as e:
        error_text = str(e)
        if "NameResolutionError" in error_text:
            logger.error(f"{url} has expired: NameResolutionError")
        else:
            logger.error(f"{url} may have expired: {error_text}")
        return

    if re.search(r"<body class=.*mediawiki ", response) is None:
        if "Cloudflare Access" in response or "grafana" in response.lower():
            if retry_cloudflare > 0:
                logger.info("got cloudflared/grafanaed. Retrying...")
                sleep((3 - retry_cloudflare) * 2)
                test_custom_domain(url, retry_cloudflare=retry_cloudflare - 1)
            else:
                logger.error(f"got cloudflared twice for {url}")
            return
        if "expired" in response.lower():
            if "namecheap" in response.lower():
                logger.warning(f"{url} has expired: namecheap")
            else:
                logger.warning(f"{url} has expired")
        else:
            logger.warning(f"{url} may no longer be a mediawiki site")
            logger.info(response[:1000].replace("\n", ""))
        return
    if "footer-mirahezeico" not in response and "Hosted by Miraheze" not in response and "meta.miraheze.org" not in response:
        logger.error(f"{url} is no longer with us")
        return
    logger.info(f"{url} seems fine")


if __name__ == "__main__":
    main()