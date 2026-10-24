# Data quality report

Generated 2026-10-24 14:39 UTC · database `tennis_db` · latest ranking snapshot: year 2026, week 43

**Summary:** 10 checks passed, 0 warnings, 5 informational findings.

## 1. Table sizes

| Table | Rows |
|---|---|
| Categories | 18 |
| Competitions | 6717 |
| Complexes | 784 |
| Venues | 4156 |
| Competitors | 1030 |
| Competitor_Rankings | 2000 |

## 2. Missing values and placeholders

Each row shows how many values were missing in the API data, what the pipeline did, and why.

| Table | Column | Issue | Rows affected | % of table | Treatment | Why this is justified |
|---|---|---|---|---|---|---|
| Venues | city_name | City missing in API | 0 | 0.0 | Stored as 'Unknown' | Column is NOT NULL; the venue is still useful for its country and timezone. |
| Venues | country_name | Country missing in API | 0 | 0.0 | Stored as 'Unknown' | Keeps the venue row instead of silently dropping it. |
| Venues | country_code | Country code missing in API | 0 | 0.0 | Stored as 'UNK' | CHAR(3) NOT NULL; 'UNK' is easy to filter out and cannot be mistaken for a real code. |
| Venues | timezone | Timezone missing in API | 0 | 0.0 | Stored as 'Unknown' | Guessing a timezone from the country would invent data. |
| Competitions | level | No level label in API | 5984 | 89.09 | Left NULL | Level is optional; most events have none, so a default would distort the level chart. |
| Competitions | gender | Gender missing in API | 0 | 0.0 | Stored as 'unknown' | NOT NULL column; keeps the event visible in type and category analysis. |
| Competitions | type | Type missing in API | 0 | 0.0 | Stored as 'unknown' | NOT NULL column; flagged value is easy to exclude. |
| Competitions | category_id | No category in API | 0 | 0.0 | Left NULL | The foreign key allows NULL, and a fake category would corrupt the category counts. |
| Competitions | parent_id | Top-level event (not an error) | 623 | 9.27 | Left NULL | Top-level competitions have no parent by design (query 1.7 depends on this). |
| Competitors | country | Country missing in API | 0 | 0.0 | Stored as 'Unknown' | Keeps the player in rankings; excluded from country analysis by name. |
| Competitors | country_code | Country code missing in API | 51 | 4.95 | Stored as 'UNK' | Needed as CHAR(3) NOT NULL; the map page ignores unknown codes. |
| Competitors | abbreviation | Abbreviation missing in API | 0 | 0.0 | Stored as 'N/A' | Abbreviation is cosmetic and not used in any analysis. |
| Competitor_Rankings | points | Zero points | 0 | 0.0 | Kept as 0 | A real value for players with no points, not a missing one. |
| Competitor_Rankings | competitions_played | Zero competitions played | 0 | 0.0 | Kept as 0 | A real value; also the default if the field is absent. |
| Competitor_Rankings | rank | Rank 0 (not possible for a real rank) | 0 | 0.0 | Kept as 0 so it is detectable | Ranks start at 1, so any 0 would indicate a parsing problem. |

## 3. Integrity, duplicates and ties

| Check | Result | Status | Note |
|---|---|---|---|
| Orphan category links (Competitions → Categories) | 0 | PASS | Enforced by a foreign key. |
| Orphan complex links (Venues → Complexes) | 0 | PASS | Enforced by a foreign key. |
| Orphan competitor links (Rankings → Competitors) | 0 | PASS | Enforced by a foreign key. |
| Duplicate ranking snapshots | 0 | PASS | The unique key uq_ranking_snapshot prevents this. |
| Parent ids that point to a missing competition | 6093 | INFO | Not enforced on purpose: the API can reference a parent it does not return. |
| Complexes without any venue | 161 | INFO | Possible when the API lists a complex with an empty venue list. |
| Players sharing a name (different ids) | 0 | INFO | Can be two real players with the same name; ids are the identity. |
| Venues sharing name, city and country | 257 | INFO | Generic names such as 'Court 1' repeat across complexes; ids are the identity. |
| Tied rank groups (doubles partners share a rank) | 27 | INFO | Expected: both partners of a doubles team carry the same rank. |

## 4. Domain checks (values must make sense)

| Check | Violations | Status |
|---|---|---|
| Rank is at least 1 | 0 | PASS |
| Points are not negative | 0 | PASS |
| Competitions played is not negative | 0 | PASS |
| Week number is between 1 and 53 | 0 | PASS |
| Competitor country codes have 3 letters | 0 | PASS |
| Venue country codes have 3 letters | 0 | PASS |

## 5. Outliers (IQR rule: above Q3 + 1.5 × IQR)

| Ranking list | Column | Players | Min | Median | Max | Upper fence | Above fence | Decision |
|---|---|---|---|---|---|---|---|---|
| ATP | points | 500 | 108.0 | 279.5 | 10360.0 | 1551.2 | 50 | Kept: genuine elite values, removing them would delete the top players |
| ATP | competitions_played | 500 | 1.0 | 22.0 | 41.0 | 54.0 | 0 | No values above the fence |
| WTA | points | 500 | 133.0 | 306.5 | 11260.0 | 1454.0 | 61 | Kept: genuine elite values, removing them would delete the top players |
| WTA | competitions_played | 500 | 1.0 | 17.0 | 45.0 | 41.0 | 1 | Kept: genuine elite values, removing them would delete the top players |

Outliers are **kept**: very high points belong to the best players, who are the most important rows. ATP and WTA points use different scales, so they are summarised per list.

## 6. Week-over-week validation of `movement`

Compared week (2026, 43) with week (2026, 42) for 970 players present in both (30 new). The stored `movement` equals the real rank change for **99.9%** of them, which means: **positive movement = moved up**.
