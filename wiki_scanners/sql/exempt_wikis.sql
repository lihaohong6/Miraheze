select all_wikis.db_name,
       site_name,
       json_extract(ws.data, '$.active_users') as au,
       json_extract(ws.data, '$.articles')     as ac,
       json_extract(ws.data, '$.pages')        as ap
from all_wikis
         join wiki_statistics ws on ws.db_name = all_wikis.db_name
where state = 'exempt'
order by au desc, ac desc, ap desc;