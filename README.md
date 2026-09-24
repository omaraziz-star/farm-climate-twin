# Farm Climate Twin

**Question:** If a farm's climate in 2040 resembles a region's climate today, what can that region teach us about which crop rotations hold up?

Built for the NASA Space Apps 2026 challenge *Field Shift: Adapting Farms with NASA Data*. Target farm: Reno County, Kansas (dryland wheat, sorghum, soybean, corn).

## Approach
1. Pull 20 years of daily temperature and rainfall from **NASA POWER** for the target and ~30 rainfed grain regions worldwide.
2. Engineer an 8-feature climate fingerprint per region in **SQL** (heat days, dry spells, growing degree days, warm-season rainfall, and more).
3. Pull 2035-2050 projections from **NASA NEX-GDDP-CMIP6** for the target, using multiple climate models and two emissions scenarios.
4. Rank analog regions by climate similarity, cluster regions, and report how stable the match is across models.
5. Replay past seasons in the analog regions to compare rotations on water stress and heat exposure, validated against crop yields where available (US only).
6. Tableau Public dashboard and written case study.

## Status
| Phase | Status |
|---|---|
| 1. Multi-region NASA POWER pipeline | Done |
| 2. SQL feature layer + data-quality checks | Done |
| 3. Future climate extraction (NEX-GDDP-CMIP6) | Planned |
| 4. Similarity and clustering | Planned |
| 5. Rotation time machine + yield validation | Planned |
| 6. Dashboard and case study | Planned |

## Run it
Python 3 only, no packages, no API key.
```
python etl_multi.py --start 2005 --end 2024      # real NASA POWER pull, resumable
python etl_multi.py --synthetic --db test.db     # offline test with fake data
```
Outputs `features.csv` (one row per region). The `--synthetic` flag generates fake data for testing only.

## Limitations
- Climate analogs ignore soil, irrigation, management, and economics, so they are hypotheses, not guarantees.
- Rotation performance is constructed from single-crop yields, since yield statistics do not cover rotations.
- Region coordinates are approximate representative points; POWER's grid is coarse (about 0.5 degrees).
- NEX-GDDP-CMIP6 is intended for research use; this is an analytics portfolio project, not agronomic advice.

## Data
NASA POWER (power.larc.nasa.gov) and NASA NEX-GDDP-CMIP6 (nccs.nasa.gov). Cite per their terms.

## Findings
_To be added after running on real data._
