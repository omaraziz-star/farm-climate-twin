"""Phase 3: pull NEX-GDDP-CMIP6 daily projections for the target farm from NASA THREDDS into climate_twin.db.
  py extract_future.py --models ACCESS-CM2 --ssps ssp245 --years 2040 2041 --hist 2013 2014   # small test
  py extract_future.py                                                                      # full default run
Default: 3 climate models, baseline 2000-2014 (historical run), ssp245 + ssp585 for 2035-2050.
Resumable: re-run the same command and it skips year-files already loaded. Standard library only."""
import argparse, csv, io, sqlite3, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = "https://ds.nccs.nasa.gov/thredds/ncss/grid/AMES/NEX/GDDP-CMIP6/%s/%s/r1i1p1f1/%s/%s.nc"
VARS = ("tasmax", "tasmin", "pr")
SUFFIXES = ("_v2.0", "", "_v1.1")      # some files carry a version suffix (test showed _v2.0 for ACCESS-CM2 ssp245)

def fetch_year(model, scen, var, year, lat, lon):
    q = urllib.parse.urlencode({"var": var, "latitude": lat, "longitude": lon, "accept": "csv",
                                "time_start": "%d-01-01T00:00:00Z" % year, "time_end": "%d-12-31T23:59:59Z" % year})
    for suf in SUFFIXES:
        name = "%s_day_%s_%s_r1i1p1f1_gn_%d%s" % (var, model, scen, year, suf)
        for attempt in range(3):
            try:
                text = urllib.request.urlopen(ROOT % (model, scen, var, name) + "?" + q, timeout=300).read().decode()
                rows = list(csv.reader(io.StringIO(text)))[1:]
                return {r[0][:10]: float(r[-1]) for r in rows if r and r[-1] not in ("", "NaN")}
            except urllib.error.HTTPError as e:
                if e.code == 404: break                     # wrong filename suffix: try the next one
                time.sleep(5 * (attempt + 1))
            except Exception:
                time.sleep(5 * (attempt + 1))
    return None

def fetch_all(job, lat, lon):
    model, scen, year = job
    d = {v: fetch_year(model, scen, v, year, lat, lon) for v in VARS}
    if any(x is None for x in d.values()): return job, None
    days = sorted(set(d["tasmax"]) & set(d["tasmin"]) & set(d["pr"]))
    # units: Kelvin -> Celsius; precipitation kg m-2 s-1 -> mm/day
    return job, [(scen, model, x, round(d["tasmax"][x]-273.15, 2), round(d["tasmin"][x]-273.15, 2), round(d["pr"][x]*86400, 2)) for x in days]

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--db", default="climate_twin.db")
    p.add_argument("--models", nargs="+", default=["ACCESS-CM2", "MPI-ESM1-2-HR", "MRI-ESM2-0"])
    p.add_argument("--ssps", nargs="+", default=["ssp245", "ssp585"])
    p.add_argument("--years", nargs=2, type=int, default=[2035, 2050]); p.add_argument("--hist", nargs=2, type=int, default=[2000, 2014])
    p.add_argument("--workers", type=int, default=3); a = p.parse_args(argv)
    con = sqlite3.connect(a.db)
    lat, lon = con.execute("SELECT lat, lon FROM regions WHERE is_target = 1").fetchone(); lon = round(lon % 360, 2)
    con.execute("""CREATE TABLE IF NOT EXISTS future_climate(scenario TEXT, model TEXT, date TEXT, tmax REAL, tmin REAL,
                   precip REAL, PRIMARY KEY(scenario, model, date))""")
    jobs = [(m, "historical", y) for m in a.models for y in range(a.hist[0], a.hist[1]+1)] + \
           [(m, s, y) for m in a.models for s in a.ssps for y in range(a.years[0], a.years[1]+1)]
    todo = [j for j in jobs if con.execute("SELECT COUNT(*) FROM future_climate WHERE model=? AND scenario=? AND date LIKE ?",
                                           (j[0], j[1], "%d-%%" % j[2])).fetchone()[0] < 360]
    print(len(todo), "of", len(jobs), "year-files to fetch for", lat, lon); failed = []
    with ThreadPoolExecutor(a.workers) as ex:
        for job, rows in ex.map(lambda j: fetch_all(j, lat, lon), todo):
            if rows:
                con.executemany("INSERT OR REPLACE INTO future_climate VALUES (?,?,?,?,?,?)", rows); con.commit(); print("ok", *job, len(rows), "days")
            else:
                failed.append(job); print("FAILED", *job)
    print("\nSUMMARY (scenario, model, days, mean daily high C, mean annual rain mm):")
    for r in con.execute("""SELECT scenario, model, COUNT(*), ROUND(AVG(tmax),1),
                            ROUND(SUM(precip)/COUNT(DISTINCT substr(date,1,4)),0) FROM future_climate GROUP BY 1,2 ORDER BY 1,2"""):
        print(r)
    print("failed year-files:", failed or "none")

if __name__ == "__main__":
    main()
