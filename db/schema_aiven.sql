-- Tennis Rankings Explorer: schema for a cloud MySQL service (Aiven)
-- The database itself is created by db/init_db.py, so there is no CREATE DATABASE or USE here.
-- Order matters because of foreign keys.

-- ---------- Dataset 1: Competitions ----------
CREATE TABLE IF NOT EXISTS Categories (
    category_id   VARCHAR(50)  PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS Competitions (
    competition_id   VARCHAR(50)  PRIMARY KEY,
    competition_name VARCHAR(100) NOT NULL,
    parent_id        VARCHAR(50)  NULL,       -- self-reference, no FK because a parent may be absent from the API data
    type             VARCHAR(20)  NOT NULL,
    gender           VARCHAR(10)  NOT NULL,
    level            VARCHAR(30)  NULL,       -- e.g. atp_250, grand_slam (extra column for the 'levels' filter)
    category_id      VARCHAR(50),
    CONSTRAINT fk_competitions_category
        FOREIGN KEY (category_id) REFERENCES Categories(category_id),
    INDEX idx_competitions_category (category_id),
    INDEX idx_competitions_parent   (parent_id),
    INDEX idx_competitions_type     (type),
    INDEX idx_competitions_level    (level)
);

-- ---------- Dataset 2: Complexes & Venues ----------
CREATE TABLE IF NOT EXISTS Complexes (
    complex_id   VARCHAR(50)  PRIMARY KEY,
    complex_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS Venues (
    venue_id     VARCHAR(50)  PRIMARY KEY,
    venue_name   VARCHAR(100) NOT NULL,
    city_name    VARCHAR(100) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    country_code CHAR(3)      NOT NULL,
    timezone     VARCHAR(100) NOT NULL,
    complex_id   VARCHAR(50),
    CONSTRAINT fk_venues_complex
        FOREIGN KEY (complex_id) REFERENCES Complexes(complex_id),
    INDEX idx_venues_complex (complex_id),
    INDEX idx_venues_country (country_name)
);

-- ---------- Dataset 3: Doubles competitor rankings ----------
-- Competitors must exist before rankings (FK).
CREATE TABLE IF NOT EXISTS Competitors (
    competitor_id VARCHAR(50)  PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    country       VARCHAR(100) NOT NULL,
    country_code  CHAR(3)      NOT NULL,
    abbreviation  VARCHAR(10)  NOT NULL,
    INDEX idx_competitors_country (country),
    INDEX idx_competitors_name    (name)
);

-- Extra columns vs. the brief (ranking_name, year, week, gender) so the
-- sample UI's Year / Week / Gender filters can work, and reloads don't duplicate rows.
CREATE TABLE IF NOT EXISTS Competitor_Rankings (
    rank_id             INT AUTO_INCREMENT PRIMARY KEY,
    `rank`              INT NOT NULL,
    movement            INT NOT NULL,
    points              INT NOT NULL,
    competitions_played INT NOT NULL,
    competitor_id       VARCHAR(50),
    ranking_name        VARCHAR(50) NOT NULL,   -- e.g. ATP / WTA
    year                INT NOT NULL,
    week                INT NOT NULL,
    gender              VARCHAR(10) NOT NULL,
    CONSTRAINT fk_rankings_competitor
        FOREIGN KEY (competitor_id) REFERENCES Competitors(competitor_id),
    UNIQUE KEY uq_ranking_snapshot (competitor_id, ranking_name, year, week),
    INDEX idx_rankings_rank   (`rank`),
    INDEX idx_rankings_points (points),
    INDEX idx_rankings_period (year, week, gender)
);
