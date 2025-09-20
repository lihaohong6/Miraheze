select all_wikis.db_name as db,
       all_wikis.site_name,
       CAST(coalesce(json_extract(wiki_extensions.data, '$.settings.wgActiveUserDays'), 30) as integer)
                         as active_user_days,
       json_extract(wiki_statistics.data, '$.active_users')
                         as active_users
from wiki_statistics
         join all_wikis on wiki_statistics.db_name = all_wikis.db_name
         join wiki_extensions on all_wikis.db_name = wiki_extensions.db_name
order by active_users DESC;