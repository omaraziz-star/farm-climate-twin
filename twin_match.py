"""Phase 4: find the climate twin. Needs climate_twin.db from phases 1 and 3. Run:  py twin_match.py
Delta method: future target = real NASA POWER baseline for the farm + each climate model's OWN change
(2035-2050 vs 2000-2014). Then rank the candidate regions by climate distance to that future fingerprint,
once per model x scenario, and report how stable the match is. Writes twin_results.csv and twin_summary.csv."""
import csv, math, sqlite3, statistics as st

FEATS = ["tmax_mean", "warm_tmax", "precip_mm", "warm_precip_mm", "cool_precip_mm", "heat_days", "frost_days", "gdd10", "warm_dry_spell"]
GROUPS = {"heat": ["tmax_mean", "warm_tmax", "heat_days", "gdd10"], "cold": ["frost_days"],
          "water": ["precip_mm", "warm_precip_mm", "cool_precip_mm"], "dry": ["warm_dry_spell"]}
RATIO = {"precip_mm", "warm_precip_mm", "cool_precip_mm"}     # rainfall change applied as a ratio, the rest as a difference
TARGET = "US_KS_RENO"

def weights(mode):
    if mode == "equal": return {f: 1.0 for f in FEATS}
    return {f: 1.0 / len(fs) for fs in GROUPS.values() for f in fs}   # correlated features share one vote per group

def main(db="climate_twin.db"):
    con = sqlite3.connect(db)
    con.executescript("""DROP TABLE IF EXISTS series_daily;
      CREATE TABLE series_daily(series_id TEXT, date TEXT, tmax REAL, tmin REAL, precip REAL);
      INSERT INTO series_daily SELECT region_id, date, tmax, tmin, precip FROM daily_climate;
      INSERT INTO series_daily SELECT 'RENO|' || model || '|' || scenario, date, tmax, tmin, precip FROM future_climate;""")
    con.executescript(open("twin.sql").read())
    F = {r[0]: dict(zip(FEATS, r[1:])) for r in con.execute("SELECT series_id, " + ",".join(FEATS) + " FROM v_sf")}
    names = dict(con.execute("SELECT region_id, name FROM regions"))
    present = {k: v for k, v in F.items() if "|" not in k}
    mu = {f: st.mean(v[f] for v in present.values()) for f in FEATS}
    sd = {f: st.pstdev([v[f] for v in present.values()]) or 1.0 for f in FEATS}
    base = present[TARGET]; cands = [k for k in present if k != TARGET]
    runs = sorted({tuple(k.split("|")[1:]) for k in F if "|" in k and not k.endswith("|historical")})   # (model, ssp)

    def future(model, ssp):
        h, s = F["RENO|%s|historical" % model], F["RENO|%s|%s" % (model, ssp)]
        return {f: base[f] * s[f] / h[f] if f in RATIO else max(0.0, base[f] + s[f] - h[f]) for f in FEATS}

    def rank(fp, w):
        z = lambda v, f: (v[f] - mu[f]) / sd[f]
        return sorted((math.sqrt(sum(w[f] * (z(fp, f) - z(present[r], f)) ** 2 for f in FEATS)), r) for r in cands)

    print("HOW EACH MODEL CHANGES THE FARM (2035-2050 vs 2000-2014):")
    for model, ssp in runs:
        h, s = F["RENO|%s|historical" % model], F["RENO|%s|%s" % (model, ssp)]
        print("  %-14s %s  daily high %+.1f C | yearly rain %+.0f%% | heat days %+.0f" % (
            model, ssp, s["tmax_mean"] - h["tmax_mean"], 100 * (s["precip_mm"] / h["precip_mm"] - 1), s["heat_days"] - h["heat_days"]))
    rows = [(mode, m, sp, i, r, names[r], round(d, 3)) for mode in ("grouped", "equal")
            for m, sp in runs for i, (d, r) in enumerate(rank(future(m, sp), weights(mode)), 1)]
    summ = []
    for mode in ("grouped", "equal"):
        for r in cands:
            rk = [x[3] for x in rows if x[0] == mode and x[4] == r]
            summ.append((mode, r, names[r], sum(k == 1 for k in rk), sum(k <= 3 for k in rk), round(st.mean(rk), 1), len(rk)))
    summ.sort(key=lambda x: (x[0] != "grouped", -x[3], -x[4], x[5]))
    for fn, hdr, data in (("twin_results.csv", "weighting,model,scenario,rank,region_id,region,distance", rows),
                          ("twin_summary.csv", "weighting,region_id,region,times_rank1,times_top3,mean_rank,n_runs", summ)):
        with open(fn, "w", newline="") as f:
            w = csv.writer(f); w.writerow(hdr.split(",")); w.writerows(data)
    print("\nTODAY'S CLOSEST MATCHES TO THE FARM:", ", ".join(names[r] for _, r in rank(base, weights("grouped"))[:3]))
    for mode in ("grouped", "equal"):
        print("\nCLIMATE TWINS FOR 2035-2050 (%s feature weights), top 5 of %d model x scenario runs:" % (mode, len(runs)))
        for x in [s for s in summ if s[0] == mode][:5]:
            print("  %-26s #1 in %d runs | top-3 in %d runs | mean rank %.1f" % (x[2], x[3], x[4], x[5]))

if __name__ == "__main__":
    main()
