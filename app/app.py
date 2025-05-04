import os
import math
import traceback
from flask import Flask, request, jsonify, render_template
import OpenVisus as ov
import requests
import threading

app = Flask(__name__)

# Ensure caching directory is set
os.environ["VISUS_CACHE"] = "./visus_cache_can_be_erased"

# Connect once at startup
try:
    db = ov.LoadDataset(
        "http://atlantis.sci.utah.edu/mod_visus?dataset=nex-gddp-cmip6&cached=arco"
    )
    app.logger.info("OpenVisus dataset loaded successfully.")
except Exception:
    app.logger.error("Failed to load OpenVisus dataset:")
    app.logger.error(traceback.format_exc())
    raise

# Preload country boundaries\countries_geojson = None
def load_countries():
    global countries_geojson
    try:
        url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
        resp = requests.get(url)
        resp.raise_for_status()
        countries_geojson = resp.json()
        app.logger.info("Countries GeoJSON loaded.")
    except Exception:
        app.logger.error("Failed to load countries GeoJSON:")
        app.logger.error(traceback.format_exc())

threading.Thread(target=load_countries, daemon=True).start()


def sanitize(obj):
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/countries')
def get_countries():
    if countries_geojson is None:
        return jsonify({"error": "Countries not loaded yet"}), 503
    return jsonify(countries_geojson)


@app.route('/api/data')
def get_climate_data():
    field   = request.args.get('field')
    time    = request.args.get('time', type=int)
    quality = request.args.get('quality', default=0, type=int)

    # Debug incoming parameters
    app.logger.info(f"/api/data called with field={field}, time={time}, quality={quality}")

    if not field or time is None:
        return jsonify({"error": "Missing 'field' or 'time' parameter"}), 400

    try:
        # Query the OpenVisus dataset
        data = db.read(field=field, time=time, quality=quality)
        raw = data.tolist()
        clean = sanitize(raw)
        return jsonify({
            'field':   field,
            'time':    time,
            'quality': quality,
            'data':    clean
        })
    except Exception as e:
        app.logger.error("Exception in /api/data:")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
