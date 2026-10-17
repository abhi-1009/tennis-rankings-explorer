-- =====================================================================
-- Tennis project: all required SQL queries
-- Database: tennis_db (MySQL)
-- =====================================================================
-- On Aiven, the database is also called tennis_db (created by db/init_db.py), so this line works there too.
USE tennis_db;

-- ---------------------------------------------------------------------
-- PART 1: COMPETITIONS
-- ---------------------------------------------------------------------

-- 1.1 List all competitions along with their category name
SELECT c.competition_id, c.competition_name, c.type, c.gender, cat.category_name
FROM Competitions c
LEFT JOIN Categories cat ON cat.category_id = c.category_id
ORDER BY cat.category_name, c.competition_name;

-- 1.2 Count the number of competitions in each category
SELECT cat.category_name, COUNT(*) AS competition_count
FROM Competitions c
JOIN Categories cat ON cat.category_id = c.category_id
GROUP BY cat.category_id, cat.category_name
ORDER BY competition_count DESC;

-- 1.3 Find all competitions of type 'doubles'
SELECT competition_id, competition_name, gender, category_id
FROM Competitions
WHERE type = 'doubles';

-- 1.4 Get competitions that belong to a specific category (e.g. ITF Men)
-- Check the exact name first:  SELECT category_name FROM Categories;
SELECT c.competition_id, c.competition_name, c.type, c.gender
FROM Competitions c
JOIN Categories cat ON cat.category_id = c.category_id
WHERE cat.category_name = 'ITF Men';

-- 1.5 Identify parent competitions and their sub-competitions
SELECT p.competition_id   AS parent_id,
       p.competition_name AS parent_name,
       s.competition_id   AS sub_competition_id,
       s.competition_name AS sub_competition_name
FROM Competitions s
JOIN Competitions p ON p.competition_id = s.parent_id
ORDER BY p.competition_name, s.competition_name;

-- 1.6 Analyze the distribution of competition types by category
SELECT cat.category_name, c.type, COUNT(*) AS competition_count
FROM Competitions c
JOIN Categories cat ON cat.category_id = c.category_id
GROUP BY cat.category_name, c.type
ORDER BY cat.category_name, competition_count DESC;

-- 1.7 List all competitions with no parent (top-level competitions)
SELECT competition_id, competition_name, type, gender
FROM Competitions
WHERE parent_id IS NULL;

-- ---------------------------------------------------------------------
-- PART 2: COMPLEXES AND VENUES
-- ---------------------------------------------------------------------

-- 2.1 List all venues along with their associated complex name
SELECT v.venue_id, v.venue_name, v.city_name, v.country_name, cx.complex_name
FROM Venues v
LEFT JOIN Complexes cx ON cx.complex_id = v.complex_id
ORDER BY cx.complex_name, v.venue_name;

-- 2.2 Count the number of venues in each complex
SELECT cx.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes cx
LEFT JOIN Venues v ON v.complex_id = cx.complex_id
GROUP BY cx.complex_id, cx.complex_name
ORDER BY venue_count DESC;

-- 2.3 Get details of venues in a specific country (e.g. Chile)
SELECT venue_id, venue_name, city_name, country_name, country_code, timezone
FROM Venues
WHERE country_name = 'Chile';

-- 2.4 Identify all venues and their timezones
SELECT venue_name, city_name, country_name, timezone
FROM Venues
ORDER BY timezone, venue_name;

-- 2.5 Find complexes that have more than one venue
SELECT cx.complex_name, COUNT(v.venue_id) AS venue_count
FROM Complexes cx
JOIN Venues v ON v.complex_id = cx.complex_id
GROUP BY cx.complex_id, cx.complex_name
HAVING COUNT(v.venue_id) > 1
ORDER BY venue_count DESC;

-- 2.6 List venues grouped by country
SELECT country_name,
       COUNT(*) AS venue_count,
       GROUP_CONCAT(venue_name ORDER BY venue_name SEPARATOR ', ') AS venues
FROM Venues
GROUP BY country_name
ORDER BY venue_count DESC;

-- 2.7 Find all venues for a specific complex (e.g. Nacional)
SELECT v.venue_id, v.venue_name, v.city_name, v.country_name
FROM Venues v
JOIN Complexes cx ON cx.complex_id = v.complex_id
WHERE cx.complex_name = 'Nacional';

-- ---------------------------------------------------------------------
-- PART 3: DOUBLES COMPETITOR RANKINGS
-- "Current week" = the latest (year, week) loaded in Competitor_Rankings.
-- ---------------------------------------------------------------------

-- 3.1 Get all competitors with their rank and points (latest week)
SELECT c.name, c.country, r.ranking_name, r.`rank`, r.points
FROM Competitor_Rankings r
JOIN Competitors c ON c.competitor_id = r.competitor_id
WHERE (r.year, r.week) = (SELECT year, week FROM Competitor_Rankings
                          ORDER BY year DESC, week DESC LIMIT 1)
ORDER BY r.ranking_name, r.`rank`;

-- 3.2 Find competitors ranked in the top 5 (latest week)
SELECT c.name, c.country, r.ranking_name, r.`rank`, r.points
FROM Competitor_Rankings r
JOIN Competitors c ON c.competitor_id = r.competitor_id
WHERE r.`rank` <= 5
  AND (r.year, r.week) = (SELECT year, week FROM Competitor_Rankings
                          ORDER BY year DESC, week DESC LIMIT 1)
ORDER BY r.ranking_name, r.`rank`;

-- 3.3 List competitors with no rank movement (stable rank)
SELECT c.name, c.country, r.ranking_name, r.`rank`, r.movement
FROM Competitor_Rankings r
JOIN Competitors c ON c.competitor_id = r.competitor_id
WHERE r.movement = 0
  AND (r.year, r.week) = (SELECT year, week FROM Competitor_Rankings
                          ORDER BY year DESC, week DESC LIMIT 1)
ORDER BY r.`rank`;

-- 3.4 Get the total points of competitors from a specific country (e.g. Croatia)
SELECT c.country, SUM(r.points) AS total_points
FROM Competitor_Rankings r
JOIN Competitors c ON c.competitor_id = r.competitor_id
WHERE c.country = 'Croatia'
  AND (r.year, r.week) = (SELECT year, week FROM Competitor_Rankings
                          ORDER BY year DESC, week DESC LIMIT 1)
GROUP BY c.country;

-- 3.5 Count the number of competitors per country
SELECT country, COUNT(*) AS competitor_count
FROM Competitors
GROUP BY country
ORDER BY competitor_count DESC;

-- 3.6 Find competitors with the highest points in the current week
SELECT c.name, c.country, r.ranking_name, r.points
FROM Competitor_Rankings r
JOIN Competitors c ON c.competitor_id = r.competitor_id
WHERE (r.year, r.week) = (SELECT year, week FROM Competitor_Rankings
                          ORDER BY year DESC, week DESC LIMIT 1)
  AND r.points = (SELECT MAX(points) FROM Competitor_Rankings
                  WHERE (year, week) = (SELECT year, week FROM Competitor_Rankings
                                        ORDER BY year DESC, week DESC LIMIT 1));
