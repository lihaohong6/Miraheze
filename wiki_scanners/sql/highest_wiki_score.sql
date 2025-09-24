with stats as (select
    db_name,
    json_extract(ws.data, '$.active_users') as au,
    json_extract(ws.data, '$.articles') as articles,
    json_extract(ws.data, '$.pages') as pages,
    json_extract(ws.data, '$.edits') as edits
from wiki_statistics ws)
select
    stats.db_name,
    all_wikis.site_name,
    round(au * au * 10 + articles + pages * 0.1 + sqrt(edits), 0) as score
from
    stats join all_wikis on stats.db_name = all_wikis.db_name
order by score desc ;
