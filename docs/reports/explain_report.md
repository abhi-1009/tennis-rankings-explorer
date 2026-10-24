# Query efficiency report (EXPLAIN and timings)

Generated 2026-10-24 14:03 UTC · server `8.4.8` · database `tennis_db`

Each indexed case is run twice: normally, and with `IGNORE INDEX` to simulate a table without that index. Times are the median of 6 runs and include network latency to the database, so compare the variants with each other rather than reading the absolute numbers.

## Results

| Case | Query | Variant | Access type | Index used | Est. rows | Median ms |
|---|---|---|---|---|---|---|
| A | Venues in a country | with index | ref | idx_venues_country | 65 | 14.89 |
| A | Venues in a country | index ignored | ALL | none | 4200 | 17.64 |
| B | Players of one country | with index | ref | idx_competitors_country | 10 | 10.8 |
| B | Players of one country | index ignored | ALL | none | 1000 | 11.73 |
| C | Top 5 ranks | with index | range | idx_rankings_rank | 10 | 10.43 |
| C | Top 5 ranks | index ignored | ALL | none | 1000 | 11.13 |
| D | Doubles competitions | with index | ref | idx_competitions_type | 3051 | 76.77 |
| D | Doubles competitions | index ignored | ALL | none | 6867 | 100.86 |
| E | Sub-competitions of the busiest parent | with index | ref | idx_competitions_parent | 5 | 14.1 |
| E | Sub-competitions of the busiest parent | index ignored | ALL | none | 6867 | 31.23 |
| F | Venues by city (no index on city_name) | as written | ALL | none | 4200 | 11.93 |
| G | Players by competitions played (no index) | as written | ALL | none | 1000 | 14.44 |
| H | Query 1.1: competitions with category name (JOIN on the foreign key) | as written | c: ALL; cat: eq_ref | c: none; cat: PRIMARY | 6867 | 313.32 |
| I | Query 2.5: complexes with more than one venue (JOIN + GROUP BY) | as written | v: index; cx: eq_ref | v: idx_venues_complex; cx: PRIMARY | 4200 | 68.27 |

## What the numbers say

- Case A (Venues in a country): with the index the plan reads about 65 rows (ref) instead of 4,200 (ALL), roughly 64.6x fewer. Median time 14.89 ms vs 17.64 ms.
- Case B (Players of one country): with the index the plan reads about 10 rows (ref) instead of 1,000 (ALL), roughly 100.0x fewer. Median time 10.8 ms vs 11.73 ms.
- Case C (Top 5 ranks): with the index the plan reads about 10 rows (range) instead of 1,000 (ALL), roughly 100.0x fewer. Median time 10.43 ms vs 11.13 ms.
- Case D (Doubles competitions): with the index the plan reads about 3,051 rows (ref) instead of 6,867 (ALL), roughly 2.3x fewer. Median time 76.77 ms vs 100.86 ms.
- Case E (Sub-competitions of the busiest parent): with the index the plan reads about 5 rows (ref) instead of 6,867 (ALL), roughly 1373.4x fewer. Median time 14.1 ms vs 31.23 ms.

## How to read this

- **type = ALL** is a full table scan. **ref, range, const and eq_ref** are index lookups.
- **Est. rows** is how many rows MySQL expects to read. Fewer is better.
- On small tables the optimizer may choose a scan even when an index exists. That is correct behaviour, and the index pays off as the data grows (a larger refresh history, more players, more competitions).
- Cases F and G have no index on the filtered column and show the full-scan baseline.
- Cases H and I are JOINs: the first table is read in full because the query returns every row, and the joined table is reached through an index lookup (eq_ref / ref) on the key, not by scanning it again.
