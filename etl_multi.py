"""Farm Climate Twin, phases 1-2: NASA POWER daily climate for a target farm + candidate regions
-> SQLite -> feature views (features.sql) -> features.csv (for Python / Tableau).
  python etl_multi.py --start 2005 --end 2024    # live pull; resumable (skips regions already loaded)
  python etl_multi.py --synthetic                # offline TEST data, not real"""
import argparse, csv, datetime, json, math, random, sqlite3, time, urllib.request

PARS = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR"]   # same variables exist in NEX-GDDP-CMIP6

def fetch(lat, lon, y0, y1, tries=4):
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=%s&community=AG&longitude=%s"
           "&latitude=%s&start=%d0101&end=%d1231&format=JSON" % (",".join(PARS), lon, lat, y0, y1))
    for i in range(tries):
        try:
            p = json.load(urllib.request.urlopen(url, timeout=180))["properties"]["parameter"]; break
        except Exception:
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))
    f = lambda v: None if v == -999 else v          # POWER fill value for missing data
    return [(k[:4]+"-"+k[4:6]+"-"+k[6:], *[f(p[x][k]) for x in PARS]) for k in p[PARS[0]]]

def synthetic(lat, y0, y1):
    rng = random.Random(int(abs(lat)*1000)); amp = 6+0.25*abs(lat); base = 33-0.38*abs(lat)
    pr = rng.uniform(.15, .4); sc = rng.uniform(4, 10); flip = -1 if lat < 0 else 1; d = datetime.date(y0, 1, 1); rows = []
    while d.year <= y1:
        s = flip*math.sin(2*math.pi*(d.timetuple().tm_yday-110)/365); tmax = base+amp*s+0.04*(d.year-y0)+rng.gauss(0, 3.5)
        rain = rng.random() < pr*(1+0.3*s)
        rows.append((d.isoformat(), round(tmax, 1), round(tmax-11, 1), round(rng.expovariate(1/sc), 1) if rain else 0.0))
        d += datetime.timedelta(days=1)
    return rows

if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--start", type=int, default=2005); a.add_argument("--end", type=int, default=2024)
    a.add_argument("--db", default="climate_twin.db"); a.add_argument("--synthetic", action="store_true"); a = a.parse_args()
    regions = list(csv.DictReader(open("regions.csv"))); con = sqlite3.connect(a.db)
    con.executescript("""CREATE TABLE IF NOT EXISTS regions(region_id TEXT PRIMARY KEY, name TEXT, country TEXT, lat REAL, lon REAL, is_target INT);
      CREATE TABLE IF NOT EXISTS daily_climate(region_id TEXT, date TEXT, tmax REAL, tmin REAL, precip REAL, PRIMARY KEY(region_id, date));
      CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);""")
    con.execute("INSERT OR REPLACE INTO meta VALUES ('source', ?)", ("SYNTHETIC test data (not NASA)" if a.synthetic else "NASA POWER daily API",))
    for r in regions:
        con.execute("INSERT OR REPLACE INTO regions VALUES (?,?,?,?,?,?)", (r["region_id"], r["name"], r["country"], r["lat"], r["lon"], r["is_target"]))
        if con.execute("SELECT COUNT(*) FROM daily_climate WHERE region_id=?", (r["region_id"],)).fetchone()[0]: continue  # resume
        rows = synthetic(float(r["lat"]), a.start, a.end) if a.synthetic else fetch(r["lat"], r["lon"], a.start, a.end)
        con.executemany("INSERT INTO daily_climate VALUES (?,?,?,?,?)", [(r["region_id"], *x) for x in rows]); con.commit()
        print("loaded", r["region_id"], len(rows), "days"); time.sleep(0 if a.synthetic else 1)
    con.executescript(open("features.sql").read()); con.commit()
    cur = con.execute("SELECT * FROM v_features ORDER BY is_target DESC, region_id")
    with open("features.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow([c[0] for c in cur.description]); w.writerows(cur)
    print("QUALITY (worst 3):", con.execute("SELECT region_id, days, pct_missing FROM v_quality ORDER BY pct_missing DESC LIMIT 3").fetchall())
    print("wrote features.csv")
