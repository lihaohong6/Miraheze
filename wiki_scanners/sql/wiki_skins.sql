select all_wikis.db_name as db,
       all_wikis.site_name,
       json_extract(wiki_extensions.data, '$.settings.wgDefaultSkin') as skin
from wiki_statistics
         join all_wikis on wiki_statistics.db_name = all_wikis.db_name
         join wiki_extensions on wiki_statistics.db_name = wiki_extensions.db_name
where
    skin is not null and
    skin != 'vector-2022' and
    state != 'deleted' and
    state != 'closed';