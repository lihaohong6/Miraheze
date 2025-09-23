from communities.wiki_list import get_item_id_from_wiki
from utils.wiki_scanner import fetch_all_mh_wikis, run_wiki_scanner_query


def list_wikis_by_active_users():
    wikis = dict((w.db_name, w) for w in fetch_all_mh_wikis())
    print('<table class="wikitable sortable">')
    print('<tr>')
    print('<th>Name</th><th>Active users</th><th style="word-break: break-word">wgActiveUserDays</th>')
    print('</tr>')
    for wiki in run_wiki_scanner_query("most_active_users")[:800]:
        db, name, au_days, active_users = wiki
        if active_users < 4:
            continue
        item_id = get_item_id_from_wiki(wikis[db])
        if item_id is None:
            item = ""
        else:
            item = f" ([[Item:{item_id}|{item_id}]])"
        lines = [
            "<tr>",
            f"<td>[[mh:{db[:-4]}|{name}]]{item}</td>"
        ]
        au_days = int(au_days)
        style = ""
        if au_days != 30:
            style = 'style="background-color: var(--background-color-disabled, #dadde3)"'
        lines.append(f"<td {style}>{active_users}</td>")
        lines.append(f"<td>{'-' if au_days == 30 else au_days}</td>")
        lines.append(f"</tr>")
        print("\n".join(lines))
    print("</table>")


if __name__ == '__main__':
    list_wikis_by_active_users()
