select all_wikis.db_name as db,
       all_wikis.site_name,
       json_extract(wiki_statistics.data, '$.articles')
                         as articles,
       json_extract(wiki_statistics.data, '$.pages')
                         as pages
from wiki_statistics
         join all_wikis on wiki_statistics.db_name = all_wikis.db_name
order by articles DESC;