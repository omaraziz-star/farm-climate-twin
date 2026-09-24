"""Phase 5: do climate stress and real USDA county yields move together, in BOTH Reno County KS and Enid (Garfield Co) OK?
Then: how steady are different crop mixes in real harvest data?
Needs climate_twin.db (phase 1) and USDA Quick Stats yield CSVs in this folder (any file names).  Run:  py yield_validation.py"""
import csv, glob, math, sqlite3, statistics as st

COUNTY_TO_REGION = {("KANSAS", "RENO"): "US_KS_RENO", ("OKLAHOMA", "GARFIELD"): "US_OK_ENID"}
CROP_OF = {"WHEAT": "wheat", "SORGHUM": "sorghum", "SOYBEANS": "soybeans", "CORN": "corn"}
# crop, water-window months, heat-window months, heat threshold C, freeze-window months (0,0 = none). ILLUSTRATIVE windows.
WINDOWS = [("wheat", 3, 5, 5, 6, 32, 3, 4), ("sorghum", 6, 8, 6, 8, 35, 0, 0), ("soybeans", 7, 8, 7, 8, 35, 0, 0), ("corn", 6, 8, 6, 8, 35, 0, 0)]
ROTATIONS = {"Wheat-Sorghum": ["wheat", "sorghum"], "Wheat-Sorghum-Soy": ["wheat", "sorghum", "soybeans"],
             "Wheat-Corn-Soy": ["wheat", "corn", "soybeans"], "Corn-Soy": ["corn", "soybeans"]}
TCRIT = {5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 12: 2.179, 14: 2.145, 16: 2.120, 18: 2.101, 20: 2.086, 25: 2.060, 30: 2.042}
LO, HI = 2005, 2024                                            # years covered by the NASA POWER pull

def load_yields():
    out = {}
    for fn in glob.glob("*.csv"):
        with open(fn, newline="", encoding="utf-8-sig") as f:
            rd = csv.DictReader(f)
            if not rd.fieldnames or "Data Item" not in rd.fieldnames: continue
            for r in rd:
                item, key = r["Data Item"], (r["State"].upper(), r["County"].upper())
                if key not in COUNTY_TO_REGION or r["Commodity"] not in CROP_OF: continue
                if "YIELD, MEASURED IN BU / ACRE" not in item or "IRRIGATED" in item: continue
                if r["Commodity"] == "WHEAT" and "WINTER" not in item: continue
                try: out[(COUNTY_TO_REGION[key], CROP_OF[r["Commodity"]], int(r["Year"]))] = float(r["Value"].replace(",", ""))
                except ValueError: continue                    # suppressed values like (D)
    return out

def rcrit(n):
    df = n - 2; t = TCRIT[max(k for k in TCRIT if k <= df)] if df >= 5 else 9
    return t / math.sqrt(df + t * t)

def main():
    Y = {k: v for k, v in load_yields().items() if LO <= k[2] <= HI}
    print("Yield records used:", len(Y), "| county-crop series:", sorted({(k[0], k[1]) for k in Y}))
    if not Y: return print("No yield CSVs found in this folder. Put the USDA files here and re-run.")
    con = sqlite3.connect("climate_twin.db")
    con.executescript("DROP TABLE IF EXISTS crop_windows; CREATE TABLE crop_windows(crop TEXT, w0 INT, w1 INT, h0 INT, h1 INT, heat_c REAL, f0 INT, f1 INT);"
                      "DROP TABLE IF EXISTS county_yield; CREATE TABLE county_yield(region_id TEXT, crop TEXT, yr INT, yield REAL);")
    con.executemany("INSERT INTO crop_windows VALUES (?,?,?,?,?,?,?,?)", WINDOWS)
    con.executemany("INSERT INTO county_yield VALUES (?,?,?,?)", [(*k[:2], k[2], v) for k, v in Y.items()])
    con.executescript(open("yield.sql").read())
    groups = {}
    for reg, crop, yr, y, w, h, fz in con.execute("SELECT * FROM v_yield_climate ORDER BY yr"):
        groups.setdefault((reg, crop), []).append((yr, y, w, h, fz))
    anom, rows, signs = {}, [], {}
    print("\nDO CLIMATE STRESS AND YIELD MOVE TOGETHER? (yield vs. trend, correlation r; * = significant at 5%)")
    for (reg, crop), g in sorted(groups.items()):
        if len(g) < 8: print("  %-11s %-9s only %d years, skipped" % (reg, crop, len(g))); continue
        yrs, ys = [x[0] for x in g], [x[1] for x in g]; sl, ic = st.linear_regression(yrs, ys)
        a = [100 * (y - (ic + sl * t)) / (ic + sl * t) for t, y in zip(yrs, ys)]
        anom.update({(reg, crop, t): v for t, v in zip(yrs, a)}); res = []
        for name, idx in (("water", 2), ("heat", 3), ("freeze", 4)):
            xs = [x[idx] for x in g]
            try: r = st.correlation(xs, a)
            except Exception: r = None
            res.append(r); signs[(crop, name, reg)] = None if r is None else (r > 0)
        txt = ["  n/a  " if r is None else "%+.2f%s" % (r, "*" if abs(r) >= rcrit(len(g)) else " ") for r in res]
        k = max(range(len(a)), key=lambda i: abs(a[i])); drop = []          # robustness: drop the most extreme year
        for idx in (2, 3, 4):
            try: drop.append(st.correlation([x[idx] for i, x in enumerate(g) if i != k], [v for i, v in enumerate(a) if i != k]))
            except Exception: drop.append(None)
        note = " | sensitive to %d" % yrs[k] if any(r is not None and d is not None and abs(r - d) > 0.2 for r, d in zip(res, drop)) else ""
        print("  %-11s %-9s n=%2d | water %s | heat %s | freeze %s%s" % (reg, crop, len(g), *txt, note))
        rows.append([reg, crop, len(g)] + [None if r is None else round(r, 3) for r in res])
    same = [(c, n) for (c, n, r) in signs if r == "US_KS_RENO" and signs[(c, n, r)] is not None
            and signs.get((c, n, "US_OK_ENID")) is not None]
    agree = sum(signs[(c, n, "US_KS_RENO")] == signs[(c, n, "US_OK_ENID")] for c, n in same)
    if same: print("\nTWIN CHECK: Kansas and Oklahoma show the same direction of climate effect in %d of %d crop-indicator pairs." % (agree, len(same)))
    print("\nHOW STEADY ARE CROP MIXES? (yield variability, % vs trend; real harvests, crops averaged within each year)")
    out = []
    for reg in sorted({k[0] for k in anom}):
        for name, crops in ROTATIONS.items():
            yrs = [t for t in range(LO, HI + 1) if all((reg, c, t) in anom for c in crops)]
            if len(yrs) < 8: continue
            idx = [st.mean(anom[(reg, c, t)] for c in crops) for t in yrs]
            single = st.mean(st.pstdev([anom[(reg, c, t)] for t in yrs]) for c in crops)
            out.append([reg, name, len(yrs), round(st.pstdev(idx), 1), round(min(idx), 1), sum(v < -15 for v in idx), round(100 * (1 - st.pstdev(idx) / single))])
            print("  %-11s %-18s n=%2d | swing %.1f%% | worst year %.1f%% | bad years %d | %d%% steadier than single crops" % (reg, name, *out[-1][2:]))
    for fn, hdr, data in (("yield_validation.csv", "region_id,crop,n_years,r_water,r_heat,r_freeze", rows),
                          ("rotation_stability.csv", "region_id,rotation,n_years,swing_pct,worst_year_pct,bad_years,pct_steadier_than_single", out)):
        with open(fn, "w", newline="") as f: w = csv.writer(f); w.writerow(hdr.split(",")); w.writerows(data)

if __name__ == "__main__":
    main()
