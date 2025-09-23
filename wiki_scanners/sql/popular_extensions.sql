SELECT je.value AS item, COUNT(*), sum(json_extract(wiki_statistics.data, '$.active_users')) AS occurrences
FROM wiki_extensions
         JOIN wiki_statistics on wiki_extensions.db_name = wiki_statistics.db_name
         JOIN json_each(wiki_extensions.data, '$.extensions') AS je
GROUP BY je.value
ORDER BY occurrences DESC;