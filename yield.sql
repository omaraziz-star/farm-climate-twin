-- Phase 5: crop-season stress indicators from NASA POWER daily data, joined to real USDA county yields.
DROP VIEW IF EXISTS v_yield_climate; DROP VIEW IF EXISTS v_stress;

CREATE VIEW v_stress AS
WITH d AS (
  SELECT region_id, CAST(substr(date,1,4) AS INT) AS yr, CAST(substr(date,6,2) AS INT) AS mo, tmax, tmin, precip
  FROM daily_climate WHERE region_id IN ('US_KS_RENO', 'US_OK_ENID'))
SELECT c.crop, d.region_id, d.yr,
       SUM(CASE WHEN d.mo BETWEEN c.w0 AND c.w1 THEN d.precip END) AS water_mm,
       SUM(CASE WHEN d.mo BETWEEN c.h0 AND c.h1 AND d.tmax > c.heat_c THEN 1 ELSE 0 END) AS heat_days,
       SUM(CASE WHEN d.mo BETWEEN c.f0 AND c.f1 AND d.tmin < -2 THEN 1 ELSE 0 END) AS freeze_days
FROM d CROSS JOIN crop_windows c GROUP BY c.crop, d.region_id, d.yr;

CREATE VIEW v_yield_climate AS
SELECT y.region_id, y.crop, y.yr, y.yield, s.water_mm, s.heat_days, s.freeze_days
FROM county_yield y JOIN v_stress s ON s.region_id = y.region_id AND s.crop = y.crop AND s.yr = y.yr;
