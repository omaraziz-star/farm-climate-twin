-- Phase 4 feature layer (v2). Runs on series_daily = NASA POWER regions + climate-model series for the target farm.
-- Fixes from the phase 2 review: dry spell is measured inside the warm season, and cool-season rain is added
-- (winter-wheat regions like Northam or Konya get their rain in the cool months).
DROP VIEW IF EXISTS v_sf; DROP VIEW IF EXISTS v_sf_year; DROP VIEW IF EXISTS v_season_months;

-- Warm season = 3 hottest months, cool season = 3 coolest months, per series (works in both hemispheres).
CREATE VIEW v_season_months AS
SELECT series_id, mo, CASE WHEN rk_hot <= 3 THEN 'warm' ELSE 'cool' END AS season FROM (
  SELECT series_id, CAST(substr(date,6,2) AS INT) AS mo,
         RANK() OVER (PARTITION BY series_id ORDER BY AVG(tmax) DESC) AS rk_hot,
         RANK() OVER (PARTITION BY series_id ORDER BY AVG(tmax) ASC)  AS rk_cold
  FROM series_daily GROUP BY series_id, mo) WHERE rk_hot <= 3 OR rk_cold <= 3;

CREATE VIEW v_sf_year AS
WITH d AS (
  SELECT s.series_id, s.date, substr(s.date,1,4) AS yr, s.tmax, s.tmin, s.precip, m.season,
         CASE WHEN s.precip < 1 THEN 1 ELSE 0 END AS dry
  FROM series_daily s LEFT JOIN v_season_months m ON m.series_id = s.series_id AND m.mo = CAST(substr(s.date,6,2) AS INT)),
g AS (   -- gaps-and-islands on warm-season days only
  SELECT *, ROW_NUMBER() OVER (PARTITION BY series_id, yr ORDER BY date)
          - ROW_NUMBER() OVER (PARTITION BY series_id, yr, dry ORDER BY date) AS grp FROM d WHERE season = 'warm'),
spell AS (
  SELECT series_id, yr, MAX(n) AS longest FROM (
    SELECT series_id, yr, COUNT(*) AS n FROM g WHERE dry = 1 GROUP BY series_id, yr, grp) GROUP BY series_id, yr)
SELECT d.series_id, d.yr, AVG(tmax) AS tmax_mean, AVG(CASE WHEN season = 'warm' THEN tmax END) AS warm_tmax,
       SUM(precip) AS precip_mm, SUM(CASE WHEN season = 'warm' THEN precip END) AS warm_precip_mm,
       SUM(CASE WHEN season = 'cool' THEN precip END) AS cool_precip_mm,
       SUM(tmax > 35) AS heat_days, SUM(tmin < 0) AS frost_days,
       SUM(MAX(0, (tmax + tmin)/2 - 10)) AS gdd10, COALESCE(sp.longest, 0) AS warm_dry_spell
FROM d LEFT JOIN spell sp ON sp.series_id = d.series_id AND sp.yr = d.yr GROUP BY d.series_id, d.yr;

-- One 9-feature climate fingerprint per series (averaged over all years available for that series).
CREATE VIEW v_sf AS
SELECT series_id, AVG(tmax_mean) AS tmax_mean, AVG(warm_tmax) AS warm_tmax, AVG(precip_mm) AS precip_mm,
       AVG(warm_precip_mm) AS warm_precip_mm, AVG(cool_precip_mm) AS cool_precip_mm, AVG(heat_days) AS heat_days,
       AVG(frost_days) AS frost_days, AVG(gdd10) AS gdd10, AVG(warm_dry_spell) AS warm_dry_spell, COUNT(*) AS years
FROM v_sf_year GROUP BY series_id;
