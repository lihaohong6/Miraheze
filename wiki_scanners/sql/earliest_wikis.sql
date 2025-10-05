select all_wikis.db_name as db,
       all_wikis.site_name,
       all_wikis.creation_date as creation,
       json_extract(ws.data, '$.articles') as ac,
       json_extract(ws.data, '$.active_users') as au,
       all_wikis.state
from all_wikis
         join wiki_statistics ws on ws.db_name = all_wikis.db_name
         join wiki_extensions on all_wikis.db_name = wiki_extensions.db_name
where creation_date is not NULL and au > 0
order by creation_date;