-- Farm Climate Twin: feature layer. Every feature uses only tmax, tmin, precip, so the SAME
-- SQL can later run on NEX-GDDP-CMIP6 projections (which provide those variables) for the twin match.
DROP VIEW IF EXISTS v_features; DROP VIEW IF EXISTS v_region_year; DROP VIEW IF EXISTS v_warm_months; DROP VIEW IF EXISTS v_quality;

-- Data-quality check: coverage and missing share per region.
CREATE VIEW v_quality AS
SELECT region_id, COUNT(*) AS days, MIN(date) AS first_day, MAX(date) AS last_day,
       ROUND(100.0 * SUM(tmax IS NULL OR precip IS NULL) / COUNT(*), 2) AS pct_missing
FROM daily_climate GROUP BY region_id;

-- Warm season = each region's 3 hottest months (works in both hemispheres).
CREATE VIEW v_warm_months AS
SELECT region_id, mo FROM (
  SELECT region_id, CAST(substr(date,6,2) AS INT) AS mo,
         RANK() OVER (PARTITION BY region_id ORDER BY AVG(tmax) DESC) AS rk
  FROM daily_climate GROUP BY region_id, mo) WHERE rk <= 3;

-- Per region-year metrics over the latest 20 years; dry spells via gaps-and-islands.
CREATE VIEW v_region_year AS
WITH d AS (
  SELECT c.region_id, c.date, substr(c.date,1,4) AS yr, c.tmax, c.tmin, c.precip,
         CASE WHEN c.precip < 1 THEN 1 ELSE 0 END AS dry, CASE WHEN w.mo IS NOT NULL THEN 1 ELSE 0 END AS warm
  FROM daily_climate c
  LEFT JOIN v_warm_months w ON w.region_id = c.region_id AND w.mo = CAST(substr(c.date,6,2) AS INT)
  WHERE CAST(substr(c.date,1,4) AS INT) > (SELECT MAX(CAST(substr(date,1,4) AS INT)) - 20 FROM daily_climate)),
g AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY region_id, yr ORDER BY date)
          - ROW_NUMBER() OVER (PARTITION BY region_id, yr, dry ORDER BY date) AS grp FROM d),
spell AS (
  SELECT region_id, yr, MAX(n) AS longest FROM (
    SELECT region_id, yr, COUNT(*) AS n FROM g WHERE dry = 1 GROUP BY region_id, yr, grp) GROUP BY region_id, yr)
SELECT d.region_id, d.yr, AVG(tmax) AS tmax_mean, AVG(CASE WHEN warm THEN tmax END) AS warm_tmax,
       SUM(precip) AS precip_mm, SUM(CASE WHEN warm THEN precip END) AS warm_precip_mm,
       SUM(tmax > 35) AS heat_days, SUM(tmin < 0) AS frost_days,
       SUM(MAX(0, (tmax + tmin)/2 - 10)) AS gdd10, COALESCE(s.longest, 0) AS dry_spell
FROM d LEFT JOIN spell s ON s.region_id = d.region_id AND s.yr = d.yr GROUP BY d.region_id, d.yr;

-- One row per region: the 8-feature climate fingerprint used for the twin match (phase 4).
CREATE VIEW v_features AS
SELECT r.region_id, r.name, r.country, r.is_target,
       ROUND(AVG(tmax_mean),2) AS tmax_mean, ROUND(AVG(warm_tmax),2) AS warm_tmax,
       ROUND(AVG(precip_mm),0) AS precip_mm, ROUND(AVG(warm_precip_mm),0) AS warm_precip_mm,
       ROUND(AVG(heat_days),1) AS heat_days, ROUND(AVG(frost_days),1) AS frost_days,
       ROUND(AVG(gdd10),0) AS gdd10, ROUND(AVG(dry_spell),1) AS dry_spell, COUNT(*) AS years
FROM v_region_year y JOIN regions r ON r.region_id = y.region_id GROUP BY r.region_id;
