# Farm Climate Twin

**Question:** If a farm's climate in 2035-2050 resembles a region's climate today, what can that region teach us about which crop rotations hold up?

Built by Omar Aziz for the 2026 NASA Space Apps Challenge, *Field Shift: Adapting Farms with NASA Data*. Target farm: Reno County, Kansas (dryland wheat, sorghum, soybean, corn).

**Live dashboard:** https://public.tableau.com/app/profile/omar.aziz/viz/FarmClimateTwin/Dashboard1
**Case study:** https://docs.google.com/document/d/1c1ycs2qPvffBo8V2MZkwMeDJ_5qioz0mq7xH8ul8Q4U

## Key findings (real NASA and USDA data)
- **Warming:** all 3 climate models agree the farm's average daily high rises **+1.3 to +2.0 C** in 2035-2050 versus 2000-2014, with roughly 20-29 more days per year above 35 C.
- **Rainfall:** models **disagree** on direction, from **-10% to +12%** in yearly rain, so rainfall should be treated as uncertain.
- **Climate twin:** Reno County's 2035-2050 climate is most similar to **present-day Enid, Oklahoma** (about 115 miles south). Enid ranked #1 in all 6 model-scenario runs under two different feature weightings.
- **Yield validation (2005-2024 USDA county yields):** summer crops respond to climate exactly as expected, and *the same way in both counties*. More growing-season rain raised corn, sorghum, and soybean yields; more extreme-heat days lowered them (5 of 6 correlations significant at p < .05, n = 11-18 years). Climate effects pointed the same direction in Reno and Enid in **8 of 9 crop-indicator pairs**, supporting the twin match with independent data. Winter wheat showed no clear relationship in either county, a genuine null result, not a forced one.
- **Crop diversification lowers risk, in both counties.** Comparing years where a farm split acreage evenly across a crop mix (not a multi-year rotation sequence), **Wheat-Corn-Soy** was the steadiest mix in both Reno and Enid (28% and 43% less year-to-year swing than single crops, respectively) and had a smaller worst-year loss than **Corn-Soy**, which was the least steady mix in both counties.
- **Caveat:** with only 11-18 years of county data, results for corn and sorghum in Kansas are sensitive to the single worst year (2011); the script flags this automatically. Treat single-crop-indicator correlations as suggestive, and the cross-county agreement as the stronger evidence.

## Approach
1. **Baseline:** 20 years (2005-2024) of daily temperature and rainfall from NASA POWER for the target and 30 rainfed grain regions worldwide.
2. **Features (SQL):** a 9-feature climate fingerprint per region (heat days, frost days, growing degree days, warm- and cool-season rain, warm-season dry spells, and more).
3. **Future climate:** NEX-GDDP-CMIP6 daily projections from NASA THREDDS (3 models, SSP2-4.5 and SSP5-8.5, 2035-2050, plus a 2000-2014 baseline).
4. **Delta method:** future farm climate = real POWER baseline + each model's own change, so the two datasets' biases do not mix.
5. **Twin match:** rank candidate regions by standardized climate distance per model and scenario; test stability with a second weighting scheme.
6. **Yield validation:** join daily NASA POWER climate to real USDA NASS county yields (wheat, sorghum, soybeans, corn; 2005-2024) for Reno and Garfield (Enid) counties. Test whether climate stress correlates with yield, whether that relationship agrees across the twin pair, and how much a diversified crop mix reduces yield volatility versus single crops.
7. **Dashboard and case study:** results laid out in an interactive Tableau dashboard and a one-page case study (links above).

## Status
| Phase | Status |
|---|---|
| 1. Multi-region NASA POWER pipeline | Done |
| 2. SQL feature layer + data-quality checks | Done |
| 3. Future climate extraction (NEX-GDDP-CMIP6) | Done |
| 4. Climate-twin match + sensitivity check | Done |
| 5. Yield validation + crop-mix stability | Done |
| 6. Tableau dashboard and case study | Done |

## Run it (Python 3, no packages, no API keys)
```
py etl_multi.py --start 2005 --end 2024      # phase 1-2: NASA POWER for 31 regions -> climate_twin.db
py extract_future.py                          # phase 3: NEX-GDDP-CMIP6 projections for the farm
py twin_match.py                              # phase 4: writes twin_results.csv and twin_summary.csv
py yield_validation.py                        # phase 5: needs USDA Quick Stats CSVs in this folder
```
`etl_multi.py --synthetic --db test.db` generates fake data for testing only.

## Files
`regions.csv` candidate regions | `features.sql`, `twin.sql`, `yield.sql` SQL feature layers (window functions, CTEs, gaps-and-islands) | `etl_multi.py`, `extract_future.py`, `twin_match.py`, `yield_validation.py` pipeline | `features.csv`, `twin_results.csv`, `twin_summary.csv`, `yield_validation.csv`, `rotation_stability.csv` outputs | USDA yield CSVs (ks_/ok_ prefix, downloaded by hand from quickstats.nass.usda.gov) — not committed if large; see Data below

## Limitations
- Only 3 climate models; the ranking of candidates is limited to the 31 regions chosen, so a better twin may exist outside the list.
- A climate analog ignores soil, irrigation, management, and economics; it is a hypothesis to investigate, not proof.
- The heat-day count uses a fixed 35 C threshold, and models run about 1 C warm, so heat-day changes may be overstated.
- NASA POWER's grid is coarse (about 0.5 degrees) and NEX-GDDP is 0.25 degrees; region coordinates are approximate points.
- Crop water/heat windows in the SQL are illustrative estimates, not sourced from agronomy references.
- The "rotation" comparison measures a diversified crop mix (average outcome across crops grown the same year), not a multi-year rotation sequence on the same field; it does not capture soil-nitrogen or pest-cycle effects of true rotation.
- County yield series are short (11-19 years) with some years withheld by USDA; some correlations are sensitive to a single extreme year (flagged in script output).
- NEX-GDDP-CMIP6 is intended for research use; this is an analytics portfolio project, not agronomic advice.

## Data
NASA POWER (power.larc.nasa.gov); NASA NEX-GDDP-CMIP6 via NCCS THREDDS (nccs.nasa.gov); USDA NASS Quick Stats (quickstats.nass.usda.gov). Cite per their terms.
