from services.cf_analytics import update_cf_analytics
from services.wiki_count_tracking import update_wiki_counts
from services.wiki_request_tracking import update_wiki_requests


def main():
    update_cf_analytics()
    update_wiki_requests()
    update_wiki_counts()


if __name__ == "__main__":
    main()
