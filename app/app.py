import os
from io import BytesIO
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from flask import Flask, request, jsonify, send_file, render_template
import OpenVisus as ov
import requests
from PIL import Image
import matplotlib.cm as cm
from shapely.geometry import shape
from shapely import contains_xy

# Flask setup 
app = Flask(__name__)
os.environ["VISUS_CACHE"] = "./visus_cache_can_be_erased"

# OpenVisus dataset connection 
try:
    db = ov.LoadDataset(
        "http://atlantis.sci.utah.edu/mod_visus?dataset=nex-gddp-cmip6&cached=arco"
    )
    app.logger.info("OpenVisus dataset loaded successfully.")
except Exception as e:
    app.logger.error("Failed to load OpenVisus dataset:")
    app.logger.error(e)
    raise


#  GeoJSON countries 
countries_geojson = None


def load_countries():
    global countries_geojson
    try:
        url = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson"
        resp = requests.get(url)
        resp.raise_for_status()
        countries_geojson = resp.json()
        app.logger.info("Countries GeoJSON loaded.")
    except Exception as e:
        app.logger.error("Failed to load countries GeoJSON:")
        app.logger.error(e)


threading.Thread(target=load_countries, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/countries')
def get_countries():
    if countries_geojson is None:
        return jsonify({"error": "Countries not loaded yet"}), 503
    return jsonify(countries_geojson)


varlist = ["hurs", "huss", "pr", "rlds", "rsds",
           "sfcWind", "tas", "tasmax", "tasmin"]
modellist = ["CESM2", "ACCESS-CM2", "CMCC-CM2-SR5", "INM-CM5-0", "CanESM5",
             "MRI-ESM2-0", "MPI-ESM1-2-HR", "MIROC6", "IPSL-CM6A-LR", "GFDL-ESM4"]
scenariolist = ["historical", "ssp585", "ssp370", "ssp245"]


def calculate_day_of_year(date_str: str) -> int:
    date = datetime.strptime(date_str, '%Y-%m-%d')
    start = datetime(date.year, 1, 1)
    return (date - start).days


def get_timestep(date_str: str) -> int:
    date = datetime.strptime(date_str, '%Y-%m-%d')
    doy = calculate_day_of_year(date_str)
    leap = 1 if ((date.year % 4 == 0 and date.year % 100 != 0)
                 or (date.year % 400 == 0)) else 0
    return date.year * (365 + leap) + doy


PAD_TOP = 0   # number of rows of “empty” data to insert at the very top
PAD_BOTTOM = 120   # number of rows of “empty” data to insert at the very bottom


def compute_wet_bulb(T_kelvin: np.ndarray, RH_percent: np.ndarray) -> np.ndarray:
    """
    Compute wet‑bulb temperature (°C) from:
      - T_kelvin: air temperature in Kelvin
      - RH_percent: relative humidity in percent (0–100)
    Uses the Stull (2011) approximation, but clamps RH so sqrt never sees a negative:
      Tw = T * atan(0.151977√(RH+8.313659)) + atan(T+RH)
           – atan(RH–1.676331) + 0.00391838·RH^1.5·atan(0.023101·RH) – 4.686035
    T must be in °C, RH in %.
    """
    # 1) Convert to workable arrays, handle NaNs by treating them as zero humidity
    T = T_kelvin - 273.15
    RH0 = np.nan_to_num(RH_percent, nan=0.0, neginf=0.0, posinf=100.0)

    # 2) Clamp argument to sqrt to ≥0
    sqrt_arg = RH0 + 8.313659
    sqrt_arg = np.clip(sqrt_arg, 0.0, None)

    # 3) Core formula
    term1 = T * np.arctan(0.151977 * np.sqrt(sqrt_arg))
    term2 = np.arctan(T + RH0)
    term3 = -np.arctan(RH0 - 1.676331)
    term4 = 0.00391838 * RH0**1.5 * np.arctan(0.023101 * RH0)

    Tw = term1 + term2 + term3 + term4 - 4.686035

    # 4) Any remaining NaNs (e.g. from T or RH originally NaN) stay NaN
    return Tw


@app.route('/api/global_heatmap.png')
def global_heatmap():
    """
    Equirectangular RGBA heatmap.  If variable=wetbulb,
    compute wet‑bulb(T=tas, RH=hurs). Otherwise read the named field.
    """
    # 1) Read knobs
    date_str = request.args.get('date',     "1950-01-01")
    var = request.args.get('variable', "wetbulb")
    model = request.args.get('model',    "ACCESS-CM2")
    raw_scen = request.args.get('scenario', "historical")
    quality = request.args.get('quality',  0, type=int)

    # 2) Force historical before 2015
    year = datetime.strptime(date_str, "%Y-%m-%d").year
    scenario = "historical" if year < 2015 else raw_scen
    t_idx = get_timestep(date_str)

    # 3) Helper to build CMIP6 field name
    def make_fname(v):
        run = "r4i1p1f1" if model == "CESM2" else "r1i1p1f1"
        return f"{v}_day_{model}_{scenario}_{run}_gn"

    # 4) Read / compute the array
    if var == "wetbulb":
        block_t = db.read(field=make_fname("tas"),
                          time=t_idx, quality=quality)
        block_rh = db.read(field=make_fname("hurs"),
                           time=t_idx, quality=quality)
        arr_t = block_t.toNumPy() if hasattr(block_t, "toNumPy") else block_t
        arr_rh = block_rh.toNumPy() if hasattr(block_rh, "toNumPy") else block_rh
        arr = compute_wet_bulb(arr_t, arr_rh)
    else:
        block = db.read(field=make_fname(var), time=t_idx, quality=quality)
        arr = block.toNumPy() if hasattr(block, "toNumPy") else block

    # 5) Orient so north=up, west=left
    arr = np.flipud(arr)
    arr = np.roll(arr, shift=arr.shape[1]//2, axis=1)

    # 6) Optional pad
    if PAD_TOP or PAD_BOTTOM:
        arr = np.pad(
            arr,
            ((PAD_TOP, PAD_BOTTOM), (0, 0)),
            mode='constant',
            constant_values=np.nan
        )

    # 7) Robust normalization
    flat = arr[np.isfinite(arr)]
    if flat.size:
        vmin, vmax = np.nanpercentile(flat, [2, 98])
    else:
        vmin, vmax = 0.0, 1.0
    norm = (arr - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(arr)
    norm = np.clip(norm, 0.0, 1.0)

    # 8) Colormap → RGBA uint8 & return PNG
    rgba8 = (cm.inferno(norm) * 255).astype(np.uint8)
    img = Image.fromarray(rgba8, mode="RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route('/api/top_changes')
def top_changes():
    """
    Compute delta T over time and economic impact with DICE quadratic
    """
    # 0) Ensure country boundaries are loaded
    if countries_geojson is None:
        return jsonify({"error": "Countries not loaded yet"}), 503

    # 1) Parse query parameters
    metric = request.args.get('metric',    'wetbulb')
    model = request.args.get('model',     'ACCESS-CM2')
    raw_scen = request.args.get('scenario',  'historical')
    start_date = request.args.get('start_date', '1950-01-01')
    end_date = request.args.get('end_date',  '1951-01-01')
    quality = request.args.get('quality',   0, type=int)
    top_n = request.args.get('top_n',     5, type=int)

    # 2) Scenario logic (historical before 2015)
    def pick_scenario(dstr):
        year = datetime.strptime(dstr, "%Y-%m-%d").year
        return 'historical' if year < 2015 else raw_scen

    # 3) Helpers for field naming & reading
    def fname_for(var, scen):
        run = "r4i1p1f1" if model == "CESM2" else "r1i1p1f1"
        return f"{var}_day_{model}_{scen}_{run}_gn"

    def read_arr(var, date_str):
        scen = pick_scenario(date_str)
        t_idx = get_timestep(date_str)
        blk = db.read(field=fname_for(var, scen), time=t_idx, quality=quality)
        return blk.toNumPy() if hasattr(blk, "toNumPy") else blk

    # 4) Accumulate year‑by‑year deltas between start and end
    sd = datetime.strptime(start_date, "%Y-%m-%d")
    ed = datetime.strptime(end_date,   "%Y-%m-%d")
    y0, y1 = sd.year, ed.year
    mmdd = sd.strftime("%m-%d")

    sum_delta = None
    for y in range(y0, y1):
        d1 = f"{y}-{mmdd}"
        d2 = f"{y+1}-{mmdd}"
        if metric == 'wetbulb':
            T1, RH1 = read_arr('tas', d1), read_arr('hurs', d1)
            T2, RH2 = read_arr('tas', d2), read_arr('hurs', d2)
            arr1 = compute_wet_bulb(T1, RH1)
            arr2 = compute_wet_bulb(T2, RH2)
        else:
            arr1 = read_arr(metric, d1)
            arr2 = read_arr(metric, d2)
        delta_i = arr2 - arr1
        sum_delta = delta_i.astype(
            np.float64) if sum_delta is None else sum_delta + delta_i

    # If start_year == end_year, fallback to zero change
    if sum_delta is None:
        tmp = read_arr(metric, start_date)
        sum_delta = np.zeros_like(tmp, dtype=np.float64)

    H, W = sum_delta.shape

    # 5) Build equirectangular lat/lon grids
    lats = np.linspace(90, -90, H)
    lons = np.linspace(-180, 180, W)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # 6) Exclude these small Antarctic regions
    EXCLUDE = {"Fr. S. Antarctic Lands", "Falkland Is."}

    # Worker function for parallel processing
    def process_feature(feat):
        name = feat['properties'].get(
            'ADMIN') or feat['properties'].get('name')
        if name in EXCLUDE:
            return None
        geom = shape(feat['geometry'])
        mask = contains_xy(geom, lon_grid, lat_grid)
        vals = sum_delta[mask]
        avg_delta = float(np.nanmean(vals)) if vals.size else 0.0
        # DICE quadratic damage
        damage_frac = 0.00236 * (avg_delta ** 2)
        return {'country': name, 'change': avg_delta, 'damage': damage_frac}

    # 7) Parallel map over all features
    with ThreadPoolExecutor() as executor:
        all_results = list(executor.map(
            process_feature, countries_geojson['features']))

    # Filter out excluded entries
    results = [r for r in all_results if r is not None]

    # 8) Sort by descending change, NaNs treated as -∞, take top_n
    def sort_key(item):
        v = item['change']
        return v if np.isfinite(v) else -np.inf

    top_list = sorted(results, key=sort_key, reverse=True)[:top_n]
    return jsonify(top_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
