select
    all_wikis.db_name,
    all_wikis.site_name,
    all_wikis.creation_date as cd,
    json_extract(ws.data, '$.articles') as ac,
    json_extract(ws.data, '$.pages') as pc,
    json_extract(ws.data, '$.files') as files,
    json_extract(ws.data, '$.edits') as edits,
    json_extract(ws.data, '$.users') as users,
    json_extract(ws.data, '$.active_users') as au
from wiki_statistics ws join all_wikis on ws.db_name = all_wikis.db_name
where all_wikis.state = 'active' or all_wikis.state = 'exempt'
order by creation_date;