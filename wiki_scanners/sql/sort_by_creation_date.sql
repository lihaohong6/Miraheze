select all_wikis.db_name as db,
       all_wikis.site_name,
       all_wikis.creation_date as creation,
       json_extract(ws.data, '$.active_users') as au
from all_wikis
         join wiki_statistics ws on ws.db_name = all_wikis.db_name
         join wiki_extensions on all_wikis.db_name = wiki_extensions.db_name
where au > 10 and creation_date is not NULL
order by creation_date;