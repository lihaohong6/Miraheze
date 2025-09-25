SELECT
    json_extract(wiki_extensions.data, '$.settings.wgDefaultSkin') as skin,
    count(*) as count,
    sum(json_extract(wiki_statistics.data, '$.active_users')) as au_count
FROM wiki_extensions
         JOIN wiki_statistics on wiki_extensions.db_name = wiki_statistics.db_name
GROUP BY skin
order by count desc ;